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
