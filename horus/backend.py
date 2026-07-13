"""The frozen LaunchBackend seam — one interface for launching a session, wherever it runs.

**This contract is frozen (2026-07-10).** It is the chokepoint every session launch
flows through, so that "where an agent session runs" becomes a backend choice rather
than a hard-coded local spawn. The interface is deliberately *minimal* — exactly four
operations, fixed by ``research/omnigent-fit-2026-07-10.md``:

    launch(brief) -> handle   # start a session, get an opaque handle
    status(handle)            # its lifecycle state
    stream(handle)            # observe its output (where the backend can)
    stop(handle)              # end it

Design rules baked into this seam:

- **Omnigent stays optional.** This module imports nothing from Omnigent. The seam
  merely *permits* an ``OmnigentBackend`` (for Linux native + named managed-container
  providers) to be added later as a separate, optional module; Horus never depends on
  it. Omnigent-only capabilities (e.g. session *fork*) are deliberately kept OUT of this
  minimal contract.
- **No silent cross-target fallback.** A :class:`LaunchBrief` names a ``target``. A
  backend either serves that target or refuses with an explicit
  :class:`UnsupportedTarget`. Native-Windows terminal sessions are an explicit, honest
  *gap*: no backend launches them today (see the LocalBackend rejection below).
- **Only LocalBackend exists.** Per the seam-freeze scope, the sole concrete backend is
  :class:`LocalBackend`, a behavior-preserving wrapper around today's local launcher
  (:mod:`horus.launch` / :mod:`horus.launcher`). Every other backend is deferred until
  the interface is fixed — which, as of this module, it is.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from horus import launch, registry

# --- target vocabulary --------------------------------------------------------
#
# A brief's ``target`` names the execution mode it wants. Only the two load-bearing
# constants live here; richer remote/managed modes (native-posix, managed-kubernetes,
# managed-boxlite, …) are defined by the *optional* backends that serve them, not by
# this minimal seam.

LOCAL = "local"
"""This machine's native terminal — served by :class:`LocalBackend`, whatever the host OS."""

NATIVE_WINDOWS = "native-windows"
"""A native Windows terminal reached via a remote execution plane — an explicit gap.

Distinct from ``LOCAL`` on a Windows host (which works): this names *remote* native
Windows execution, which no LaunchBackend provides. Omnigent explicitly excludes it
(``research/omnigent-fit-2026-07-10.md``), so it is rejected honestly rather than
silently downgraded to an SDK harness or a POSIX host.
"""


# --- neutral value types ------------------------------------------------------


@dataclass(frozen=True)
class LaunchBrief:
    """A backend-neutral request to launch a session.

    Mirrors the inputs of today's local launcher plus a ``target`` execution-mode
    marker. Kept flat and JSON-friendly so a remote backend can serialize it without
    reaching back into Horus internals.
    """

    project_dir: Path
    agent: str = "claude"
    account: str | None = None
    posture: str = "default"
    model: str | None = None
    prompt: str = ""
    target: str = LOCAL


@dataclass(frozen=True)
class Handle:
    """An opaque reference to a launched session, returned by :meth:`LaunchBackend.launch`.

    ``session_id`` is the neutral identifier shared with the registry. ``meta`` holds
    backend-private data (a local pid, later a remote conversation id) that only the
    issuing backend interprets — callers pass the handle back verbatim.
    """

    backend: str
    session_id: str
    meta: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionStatus:
    """A backend-neutral lifecycle snapshot returned by :meth:`LaunchBackend.status`."""

    state: str  # running | exited | failed | stale | unknown
    returncode: int | None = None
    detail: str | None = None


@dataclass(frozen=True)
class StreamEvent:
    """One observed output event from :meth:`LaunchBackend.stream`.

    Minimal on purpose: ``kind`` distinguishes output vs status vs end; ``data`` is the
    payload. A remote backend maps its SSE items onto this; LocalBackend does not stream.
    """

    kind: str
    data: str = ""


# --- errors -------------------------------------------------------------------


class BackendError(Exception):
    """Base for LaunchBackend failures."""


class UnsupportedTarget(BackendError):
    """The backend cannot serve the brief's ``target`` (raised instead of falling back)."""


class UnsupportedOperation(BackendError):
    """The backend has no honest implementation of this operation for this handle."""


class LaunchFailed(BackendError):
    """The launch was attempted but did not start a session."""


# --- the frozen interface -----------------------------------------------------


