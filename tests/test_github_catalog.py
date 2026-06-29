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

    projects = github_catalog.discover("rafaelmjf", local_projects=[str(local)])

    assert len(projects) == 1
    assert projects[0].full_name == "rafaelmjf/demo"
    assert projects[0].current_focus == "Build the thing"
    assert projects[0].next_action == "Do the next thing"
    assert projects[0].local_path == str(local)


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
    monkeypatch.setattr(github_catalog, "discover", lambda owner, **kw: [project])

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
    projects = github_catalog.discover("rafaelmjf", prior=prior)

    # No .horus/ content calls must have been made.
    assert horus_calls == [], f"Unexpected .horus/ API calls: {horus_calls}"

    assert len(projects) == 1
    p = projects[0]
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
    projects = github_catalog.discover("rafaelmjf", prior=prior)

    assert len(projects) == 1
    p = projects[0]
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

    def fake_discover(owner, *, local_projects=None, limit=100, prior=None):
        received_prior.append(prior)
        return [_CACHED_PRIOR]

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

    def fake_discover(owner, *, local_projects=None, limit=100, prior=None):
        received_prior.append(prior)
        return []

    monkeypatch.setattr(github_catalog, "discover", fake_discover)

    github_catalog.refresh_cache("rafaelmjf")

    assert len(received_prior) == 1
    assert received_prior[0] is None
