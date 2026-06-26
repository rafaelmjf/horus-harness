"""Spawn an attended agent session and track it — shared by the CLI and the dashboard.

This is the orchestration that turns "open a session under account X in project Y,
optionally seeded with a prompt" into a tracked, running terminal: pick the adapter,
run the per-account identity guard, pre-assign a session id, build the interactive
argv (with an optional initial prompt for the TUI), launch it in its own terminal,
and register it as ``running``.

``horus open`` (CLI) and the dashboard's Control-tab launch buttons both call
:func:`launch_interactive`, so there is exactly one launch path and one identity
guard regardless of whether the trigger was a terminal command or a click.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from horus import adapters, launcher, registry


@dataclass
class LaunchResult:
    ok: bool
    agent: str
    project: Path
    account: str | None = None
    session_id: str | None = None
    pid: int | None = None
    error: str | None = None


def launch_interactive(
    *,
    agent: str = "claude",
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    prompt: str = "",
    reg: registry.Registry | None = None,
) -> LaunchResult:
    """Open an attended session in its own terminal and register it as running.

    ``prompt`` is injected as the interactive session's initial prompt (e.g. a
    project's continuity/resume prompt); empty means a fresh, unseeded session.
    Returns a :class:`LaunchResult` rather than raising for the expected failure
    modes (unknown agent, no interactive support, account-login mismatch, spawn
    error), so both the CLI and the web handler can report them uniformly.
    """
    root = Path(project_dir).resolve()
    try:
        adapter = adapters.get_adapter(agent)
    except KeyError as exc:
        return LaunchResult(ok=False, agent=agent, project=root, account=account, error=str(exc))

    if not hasattr(adapter, "interactive_command"):
        return LaunchResult(
            ok=False, agent=agent, project=root, account=account,
            error=f"{agent!r} does not support interactive sessions yet.",
        )

    spec = adapters.SpawnSpec(
        prompt=prompt,
        project_dir=root,
        account=account,
        posture=adapters.PermissionPosture(posture),
        model=model,
    )

    # Same identity guard as a headless spawn: refuse if a mapped account's login
    # doesn't match the requested account (never run under the wrong login).
    if account and getattr(adapter, "config_dirs", {}).get(account) and hasattr(adapter, "verify_account"):
        check = adapter.verify_account(account)
        if not check.ok:
            return LaunchResult(
                ok=False, agent=agent, project=root, account=account,
                error=f"account {account!r} login mismatch (found {check.detected_email or 'no login'}).",
            )

    session_id = str(uuid.uuid4())
    argv = adapter.interactive_command(spec, session_id=session_id)
    try:
        pid = launcher.open_terminal(argv, cwd=root, env=adapter.build_env(spec))
    except OSError as exc:
        return LaunchResult(
            ok=False, agent=agent, project=root, account=account,
            error=f"failed to open a terminal: {exc}",
        )

    (reg or registry.Registry.default()).upsert(
        registry.SessionRecord(
            session_id=session_id, agent=adapter.name, project=root.as_posix(),
            account=account, pid=pid, status="running",
        )
    )
    return LaunchResult(
        ok=True, agent=adapter.name, project=root, account=account,
        session_id=session_id, pid=pid,
    )
