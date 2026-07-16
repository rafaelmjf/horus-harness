"""Private child entry point for a Horus-managed tmux pane."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from horus import registry, run_executor
from horus.terminal_sessions import _runner_ready_path, _runner_spec_path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m horus.tmux_runner SESSION_ID", file=sys.stderr)
        return 2
    try:
        path = _runner_spec_path(args[0])
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid runner spec")
        kind = payload.get("kind", "interactive")
        if kind == "run":
            request = run_executor.RunRequest.from_payload(payload.get("run"))
            if request.session_id != args[0]:
                raise ValueError("runner run id does not match its filename")
            return _run_worker(request, path)
        session_id, agent, project, command, extra_env, account = _validated(payload, expected_id=args[0])
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"horus tmux runner: {exc}", file=sys.stderr)
        return 2
    return _run_interactive(session_id, agent, project, command, extra_env, account, path)


def _handoff(session_id: str, *, path: Path) -> registry.Registry:
    """Record the durable pane-runner PID before starting any agent process."""
    store = registry.Registry.default()
    current = store.get(session_id)
    if current is None:
        raise ValueError("runner has no preallocated registry row")
    current.pid = os.getpid()
    current.status = "running"
    store.upsert(current)
    ready = _runner_ready_path(session_id)
    descriptor = os.open(ready, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(f"{os.getpid()}\n")
    return store


def _run_worker(request: run_executor.RunRequest, path: Path) -> int:
    try:
        _handoff(request.session_id, path=path)
    except (OSError, ValueError) as exc:
        print(f"horus tmux runner: {exc}", file=sys.stderr)
        return 2
    try:
        # Import lazily to avoid a CLI/terminal runner import cycle.  The same
        # watcher behavior is retained if the caller explicitly requested it.
        from horus.cli import _spawn_watcher

        return run_executor.execute(request, watcher=_spawn_watcher)
    finally:
        path.unlink(missing_ok=True)
        _runner_ready_path(request.session_id).unlink(missing_ok=True)


def _run_interactive(
    session_id: str, agent: str, project: Path, command: list[str], extra_env: dict[str, str],
    account: str | None, path: Path,
) -> int:
    try:
        store = _handoff(session_id, path=path)
    except (OSError, ValueError) as exc:
        print(f"horus tmux runner: {exc}", file=sys.stderr)
        return 2
    try:
        proc = subprocess.Popen(  # noqa: S603 - command came from Horus's 0600 spec
            command, cwd=str(project), env={**os.environ, **extra_env},
        )
    except OSError as exc:
        store.update(session_id, termination_reason="launch-error")
        store.set_status(session_id, "failed")
        print(f"horus tmux runner: failed to start {agent}: {exc}", file=sys.stderr)
        path.unlink(missing_ok=True)
        return 127

    current = store.get(session_id)
    if current is None:
        current = registry.SessionRecord(
            session_id=session_id, agent=agent, project=project.as_posix(), account=account,
            launch_target="tmux",
        )
    current.pid = proc.pid
    current.status = "running"
    store.upsert(current)
    returncode = proc.wait()
    store.set_status(session_id, "exited" if returncode == 0 else "failed", returncode=returncode)
    path.unlink(missing_ok=True)
    _runner_ready_path(session_id).unlink(missing_ok=True)
    return returncode


def _validated(
    payload: object, *, expected_id: str,
) -> tuple[str, str, Path, list[str], dict[str, str], str | None]:
    if not isinstance(payload, dict):
        raise ValueError("invalid runner spec")
    session_id = payload.get("session_id")
    agent = payload.get("agent")
    project_raw = payload.get("project")
    command = payload.get("argv")
    extra_env = payload.get("env")
    account = payload.get("account")
    if not isinstance(session_id, str) or not isinstance(agent, str):
        raise ValueError("runner spec is missing session identity")
    if session_id != expected_id:
        raise ValueError("runner spec session id does not match its filename")
    if not isinstance(project_raw, str) or not Path(project_raw).is_dir():
        raise ValueError("runner project directory is missing")
    if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
        raise ValueError("runner command is invalid")
    if not isinstance(extra_env, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in extra_env.items()
    ):
        raise ValueError("runner environment is invalid")
    if account is not None and not isinstance(account, str):
        raise ValueError("runner account is invalid")
    return session_id, agent, Path(project_raw), command, extra_env, account


if __name__ == "__main__":
    raise SystemExit(main())
