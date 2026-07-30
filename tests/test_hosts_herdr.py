"""The herdr session host.

Shapes here mirror what the 2026-07-29 probe observed from herdr v0.7.5 — the
JSON envelope, the pane-id form, the fact that its server does not autostart —
so a herdr change that breaks the contract shows up as a test failure rather
than as a confusing launch.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from horus import hosts, launch, registry, terminal_sessions
from horus.hosts import herdr as herdr_host
from horus.hosts import runnerspec
from horus.launch import PreparedInteractive
from horus.registry import Registry, SessionRecord

SID = "12345678-1234-1234-1234-123456789abc"


def _home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _project(tmp_path):
    root = tmp_path / "demo"
    (root / ".horus").mkdir(parents=True, exist_ok=True)
    (root / ".horus" / "PRD.md").write_text("---\nnext_action: probe\n---\n", encoding="utf-8")
    return root


def _ok(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], 0, json.dumps({"id": "x", "result": payload}), "")


def _fail(stderr: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], 1, "", stderr)


def _created(pane_id: str = "w1:p1", label: str = "Agents") -> dict:
    """The envelope `herdr workspace create` actually returns (probe, v0.7.5)."""
    return {
        "type": "workspace_created",
        "workspace": {"workspace_id": "w1", "label": label},
        "root_pane": {"pane_id": pane_id, "workspace_id": "w1", "agent_status": "unknown"},
        "tab": {"tab_id": "w1:t1", "label": "1"},
    }


def _placement_stub(existing_tabs=(), idle_panes=(), panes=()):
    """A `_run` stand-in covering the calls `place_session` makes."""
    def fake(*args, **_kwargs):
        body: dict = {"type": "ok"}
        if args[:2] == ("workspace", "list"):
            body = {"workspaces": list(existing_tabs and [{"workspace_id": "w1",
                                                           "label": "Agents"}] or [])}
        elif args[:2] == ("workspace", "create"):
            body = _created()
        elif args[:2] == ("api", "snapshot"):
            body = {"snapshot": {"tabs": list(existing_tabs)}}
        elif args[:2] == ("pane", "list"):
            body = {"panes": list(panes)}
        elif args[:2] == ("pane", "process-info"):
            ref = args[3]
            name = "bash" if ref in idle_panes else "python"
            body = {"process_info": {"foreground_processes": [{"name": name, "cmdline": name}]}}
        elif args[:2] == ("tab", "create"):
            body = {"root_pane": {"pane_id": "w1:p9", "tab_id": "w1:t9"},
                    "tab": {"tab_id": "w1:t9"}}
        return _ok(body)
    return fake


def _prepared(root):
    return PreparedInteractive(
        agent="fake", project=root, account=None, session_id=SID,
        argv=[sys.executable, "-c", "pass"], env={},
    )


@pytest.fixture
def host(monkeypatch, tmp_path):
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host.shutil, "which", lambda name: f"/usr/bin/{name}")
    return herdr_host.HerdrHost()


def test_capabilities_match_what_the_probe_measured(host):
    caps = host.capabilities
    assert caps.persistent and caps.attach and caps.viewer
    # No attached flag and no activity clock exist in herdr's API, so two of the
    # four reaping conditions are unanswerable.
    assert caps.liveness is False
    # `pane run` types into a shell rather than exec'ing an argv.
    assert caps.reports_exit_code is False
    # The one thing tmux cannot do.
    assert caps.state is True


def test_registered_and_offered_as_a_target():
    assert hosts.get("herdr") is not None
    assert "herdr" in terminal_sessions.display_choices()
    # Opt-in, not automatic: tmux stays ahead of herdr in `auto` because it is the
    # proven host, it can be reaped, and it backs the phone path.
    assert hosts.AUTO_ORDER.index("tmux") < hosts.AUTO_ORDER.index("herdr")


def test_ensure_ready_starts_the_server_because_the_cli_never_does(host, monkeypatch):
    """The probe's Q1 finding, pinned: `workspace create` against no server fails
    with a bare ENOENT, so the host must bring the server up itself."""
    states = iter([False, True])
    started = []
    monkeypatch.setattr(host, "server_running", lambda: next(states))
    monkeypatch.setattr(
        herdr_host.subprocess, "Popen",
        lambda argv, **kwargs: started.append((argv, kwargs.get("start_new_session"))),
    )
    assert host.ensure_ready() is None
    assert started == [(["herdr", "server"], True)]


def test_ensure_ready_is_a_noop_when_the_server_is_already_up(host, monkeypatch):
    monkeypatch.setattr(host, "server_running", lambda: True)
    monkeypatch.setattr(
        herdr_host.subprocess, "Popen",
        lambda *_a, **_k: pytest.fail("must not start a second server"),
    )
    assert host.ensure_ready() is None


def test_ensure_ready_reports_a_server_that_never_comes_up(host, monkeypatch):
    monkeypatch.setattr(host, "server_running", lambda: False)
    monkeypatch.setattr(herdr_host.subprocess, "Popen", lambda *_a, **_k: None)
    monkeypatch.setattr(herdr_host, "_SERVER_READY_TIMEOUT", 0.05)
    assert "did not come up" in host.ensure_ready()


def test_launch_puts_the_session_in_a_project_named_tab(host, tmp_path, monkeypatch):
    """Layout: two fixed spaces, a tab per session labelled with just the project name.
    The first session reuses the fresh space's root tab rather than leaving an empty
    "1" tab beside it."""
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(launch, "prepare_interactive", lambda **_k: (_prepared(root), None))
    calls = []
    stub = _placement_stub()

    def fake_run(*args, **kwargs):
        calls.append(args)
        return stub(*args, **kwargs)

    monkeypatch.setattr(herdr_host, "_run", fake_run)
    monkeypatch.setattr(runnerspec, "await_handoff", lambda *_a, **_k: True)

    result = host.launch(agent="fake", project_dir=root, attach=False)
    assert result.ok, result.error
    # The pane id is the ref: it is what every other verb takes.
    assert result.target_ref == "w1:p1"

    created = next(a for a in calls if a[:2] == ("workspace", "create"))
    assert "--label" in created and created[created.index("--label") + 1] == "Agents"
    assert "--cwd" in created and "--no-focus" in created
    # The root tab is renamed to the project, not left as "1".
    renamed = next(a for a in calls if a[:2] == ("tab", "rename"))
    assert renamed == ("tab", "rename", "w1:t1", root.name)
    ran = next(a for a in calls if a[:2] == ("pane", "run"))
    assert ran[:3] == ("pane", "run", "w1:p1") and "horus.tmux_runner" in ran[3]

    record = Registry.default().get(SID)
    assert record.launch_target == "herdr" and record.target_ref == "w1:p1"
    # Attachable via the capability, with no id comparison anywhere.
    assert terminal_sessions.is_attachable(record)
    assert terminal_sessions.access_label(record) == "attachable"


def test_launch_tears_down_its_own_pane_when_the_runner_never_takes_over(host, tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(launch, "prepare_interactive", lambda **_k: (_prepared(root), None))
    closed = []

    stub = _placement_stub()

    def fake_run(*args, **kwargs):
        if args[:2] == ("pane", "close"):
            closed.append(args[2])
            return _ok({"type": "ok"})
        return stub(*args, **kwargs)

    monkeypatch.setattr(herdr_host, "_run", fake_run)
    monkeypatch.setattr(runnerspec, "await_handoff", lambda *_a, **_k: False)

    result = host.launch(agent="fake", project_dir=root, attach=False)
    assert not result.ok and "PID handoff" in result.error
    assert closed == ["w1:p1"]  # the pane it created, and only that one
    assert not runnerspec.spec_path(SID).exists()
    assert Registry.default().get(SID).status == "failed"


def test_launch_surfaces_why_the_workspace_could_not_be_created(host, tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(launch, "prepare_interactive", lambda **_k: (_prepared(root), None))
    # Exactly what the probe saw with no server running.
    monkeypatch.setattr(
        herdr_host, "_run",
        lambda *_a, **_k: _fail('Os { code: 2, kind: NotFound, message: "No such file or directory" }'),
    )
    result = host.launch(agent="fake", project_dir=root, attach=False)
    assert not result.ok
    assert "failed to create the Agents space" in result.error and "NotFound" in result.error


def test_viewer_focuses_the_pane_before_handing_back_the_client(host, monkeypatch):
    """Why the protocol lets a host prepare itself: a herdr client renders the
    whole session, so the pane must be focused first or the viewer shows someone
    else's work. tmux needs no such step."""
    calls = []

    def fake_run(*args, **_kwargs):
        calls.append(args)
        if args[:2] == ("pane", "get"):
            return _ok({"pane": {"pane_id": "w1:p1", "workspace_id": "w1"}})
        return _ok({"type": "ok"})

    monkeypatch.setattr(herdr_host, "_run", fake_run)
    assert host.viewer_argv("w1:p1") == ["herdr"]
    # Focus is per workspace: `pane focus` means "directional neighbour", which is
    # not "show me this session". The workspace id is read, never parsed off the ref.
    assert calls == [("pane", "get", "w1:p1"), ("workspace", "focus", "w1")]

    calls.clear()
    monkeypatch.setattr(herdr_host, "_run", lambda *_a, **_k: _fail("no such pane"))
    assert host.viewer_argv("w1:p1") is None


