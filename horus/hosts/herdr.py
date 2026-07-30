"""The herdr host: one workspace per agent on a herdr server.

Everything here follows what the 2026-07-29 probe measured against herdr v0.7.5
(evidence in `.horus/backlog/archive/herdr-host-probe.md`), and the three places
herdr differs from tmux are declared rather than worked around:

- **Its server does not autostart.** `workspace create` against no server fails
  outright, so :meth:`HerdrHost.ensure_ready` starts one. tmux gets this free.
- **It cannot answer the reaping questions.** There is no attached flag and no
  activity clock anywhere in its API (checked against the full bundled schema),
  so ``liveness=False`` and its panes are never reaped. Leaking an idle pane is
  cheap; killing a live agent is not.
- **`pane run` types into the pane's shell** rather than exec'ing an argv, so the
  runner is a shell child and herdr never yields a returncode
  (``reports_exit_code=False``). That costs nothing: the runner records its own
  outcome in the registry, which is the single source of outcome truth on every
  host already.

In exchange it is the first host that reports agent state (working/idle/blocked),
which is the capability the tmux host cannot offer at all.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from horus import launch, registry
from horus.hosts import runnerspec
from horus.hosts.base import Capabilities

if TYPE_CHECKING:
    from horus.run_executor import RunRequest

ID = "herdr"

# Layout (owner decision, 2026-07-29). herdr's own idiom is agents as tabs inside a
# space, with the sidebar reporting their state across the session — so porting tmux's
# session-per-agent 1:1 produced a flat list of spaces that read wrong. Two fixed
# spaces instead: the cockpit in one, every agent session a tab in the other, labelled
# with just the project name. Project *grouping* was considered and dropped: this owner
# rarely runs parallel sessions per project, so a space per project would usually hold
# exactly one tab.
COCKPIT_LABEL = "Horus"
AGENTS_LABEL = "Agents"

# A pane sitting at one of these has nothing of ours running in it. Used instead of
# matching our own command line, which would break the moment the runner's argv changes.
_SHELLS = frozenset({"bash", "sh", "zsh", "fish", "dash", "ksh", "tcsh"})

# The server takes a moment to bind its socket after being started.
_SERVER_READY_TIMEOUT = 10.0

# Agent states herdr reports. `unknown` is its own honest answer for "no
# manifest matched", and Horus keeps it rather than guessing.
STATES = ("idle", "working", "blocked", "done", "unknown")


def executable() -> str | None:
    return shutil.which("herdr")


def available() -> bool:
    return os.name != "nt" and executable() is not None


def inside_herdr() -> bool:
    """Whether Horus itself is running in a herdr pane.

    herdr exports ``HERDR_ENV``/``HERDR_PANE_ID``/``HERDR_SOCKET_PATH`` into every
    pane — the structural analogue of ``$TMUX``, and like it, the socket path comes
    along, so a nested Horus talks to the same server it is running in and
    create-then-switch stays self-consistent.
    """
    return bool(os.environ.get("HERDR_ENV") or os.environ.get("HERDR_PANE_ID"))


def _run(*args: str, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """Invoke the herdr CLI. Never discards stderr: on this host the CLI's own
    message ("no such file or directory" for an absent server) is the only thing
    that explains a failure."""
    return subprocess.run(  # noqa: S603,S607 - fixed argv; refs are Horus-generated
        ["herdr", *args], capture_output=True, text=True, check=False, timeout=timeout,
    )


def _payload(completed: subprocess.CompletedProcess) -> dict:
    """herdr answers with one JSON object per call. A non-zero exit or unparseable
    body yields ``{}`` so callers branch on emptiness, never on a parse crash."""
    if completed.returncode != 0:
        return {}
    try:
        decoded = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    return decoded.get("result", {}) if isinstance(decoded, dict) else {}


def _detail(completed: subprocess.CompletedProcess) -> str:
    return (completed.stderr or completed.stdout).strip() or f"herdr exited {completed.returncode}"


def _pane(target_ref: str) -> dict:
    """One pane's live facts, or ``{}``. The authoritative source for both the
    workspace a pane belongs to and its agent state — `pane get` carries
    ``workspace_id`` and ``agent_status`` in the same payload."""
    return _payload(_run("pane", "get", target_ref)).get("pane", {})


def _why_not(fallback: str) -> str:
    """Explain a failed call, checking the cheap structural cause first.

    Every herdr verb fails identically when the server is down — a bare ENOENT on
    the socket — so a message about the *pane* would send someone hunting the wrong
    thing. Only consulted on a failure path, so the extra call costs nothing normally.
    """
    if not HerdrHost().server_running():
        return "the herdr server is not running"
    return fallback


def _bring_into_view(target_ref: str) -> str | None:
    """Make ``target_ref`` the visible pane. Error string, or ``None``.

    Focus is per *workspace*, not per pane: `herdr pane focus` moves to a
    directional neighbour (left/right/up/down), which is not what "show me this
    session" means. Horus gives each agent its own workspace with a single root
    pane, so focusing that workspace is exactly equivalent — and the workspace id
    is read from the pane rather than parsed out of the ref, so the ref stays an
    opaque string as far as this host is concerned.
    """
    workspace_id = _pane(target_ref).get("workspace_id")
    if not workspace_id:
        return _why_not(f"herdr does not know pane {target_ref}")
    focused = _run("workspace", "focus", workspace_id)
    if focused.returncode != 0:
        return f"herdr could not focus the workspace: {_detail(focused)}"
    return None


def _workspaces() -> list[dict]:
    return _payload(_run("workspace", "list")).get("workspaces", [])


def _find_workspace(label: str) -> str | None:
    for workspace in _workspaces():
        if workspace.get("label") == label and workspace.get("workspace_id"):
            return workspace["workspace_id"]
    return None


def _tabs(workspace_id: str) -> list[dict]:
    snapshot = _payload(_run("api", "snapshot")).get("snapshot", {})
    return [tab for tab in snapshot.get("tabs", []) if tab.get("workspace_id") == workspace_id]


def _pane_of_tab(tab_id: str) -> str | None:
    for pane in _payload(_run("pane", "list")).get("panes", []):
        if pane.get("tab_id") == tab_id:
            return pane.get("pane_id")
    return None


def pane_is_idle(target_ref: str) -> bool:
    """Whether ``target_ref`` is sitting at a bare shell with nothing of ours in it.

    herdr restores workspace/tab *structure* across a server restart but not the
    processes, so a tab can come back looking populated while holding only a shell.
    Judging by "is the foreground process a shell" rather than by matching our own
    command line means this keeps working when the runner's argv changes.
    """
    info = _payload(_run("pane", "process-info", "--pane", target_ref))
    running = info.get("process_info", {}).get("foreground_processes", [])
    if not running:
        return True
    return all((proc.get("name") or "") in _SHELLS for proc in running)


def place_session(project: Path) -> tuple[str | None, str | None]:
    """Find or make the tab this session belongs in. Returns ``(pane_id, error)``.

    Reuses a same-project tab that is idle — a restart leaves those behind, and this
    owner runs about one session per project, so reuse is what keeps the Agents space
    from silently growing a tab per launch forever. A same-project tab that is *busy*
    gets a sibling rather than being trampled.
    """
    label = project.name
    workspace_id = _find_workspace(AGENTS_LABEL)
    if workspace_id is None:
        created = _run(
            "workspace", "create", "--label", AGENTS_LABEL,
            "--cwd", str(project), "--no-focus",
        )
        body = _payload(created)
        pane_id = body.get("root_pane", {}).get("pane_id")
        tab_id = body.get("tab", {}).get("tab_id")
        if not pane_id or not tab_id:
            return None, f"failed to create the {AGENTS_LABEL} space: {_detail(created)}"
        # A fresh space already has one tab; name it and use it rather than leaving an
        # empty "1" tab beside the first session.
        _run("tab", "rename", tab_id, label)
        return pane_id, None

    for tab in _tabs(workspace_id):
        if tab.get("label") != label:
            continue
        pane_id = _pane_of_tab(tab.get("tab_id", ""))
        if pane_id and pane_is_idle(pane_id):
            return pane_id, None

    created = _run(
        "tab", "create", "--workspace", workspace_id, "--cwd", str(project), "--label", label,
    )
    pane_id = _payload(created).get("root_pane", {}).get("pane_id")
    if not pane_id:
        return None, f"failed to create a tab for {label}: {_detail(created)}"
    return pane_id, None


class HerdrHost:
    id = ID
    # herdr leaves `previous_workspace` unbound by default, so point at the
    # picker rather than a key that does nothing.
    switch_hint = "Ctrl+b w picks a space — the cockpit is 'Horus'"
    capabilities = Capabilities(
        persistent=True,
        attach=True,
        viewer=True,
        # Measured 2026-07-29: no attached flag, no activity clock. Two of the four
        # reaping conditions are unanswerable, so this host has no reap candidates.
        liveness=False,
        # `pane run` types into a shell; the runner reports its own outcome.
        reports_exit_code=False,
        state=True,
    )

    def available(self) -> bool:
        return available()

    def server_running(self) -> bool:
        status = _run("status", "server")
        return status.returncode == 0 and "status: running" in status.stdout

    def ensure_ready(self) -> str | None:
        """Start the herdr server if it is not already up.

        Unlike tmux, the herdr CLI never autostarts its server — every command
        against an absent one fails with a bare ENOENT on the socket. Discovering
        that here means a launch fails with a reason instead of somewhere deeper.
        """
        if not available():
            return "herdr is not installed or is unavailable on this platform"
        if self.server_running():
            return None
        try:
            subprocess.Popen(  # noqa: S603,S607 - fixed argv, no user input
                ["herdr", "server"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            return f"failed to start the herdr server: {exc}"
        deadline = time.monotonic() + _SERVER_READY_TIMEOUT
        while time.monotonic() < deadline:
            if self.server_running():
                return None
            time.sleep(0.1)
        return "the herdr server did not come up within its timeout"

    def switches_in_place(self) -> bool:
        return inside_herdr()

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
        """Create a workspace for this agent and run the pane runner in it.

        ``cols``/``rows`` are accepted and ignored: herdr sizes its own panes from
        the attached client, and there is no create-time geometry to set.
        """
        root = Path(project_dir).resolve()
        if not available():
            return launch.LaunchResult(
                False, agent, root, account=account,
                error="herdr is not installed or is unavailable on this platform",
            )

        prepared, error = launch.prepare_interactive(
            agent=agent, project_dir=root, account=account, posture=posture,
            model=model, effort=effort, prompt=prompt, proxied=proxied,
            remote_control=remote_control,
            # Reusing the caller's id keeps a RESTORED session in its original
            # registry row, so its identity and delivery evidence survive.
            session_id=session_id, resume_thread_id=resume_thread_id,
        )
        if prepared is None:
            return launch.LaunchResult(False, agent, root, account=account, error=error)

        resolved = shutil.which(prepared.argv[0])
        if resolved is None:
            return launch.LaunchResult(
                False, prepared.agent, prepared.project, account=account,
                error=f"agent executable not found on PATH: {prepared.argv[0]}",
            )

        spec_path = runnerspec.write_spec(prepared, argv=[resolved, *prepared.argv[1:]])
        store = reg or registry.Registry.default()
        pane_id, placement_error = place_session(prepared.project)
        if pane_id is None:
            spec_path.unlink(missing_ok=True)
            return launch.LaunchResult(
                False, prepared.agent, prepared.project, account=account,
                session_id=prepared.session_id, error=placement_error,
            )

        # The pane id IS the ref: it is what every other verb takes, and unlike the
        # workspace id it survives being the thing we later read, close, or view.
        store.upsert(runnerspec.new_record(
            prepared, pid=os.getpid(), target=ID, target_ref=pane_id,
        ))
        runner = shlex.join([sys.executable, "-m", "horus.tmux_runner", prepared.session_id])
        started = _run("pane", "run", pane_id, runner)
        if started.returncode != 0:
            self._teardown(pane_id, prepared.session_id, store, spec_path)
            return launch.LaunchResult(
                False, prepared.agent, prepared.project, account=account,
                session_id=prepared.session_id, target_ref=pane_id,
                error=f"failed to start the runner in the herdr pane: {_detail(started)}",
            )
        if not runnerspec.await_handoff(prepared.session_id, store):
            current = store.get(prepared.session_id)
            detail = "runner did not report its PID handoff"
            if current and current.status != "running":
                detail = f"runner ended during launch ({current.status})"
            self._teardown(pane_id, prepared.session_id, store, spec_path)
            return launch.LaunchResult(
                False, prepared.agent, prepared.project, account=account,
                session_id=prepared.session_id, target_ref=pane_id, error=detail,
            )

        if attach:
            record = store.get(prepared.session_id)
            attached = self.attach(record) if record is not None else "session vanished during launch"
            if attached:
                return launch.LaunchResult(
                    False, prepared.agent, prepared.project, account=account,
                    session_id=prepared.session_id, target_ref=pane_id, error=attached,
                )
        current = store.get(prepared.session_id)
        return launch.LaunchResult(
            True, prepared.agent, prepared.project, account=account,
            session_id=prepared.session_id, pid=current.pid if current else None,
            target_ref=pane_id,
        )

    def launch_worker(
        self, request: "RunRequest", *, reg: registry.Registry | None = None,
    ) -> launch.LaunchResult:
        """Host a one-shot `horus run` worker in a herdr pane."""
        if not available():
            return launch.LaunchResult(
                False, request.agent, request.project, account=request.account,
                error="herdr is not installed or is unavailable on this platform",
            )
        store = reg or registry.Registry.default()
        pane_id, placement_error = place_session(request.project)
        if pane_id is None:
            return launch.LaunchResult(
                False, request.agent, request.project, account=request.account,
                session_id=request.session_id, error=placement_error,
            )
        store.upsert(registry.SessionRecord(
            session_id=request.session_id, agent=request.agent, project=request.project.as_posix(),
            account=request.account, pid=os.getpid(), status="running", launch_target=ID,
            target_ref=pane_id, agent_session_id=request.resume,
            dispatch_base_sha=request.dispatch_base_sha, delivery_expected=request.delivery_expected,
        ))
        spec_path = runnerspec.write_payload({"kind": "run", "run": request.payload()}, request.session_id)
        runner = shlex.join([sys.executable, "-m", "horus.tmux_runner", request.session_id])
        started = _run("pane", "run", pane_id, runner)
        if started.returncode != 0:
            self._teardown(pane_id, request.session_id, store, spec_path, launch_error=True)
            return launch.LaunchResult(
                False, request.agent, request.project, account=request.account,
                session_id=request.session_id, target_ref=pane_id,
                error=f"failed to start the runner in the herdr pane: {_detail(started)}",
            )
        if not runnerspec.await_handoff(request.session_id, store):
            current = store.get(request.session_id)
            detail = "runner did not report its PID handoff"
            if current and current.status != "running":
                detail = f"runner ended during launch ({current.status})"
            self._teardown(pane_id, request.session_id, store, spec_path, launch_error=True)
            return launch.LaunchResult(
                False, request.agent, request.project, account=request.account,
                session_id=request.session_id, target_ref=pane_id, error=detail,
            )
        current = store.get(request.session_id)
        return launch.LaunchResult(
            True, request.agent, request.project, account=request.account,
            session_id=request.session_id, pid=current.pid if current else None,
            target_ref=pane_id,
        )

    def _teardown(
        self, pane_id: str, session_id: str, store: registry.Registry, spec_path: Path,
        *, launch_error: bool = False,
    ) -> None:
        """Undo a known newly-created pane whose runner never took over."""
        _run("pane", "close", pane_id)
        spec_path.unlink(missing_ok=True)
        runnerspec.ready_path(session_id).unlink(missing_ok=True)
        if launch_error:
            store.update(session_id, termination_reason="launch-error")
        store.set_status(session_id, "failed")

    def attach(self, record: registry.SessionRecord) -> str | None:
        """Put this terminal on a live pane.

        Inside herdr this is `workspace focus`, which moves the view and returns at
        once — the same shape as tmux's `switch-client`, and for the same reason
        (one server, so the client is moved rather than nested). Outside herdr it
        focuses the pane and then attaches a client, which blocks until detach.
        """
        if not available():
            return "herdr is not installed or is unavailable on this platform"
        if not record.target_ref:
            return f"session {record.session_id[:8]} is not hosted by herdr"
        if record.status != "running":
            return f"session {record.session_id[:8]} is {record.status}, not running"
        if (not_visible := _bring_into_view(record.target_ref)) is not None:
            return not_visible
        if inside_herdr():
            return None
        attached = subprocess.run(  # noqa: S603,S607 - fixed argv
            ["herdr"], check=False,
        )
        if attached.returncode != 0:
            return f"herdr attach failed with exit code {attached.returncode}"
        return None

    def stop(self, record: registry.SessionRecord) -> str | None:
        if not record.target_ref:
            return f"session {record.session_id[:8]} is not hosted by herdr"
        closed = _run("pane", "close", record.target_ref)
        runnerspec.spec_path(record.session_id).unlink(missing_ok=True)
        if closed.returncode != 0:
            return _why_not(f"herdr could not close the pane: {_detail(closed)}")
        return None

    def viewer_argv(self, target_ref: str) -> list[str] | None:
        """Focus the pane, then hand back the client argv.

        This is why the protocol lets a host prepare itself before returning an
        argv: unlike tmux — where one session per agent means `attach -t <ref>`
        frames exactly that agent — a herdr client renders the whole session, so
        the right pane has to be focused first or the viewer shows someone else's
        work.
        """
        if not target_ref or not available():
            return None
        if _bring_into_view(target_ref) is not None:
            return None
        return ["herdr"]

    def live_refs(self) -> dict[str, tuple[bool, float]]:
        """Always empty: this host declares ``liveness=False``.

        herdr exposes neither an attached flag nor an activity clock, so it can
        never satisfy the last two reaping conditions. Returning nothing is the
        honest answer — and `reap_orphans` skips this host entirely anyway.
        """
        return {}

    # -- beyond the protocol: the capability tmux does not have ----------------

    def agent_state(self, target_ref: str) -> str:
        """This pane's agent state: one of :data:`STATES`.

        ``unknown`` is herdr's own answer when no detection manifest matched, and
        it is passed through rather than guessed at — a confident wrong `idle` is
        worse than an honest `unknown`.
        """
        if not target_ref or not available():
            return "unknown"
        # Read it from `pane get`, not `agent explain`: the pane payload carries
        # `agent_status` for every pane, whereas `agent explain` errors outright on
        # a pane herdr has not detected an agent in (`agent_not_found`) — which is
        # a normal state, not a failure.
        state = _pane(target_ref).get("agent_status")
        return state if state in STATES else "unknown"
