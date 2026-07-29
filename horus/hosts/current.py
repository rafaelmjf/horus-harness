"""The current-TTY host: the floor every other host is measured against.

It promises nothing — no persistence, no attach, no viewer, no reaping — and that
is its job. Native Windows and hosts without tmux land here, and because it
declares its limits rather than being an `else` branch, every caller already has
to tolerate a host that cannot do something. That is what makes adding a third
host a matter of declaring a different set of gaps instead of a new special case.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from horus import launch, registry
from horus.hosts import runnerspec
from horus.hosts.base import Capabilities

if TYPE_CHECKING:
    from horus.run_executor import RunRequest

ID = "current"


class CurrentHost:
    """Run the agent in this terminal; it lives and dies with it."""

    id = ID
    # Never switches in place, so no hint is ever shown for it.
    switch_hint = ""
    capabilities = Capabilities(
        persistent=False,
        attach=False,
        viewer=False,
        liveness=False,
        # It is this process's own child, so `Popen.wait()` is the returncode.
        reports_exit_code=True,
        state=False,
    )

    def available(self) -> bool:
        return True

    def ensure_ready(self) -> str | None:
        return None

    def switches_in_place(self) -> bool:
        return False

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
        """Run an attended agent in this TTY, returning after the agent exits.

        ``attach``/``cols``/``rows`` are accepted and ignored: this host has exactly
        one display and cannot be sized from here. Accepting them keeps every host
        callable through one signature, which is the point of the protocol.
        """
        prepared, error = launch.prepare_interactive(
            agent=agent,
            project_dir=project_dir,
            account=account,
            posture=posture,
            model=model,
            effort=effort,
            prompt=prompt,
            proxied=proxied,
            remote_control=remote_control,
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
        store.upsert(runnerspec.new_record(prepared, pid=proc.pid, target=ID))
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

    def launch_worker(
        self, request: "RunRequest", *, reg: registry.Registry | None = None,
    ) -> launch.LaunchResult:
        return launch.LaunchResult(
            False, request.agent, request.project, account=request.account,
            error="the current-terminal host cannot host a detached worker",
        )

    def attach(self, record: registry.SessionRecord) -> str | None:
        return f"session {record.session_id[:8]} remains in its original terminal"

    def stop(self, record: registry.SessionRecord) -> str | None:
        return f"session {record.session_id[:8]} is not hosted by a persistent host"

    def viewer_argv(self, target_ref: str) -> list[str] | None:
        return None

    def live_refs(self) -> dict[str, tuple[bool, float]]:
        return {}
