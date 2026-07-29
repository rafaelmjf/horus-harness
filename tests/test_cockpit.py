"""`horus tui <host>` — the cockpit front door, and the host-preference default."""

from __future__ import annotations

import json
import subprocess
import tempfile

import pytest

from horus import cli, cockpit, config, hosts, terminal_sessions
from horus.launch import LaunchResult
from horus.hosts import herdr as herdr_host
from horus.hosts import tmux as tmux_host


def _home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


# ---------------------------------------------------------------------------
# The CLI surface
# ---------------------------------------------------------------------------


def test_tui_accepts_a_host_positional_built_from_the_registry():
    """`horus tui tmux` / `horus tui herdr`, with the choices coming from the host
    registry so a newly registered host is offered without touching argparse."""
    parser = cli.build_parser()
    action = next(
        a for a in parser._subparsers._group_actions[0].choices["tui"]._actions
        if a.dest == "host"
    )
    assert tuple(action.choices) == terminal_sessions.host_choices()
    assert set(hosts.ids()) == set(action.choices)
    # Optional, and absent means "run right here" — bare `horus tui` is unchanged.
    assert parser.parse_args(["tui"]).host is None
    assert parser.parse_args(["tui", "tmux"]).host == "tmux"
    with pytest.raises(SystemExit):
        parser.parse_args(["tui", "nosuchhost"])


def test_open_in_rejects_an_unknown_host_and_names_the_real_ones():
    code, message = cockpit.open_in("nosuchhost")
    assert code == 2
    assert "unknown session host" in message
    for host_id in hosts.ids():
        assert host_id in message


def test_open_in_current_is_the_explicit_in_place_case():
    """`horus tui current` must behave exactly like bare `horus tui` — an empty
    message is the signal to run the TUI in this process."""
    assert cockpit.open_in("current") == (0, "")


def test_open_in_refuses_a_host_that_is_not_installed(monkeypatch):
    monkeypatch.setattr(tmux_host, "available", lambda: False)
    code, message = cockpit.open_in("tmux")
    assert code == 2 and "not installed" in message


def test_open_in_surfaces_a_host_that_cannot_be_made_ready(monkeypatch):
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setattr(
        herdr_host.HerdrHost, "ensure_ready", lambda _self: "the herdr server did not come up",
    )
    code, message = cockpit.open_in("herdr")
    assert code == 2 and message == "the herdr server did not come up"


def test_open_in_does_not_nest_a_cockpit_inside_its_own_host(monkeypatch):
    """Already in a tmux pane? Run here. Creating a cockpit inside a cockpit is
    the mistake this guard exists to prevent."""
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    monkeypatch.setenv("TMUX", "/tmp/tmux,1,0")
    created = []
    monkeypatch.setattr(
        cockpit.subprocess, "run", lambda *a, **k: created.append(a) or subprocess.CompletedProcess([], 0),
    )
    assert cockpit.open_in("tmux") == (0, "")
    assert created == []


def test_open_in_creates_then_attaches_a_tmux_cockpit(monkeypatch):
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(tmux_host.TmuxHost, "live_refs", lambda _self: {})
    monkeypatch.setattr(cockpit, "_tui_command", lambda: ["/usr/bin/horus", "tui"])
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(cockpit.subprocess, "run", fake_run)
    assert cockpit.open_in("tmux") == (0, "")
    assert calls[0] == [
        "tmux", "new-session", "-d", "-s", "horus-cockpit", "/usr/bin/horus", "tui",
    ]
    # Attach goes through the host's own viewer argv, not a hand-built command.
    assert calls[1] == ["tmux", "attach-session", "-t", "horus-cockpit"]


