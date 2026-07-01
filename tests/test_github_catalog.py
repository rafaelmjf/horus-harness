import base64
import json
from pathlib import Path

from horus import github_catalog


def _content(text: str) -> str:
    return json.dumps({"encoding": "base64", "content": base64.b64encode(text.encode()).decode()})


def test_discover_finds_horus_repos_and_matches_local_remote(tmp_path, monkeypatch):
    local = tmp_path / "demo"
    local.mkdir()
    project_md = """---
status: active
current_focus: "Build the thing"
---

# Demo
"""
    roadmap_md = """---
next_action: "Do the next thing"
next_prompt: "Resume the thing"
---

# Roadmap
"""

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        result = Result()
        if cmd[:3] == ["gh", "repo", "list"]:
            result.stdout = json.dumps([
                {
                    "name": "demo",
                    "nameWithOwner": "rafaelmjf/demo",
                    "url": "https://github.com/rafaelmjf/demo",
                    "sshUrl": "git@github.com:rafaelmjf/demo.git",
                    "defaultBranchRef": {"name": "main"},
                    "pushedAt": "2026-06-28T12:00:00Z",
                },
                {
                    "name": "plain",
                    "nameWithOwner": "rafaelmjf/plain",
                    "url": "https://github.com/rafaelmjf/plain",
                    "sshUrl": "git@github.com:rafaelmjf/plain.git",
                    "defaultBranchRef": {"name": "main"},
                    "pushedAt": "2026-06-28T12:00:00Z",
                },
            ])
            return result
        if "repos/rafaelmjf/demo/contents/.horus/project.md" in cmd:
            result.stdout = _content(project_md)
            return result
        if "repos/rafaelmjf/demo/contents/.horus/roadmap.md" in cmd:
            result.stdout = _content(roadmap_md)
            return result
        result.returncode = 1
        result.stderr = "not found"
        return result

    monkeypatch.setattr(github_catalog.subprocess, "run", fake_run)
    monkeypatch.setattr(
        github_catalog.gitstate,
        "git_state",
        lambda root: {"remote_url": "git@github.com:rafaelmjf/demo.git"},
    )

    result = github_catalog.discover("rafaelmjf", local_projects=[str(local)])

    assert len(result.projects) == 1
    assert result.projects[0].full_name == "rafaelmjf/demo"
    assert result.projects[0].current_focus == "Build the thing"
    assert result.projects[0].next_action == "Do the next thing"
    assert result.projects[0].local_path == str(local)
    # plain repo (no .horus/project.md) should appear in untracked
    assert len(result.untracked) == 1
    assert result.untracked[0].full_name == "rafaelmjf/plain"


def test_discover_reports_gh_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "auth required"

        return Result()

    monkeypatch.setattr(github_catalog.subprocess, "run", fake_run)

    try:
        github_catalog.discover("rafaelmjf")
    except RuntimeError as exc:
        assert "auth required" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_cache_round_trips_projects_and_recomputes_local_match(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    local = tmp_path / "demo"
    local.mkdir()
    project = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
        current_focus="Focus",
        next_action="Next",
        next_prompt="Prompt",
        local_path="/old/machine/path",
    )
    monkeypatch.setattr(github_catalog.gitstate, "git_state", lambda root: {"remote_url": "git@github.com:rafaelmjf/demo.git"})

    github_catalog.save_cache("rafaelmjf", [project])
    cached = github_catalog.load_cache("rafaelmjf", local_projects=[str(local)])

    assert cached is not None
    assert cached.fetched_at
    assert cached.error == ""
    assert cached.projects[0].full_name == "rafaelmjf/demo"
    assert cached.projects[0].local_path == str(local)


def test_cache_records_refresh_error_without_dropping_projects(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    project = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="",
    )

    github_catalog.save_cache("rafaelmjf", [project])
    github_catalog.record_cache_error("rafaelmjf", "rate limited")
    cached = github_catalog.load_cache("rafaelmjf")

    assert cached is not None
    assert cached.projects[0].full_name == "rafaelmjf/demo"
    assert cached.error == "rate limited"
    assert cached.error_at


def test_force_refresh_reports_success(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    project = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="",
    )
    monkeypatch.setattr(
        github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(projects=[project], untracked=[]),
    )

    result = github_catalog.force_refresh("rafaelmjf")

    assert result.ok is True
    assert result.count == 1
    assert result.fetched_at


