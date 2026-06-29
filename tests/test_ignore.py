"""Tests for the per-machine ignored_repos config (Phase A2)."""

from horus import config, github_catalog


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


# ---------------------------------------------------------------------------
# Config: ignored_repos
# ---------------------------------------------------------------------------

def test_ignored_repos_defaults_empty(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_ignored_repos() == []


def test_ignore_adds_and_returns_true(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.ignore_repo("owner/repo") is True
    assert "owner/repo" in config.load_ignored_repos()


def test_ignore_duplicate_returns_false(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/repo")
    assert config.ignore_repo("owner/repo") is False


def test_unignore_present_returns_true(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/repo")
    assert config.unignore_repo("owner/repo") is True
    assert "owner/repo" not in config.load_ignored_repos()


def test_unignore_absent_returns_false(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.unignore_repo("owner/repo") is False


def test_ignore_strips_github_prefix(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("github:owner/repo")
    repos = config.load_ignored_repos()
    assert "owner/repo" in repos
    assert "github:owner/repo" not in repos


def test_ignore_case_variants_of_github_prefix(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("GitHub:owner/repo")
    repos = config.load_ignored_repos()
    assert "owner/repo" in repos


def test_ignore_empty_string_rejected(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.ignore_repo("") is False
    assert config.ignore_repo("  ") is False
    # Stripping "github:" from "github:" leaves an empty string
    assert config.ignore_repo("github:") is False


def test_ignore_preserves_projects_and_owners_and_workflow(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "p1"
    proj.mkdir()
    config.register_project(proj)
    config.register_github_owner("rafaelmjf")
    config.set_workflow_policy(integration="branch-pr-review")

    config.ignore_repo("owner/repo")

    assert config._as_key(proj) in config.load_projects()
    assert "rafaelmjf" in config.load_github_owners()
    assert config.load_workflow_policy()["integration"] == "branch-pr-review"


def test_register_github_owner_preserves_ignored_repos(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/repo")
    config.register_github_owner("rafaelmjf")
    assert "owner/repo" in config.load_ignored_repos()


def test_set_workspace_root_preserves_ignored_repos(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/repo")
    config.set_workspace_root(tmp_path / "ws")
    assert "owner/repo" in config.load_ignored_repos()


def test_set_workflow_policy_preserves_ignored_repos(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/repo")
    config.set_workflow_policy(commit="manual")
    assert "owner/repo" in config.load_ignored_repos()


def test_register_project_preserves_ignored_repos(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/repo")
    proj = tmp_path / "p1"
    proj.mkdir()
    config.register_project(proj)
    assert "owner/repo" in config.load_ignored_repos()


def test_ignore_round_trip_multiple_repos(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/a")
    config.ignore_repo("owner/b")
    repos = config.load_ignored_repos()
    assert "owner/a" in repos
    assert "owner/b" in repos
    config.unignore_repo("owner/a")
    repos = config.load_ignored_repos()
    assert "owner/a" not in repos
    assert "owner/b" in repos


# ---------------------------------------------------------------------------
# filter_ignored helper
# ---------------------------------------------------------------------------

def _make_remote(full_name: str) -> github_catalog.RemoteProject:
    owner, name = full_name.split("/", 1)
    return github_catalog.RemoteProject(
        owner=owner,
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="",
    )


def _make_untracked(full_name: str) -> github_catalog.UntrackedRepo:
    owner, name = full_name.split("/", 1)
    return github_catalog.UntrackedRepo(
        owner=owner,
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="",
    )


def test_filter_ignored_partitions_correctly(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    repos = [_make_remote("owner/a"), _make_remote("owner/b"), _make_remote("owner/c")]
    visible, hidden = github_catalog.filter_ignored(repos, ignored=["owner/b"])
    assert [r.full_name for r in visible] == ["owner/a", "owner/c"]
    assert [r.full_name for r in hidden] == ["owner/b"]


def test_filter_ignored_case_insensitive(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    repos = [_make_remote("Owner/Repo")]
    visible, hidden = github_catalog.filter_ignored(repos, ignored=["owner/repo"])
    assert hidden and hidden[0].full_name == "Owner/Repo"
    assert not visible


def test_filter_ignored_empty_ignored_list(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    repos = [_make_remote("owner/a"), _make_remote("owner/b")]
    visible, hidden = github_catalog.filter_ignored(repos, ignored=[])
    assert len(visible) == 2
    assert len(hidden) == 0


def test_filter_ignored_all_hidden(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    repos = [_make_remote("owner/a")]
    visible, hidden = github_catalog.filter_ignored(repos, ignored=["owner/a"])
    assert not visible
    assert len(hidden) == 1


def test_filter_ignored_uses_config_by_default(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.ignore_repo("owner/b")
    repos = [_make_remote("owner/a"), _make_remote("owner/b")]
    visible, hidden = github_catalog.filter_ignored(repos)
    assert [r.full_name for r in visible] == ["owner/a"]
    assert [r.full_name for r in hidden] == ["owner/b"]


def test_filter_ignored_works_with_untracked_repos(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    repos = [_make_untracked("owner/a"), _make_untracked("owner/b")]
    visible, hidden = github_catalog.filter_ignored(repos, ignored=["owner/a"])
    assert [r.full_name for r in visible] == ["owner/b"]
    assert [r.full_name for r in hidden] == ["owner/a"]
