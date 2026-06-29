"""Tests for horus.remote_start.onboard_github_project and the CLI `horus onboard`.

No real network or git calls are made:
- ``github_catalog.discover`` is monkeypatched.
- ``remote_start._clone_repo`` is monkeypatched for the clone path.
- ``integration._run`` is monkeypatched so integrate() runs its real logic but
  issues no real git/gh commands.
- ``initialize.init_project`` runs for real in tmp_path (safe file I/O) to give
  genuine coverage of the scaffolding step.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from horus import github_catalog, integration as intmod, remote_start
from horus.remote_start import OnboardResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _untracked(name: str = "my-repo", full_name: str = "acme/my-repo", local_path: str | None = None):
    return github_catalog.UntrackedRepo(
        owner="acme",
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
        description="A test repo",
        local_path=local_path,
    )


def _remote_project(name: str = "my-repo", full_name: str = "acme/my-repo"):
    return github_catalog.RemoteProject(
        owner="acme",
        name=name,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        clone_url=f"git@github.com:{full_name}.git",
        default_branch="main",
        pushed_at="2026-06-28T12:00:00Z",
    )


def _ok(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=stderr)


def _fail(stderr: str = "fatal: something went wrong") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class FakeRunner:
    """Records (cmd, cwd) pairs for integration._run and returns canned results."""

    def __init__(self, responses: list[subprocess.CompletedProcess] | None = None):
        self.calls: list[tuple[list[str], str]] = []
        self._responses = list(responses or [])
        self._index = 0

    def __call__(self, cmd: list[str], cwd) -> subprocess.CompletedProcess:
        self.calls.append((cmd, str(cwd)))
        if self._index < len(self._responses):
            result = self._responses[self._index]
            self._index += 1
            return result
        return _ok()  # default: success


def _automerge_responses(pr_url: str = "https://github.com/acme/my-repo/pull/1"):
    """Canned successes for branch-pr-automerge: checkout, add, commit, push, symbolic-ref, pr create, pr merge."""
    return [
        _ok(),                                  # git checkout -b
        _ok(),                                  # git add <files>
        _ok(),                                  # git commit
        _ok(),                                  # git push -u
        _ok("refs/remotes/origin/main\n"),      # git symbolic-ref
        _ok(pr_url + "\n"),                     # gh pr create
        _ok(""),                                # gh pr merge --auto
    ]


def _policy(integration_mode: str = "branch-pr-automerge") -> dict[str, str]:
    return {"integration": integration_mode, "commit": "auto", "merge": "auto"}


# ---------------------------------------------------------------------------
# Happy path — already-local clone (no clone step needed)
# ---------------------------------------------------------------------------

def test_onboard_already_local_no_clone(tmp_path, monkeypatch):
    """When the untracked repo has local_path, skip cloning and run init + integrate."""
    pr_url = "https://github.com/acme/my-repo/pull/1"
    project_path = tmp_path / "my-repo"
    project_path.mkdir()
    # Create a fake .git dir so we don't need a real git repo for init_project.
    (project_path / ".git").mkdir()

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=str(project_path))]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "load_workspace_root", lambda: str(tmp_path))

    registered_paths: list = []
    monkeypatch.setattr(remote_start.config, "register_project", lambda p: registered_paths.append(p) or True)

    runner = FakeRunner(_automerge_responses(pr_url))
    monkeypatch.setattr(intmod, "_run", runner)

    # Isolate the user HOME so init_project doesn't write to the real ~/.horus/config.toml.
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    result = remote_start.onboard_github_project(
        "github:acme/my-repo",
        policy=_policy(),
    )

    # No clone should have happened.
    assert isinstance(result, OnboardResult)
    assert result.cloned is False
    assert result.path == project_path.resolve()

    # .horus/ must have been scaffolded.
    assert (project_path / ".horus").is_dir()

    # Registered once (by onboard; init_project also calls register_project
    # internally but we've already monkeypatched it).
    assert result.registered is True

    # Integration must be the branch-pr-automerge result.
    assert result.integration.ok is True
    assert result.integration.pr_url == pr_url

    # Init actions should include at least the .horus/ lane files.
    assert len(result.init_actions) > 0


# ---------------------------------------------------------------------------
# Clone path — repo has no local_path
# ---------------------------------------------------------------------------

def test_onboard_clones_when_no_local_path(tmp_path, monkeypatch):
    """When the untracked repo has no local_path, _clone_repo should be called."""
    clone_calls: list = []

    def fake_clone(full_name: str, path: Path) -> bool:
        clone_calls.append((full_name, path))
        # Simulate a real clone: create .git + directory.
        path.mkdir(parents=True, exist_ok=True)
        (path / ".git").mkdir()
        return True

    monkeypatch.setattr(remote_start, "_clone_repo", fake_clone)
    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=None)]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "load_workspace_root", lambda: str(tmp_path))
    monkeypatch.setattr(remote_start.config, "register_project", lambda p: True)

    runner = FakeRunner(_automerge_responses())
    monkeypatch.setattr(intmod, "_run", runner)

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    result = remote_start.onboard_github_project(
        "github:acme/my-repo",
        workspace_root=tmp_path,
        policy=_policy(),
    )

    assert result.cloned is True
    assert len(clone_calls) == 1
    full_name_cloned, path_cloned = clone_calls[0]
    assert full_name_cloned == "acme/my-repo"
    assert path_cloned == tmp_path / "my-repo"


# ---------------------------------------------------------------------------
# Error: repo is already a Horus project
# ---------------------------------------------------------------------------

def test_onboard_raises_if_already_horus_project(tmp_path, monkeypatch):
    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[_remote_project()], untracked=[]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])

    with pytest.raises(RuntimeError, match="already a Horus project"):
        remote_start.onboard_github_project("github:acme/my-repo")


# ---------------------------------------------------------------------------
# Error: repo not found in untracked or projects
# ---------------------------------------------------------------------------

def test_onboard_raises_if_repo_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(projects=[], untracked=[]),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])

    with pytest.raises(RuntimeError, match="no GitHub repo found"):
        remote_start.onboard_github_project("github:acme/my-repo")


# ---------------------------------------------------------------------------
# Error: .horus/ already exists in the clone
# ---------------------------------------------------------------------------

def test_onboard_raises_if_horus_already_exists(tmp_path, monkeypatch):
    project_path = tmp_path / "my-repo"
    project_path.mkdir()
    (project_path / ".horus").mkdir()  # Pre-existing .horus/ — must be rejected.

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=str(project_path))]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])

    with pytest.raises(RuntimeError, match="already has .horus/"):
        remote_start.onboard_github_project("github:acme/my-repo")


# ---------------------------------------------------------------------------
# Integration failure is surfaced as non-ok but onboard still returns a result
# ---------------------------------------------------------------------------

def test_onboard_returns_result_on_integration_failure(tmp_path, monkeypatch):
    """A non-ok integration result must NOT raise — OnboardResult is returned."""
    project_path = tmp_path / "my-repo"
    project_path.mkdir()
    (project_path / ".git").mkdir()

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=str(project_path))]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "load_workspace_root", lambda: str(tmp_path))
    monkeypatch.setattr(remote_start.config, "register_project", lambda p: True)

    # Simulate: checkout ok, add ok, commit ok, push ok, symbolic-ref ok, pr create ok,
    # but gh pr merge --auto fails (common on a brand-new repo with no checks set up).
    pr_url = "https://github.com/acme/my-repo/pull/1"
    runner = FakeRunner([
        _ok(),                              # git checkout -b
        _ok(),                              # git add
        _ok(),                              # git commit
        _ok(),                              # git push -u
        _ok("refs/remotes/origin/main\n"),  # symbolic-ref
        _ok(pr_url + "\n"),                 # gh pr create
        _fail("auto-merge is not supported"),  # gh pr merge --auto fails
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    result = remote_start.onboard_github_project(
        "github:acme/my-repo",
        policy=_policy(),
    )

    # Onboard must succeed even though auto-merge failed.
    assert isinstance(result, OnboardResult)
    assert result.integration.ok is False
    assert "auto-merge" in result.integration.detail
    # PR URL should still be captured because pr create succeeded before merge failed.
    assert result.integration.pr_url == pr_url


# ---------------------------------------------------------------------------
# Integration sequence for branch-pr-automerge — verify the exact git/gh calls
# ---------------------------------------------------------------------------

def test_onboard_integration_command_sequence(tmp_path, monkeypatch):
    """Verify the exact git/gh command sequence for branch-pr-automerge policy."""
    project_path = tmp_path / "my-repo"
    project_path.mkdir()
    (project_path / ".git").mkdir()

    pr_url = "https://github.com/acme/my-repo/pull/99"
    runner = FakeRunner(_automerge_responses(pr_url))
    monkeypatch.setattr(intmod, "_run", runner)

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=str(project_path))]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "load_workspace_root", lambda: str(tmp_path))
    monkeypatch.setattr(remote_start.config, "register_project", lambda p: True)

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    result = remote_start.onboard_github_project(
        "github:acme/my-repo",
        policy=_policy("branch-pr-automerge"),
    )

    assert result.integration.ok is True
    assert result.integration.pr_url == pr_url

    cmds = [c[0] for c in runner.calls]
    # Must include: git checkout -b, git add, git commit, git push -u, gh pr create, gh pr merge.
    assert any(c[:2] == ["git", "checkout"] for c in cmds)
    assert any(c[:2] == ["git", "add"] for c in cmds)
    assert any(c[:2] == ["git", "commit"] for c in cmds)
    assert any(c[:3] == ["git", "push", "-u"] for c in cmds)
    pr_create_cmds = [c for c in cmds if c[:3] == ["gh", "pr", "create"]]
    assert len(pr_create_cmds) == 1
    merge_cmds = [c for c in cmds if c[:3] == ["gh", "pr", "merge"]]
    assert len(merge_cmds) == 1
    assert "--auto" in merge_cmds[0]


# ---------------------------------------------------------------------------
# CLI — cmd_onboard
# ---------------------------------------------------------------------------

def test_cli_onboard_success(tmp_path, monkeypatch):
    """cmd_onboard returns 0 on success and prints a summary."""
    from horus.cli import cmd_onboard
    import argparse

    project_path = tmp_path / "my-repo"
    project_path.mkdir()
    (project_path / ".git").mkdir()

    pr_url = "https://github.com/acme/my-repo/pull/5"
    runner = FakeRunner(_automerge_responses(pr_url))
    monkeypatch.setattr(intmod, "_run", runner)

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=str(project_path))]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "load_workspace_root", lambda: str(tmp_path))
    monkeypatch.setattr(remote_start.config, "register_project", lambda p: True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    args = argparse.Namespace(target="github:acme/my-repo", workspace_root=None, limit=100)
    rc = cmd_onboard(args)
    assert rc == 0


def test_cli_onboard_hard_failure_returns_1(tmp_path, monkeypatch):
    """cmd_onboard returns 1 when a hard error (RuntimeError) occurs."""
    from horus.cli import cmd_onboard
    import argparse

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(projects=[], untracked=[]),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])

    args = argparse.Namespace(target="github:acme/my-repo", workspace_root=None, limit=100)
    rc = cmd_onboard(args)
    assert rc == 1


def test_cli_onboard_integration_failure_returns_0(tmp_path, monkeypatch):
    """cmd_onboard returns 0 even when integration fails (non-hard failure)."""
    from horus.cli import cmd_onboard
    import argparse

    project_path = tmp_path / "my-repo"
    project_path.mkdir()
    (project_path / ".git").mkdir()

    # Integration fails at the push step.
    runner = FakeRunner([
        _ok(),  # checkout -b
        _ok(),  # git add
        _ok(),  # git commit
        _fail("push rejected"),  # push fails
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    monkeypatch.setattr(
        remote_start.github_catalog,
        "discover",
        lambda owner, **kw: github_catalog.DiscoveryResult(
            projects=[], untracked=[_untracked(local_path=str(project_path))]
        ),
    )
    monkeypatch.setattr(remote_start.config, "load_projects", lambda: [])
    monkeypatch.setattr(remote_start.config, "load_workspace_root", lambda: str(tmp_path))
    monkeypatch.setattr(remote_start.config, "register_project", lambda p: True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    args = argparse.Namespace(target="github:acme/my-repo", workspace_root=None, limit=100)
    rc = cmd_onboard(args)
    assert rc == 0  # non-hard failure: push failed but onboard still succeeds