def test_force_refresh_reports_failure_and_keeps_cached_count(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    project = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="",
    )
    github_catalog.save_cache("rafaelmjf", [project])

    def fail(owner, **kw):
        raise RuntimeError("auth required")

    monkeypatch.setattr(github_catalog, "discover", fail)

    result = github_catalog.force_refresh("rafaelmjf")

    assert result.ok is False
    assert result.count == 1
    assert "auth required" in result.error


# ---------------------------------------------------------------------------
# Phase 1A: incremental refresh via pushedAt skip
# ---------------------------------------------------------------------------

_REPO_LIST_RESPONSE = json.dumps([
    {
        "name": "demo",
        "nameWithOwner": "rafaelmjf/demo",
        "url": "https://github.com/rafaelmjf/demo",
        "sshUrl": "git@github.com:rafaelmjf/demo.git",
        "defaultBranchRef": {"name": "main"},
        "pushedAt": "2026-06-28T12:00:00Z",
    },
])

_CACHED_PRIOR = github_catalog.RemoteProject(
    owner="rafaelmjf",
    name="demo",
    full_name="rafaelmjf/demo",
    url="https://github.com/rafaelmjf/demo",
    clone_url="git@github.com:rafaelmjf/demo.git",
    default_branch="main",
    pushed_at="2026-06-28T12:00:00Z",
    current_focus="Cached focus",
    next_action="Cached action",
    next_prompt="Cached prompt",
)


def test_discover_skips_horus_reads_when_pushed_at_unchanged(monkeypatch):
    """(a) Unchanged pushedAt → no .horus/ content calls; cached fields reused."""
    horus_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        result = Result()
        if cmd[:3] == ["gh", "repo", "list"]:
            result.stdout = _REPO_LIST_RESPONSE
            return result
        # Any gh api call for .horus/ content must NOT happen for this repo.
        if "contents/.horus/" in " ".join(cmd):
            horus_calls.append(cmd)
        result.returncode = 1
        result.stderr = "should not be called"
        return result

    monkeypatch.setattr(github_catalog.subprocess, "run", fake_run)
    monkeypatch.setattr(github_catalog.gitstate, "git_state", lambda root: None)

    prior = {_CACHED_PRIOR.full_name: _CACHED_PRIOR}
    result = github_catalog.discover("rafaelmjf", prior=prior)

    # No .horus/ content calls must have been made.
    assert horus_calls == [], f"Unexpected .horus/ API calls: {horus_calls}"

    assert len(result.projects) == 1
    p = result.projects[0]
    assert p.full_name == "rafaelmjf/demo"
    assert p.current_focus == "Cached focus"
    assert p.next_action == "Cached action"
    assert p.next_prompt == "Cached prompt"
    assert p.pushed_at == "2026-06-28T12:00:00Z"


def test_discover_fetches_horus_when_pushed_at_changed(monkeypatch):
    """(b) Changed pushedAt → full .horus/ fetch; freshly-read values returned."""
    fresh_project_md = """---
current_focus: "Fresh focus"
---
"""
    fresh_roadmap_md = """---
next_action: "Fresh action"
next_prompt: "Fresh prompt"
---
"""
    # Live repo list returns a DIFFERENT pushedAt than the cached entry.
    live_repo_list = json.dumps([
        {
            "name": "demo",
            "nameWithOwner": "rafaelmjf/demo",
            "url": "https://github.com/rafaelmjf/demo",
            "sshUrl": "git@github.com:rafaelmjf/demo.git",
            "defaultBranchRef": {"name": "main"},
            "pushedAt": "2026-06-29T08:00:00Z",  # newer than cached
        },
    ])

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        result = Result()
        if cmd[:3] == ["gh", "repo", "list"]:
            result.stdout = live_repo_list
            return result
        if "repos/rafaelmjf/demo/contents/.horus/project.md" in " ".join(cmd):
            result.stdout = _content(fresh_project_md)
            return result
        if "repos/rafaelmjf/demo/contents/.horus/roadmap.md" in " ".join(cmd):
            result.stdout = _content(fresh_roadmap_md)
            return result
        result.returncode = 1
        result.stderr = "not found"
        return result

    monkeypatch.setattr(github_catalog.subprocess, "run", fake_run)
    monkeypatch.setattr(github_catalog.gitstate, "git_state", lambda root: None)

    # Prior entry has the OLD pushedAt.
    prior = {_CACHED_PRIOR.full_name: _CACHED_PRIOR}
    result = github_catalog.discover("rafaelmjf", prior=prior)

    assert len(result.projects) == 1
    p = result.projects[0]
    assert p.current_focus == "Fresh focus"
    assert p.next_action == "Fresh action"
    assert p.next_prompt == "Fresh prompt"
    assert p.pushed_at == "2026-06-29T08:00:00Z"