def test_open_in_reattaches_the_existing_cockpit_instead_of_making_a_second(monkeypatch):
    """One cockpit per host. Two would split the owner's state across panes they
    then have to tell apart."""
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(
        tmux_host.TmuxHost, "live_refs", lambda _self: {"horus-cockpit": (False, 0.0)},
    )
    calls = []
    monkeypatch.setattr(
        cockpit.subprocess, "run",
        lambda argv, **_k: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )
    assert cockpit.open_in("tmux") == (0, "")
    assert all("new-session" not in argv for argv in calls), calls
    assert calls == [["tmux", "attach-session", "-t", "horus-cockpit"]]


def test_open_in_creates_a_herdr_cockpit_through_the_hosts_own_verbs(monkeypatch):
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host.HerdrHost, "ensure_ready", lambda _self: None)
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.setattr(cockpit, "_tui_command", lambda: ["/usr/bin/horus", "tui"])
    seen = []

    def fake_herdr_run(*args, **_kwargs):
        seen.append(args)
        body: dict = {"type": "ok"}
        if args[:2] == ("pane", "list"):
            body = {"panes": []}
        elif args[:2] == ("workspace", "create"):
            body = {"root_pane": {"pane_id": "w1:p1", "workspace_id": "w1"}}
        elif args[:2] == ("pane", "get"):
            body = {"pane": {"pane_id": "w1:p1", "workspace_id": "w1"}}
        return subprocess.CompletedProcess([], 0, json.dumps({"result": body}), "")

    monkeypatch.setattr(herdr_host, "_run", fake_herdr_run)
    monkeypatch.setattr(
        cockpit.subprocess, "run",
        lambda argv, **_k: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    assert cockpit.open_in("herdr") == (0, "")
    verbs = [args[:2] for args in seen]
    assert ("workspace", "create") in verbs and ("pane", "run") in verbs
    # The viewer focuses the workspace before the client is spawned.
    assert ("workspace", "focus") in verbs


# ---------------------------------------------------------------------------
# Resolution: launch agents where Horus is already running
# ---------------------------------------------------------------------------


def test_resolution_prefers_the_host_horus_is_running_inside(monkeypatch):
    """The bug this fixes: a cockpit in a herdr pane used to launch agents into
    tmux (first in AUTO_ORDER and available), so switching back could not work —
    the two live on different servers."""
    monkeypatch.delenv("HORUS_TERMINAL_TARGET", raising=False)
    monkeypatch.setattr(config, "load_terminal_host", lambda: "auto")
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host, "available", lambda: True)

    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setenv("HERDR_ENV", "1")
    assert hosts.enclosing().id == "herdr"
    assert hosts.resolve().id == "herdr"

    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.setenv("TMUX", "/tmp/tmux,1,0")
    assert hosts.resolve().id == "tmux"


def test_an_explicit_choice_still_beats_the_enclosing_host(monkeypatch):
    """Being inside herdr is a default, not a veto: the owner's config and the env
    override are them saying otherwise on purpose."""
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.delenv("TMUX", raising=False)

    monkeypatch.setattr(config, "load_terminal_host", lambda: "tmux")
    monkeypatch.delenv("HORUS_TERMINAL_TARGET", raising=False)
    assert hosts.resolve().id == "tmux"

    monkeypatch.setattr(config, "load_terminal_host", lambda: "auto")
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "current")
    assert hosts.resolve().id == "current"


