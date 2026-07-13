"""Tests for the PTY session-host and the cross-platform PTY abstraction."""

import base64
import itertools
import queue
import sys
import time

import pytest

from horus import pty_host
from horus.launch import LaunchResult
from horus.pty_session import spawn_pty


class _FakePty:
    """In-memory stand-in for a PtySession: feed output, capture input."""

    def __init__(self):
        self.pid = 4242
        self.written = bytearray()
        self.size = None
        self._q: queue.Queue = queue.Queue()
        self._alive = True

    # producer side (test drives these)
    def feed(self, data: bytes):
        self._q.put(data)

    def eof(self):
        self._q.put(None)

    # PtySession interface
    def read(self) -> bytes:
        item = self._q.get()
        if item is None:
            raise EOFError
        return item

    def write(self, data: bytes) -> None:
        self.written.extend(data)

    def resize(self, cols: int, rows: int) -> None:
        self.size = (cols, rows)

    def isalive(self) -> bool:
        return self._alive

    def terminate(self) -> None:
        self._alive = False
        self._q.put(None)


def _wait(pred, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


def test_host_streams_writes_resizes_and_persists(tmp_path, monkeypatch):
    fake = _FakePty()
    captured: dict = {}

    def _fake_spawn(*a, **k):
        captured.update(k)
        return fake

    monkeypatch.setattr(pty_host, "spawn_pty", _fake_spawn)
    h = pty_host.PtyHost()

    tid = h.start(agent="fake", project_dir=tmp_path, account=None)
    term = h.get(tid)
    assert term is not None and term.pid == 4242 and term.alive

    # The PTY env marks the hosted runtime so the self-restart guard can detect it.
    env = captured.get("env") or {}
    assert env.get("HORUS_HOSTED_SESSION") == "1"
    assert env.get("HORUS_PTY_HOST_PID")  # the host (dashboard) process PID
    assert env.get("TERM") == "xterm-256color"

    # Output the PTY produces is buffered on the host.
    fake.feed(b"hello "); fake.feed(b"world")
    assert _wait(lambda: term._total >= 11)

    # Keystrokes flow back to the PTY; resize is forwarded.
    assert h.write(tid, b"abc") is True
    assert _wait(lambda: bytes(fake.written) == b"abc")
    assert h.resize(tid, 100, 30) is True and fake.size == (100, 30)

    # A late subscriber replays the scrollback, then sees the exit.
    fake.eof()
    assert _wait(lambda: not term.alive)
    frames = list(itertools.islice(h.subscribe(tid, heartbeat=0.05), 5))
    outputs = [f for f in frames if f.startswith("event: output")]
    decoded = b"".join(base64.b64decode(f.split("data: ", 1)[1].strip()) for f in outputs)
    assert b"hello world" in decoded
    assert any("event: status\ndata: exited" in f for f in frames)


def test_managed_host_views_and_closes_same_tmux_session(tmp_path, monkeypatch):
    fake = _FakePty()
    captured = {}
    stopped = []
    monkeypatch.setattr(pty_host.terminal_sessions, "default_target", lambda: "tmux")
    monkeypatch.setattr(
        pty_host.terminal_sessions,
        "launch_tmux",
        lambda **kwargs: captured.update(launch=kwargs) or LaunchResult(
            True,
            kwargs["agent"],
            tmp_path,
            session_id="12345678-1234-1234-1234-123456789abc",
            target_ref="horus-123456781234",
        ),
    )

    def fake_spawn(argv, **kwargs):
        captured.update(argv=argv, spawn=kwargs)
        return fake

    monkeypatch.setattr(pty_host, "spawn_pty", fake_spawn)
    monkeypatch.setattr(
        pty_host.terminal_sessions,
        "stop_session",
        lambda session_id: stopped.append(session_id),
    )

    h = pty_host.PtyHost()
    tid = h.start(
        agent="fake",
        project_dir=tmp_path,
        account="work",
        cols=39,
        rows=25,
        managed=True,
    )
    term = h.get(tid)
    assert term is not None and term.session_id == "12345678-1234-1234-1234-123456789abc"
    assert term.target_ref == "horus-123456781234"
    assert captured["launch"]["attach"] is False
    assert captured["launch"]["cols"] == 39 and captured["launch"]["rows"] == 25
    assert captured["argv"] == ["tmux", "attach-session", "-t", "horus-123456781234"]
    assert captured["spawn"]["cols"] == 39 and captured["spawn"]["rows"] == 25

    assert h.close(tid) is True
    assert stopped == ["12345678-1234-1234-1234-123456789abc"]
    assert h.get(tid) is None
    fake.eof()


def test_managed_host_rolls_back_tmux_when_browser_viewer_fails(tmp_path, monkeypatch):
    stopped = []
    monkeypatch.setattr(pty_host.terminal_sessions, "default_target", lambda: "tmux")
    monkeypatch.setattr(
        pty_host.terminal_sessions,
        "launch_tmux",
        lambda **kwargs: LaunchResult(
            True,
            kwargs["agent"],
            tmp_path,
            session_id="12345678-1234-1234-1234-123456789abc",
            target_ref="horus-123456781234",
        ),
    )
    monkeypatch.setattr(
        pty_host,
        "spawn_pty",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("no pty")),
    )
    monkeypatch.setattr(
        pty_host.terminal_sessions,
        "stop_session",
        lambda session_id: stopped.append(session_id),
    )
    with pytest.raises(ValueError, match="failed to attach browser terminal"):
        pty_host.PtyHost().start(agent="fake", project_dir=tmp_path, managed=True)
    assert stopped == ["12345678-1234-1234-1234-123456789abc"]


