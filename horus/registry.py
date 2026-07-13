"""Session/process registry — what agent sessions exist and their live state.

The row shape is exactly :class:`horus.adapters.base.AgentSession`:
``(agent, account, project, environment, pid, session_id, status)``. Stored as
JSON at ``~/.horus/registry.json`` so it survives restarts. It is **machine-local**
by nature (it tracks PIDs), which is why it lives under ``~/.horus`` and is not
git-synced — consistent with the file-first ethos; SQLite remains the later step if
concurrency/scale ever demands it.

``reconcile()`` is the restart story: a record left ``running`` from a previous run
is checked against its run log and PID; if the run has a terminal RESULT or the
process is gone, the record is corrected before callers count it as running.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horus.adapters.base import AgentSession
from horus.config import config_dir
from horus import runlog

# Terminal statuses never get liveness-reconciled.
TERMINAL = frozenset({"exited", "failed", "orphaned", "stale"})

_RESULT_RE = re.compile(r"^(?P<status>exited|failed) — session (?P<session_id>\S+)", re.MULTILINE)


def _now_iso() -> str:
    """Aware UTC timestamp (``…+00:00``). Rows must be comparable against agent
    transcripts and rollouts, whose own clocks mix local and UTC; legacy rows
    written before this were naive local time."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _aware_utc_iso(value: object) -> str:
    """Return an aware UTC ISO timestamp, tolerating legacy naive rows."""
    if not isinstance(value, str) or not value:
        return _now_iso()
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError:
        return _now_iso()
    if stamp.tzinfo is None:
        stamp = stamp.astimezone()
    return stamp.astimezone(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class _RunResult:
    status: str
    returncode: int | None = None


def _jsonl_result(session_id: str) -> _RunResult | None:
    """Terminal status from the structured run-event sidecar, when present."""
    for event in reversed(runlog.read_events(session_id)):
        if event.get("event") != "result" or event.get("session_id") != session_id:
            continue
        status = event.get("status")
        if status not in {"exited", "failed"}:
            continue
        rc = event.get("rc")
        return _RunResult(status=status, returncode=rc if isinstance(rc, int) else None)
    return None


def _legacy_log_result(session_id: str) -> _RunResult | None:
    """Terminal status from a legacy text run log's RESULT line."""
    text, _ = runlog.read_from(runlog.run_log_path(session_id), 0)
    for match in _RESULT_RE.finditer(text):
        if match.group("session_id") == session_id:
            return _RunResult(match.group("status"))
    for line in text.splitlines():
        if "RESULT" in line and session_id in line:
            if "failed" in line:
                return _RunResult("failed")
            if "exited" in line:
                return _RunResult("exited")
    return None


@dataclass
class SessionRecord:
    session_id: str
    agent: str
    project: str            # POSIX path string
    account: str | None = None
    environment: str = "host"
    pid: int | None = None
    status: str = "running"
    returncode: int | None = None
    updated_at: str = ""
    launch_target: str = "local"
    target_ref: str | None = None

    @classmethod
    def from_session(cls, session: AgentSession) -> "SessionRecord":
        if not session.session_id:
            raise ValueError("cannot register a session without a session_id")
        return cls(
            session_id=session.session_id,
            agent=session.agent,
            project=Path(session.project_dir).as_posix(),
            account=session.account,
            environment=session.environment,
            pid=session.pid,
            status=session.status,
            returncode=session.returncode,
        )


# How long a terminal (non-running) row stays in `horus sessions`'s default view
# before it's hidden behind ``--all`` — long enough to catch "what happened
# yesterday", short enough that months of dead workers don't bury a live session.
RECENCY_HORIZON_HOURS = 24.0


def is_recent(record: SessionRecord, *, now: datetime | None = None, horizon_hours: float = RECENCY_HORIZON_HOURS) -> bool:
    """Whether ``record`` was updated within ``horizon_hours`` of ``now``.

    Used to de-emphasize (not delete) long-stale rows in the default `horus
    sessions` view. An unparseable timestamp fails open (stays visible) rather
    than silently disappearing a row."""
    now = now or datetime.now(timezone.utc)
    try:
        stamp = datetime.fromisoformat(record.updated_at)
    except (ValueError, TypeError):
        return True
    if stamp.tzinfo is None:
        stamp = stamp.astimezone()
    return (now - stamp) <= timedelta(hours=horizon_hours)


def process_alive(pid: int | None) -> bool:
    """True if ``pid`` is a live process. Cross-platform, no third-party deps.

    Note: never uses ``os.kill`` on Windows — there ``os.kill`` calls
    ``TerminateProcess`` for any signal (including 0), which would *kill* the target.
    """
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        return _win_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def _win_alive(pid: int) -> bool:
    import ctypes

    SYNCHRONIZE = 0x00100000
    WAIT_TIMEOUT = 0x00000102
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return False  # no such process (or no access — treat as not-ours/not-alive)
    try:
        # A process handle is signaled once the process exits; still-running -> timeout.
        return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


class Registry:
    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def default(cls) -> "Registry":
        return cls(config_dir() / "registry.json")

    # --- persistence ----------------------------------------------------------

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        sessions = data.get("sessions")
        return sessions if isinstance(sessions, dict) else {}

    def _save(self, sessions: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"sessions": sessions}, indent=2) + "\n", encoding="utf-8")

    # --- reads ----------------------------------------------------------------

    def all(self) -> list[SessionRecord]:
        self.reconcile()
        return [SessionRecord(**row) for row in self._load().values()]

    def get(self, session_id: str) -> SessionRecord | None:
        self.reconcile()
        row = self._load().get(session_id)
        return SessionRecord(**row) if row else None

    # --- writes ---------------------------------------------------------------

    def upsert(self, record: SessionRecord, *, now: str | None = None) -> SessionRecord:
        record.updated_at = now or _now_iso()
        sessions = self._load()
        sessions[record.session_id] = asdict(record)
        self._save(sessions)
        return record

    def set_status(self, session_id: str, status: str, *, returncode: int | None = None) -> bool:
        sessions = self._load()
        row = sessions.get(session_id)
        if row is None:
            return False
        row["status"] = status
        if returncode is not None:
            row["returncode"] = returncode
        row["updated_at"] = _now_iso()
        self._save(sessions)
        return True

    def remove(self, session_id: str) -> bool:
        sessions = self._load()
        if session_id not in sessions:
            return False
        del sessions[session_id]
        self._save(sessions)
        return True

    def reconcile(self) -> list[SessionRecord]:
        """Correct stale ``running`` records against RESULT logs and PID liveness.

        Returns records whose status changed. Dead or pid-less running rows become
        ``stale`` so they are visible but never counted as running.
        """
        sessions = self._load()
        changed: list[SessionRecord] = []
        dirty = False
        for row in sessions.values():
            normalized = _aware_utc_iso(row.get("updated_at"))
            if row.get("updated_at") != normalized:
                row["updated_at"] = normalized
                dirty = True
            if row.get("status") in TERMINAL:
                continue
            session_id = str(row.get("session_id", ""))
            result = _jsonl_result(session_id) or _legacy_log_result(session_id)
            if result is not None:
                row["status"] = result.status
                if result.returncode is not None:
                    row["returncode"] = result.returncode
                row["updated_at"] = _now_iso()
                dirty = True
                changed.append(SessionRecord(**row))
                continue
            if not process_alive(row.get("pid")):
                row["status"] = "stale"
                row["updated_at"] = _now_iso()
                dirty = True
                changed.append(SessionRecord(**row))
        if dirty:
            self._save(sessions)
        return changed

    def prune(self) -> list[str]:
        """Drop terminal records (after reconcile). Returns the removed session ids."""
        sessions = self._load()
        dead = [sid for sid, row in sessions.items() if row.get("status") in TERMINAL]
        if dead:
            for sid in dead:
                del sessions[sid]
            self._save(sessions)
        return dead


def track(registry: Registry, run):
    """Wrap an :class:`AgentRun`: register the session once its id is known and
    record the final status when the stream ends. Yields the events through, so the
    caller still consumes them normally."""
    registered = False
    for event in run:
        if not registered and run.session.session_id:
            registry.upsert(SessionRecord.from_session(run.session))
            registered = True
        yield event
    if run.session.session_id:
        registry.upsert(SessionRecord.from_session(run.session))
