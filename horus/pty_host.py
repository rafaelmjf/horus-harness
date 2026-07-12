"""The local session-host: owns real PTY terminals, persists them across viewers.

This is the tmux-style half of the unified-terminal design. A terminal is spawned
under a real pseudo-terminal (:mod:`horus.pty_session`) and **kept alive in this
process regardless of who is watching** — a browser tab attaches by streaming the
scrollback then live output, and detaches simply by disconnecting; the agent keeps
running and can be re-attached (from another tab now; from another machine later).

Scope today is deliberately local and in-process (the dashboard server is the host),
so "re-attach" spans tabs/reloads while Horus runs. A standalone daemon (survive a
Horus restart) and remote attach (over a tailnet, authenticated) are the planned
next stages — the attach protocol here is intentionally transport-agnostic so they
slot in without reshaping it.
"""

from __future__ import annotations

import base64
import itertools
import os
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from horus import adapters
from horus.pty_session import PtySession, spawn_pty

# Cap the per-terminal scrollback kept for re-attach replay. Generous enough that a
# typical session replays intact; an extreme session trims from the front (a TUI
# repaints on the next activity/resize, so the live screen still converges).
SCROLLBACK_CAP = 1_000_000

# Floor between applied resizes for one terminal. A terminal has exactly one
# geometry shared by every viewer (a panel tab, a pop-out, a second device);
# a ResizeObserver/visualViewport-driven client can post several resizes in a
# burst (a fullscreen toggle, an orientation change, two viewers fitting at
# once), and each applied resize is a TIOCSWINSZ that makes the TUI repaint.
# This drops a resize that arrives too soon after the last applied one — a
# later post (there always is one once the box settles) supersedes it.
RESIZE_DEBOUNCE_S = 0.05


@dataclass
class PtyTerminal:
    term_id: str
    agent: str
    project_dir: Path
    account: str | None = None
    title: str = ""
    session_id: str | None = None
    pid: int | None = None
    cols: int = 80
    rows: int = 24
    alive: bool = True
    ended_at: float | None = None   # monotonic time of exit; None while alive
    _pty: PtySession | None = field(default=None, repr=False)
    _buf: bytearray = field(default_factory=bytearray, repr=False)
    _base: int = 0          # absolute offset of _buf[0] (grows as the front is trimmed)
    _total: int = 0         # total bytes ever produced
    _cond: threading.Condition = field(default_factory=threading.Condition, repr=False)
    _last_resize_at: float | None = field(default=None, repr=False)
    # viewer id -> (cols, rows) it can render; PTY takes the per-dimension min.
    _viewers: dict[str, tuple[int, int]] = field(default_factory=dict, repr=False)

    def _append(self, data: bytes) -> None:
        with self._cond:
            self._buf.extend(data)
            self._total += len(data)
            if len(self._buf) > SCROLLBACK_CAP:
                drop = len(self._buf) - SCROLLBACK_CAP
                del self._buf[:drop]
                self._base += drop
            self._cond.notify_all()

    def _mark_dead(self) -> None:
        with self._cond:
            self.alive = False
            self.ended_at = time.monotonic()
            self._cond.notify_all()


