"""The runner spec: how Horus tells a pane what to become, host-agnostically.

Any host that can run *one command in a persistent pane* inherits Horus's whole
delivery story from here — the 0600 spec file, the durable PID handoff, the
registry status transitions, and the `horus run` worker path. That is why this
module knows nothing about tmux (or herdr): it is the seam that makes a second
host cheap.

The on-disk directory is still ``~/.horus/tmux`` even though the contents are
host-neutral. Renaming it would orphan the specs of sessions that are running
right now, which is a worse trade than a stale directory name.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from horus import config, launch, registry

SESSION_RE = re.compile(r"^[0-9a-f-]{36}$")


def runner_dir() -> Path:
    return config.config_dir() / "tmux"


def spec_path(session_id: str) -> Path:
    if not SESSION_RE.fullmatch(session_id):
        raise ValueError("invalid Horus session id")
    return runner_dir() / f"{session_id}.json"


def ready_path(session_id: str) -> Path:
    return runner_dir() / f"{session_id}.ready"


def write_spec(prepared: launch.PreparedInteractive, *, argv: list[str] | None = None) -> Path:
    payload = {
        "kind": "interactive",
        "session_id": prepared.session_id,
        "agent": prepared.agent,
        "account": prepared.account,
        "project": prepared.project.as_posix(),
        "argv": argv or prepared.argv,
        # A long-lived host server may hold a stale PATH. Carry only this benign
        # process-search value plus adapter-owned account isolation, never the full
        # parent environment (which may contain credentials).
        "env": {"PATH": os.environ.get("PATH", ""), **prepared.env},
    }
    return write_payload(payload, prepared.session_id)


def write_payload(payload: dict, session_id: str) -> Path:
    directory = runner_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = spec_path(session_id)
    ready_path(session_id).unlink(missing_ok=True)
    encoded = json.dumps(payload).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
    return path


def await_handoff(session_id: str, store: registry.Registry, *, timeout: float = 5.0) -> bool:
    """Wait only for the runner's durable PID handoff, never for its agent."""
    ready = ready_path(session_id)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if ready.exists():
            current = store.get(session_id)
            return bool(current and current.pid and current.pid != os.getpid() and current.status == "running")
        current = store.get(session_id)
        if current is not None and current.status in registry.TERMINAL:
            return False
        time.sleep(0.02)
    return False


def new_record(
    prepared: launch.PreparedInteractive,
    *,
    pid: int | None,
    target: str,
    target_ref: str | None = None,
) -> registry.SessionRecord:
    return registry.SessionRecord(
        session_id=prepared.session_id,
        agent=prepared.agent,
        project=prepared.project.as_posix(),
        account=prepared.account,
        pid=pid,
        status="running",
        launch_target=target,
        target_ref=target_ref,
    )