def _fake_host(tmp_path, monkeypatch):
    fake = _FakePty()
    monkeypatch.setattr(pty_host, "spawn_pty", lambda *a, **k: fake)
    h = pty_host.PtyHost()
    tid = h.start(agent="fake", project_dir=tmp_path)
    return h, tid, fake


def test_subscribe_announces_live_on_attach_to_running_terminal(tmp_path, monkeypatch):
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    fake.feed(b"boot")
    frames = list(itertools.islice(h.subscribe(tid, heartbeat=0.05), 3))
    # Geometry first (so a mismatched viewer can reset before rendering the
    # replay), then `live`, then output.
    assert frames[0] == "event: geometry\ndata: 80x24\n\n"
    assert frames[1] == "event: status\ndata: live\n\n"
    assert frames[2].startswith("event: output")


def test_subscribe_skips_live_for_dead_terminal(tmp_path, monkeypatch):
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    fake.eof()
    assert _wait(lambda: not h.get(tid).alive)
    frames = list(itertools.islice(h.subscribe(tid, heartbeat=0.05), 2))
    assert frames[0].startswith("event: geometry")
    assert frames[1] == "event: status\ndata: exited\n\n"


def test_close_kills_and_forgets_terminal(tmp_path, monkeypatch):
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    assert h.close(tid) is True
    assert fake.isalive() is False          # a live session is terminated…
    assert h.get(tid) is None               # …and no tab renders for it again
    assert h.close(tid) is False            # idempotent: already forgotten


def test_reap_dead_respects_grace(tmp_path, monkeypatch):
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    assert h.reap_dead() == []              # alive -> never reaped
    fake.eof()
    assert _wait(lambda: not h.get(tid).alive)
    assert h.reap_dead() == []              # freshly dead -> kept (crash stays readable)
    h.get(tid).ended_at = time.monotonic() - 601
    assert h.reap_dead() == [tid]           # past the grace -> forgotten
    assert h.get(tid) is None


def test_host_write_resize_unknown_terminal(tmp_path):
    h = pty_host.PtyHost()
    assert h.write("nope", b"x") is False
    assert h.resize("nope", 80, 24) is False
    assert h.get("nope") is None


