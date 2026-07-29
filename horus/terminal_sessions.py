"""Terminal-native attended sessions: the caller-facing façade over session hosts.

This module chooses *where the local interactive CLI is displayed* and answers what
the chosen host can do. The host implementations live in :mod:`horus.hosts`
(`current`, `tmux`, …); nothing here knows a host's mechanics any more, and no
caller outside this module should compare a launch target to a literal — ask the
host's capabilities instead, because that is the only question with a stable
answer as hosts are added.

It deliberately does not add remote execution targets to :mod:`horus.backend`:
account validation, argv construction, and registry identity still come from the
shared launch layer.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from horus import hosts, launch, launcher, registry
from horus.hosts import runnerspec
from horus.hosts.tmux import _enable_mouse_mode, _kill_tmux_session, inside_tmux  # noqa: F401

if TYPE_CHECKING:
    from horus.run_executor import RunRequest

CURRENT = hosts.CURRENT
TMUX = hosts.TMUX
WINDOW = "window"


def host_choices() -> tuple[str, ...]:
    """Host ids a `--target` may name, built from the host registry so a new host
    is offered automatically. `current` and `tmux` keep working forever: scripted
    `horus open --target` behaviour is explicit and stable by rule, so ids are
    only ever added here, never renamed or removed."""
    return hosts.ids()


def display_choices() -> tuple[str, ...]:
    """`horus open --target`: a host id, or ``window`` — which is not a host but a
    way of displaying one (open the resolved host's viewer in a native window)."""
    return (WINDOW, *hosts.ids())


# Retained for callers that want the historical tuple; prefer display_choices().
TARGETS = (WINDOW, CURRENT, TMUX)

# A detached, unattached session must sit idle at least this long before it is
# even considered for reaping — insurance against racing a session that was just
# created (host activity and the registry pid handoff both need a moment to settle).
ORPHAN_MIN_IDLE_SECONDS = 600.0

# Kept as module-level aliases because `horus.tmux_runner` and the tests import
# them by these names, and a live session's spec is found through them.
_SESSION_RE = runnerspec.SESSION_RE
_runner_dir = runnerspec.runner_dir
_runner_spec_path = runnerspec.spec_path
_runner_ready_path = runnerspec.ready_path
_write_runner_spec = runnerspec.write_spec
_write_runner_payload = runnerspec.write_payload
_await_runner_handoff = runnerspec.await_handoff
_record = runnerspec.new_record


def tmux_available() -> bool:
    from horus.hosts import tmux

    return tmux.available()


def _inside_tmux() -> bool:
    return inside_tmux()


def attach_returns_immediately() -> bool:
    """Whether :func:`attach_session` hands control back right away.

    Inside a host Horus is itself running in, attaching switches the current client
    and returns at once; otherwise it blocks until the owner detaches. Callers use
    this only to describe what happened — the attach itself needs no branch.
    """
    return hosts.resolve().switches_in_place()


def default_target() -> str:
    """The id of the host this process will use. Prefers a persistent host whenever
    this runtime can provide one; see :func:`horus.hosts.resolve`."""
    return hosts.resolve().id


def resolve_window_launch(preference: str) -> bool:
    """Whether a TUI launch should open its own terminal window (True) or take
    over the current TTY (False), given the owner's ``window`` launch default.

    Platform-aware: ``new-window`` only pops a real window when a desktop session
    exists AND we are not driving the TUI over SSH. The mobile path (Termius SSH
    into ``horus tui``) has no local display the phone can see, so it falls back to
    ``takeover`` — the reliable attach/detach flow the Rules pin as the phone path.
    ``takeover`` (the default) always stays in this terminal.
    """
    if preference != "new-window":
        return False
    return launcher.has_display() and not os.environ.get("SSH_CONNECTION")


def is_attachable(record: registry.SessionRecord) -> bool:
    """Whether Horus has a persistent host it can safely reattach.

    Asked of the host, not of the string: a record written by a newer Horus naming
    a host this install lacks is honestly *not* attachable here, and must never be
    offered a reattach that cannot work.
    """
    host = hosts.for_record(record)
    return bool(host is not None and host.capabilities.attach and record.target_ref)


def access_label(record: registry.SessionRecord) -> str:
    return "attachable" if is_attachable(record) else "original terminal only"


def attach_outcome_message(session_id: str) -> str:
    """What a successful :func:`attach_session` did, in the owner's words.

    The two cases differ in kind, not wording: inside the host control came back at
    once with the session still live, so "Detached from …" would be a lie. Phrased
    to stay true whenever it is read — including after the owner switched back.
    """
    short = session_id[:8]
    if attach_returns_immediately():
        return f"Switched to {short}. Ctrl-b L toggles between it and Horus."
    return f"Detached from {short}."


def launch_outcome_message(result: launch.LaunchResult) -> str:
    """What a successful attended launch left behind.

    Keyed on the host that actually ran — ``target_ref`` is set only by a
    persistent host — never on the ambient environment alone: an owner inside tmux
    who forced ``HORUS_TERMINAL_TARGET=current`` did NOT get a switchable session,
    and telling them otherwise would send them chasing one that isn't there.
    """
    short = (result.session_id or "")[:8]
    if result.target_ref and attach_returns_immediately():
        return f"Session {short} started in tmux. Ctrl-b L toggles between it and Horus."
    return f"Session {short} returned to Horus."


def run_attached(**kwargs) -> launch.LaunchResult:
    """Run an attended agent in this TTY, returning after the agent exits."""
    return hosts.get(CURRENT).launch(**kwargs)


def launch_tmux(**kwargs) -> launch.LaunchResult:
    """Create a unique detached tmux session, then optionally attach this TTY."""
    return hosts.get(TMUX).launch(**kwargs)


def launch_on(target: str, **kwargs) -> launch.LaunchResult:
    """Launch on the host named ``target``.

    This is what a caller should use instead of branching on the host id: a new
    host becomes launchable from the TUI, the plain terminal app, and `horus open`
    the moment it is registered, with no caller-side change.
    """
    host = hosts.get(target)
    if host is None:
        return launch.LaunchResult(
            False, kwargs.get("agent", ""), Path(kwargs.get("project_dir", ".")),
            account=kwargs.get("account"), error=f"unknown session host {target!r}",
        )
    if (not_ready := host.ensure_ready()) is not None:
        return launch.LaunchResult(
            False, kwargs.get("agent", ""), Path(kwargs.get("project_dir", ".")),
            account=kwargs.get("account"), error=not_ready,
        )
    return host.launch(**kwargs)


def persistent_hosts() -> tuple[str, ...]:
    """Host ids that keep a session alive after the launcher returns — the hosts a
    `--detach` or a worker can legitimately name."""
    return tuple(host.id for host in hosts.all_hosts() if host.capabilities.persistent)


def default_persistent_host() -> str:
    """The persistent host a worker should use when none was named: the resolved
    host if it qualifies, else the first that does. Never silently tmux — a machine
    configured for another host would have its workers land somewhere else."""
    resolved = hosts.resolve()
    if resolved.capabilities.persistent:
        return resolved.id
    available = [
        host.id for host in hosts.all_hosts()
        if host.capabilities.persistent and host.available()
    ]
    return available[0] if available else TMUX


def hosts_persistently(target: str) -> bool:
    """Whether ``target`` keeps the session alive after the launcher returns —
    i.e. whether a launch on it "starts" something or merely "completes"."""
    host = hosts.get(target)
    return bool(host is not None and host.capabilities.persistent)


def launch_detached_run(
    request: "RunRequest", *, target: str | None = None, reg: registry.Registry | None = None,
) -> launch.LaunchResult:
    """Host a one-shot worker on a persistent host, returning after runner handoff.

    ``target`` names the host; it defaults to the resolved one rather than to tmux,
    because a machine configured for another host would otherwise have its workers
    silently land somewhere else.
    """
    host = hosts.get(target) if target else hosts.resolve()
    if host is None:
        return launch.LaunchResult(
            False, request.agent, request.project, account=request.account,
            error=f"unknown session host {target!r}",
        )
    if not host.capabilities.persistent:
        return launch.LaunchResult(
            False, request.agent, request.project, account=request.account,
            error=f"{host.id} cannot host a detached worker",
        )
    if (not_ready := host.ensure_ready()) is not None:
        return launch.LaunchResult(
            False, request.agent, request.project, account=request.account, error=not_ready,
        )
    return host.launch_worker(request, reg=reg)


def launch_window(
    *,
    agent: str,
    project_dir: Path | str,
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    effort: str | None = None,
    prompt: str = "",
    proxied: bool = False,
    remote_control: bool | None = None,
    reg: registry.Registry | None = None,
) -> launch.LaunchResult:
    """Open a session in its own native terminal window, backed by a persistent host
    when one can provide a viewer. Used by web-requested windows and by a
    ``new-window`` TUI launch."""
    host = hosts.resolve()
    if host.capabilities.viewer and (not_ready := host.ensure_ready()) is not None:
        # A host that owns a server it cannot start must fail with the reason here.
        # Without this, a herdr window launch dies on a bare ENOENT from the socket.
        return launch.LaunchResult(
            False, agent, Path(project_dir).resolve(), account=account, error=not_ready,
        )
    if not host.capabilities.viewer:
        # No host viewer to put in the window: fall back to a plain interactive spawn.
        # (This branch cannot carry the proxy env; a no-viewer desktop is the rare
        # case and the proxy toggle is off by default.)
        return launch.launch_interactive(
            agent=agent,
            project_dir=project_dir,
            account=account,
            posture=posture,
            model=model,
            effort=effort,
            prompt=prompt,
            remote_control=remote_control,
            reg=reg,
        )

    result = host.launch(
        agent=agent,
        project_dir=project_dir,
        account=account,
        posture=posture,
        model=model,
        effort=effort,
        prompt=prompt,
        attach=False,
        proxied=proxied,
        remote_control=remote_control,
        reg=reg,
    )
    if not result.ok or not result.session_id or not result.target_ref:
        return result
    argv = host.viewer_argv(result.target_ref)
    if argv is None:
        stop_session(result.session_id, reg=reg)
        return launch.LaunchResult(
            False, result.agent, result.project, account=account,
            session_id=result.session_id, target_ref=result.target_ref,
            error="host could not provide a viewer for the new session",
        )
    try:
        viewer_pid = launcher.open_terminal(
            argv,
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
            error=f"failed to open the session in a native terminal: {exc}",
        )
    result.pid = viewer_pid
    return result


def viewer_argv(record: registry.SessionRecord) -> list[str] | None:
    """The argv that renders ``record`` in a PTY or native window, or ``None``.

    The host may prepare itself first (focus the right workspace, say), so this is
    a call rather than a template a caller can assemble.
    """
    host = hosts.for_record(record)
    if host is None or not record.target_ref:
        return None
    return host.viewer_argv(record.target_ref)


def attach_session(session_id: str, *, reg: registry.Registry | None = None) -> str | None:
    """Put this terminal on a tracked session. Return an error string, or ``None``."""
    record, error = resolve_session(session_id, reg=reg)
    if record is None:
        return error
    host = hosts.for_record(record)
    if host is None or not host.capabilities.attach:
        return f"session {record.session_id[:8]} is not hosted by an attachable host"
    return host.attach(record)


def stop_session(session_id: str, *, reg: registry.Registry | None = None) -> str | None:
    """Stop a tracked session by id or unique prefix."""
    store = reg or registry.Registry.default()
    record, error = resolve_session(session_id, reg=store)
    if record is None:
        return error
    host = hosts.for_record(record)
    if host is None or not host.capabilities.persistent:
        return f"session {record.session_id[:8]} is not hosted by a persistent host"
    stopped = host.stop(record)
    if stopped is not None:
        return stopped
    store.update(record.session_id, termination_reason="stopped")
    store.set_status(record.session_id, "failed")
    return None


def _live_tmux_sessions() -> dict[str, tuple[bool, float]]:
    from horus.hosts import tmux

    return tmux.TmuxHost().live_refs()


def reap_orphans(
    *, reg: registry.Registry | None = None, min_idle_seconds: float = ORPHAN_MIN_IDLE_SECONDS,
) -> list[str]:
    """Kill host sessions that are provably abandoned; return the killed refs.

    Safety invariant — positive confirmation only: a session is reaped only when
    Horus's own registry positively confirms it is no longer live (a matching
    record exists, and either that record's own status is already terminal, or the
    pid Horus tracked for it is dead), AND it is not attached, AND it has been idle
    beyond ``min_idle_seconds`` by the host's own clock. A live ref with NO matching
    registry record is never touched, however idle or unattached it looks — an
    absent record is not evidence of anything (a stale, foreign, or rebuilt registry
    looks identical from here); guessing on absence is exactly how a live session
    gets killed.

    Only hosts that declare ``liveness`` participate. A host that cannot report
    "attached?" and "idle how long?" can never satisfy the last two conditions, so
    its sessions are not candidates at all — leaking an idle pane is cheap, killing
    a live agent is not.
    """
    store = reg or registry.Registry.default()
    by_target_ref = {record.target_ref: record for record in store.all() if record.target_ref}
    now = time.time()
    reaped: list[str] = []
    for host in hosts.all_hosts():
        if not host.capabilities.liveness:
            continue
        for name, (attached, activity) in host.live_refs().items():
            if attached:
                continue
            if now - activity < min_idle_seconds:
                continue
            record = by_target_ref.get(name)
            if record is None:
                continue  # no positive confirmation this is ours to reap — leave it alone
            if record.status == "running" and registry.process_alive(record.pid):
                continue
            host.stop(record)
            store.update(record.session_id, termination_reason="orphan-reaped")
            store.set_status(record.session_id, "failed")
            reaped.append(name)
    return reaped


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