@runtime_checkable
class LaunchBackend(Protocol):
    """The frozen seam. A backend serves one or more targets; callers hold only handles.

    Implementations must not silently substitute a different target or a fake session:
    refuse with :class:`UnsupportedTarget` / :class:`UnsupportedOperation` instead.
    """

    name: str

    def launch(self, brief: LaunchBrief) -> Handle:
        """Start a session for ``brief`` and return its :class:`Handle`."""
        ...

    def status(self, handle: Handle) -> SessionStatus:
        """The current lifecycle state of the session ``handle`` refers to."""
        ...

    def stream(self, handle: Handle) -> Iterator[StreamEvent]:
        """Yield the session's output events (where the backend can observe them)."""
        ...

    def stop(self, handle: Handle) -> None:
        """End the session ``handle`` refers to; idempotent for an already-dead session."""
        ...


# --- the only concrete backend: LocalBackend ----------------------------------


class LocalBackend:
    """Runs the session on *this* machine, wrapping today's attended local launcher.

    The default is a behavior-preserving adapter around ``launch_interactive``. A local
    presentation surface may inject another launch function that returns the same
    :class:`~horus.launch.LaunchResult` contract (the web app uses its managed-tmux
    window host). It serves only the :data:`LOCAL` target — any other target, including
    the :data:`NATIVE_WINDOWS` gap, is rejected honestly with no fallback.
    """

    name = LOCAL

    def __init__(
        self,
        reg: registry.Registry | None = None,
        launch_fn: Callable[..., launch.LaunchResult] | None = None,
    ) -> None:
        self._reg = reg
        self._launch_fn = launch_fn or launch.launch_interactive

    # -- interface --

    def launch(self, brief: LaunchBrief) -> Handle:
        self._require_local(brief.target)
        result = self._launch_fn(
            agent=brief.agent,
            project_dir=brief.project_dir,
            account=brief.account,
            posture=brief.posture,
            model=brief.model,
            prompt=brief.prompt,
            reg=self._reg,
        )
        if not result.ok or not result.session_id:
            raise LaunchFailed(result.error or "launch failed")
        return Handle(
            backend=self.name,
            session_id=result.session_id,
            meta={"pid": result.pid, "target_ref": result.target_ref},
        )

    def status(self, handle: Handle) -> SessionStatus:
        self._own(handle)
        record = self._registry().get(handle.session_id)
        if record is None:
            return SessionStatus(state="unknown", detail="no registry record")
        return SessionStatus(state=record.status, returncode=record.returncode)

    def stream(self, handle: Handle) -> Iterator[StreamEvent]:
        self._own(handle)
        raise UnsupportedOperation(
            "LocalBackend launches attended sessions in their own terminal window; there "
            "is no parent-side byte stream to replay. Observe the session in its window "
            "or the in-app Sessions cockpit."
        )

    def stop(self, handle: Handle) -> None:
        self._own(handle)
        if handle.meta.get("target_ref"):
            from horus import terminal_sessions

            terminal_sessions.stop_session(handle.session_id, reg=self._registry())
            return
        pid = handle.meta.get("pid")
        if pid:
            _terminate_process(int(pid))
        self._registry().set_status(handle.session_id, "exited")

    # -- helpers --

    def _registry(self) -> registry.Registry:
        return self._reg or registry.Registry.default()

    def _own(self, handle: Handle) -> None:
        if handle.backend != self.name:
            raise BackendError(f"handle belongs to backend {handle.backend!r}, not {self.name!r}")

    def _require_local(self, target: str) -> None:
        if target == LOCAL:
            return
        if target == NATIVE_WINDOWS:
            raise UnsupportedTarget(
                "native-windows terminal sessions are an explicit gap: no LaunchBackend "
                "launches them. LocalBackend runs on the host it is invoked on (a Windows "
                "host serves the 'local' target); the optional Omnigent backend explicitly "
                "excludes native Windows. See research/omnigent-fit-2026-07-10.md."
            )
        raise UnsupportedTarget(
            f"LocalBackend only serves the {LOCAL!r} target; {target!r} needs a remote "
            "backend, which is optional and not built here. No silent fallback to local."
        )


def _terminate_process(pid: int) -> None:
    """Best-effort terminate ``pid`` (and its console tree on Windows).

    Swallows the already-gone races: stopping an exited session is a no-op, not an error.
    """
    import os
    import signal
    import subprocess

    if pid <= 0:
        return
    try:
        if os.name == "nt":
            subprocess.run(  # noqa: S603,S607 (fixed argv, no shell)
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
