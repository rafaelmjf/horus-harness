from unittest.mock import Mock

import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from horus import config, github_catalog, remote_start, terminal_tui


def _isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _remote_project(full_name: str, *, local_path: str | None = None, current_focus: str = "") -> github_catalog.RemoteProject:
    owner, name = full_name.split("/")
    return github_catalog.RemoteProject(
        owner=owner,
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
        current_focus=current_focus,
        local_path=local_path,
    )


def _new_ui(tmp_path, monkeypatch) -> terminal_tui.TerminalUI:
    _isolated_home(tmp_path, monkeypatch)
    inp = create_pipe_input()
    return terminal_tui.TerminalUI(input=inp, output=DummyOutput())


def _project_with_cards(tmp_path, monkeypatch) -> tuple[terminal_tui.TerminalUI, object]:
    """A UI parked on the backlog screen of a project with two cards: one carrying
    the full field set, one missing `tier` entirely."""
    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True)
    (hdir / "full.md").write_text(
        "---\nstatus: open\npriority: now\ntier: sonnet\ntype: feature\n---\n# My card\n",
        encoding="utf-8",
    )
    (hdir / "sparse.md").write_text(
        "---\nstatus: open\ntype: bug\n---\n# Thin card\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(root)])
    inp = create_pipe_input()
    ui = terminal_tui.TerminalUI(input=inp, output=DummyOutput())
    ui.project = root
    ui._show("backlog")
    return ui, root


def test_backlog_rows_are_unchanged_when_no_fields_are_configured(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)

    rendered = "".join(text for _style, text in ui._body_text())

    assert "[feature] My card\n" in rendered  # nothing appended after the title
    assert "     priority now\n" in rendered  # the classic sub-line survives
    assert " · " not in rendered


def test_backlog_rows_render_configured_fields_inline_in_pick_order(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui.backlog_fields = ["tier", "status"]

    rendered = "".join(text for _style, text in ui._body_text())

    assert "[feature] My card · tier sonnet · status open\n" in rendered
    # The card without `tier` omits it cleanly rather than showing a blank slot.
    assert "[bug] Thin card · status open\n" in rendered


def test_inline_priority_replaces_the_priority_sub_line(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui.backlog_fields = ["priority"]

    rendered = "".join(text for _style, text in ui._body_text())

    assert "[feature] My card · priority now\n" in rendered
    assert "     priority now\n" not in rendered  # not repeated below the row


def test_field_picker_offers_every_key_present_on_the_cards(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui._show("backlog_fields")

    assert [value for _kind, value in ui.items] == ["priority", "status", "tier", "type"]

    rendered = "".join(text for _style, text in ui._body_text())
    assert "[ ] tier\n" in rendered
    assert "on 1 of 2 cards · e.g. sonnet" in rendered


def test_field_picker_keeps_a_configured_field_visible_where_no_card_has_it(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui.backlog_fields = ["vision_facet"]
    ui._show("backlog_fields")

    assert "vision_facet" in [value for _kind, value in ui.items]
    rendered = "".join(text for _style, text in ui._body_text())
    assert "[x] vision_facet\n" in rendered
    assert "on no card here" in rendered


def test_toggling_a_field_saves_globally_and_renders_immediately(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui._show("backlog_fields")
    ui.selected = [value for _kind, value in ui.items].index("tier")

    ui.activate()

    assert ui.backlog_fields == ["tier"]
    assert config.load_backlog_fields() == ["tier"]  # persisted, not just in memory
    assert "[x] tier" in "".join(text for _style, text in ui._body_text())
    ui._show("backlog")
    assert "[feature] My card · tier sonnet" in "".join(text for _style, text in ui._body_text())

    # Toggling again removes it, and that removal persists too.
    ui._show("backlog_fields")
    ui.selected = [value for _kind, value in ui.items].index("tier")
    ui.activate()
    assert config.load_backlog_fields() == []


def test_saved_fields_apply_on_the_next_launch(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    config.set_backlog_fields(["type"])

    fresh = terminal_tui.TerminalUI(input=create_pipe_input(), output=DummyOutput())
    fresh.project = ui.project
    fresh._show("backlog")

    assert fresh.backlog_fields == ["type"]
    assert "[feature] My card · type feature" in "".join(text for _style, text in fresh._body_text())


def test_remote_projects_reads_cache_only_and_never_calls_gh(tmp_path, monkeypatch):
    _isolated_home(tmp_path, monkeypatch)

    def _forbidden(*args, **kwargs):
        raise AssertionError("must not shell out to gh for the cached listing")

    monkeypatch.setattr(github_catalog.subprocess, "run", _forbidden)
    monkeypatch.setattr(config, "load_github_owners", lambda: ["rafaelmjf"])
    monkeypatch.setattr(config, "load_projects", lambda: [])

    cloned_local = tmp_path / "cloned-repo"
    cloned_local.mkdir()
    remote_only = _remote_project("rafaelmjf/remote-only")
    cloned_unregistered = _remote_project("rafaelmjf/cloned-repo", local_path=str(cloned_local))
    ignored = _remote_project("rafaelmjf/ignored-repo")

    github_catalog.save_cache("rafaelmjf", [remote_only, cloned_unregistered, ignored])
    monkeypatch.setattr(config, "load_ignored_repos", lambda: ["rafaelmjf/ignored-repo"])

    visible, hidden, errors = terminal_tui._remote_projects()

    assert {p.full_name for p in visible} == {"rafaelmjf/remote-only", "rafaelmjf/cloned-repo"}
    assert [p.full_name for p in hidden] == ["rafaelmjf/ignored-repo"]
    assert errors == []


def test_remote_projects_drops_already_registered(tmp_path, monkeypatch):
    _isolated_home(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "load_github_owners", lambda: ["rafaelmjf"])

    registered = tmp_path / "demo"
    registered.mkdir()
    monkeypatch.setattr(config, "load_projects", lambda: [str(registered)])
    monkeypatch.setattr(
        github_catalog.gitstate,
        "git_state",
        lambda root: {"remote_url": "git@github.com:rafaelmjf/demo.git"},
    )

    already_registered = _remote_project("rafaelmjf/demo")
    github_catalog.save_cache("rafaelmjf", [already_registered])

    visible, hidden, errors = terminal_tui._remote_projects()

    assert visible == []
    assert hidden == []


def test_remote_projects_surfaces_refresh_error(tmp_path, monkeypatch):
    _isolated_home(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "load_github_owners", lambda: ["rafaelmjf"])
    monkeypatch.setattr(config, "load_projects", lambda: [])
    github_catalog.record_cache_error("rafaelmjf", "gh auth required")

    visible, hidden, errors = terminal_tui._remote_projects()

    assert visible == []
    assert len(errors) == 1
    assert "gh auth required" in errors[0]


def test_projects_screen_lists_remote_items_and_renders_distinct_states(tmp_path, monkeypatch):
    ui = _new_ui(tmp_path, monkeypatch)
    cloned_local = tmp_path / "cloned-repo"
    cloned_local.mkdir()
    remote_only = _remote_project("rafaelmjf/remote-only", current_focus="Ship the thing")
    cloned_unregistered = _remote_project("rafaelmjf/cloned-repo", local_path=str(cloned_local))
    ui.remote_projects = [remote_only, cloned_unregistered]
    ui.remote_ignored = [_remote_project("rafaelmjf/ignored-repo")]
    ui.remote_errors = ["rafaelmjf: last refresh failed: gh auth required"]
    ui._refresh_items()

    kinds = [kind for kind, _value in ui.items]
    assert kinds.count("remote_project") == 2

    rendered = "".join(text for _style, text in ui._body_text())
    assert "remote-only · remote only" in rendered
    assert "cloned-repo · cloned, not registered" in rendered
    assert "Ship the thing" in rendered
    assert "1 remote repo hidden via `horus ignore`" in rendered
    assert "Remote catalog unavailable: rafaelmjf: last refresh failed: gh auth required" in rendered


def test_activate_remote_project_exits_with_remote_start(tmp_path, monkeypatch):
    ui = _new_ui(tmp_path, monkeypatch)
    project = _remote_project("rafaelmjf/remote-only")
    ui.remote_projects = [project]
    ui._refresh_items()
    ui.selected = [kind for kind, _v in ui.items].index("remote_project")
    ui.application.exit = Mock()

    ui.activate()

    ui.application.exit.assert_called_once()
    result = ui.application.exit.call_args.kwargs["result"]
    assert isinstance(result, terminal_tui._RemoteStart)
    assert result.project is project


def test_start_remote_reuses_start_github_project_and_reports_clone(monkeypatch, tmp_path):
    project = _remote_project("rafaelmjf/remote-only")
    path = tmp_path / "remote-only"
    calls = []

    def fake_start(target, **kwargs):
        calls.append(target)
        return remote_start.StartResult(project=project, path=path, cloned=True, registered=True, upgrade_actions=[])

    monkeypatch.setattr(remote_start, "start_github_project", fake_start)

    status = terminal_tui._start_remote(terminal_tui._RemoteStart(project))

    assert calls == ["github:rafaelmjf/remote-only"]
    assert "Cloned and registered remote-only" in status
    assert str(path) in status


def test_start_remote_reports_failure_without_raising(monkeypatch):
    project = _remote_project("rafaelmjf/remote-only")

    def fake_start(target, **kwargs):
        raise RuntimeError("gh repo clone failed: boom")

    monkeypatch.setattr(remote_start, "start_github_project", fake_start)

    status = terminal_tui._start_remote(terminal_tui._RemoteStart(project))

    assert "Remote start failed" in status
    assert "boom" in status


# ---------------------------------------------------------------------------
# Backlog tree screen (branch umbrellas + facets) and the receipts shelf
# ---------------------------------------------------------------------------


def _project_with_branch_tree(tmp_path, monkeypatch) -> tuple[terminal_tui.TerminalUI, object]:
    """A UI parked on the backlog screen of a project with one branch umbrella
    (one child) plus one facet-only card, and one dated research receipt."""
    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True)
    (hdir / "umbrella-a.md").write_text(
        "---\nstatus: open\npriority: medium\n---\n"
        "# Umbrella A\n\n## Acceptance\n\n- Converged when it ships.\n",
        encoding="utf-8",
    )
    (hdir / "child-1.md").write_text(
        "---\nstatus: open\npriority: high\ntier: sonnet\nbranch: umbrella-a\n---\n# Child one\n",
        encoding="utf-8",
    )
    (hdir / "lonely.md").write_text(
        '---\nstatus: open\npriority: low\nvision_facet: "Dashboard"\n---\n# Lonely card\n',
        encoding="utf-8",
    )
    rdir = root / ".horus" / "research"
    rdir.mkdir(parents=True)
    (rdir / "2026-07-17-x.md").write_text("# X receipt\n\nbody\n", encoding="utf-8")
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(root)])
    inp = create_pipe_input()
    ui = terminal_tui.TerminalUI(input=inp, output=DummyOutput())
    ui.project = root
    ui._show("backlog")
    return ui, root


def test_backlog_screen_shows_collapsed_branch_and_facet_section(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)

    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["branch", "facet", "card"]  # branch collapsed; facet + its card shown

    rendered = "".join(text for _style, text in ui._body_text())
    assert "Umbrella A (1)" in rendered
    assert "converges: Converged when it ships." in rendered
    assert "Dashboard (1)" in rendered
    assert "[task] Lonely card" in rendered
    assert "Child one" not in rendered  # collapsed umbrella hides its child


def test_selecting_a_branch_expands_it_inline(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui.selected = 0  # the branch header
    assert ui.items[0][0] == "branch"

    ui.activate()

    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["branch", "card", "facet", "card"]
    rendered = "".join(text for _style, text in ui._body_text())
    assert "Child one" in rendered

    # Selecting it again collapses it back.
    ui.selected = 0
    ui.activate()
    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["branch", "facet", "card"]


def test_backlog_screen_with_no_branches_stays_flat(tmp_path, monkeypatch):
    """Forward-readable degrade: a project with no `branch:` keys renders
    exactly like the pre-tree flat card list (no branch/facet headers)."""
    ui, _root = _project_with_cards(tmp_path, monkeypatch)

    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["card", "card"]


def test_project_screen_offers_receipts_entry(tmp_path, monkeypatch):
    ui, root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui._show("project")

    assert ("receipts", None) in ui.items
    rendered = "".join(text for _style, text in ui._body_text())
    assert "Receipts" in rendered
    assert "1 research receipt" in rendered


def test_receipts_screen_lists_newest_first_and_opens_read_only(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui._show("receipts")

    assert [value.title for _kind, value in ui.items] == ["X receipt"]

    ui.selected = 0
    ui.activate()

    assert ui.screen == "receipt"
    rendered = "".join(text for _style, text in ui._body_text())
    assert "X receipt" in rendered
    assert "body" in rendered

    ui.back()
    assert ui.screen == "receipts"


def _project_with_skill_drift(tmp_path, monkeypatch) -> tuple[terminal_tui.TerminalUI, object]:
    """A UI on the skills screen of a project where claude skills are installed with
    one outdated + one unversioned, and codex skills are entirely missing."""
    from horus import skills

    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    (root / ".horus").mkdir(parents=True)
    skills.install_skills(root)  # all claude skills current
    skills.skill_path(skills.SKILLS[0], root).write_text(
        "<!-- horus-skill-version: 0 -->\n", encoding="utf-8"
    )
    skills.skill_path(skills.SKILLS[1], root).write_text("no marker\n", encoding="utf-8")
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(root)])
    inp = create_pipe_input()
    ui = terminal_tui.TerminalUI(input=inp, output=DummyOutput())
    ui.project = root
    ui._load_project_skills()
    return ui, root


def test_project_screen_offers_skills_entry(tmp_path, monkeypatch):
    ui, _root = _project_with_skill_drift(tmp_path, monkeypatch)
    ui._show("project")

    assert ("skills", None) in ui.items
    rendered = "".join(text for _style, text in ui._body_text())
    assert "Skills" in rendered
    assert "outdated" in rendered  # roll-up reflects the drifted claude skill


def test_skills_screen_groups_by_agent_and_shows_per_agent_states(tmp_path, monkeypatch):
    from horus import skills

    ui, _root = _project_with_skill_drift(tmp_path, monkeypatch)
    ui._show("skills")

    # One row per bundled skill, for both agents, straight from skill_states.
    assert len(ui.items) == len(skills.SKILLS) * 2
    assert {state.target for _kind, state in ui.items} == {"claude", "codex"}

    rendered = "".join(text for _style, text in ui._body_text())
    assert "Claude" in rendered and "Codex" in rendered
    assert "outdated (v0 → v" in rendered  # downgraded claude skill
    assert "unversioned / customized" in rendered  # unmarked claude skill
    assert "available, not installed" in rendered  # every codex skill
    assert "installed (v" in rendered
    # Read-only projection: never proposes an overwrite of the customized file.
    assert "never auto-flagged for overwrite" in rendered
    assert "horus upgrade-project --apply --target codex" in rendered

    ui.back()
    assert ui.screen == "project"


def test_launch_prompt_prepends_inline_batch_skill_preamble():
    from pathlib import Path
    from horus import terminal_tui
    launch = terminal_tui._Launch(
        Path("/repo"), "claude", "fresh", None,
        None, None, None, None, "inline-batch",
    )
    prompt = terminal_tui._launch_prompt(launch)
    assert "inline-batch-session" in prompt


def test_launch_prompt_has_no_preamble_for_standard_mode():
    from pathlib import Path
    from horus import terminal_tui
    launch = terminal_tui._Launch(
        Path("/repo"), "claude", "fresh", None,
        None, None, None, None, "standard",
    )
    prompt = terminal_tui._launch_prompt(launch)
    assert "inline-batch-session" not in prompt
    assert prompt == ""  # fresh + standard = today's empty prompt


# --- Machine Control pane (`c`) -------------------------------------------------

def _control_ui(tmp_path, monkeypatch, *, listener=False, keepwarm=None, linger=True, sink="telegram"):
    """A UI on the Control screen with every machine-state read stubbed."""
    from horus import terminal_tui, schedule, activity
    ui = _new_ui(tmp_path, monkeypatch)
    keepwarm = keepwarm or {"personal": False, "work": False}
    monkeypatch.setattr(terminal_tui.schedule, "availability", lambda: schedule.Availability(True, "ok"))
    monkeypatch.setattr(terminal_tui.schedule, "listen_service_installed", lambda: listener)
    monkeypatch.setattr(terminal_tui.schedule, "listen_service_active", lambda: listener)
    monkeypatch.setattr(terminal_tui.schedule, "linger_enabled", lambda: linger)
    monkeypatch.setattr(terminal_tui.schedule, "keepwarm_service_active", lambda alias: keepwarm.get(alias, False))
    monkeypatch.setattr(terminal_tui.warmup, "claude_accounts", lambda: sorted(keepwarm))
    monkeypatch.setattr(terminal_tui.notify, "load_notify_config", lambda: type("C", (), {"sink": sink})())
    monkeypatch.setattr(terminal_tui.envelope, "load_all", lambda: [])
    monkeypatch.setattr(terminal_tui.activity, "collect", lambda limit=8: activity.Activity(armed=[], ran=[]))
    return ui


def _plain(frags) -> str:
    return "".join(text for _style, text in frags)


def test_control_pane_lists_listener_and_per_account_keepwarm(tmp_path, monkeypatch):
    ui = _control_ui(tmp_path, monkeypatch, keepwarm={"personal": True, "work": False})
    ui._show("control")
    kinds = [k for k, _v in ui.items]
    assert kinds.count("ctl_keepwarm") == 2
    assert "ctl_listener" in kinds and "ctl_notify_test" in kinds
    body = _plain(ui._body_text())
    assert "[x] Keep-warm · personal" in body   # active account is checked
    assert "[ ] Keep-warm · work" in body
    assert "notify sink: telegram" in body
    assert "linger: on" in body


def test_control_pane_shows_restart_only_when_listener_active(tmp_path, monkeypatch):
    ui = _control_ui(tmp_path, monkeypatch, listener=False)
    ui._show("control")
    assert "ctl_listener_restart" not in [k for k, _v in ui.items]
    # Bring the listener up and re-load: the restart action appears.
    monkeypatch.setattr(terminal_tui.schedule, "listen_service_active", lambda: True)
    ui._show("control")
    assert "ctl_listener_restart" in [k for k, _v in ui.items]


def test_control_toggle_keepwarm_installs_via_the_primitive(tmp_path, monkeypatch):
    ui = _control_ui(tmp_path, monkeypatch, keepwarm={"personal": False, "work": False})
    ui._show("control")
    calls = []
    monkeypatch.setattr(terminal_tui.schedule, "install_keepwarm_service",
                        lambda **kw: calls.append(kw))
    idx = next(i for i, (k, v) in enumerate(ui.items) if k == "ctl_keepwarm" and v == "personal")
    ui.selected = idx
    ui.activate()
    assert calls and calls[0]["account"] == "personal"
    assert calls[0]["command"] == ("horus", "warmup", "--keep", "--account", "personal")
    assert "Keep-warm on for personal" in ui.status


def test_control_toggle_listener_off_stops_the_service(tmp_path, monkeypatch):
    ui = _control_ui(tmp_path, monkeypatch, listener=True)
    ui._show("control")
    stopped = []
    monkeypatch.setattr(terminal_tui.schedule, "remove_listen_service", lambda: stopped.append(True))
    ui.selected = next(i for i, (k, _v) in enumerate(ui.items) if k == "ctl_listener")
    ui.activate()
    assert stopped and "listener stopped" in ui.status.lower()


def test_control_notify_test_uses_escalate_force(tmp_path, monkeypatch):
    ui = _control_ui(tmp_path, monkeypatch)
    ui._show("control")
    seen = {}
    def _fake_escalate(esc, *, force=False, **kw):
        seen["force"] = force
        return type("R", (), {"describe": lambda self: "delivered via telegram"})()
    monkeypatch.setattr(terminal_tui.notify, "escalate", _fake_escalate)
    ui.selected = next(i for i, (k, _v) in enumerate(ui.items) if k == "ctl_notify_test")
    ui.activate()
    assert seen["force"] is True and "delivered" in ui.status


def test_control_back_returns_to_projects(tmp_path, monkeypatch):
    ui = _control_ui(tmp_path, monkeypatch)
    ui._show("control")
    ui.back()
    assert ui.screen == "projects"
