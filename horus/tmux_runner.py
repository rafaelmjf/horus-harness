"""Private child entry point for a Horus-managed tmux pane."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from horus import registry
from horus.terminal_sessions import _runner_spec_path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m horus.tmux_runner SESSION_ID", file=sys.stderr)
        return 2
    try:
        path = _runner_spec_path(args[0])
        payload = json.loads(path.read_text(encoding="utf-8"))
        session_id, agent, project, command, extra_env, account = _validated(payload, expected_id=args[0])
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"horus tmux runner: {exc}", file=sys.stderr)
        return 2

    store = registry.Registry.default()
    try:
        proc = subprocess.Popen(  # noqa: S603 - command came from Horus's 0600 spec
            command,
            cwd=str(project),
            env={**os.environ, **extra_env},
        )
    except OSError as exc:
        store.set_status(session_id, "failed")
        print(f"horus tmux runner: failed to start {agent}: {exc}", file=sys.stderr)
        path.unlink(missing_ok=True)
        return 127

    current = store.get(session_id)
    if current is None:
        current = registry.SessionRecord(
            session_id=session_id,
            agent=agent,
            project=project.as_posix(),
            account=account,
            launch_target="tmux",
        )
    current.pid = proc.pid
    current.status = "running"
    store.upsert(current)
    returncode = proc.wait()
    store.set_status(
        session_id,
        "exited" if returncode == 0 else "failed",
        returncode=returncode,
    )
    path.unlink(missing_ok=True)
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
