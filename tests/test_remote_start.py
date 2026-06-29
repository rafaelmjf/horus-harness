from pathlib import Path

import pytest

from horus import github_catalog, remote_start, upgrade


def _remote(local_path=None):
    return github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
        next_prompt="Resume demo",
        local_path=local_path,
    )


def test_start_github_project_clones_registers_and_upgrades(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        dest = Path(cmd[-1])
        (dest / ".git").mkdir(parents=True)
        (dest / ".horus").mkdir()

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    registered = []
    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(projects=[_remote()], untracked=[]),
    )
    monkeypatch.setattr(remote_start.subprocess, "run", fake_run)
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "register_project", lambda path: registered.append(path) or True)
    monkeypatch.setattr(
        remote_start.upgrade,
        "upgrade_project",
        lambda path, apply: [upgrade.UpgradeAction("updated", "refreshed")],
    )

    result = remote_start.start_github_project("github:rafaelmjf/demo", workspace_root=tmp_path)

    assert calls[0][:4] == ["gh", "repo", "clone", "rafaelmjf/demo"]
    assert result.cloned is True
    assert result.path == tmp_path / "demo"
    assert registered == [tmp_path / "demo"]
    assert result.upgrade_actions[0].status == "updated"


def test_start_github_project_reuses_existing_local_clone(tmp_path, monkeypatch):
    project = tmp_path / "demo"
    (project / ".horus").mkdir(parents=True)
    registered = []

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(projects=[_remote(str(project))], untracked=[]),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [str(project)])
    monkeypatch.setattr(remote_start.config, "register_project", lambda path: registered.append(path) or False)
    monkeypatch.setattr(remote_start.upgrade, "upgrade_project", lambda path, apply: [])

    result = remote_start.start_github_project("github:rafaelmjf/demo", workspace_root=tmp_path)

    assert result.cloned is False
    assert result.registered is False
    assert registered == [project]


def test_start_github_project_refuses_non_git_destination(tmp_path, monkeypatch):
    (tmp_path / "demo").mkdir()
    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(projects=[_remote()], untracked=[]),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])

    with pytest.raises(RuntimeError, match="destination already exists"):
        remote_start.start_github_project("github:rafaelmjf/demo", workspace_root=tmp_path)


def test_parse_github_target_requires_owner_and_repo():
    assert remote_start.parse_github_target("github:owner/repo") == ("owner", "repo")
    with pytest.raises(ValueError):
        remote_start.parse_github_target("github:owner")