def test_resize_is_a_noop_when_size_is_unchanged(tmp_path, monkeypatch):
    # A duplicate/redundant resize post (e.g. two viewers fitting to the same
    # size) shouldn't re-issue a TIOCSWINSZ.
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    assert h.resize(tid, 100, 30) is True and fake.size == (100, 30)
    fake.size = None  # prove the second call never touches the PTY again
    assert h.resize(tid, 100, 30) is True and fake.size is None


def test_resize_debounces_rapid_repeats(tmp_path, monkeypatch):
    # pty_host holds one geometry per terminal shared by every viewer; a
    # ResizeObserver/visualViewport-driven client (or two viewers at once) can
    # post several different resizes in a burst. A resize arriving within the
    # debounce floor of the last *applied* one is dropped — a later post
    # (there always is one once the box settles) supersedes it.
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    assert h.resize(tid, 100, 30) is True and fake.size == (100, 30)
    assert h.resize(tid, 90, 28) is False and fake.size == (100, 30)  # dropped: too soon
    term = h.get(tid)
    term._last_resize_at -= pty_host.RESIZE_DEBOUNCE_S * 2  # simulate the floor elapsing
    assert h.resize(tid, 90, 28) is True and fake.size == (90, 28)  # now applies


def test_subscribe_unknown_terminal_emits_status():
    h = pty_host.PtyHost()
    frames = list(itertools.islice(h.subscribe("ghost", heartbeat=0.05), 1))
    assert frames[0] == "event: status\ndata: unknown\n\n"


def test_viewer_resize_smallest_wins_across_viewers(tmp_path, monkeypatch):
    """Two simultaneously visible viewers must BOTH be able to render the full
    grid: the PTY takes the per-dimension minimum, tmux-style, instead of the
    last writer garbling the other viewer."""
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    assert h.viewer_resize(tid, "desktop", 110, 24) is True
    assert fake.size == (110, 24)
    h.get(tid)._last_resize_at -= pty_host.RESIZE_DEBOUNCE_S * 2
    assert h.viewer_resize(tid, "phone", 38, 26) is True
    assert fake.size == (38, 24)  # min cols from phone, min rows from desktop


def test_viewer_release_restores_remaining_viewer_size(tmp_path, monkeypatch):
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    h.viewer_resize(tid, "desktop", 110, 24)
    h.get(tid)._last_resize_at -= pty_host.RESIZE_DEBOUNCE_S * 2
    h.viewer_resize(tid, "phone", 38, 26)
    h.get(tid)._last_resize_at -= pty_host.RESIZE_DEBOUNCE_S * 2
    h.viewer_release(tid, "phone")          # phone went hidden/disconnected
    assert fake.size == (110, 24)           # desktop gets its full size back
    h.viewer_release(tid, "desktop")        # nobody left -> size kept as-is
    assert fake.size == (110, 24)


def test_viewer_resize_gone_terminal_is_false(tmp_path):
    h = pty_host.PtyHost()
    assert h.viewer_resize("nope", "v1", 80, 24) is False
    h.viewer_release("nope", "v1")  # must not raise


def test_resize_preserves_scrollback_replay(tmp_path, monkeypatch):
    """A resize must NOT drop the buffer: it carries the TUI's mode-setting
    sequences (alt-screen, sync output) a fresh viewer needs, and not every TUI
    repaints on SIGWINCH (Claude Code's trust prompt doesn't — an eager clear
    left viewers blank until a keypress). Replay-poison across grids is handled
    viewer-side (geometry handshake + /pty/redraw + ordered reset marker)."""
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    term = h.get(tid)
    fake.feed(b"OLD-GRID-BYTES")
    assert _wait(lambda: term._total >= 14)
    assert h.resize(tid, 100, 30) is True
    fake.feed(b"NEW-GRID-BYTES")
    assert _wait(lambda: term._total >= 28)
    fake.eof()
    assert _wait(lambda: not term.alive)
    frames = list(itertools.islice(h.subscribe(tid, heartbeat=0.05), 5))
    outputs = [f for f in frames if f.startswith("event: output")]
    decoded = b"".join(base64.b64decode(f.split("data: ", 1)[1].strip()) for f in outputs)
    assert b"OLD-GRID-BYTES" in decoded
    assert b"NEW-GRID-BYTES" in decoded


