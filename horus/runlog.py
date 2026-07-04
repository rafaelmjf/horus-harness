"""Per-session run logs — the file side of background-worker visibility.

``horus run`` tees every line it prints (session start, assistant text, tool
markers, errors, final status) to ``~/.horus/logs/runs/<session_id>.log`` so a
detached watcher (``horus tail``) can render the same stream from another
terminal. Same log-dir convention as the companion startup logs; per-run files
stay small so there is no rotation. Writing is strictly best-effort: any
``OSError`` is swallowed, because logging must never break the run itself.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from horus import config

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]")


def run_log_path(session_id: str) -> Path:
    """Log file for a session. The id is sanitized because it names a file and
    comes from an agent's output stream, not from us."""
    return config.config_dir() / "logs" / "runs" / f"{_SAFE_ID.sub('-', session_id)}.log"


def run_events_path(session_id: str) -> Path:
    """Structured event sidecar for a session, next to the human-readable log."""
    return config.config_dir() / "logs" / "runs" / f"{_SAFE_ID.sub('-', session_id)}.jsonl"


def utc_iso() -> str:
    """Current aware UTC timestamp for run-event payloads."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_event(session_id: str | None, event: str, **fields: Any) -> None:
    """Append one structured run event as JSONL.

    The sidecar is best-effort like the text log: run visibility must never be
    able to break the agent process.
    """
    if not session_id:
        return
    payload = {
        "ts": utc_iso(),
        "event": event,
        "session_id": session_id,
        **fields,
    }
    try:
        path = run_events_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
    except (OSError, TypeError, ValueError):
        pass


def read_events(session_id: str) -> list[dict[str, Any]]:
    """Best-effort read of a session's structured JSONL events."""
    try:
        lines = run_events_path(session_id).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


class RunLog:
    """Append-only tee for one run's printed lines.

    The session id is not known until the stream's first event, so lines are
    buffered until :meth:`bind` supplies it, then flushed. Every filesystem
    failure is swallowed (the run must not care whether its log exists).
    """

    def __init__(self) -> None:
        self.path: Path | None = None
        self._pending: list[str] = []

    def bind(self, session_id: str | None) -> None:
        if self.path is not None or not session_id:
            return
        self.path = run_log_path(session_id)
        pending, self._pending = self._pending, []
        for line in pending:
            self._append(line)

    def line(self, text: str) -> None:
        if self.path is None:
            self._pending.append(text)
        else:
            self._append(text)

    def _append(self, text: str) -> None:
        assert self.path is not None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except OSError:
            pass


def read_from(path: Path, offset: int) -> tuple[str, int]:
    """Read everything after ``offset`` bytes; return ``(text, new_offset)``.

    The single testable read step of the tail loop. A missing/unreadable file
    reads as empty (the run may not have produced a log yet)."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(offset)
            text = fh.read()
            return text, fh.tell()
    except OSError:
        return "", offset


def follow(
    path: Path,
    offset: int,
    *,
    emit,
    is_terminal,
    poll_interval: float = 0.5,
    quiet_seconds: float = 2.0,
) -> int:
    """Poll ``path`` from ``offset``, passing new text to ``emit``, until
    ``is_terminal()`` reports the session is over AND the file has been quiet
    for ``quiet_seconds`` (a just-finished run may still flush a final line).
    Returns the final offset. Callbacks are injected so tests never sleep."""
    quiet_since: float | None = None
    while True:
        text, offset = read_from(path, offset)
        if text:
            emit(text)
            quiet_since = None
        elif is_terminal():
            now = time.monotonic()
            if quiet_since is None:
                quiet_since = now
            elif now - quiet_since >= quiet_seconds:
                return offset
        time.sleep(poll_interval)
