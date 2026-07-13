"""Terminal-native attended sessions: current TTY and persistent tmux hosts.

This module chooses *where the local interactive CLI is displayed*. It deliberately
does not add remote execution targets to :mod:`horus.backend`: account validation,
argv construction, and registry identity still come from the shared launch layer.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from horus import config, launch, launcher, registry

CURRENT = "current"
TMUX = "tmux"
WINDOW = "window"
TARGETS = (WINDOW, CURRENT, TMUX)

_SESSION_RE = re.compile(r"^[0-9a-f-]{36}$")


def tmux_available() -> bool:
    return os.name != "nt" and shutil.which("tmux") is not None


def default_target() -> str:
    """Prefer a persistent host whenever this runtime can provide one."""
    override = os.environ.get("HORUS_TERMINAL_TARGET", "").strip().lower()
    if override in {CURRENT, TMUX}:
        return override
    if os.environ.get("TMUX"):
        return CURRENT
    if tmux_available():
        return TMUX
    return CURRENT


def is_attachable(record: registry.SessionRecord) -> bool:
    """Whether Horus has a persistent host it can safely reattach."""
    return record.launch_target == TMUX and bool(record.target_ref)


def access_label(record: registry.SessionRecord) -> str:
    return "attachable" if is_attachable(record) else "original terminal only"


def run_attached(
    *,
    agent: str,
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    prompt: str = "",
    reg: registry.Registry | None = None,
) -> launch.LaunchResult:
    """Run an attended agent in this TTY, returning after the agent exits."""
    prepared, error = launch.prepare_interactive(
        agent=agent,
        project_dir=project_dir,
        account=account,
        posture=posture,
        model=model,
        prompt=prompt,
    )
    root = Path(project_dir).resolve()
    if prepared is None:
        return launch.LaunchResult(False, agent, root, account=account, error=error)

    try:
        proc = subprocess.Popen(  # noqa: S603 - argv is produced by a trusted adapter
            prepared.argv,
            cwd=str(prepared.project),
            env={**os.environ, **prepared.env},
        )
    except OSError as exc:
        return launch.LaunchResult(
            False, prepared.agent, prepared.project, account=account,
            error=f"failed to start in the current terminal: {exc}",
        )

    store = reg or registry.Registry.default()
    store.upsert(_record(prepared, pid=proc.pid, target=CURRENT))
    returncode = proc.wait()
    store.set_status(
        prepared.session_id,
        "exited" if returncode == 0 else "failed",
        returncode=returncode,
    )
    return launch.LaunchResult(
        True,
        prepared.agent,
        prepared.project,
        account=account,
        session_id=prepared.session_id,
        pid=proc.pid,
    )


def launch_tmux(
    *,
    agent: str,
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    prompt: str = "",
    attach: bool = True,
    cols: int | None = None,
    rows: int | None = None,
    reg: registry.Registry | None = None,
) -> launch.LaunchResult:
    """Create a unique detached tmux session, then optionally attach this TTY."""
    root = Path(project_dir).resolve()
    if not tmux_available():
        return launch.LaunchResult(
            False, agent, root, account=account,
            error="tmux is not installed or is unavailable on this platform",
        )
    if attach and os.environ.get("TMUX"):
        return launch.LaunchResult(
            False, agent, root, account=account,
            error="already inside tmux; use --target current to avoid a nested tmux client",
        )

    prepared, error = launch.prepare_interactive(
        agent=agent,
        project_dir=root,
        account=account,
        posture=posture,
        model=model,
        prompt=prompt,
    )
    if prepared is None:
        return launch.LaunchResult(False, agent, root, account=account, error=error)

    executable = shutil.which(prepared.argv[0])
    if executable is None:
        return launch.LaunchResult(
            False, prepared.agent, prepared.project, account=account,
            error=f"agent executable not found on PATH: {prepared.argv[0]}",
        )
    runner_argv = [executable, *prepared.argv[1:]]

    tmux_name = f"horus-{prepared.session_id[:12]}"
    spec_path = _write_runner_spec(prepared, argv=runner_argv)
    store = reg or registry.Registry.default()
    # Keep reconciliation honest during the short handoff before the runner records
    # its own child PID. A failed tmux spawn is immediately corrected below.
    store.upsert(_record(prepared, pid=os.getpid(), target=TMUX, target_ref=tmux_name))
    runner = shlex.join([sys.executable, "-m", "horus.tmux_runner", prepared.session_id])
    size_args = []
    if cols is not None:
        size_args.extend(["-x", str(cols)])
    if rows is not None:
        size_args.extend(["-y", str(rows)])
    tmux_argv = [
        "tmux", "new-session", "-d", *size_args,
        "-s", tmux_name, "-c", str(prepared.project), runner,
    ]
    created = subprocess.run(  # noqa: S603,S607 - fixed tmux argv; runner is shell-quoted
        tmux_argv,
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        spec_path.unlink(missing_ok=True)
        store.set_status(prepared.session_id, "failed", returncode=created.returncode)
        detail = (created.stderr or created.stdout).strip() or f"tmux exited {created.returncode}"
        return launch.LaunchResult(
            False, prepared.agent, prepared.project, account=account,
            session_id=prepared.session_id,
            target_ref=tmux_name,
            error=f"failed to create tmux session: {detail}",
        )

    if attach:
        attached = attach_session(prepared.session_id, reg=store)
        if attached:
            return launch.LaunchResult(
                False, prepared.agent, prepared.project, account=account,
                session_id=prepared.session_id,
                target_ref=tmux_name,
                error=attached,
            )
    return launch.LaunchResult(
        True,
        prepared.agent,
        prepared.project,
        account=account,
        session_id=prepared.session_id,
        target_ref=tmux_name,
    )


def launch_window(
    *,
    agent: str,
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    prompt: str = "",
    reg: registry.Registry | None = None,
) -> launch.LaunchResult:
    """Open a web-requested native window, backed by tmux when supported."""
    if default_target() != TMUX:
        return launch.launch_interactive(
            agent=agent,
            project_dir=project_dir,
            account=account,
            posture=posture,
            model=model,
            prompt=prompt,
            reg=reg,
        )

    result = launch_tmux(
        agent=agent,
        project_dir=project_dir,
        account=account,
        posture=posture,
        model=model,
        prompt=prompt,
        attach=False,
        reg=reg,
    )
    if not result.ok or not result.session_id or not result.target_ref:
        return result
    try:
        viewer_pid = launcher.open_terminal(
            ["tmux", "attach-session", "-t", result.target_ref],
            cwd=result.project,
            env={"TERM": os.environ.get("TERM") or "xterm-256color"},
        )
    except OSError as exc:
        stop_session(result.session_id, reg=reg)
        return launch.LaunchResult(
            False,
            result.agent,
            result.project,
            account=account,
            session_id=result.session_id,
            target_ref=result.target_ref,
            error=f"failed to open tmux in a native terminal: {exc}",
        )
    result.pid = viewer_pid
    return result


def attach_session(session_id: str, *, reg: registry.Registry | None = None) -> str | None:
    """Attach to a tracked tmux session. Return an error string, or ``None``."""
    if not tmux_available():
        return "tmux is not installed or is unavailable on this platform"
    if os.environ.get("TMUX"):
        return "already inside tmux; detach first, then attach the Horus session"
    record, error = resolve_session(session_id, reg=reg)
    if record is None:
        return error
    if not is_attachable(record):
        return f"session {record.session_id[:8]} is not hosted by tmux"
    if record.status != "running":
        return f"session {record.session_id[:8]} is {record.status}, not running"
    attached = subprocess.run(  # noqa: S603,S607 - tmux name is Horus-generated
        ["tmux", "attach-session", "-t", record.target_ref],
        check=False,
    )
    if attached.returncode != 0:
        return f"tmux attach failed with exit code {attached.returncode}"
    return None


def stop_session(session_id: str, *, reg: registry.Registry | None = None) -> str | None:
    """Stop a tracked tmux session by id or unique prefix."""
    store = reg or registry.Registry.default()
    record, error = resolve_session(session_id, reg=store)
    if record is None:
        return error
    if not is_attachable(record):
        return f"session {record.session_id[:8]} is not hosted by tmux"
    subprocess.run(  # noqa: S603,S607 - tmux name is Horus-generated
        ["tmux", "kill-session", "-t", record.target_ref],
        capture_output=True,
        check=False,
    )
    store.set_status(record.session_id, "exited")
    _runner_spec_path(record.session_id).unlink(missing_ok=True)
    return None


def resolve_session(
    session_id: str, *, reg: registry.Registry | None = None,
) -> tuple[registry.SessionRecord | None, str | None]:
    store = reg or registry.Registry.default()
    matches = [record for record in store.all() if record.session_id.startswith(session_id)]
    if not matches:
        return None, f"no session matching {session_id!r}"
    if len(matches) > 1:
        return None, f"session prefix {session_id!r} is ambiguous"
    return matches[0], None


def _record(
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


def _runner_dir() -> Path:
    return config.config_dir() / "tmux"


def _runner_spec_path(session_id: str) -> Path:
    if not _SESSION_RE.fullmatch(session_id):
        raise ValueError("invalid Horus session id")
    return _runner_dir() / f"{session_id}.json"


def _write_runner_spec(prepared: launch.PreparedInteractive, *, argv: list[str] | None = None) -> Path:
    directory = _runner_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _runner_spec_path(prepared.session_id)
    payload = {
        "session_id": prepared.session_id,
        "agent": prepared.agent,
        "account": prepared.account,
        "project": prepared.project.as_posix(),
        "argv": argv or prepared.argv,
        # A long-lived tmux server may hold a stale PATH. Carry only this benign
        # process-search value plus adapter-owned account isolation, never the full
        # parent environment (which may contain credentials).
        "env": {"PATH": os.environ.get("PATH", ""), **prepared.env},
    }
    encoded = json.dumps(payload).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
    return path