class PtyHost:
    """Owns the live PTY terminals for one dashboard process (thread-safe)."""

    def __init__(self) -> None:
        self._terms: dict[str, PtyTerminal] = {}
        self._lock = threading.Lock()
        self._ids = itertools.count(1)

    # --- lifecycle ------------------------------------------------------------

    def start(
        self,
        *,
        agent: str = "claude",
        project_dir: Path | str,
        account: str | None = None,
        model: str | None = None,
        posture: str = "default",
        prompt: str = "",
        cols: int = 80,
        rows: int = 24,
        title: str | None = None,
    ) -> str:
        """Spawn an interactive agent under a PTY; return the terminal id.

        Reuses the adapter's ``interactive_command`` (the same argv as ``horus open``)
        and ``build_env`` (per-account isolation), plus the per-account identity guard.
        ``prompt`` seeds the TUI (e.g. a continuity/resume prompt); empty = fresh.
        """
        adapter = adapters.get_adapter(agent)
        if not hasattr(adapter, "interactive_command"):
            raise ValueError(f"{agent!r} does not support interactive sessions yet.")
        root = Path(project_dir)
        spec = adapters.SpawnSpec(
            prompt=prompt, project_dir=root, account=account,
            posture=adapters.PermissionPosture(posture), model=model,
        )
        if account and getattr(adapter, "config_dirs", {}).get(account) and hasattr(adapter, "verify_account"):
            check = adapter.verify_account(account)
            if not check.ok:
                raise adapters.AccountMismatch(
                    f"account {account!r} login mismatch (found {check.detected_email or 'no login'})."
                )

        session_id = str(uuid.uuid4())
        argv = adapter.interactive_command(spec, session_id=session_id)
        # Mark the hosted runtime so anything running *inside* this PTY (notably the
        # agent's own shell) can tell it lives inside Horus's dashboard process — and
        # which PID is that host. The self-restart guard hook reads these to refuse a
        # command that would kill/restart the very process hosting this session (the
        # footgun in history.md: an in-app agent restarted the app and killed itself).
        env = adapter.build_env(spec)
        env["HORUS_HOSTED_SESSION"] = "1"
        env["HORUS_PTY_HOST_PID"] = str(os.getpid())
        if not env.get("TERM") or env.get("TERM") == "dumb":
            env["TERM"] = "xterm-256color"
        pty = spawn_pty(argv, cwd=root, env=env, cols=cols, rows=rows)

        term_id = f"pty-{next(self._ids)}"
        term = PtyTerminal(
            term_id=term_id, agent=adapter.name, project_dir=root, account=account,
            title=title or f"{root.name} · {account or 'ambient'}",
            session_id=session_id, pid=pty.pid, cols=cols, rows=rows, _pty=pty,
        )
        with self._lock:
            self._terms[term_id] = term
        threading.Thread(target=self._reader, args=(term,), daemon=True).start()
        return term_id

    def _reader(self, term: PtyTerminal) -> None:
        pty = term._pty
        assert pty is not None
        try:
            while True:
                term._append(pty.read())   # blocks; raises EOFError at end
        except EOFError:
            pass
        finally:
            term._mark_dead()

    # --- input / control ------------------------------------------------------

    def write(self, term_id: str, data: bytes) -> bool:
        term = self.get(term_id)
        if term is None or term._pty is None or not term.alive:
            return False
        try:
            term._pty.write(data)
        except OSError:
            return False
        return True

    def resize(self, term_id: str, cols: int, rows: int) -> bool:
        term = self.get(term_id)
        if term is None or term._pty is None or not term.alive:
            return False
        if term.cols == cols and term.rows == rows:
            return True  # no-op: already this size (duplicate/redundant post)
        now = time.monotonic()
        if term._last_resize_at is not None and now - term._last_resize_at < RESIZE_DEBOUNCE_S:
            return False  # dropped: too soon after the last applied resize
        term.cols, term.rows = cols, rows
        term._last_resize_at = now
        try:
            term._pty.resize(cols, rows)
        except OSError:
            return False
        return True

    # --- multi-viewer geometry (smallest-wins) ---------------------------------
    #
    # One PTY holds one cols/rows for every viewer, so two simultaneously visible
    # viewers of different sizes cannot BOTH get a private geometry — last-writer-
    # wins garbled whichever screen wrote earlier (observed live: desktop repaints
    # scattering across a phone's narrower grid). tmux's answer, adopted here:
    # each viewer registers the size it fits, and the PTY takes the per-dimension
    # MINIMUM over registered viewers — every screen can render the full grid;
    # larger viewers simply show margins. A viewer is dropped when its stream
    # disconnects (subscribe() finally) or it reports itself hidden (/pty/release),
    # so a closed/backgrounded desktop tab stops constraining the phone.

    def viewer_resize(self, term_id: str, viewer_id: str, cols: int, rows: int) -> bool:
        """Register viewer `viewer_id`'s fitted size and apply the smallest-wins
        effective geometry. Returns False only for a gone/dead terminal."""
        term = self.get(term_id)
        if term is None or term._pty is None or not term.alive:
            return False
        if cols <= 0 or rows <= 0:
            return True  # ignore nonsense fits; keep the viewer's previous entry
        with self._lock:
            term._viewers[viewer_id] = (cols, rows)
        self._apply_effective(term)
        return True

    def viewer_release(self, term_id: str, viewer_id: str) -> None:
        """Drop a viewer (hidden page or disconnected stream) and re-apply the
        smallest-wins geometry over whoever is left. No viewers left keeps the
        last effective size — nothing is watching, so nothing needs a resize."""
        term = self.get(term_id)
        if term is None:
            return
        with self._lock:
            term._viewers.pop(viewer_id, None)
            remaining = bool(term._viewers)
        if remaining:
            self._apply_effective(term)

    def _apply_effective(self, term: PtyTerminal) -> None:
        with self._lock:
            if not term._viewers:
                return
            cols = min(c for c, _ in term._viewers.values())
            rows = min(r for _, r in term._viewers.values())
        self.resize(term.term_id, cols, rows)

    def kill(self, term_id: str) -> bool:
        term = self.get(term_id)
        if term is None or term._pty is None:
            return False
        term._pty.terminate()
        return True

    def close(self, term_id: str) -> bool:
        """Kill (if still alive) and *forget* a terminal — no tab renders for it
        again. Attached viewers keep their object reference, so they still drain
        the scrollback and receive the final ``exited`` frame."""
        with self._lock:
            term = self._terms.pop(term_id, None)
        if term is None:
            return False
        if term._pty is not None and term.alive:
            term._pty.terminate()
        return True

    def reap_dead(self, *, grace: float = 600.0) -> list[str]:
        """Forget terminals whose process exited more than ``grace`` seconds ago;
        return their ids. Recently-exited ones are kept so a crash right after a
        launch stays inspectable (its scrollback holds the error) until it is
        explicitly closed or the grace lapses."""
        now = time.monotonic()
        with self._lock:
            dead = [
                tid for tid, t in self._terms.items()
                if not t.alive and t.ended_at is not None and now - t.ended_at > grace
            ]
            for tid in dead:
                del self._terms[tid]
        return dead

    # --- reads ----------------------------------------------------------------

    def get(self, term_id: str) -> PtyTerminal | None:
        with self._lock:
            return self._terms.get(term_id)

    def terminals(self) -> list[PtyTerminal]:
        with self._lock:
            return list(self._terms.values())

    # --- attach (SSE) ---------------------------------------------------------

    def subscribe(self, term_id: str, *, heartbeat: float = 15.0, viewer_id: str | None = None) -> Iterator[str]:
        """Yield SSE frames for a viewer: the scrollback, then live output, then a
        final ``status: exited``. A heartbeat comment when idle lets the HTTP handler
        notice a disconnected client on its next write. A ``viewer_id`` ties this
        stream to the viewer's registered geometry: when the stream ends (client
        gone), the viewer stops constraining the smallest-wins PTY size."""
        term = self.get(term_id)
        if term is None:
            yield "event: status\ndata: unknown\n\n"
            return
        if viewer_id is not None:
            try:
                yield from self._subscribe_frames(term, heartbeat)
            finally:
                self.viewer_release(term_id, viewer_id)
            return
        yield from self._subscribe_frames(term, heartbeat)

    def _subscribe_frames(self, term: PtyTerminal, heartbeat: float) -> Iterator[str]:
        # Tell the viewer it attached to a *live* session. A viewer that saw this
        # knows a later ``exited`` means the session ended under its feet (its tab
        # can go away); attaching straight to a dead terminal skips it, so the
        # scrollback of an already-crashed session stays on screen for reading.
        if term.alive:
            yield "event: status\ndata: live\n\n"
        cursor = 0
        while True:
            with term._cond:
                if cursor < term._base:
                    cursor = term._base  # missed bytes trimmed from scrollback
                while cursor >= term._total and term.alive:
                    if not term._cond.wait(timeout=heartbeat):
                        break
                if cursor < term._total:
                    chunk = bytes(term._buf[cursor - term._base:])
                    cursor = term._total
                else:
                    chunk = b""
                done = not term.alive and cursor >= term._total
            if chunk:
                yield "event: output\ndata: " + base64.b64encode(chunk).decode("ascii") + "\n\n"
            elif done:
                yield "event: status\ndata: exited\n\n"
                return
            else:
                yield ": hb\n\n"


# One host per dashboard process (the server is single-instance per port).
host = PtyHost()