def test_attach_inside_herdr_switches_the_view_and_returns(host, monkeypatch):
    """The `switch-client` analogue: one server, so the view moves rather than
    nesting a client. Verified live 2026-07-29 — `workspace focus` from inside a
    pane returned rc=0 and moved the focused workspace."""
    monkeypatch.setenv("HERDR_PANE_ID", "w9:p1")
    calls = []
    def fake_run(*args, **_kwargs):
        calls.append(args)
        if args[:2] == ("pane", "get"):
            return _ok({"pane": {"pane_id": "w1:p1", "workspace_id": "w1"}})
        return _ok({"type": "ok"})

    monkeypatch.setattr(herdr_host, "_run", fake_run)
    monkeypatch.setattr(
        herdr_host.subprocess, "run",
        lambda *_a, **_k: pytest.fail("must not nest a client when already inside herdr"),
    )
    record = SessionRecord(
        session_id=SID, agent="fake", project="/tmp/x",
        launch_target="herdr", target_ref="w1:p1", status="running",
    )
    assert host.attach(record) is None
    assert calls == [("pane", "get", "w1:p1"), ("workspace", "focus", "w1")]


def test_reaping_never_touches_a_herdr_pane(host, tmp_path, monkeypatch):
    """The hard limit, pinned. herdr cannot report attached/idle, so its panes are
    leaked rather than risked — and `reap_orphans` must not even ask."""
    _home(tmp_path, monkeypatch)
    assert host.live_refs() == {}
    monkeypatch.setattr(
        herdr_host, "_run", lambda *_a, **_k: pytest.fail("reaping must not query herdr"),
    )
    Registry.default().upsert(SessionRecord(
        session_id=SID, agent="fake", project="/tmp/x", launch_target="herdr",
        target_ref="w1:p1", status="exited",
    ))
    assert terminal_sessions.reap_orphans(min_idle_seconds=0.0) == []