def test_no_enclosing_host_when_outside_all_of_them(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("HERDR_ENV", raising=False)
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    assert hosts.enclosing() is None


# ---------------------------------------------------------------------------
# The global default
# ---------------------------------------------------------------------------


def test_terminal_host_round_trips_and_survives_unrelated_writes(monkeypatch):
    monkeypatch.setenv("HOME", tempfile.mkdtemp())
    assert config.load_terminal_host() == "auto"
    assert config.set_terminal_host("herdr") == "herdr"
    assert config.load_terminal_host() == "herdr"
    # A writer for a different section must not drop it.
    config.set_launch_default_posture("plan")
    assert config.load_terminal_host() == "herdr"
    text = (config.config_path()).read_text(encoding="utf-8")
    assert text.count("[terminal]") == 1  # managed exactly once, never duplicated


def test_set_terminal_host_refuses_an_empty_value(monkeypatch):
    monkeypatch.setenv("HOME", tempfile.mkdtemp())
    with pytest.raises(ValueError):
        config.set_terminal_host("   ")


def test_defaults_screen_offers_every_host_plus_auto_and_persists_the_pick(tmp_path, monkeypatch):
    from horus import terminal_tui

    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui._show("settings")

    offered = [value for kind, value in ui.items if kind == "host"]
    assert offered == ["auto", *hosts.ids()]

    # The host rows sit after posture and window in the Defaults list.
    target = (
        len(config.LAUNCH_POSTURE_CHOICES)
        + len(config.LAUNCH_WINDOW_CHOICES)
        + offered.index("tmux")
    )
    ui.move(target - ui.selected)
    assert ui.items[ui.selected] == ("host", "tmux")
    ui.activate()

    assert config.load_terminal_host() == "tmux"
    assert ui.selected == target  # selection tracks the just-set host
    assert "hosted by: tmux" in ui.status
    rendered = "".join(text for _s, text in ui._body_text() if isinstance(text, str))
    assert "Session host" in rendered and "[current] tmux" in rendered


def test_defaults_screen_marks_a_host_that_is_not_installed(tmp_path, monkeypatch):
    """Unavailable hosts stay listed and are marked rather than hidden: an owner
    setting up a machine needs to see herdr is an option they have not installed."""
    from horus import terminal_tui

    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(herdr_host, "available", lambda: False)
    ui = terminal_tui.TerminalUI()
    ui._show("settings")
    rendered = "".join(text for _s, text in ui._body_text() if isinstance(text, str))
    assert "herdr  (not installed here)" in rendered


def test_defaults_screen_shows_what_auto_resolves_to(tmp_path, monkeypatch):
    """`auto` is a recommendation, so the status names the host it actually picked
    — otherwise the owner cannot tell what they just chose."""
    from horus import terminal_tui

    _home(tmp_path, monkeypatch)
    monkeypatch.delenv("HORUS_TERMINAL_TARGET", raising=False)
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    ui = terminal_tui.TerminalUI()
    ui._show("settings")
    offered = [value for kind, value in ui.items if kind == "host"]
    target = (
        len(config.LAUNCH_POSTURE_CHOICES)
        + len(config.LAUNCH_WINDOW_CHOICES)
        + offered.index("auto")
    )
    ui.move(target - ui.selected)
    ui.activate()
    assert "auto (resolves to tmux)" in ui.status


# ---------------------------------------------------------------------------
# Host-selection leaks found in a pre-release sweep (2026-07-29). Each of these
# only bites a machine that opted into a non-default host, which is exactly the
# configuration the herdr work just made possible.
# ---------------------------------------------------------------------------


def test_launch_window_makes_the_host_ready_before_launching(tmp_path, monkeypatch):
    """Bug: `launch_window` skipped `ensure_ready()`, so a herdr window launch died
    on a bare ENOENT from the socket instead of starting the server."""
    _home(tmp_path, monkeypatch)
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "herdr")
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setattr(
        herdr_host.HerdrHost, "ensure_ready", lambda _self: "the herdr server did not come up",
    )
    monkeypatch.setattr(
        herdr_host.HerdrHost, "launch",
        lambda _self, **_k: pytest.fail("must not launch onto a host that is not ready"),
    )
    result = terminal_sessions.launch_window(agent="fake", project_dir=tmp_path)
    assert not result.ok and result.error == "the herdr server did not come up"