def test_refresh_cache_passes_prior_from_existing_cache(tmp_path, monkeypatch):
    """(c) refresh_cache() builds prior from on-disk cache and passes it to discover()."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    # Pre-seed an on-disk cache.
    github_catalog.save_cache("rafaelmjf", [_CACHED_PRIOR])

    received_prior: list[dict | None] = []

    def fake_discover(owner, *, local_projects=None, limit=100, prior=None, prior_untracked=None):
        received_prior.append(prior)
        return github_catalog.DiscoveryResult(projects=[_CACHED_PRIOR], untracked=[])

    monkeypatch.setattr(github_catalog, "discover", fake_discover)

    github_catalog.refresh_cache("rafaelmjf")

    assert len(received_prior) == 1
    assert received_prior[0] is not None
    assert "rafaelmjf/demo" in received_prior[0]


def test_refresh_cache_passes_none_prior_when_no_cache(tmp_path, monkeypatch):
    """refresh_cache() passes prior=None when no on-disk cache exists yet."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    received_prior: list[dict | None] = []

    def fake_discover(owner, *, local_projects=None, limit=100, prior=None, prior_untracked=None):
        received_prior.append(prior)
        return github_catalog.DiscoveryResult(projects=[], untracked=[])

    monkeypatch.setattr(github_catalog, "discover", fake_discover)

    github_catalog.refresh_cache("rafaelmjf")

    assert len(received_prior) == 1
    assert received_prior[0] is None


# ---------------------------------------------------------------------------
# Phase A1: untracked-repo discovery + verdict cache
# ---------------------------------------------------------------------------

_REPO_LIST_WITH_UNTRACKED = json.dumps([
    {
        "name": "horus-project",
        "nameWithOwner": "rafaelmjf/horus-project",
        "url": "https://github.com/rafaelmjf/horus-project",
        "sshUrl": "git@github.com:rafaelmjf/horus-project.git",
        "defaultBranchRef": {"name": "main"},
        "pushedAt": "2026-06-28T10:00:00Z",
        "description": "A Horus project",
    },
    {
        "name": "plain-repo",
        "nameWithOwner": "rafaelmjf/plain-repo",
        "url": "https://github.com/rafaelmjf/plain-repo",
        "sshUrl": "git@github.com:rafaelmjf/plain-repo.git",
        "defaultBranchRef": {"name": "main"},
        "pushedAt": "2026-06-28T11:00:00Z",
        "description": "Just a plain repo",
    },
])

_HORUS_PROJECT_MD = """---
current_focus: "A1 focus"
---
"""
_HORUS_ROADMAP_MD = """---
next_action: "A1 action"
next_prompt: "A1 prompt"
---
"""


def _make_fake_run_with_untracked(horus_repo_name: str = "horus-project"):
    """Return a fake subprocess.run that serves one Horus project and one plain repo."""

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        result = Result()
        if cmd[:3] == ["gh", "repo", "list"]:
            result.stdout = _REPO_LIST_WITH_UNTRACKED
            return result
        if f"repos/rafaelmjf/{horus_repo_name}/contents/.horus/project.md" in " ".join(cmd):
            result.stdout = _content(_HORUS_PROJECT_MD)
            return result
        if f"repos/rafaelmjf/{horus_repo_name}/contents/.horus/roadmap.md" in " ".join(cmd):
            result.stdout = _content(_HORUS_ROADMAP_MD)
            return result
        # Any other .horus/ check → 404
        result.returncode = 1
        result.stderr = "not found"
        return result

    return fake_run


def test_discover_returns_untracked_repos_in_second_bucket(monkeypatch):
    """Repos without .horus/project.md appear in result.untracked with description."""
    monkeypatch.setattr(github_catalog.subprocess, "run", _make_fake_run_with_untracked())
    monkeypatch.setattr(github_catalog.gitstate, "git_state", lambda root: None)

    result = github_catalog.discover("rafaelmjf")

    assert len(result.projects) == 1
    assert result.projects[0].full_name == "rafaelmjf/horus-project"

    assert len(result.untracked) == 1
    u = result.untracked[0]
    assert u.full_name == "rafaelmjf/plain-repo"
    assert u.description == "Just a plain repo"
    assert u.pushed_at == "2026-06-28T11:00:00Z"


