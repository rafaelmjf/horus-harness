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
import time
from pathlib import Path
from typing import TYPE_CHECKING

from horus import config, launch, launcher, registry

if TYPE_CHECKING:
    from horus.run_executor import RunRequest

CURRENT = "current"
TMUX = "tmux"
WINDOW = "window"
TARGETS = (WINDOW, CURRENT, TMUX)

_SESSION_RE = re.compile(r"^[0-9a-f-]{36}$")

# A detached, unattached tmux session must sit idle at least this long before it is
# even considered for reaping — insurance against racing a session that was just
# created (tmux activity and the registry pid handoff both need a moment to settle).
ORPHAN_MIN_IDLE_SECONDS = 600.0


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
    effort: str | None = None,
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
        effort=effort,
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
    effort: str | None = None,
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
        effort=effort,
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

    # Wheel input reaches an attended agent as raw terminal escape sequences
    # (e.g. recalled shell/agent history) unless tmux's mouse handling is on for
    # this pane. Scope it to just the new session (-t <name>, never -g) so a
    # Horus launch never touches the tmux server/user default. A session that
    # fails to configure is torn down rather than left half-configured.
    mouse_error = _enable_mouse_mode(tmux_name)
    if mouse_error:
        _kill_tmux_session(tmux_name)
        spec_path.unlink(missing_ok=True)
        store.set_status(prepared.session_id, "failed")
        return launch.LaunchResult(
            False, prepared.agent, prepared.project, account=account,
            session_id=prepared.session_id,
            target_ref=tmux_name,
            error=f"failed to enable tmux mouse mode for the new session: {mouse_error}",
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


def launch_detached_run(request: "RunRequest", *, reg: registry.Registry | None = None) -> launch.LaunchResult:
    """Host a one-shot worker in managed tmux and return after runner handoff.

    The pane executes the exact same adapter executor as a foreground ``run``;
    this function only provides lifetime isolation and the attachable tmux target.
    """
    if not tmux_available():
        return launch.LaunchResult(False, request.agent, request.project, account=request.account,
                                   error="tmux is not installed or is unavailable on this platform")
    tmux_name = f"horus-{request.session_id[:12]}"
    store = reg or registry.Registry.default()
    store.upsert(registry.SessionRecord(
        session_id=request.session_id, agent=request.agent, project=request.project.as_posix(),
        account=request.account, pid=os.getpid(), status="running", launch_target=TMUX,
        target_ref=tmux_name, agent_session_id=request.resume,
        dispatch_base_sha=request.dispatch_base_sha, delivery_expected=request.delivery_expected,
    ))
    spec_path = _write_runner_payload({"kind": "run", "run": request.payload()}, request.session_id)
    runner = shlex.join([sys.executable, "-m", "horus.tmux_runner", request.session_id])
    created = subprocess.run(  # noqa: S603,S607 - fixed tmux argv; runner is shell-quoted
        ["tmux", "new-session", "-d", "-s", tmux_name, "-c", str(request.project), runner],
        capture_output=True, text=True, check=False,
    )
    if created.returncode != 0:
        spec_path.unlink(missing_ok=True)
        _runner_ready_path(request.session_id).unlink(missing_ok=True)
        store.update(request.session_id, termination_reason="launch-error")
        store.set_status(request.session_id, "failed", returncode=created.returncode)
        detail = (created.stderr or created.stdout).strip() or f"tmux exited {created.returncode}"
        return launch.LaunchResult(False, request.agent, request.project, account=request.account,
                                   session_id=request.session_id, target_ref=tmux_name,
                                   error=f"failed to create tmux session: {detail}")
    mouse_error = _enable_mouse_mode(tmux_name)
    if mouse_error:
        return _failed_detached_launch(
            request, store, tmux_name, spec_path,
            error=f"failed to enable tmux mouse mode for the new session: {mouse_error}",
        )
    if not _await_runner_handoff(request.session_id, store):
        current = store.get(request.session_id)
        detail = "runner did not report its PID handoff"
        if current and current.status != "running":
            detail = f"runner ended during launch ({current.status})"
        return _failed_detached_launch(request, store, tmux_name, spec_path, error=detail)
    current = store.get(request.session_id)
    return launch.LaunchResult(True, request.agent, request.project, account=request.account,
                               session_id=request.session_id, pid=current.pid if current else None,
                               target_ref=tmux_name)


def _failed_detached_launch(
    request: "RunRequest", store: registry.Registry, tmux_name: str, spec_path: Path, *, error: str,
) -> launch.LaunchResult:
    """Undo a known newly-created detached host after its handoff fails."""
    _kill_tmux_session(tmux_name)
    spec_path.unlink(missing_ok=True)
    _runner_ready_path(request.session_id).unlink(missing_ok=True)
    store.update(request.session_id, termination_reason="launch-error")
    store.set_status(request.session_id, "failed")
    return launch.LaunchResult(False, request.agent, request.project, account=request.account,
                               session_id=request.session_id, target_ref=tmux_name, error=error)


def launch_window(
    *,
    agent: str,
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    effort: str | None = None,
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
            effort=effort,
            prompt=prompt,
            reg=reg,
        )

    result = launch_tmux(
        agent=agent,
        project_dir=project_dir,
        account=account,
        posture=posture,
        model=model,
        effort=effort,
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
    store.update(record.session_id, termination_reason="stopped")
    store.set_status(record.session_id, "failed")
    _runner_spec_path(record.session_id).unlink(missing_ok=True)
    return None


def _live_tmux_sessions() -> dict[str, tuple[bool, float]]:
    """Horus-named tmux sessions the tmux server currently holds, keyed by name to
    ``(attached, last_activity_epoch)``. Empty when tmux is unavailable or has no
    server running (never an error — an absent server just means nothing to reap)."""
    if not tmux_available():
        return {}
    listed = subprocess.run(  # noqa: S603,S607 - fixed tmux argv, no user input
        ["tmux", "list-sessions", "-F", "#{session_name}\t#{session_attached}\t#{session_activity}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        return {}
    sessions: dict[str, tuple[bool, float]] = {}
    for line in listed.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].startswith("horus-"):
            continue
        name, attached, activity = parts
        try:
            sessions[name] = (attached != "0", float(activity))
        except ValueError:
            continue
    return sessions


def reap_orphans(
    *, reg: registry.Registry | None = None, min_idle_seconds: float = ORPHAN_MIN_IDLE_SECONDS,
) -> list[str]:
    """Kill Horus tmux sessions that are provably abandoned; return the killed names.

    Safety invariant — positive confirmation only: a session is reaped only when
    Horus's own registry positively confirms it is no longer live (a matching
    record exists, and either that record's own status is already terminal, or the
    pid Horus tracked for it is dead), AND it is not attached, AND it has been idle
    beyond ``min_idle_seconds`` by tmux's own clock. A tmux session with NO
    matching registry record is never touched, however idle or unattached it
    looks — an absent record is not evidence of anything (a stale, foreign, or
    rebuilt registry looks identical from here); guessing on absence is exactly
    how a live session gets killed.
    """
    live = _live_tmux_sessions()
    if not live:
        return []
    store = reg or registry.Registry.default()
    by_target_ref = {record.target_ref: record for record in store.all() if record.target_ref}
    now = time.time()
    reaped: list[str] = []
    for name, (attached, activity) in live.items():
        if attached:
            continue
        if now - activity < min_idle_seconds:
            continue
        record = by_target_ref.get(name)
        if record is None:
            continue  # no positive confirmation this is ours to reap — leave it alone
        if record.status == "running" and registry.process_alive(record.pid):
            continue
        _kill_tmux_session(name)
        store.update(record.session_id, termination_reason="orphan-reaped")
        store.set_status(record.session_id, "failed")
        _runner_spec_path(record.session_id).unlink(missing_ok=True)
        reaped.append(name)
    return reaped


def _enable_mouse_mode(tmux_name: str) -> str | None:
    """Turn on mouse handling for exactly one session (never ``-g``/global).
    Returns an error string on failure, or ``None`` on success."""
    configured = subprocess.run(  # noqa: S603,S607 - tmux name is Horus-generated
        ["tmux", "set-option", "-t", tmux_name, "mouse", "on"],
        capture_output=True,
        text=True,
        check=False,
    )
    if configured.returncode != 0:
        detail = (configured.stderr or configured.stdout).strip() or f"tmux exited {configured.returncode}"
        return detail
    return None


def _kill_tmux_session(name: str) -> None:
    subprocess.run(  # noqa: S603,S607 - tmux name came from Horus's own list-sessions output
        ["tmux", "kill-session", "-t", name],
        capture_output=True,
        check=False,
    )


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


def _runner_ready_path(session_id: str) -> Path:
    return _runner_dir() / f"{session_id}.ready"


def _write_runner_spec(prepared: launch.PreparedInteractive, *, argv: list[str] | None = None) -> Path:
    payload = {
        "kind": "interactive",
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
    return _write_runner_payload(payload, prepared.session_id)


def _write_runner_payload(payload: dict, session_id: str) -> Path:
    directory = _runner_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _runner_spec_path(session_id)
    _runner_ready_path(session_id).unlink(missing_ok=True)
    encoded = json.dumps(payload).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
    return path


def _await_runner_handoff(session_id: str, store: registry.Registry, *, timeout: float = 5.0) -> bool:
    """Wait only for the runner's durable PID handoff, never for its agent."""
    ready = _runner_ready_path(session_id)
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
