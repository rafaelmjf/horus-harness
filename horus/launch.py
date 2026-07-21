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

from horus import adapters, config, launcher, registry

# A launch has exactly one axis: WHAT CONTEXT IS LOADED (`fresh` / `resume` / a card).
# There is deliberately no second "session mode" axis describing how much process the
# model should perform — that was prose the model could reinterpret, it cost a turn at
# launch to deliver, and it could contradict the authored handoff it wrapped. What the
# session may actually DO is the permission posture (`config.LAUNCH_POSTURE_CHOICES`),
# which the native CLIs enforce themselves. Removed 2026-07-19; see the
# `review-session-control-calibration` verdict.


@dataclass
class LaunchResult:
    ok: bool
    agent: str
    project: Path
    account: str | None = None
    session_id: str | None = None
    pid: int | None = None
    target_ref: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class PreparedInteractive:
    """Validated attended-agent command shared by every local terminal surface."""

    agent: str
    project: Path
    account: str | None
    session_id: str
    argv: list[str]
    env: dict[str, str]


def prepare_interactive(
    *,
    agent: str = "claude",
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    effort: str | None = None,
    prompt: str = "",
    session_id: str | None = None,
    proxied: bool = False,
    remote_control: bool | None = None,
) -> tuple[PreparedInteractive | None, str | None]:
    """Validate and build an attended launch without choosing its terminal host.

    ``remote_control`` is the per-launch override: ``None`` (the usual case) reads
    the global default (``config.load_remote_control_default()``), so the sessions
    you *forgot* about are still covered; an explicit ``True``/``False`` wins over
    it. The request is honored only by an adapter that supports Remote Control
    (Claude today); others ignore it.
    """
    root = Path(project_dir).resolve()
    try:
        adapter = adapters.get_adapter(agent)
    except KeyError as exc:
        return None, str(exc)
    if not hasattr(adapter, "interactive_command"):
        return None, f"{agent!r} does not support interactive sessions yet."
    try:
        permission_posture = adapters.PermissionPosture(posture)
    except ValueError:
        return None, f"unknown permission posture: {posture!r}"

    want_rc = remote_control if remote_control is not None else config.load_remote_control_default()
    spec = adapters.SpawnSpec(
        prompt=prompt,
        project_dir=root,
        account=account,
        posture=permission_posture,
        model=model,
        effort=effort,
        proxied=proxied,
        remote_control=bool(want_rc) and getattr(adapter, "supports_remote_control", False),
    )
    # Never enter an attended session under a mapped alias whose login differs — EXCEPT
    # a proxied launch, whose auth is the proxy's subscription token, not the account's
    # own login (so the account's login is irrelevant; this is "works regardless of account").
    if account and not proxied and getattr(adapter, "config_dirs", {}).get(account) and hasattr(adapter, "verify_account"):
        check = adapter.verify_account(account)
        if not check.ok:
            return None, (
                f"account {account!r} login mismatch "
                f"(found {check.detected_email or 'no login'})."
            )

    sid = session_id or str(uuid.uuid4())
    return PreparedInteractive(
        agent=adapter.name,
        project=root,
        account=account,
        session_id=sid,
        argv=adapter.interactive_command(spec, session_id=sid),
        env=adapter.build_env(spec),
    ), None


def launch_interactive(
    *,
    agent: str = "claude",
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    effort: str | None = None,
    prompt: str = "",
    remote_control: bool | None = None,
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
    prepared, error = prepare_interactive(
        agent=agent,
        project_dir=root,
        account=account,
        posture=posture,
        model=model,
        effort=effort,
        prompt=prompt,
        remote_control=remote_control,
    )
    if prepared is None:
        return LaunchResult(ok=False, agent=agent, project=root, account=account, error=error)
    try:
        pid = launcher.open_terminal(prepared.argv, cwd=root, env=prepared.env)
    except OSError as exc:
        return LaunchResult(
            ok=False, agent=prepared.agent, project=root, account=account,
            error=f"failed to open a terminal: {exc}",
        )

    (reg or registry.Registry.default()).upsert(
        registry.SessionRecord(
            session_id=prepared.session_id, agent=prepared.agent, project=root.as_posix(),
            account=account, pid=pid, status="running",
        )
    )
    return LaunchResult(
        ok=True, agent=prepared.agent, project=root, account=account,
        session_id=prepared.session_id, pid=pid,
    )
