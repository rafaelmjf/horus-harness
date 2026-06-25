"""Session/process registry — what agent sessions exist and their live state.

The row shape is exactly :class:`horus.adapters.base.AgentSession`:
``(agent, account, project, environment, pid, session_id, status)``. Stored as
JSON at ``~/.horus/registry.json`` so it survives restarts. It is **machine-local**
by nature (it tracks PIDs), which is why it lives under ``~/.horus`` and is not
git-synced — consistent with the file-first ethos; SQLite remains the later step if
concurrency/scale ever demands it.

``reconcile()`` is the restart story: a record left ``running`` from a previous run
is checked against its PID; if the process is gone, the record is corrected to
``exited`` (or ``orphaned`` when the PID was never known).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from horus.adapters.base import AgentSession
from horus.config import config_dir

# Terminal statuses never get liveness-reconciled.
TERMINAL = frozenset({"exited", "failed", "orphaned"})


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
        return [SessionRecord(**row) for row in self._load().values()]

    def get(self, session_id: str) -> SessionRecord | None:
        row = self._load().get(session_id)
        return SessionRecord(**row) if row else None

    # --- writes ---------------------------------------------------------------

    def upsert(self, record: SessionRecord, *, now: str | None = None) -> SessionRecord:
        record.updated_at = now or datetime.now().isoformat(timespec="seconds")
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
        row["updated_at"] = datetime.now().isoformat(timespec="seconds")
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
        """Correct stale ``running`` records against real PID liveness. Returns the
        records whose status changed (e.g. a session left running by a crashed run)."""
        sessions = self._load()
        changed: list[SessionRecord] = []
        for row in sessions.values():
            if row.get("status") in TERMINAL:
                continue
            if not process_alive(row.get("pid")):
                row["status"] = "exited" if row.get("pid") else "orphaned"
                row["updated_at"] = datetime.now().isoformat(timespec="seconds")
                changed.append(SessionRecord(**row))
        if changed:
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