def test_redraw_jiggles_rows_to_force_full_repaint(tmp_path, monkeypatch):
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    h.resize(tid, 100, 30)
    sizes = []
    fake.resize = lambda cols, rows: sizes.append((cols, rows))
    assert h.redraw(tid) is True
    assert sizes == [(100, 29), (100, 30)]  # rows-1 then back: double SIGWINCH
    assert h.redraw("nope") is False


def test_redraw_reset_marker_orders_old_replay_before_repaint(tmp_path, monkeypatch):
    """The browser reset marker must sit exactly between already-buffered bytes
    and bytes produced by the redraw, even though POST and SSE are independent."""
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    stream = h.subscribe(tid, heartbeat=0.05, viewer_id="phone")
    assert next(stream).startswith("event: geometry")
    assert next(stream) == "event: status\ndata: live\n\n"

    fake.feed(b"OLD-REPLAY")
    assert _wait(lambda: h.get(tid)._total == len(b"OLD-REPLAY"))
    assert h.redraw(tid, "phone-reset-1") is True
    fake.feed(b"FRESH-REPAINT")
    assert _wait(lambda: h.get(tid)._total == len(b"OLD-REPLAYFRESH-REPAINT"))

    # Both byte ranges are already buffered when the subscriber advances. It
    # must split at the marker rather than returning one poisoned combined chunk.
    old = next(stream)
    assert old.startswith("event: output")
    assert base64.b64decode(old.split("data: ", 1)[1].strip()) == b"OLD-REPLAY"
    assert next(stream) == "event: reset\ndata: phone-reset-1\n\n"
    fresh = next(stream)
    assert fresh.startswith("event: output")
    assert base64.b64decode(fresh.split("data: ", 1)[1].strip()) == b"FRESH-REPAINT"
    stream.close()


def test_subscribe_with_viewer_id_releases_geometry_on_disconnect(tmp_path, monkeypatch):
    """A viewer that vanishes without posting /pty/release (killed tab, dropped
    network) must stop constraining the smallest-wins size when its SSE stream
    dies — the stream teardown is the cleanup backstop."""
    h, tid, fake = _fake_host(tmp_path, monkeypatch)
    h.viewer_resize(tid, "desktop", 110, 24)
    h.get(tid)._last_resize_at -= pty_host.RESIZE_DEBOUNCE_S * 2
    h.viewer_resize(tid, "phone", 38, 26)
    assert fake.size == (38, 24)
    stream = h.subscribe(tid, heartbeat=0.05, viewer_id="phone")
    next(stream)                            # attach ('live')
    h.get(tid)._last_resize_at -= pty_host.RESIZE_DEBOUNCE_S * 2
    stream.close()                          # client detached
    assert fake.size == (110, 24)           # phone no longer constrains


def test_spawn_pty_runs_a_real_command(tmp_path):
    """Integration: a real PTY echoes output (platform-native ConPTY / stdlib pty)."""
    argv = ["cmd", "/c", "echo PTYOK"] if sys.platform == "win32" else ["sh", "-c", "echo PTYOK"]
    p = spawn_pty(argv, cwd=tmp_path)
    out = b""
    for _ in range(200):
        try:
            out += p.read()
        except EOFError:
            break
        if not p.isalive():
            try:
                out += p.read()
            except EOFError:
                break
    assert b"PTYOK" in out