def test_agent_state_passes_through_and_never_guesses(host, monkeypatch):
    for reported, expected in [
        ("blocked", "blocked"), ("working", "working"), ("idle", "idle"),
        ("done", "done"), ("unknown", "unknown"),
        # A state this Horus does not know must degrade, not propagate.
        ("something-new", "unknown"),
    ]:
        monkeypatch.setattr(
            herdr_host, "_run",
            lambda *_a, _r=reported, **_k: _ok({"pane": {"agent_status": _r}}),
        )
        assert host.agent_state("w1:p1") == expected

    # A failed call is `unknown`, never a confident `idle`.
    monkeypatch.setattr(herdr_host, "_run", lambda *_a, **_k: _fail("no agent"))
    assert host.agent_state("w1:p1") == "unknown"


def test_unavailable_host_refuses_cleanly(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(herdr_host, "available", lambda: False)
    host = herdr_host.HerdrHost()
    assert not host.available()
    assert "not installed" in host.ensure_ready()
    result = host.launch(agent="fake", project_dir=root)
    assert not result.ok and "not installed" in result.error
    assert host.viewer_argv("w1:p1") is None


@pytest.mark.skipif(shutil.which("herdr") is None, reason="herdr is not installed")
def test_live_herdr_server_lifecycle(tmp_path, monkeypatch):
    """Against a real herdr: bring a server up, create a pane, run something in
    it, read its pid back, then close it.

    Isolation is MANDATORY here and is asserted, not assumed (PRD Rules; the
    2026-07-30 incident). This test previously claimed in this very docstring to
    be "isolated via a private config dir", set no such thing, and then stopped
    the owner's default server in its `finally` — killing three live agent
    sessions. Two things were wrong and both are fixed below:

    - The lever is `HERDR_SOCKET_PATH`, which sets the API socket directly.
      `HERDR_CONFIG_PATH` — what the old docstring implied — moves only the
      config *file*; measured against herdr v0.7.5 on 2026-07-30, the socket
      stayed on the real one. `tests/conftest.py` now redirects it suite-wide;
      this test overrides that with a socket it may actually bind.
    - Teardown now stops only a server this test started. `ensure_ready()`
      returns `None` both when it starts one and when it finds one already up,
      so its result can never answer "is this mine to stop?".

    The socket path is kept SHORT because `sun_path` caps it at 108 bytes on
    Linux (104 on macOS), and pytest's `tmp_path` alone can exhaust that.
    """
    socket_dir = Path(tempfile.mkdtemp(prefix="hz-live-"))
    monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket_dir / "h.sock"))

    host = herdr_host.HerdrHost()
    # The guard, asserted before anything is started: if the redirection above
    # ever stops working, fail here rather than operate on the owner's server.
    assert not host.server_running(), (
        f"a herdr server is already live on the isolated socket {socket_dir / 'h.sock'} — "
        "refusing to run, because teardown would stop a server this test does not own"
    )
    assert host.ensure_ready() is None, "the real herdr server did not start"
    started_by_this_test = True
    try:
        created = herdr_host._payload(
            herdr_host._run("workspace", "create", "--cwd", str(tmp_path), "--label", "horus-live-test"),
        )
        pane_id = created.get("root_pane", {}).get("pane_id")
        assert pane_id, f"no pane id in {created}"
        assert herdr_host._run("pane", "run", pane_id, "sleep 120").returncode == 0
        # Wait for the *named* process, not merely for a foreground process: the
        # pane's shell is always there, so "is the command up yet" cannot be
        # answered by process-info being non-empty. (This is also why the host
        # waits on the runner's own PID handoff instead of polling process-info.)
        foreground = {}
        for _ in range(100):
            info = herdr_host._payload(herdr_host._run("pane", "process-info", "--pane", pane_id))
            candidates = info.get("process_info", {}).get("foreground_processes", [])
            foreground = next((p for p in candidates if p.get("name") == "sleep"), {})
            if foreground:
                break
            __import__("time").sleep(0.1)
        assert foreground, "the command typed into the pane never became a live process"
        pid = foreground["pid"]
        assert herdr_host._run("pane", "close", pane_id).returncode == 0
        for _ in range(50):
            if not registry.process_alive(pid):
                break
            __import__("time").sleep(0.1)
        assert not registry.process_alive(pid), "closing the pane must kill its process"
    finally:
        # Only ever stop a server this test brought up, on this test's own
        # socket. Both halves matter: the socket keeps the command off the
        # owner's server, and the flag keeps it off a pre-existing one.
        if started_by_this_test:
            herdr_host._run("server", "stop")
        shutil.rmtree(socket_dir, ignore_errors=True)


