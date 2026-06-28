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