def test_discover_untracked_fast_path_skips_api_call(monkeypatch):
    """When prior_untracked has a matching pushed_at, no gh api .horus/ call is made."""
    api_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        result = Result()
        if cmd[:3] == ["gh", "repo", "list"]:
            result.stdout = _REPO_LIST_WITH_UNTRACKED
            return result
        if f"repos/rafaelmjf/horus-project/contents/.horus/project.md" in " ".join(cmd):
            result.stdout = _content(_HORUS_PROJECT_MD)
            return result
        if f"repos/rafaelmjf/horus-project/contents/.horus/roadmap.md" in " ".join(cmd):
            result.stdout = _content(_HORUS_ROADMAP_MD)
            return result
        # Track any content API call for plain-repo
        if "contents/.horus/" in " ".join(cmd) and "plain-repo" in " ".join(cmd):
            api_calls.append(cmd)
        result.returncode = 1
        result.stderr = "not found"
        return result

    monkeypatch.setattr(github_catalog.subprocess, "run", fake_run)
    monkeypatch.setattr(github_catalog.gitstate, "git_state", lambda root: None)

    prior_untracked = {
        "rafaelmjf/plain-repo": github_catalog.UntrackedRepo(
            owner="rafaelmjf",
            name="plain-repo",
            full_name="rafaelmjf/plain-repo",
            url="https://github.com/rafaelmjf/plain-repo",
            clone_url="git@github.com:rafaelmjf/plain-repo.git",
            default_branch="main",
            pushed_at="2026-06-28T11:00:00Z",
            description="Just a plain repo",
        )
    }

    result = github_catalog.discover("rafaelmjf", prior_untracked=prior_untracked)

    # No API calls should have been made for plain-repo's .horus/ files
    assert api_calls == [], f"Unexpected API calls for untracked repo: {api_calls}"

    assert len(result.untracked) == 1
    assert result.untracked[0].full_name == "rafaelmjf/plain-repo"
    assert result.untracked[0].description == "Just a plain repo"


def test_discover_untracked_changed_pushed_at_rechecks_and_can_promote(monkeypatch):
    """Changed pushedAt on a previously-untracked repo triggers full fetch.

    If .horus/project.md now exists, the repo moves to .projects.
    """
    # Repo list returns a NEWER pushedAt than what's cached as untracked
    updated_repo_list = json.dumps([
        {
            "name": "plain-repo",
            "nameWithOwner": "rafaelmjf/plain-repo",
            "url": "https://github.com/rafaelmjf/plain-repo",
            "sshUrl": "git@github.com:rafaelmjf/plain-repo.git",
            "defaultBranchRef": {"name": "main"},
            "pushedAt": "2026-06-29T09:00:00Z",  # newer than cached
            "description": "Now a Horus project",
        },
    ])

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stderr = ""
            stdout = ""

        result = Result()
        if cmd[:3] == ["gh", "repo", "list"]:
            result.stdout = updated_repo_list
            return result
        if "repos/rafaelmjf/plain-repo/contents/.horus/project.md" in " ".join(cmd):
            result.stdout = _content(_HORUS_PROJECT_MD)
            return result
        if "repos/rafaelmjf/plain-repo/contents/.horus/roadmap.md" in " ".join(cmd):
            result.stdout = _content(_HORUS_ROADMAP_MD)
            return result
        result.returncode = 1
        result.stderr = "not found"
        return result

    monkeypatch.setattr(github_catalog.subprocess, "run", fake_run)
    monkeypatch.setattr(github_catalog.gitstate, "git_state", lambda root: None)

    # Old cached verdict says it was untracked at the old pushedAt
    prior_untracked = {
        "rafaelmjf/plain-repo": github_catalog.UntrackedRepo(
            owner="rafaelmjf",
            name="plain-repo",
            full_name="rafaelmjf/plain-repo",
            url="https://github.com/rafaelmjf/plain-repo",
            clone_url="git@github.com:rafaelmjf/plain-repo.git",
            default_branch="main",
            pushed_at="2026-06-28T11:00:00Z",  # old — mismatch triggers re-check
            description="Just a plain repo",
        )
    }

    result = github_catalog.discover("rafaelmjf", prior_untracked=prior_untracked)

    # Repo promoted to projects because it now has .horus/project.md
    assert len(result.projects) == 1
    assert result.projects[0].full_name == "rafaelmjf/plain-repo"
    assert result.projects[0].current_focus == "A1 focus"
    assert len(result.untracked) == 0


