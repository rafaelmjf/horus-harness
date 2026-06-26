"""Tests for the PTY session-host and the cross-platform PTY abstraction."""

import base64
import itertools
import queue
import sys
import time

import pytest

from horus import pty_host
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


def test_host_write_resize_unknown_terminal(tmp_path):
    h = pty_host.PtyHost()
    assert h.write("nope", b"x") is False
    assert h.resize("nope", 80, 24) is False
    assert h.get("nope") is None


def test_subscribe_unknown_terminal_emits_status():
    h = pty_host.PtyHost()
    frames = list(itertools.islice(h.subscribe("ghost", heartbeat=0.05), 1))
    assert frames[0] == "event: status\ndata: unknown\n\n"


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
