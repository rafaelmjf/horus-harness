"""What a session host is, and what it can be asked to do.

A *session host* is the thing that owns an interactive agent process and decides
where it is displayed: this TTY, a Horus-managed tmux session, or (next) a herdr
pane. Callers must never ask "is this tmux?" — they ask the host what it can do,
because that is the only question with a stable answer across hosts.

Every capability here exists because some caller branches on it today. Adding a
flag with no consumer is how this file rots, so don't.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from horus import launch, registry

if TYPE_CHECKING:
    from horus.run_executor import RunRequest


@dataclass(frozen=True)
class Capabilities:
    """Static facts about a host. Dynamic ones are methods on the host itself."""

    persistent: bool
    """The agent survives its viewer going away. False means the session lives and
    dies with the terminal that started it — the `current` host."""

    attach: bool
    """A terminal can be bound to an already-running session. Drives the Sessions
    view's attach action and the `attachable` / `original terminal only` label."""

    viewer: bool
    """The host can hand back an argv that renders an existing session inside a PTY
    or a native window — what the browser terminal and `launch_window` need."""

    liveness: bool
    """The host can report, for each of its live refs, whether a client is attached
    and how long it has been idle.

    This one is load-bearing for safety. Reaping requires four conditions, and two
    of them (not attached, idle past a grace window) can ONLY come from the host.
    A host that cannot answer them declares ``liveness=False`` and its sessions are
    never reaped — leaking an idle pane is cheap, killing a live agent is not. This
    is the positive-confirmation rule made structural instead of remembered.
    """

    reports_exit_code: bool
    """The host itself yields the agent's returncode. False means the outcome is
    known only from what the runner recorded in the registry — true of any host
    that types a command into a shell rather than exec'ing an argv."""

    state: bool
    """The host reports per-session agent state (working / idle / blocked)."""


@runtime_checkable
class SessionHost(Protocol):
    """The nine things every caller of a host needs. Implementations live beside
    this file; nothing outside :mod:`horus.hosts` should import one directly."""

    id: str
    capabilities: Capabilities

    switch_hint: str
    """How the owner gets back to Horus from one of this host's sessions.

    User-facing text, and it belongs to the host because the keys differ: tmux binds
    last-session to ``Ctrl-b L`` out of the box, herdr leaves `previous_workspace`
    unbound and offers a space picker instead. A single hardcoded hint was shipped in
    0.0.78 and was simply wrong on herdr.
    """

    def available(self) -> bool:
        """Whether this host can be used on this machine at all."""

    def ensure_ready(self) -> str | None:
        """Make the host usable, returning an error string or ``None``.

        A no-op for tmux (``new-session`` starts its own server) and for the
        current TTY. It exists because a host may own a server that does NOT
        autostart — herdr's does not — and discovering that at launch time
        rather than in the interface is how a launch fails confusingly.
        """

    def switches_in_place(self) -> bool:
        """Whether :meth:`attach` moves the current client and returns immediately,
        rather than blocking until the owner detaches. True when Horus is running
        *inside* this host, so attaching is a switch, not a nested client.

        Dynamic, hence a method: it depends on the environment Horus was started
        in, not on which host was chosen.
        """

    def launch(
        self,
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
        proxied: bool = False,
        remote_control: bool | None = None,
        session_id: str | None = None,
        resume_thread_id: str | None = None,
        reg: registry.Registry | None = None,
    ) -> launch.LaunchResult:
        """Create an attended session, and attend it when ``attach`` is set."""

    def launch_worker(
        self, request: "RunRequest", *, reg: registry.Registry | None = None,
    ) -> launch.LaunchResult:
        """Host a one-shot `horus run` worker and return after the runner handoff."""

    def attach(self, record: registry.SessionRecord) -> str | None:
        """Put this terminal on a live session. Error string, or ``None``."""

    def stop(self, record: registry.SessionRecord) -> str | None:
        """Kill a live session. Error string, or ``None``."""

    def viewer_argv(self, target_ref: str) -> list[str] | None:
        """An argv that renders ``target_ref`` in a PTY or native window.

        Takes the ref rather than a registry record on purpose: a viewer is a
        property of the host's own naming, so building one must not depend on a
        registry lookup succeeding. The host may do side-effecting preparation
        first (herdr must focus the right workspace before attaching), which is
        why this is a method and not a format string. ``None`` when the host has
        no viewer.
        """

    def live_refs(self) -> dict[str, tuple[bool, float]]:
        """Live refs owned by this host → ``(attached, last_activity_epoch)``.

        Only meaningful when ``capabilities.liveness`` is set; a host without it
        returns an empty mapping and is therefore never reaped.
        """