def test_cache_round_trips_untracked_and_recomputes_local_path(tmp_path, monkeypatch):
    """save_cache + load_cache persists untracked repos; local_path is recomputed on load."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    local = tmp_path / "plain-repo"
    local.mkdir()

    untracked = github_catalog.UntrackedRepo(
        owner="rafaelmjf",
        name="plain-repo",
        full_name="rafaelmjf/plain-repo",
        url="https://github.com/rafaelmjf/plain-repo",
        clone_url="git@github.com:rafaelmjf/plain-repo.git",
        default_branch="main",
        pushed_at="2026-06-28T11:00:00Z",
        description="Just a plain repo",
        local_path="/old/machine/path",
    )

    monkeypatch.setattr(
        github_catalog.gitstate,
        "git_state",
        lambda root: {"remote_url": "git@github.com:rafaelmjf/plain-repo.git"},
    )

    github_catalog.save_cache("rafaelmjf", [], [untracked])
    cached = github_catalog.load_cache("rafaelmjf", local_projects=[str(local)])

    assert cached is not None
    assert len(cached.untracked) == 1
    u = cached.untracked[0]
    assert u.full_name == "rafaelmjf/plain-repo"
    assert u.description == "Just a plain repo"
    assert u.pushed_at == "2026-06-28T11:00:00Z"
    # local_path recomputed from local_projects — not the stale cached value
    assert u.local_path == str(local)


def test_cache_without_untracked_key_loads_as_empty(tmp_path, monkeypatch):
    """Older cache files without the 'untracked' key load as empty list (backward compat)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    # Write a cache file in the old format (no 'untracked' key)
    project = github_catalog.RemoteProject(
        owner="rafaelmjf",
        name="demo",
        full_name="rafaelmjf/demo",
        url="https://github.com/rafaelmjf/demo",
        clone_url="git@github.com:rafaelmjf/demo.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
    )
    github_catalog.save_cache("rafaelmjf", [project])

    # Manually remove the 'untracked' key to simulate an old cache file
    path = github_catalog._cache_path("rafaelmjf")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("untracked", None)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    cached = github_catalog.load_cache("rafaelmjf")
    assert cached is not None
    assert cached.untracked == []
    assert len(cached.projects) == 1


def test_untracked_cache_matches_workspace_clone_when_not_registered(tmp_path, monkeypatch):
    """A repo cloned at workspace_root/<name> but never registered still shows as
    local (the two-machine test found already-cloned repos labeled 'remote only'
    right up until onboarding registered them)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    workspace = tmp_path / "ws"
    clone = workspace / "plain-repo"
    clone.mkdir(parents=True)
    monkeypatch.setattr(github_catalog.config, "load_workspace_root", lambda: str(workspace))
    monkeypatch.setattr(
        github_catalog.gitstate,
        "git_state",
        lambda root: (
            {"remote_url": "git@github.com:rafaelmjf/plain-repo.git"} if Path(root) == clone else {}
        ),
    )

    untracked = github_catalog.UntrackedRepo(
        owner="rafaelmjf",
        name="plain-repo",
        full_name="rafaelmjf/plain-repo",
        url="https://github.com/rafaelmjf/plain-repo",
        clone_url="git@github.com:rafaelmjf/plain-repo.git",
        default_branch="main",
        pushed_at="2026-07-02T00:00:00Z",
    )
    github_catalog.save_cache("rafaelmjf", [], [untracked])

    cached = github_catalog.load_cache("rafaelmjf", local_projects=[])
    assert cached is not None
    u = cached.untracked[0]
    assert u.local_path == str(clone)
    assert u.is_local


def test_untracked_cache_ignores_workspace_dir_with_different_remote(tmp_path, monkeypatch):
    """A same-named workspace directory whose remote points elsewhere must NOT match."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    workspace = tmp_path / "ws"
    (workspace / "plain-repo").mkdir(parents=True)
    monkeypatch.setattr(github_catalog.config, "load_workspace_root", lambda: str(workspace))
    monkeypatch.setattr(
        github_catalog.gitstate,
        "git_state",
        lambda root: {"remote_url": "git@github.com:someone-else/plain-repo.git"},
    )

    untracked = github_catalog.UntrackedRepo(
        owner="rafaelmjf",
        name="plain-repo",
        full_name="rafaelmjf/plain-repo",
        url="https://github.com/rafaelmjf/plain-repo",
        clone_url="git@github.com:rafaelmjf/plain-repo.git",
        default_branch="main",
        pushed_at="2026-07-02T00:00:00Z",
    )
    github_catalog.save_cache("rafaelmjf", [], [untracked])

    cached = github_catalog.load_cache("rafaelmjf", local_projects=[])
    assert cached is not None
    assert cached.untracked[0].local_path is None
