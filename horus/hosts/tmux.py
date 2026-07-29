"""The tmux host: one Horus-managed tmux session per agent.

Everything here was `terminal_sessions`'s tmux implementation and behaves
identically; it moved so a second host could exist beside it rather than as an
`else` branch. Two invariants travel with it and must not be relaxed:

- **Positive-confirmation reaping** (:meth:`TmuxHost.live_refs` feeds it) — a
  session is killed only on evidence it is dead, never on absence of evidence.
- **Mouse mode is scoped to the new session, never `-g`** — a Horus launch must
  not touch the owner's tmux server/user default.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from horus import launch, registry
from horus.hosts import runnerspec
from horus.hosts.base import Capabilities

if TYPE_CHECKING:
    from horus.run_executor import RunRequest

ID = "tmux"


def available() -> bool:
    return os.name != "nt" and shutil.which("tmux") is not None


def inside_tmux() -> bool:
    """Whether Horus itself is running in a tmux pane.

    When it is, Horus and the sessions it creates share ONE tmux server (the plain
    ``tmux`` CLI resolves its socket from ``$TMUX``), so a client can be *moved*
    between them with ``switch-client`` instead of nesting a second client inside
    the pane. That is what makes ``horus tui`` usable from inside tmux.
    """
    return bool(os.environ.get("TMUX"))


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


class TmuxHost:
    id = ID
    switch_hint = "Ctrl-b L toggles between it and Horus"
    capabilities = Capabilities(
        persistent=True,
        attach=True,
        viewer=True,
        # tmux answers both reaping questions itself: `#{session_attached}` and
        # `#{session_activity}`.
        liveness=True,
        # The runner is the pane's own root process, so its returncode is real.
        reports_exit_code=True,
        state=False,
    )

    def available(self) -> bool:
        return available()

    def ensure_ready(self) -> str | None:
        # `tmux new-session` starts a server on demand; nothing to do.
        return None

    def switches_in_place(self) -> bool:
        return inside_tmux()

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
        reg: registry.Registry | None = None,
    ) -> launch.LaunchResult:
        """Create a unique detached tmux session, then optionally attend it."""
        root = Path(project_dir).resolve()
        if not available():
            return launch.LaunchResult(
                False, agent, root, account=account,
                error="tmux is not installed or is unavailable on this platform",
            )

        prepared, error = launch.prepare_interactive(
            agent=agent,
            project_dir=root,
            account=account,
            posture=posture,
            model=model,
            effort=effort,
            prompt=prompt,
            proxied=proxied,
            remote_control=remote_control,
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
        spec_path = runnerspec.write_spec(prepared, argv=runner_argv)
        store = reg or registry.Registry.default()
        # Keep reconciliation honest during the short handoff before the runner records
        # its own child PID. A failed tmux spawn is immediately corrected below.
        store.upsert(runnerspec.new_record(prepared, pid=os.getpid(), target=ID, target_ref=tmux_name))
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
            record = store.get(prepared.session_id)
            attached = self.attach(record) if record is not None else "session vanished during launch"
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

    def launch_worker(
        self, request: "RunRequest", *, reg: registry.Registry | None = None,
    ) -> launch.LaunchResult:
        """Host a one-shot worker in managed tmux and return after runner handoff.

        The pane executes the exact same adapter executor as a foreground ``run``;
        this only provides lifetime isolation and the attachable tmux target.
        """
        if not available():
            return launch.LaunchResult(False, request.agent, request.project, account=request.account,
                                       error="tmux is not installed or is unavailable on this platform")
        tmux_name = f"horus-{request.session_id[:12]}"
        store = reg or registry.Registry.default()
        store.upsert(registry.SessionRecord(
            session_id=request.session_id, agent=request.agent, project=request.project.as_posix(),
            account=request.account, pid=os.getpid(), status="running", launch_target=ID,
            target_ref=tmux_name, agent_session_id=request.resume,
            dispatch_base_sha=request.dispatch_base_sha, delivery_expected=request.delivery_expected,
        ))
        spec_path = runnerspec.write_payload({"kind": "run", "run": request.payload()}, request.session_id)
        runner = shlex.join([sys.executable, "-m", "horus.tmux_runner", request.session_id])
        created = subprocess.run(  # noqa: S603,S607 - fixed tmux argv; runner is shell-quoted
            ["tmux", "new-session", "-d", "-s", tmux_name, "-c", str(request.project), runner],
            capture_output=True, text=True, check=False,
        )
        if created.returncode != 0:
            spec_path.unlink(missing_ok=True)
            runnerspec.ready_path(request.session_id).unlink(missing_ok=True)
            store.update(request.session_id, termination_reason="launch-error")
            store.set_status(request.session_id, "failed", returncode=created.returncode)
            detail = (created.stderr or created.stdout).strip() or f"tmux exited {created.returncode}"
            return launch.LaunchResult(False, request.agent, request.project, account=request.account,
                                       session_id=request.session_id, target_ref=tmux_name,
                                       error=f"failed to create tmux session: {detail}")
        mouse_error = _enable_mouse_mode(tmux_name)
        if mouse_error:
            return self._failed_worker(
                request, store, tmux_name, spec_path,
                error=f"failed to enable tmux mouse mode for the new session: {mouse_error}",
            )
        if not runnerspec.await_handoff(request.session_id, store):
            current = store.get(request.session_id)
            detail = "runner did not report its PID handoff"
            if current and current.status != "running":
                detail = f"runner ended during launch ({current.status})"
            return self._failed_worker(request, store, tmux_name, spec_path, error=detail)
        current = store.get(request.session_id)
        return launch.LaunchResult(True, request.agent, request.project, account=request.account,
                                   session_id=request.session_id, pid=current.pid if current else None,
                                   target_ref=tmux_name)

    @staticmethod
    def _failed_worker(
        request: "RunRequest", store: registry.Registry, tmux_name: str, spec_path: Path, *, error: str,
    ) -> launch.LaunchResult:
        """Undo a known newly-created detached host after its handoff fails."""
        _kill_tmux_session(tmux_name)
        spec_path.unlink(missing_ok=True)
        runnerspec.ready_path(request.session_id).unlink(missing_ok=True)
        store.update(request.session_id, termination_reason="launch-error")
        store.set_status(request.session_id, "failed")
        return launch.LaunchResult(False, request.agent, request.project, account=request.account,
                                   session_id=request.session_id, target_ref=tmux_name, error=error)

    def attach(self, record: registry.SessionRecord) -> str | None:
        """Put this terminal on a tracked tmux session.

        Outside tmux this attaches a client and blocks until the owner detaches.
        Inside tmux — Horus running in its own pane — it instead *switches* the
        current client to the session and returns immediately, because both live on
        the same tmux server. Nesting a client would double every prefix key;
        switching does not. Coming back is ``Ctrl-b L`` (or choose-tree), and the
        Horus pane is untouched meanwhile.
        """
        if not available():
            return "tmux is not installed or is unavailable on this platform"
        if not record.target_ref:
            return f"session {record.session_id[:8]} is not hosted by tmux"
        if record.status != "running":
            return f"session {record.session_id[:8]} is {record.status}, not running"
        if inside_tmux():
            # No -c: run from inside a pane, tmux resolves the current client from $TMUX.
            # Keep stderr — "no current client" (a detached Horus pane) is the one message
            # that explains a failure here, and discarding it would leave no explanation.
            switched = subprocess.run(  # noqa: S603,S607 - tmux name is Horus-generated
                ["tmux", "switch-client", "-t", record.target_ref],
                capture_output=True, text=True, check=False,
            )
            if switched.returncode != 0:
                detail = (switched.stderr or switched.stdout).strip() or f"exit code {switched.returncode}"
                return f"tmux switch-client failed: {detail}"
            return None
        attached = subprocess.run(  # noqa: S603,S607 - tmux name is Horus-generated
            ["tmux", "attach-session", "-t", record.target_ref],
            check=False,
        )
        if attached.returncode != 0:
            return f"tmux attach failed with exit code {attached.returncode}"
        return None

    def stop(self, record: registry.SessionRecord) -> str | None:
        if not record.target_ref:
            return f"session {record.session_id[:8]} is not hosted by tmux"
        _kill_tmux_session(record.target_ref)
        runnerspec.spec_path(record.session_id).unlink(missing_ok=True)
        return None

    def viewer_argv(self, target_ref: str) -> list[str] | None:
        if not target_ref:
            return None
        return ["tmux", "attach-session", "-t", target_ref]

    def live_refs(self) -> dict[str, tuple[bool, float]]:
        """Horus-named tmux sessions the tmux server currently holds, keyed by name to
        ``(attached, last_activity_epoch)``. Empty when tmux is unavailable or has no
        server running (never an error — an absent server just means nothing to reap)."""
        if not available():
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