def test_failures_name_a_stopped_server_rather_than_blaming_the_pane(host, monkeypatch):
    """Every herdr verb fails the same way when the server is down (a bare ENOENT on
    the socket), so "herdr does not know pane w1:p1" would send the owner hunting a
    pane problem that does not exist."""
    monkeypatch.setattr(herdr_host, "_run", lambda *_a, **_k: _fail("No such file or directory"))
    monkeypatch.setattr(herdr_host.HerdrHost, "server_running", lambda _self: False)
    record = SessionRecord(
        session_id=SID, agent="fake", project="/tmp/x",
        launch_target="herdr", target_ref="w1:p1", status="running",
    )
    assert host.attach(record) == "the herdr server is not running"
    assert host.stop(record) == "the herdr server is not running"

    # Server up but the pane genuinely absent → the specific message survives.
    monkeypatch.setattr(herdr_host.HerdrHost, "server_running", lambda _self: True)
    assert "does not know pane w1:p1" in host.attach(record)


# ---------------------------------------------------------------------------
# Placement (owner decision, 2026-07-29): two fixed spaces, a tab per session
# labelled with just the project name.
# ---------------------------------------------------------------------------


def test_the_layout_labels_are_spelled_for_a_human():
    """These are read in a sidebar and a tab strip, so they are names, not refs. The
    tmux cockpit keeps its `horus-` prefixed session name — that prefix is how
    Horus-owned tmux sessions are identifiable."""
    assert herdr_host.COCKPIT_LABEL == "Horus"
    assert herdr_host.AGENTS_LABEL == "Agents"


