import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput

from horus import backlog, config, github_catalog, remote_start, terminal_tui, usage_snapshot
from horus.cli import main


def _plain(frags) -> str:
    return "".join(fragment[1] for fragment in frags)


def _mouse_event(event_type, button=MouseButton.LEFT) -> MouseEvent:
    return MouseEvent(Point(0, 0), event_type, button, frozenset())


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

    rendered = _plain(ui._body_text())

    assert "[feature] My card\n" in rendered  # nothing appended after the title
    assert "     priority now\n" in rendered  # the classic sub-line survives
    assert "[feature] My card ·" not in rendered


def test_left_click_selects_and_activates_the_clicked_row(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    clicked = next(
        fragment
        for fragment in ui._body_text()
        if len(fragment) == 3 and "Thin card" in fragment[1]
    )

    assert clicked[2](_mouse_event(MouseEventType.MOUSE_UP)) is None
    assert ui.screen == "card"
    assert ui.card is not None and ui.card.title == "Thin card"


def test_only_left_button_release_activates_the_launch_row(tmp_path, monkeypatch):
    ui, root = _project_with_cards(tmp_path, monkeypatch)
    ui.project = root
    ui.pending_mode = "resume"
    ui.pending_account = terminal_tui.LaunchAccount("claude", "personal", None)
    ui._show("launch_form")
    launch = next(
        fragment
        for fragment in ui._body_text()
        if len(fragment) == 3 and fragment[1].strip().endswith("Launch")
    )
    exit_launch = Mock()
    monkeypatch.setattr(ui, "_exit_launch", exit_launch)

    assert launch[2](_mouse_event(MouseEventType.MOUSE_DOWN)) is NotImplemented
    assert launch[2](
        _mouse_event(MouseEventType.MOUSE_UP, MouseButton.RIGHT)
    ) is NotImplemented
    exit_launch.assert_not_called()

    assert launch[2](_mouse_event(MouseEventType.MOUSE_UP)) is None
    exit_launch.assert_called_once_with(ui.pending_account)
    assert ui.items[ui.selected][0] == "launch"


def test_backlog_screen_reports_all_six_readiness_queues(tmp_path, monkeypatch):
    ui, root = _project_with_cards(tmp_path, monkeypatch)
    hdir = root / ".horus" / "backlog"
    (hdir / "full.md").write_text(
        "---\nstatus: open\npriority: now\ntype: feature\n"
        "readiness: ready\nautonomy: eligible\n---\n# My card\n",
        encoding="utf-8",
    )
    (hdir / "blocked.md").write_text(
        "---\nstatus: open\ntype: task\nreadiness: gated\n"
        'readiness_reason: "await upstream"\n---\n# Blocked card\n',
        encoding="utf-8",
    )
    ui._reload_project_backlog(root)
    ui._show("backlog")

    rendered = _plain(ui._body_text())

    assert "Ready—Autonomous eligible 1 · Ready—Attended 0" in rendered
    assert "Shaping 0 · Gated 1 · Deferred 0 · Unclassified 1" in rendered
    assert "Ready—Autonomous eligible\n" in rendered
    assert "Gated\n" in rendered
    assert "await upstream\n" in rendered


def test_readiness_transition_updates_cli_tui_and_scheduler_gate(
    tmp_path, monkeypatch, capsys,
):
    ui, root = _project_with_cards(tmp_path, monkeypatch)
    card_path = root / ".horus" / "backlog" / "full.md"
    (root / ".horus" / "backlog" / "sparse.md").unlink()

    def write_state(*, readiness, autonomy="", reason=""):
        lines = ["---", "status: open", "priority: now", "type: feature"]
        lines.append(f"readiness: {readiness}")
        if autonomy:
            lines.append(f"autonomy: {autonomy}")
        if reason:
            lines.append(f'readiness_reason: "{reason}"')
        lines.extend(["---", "# My card", ""])
        card_path.write_text("\n".join(lines), encoding="utf-8")
        ui._reload_project_backlog(root)
        ui._show("backlog")
        card = terminal_tui.backlog.find_card(root, "full")
        assert card is not None
        return card

    card = write_state(readiness="shaping", reason="needs owner scope")
    assert not terminal_tui.backlog.is_autonomous_candidate(card)
    assert "needs owner scope" in terminal_tui.backlog.autonomy_block_reason(card)
    assert main(["backlog", "list", "--path", str(root)]) == 0
    assert "Shaping (1)" in capsys.readouterr().out
    assert "Shaping\n" in _plain(ui._body_text())

    card = write_state(readiness="ready", autonomy="attended")
    assert not terminal_tui.backlog.is_autonomous_candidate(card)
    assert "owner presence" in terminal_tui.backlog.autonomy_block_reason(card)
    assert main(["backlog", "list", "--path", str(root)]) == 0
    assert "Ready—Attended (1)" in capsys.readouterr().out
    assert "Ready—Attended\n" in _plain(ui._body_text())

    card = write_state(readiness="ready", autonomy="eligible")
    assert terminal_tui.backlog.is_autonomous_candidate(card)
    assert terminal_tui.backlog.autonomy_block_reason(card) == ""
    assert main(["backlog", "list", "--path", str(root)]) == 0
    assert "Ready—Autonomous eligible (1)" in capsys.readouterr().out
    rendered = _plain(ui._body_text())
    assert "Ready—Autonomous eligible\n" in rendered


def test_backlog_rows_render_configured_fields_inline_in_pick_order(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui.backlog_fields = ["tier", "status"]

    rendered = _plain(ui._body_text())

    assert "[feature] My card · tier sonnet · status open\n" in rendered
    # The card without `tier` omits it cleanly rather than showing a blank slot.
    assert "[bug] Thin card · status open\n" in rendered


def test_inline_priority_replaces_the_priority_sub_line(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui.backlog_fields = ["priority"]

    rendered = _plain(ui._body_text())

    assert "[feature] My card · priority now\n" in rendered
    assert "     priority now\n" not in rendered  # not repeated below the row


def test_field_picker_offers_every_key_present_on_the_cards(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui._show("backlog_fields")

    assert [value for _kind, value in ui.items] == ["priority", "status", "tier", "type"]

    rendered = _plain(ui._body_text())
    assert "[ ] tier\n" in rendered
    assert "on 1 of 2 cards · e.g. sonnet" in rendered


def test_field_picker_keeps_a_configured_field_visible_where_no_card_has_it(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui.backlog_fields = ["topic"]
    ui._show("backlog_fields")

    assert "topic" in [value for _kind, value in ui.items]
    rendered = _plain(ui._body_text())
    assert "[x] topic\n" in rendered
    assert "on no card here" in rendered


def test_toggling_a_field_saves_globally_and_renders_immediately(tmp_path, monkeypatch):
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    ui._show("backlog_fields")
    ui.selected = [value for _kind, value in ui.items].index("tier")

    ui.activate()

    assert ui.backlog_fields == ["tier"]
    assert config.load_backlog_fields() == ["tier"]  # persisted, not just in memory
    assert "[x] tier" in _plain(ui._body_text())
    ui._show("backlog")
    assert "[feature] My card · tier sonnet" in _plain(ui._body_text())

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
    assert "[feature] My card · type feature" in _plain(fresh._body_text())


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

    rendered = _plain(ui._body_text())
    assert "remote-only · remote only" in rendered
    assert "cloned-repo · cloned, not registered" in rendered
    assert "Ship the thing" in rendered
    assert "1 remote repo hidden via `horus ignore`" in rendered
    assert "Remote catalog unavailable: rafaelmjf: last refresh failed: gh auth required" in rendered


def test_projects_footer_names_selected_row_action_at_narrow_width(tmp_path, monkeypatch):
    ui = _new_ui(tmp_path, monkeypatch)
    registered = tmp_path / "registered"
    (registered / ".horus").mkdir(parents=True)
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(registered)])
    ui.projects = [registered]
    cloned = _remote_project("rafaelmjf/cloned", local_path=str(tmp_path / "cloned"))
    remote = _remote_project("rafaelmjf/remote")
    ui.remote_projects = [cloned, remote]
    ui._refresh_items()
    monkeypatch.setattr(ui.application.output, "get_size", lambda: Size(rows=40, columns=63))

    for expected, index in (
        ("Enter open", next(i for i, (kind, _value) in enumerate(ui.items) if kind == "project")),
        ("Enter register", next(i for i, (_kind, value) in enumerate(ui.items) if value is cloned)),
        ("Enter clone + register", next(i for i, (_kind, value) in enumerate(ui.items) if value is remote)),
    ):
        ui.selected = index
        assert expected in _footer(ui)


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
# Backlog topic screen and the receipts shelf
# ---------------------------------------------------------------------------


def _project_with_branch_tree(tmp_path, monkeypatch) -> tuple[terminal_tui.TerminalUI, object]:
    """A UI parked on a two-topic backlog plus one dated research receipt."""
    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True)
    (hdir / "umbrella-a.md").write_text(
        "---\nstatus: open\npriority: medium\ntopic: delivery\n---\n"
        "# Umbrella A\n",
        encoding="utf-8",
    )
    (hdir / "child-1.md").write_text(
        "---\nstatus: open\npriority: high\ntier: sonnet\ntopic: delivery\n---\n# Child one\n",
        encoding="utf-8",
    )
    (hdir / "lonely.md").write_text(
        "---\nstatus: open\npriority: low\ntopic: workspace\n---\n# Lonely card\n",
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


def test_backlog_screen_shows_grouped_sections_expanded_by_default(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)

    # Default topic sections render expanded with counted headers.
    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["group", "card", "card", "group", "card"]

    rendered = _plain(ui._body_text())
    assert "workspace (1)" in rendered
    assert "delivery (2)" in rendered
    assert "[task] Lonely card" in rendered
    assert "Child one" in rendered  # expanded by default now shows the child


def test_selecting_a_group_header_collapses_then_expands_it(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui.selected = 0  # the first topic header
    assert ui.items[0][0] == "group"

    ui.activate()  # collapse it
    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["group", "group", "card"]
    rendered = _plain(ui._body_text())
    assert "Child one" not in rendered

    ui.selected = 0
    ui.activate()  # expand it again
    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["group", "card", "card", "group", "card"]


def test_group_by_lens_switch_regroups_and_none_is_flat(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)

    # Switch to the priority lens: 3 distinct priorities -> 3 group sections
    # Every card is a plain card under non-topic lenses.
    ui.backlog_group_by = "priority"
    ui.selected = 0
    ui._refresh_items()
    group_labels = [v.label for k, v in ui.items if k == "group"]
    assert group_labels == ["high", "medium", "low"]

    # `none` lens: a flat card list, no group headers, every card present.
    ui.backlog_group_by = "none"
    ui._refresh_items()
    assert all(kind == "card" for kind, _v in ui.items)
    assert len(ui.items) == 3


def test_backlog_screen_with_only_unsorted_cards_falls_back_to_flat(tmp_path, monkeypatch):
    """One Unsorted bucket has no useful structure, so the list stays flat."""
    ui, _root = _project_with_cards(tmp_path, monkeypatch)

    kinds = [kind for kind, _value in ui.items]
    assert kinds == ["card", "card"]


# ---------------------------------------------------------------------------
# Priority board + readiness filter
# ---------------------------------------------------------------------------


def _board_ui(tmp_path, monkeypatch, *, columns=120):
    """A UI parked on the backlog of a project with a priority + readiness spread,
    board view on, at a wide terminal size."""
    from prompt_toolkit.data_structures import Size
    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True)
    cards = [
        ("hi-ready", "high", "ready", "eligible"),
        ("hi-shaped", "high", "shaping", ""),
        ("med-ready", "medium", "ready", "attended"),
        ("lo-deferred", "low", "deferred", ""),
    ]
    for name, prio, rdy, auto in cards:
        fm = f"---\nstatus: open\npriority: {prio}\ntype: feature\nreadiness: {rdy}\n"
        if auto:
            fm += f"autonomy: {auto}\n"
        fm += "---\n"
        (hdir / f"{name}.md").write_text(fm + f"# {name.title()}\n\nWhy {name} matters.\n", encoding="utf-8")
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(root)])
    inp = create_pipe_input()
    ui = terminal_tui.TerminalUI(input=inp, output=DummyOutput())
    ui.application.output.get_size = lambda: Size(rows=40, columns=columns)
    ui.project = root
    ui.backlog_board = True
    ui._show("backlog")
    return ui, root


def test_board_renders_priority_columns_and_detail_pane_when_wide(tmp_path, monkeypatch):
    ui, _root = _board_ui(tmp_path, monkeypatch)
    assert ui._board_active()
    # one column per non-empty priority (high, medium, low)
    assert len(ui._board_columns) == 3
    rendered = _plain(ui._body_text())
    assert "Priority board" in rendered
    assert "high · 1 ready" in rendered   # only hi-ready is dispatchable
    assert "medium · 1 ready" in rendered
    assert "low · 0 ready" in rendered
    # detail pane (under the rule) shows the selected card's why snippet
    assert "─" in rendered
    assert "Why hi-ready matters." in rendered


def test_clicking_a_card_in_the_wide_board_opens_that_card(tmp_path, monkeypatch):
    ui, _root = _board_ui(tmp_path, monkeypatch)
    clicked = next(
        fragment
        for fragment in ui._body_text()
        if len(fragment) == 3 and "med-ready" in fragment[1]
    )

    assert clicked[2](_mouse_event(MouseEventType.MOUSE_UP)) is None
    assert ui.screen == "card"
    assert ui.card is not None and ui.card.name == "med-ready"


def test_board_falls_back_to_list_when_narrow(tmp_path, monkeypatch):
    ui, _root = _board_ui(tmp_path, monkeypatch, columns=80)
    # board flag is on, but a narrow terminal renders the list instead
    assert not ui._board_active()
    assert ui._board_columns == []


def test_board_2d_navigation_moves_across_and_within_columns(tmp_path, monkeypatch):
    ui, _root = _board_ui(tmp_path, monkeypatch)
    ui.selected = ui._board_columns[0][0]  # top of the high column
    ui._nav("down")
    assert ui.selected == ui._board_columns[0][1]  # down within the column
    ui._nav("right")
    assert ui.selected in ui._board_columns[1]     # over to the medium column


def test_readiness_filter_applies_to_the_board(tmp_path, monkeypatch):
    ui, _root = _board_ui(tmp_path, monkeypatch)
    ui.backlog_filter = "ready"
    ui.selected = 0
    ui._refresh_items()
    names = {v.name for k, v in ui.items if k == "card"}
    assert names == {"hi-ready", "med-ready"}  # only dispatchable cards remain
    # low column is now empty -> dropped, so 2 columns
    assert len(ui._board_columns) == 2


def test_readiness_filter_applies_to_the_list_on_mobile(tmp_path, monkeypatch):
    # The filter's real payoff: it works in the list view too (narrow/mobile).
    ui, _root = _board_ui(tmp_path, monkeypatch, columns=80)
    ui.backlog_group_by = "none"
    ui.backlog_filter = "parked"
    ui._refresh_items()
    names = {v.name for k, v in ui.items if k == "card"}
    assert names == {"lo-deferred"}


def test_vision_view_renders_topic_standings_and_readiness(tmp_path, monkeypatch):
    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    hdir = root / ".horus" / "backlog"
    (hdir / "archive").mkdir(parents=True)
    (root / ".horus" / "PRD.md").write_text(
        "---\nstatus: active\n---\n# demo\n\n## Vision\n\nSeed.\n\n## Backlog\n\nmenu\n",
        encoding="utf-8",
    )
    (hdir / "active.md").write_text(
        "---\nstatus: open\ntopic: continuity\n---\n# Active\n",
        encoding="utf-8",
    )
    (hdir / "archive" / "shipped.md").write_text(
        "---\nstatus: shipped\ntopic: continuity\n---\n# Shipped\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(root)])
    inp = create_pipe_input()
    ui = terminal_tui.TerminalUI(input=inp, output=DummyOutput())
    ui.project = root
    ui._show("vision")

    rendered = "".join(text for line in ui._vision_lines() for _s, text in line)
    assert "Topic standings" in rendered
    assert "continuity" in rendered and "1 open · 1 shipped" in rendered
    assert "Readiness queues" in rendered and "Unclassified:" in rendered
    assert "Facet" not in rendered and "Vision branches" not in rendered


def test_vision_view_is_scroll_only_with_no_selectable_items(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui._show("vision")
    assert ui.items == []
    # down scrolls the read-out rather than moving a selection
    ui._nav("down")
    assert ui.vision_scroll == 1


def test_project_screen_offers_vision_entry(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui._show("project")
    assert ("vision", None) in ui.items


def test_project_screen_offers_receipts_entry(tmp_path, monkeypatch):
    ui, root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui._show("project")

    assert ("receipts", None) in ui.items
    rendered = _plain(ui._body_text())
    assert "Receipts" in rendered
    assert "1 research receipt" in rendered


def test_receipts_screen_lists_newest_first_and_opens_read_only(tmp_path, monkeypatch):
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    ui._show("receipts")

    assert [value.title for _kind, value in ui.items] == ["X receipt"]

    ui.selected = 0
    ui.activate()

    assert ui.screen == "receipt"
    rendered = _plain(ui._body_text())
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
    rendered = _plain(ui._body_text())
    assert "Skills" in rendered
    assert "outdated" in rendered  # roll-up reflects the drifted claude skill


def test_skills_screen_groups_by_agent_and_shows_per_agent_states(tmp_path, monkeypatch):
    from horus import skills

    ui, _root = _project_with_skill_drift(tmp_path, monkeypatch)
    ui._show("skills")

    # One row per skill that belongs in this project, for both agents.
    assert len(ui.items) == len(skills.bundled_for(_root)) * 2
    assert {state.target for _kind, state in ui.items} == {"claude", "codex"}

    rendered = _plain(ui._body_text())
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


def test_fresh_launch_prompt_is_genuinely_empty():
    """Fresh means fresh: nothing injected, so the owner types into an empty session.
    No mode preamble spends a turn announcing a posture before work can start."""
    from pathlib import Path
    from horus import terminal_tui
    launch = terminal_tui._Launch(
        Path("/repo"), "claude", "fresh", None, None, None, None, None, "default",
    )
    assert terminal_tui._launch_prompt(launch) == ""


def test_launch_prompt_loads_only_the_chosen_context(tmp_path):
    """The one launch axis is WHAT CONTEXT is loaded — resume loads the authored
    handoff, fresh loads nothing. Neither carries a session-mode preamble."""
    from horus import terminal_tui

    (tmp_path / ".horus").mkdir()
    (tmp_path / ".horus" / "PRD.md").write_text(
        "---\ncurrent_focus: ship it\nnext_prompt: Pick up the parser work.\n---\n\n# P\n",
        encoding="utf-8",
    )

    resume = terminal_tui._launch_prompt(
        terminal_tui._Launch(tmp_path, "claude", "resume", None, None, None, None, None, "default")
    )
    assert "Pick up the parser work." in resume
    assert "session mode" not in resume.lower()

    fresh = terminal_tui._launch_prompt(
        terminal_tui._Launch(tmp_path, "claude", "fresh", None, None, None, None, None, "default")
    )
    assert fresh == ""


def test_launch_form_is_compact_until_a_row_is_expanded(tmp_path, monkeypatch):
    """Compact review form: one row per setting showing only its selected value, with
    Launch focused by default so the common case costs a single keypress."""
    from horus import terminal_tui
    ui = _new_ui(tmp_path, monkeypatch)
    ui.pending_account = terminal_tui.LaunchAccount("claude", "personal", None)
    ui.pending_mode = "fresh"
    ui._show("launch_form")

    kinds = [kind for kind, _v in ui.items]
    assert kinds == ["launch_row", "launch_row", "launch_row", "save_defaults", "launch"]
    assert ui.items[ui.selected][0] == "launch"

    rendered = _plain(ui._body_text())
    assert "Model" in rendered and "Effort" in rendered and "Permission" in rendered
    assert "Launch" in rendered and "Save as defaults" in rendered
    # Help stays hidden while compact.
    assert "bypass permissions" not in rendered

    ui.launch_expanded = "posture"
    ui._refresh_items()
    rendered = _plain(ui._body_text())
    # ...and appears on demand when the row is entered.
    assert "bypass permissions" in rendered
    assert "(o)" in rendered  # radio marker on the selected alternative


def test_launch_form_preselects_the_saved_agent_profile(tmp_path, monkeypatch):
    from horus import config, terminal_tui
    ui = _new_ui(tmp_path, monkeypatch)
    config.save_launch_profile("claude", {"model": "opus", "effort": "high", "posture": "auto-edit"})

    ui.pending_mode = "fresh"
    ui.project = tmp_path
    ui._show("accounts")
    ui.items = [("account", terminal_tui.LaunchAccount("claude", "personal", None))]
    ui.selected = 0
    ui.activate()

    assert ui.screen == "launch_form"
    assert (ui.pending_model, ui.pending_effort, ui.pending_posture) == ("opus", "high", "auto-edit")


def test_launch_form_save_as_defaults_persists_only_on_request(tmp_path, monkeypatch):
    from horus import config, terminal_tui
    ui = _new_ui(tmp_path, monkeypatch)
    ui.pending_account = terminal_tui.LaunchAccount("codex", "personal", None)
    ui.pending_mode = "fresh"
    ui._show("launch_form")

    # An occasional override alone never rewrites the profile...
    ui._handle_launch_form("model", "gpt-5.6-sol")
    ui._handle_launch_form("effort", "high")
    assert config.load_launch_profile("codex") == {}

    # ...only pressing Save as defaults does.
    ui._handle_launch_form("save_defaults", None)
    saved = config.load_launch_profile("codex")
    assert saved["model"] == "gpt-5.6-sol" and saved["effort"] == "high"


def test_launch_form_back_collapses_a_row_before_leaving(tmp_path, monkeypatch):
    from horus import terminal_tui
    ui = _new_ui(tmp_path, monkeypatch)
    ui.pending_account = terminal_tui.LaunchAccount("claude", "personal", None)
    ui.pending_mode = "fresh"
    ui._show("launch_form")

    ui._handle_launch_form("launch_row", "model")
    assert ui.launch_expanded == "model"

    ui.back()
    assert ui.launch_expanded is None and ui.screen == "launch_form"

    ui.back()
    assert ui.screen == "accounts"


# --- Mission Control (`m`) + Settings (`t`) panes -------------------------------

def _machine_ui(tmp_path, monkeypatch, *, listener=False, keepwarm=None, linger=True,
                sink="telegram", armed=None, ran=None, envelopes=None):
    """A UI with every machine-state read stubbed, for the Mission Control / Settings panes."""
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
    monkeypatch.setattr(terminal_tui.envelope, "load_all", lambda: envelopes or [])
    monkeypatch.setattr(terminal_tui.activity, "collect",
                        lambda limit=8: activity.Activity(armed=armed or [], ran=ran or []))
    return ui


# Settings pane (`t`) — the machine feature toggles

def test_settings_pane_lists_listener_and_per_account_keepwarm(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch, keepwarm={"personal": True, "work": False})
    ui._show("toggles")
    kinds = [k for k, _v in ui.items]
    assert kinds.count("ctl_keepwarm") == 2
    assert "ctl_listener" in kinds and "ctl_notify_test" in kinds
    body = _plain(ui._body_text())
    assert "[x] Keep-warm · personal" in body   # active account is checked
    assert "[ ] Keep-warm · work" in body
    assert "Tokenmaxxing" in body
    assert "sink: telegram" in body


def test_settings_pane_shows_restart_only_when_listener_active(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch, listener=False)
    ui._show("toggles")
    assert "ctl_listener_restart" not in [k for k, _v in ui.items]
    monkeypatch.setattr(terminal_tui.schedule, "listen_service_active", lambda: True)
    ui._show("toggles")
    assert "ctl_listener_restart" in [k for k, _v in ui.items]


def test_settings_toggle_keepwarm_installs_via_the_primitive(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch, keepwarm={"personal": False, "work": False})
    ui._show("toggles")
    calls = []
    monkeypatch.setattr(terminal_tui.schedule, "install_keepwarm_service", lambda **kw: calls.append(kw))
    ui.selected = next(i for i, (k, v) in enumerate(ui.items) if k == "ctl_keepwarm" and v == "personal")
    ui.activate()
    assert calls and calls[0]["account"] == "personal"
    assert calls[0]["command"] == ("horus", "warmup", "--keep", "--account", "personal")
    assert "Keep-warm on for personal" in ui.status


def test_settings_toggle_listener_off_stops_the_service(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch, listener=True)
    ui._show("toggles")
    stopped = []
    monkeypatch.setattr(terminal_tui.schedule, "remove_listen_service", lambda: stopped.append(True))
    ui.selected = next(i for i, (k, _v) in enumerate(ui.items) if k == "ctl_listener")
    ui.activate()
    assert stopped and "listener stopped" in ui.status.lower()


def test_settings_notify_test_uses_escalate_force(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch)
    ui._show("toggles")
    seen = {}
    def _fake_escalate(esc, *, force=False, **kw):
        seen["force"] = force
        return type("R", (), {"describe": lambda self: "delivered via telegram"})()
    monkeypatch.setattr(terminal_tui.notify, "escalate", _fake_escalate)
    ui.selected = next(i for i, (k, _v) in enumerate(ui.items) if k == "ctl_notify_test")
    ui.activate()
    assert seen["force"] is True and "delivered" in ui.status


# Mission Control pane (`m`) — read-mostly observability

def test_mission_pane_is_read_only_and_shows_readiness_and_activity(tmp_path, monkeypatch):
    from horus import activity, schedule
    armed = [schedule.Schedule(id="s1", description="ship a card", when="2026-07-19 09:00:00", command=("horus", "run"))]
    ran = [activity.RanItem("2026-07-18T00:05:00+00:00", "some-card", "claude-work", "b", activity.OK, "delivered")]
    ui = _machine_ui(tmp_path, monkeypatch, linger=True, armed=armed, ran=ran)
    ui._show("mission")
    assert ui.items == []  # read-mostly: no toggles live here
    body = _plain(ui._body_text())
    assert "Execution readiness" in body and "linger: on" in body
    assert "Armed dispatches" in body and "ship a card" in body
    assert "Recent runs" in body and "some-card" in body
    # No feature-toggle text leaks into Mission Control.
    assert "Keep-warm" not in body and "Steering listener" not in body


def test_mission_and_settings_back_returns_to_projects(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch)
    for screen in ("mission", "toggles"):
        ui._show(screen)
        ui.back()
        assert ui.screen == "projects"


def _footer(ui) -> str:
    return "".join(text for _style, text in ui._footer_text())


def test_top_level_footers_advertise_the_mission_and_settings_keys(tmp_path, monkeypatch):
    """The `m` (Mission Control) and `t` (Settings) global keys were reachable but
    invisible — every top-level footer must name them (regression for the missing
    footnotes reported after the m/t panes shipped in #328)."""
    ui = _new_ui(tmp_path, monkeypatch)
    for screen in ("projects", "accounts", "project"):
        ui.screen = screen
        footer = _footer(ui)
        assert "m mission" in footer, f"{screen} footer missing the mission key: {footer!r}"
        assert "t settings" in footer, f"{screen} footer missing the settings key: {footer!r}"


# Home-view usage meters (item 1) — reuse the status bar's bar + capacity band.

def test_usage_meter_lines_color_by_capacity_band():
    from horus import terminal_tui, usage_snapshot
    snap = usage_snapshot.UsageSnapshot(
        percent=23.0, resets_at="22:40", weekly_percent=92.0, weekly_resets_at="Jul 23"
    )
    five, weekly = terminal_tui._usage_meter_lines(snap)
    assert five[0] == "class:usage-ok" and "23%" in five[1] and "█" in five[1]
    assert weekly[0] == "class:usage-high" and "92%" in weekly[1]
    assert "↻ 22:40" in five[1]  # carries the reset


def test_usage_meter_lines_unknown_window_is_a_dim_dash_not_a_zero_bar():
    from horus import terminal_tui, usage_snapshot
    snap = usage_snapshot.UsageSnapshot(percent=None, resets_at=None, weekly_percent=40.0, weekly_resets_at=None)
    five, weekly = terminal_tui._usage_meter_lines(snap)
    assert five == ("class:muted", "5h     --")  # unknown → dash, never a misleading bar
    assert weekly[0] == "class:usage-ok" and "█" in weekly[1]
    # A wholly-missing snapshot is two dashes.
    assert all(style == "class:muted" and text.endswith("--") for style, text in terminal_tui._usage_meter_lines(None))


# Projects grid navigation (item 2) — down/up = row, left/right = column.

def _gt(sel, count, projects, cols, direction):
    from horus import terminal_tui
    return terminal_tui._grid_nav_target(sel, count, projects, cols, direction)


def test_grid_nav_two_columns_down_moves_a_row_not_sideways():
    # 4 projects in 2 cols: [0 1 / 2 3]. Down from 0 → 2 (row below), NOT 1 (sideways).
    assert _gt(0, 4, 4, 2, "down") == 2
    assert _gt(2, 4, 4, 2, "up") == 0
    # Right/left move a column.
    assert _gt(0, 4, 4, 2, "right") == 1
    assert _gt(1, 4, 4, 2, "left") == 0
    # Left with no column to the left → None (caller does Back).
    assert _gt(0, 4, 4, 2, "left") is None
    # Right at the rightmost column stays put.
    assert _gt(1, 4, 4, 2, "right") == 1


def test_grid_nav_falls_into_and_back_out_of_the_single_column_tail():
    # 3 projects (cols=2) then 2 tail items: grid rows [0 1 / 2], tail 3,4.
    # Down off the last grid row drops into the tail (first tail item).
    assert _gt(2, 5, 3, 2, "down") == 3      # from project 2 → tail item 3
    assert _gt(1, 5, 3, 2, "down") == 3      # last project row col1 → tail
    # Up from the first tail item climbs back into the grid (last project).
    assert _gt(3, 5, 3, 2, "up") == 2
    # Within the tail, up/down is linear and left is Back.
    assert _gt(3, 5, 3, 2, "down") == 4
    assert _gt(4, 5, 3, 2, "up") == 3
    assert _gt(3, 5, 3, 2, "left") is None


def test_grid_nav_single_column_is_linear_with_left_as_back():
    # cols=1 (narrow/mobile or any non-projects list): down/up ±1, right no-op, left Back.
    assert _gt(0, 3, 3, 1, "down") == 1
    assert _gt(2, 3, 3, 1, "down") == 2      # clamps at the end
    assert _gt(1, 3, 3, 1, "up") == 0
    assert _gt(1, 3, 3, 1, "right") == 1     # no-op
    assert _gt(1, 3, 3, 1, "left") is None   # Back


def test_project_columns_narrow_vs_wide(tmp_path, monkeypatch):
    from horus import terminal_tui
    ui = _new_ui(tmp_path, monkeypatch)
    ui.screen = "projects"
    assert ui._project_columns(80) == 1     # narrow → single list (mobile)
    assert ui._project_columns(120) == 2    # desktop → two columns
    assert ui._project_columns(240) == 3    # ultra-wide → three, fluid
    ui.screen = "sessions"
    assert ui._project_columns(240) == 1    # non-projects list is always single-column


# Backlog visual guidance (item 3) — branch membership + priority dots.

def test_backlog_group_children_get_tree_connectors_and_priority_dots(tmp_path, monkeypatch):
    from horus import terminal_tui
    ui, _root = _project_with_branch_tree(tmp_path, monkeypatch)
    # Groups are expanded by default, so the umbrella's child is already shown.
    assert ui.items[0][0] == "group"

    frags = ui._body_text()
    rendered = _plain(frags)
    # The child card is nested under the branch with a tree connector...
    assert "└─" in rendered or "├─" in rendered
    assert "Child one" in rendered
    # ...and its priority renders as a colored dot fragment.
    assert any(fragment[0] == "class:prio-high" and "●" in fragment[1] for fragment in frags)
    # The branch header caret + accent style is present.
    assert any(fragment[0] == "class:branch" and "▾" in fragment[1] for fragment in frags) or \
           any(fragment[0] == "class:selected" and "▾" in fragment[1] for fragment in frags)


def test_priority_dot_colors_by_band_and_omits_when_absent():
    from horus import terminal_tui
    assert terminal_tui._priority_dot("high") == ("class:prio-high", "● ")
    assert terminal_tui._priority_dot("Medium") == ("class:prio-medium", "● ")
    assert terminal_tui._priority_dot("low") == ("class:prio-low", "● ")
    assert terminal_tui._priority_dot("") == ("", "")
    assert terminal_tui._priority_dot(None) == ("", "")
    # Unknown priority word still gets a (muted) dot rather than crashing.
    assert terminal_tui._priority_dot("someday")[1] == "● "


# Inline priority picker (item 4) — reprioritize a card without the editor.

def test_backlog_set_priority_writes_frontmatter_in_place(tmp_path):
    from horus import backlog
    card = tmp_path / "c.md"
    card.write_text("---\nstatus: open\npriority: low\ntier: sonnet\n---\n# C\n", encoding="utf-8")
    backlog.set_priority(card, "high")
    assert "priority: high" in card.read_text()
    assert "tier: sonnet" in card.read_text()  # other frontmatter untouched
    import pytest
    with pytest.raises(ValueError):
        backlog.set_priority(card, "sometime")


def test_backlog_set_priority_inserts_when_absent(tmp_path):
    from horus import backlog
    card = tmp_path / "c.md"
    card.write_text("---\nstatus: open\n---\n# C\n", encoding="utf-8")
    backlog.set_priority(card, "medium")
    assert "priority: medium" in card.read_text()


def test_tui_priority_picker_sets_priority_and_returns_to_backlog(tmp_path, monkeypatch):
    from horus import terminal_tui, backlog
    ui, root = _project_with_cards(tmp_path, monkeypatch)  # cards: full (now→) + sparse
    # Park on the backlog, select the first card, open the picker.
    card_index = next(i for i, (k, _v) in enumerate(ui.items) if k == "card")
    ui.selected = card_index
    card = ui.items[card_index][1]
    ui.priority_card = card
    ui._show("card_priority")
    assert [v for _k, v in ui.items] == list(backlog.PRIORITY_CHOICES)
    # Pick 'high' and confirm it writes + returns.
    ui.selected = backlog.PRIORITY_CHOICES.index("high")
    ui.activate()
    assert ui.screen == "backlog"
    assert "priority set to high" in ui.status
    assert "priority: high" in card.path.read_text()
    # The reloaded backlog reflects the new priority.
    assert any(c.name == card.name and c.priority == "high" for c in ui.project_cards[root])


def test_tui_priority_picker_esc_returns_without_writing(tmp_path, monkeypatch):
    from horus import terminal_tui
    ui, _root = _project_with_cards(tmp_path, monkeypatch)
    card = next(v for k, v in ui.items if k == "card")
    before = card.path.read_text()
    ui.priority_card = card
    ui._show("card_priority")
    ui.back()
    assert ui.screen == "backlog"
    assert ui.priority_card is None
    assert card.path.read_text() == before  # nothing written on cancel


# Mission Control: revoked/expired envelopes must not read as live readiness.

class _StubEnv:
    def __init__(self, name, expires, revoked=False, expired=False):
        self.name = name
        self.expires = expires
        self.revoked = revoked
        self._expired = expired

    def is_expired(self, *, today):
        return self._expired


def test_mission_marks_revoked_and_expired_envelopes_not_live(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch, envelopes=[
        _StubEnv("live-one", "2099-01-01"),
        _StubEnv("dead-one", "2099-01-01", revoked=True),
        _StubEnv("old-one", "2020-01-01", expired=True),
    ])
    ui._show("mission")
    body = _plain(ui._body_text())
    # The live one is shown as a standing authorization with a revoke hint.
    assert "envelope live-one · expires 2099-01-01 · revoke:" in body
    # The revoked/expired ones are marked, never rendered as live readiness.
    assert "dead-one · REVOKED — not a live authorization" in body
    assert "old-one · EXPIRED 2020-01-01 — not a live authorization" in body


def test_mission_all_dead_envelopes_reads_as_no_live_envelope(tmp_path, monkeypatch):
    ui = _machine_ui(tmp_path, monkeypatch, envelopes=[
        _StubEnv("dead-one", "2099-01-01", revoked=True),
    ])
    ui._show("mission")
    body = _plain(ui._body_text())
    assert "no live dispatch envelope" in body
    assert "dead-one · REVOKED" in body  # still visible, just not counted live


def test_backlog_pane_o_launches_an_attended_refine_pass(tmp_path, monkeypatch):
    """The one action the card asked for: `o` on the backlog pane hands the whole
    backlog to `backlog-refine` through the SAME accounts -> launch pipeline every
    other launch uses, so nothing about account/model/posture is reimplemented."""
    from horus import terminal_tui

    ui = _new_ui(tmp_path, monkeypatch)
    ui.project = tmp_path
    ui._show("backlog")

    # Drive the real binding, not just the method behind it, so the key stays wired.
    bindings = [b for b in ui.application.key_bindings.bindings if b.keys == ("o",)]
    assert len(bindings) == 1, "the backlog pane's refine key must be registered once"
    binding = bindings[0]
    assert binding.filter(), "must be live on the backlog pane"
    binding.handler(None)

    assert ui.screen == "accounts"
    assert ui.pending_mode == terminal_tui._MODE_REFINE
    assert ui.pending_card is None
    # Not built at the keypress: the prompt reads `gh pr list`, so it is deferred to
    # spawn time where a second of latency is expected.
    assert ui.pending_prompt is None
    assert ui.pending_origin == "backlog"


def test_refine_launch_prompt_is_built_at_spawn_time(tmp_path, monkeypatch):
    from horus import terminal_tui

    (tmp_path / ".horus" / "backlog").mkdir(parents=True)
    (tmp_path / ".horus" / "backlog" / "a-card.md").write_text(
        "---\nstatus: open\npriority: high\nreadiness: ready\nautonomy: eligible\n---\n# A\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(terminal_tui.backlog_refine.integration, "open_prs", lambda root, timeout=0: [])
    monkeypatch.setattr(terminal_tui.backlog_refine.closure, "unmerged_branch_findings", lambda root: [])
    monkeypatch.setattr(terminal_tui.backlog_refine.routines, "freshness_signals", lambda root: [])

    prompt = terminal_tui._launch_prompt(
        terminal_tui._Launch(
            tmp_path, "claude", terminal_tui._MODE_REFINE, None, None, None, None, None, "default",
        )
    )

    assert "`backlog-refine` skill" in prompt
    assert "1 active cards" in prompt


def test_refine_key_is_scoped_to_the_backlog_pane(tmp_path, monkeypatch):
    """`o` must not fire on other screens — the backlog-only bindings are filtered
    precisely so they never shadow a same-letter binding elsewhere."""
    ui = _new_ui(tmp_path, monkeypatch)
    ui.project = tmp_path
    ui._show("project")

    binding = next(b for b in ui.application.key_bindings.bindings if b.keys == ("o",))

    assert not binding.filter()


# --- remote-freshness indicator (tui-remote-freshness-indicator) ---


def _remote_state(**over):
    """A git_state dict with a live upstream, overridable per key."""
    state = {
        "branch": "main",
        "commit": {"hash": "abc1234", "rel": "1 hour ago", "subject": "x"},
        "dirty": False,
        "upstream": "origin/main",
        "behind": 0,
        "ahead": 0,
        "remote_url": "git@github.com:o/r.git",
        "detached": False,
        "own_upstream_gone": False,
        "default_branch": "main",
        "default_ahead": 0,
        "default_behind": 0,
    }
    state.update(over)
    return state


def _home_with_project(tmp_path, monkeypatch, state):
    """A UI parked on the projects (home) screen for one project whose git_state is
    fixed to ``state`` (any callable receives the project path)."""
    _isolated_home(tmp_path, monkeypatch)
    root = tmp_path / "demo"
    (root / ".horus" / "backlog").mkdir(parents=True)
    monkeypatch.setattr(terminal_tui.config, "load_projects", lambda: [str(root)])
    resolve = state if callable(state) else (lambda _root: state)
    monkeypatch.setattr(terminal_tui.gitstate, "git_state", resolve)
    inp = create_pipe_input()
    ui = terminal_tui.TerminalUI(input=inp, output=DummyOutput())
    return ui, root


def test_project_row_shows_behind_when_behind_origin(tmp_path, monkeypatch):
    ui, _root = _home_with_project(tmp_path, monkeypatch, _remote_state(behind=3))
    rendered = _plain(ui._body_text())
    assert "behind 3 · not fetched" in rendered


def test_project_row_shows_current_when_up_to_date(tmp_path, monkeypatch):
    ui, _root = _home_with_project(tmp_path, monkeypatch, _remote_state(behind=0))
    rendered = _plain(ui._body_text())
    assert "current · not fetched" in rendered


def test_clicking_a_project_in_the_wide_grid_opens_it(tmp_path, monkeypatch):
    ui, root = _home_with_project(tmp_path, monkeypatch, _remote_state())
    ui.application.output.get_size = lambda: Size(rows=40, columns=120)
    clicked = next(
        fragment
        for fragment in ui._body_text()
        if len(fragment) == 3 and "demo" in fragment[1]
    )

    assert clicked[2](_mouse_event(MouseEventType.MOUSE_UP)) is None
    assert ui.screen == "project"
    assert ui.project == root


def test_local_only_repo_shows_no_freshness_token(tmp_path, monkeypatch):
    state = _remote_state(upstream=None, remote_url=None, default_behind=0)
    ui, _root = _home_with_project(tmp_path, monkeypatch, state)
    rendered = _plain(ui._body_text())
    assert "behind" not in rendered
    assert "current ·" not in rendered


def test_branch_without_upstream_falls_back_to_default_divergence(tmp_path, monkeypatch):
    state = _remote_state(upstream=None, behind=None, default_behind=2)
    ui, _root = _home_with_project(tmp_path, monkeypatch, state)
    rendered = _plain(ui._body_text())
    assert "behind 2 · not fetched" in rendered


def test_g_key_fetches_the_fleet_and_refreshes_freshness(tmp_path, monkeypatch):
    """The real `g` binding must fetch every project (read-only) then re-read
    freshness — behind-before, current-after, with a spoken status line."""
    holder = {"behind": 5}
    fetched = []

    def fake_fetch(root, *, timeout=10.0):
        fetched.append(root)
        holder["behind"] = 0  # simulate the fast-forward the fetch enables
        return True

    ui, root = _home_with_project(
        tmp_path, monkeypatch, lambda _root: _remote_state(behind=holder["behind"])
    )
    monkeypatch.setattr(terminal_tui.fetchcheck, "fetch", fake_fetch)
    monkeypatch.setattr(terminal_tui.fetchcheck, "note_fetch", lambda root, ok: None)

    before = _plain(ui._body_text())
    assert "behind 5 · not fetched" in before

    binding = next(b for b in ui.application.key_bindings.bindings if b.keys == ("g",))
    assert binding.filter(), "g must be live on the projects screen"
    binding.handler(None)

    assert fetched == [root], "every registered project is fetched exactly once"
    assert "Fetched 1 project(s)" in ui.status and "all current" in ui.status
    after = _plain(ui._body_text())
    assert "current · just now" in after


def test_g_key_is_inert_off_the_projects_screen(tmp_path, monkeypatch):
    """`g` must never fetch from another screen — the network touch is projects-only."""
    fetched = []
    ui, _root = _home_with_project(tmp_path, monkeypatch, _remote_state(behind=1))
    monkeypatch.setattr(
        terminal_tui.fetchcheck, "fetch", lambda root, **_k: fetched.append(root) or True
    )
    ui._show("sessions")

    binding = next(b for b in ui.application.key_bindings.bindings if b.keys == ("g",))
    binding.handler(None)

    assert fetched == []


# --- inbound Sync action (cockpit-sync-action) ---


def _select_project_row(ui):
    ui.selected = next(i for i, (kind, _v) in enumerate(ui.items) if kind == "project")


def _drive(ui, key):
    binding = next(b for b in ui.application.key_bindings.bindings if b.keys == (key,))
    binding.handler(None)
    return binding


def test_y_fast_forwards_the_selected_project(tmp_path, monkeypatch):
    holder = {"behind": 3}
    ff_calls = []

    def fake_ff(root, upstream, *, timeout=30.0):
        ff_calls.append((root, upstream))
        holder["behind"] = 0  # the fast-forward lands
        return True, "Fast-forwarded to origin/main"

    ui, root = _home_with_project(
        tmp_path, monkeypatch, lambda _root: _remote_state(behind=holder["behind"])
    )
    monkeypatch.setattr(terminal_tui.sync, "fast_forward", fake_ff)
    _select_project_row(ui)

    _drive(ui, "y")

    assert ff_calls == [(root, "origin/main")], "fast_forward runs once, on the real upstream"
    assert "synced →" in ui.status
    assert "current · " in _plain(ui._body_text())


def test_y_refuses_a_dirty_project_without_mutating(tmp_path, monkeypatch):
    ff_calls = []
    ui, _root = _home_with_project(
        tmp_path, monkeypatch, _remote_state(behind=3, dirty=True)
    )
    monkeypatch.setattr(
        terminal_tui.sync, "fast_forward", lambda *a, **k: ff_calls.append(a) or (True, "")
    )
    _select_project_row(ui)

    _drive(ui, "y")

    assert ff_calls == [], "a dirty tree is never fast-forwarded"
    assert "sync refused" in ui.status and "uncommitted" in ui.status


def test_y_on_a_non_project_row_explains_itself(tmp_path, monkeypatch):
    ui, _root = _home_with_project(tmp_path, monkeypatch, _remote_state(behind=1))
    ui.selected = next(i for i, (kind, _v) in enumerate(ui.items) if kind != "project")

    _drive(ui, "y")

    assert "Move to a project row" in ui.status


def test_capital_y_syncs_every_clean_behind_project(tmp_path, monkeypatch):
    _isolated_home(tmp_path, monkeypatch)
    behind_root = tmp_path / "behind"
    dirty_root = tmp_path / "dirty"
    for root in (behind_root, dirty_root):
        (root / ".horus" / "backlog").mkdir(parents=True)
    monkeypatch.setattr(
        terminal_tui.config, "load_projects", lambda: [str(behind_root), str(dirty_root)]
    )
    states = {
        behind_root: _remote_state(behind=2),
        dirty_root: _remote_state(behind=2, dirty=True),
    }
    monkeypatch.setattr(terminal_tui.gitstate, "git_state", lambda root: states[Path(root)])
    synced = []
    monkeypatch.setattr(
        terminal_tui.sync,
        "fast_forward",
        lambda root, upstream, **k: (synced.append(root), (True, "ff"))[1],
    )
    ui = terminal_tui.TerminalUI(input=create_pipe_input(), output=DummyOutput())

    _drive(ui, "Y")

    assert synced == [behind_root], "only the clean-behind project is fast-forwarded"
    assert "1 synced" in ui.status and "1 skipped" in ui.status


def test_sync_keys_are_inert_off_the_projects_screen(tmp_path, monkeypatch):
    ff_calls = []
    ui, _root = _home_with_project(tmp_path, monkeypatch, _remote_state(behind=1))
    monkeypatch.setattr(
        terminal_tui.sync, "fast_forward", lambda *a, **k: ff_calls.append(a) or (True, "")
    )
    ui._show("sessions")

    _drive(ui, "y")
    _drive(ui, "Y")

    assert ff_calls == []


def test_agent_models_prefers_config_over_adapter_default(tmp_path, monkeypatch):
    _isolated_home(tmp_path, monkeypatch)
    # No config → the adapter default (bare families + the pinned comparison models).
    default = terminal_tui._agent_models("claude")
    assert "opus" in default and "claude-opus-4-8" in default and "claude-opus-5" in default
    # An owner-curated [launch_models] list wins outright.
    terminal_tui.config.set_launch_models("claude", ["claude-opus-5", "claude-opus-4-8"])
    assert terminal_tui._agent_models("claude") == ["claude-opus-5", "claude-opus-4-8"]
    # Unknown agent stays empty, never raises.
    assert terminal_tui._agent_models("nope") == []


def test_fmt_age_and_freshness_token_units():
    import time as _t

    assert terminal_tui._fmt_age(None) == "not fetched"
    assert terminal_tui._fmt_age(_t.time()) == "just now"
    assert terminal_tui._fmt_age(_t.time() - 300) == "5m ago"
    assert terminal_tui._fmt_age(_t.time() - 7200) == "2h ago"

    assert terminal_tui._freshness_token(None, None) is None
    style, text = terminal_tui._freshness_token(_remote_state(detached=True), None)
    assert style == "class:warning" and text.startswith("detached ·")
    style, text = terminal_tui._freshness_token(_remote_state(behind=4), None)
    assert style == "class:warning" and text.startswith("behind 4 ·")
    style, text = terminal_tui._freshness_token(_remote_state(behind=0), None)
    assert style == "class:ok" and text.startswith("current ·")


def _vanished_tmux_record():
    """A vanished session shaped as `reconcile()` actually leaves it.

    `target_ref` is the load-bearing detail: a tmux-hosted session keeps its
    pane name in the row after the pane is gone, so any check that asks whether
    the STRING exists still says "attachable" long after there is nothing to
    attach to.
    """
    from horus.registry import SessionRecord

    return SessionRecord(
        session_id="dddddddd-1111-2222-3333-444444444444",
        agent="claude",
        project="/tmp/proj",
        status="stale",
        launch_target="tmux",
        target_ref="horus-dddddddd-111",
        termination_reason="vanished",
        agent_session_id="thread-42",
    )


def test_a_vanished_session_offers_restore_even_though_its_target_ref_survives(tmp_path, monkeypatch):
    """The session screen must offer Restore for a vanished row.

    Found by a live probe on 2026-07-30: the sessions list labelled the row
    "vanished — restorable" and the detail screen then offered Attach/Close and
    no Restore, because `is_attachable()` only asks whether a `target_ref`
    string is present — and a dead tmux session keeps one. The unit fixtures
    left `target_ref` unset, so they agreed with the code instead of with
    reality.
    """
    ui = _new_ui(tmp_path, monkeypatch)
    record = _vanished_tmux_record()

    assert terminal_tui.terminal_sessions.is_restorable(record) is True

    ui.screen = "session"
    ui.selected_session = record
    ui._refresh_items()

    kinds = [kind for kind, _value in ui.items]
    assert "restore" in kinds, f"vanished session offered {kinds}, not a restore"
    assert "attach" not in kinds, "a session that vanished has nothing to attach to"


def _card(root: Path, name: str, *, status: str = "open", type: str = "feature") -> None:
    d = root / ".horus" / "backlog"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text(
        f"---\nstatus: {status}\npriority: medium\ntype: {type}\n---\n# {name}\n",
        encoding="utf-8",
    )


def test_fleet_row_counts_actionable_work_not_the_whole_backlog(tmp_path):
    """A project row reports what is ACTIONABLE, not every non-shipped card.

    This filtered a hand-written ``{"done", "shipped"}`` literal — the third and
    least complete copy of the inactive-status list — so `retired`, `folded-in`
    and `shelved` cards all counted as open work. On this repo that rendered
    "75" while two cards were actually actionable: the row was counting the box
    along with the queue, which is the impression the number is supposed to give
    correctly.
    """
    _card(tmp_path, "live-one")
    _card(tmp_path, "live-bug", type="bug")
    _card(tmp_path, "boxed", status=backlog.SHELVED_STATUS)
    _card(tmp_path, "killed", status="retired")
    _card(tmp_path, "absorbed", status="folded-in")
    _card(tmp_path, "delivered", status="shipped")

    cards = terminal_tui._active_cards(tmp_path)
    assert sorted(c.name for c in cards) == ["live-bug", "live-one"]

    count, bugs = terminal_tui._backlog_metrics(tmp_path, cards)
    assert (count, bugs) == (2, 1)


def test_active_card_filter_has_no_status_list_of_its_own(tmp_path):
    """The TUI must not re-derive which statuses are inactive.

    Three copies of this list existed on 2026-08-01 (`backlog`, `fleet_review`,
    here) and only one was complete. Adding a status to `backlog` must change
    every surface at once, or a card silently counts as open in one view and not
    another.
    """
    for status in backlog.INACTIVE_STATUSES:
        _card(tmp_path, f"x-{status}", status=status)
    _card(tmp_path, "the-only-live-one")

    assert [c.name for c in terminal_tui._active_cards(tmp_path)] == ["the-only-live-one"]


# --------------------------------------------------------------------------- #
# Live all-accounts usage refresh (`U`)
# --------------------------------------------------------------------------- #

def _usage_accounts() -> list:
    return [
        terminal_tui.LaunchAccount("claude", "work", None),
        terminal_tui.LaunchAccount("claude", "personal", None),
        terminal_tui.LaunchAccount("codex", "personal", None),
    ]


def test_live_usage_refresh_reads_every_account_not_just_the_selected_one(monkeypatch):
    """`U` exists because usage is spent on other machines and the native apps.

    A refresh that only covered the highlighted row would leave exactly the stale
    readings the key was added to fix, so assert every configured account is hit.
    """
    seen = []
    monkeypatch.setattr(
        terminal_tui.usage_snapshot, "refresh_usage",
        lambda agent, account, **kw: seen.append((agent, account)),
    )
    monkeypatch.setattr(terminal_tui, "_account_usage", lambda accounts: {})

    terminal_tui._refresh_all_account_usage(_usage_accounts())

    assert sorted(seen) == [
        ("claude", "personal"), ("claude", "work"), ("codex", "personal"),
    ]


def test_live_usage_refresh_survives_one_account_failing(monkeypatch):
    """One unreachable account must not cost the other accounts their refresh.

    `refresh_usage` is best-effort per target; a raising target is reported as
    "kept its cached reading", never propagated into the frame.
    """
    def _flaky(agent, account, **kw):
        if account == "work":
            raise RuntimeError("network down")
        return usage_snapshot.UsageSnapshot(10.0, None)

    monkeypatch.setattr(terminal_tui.usage_snapshot, "refresh_usage", _flaky)
    monkeypatch.setattr(terminal_tui, "_account_usage", lambda accounts: {})

    _usage, fresh, stale = terminal_tui._refresh_all_account_usage(_usage_accounts())

    assert (fresh, stale) == (2, 0)  # the two that answered; the raiser is absorbed


def test_live_usage_refresh_reports_partial_success_honestly(tmp_path, monkeypatch):
    """A partial refresh must not read as a full one.

    The whole point of the key is trusting the number on screen, so a run where
    only some accounts answered has to say so rather than claiming success.
    """
    ui = _new_ui(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_tui, "_launch_accounts", _usage_accounts)
    monkeypatch.setattr(
        terminal_tui, "_refresh_all_account_usage", lambda accounts, **kw: ({}, 2, 0)
    )

    ui.refresh_account_usage_live()

    assert "2 current" in ui.status
    assert "1 kept cached" in ui.status


def test_cheap_usage_key_still_never_touches_the_network(tmp_path, monkeypatch):
    """`u` stays cache-only; only `U` is allowed to fetch.

    They are one keystroke apart, so a refactor that quietly promoted `u` to a
    network read would add an unexpected stall to a key pressed constantly.
    """
    ui = _new_ui(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_tui, "_launch_accounts", _usage_accounts)

    def _forbidden(*a, **kw):
        raise AssertionError("`u` must not perform a live usage read")

    monkeypatch.setattr(terminal_tui.usage_snapshot, "refresh_usage", _forbidden)

    ui.refresh_account_usage()

    assert "cache" in ui.status


def test_shift_u_binding_dispatches_the_live_refresh_from_any_screen(tmp_path, monkeypatch):
    """The binding itself must be wired, and must work off the accounts screen.

    The direct-method tests above would all still pass if `U` were never bound,
    and usage staleness is noticed from wherever the owner happens to be — so
    unlike `g`, this key is deliberately not screen-gated.
    """
    ui = _new_ui(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_tui, "_launch_accounts", _usage_accounts)
    called = []
    monkeypatch.setattr(
        terminal_tui, "_refresh_all_account_usage",
        lambda accounts, **kw: called.append(len(accounts)) or ({}, len(accounts), 0),
    )
    ui._show("sessions")

    _drive(ui, "U")

    assert called == [3], "U must refresh all three accounts from the sessions screen"
    assert "3 account(s)" in ui.status


def test_an_idle_codex_reading_is_not_reported_as_current(monkeypatch):
    """A refresh that returns a stale capture must be counted apart from a live one.

    Refreshing Claude is an OAuth read; refreshing Codex only re-reads the newest
    local rollout, which is hours old whenever that account has been idle and is
    blind to other machines. Calling both "refreshed" is what let a stale reading
    hard-refuse a valid dispatch (2026-07-23) — the bug this split exists to avoid.
    """
    old = time.time() - 3 * 3600  # older than REFUSAL_MAX_READING_AGE (2h)

    def _by_agent(agent, account, **kw):
        if agent == "codex":
            return usage_snapshot.UsageSnapshot(80.0, None, None, None, old)
        return usage_snapshot.UsageSnapshot(10.0, None)  # no capture stamp = live read

    monkeypatch.setattr(terminal_tui.usage_snapshot, "refresh_usage", _by_agent)
    monkeypatch.setattr(terminal_tui, "_account_usage", lambda accounts: {})

    _usage, fresh, stale = terminal_tui._refresh_all_account_usage(_usage_accounts())

    assert (fresh, stale) == (2, 1), "the idle Codex capture must not count as current"


def test_status_names_the_older_capture_instead_of_claiming_success(tmp_path, monkeypatch):
    """The owner reads this line to decide whether to trust the numbers on screen."""
    ui = _new_ui(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_tui, "_launch_accounts", _usage_accounts)
    monkeypatch.setattr(
        terminal_tui, "_refresh_all_account_usage", lambda accounts, **kw: ({}, 2, 1)
    )

    ui.refresh_account_usage_live()

    assert "2 current" in ui.status
    assert "older capture" in ui.status
