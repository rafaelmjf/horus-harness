"""Tests for horus.integration — the git/gh workflow helper.

All subprocess calls are monkeypatched via ``horus.integration._run`` so no
real git or GitHub interaction occurs.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from horus import integration as intmod
from horus.integration import IntegrationResult, integrate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=stderr)


def _fail(stderr: str = "fatal: something went wrong") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class FakeRunner:
    """Records every (cmd, cwd) pair and returns canned results."""

    def __init__(self, responses: list[subprocess.CompletedProcess]):
        self.calls: list[tuple[list[str], str]] = []
        self._responses = list(responses)
        self._index = 0

    def __call__(self, cmd: list[str], cwd) -> subprocess.CompletedProcess:
        self.calls.append((cmd, str(cwd)))
        if self._index < len(self._responses):
            result = self._responses[self._index]
            self._index += 1
            return result
        # Default: success with empty output.
        return _ok()


def _policy(**kwargs) -> dict[str, str]:
    base = {"integration": "branch-pr-automerge", "commit": "auto", "merge": "auto"}
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# local-only
# ---------------------------------------------------------------------------

def test_local_only_commit_auto(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok()])  # git add -A, git commit
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="test commit",
                       policy=_policy(integration="local-only"))

    assert isinstance(result, IntegrationResult)
    assert result.ok is True
    assert result.committed is True
    assert result.pushed is False
    assert result.pr_url is None
    assert result.merged is False
    assert result.mode == "local-only"

    # Verify exact command sequence.
    assert runner.calls[0][0] == ["git", "add", "-A"]
    assert runner.calls[1][0] == ["git", "commit", "-m", "test commit"]


def test_local_only_commit_auto_specific_files(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok()])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="add file", files=["README.md"],
                       policy=_policy(integration="local-only"))

    assert result.ok is True
    assert runner.calls[0][0] == ["git", "add", "README.md"]


def test_local_only_commit_manual(tmp_path, monkeypatch):
    runner = FakeRunner([])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="manual commit",
                       policy=_policy(integration="local-only", commit="manual"))

    assert result.ok is True
    assert result.committed is False
    assert result.pushed is False
    # No subprocess calls made.
    assert runner.calls == []


def test_local_only_stage_failure(tmp_path, monkeypatch):
    runner = FakeRunner([_fail("nothing to commit")])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="bad",
                       policy=_policy(integration="local-only"))

    assert result.ok is False
    assert result.committed is False


# ---------------------------------------------------------------------------
# direct-push
# ---------------------------------------------------------------------------

def test_direct_push_auto_commit(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _ok()])  # add, commit, push
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="push it",
                       policy=_policy(integration="direct-push"))

    assert result.ok is True
    assert result.committed is True
    assert result.pushed is True
    assert result.pr_url is None
    assert result.merged is False
    assert runner.calls[0][0] == ["git", "add", "-A"]
    assert runner.calls[1][0] == ["git", "commit", "-m", "push it"]
    assert runner.calls[2][0] == ["git", "push", "origin", "HEAD"]


def test_direct_push_manual_commit(tmp_path, monkeypatch):
    runner = FakeRunner([_ok()])  # only push
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="already committed",
                       policy=_policy(integration="direct-push", commit="manual"))

    assert result.ok is True
    assert result.committed is False
    assert result.pushed is True
    assert runner.calls[0][0] == ["git", "push", "origin", "HEAD"]


def test_direct_push_failure(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _fail("rejected")])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="fail push",
                       policy=_policy(integration="direct-push"))

    assert result.ok is False
    assert result.pushed is False
    assert "rejected" in result.detail


# ---------------------------------------------------------------------------
# branch-pr-review
# ---------------------------------------------------------------------------

def test_branch_pr_review_full_sequence(tmp_path, monkeypatch):
    pr_url = "https://github.com/owner/repo/pull/42"
    runner = FakeRunner([
        _ok(),                              # git checkout -b
        _ok(),                              # git add -A
        _ok(),                              # git commit
        _ok(),                              # git push -u origin branch
        _ok("refs/remotes/origin/main\n"),  # git symbolic-ref (default branch)
        _ok(pr_url + "\n"),                 # gh pr create
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="feature: add widget",
                       policy=_policy(integration="branch-pr-review"))

    assert result.ok is True
    assert result.committed is True
    assert result.pushed is True
    assert result.pr_url == pr_url
    assert result.merged is False
    assert result.branch is not None
    assert result.branch.startswith("horus/")

    # Spot-check the key commands.
    cmds = [c[0] for c in runner.calls]
    assert cmds[0][0:2] == ["git", "checkout"]
    assert cmds[0][2] == "-b"
    assert cmds[3][0:3] == ["git", "push", "-u"]
    # gh pr create must include --base and --head.
    gh_cmd = cmds[5]
    assert gh_cmd[0] == "gh"
    assert "--base" in gh_cmd
    assert "--head" in gh_cmd


def test_branch_pr_review_custom_branch_and_title(tmp_path, monkeypatch):
    runner = FakeRunner([
        _ok(),                      # checkout -b
        _ok(), _ok(),               # add, commit
        _ok(),                      # push
        _ok("refs/remotes/origin/main\n"),  # symbolic-ref
        _ok("https://gh/pr/7\n"),   # gh pr create
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="fix bug",
                       branch="my-custom-branch",
                       title="Fix the big bug",
                       policy=_policy(integration="branch-pr-review"))

    assert result.branch == "my-custom-branch"
    gh_cmd = [c[0] for c in runner.calls if c[0][0] == "gh"][0]
    assert "Fix the big bug" in gh_cmd


def test_branch_pr_review_no_merge_requested(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/main\n"),
                         _ok("https://gh/pr/1\n")])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="review needed",
                       policy=_policy(integration="branch-pr-review"))

    # No gh pr merge call should have been made.
    merge_calls = [c for c in runner.calls if c[0][0:3] == ["gh", "pr", "merge"]]
    assert merge_calls == []
    assert result.merged is False


# ---------------------------------------------------------------------------
# branch-pr-automerge
# ---------------------------------------------------------------------------

def test_branch_pr_automerge_sequence(tmp_path, monkeypatch):
    pr_url = "https://github.com/owner/repo/pull/99"
    runner = FakeRunner([
        _ok(),                              # checkout -b
        _ok(), _ok(),                       # add, commit
        _ok(),                              # push
        _ok("refs/remotes/origin/main\n"),  # symbolic-ref
        _ok(pr_url + "\n"),                 # gh pr create
        _ok(""),                            # gh pr merge --auto
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="auto merge this",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is True
    assert result.pr_url == pr_url
    # auto-merge requested but not yet merged (checks may be pending)
    assert "auto-merge" in result.detail

    merge_calls = [c for c in runner.calls if c[0][0:3] == ["gh", "pr", "merge"]]
    assert len(merge_calls) == 1
    merge_cmd = merge_calls[0][0]
    assert "--auto" in merge_cmd
    assert "--merge" in merge_cmd


def test_branch_pr_automerge_merge_failure_returns_not_ok(tmp_path, monkeypatch):
    pr_url = "https://github.com/owner/repo/pull/5"
    runner = FakeRunner([
        _ok(), _ok(), _ok(), _ok(),
        _ok("refs/remotes/origin/main\n"),
        _ok(pr_url + "\n"),
        _fail("merge not permitted"),
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="fail merge",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is False
    assert "merge not permitted" in result.detail


# ---------------------------------------------------------------------------
# policy loaded from config when not supplied
# ---------------------------------------------------------------------------

def test_integrate_loads_policy_from_config(tmp_path, monkeypatch):
    """When policy=None, integrate() reads from horus config."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    from horus import config as cfg
    cfg.set_workflow_policy(integration="local-only")

    runner = FakeRunner([_ok(), _ok()])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="from config")
    assert result.mode == "local-only"
    assert result.ok is True


# ---------------------------------------------------------------------------
# Slug generation (regression — branch names must be safe)
# ---------------------------------------------------------------------------

def test_slug_strips_special_chars(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/main\n"),
                         _ok("https://gh/pr/3\n")])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="Fix: my feature (v2.0)!",
                       policy=_policy(integration="branch-pr-review"))

    assert result.branch is not None
    # Branch name should not contain spaces or parens.
    assert " " not in result.branch
    assert "(" not in result.branch
    assert ")" not in result.branch