def test_a_second_project_gets_its_own_tab_in_the_existing_space(monkeypatch):
    existing = [{"tab_id": "w1:t1", "label": "horus-harness", "workspace_id": "w1"}]
    calls = []
    stub = _placement_stub(existing_tabs=existing, panes=[{"pane_id": "w1:p1", "tab_id": "w1:t1"}])

    def fake(*args, **kwargs):
        calls.append(args)
        return stub(*args, **kwargs)

    monkeypatch.setattr(herdr_host, "_run", fake)
    pane, error = herdr_host.place_session(Path("/tmp/agentic-gym-coach"))
    assert (pane, error) == ("w1:p9", None)
    # Reused the space, added a tab, and did not create a second Agents space.
    assert ("workspace", "create") not in [a[:2] for a in calls]
    created = next(a for a in calls if a[:2] == ("tab", "create"))
    assert created[created.index("--label") + 1] == "agentic-gym-coach"
    assert created[created.index("--cwd") + 1] == "/tmp/agentic-gym-coach"


def test_an_idle_same_project_tab_is_reused_rather_than_duplicated(monkeypatch):
    """A restart leaves tabs behind holding only a shell, and this owner runs about one
    session per project — so without reuse the Agents space grows a tab per launch
    forever."""
    existing = [{"tab_id": "w1:t1", "label": "horus-harness", "workspace_id": "w1"}]
    calls = []
    stub = _placement_stub(
        existing_tabs=existing,
        panes=[{"pane_id": "w1:p1", "tab_id": "w1:t1"}],
        idle_panes=("w1:p1",),
    )

    def fake(*args, **kwargs):
        calls.append(args)
        return stub(*args, **kwargs)

    monkeypatch.setattr(herdr_host, "_run", fake)
    pane, error = herdr_host.place_session(Path("/tmp/horus-harness"))
    assert (pane, error) == ("w1:p1", None)
    assert ("tab", "create") not in [a[:2] for a in calls]


def test_a_busy_same_project_tab_gets_a_sibling_never_trampled(monkeypatch):
    """Launching a second session for a project must not land in the pane where the
    first one is still working."""
    existing = [{"tab_id": "w1:t1", "label": "horus-harness", "workspace_id": "w1"}]
    stub = _placement_stub(
        existing_tabs=existing,
        panes=[{"pane_id": "w1:p1", "tab_id": "w1:t1"}],
        idle_panes=(),  # w1:p1 is busy
    )
    monkeypatch.setattr(herdr_host, "_run", stub)
    pane, error = herdr_host.place_session(Path("/tmp/horus-harness"))
    assert error is None and pane == "w1:p9"  # a new tab, not the busy pane


def test_pane_is_idle_judges_by_process_name_not_our_command_line(monkeypatch):
    """Matching our own argv would break the moment the runner's command changes; a
    bare shell is the durable signal."""
    for name, expected in [("bash", True), ("zsh", True), ("fish", True),
                           ("python", False), ("claude", False), ("node", False)]:
        monkeypatch.setattr(
            herdr_host, "_run",
            lambda *_a, _n=name, **_k: _ok(
                {"process_info": {"foreground_processes": [{"name": _n, "cmdline": _n}]}},
            ),
        )
        assert herdr_host.pane_is_idle("w1:p1") is expected, name

    # No foreground process at all, and an unreachable server, both read as idle —
    # never as "something of ours is running here".
    monkeypatch.setattr(herdr_host, "_run", lambda *_a, **_k: _ok({"process_info": {}}))
    assert herdr_host.pane_is_idle("w1:p1") is True
    monkeypatch.setattr(herdr_host, "_run", lambda *_a, **_k: _fail("no server"))
    assert herdr_host.pane_is_idle("w1:p1") is True


def test_a_hosted_launch_carries_the_thread_id_into_the_registry_row(tmp_path, monkeypatch):
    """The thread id must survive the host layer, not just `prepare_interactive` —
    `runnerspec.new_record` builds the row for every host, so a host that dropped it
    would leave exactly the sessions worth restoring (the persistent ones) unrestorable."""
    prepared = PreparedInteractive(
        agent="claude", project=tmp_path, account=None, session_id=SID,
        argv=["claude"], env={}, agent_session_id=SID,
    )
    record = runnerspec.new_record(prepared, pid=123, target="herdr", target_ref="w1:p1")
    assert record.agent_session_id == SID

    codex_like = PreparedInteractive(
        agent="codex", project=tmp_path, account=None, session_id=SID,
        argv=["codex"], env={}, agent_session_id=None,
    )
    assert runnerspec.new_record(codex_like, pid=123, target="herdr").agent_session_id is None
