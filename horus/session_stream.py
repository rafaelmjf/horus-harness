"""In-app session streaming — run agent turns inside the dashboard process and
fan their events out to browser tabs over Server-Sent Events.

This backs the Control tab's *integrated terminal*: instead of opening a separate
OS console (``horus open``), an in-app session runs the agent **headless**
(``adapter.spawn``/``resume``, the stream-json path) in a background thread, and
its normalized :class:`AgentEvent`s are buffered + pushed to any subscribed tab.
Each typed message is a new turn, resumed by session id so context carries across.

It is deliberately in-process and ephemeral (it lives only as long as the
dashboard server) and zero-dependency — SSE is a plain streaming HTTP response,
no WebSocket library, no async framework. It renders the agent's transcript
(assistant text, tool calls, results), **not** the raw TUI; a true terminal
(xterm.js + a ConPTY via pywinpty) is the deferred higher-fidelity upgrade.
"""

from __future__ import annotations

import itertools
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from horus import adapters


@dataclass
class _Turn:
    """One streamed event, in the shape the browser tab consumes."""

    kind: str                       # user | text | tool | tool_result | result | status | error
    text: str | None = None
    tool: str | None = None
    is_error: bool = False

    def as_payload(self) -> dict:
        d: dict = {"kind": self.kind}
        if self.text is not None:
            d["text"] = self.text
        if self.tool is not None:
            d["tool"] = self.tool
        if self.is_error:
            d["is_error"] = True
        return d


@dataclass
class InAppSession:
    client_id: str                  # stable id assigned at tab creation
    agent: str
    project_dir: Path
    account: str | None = None
    model: str | None = None
    posture: str = "default"
    title: str = ""
    session_id: str | None = None   # the agent's real id (from SESSION_STARTED), for resume
    status: str = "idle"            # idle | running | exited | failed
    events: list[_Turn] = field(default_factory=list)
    _cond: threading.Condition = field(default_factory=threading.Condition, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def _append(self, turn: _Turn) -> None:
        with self._cond:
            self.events.append(turn)
            self._cond.notify_all()

    def _set_status(self, status: str) -> None:
        self.status = status
        self._append(_Turn("status", text=status))


# Maps an adapter EventType to the browser-facing kind + how to extract its fields.
def _to_turn(ev: adapters.AgentEvent) -> _Turn | None:
    et = ev.type
    if et is adapters.EventType.ASSISTANT_TEXT and ev.text:
        return _Turn("text", text=ev.text)
    if et is adapters.EventType.TOOL_USE:
        return _Turn("tool", tool=ev.tool)
    if et is adapters.EventType.TOOL_RESULT:
        return _Turn("tool_result", is_error=ev.is_error)
    if et is adapters.EventType.RESULT:
        return _Turn("result", text=ev.text, is_error=ev.is_error)
    if et is adapters.EventType.ERROR:
        return _Turn("error", text=ev.text or "error", is_error=True)
    return None  # SESSION_STARTED handled separately; RAW/PERMISSION ignored for now


class SessionManager:
    """Owns the live in-app sessions for one dashboard process (thread-safe)."""

    def __init__(self) -> None:
        self._sessions: dict[str, InAppSession] = {}
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
        title: str | None = None,
    ) -> str:
        """Create a session tab and (if ``prompt`` is given) run its first turn.

        Returns the client id used by the SSE stream and the input endpoint. With
        an empty prompt the tab opens idle, waiting for the first typed message.
        """
        client_id = f"app-{next(self._ids)}"
        root = Path(project_dir)
        sess = InAppSession(
            client_id=client_id, agent=agent, project_dir=root, account=account,
            model=model, posture=posture, title=title or f"{root.name} · {account or 'ambient'}",
        )
        with self._lock:
            self._sessions[client_id] = sess
        if prompt:
            self._start_turn(sess, prompt)
        return client_id

    def send_input(self, client_id: str, prompt: str) -> bool:
        """Run another turn (resumed by session id). False if unknown or mid-turn."""
        sess = self.get(client_id)
        if sess is None or sess.status == "running" or not prompt.strip():
            return False
        self._start_turn(sess, prompt)
        return True

    def _start_turn(self, sess: InAppSession, prompt: str) -> None:
        sess._append(_Turn("user", text=prompt))
        sess._set_status("running")
        sess._thread = threading.Thread(target=self._run_turn, args=(sess, prompt), daemon=True)
        sess._thread.start()

    def _run_turn(self, sess: InAppSession, prompt: str) -> None:
        try:
            adapter = adapters.get_adapter(sess.agent)
            spec = adapters.SpawnSpec(
                prompt=prompt,
                project_dir=sess.project_dir,
                account=sess.account,
                posture=adapters.PermissionPosture(sess.posture),
                model=sess.model,
            )
            run = (
                adapter.resume(sess.session_id, spec)
                if sess.session_id
                else adapter.spawn(spec)
            )
            for ev in run:
                if ev.session_id and not sess.session_id:
                    sess.session_id = ev.session_id
                turn = _to_turn(ev)
                if turn is not None:
                    sess._append(turn)
            sess._set_status("failed" if run.session.status == "failed" else "idle")
        except Exception as exc:  # noqa: BLE001 — surface any launch error into the tab
            sess._append(_Turn("error", text=str(exc), is_error=True))
            sess._set_status("failed")

    # --- reads ----------------------------------------------------------------

    def get(self, client_id: str) -> InAppSession | None:
        with self._lock:
            return self._sessions.get(client_id)

    def sessions(self) -> list[InAppSession]:
        with self._lock:
            return list(self._sessions.values())

    # --- SSE ------------------------------------------------------------------

    def subscribe(self, client_id: str, *, heartbeat: float = 15.0) -> Iterator[str]:
        """Yield SSE frames for a tab: every buffered event, then live ones as they
        arrive. Emits a heartbeat comment when idle so a dead client is detected on
        the next write (the HTTP handler stops on the resulting broken pipe)."""
        sess = self.get(client_id)
        if sess is None:
            yield _sse({"kind": "error", "text": "unknown session"})
            return
        cursor = 0
        while True:
            with sess._cond:
                while cursor >= len(sess.events):
                    if not sess._cond.wait(timeout=heartbeat):
                        break  # timed out -> send a heartbeat below
                pending = sess.events[cursor:]
                cursor += len(pending)
            if pending:
                for turn in pending:
                    yield _sse(turn.as_payload())
            else:
                yield ": heartbeat\n\n"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# One manager per dashboard process (the server is single-instance per port).
manager = SessionManager()