def test_browser_terminal_launches_on_the_same_host_it_gated_on(tmp_path, monkeypatch):
    """Bug: pty_host gated on the RESOLVED host's viewer capability but launched via
    the tmux façade, then asked the resolved host for a viewer onto a tmux ref. On a
    herdr-configured machine that returns None and the browser terminal dies."""
    from horus import pty_host

    _home(tmp_path, monkeypatch)
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "herdr")
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host.HerdrHost, "ensure_ready", lambda _self: None)
    monkeypatch.setattr(
        tmux_host.TmuxHost, "launch",
        lambda _self, **_k: pytest.fail("gated on herdr, so it must not launch on tmux"),
    )
    launched = {}
    monkeypatch.setattr(
        herdr_host.HerdrHost, "launch",
        lambda _self, **kwargs: launched.update(kwargs) or LaunchResult(
            True, kwargs["agent"], tmp_path,
            session_id="12345678-1234-1234-1234-123456789abc", target_ref="w1:p1",
        ),
    )
    seen = {}

    def fake_viewer(_self, ref):
        seen["ref"] = ref
        return ["herdr"]

    monkeypatch.setattr(herdr_host.HerdrHost, "viewer_argv", fake_viewer)

    # Reuse the properly-shaped fake: pty_host starts a reader thread, and a
    # half-fake without read() only surfaces as a swallowed thread exception.
    from tests.test_pty_host import _FakePty

    fake = _FakePty()
    monkeypatch.setattr(pty_host, "spawn_pty", lambda *_a, **_k: fake)
    try:
        pty_host.PtyHost().start(agent="fake", project_dir=tmp_path, managed=True)
    finally:
        fake.eof()
    # The viewer was asked for the ref the SAME host produced, not a foreign one.
    assert seen["ref"] == "w1:p1"


def test_detached_workers_follow_the_named_host_not_tmux(tmp_path, monkeypatch):
    """Bug: `launch_detached_run` hardcoded tmux, so `--target herdr` was accepted by
    argparse and then ignored; and the `--detach` guards compared against the literal
    tmux, so a herdr machine could not host a worker at all."""
    _home(tmp_path, monkeypatch)
    from horus.run_executor import RunRequest

    # The guards now ask about persistence, so every persistent host qualifies.
    assert set(terminal_sessions.persistent_hosts()) == {"tmux", "herdr"}
    assert terminal_sessions.hosts_persistently("herdr")
    assert not terminal_sessions.hosts_persistently("current")

    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host.HerdrHost, "ensure_ready", lambda _self: None)
    picked = {}
    monkeypatch.setattr(
        herdr_host.HerdrHost, "launch_worker",
        lambda _self, request, reg=None: picked.setdefault("host", "herdr"),
    )
    monkeypatch.setattr(
        tmux_host.TmuxHost, "launch_worker",
        lambda _self, request, reg=None: pytest.fail("--target herdr must not run on tmux"),
    )
    request = RunRequest(
        session_id="12345678-1234-1234-1234-123456789abc", agent="fake", project=tmp_path,
        prompt="host-selection probe", account=None, posture="auto-edit", model=None,
        effort=None, worker=True, resume=None, dispatch_base_sha=None, dispatch_pending=0,
    )
    terminal_sessions.launch_detached_run(request, target="herdr")
    assert picked["host"] == "herdr"

    # A non-persistent host is refused with a reason rather than silently redirected.
    result = terminal_sessions.launch_detached_run(request, target="current")
    assert not result.ok and "cannot host a detached worker" in result.error


def test_worker_default_host_follows_the_machine_config(monkeypatch):
    """`horus run --unattended` used to default the target to literal tmux, so a
    herdr-configured machine had its workers land on the wrong host."""
    monkeypatch.setattr(tmux_host, "available", lambda: True)
    monkeypatch.setattr(herdr_host, "available", lambda: True)
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("HERDR_ENV", raising=False)

    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "herdr")
    assert terminal_sessions.default_persistent_host() == "herdr"

    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "tmux")
    assert terminal_sessions.default_persistent_host() == "tmux"

    # The resolved host cannot host a worker → fall back to one that can.
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "current")
    assert terminal_sessions.default_persistent_host() in {"tmux", "herdr"}
