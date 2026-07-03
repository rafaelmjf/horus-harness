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
        _fail("merge not permitted"),   # gh pr merge --auto
        _fail("Branch not protected"),  # required-checks probe → none
        _fail("still not permitted"),   # direct-merge fallback also refused
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="fail merge",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is False
    assert "merge not permitted" in result.detail
    assert "still not permitted" in result.detail


def test_branch_pr_automerge_falls_back_to_direct_merge(tmp_path, monkeypatch):
    """Free-plan private repos can't enable auto-merge at all; with no required
    checks on the base branch, integrate() merges the PR immediately instead of
    leaving it stranded OPEN (the gym-coach 2026-07-02 case)."""
    pr_url = "https://github.com/owner/repo/pull/6"
    runner = FakeRunner([
        _ok(), _ok(), _ok(), _ok(),
        _ok("refs/remotes/origin/master\n"),  # non-main default branch, seen live
        _ok(pr_url + "\n"),
        _fail("Pull request Protected branch rules not configured"),  # --auto
        _fail("HTTP 404: Branch not protected"),                      # probe → none
        _ok(""),                                                      # direct merge
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="fallback merge",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is True
    assert result.merged is True
    assert "merged PR directly" in result.detail
    probe = [c[0] for c in runner.calls if c[0][:2] == ["gh", "api"]][0]
    assert "branches/master/protection/required_status_checks" in probe[2]


def test_branch_pr_automerge_leaves_pr_open_when_checks_required(tmp_path, monkeypatch):
    """With required status checks on the base branch, an immediate merge would skip
    gates auto-merge would have waited for — leave the PR to the open-PR nudge."""
    pr_url = "https://github.com/owner/repo/pull/7"
    runner = FakeRunner([
        _ok(), _ok(), _ok(), _ok(),
        _ok("refs/remotes/origin/main\n"),
        _ok(pr_url + "\n"),
        _fail("auto-merge is not allowed"),   # --auto
        _ok('{"strict": true}'),              # probe → required checks exist
    ])
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="respect checks",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is False
    assert result.merged is False
    assert "left open" in result.detail
    direct = [c for c in runner.calls if c[0][:3] == ["gh", "pr", "merge"] and "--auto" not in c[0]]
    assert direct == []  # never bypassed the required checks


# ---------------------------------------------------------------------------
# Return to base branch after the branch flow (regression: clones were left
# stranded on the horus/… branch — seen live in agentic-gym-coach)
# ---------------------------------------------------------------------------

def _last_git_checkout(runner: FakeRunner) -> list[str]:
    checkouts = [c[0] for c in runner.calls if c[0][:2] == ["git", "checkout"]]
    return checkouts[-1]


def test_branch_pr_review_returns_to_base_branch(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/main\n"),
                         _ok("https://gh/pr/1\n"),
                         _ok()])                     # git checkout main
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="back to base",
                       policy=_policy(integration="branch-pr-review"))

    assert result.ok is True
    assert _last_git_checkout(runner) == ["git", "checkout", "main"]
    # And it happens after the PR is created.
    assert runner.calls[-1][0] == ["git", "checkout", "main"]


def test_branch_pr_automerge_returns_to_non_main_default(tmp_path, monkeypatch):
    """Default branch may be master — never hardcode main."""
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/master\n"),
                         _ok("https://gh/pr/2\n"),
                         _ok(""),                    # gh pr merge --auto
                         _ok()])                     # git checkout master
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="auto merge",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is True
    assert runner.calls[-1][0] == ["git", "checkout", "master"]


def test_direct_merge_fallback_returns_to_base(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/master\n"),
                         _ok("https://gh/pr/6\n"),
                         _fail("auto-merge not allowed"),   # --auto
                         _fail("Branch not protected"),     # probe → none
                         _ok(""),                           # direct merge
                         _ok()])                            # git checkout master
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="fallback",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.merged is True
    assert runner.calls[-1][0] == ["git", "checkout", "master"]


def test_merge_failure_still_returns_to_base(tmp_path, monkeypatch):
    """Even when the PR is left open, the work is pushed — don't strand the clone."""
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/main\n"),
                         _ok("https://gh/pr/7\n"),
                         _fail("auto-merge is not allowed"),  # --auto
                         _ok('{"strict": true}'),             # required checks exist
                         _ok()])                              # git checkout main
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="left open",
                       policy=_policy(integration="branch-pr-automerge"))

    assert result.ok is False
    assert runner.calls[-1][0] == ["git", "checkout", "main"]


def test_push_failure_stays_on_feature_branch(tmp_path, monkeypatch):
    """When the push fails the commits exist only locally on the branch — leaving
    it checked out is the safe state, so no checkout back."""
    runner = FakeRunner([_ok(), _ok(), _ok(),
                         _fail("could not read from remote")])  # git push
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="push fails",
                       policy=_policy(integration="branch-pr-review"))

    assert result.ok is False
    assert result.pushed is False
    checkouts = [c[0] for c in runner.calls if c[0][:2] == ["git", "checkout"]]
    assert len(checkouts) == 1  # only the initial checkout -b


def test_checkout_back_failure_warns_without_flipping_ok(tmp_path, monkeypatch):
    runner = FakeRunner([_ok(), _ok(), _ok(), _ok(),
                         _ok("refs/remotes/origin/main\n"),
                         _ok("https://gh/pr/9\n"),
                         _fail("local changes would be overwritten")])  # checkout main
    monkeypatch.setattr(intmod, "_run", runner)

    result = integrate(tmp_path, message="checkout back fails",
                       policy=_policy(integration="branch-pr-review"))

    assert result.ok is True
    assert "could not return to main" in result.detail
    assert "PR created" in result.detail


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


# ---------------------------------------------------------------------------
# Open continuity-PR nudge (open_horus_prs / continuity_pr_findings)
# ---------------------------------------------------------------------------

def _pr_json(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def test_open_horus_prs_filters_to_horus_branches(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    payload = (
        '[{"headRefName": "horus/chore-continuity", "url": "https://gh/pr/7", "title": "Continuity"},'
        ' {"headRefName": "feat/other-work", "url": "https://gh/pr/8", "title": "Other"}]'
    )
    monkeypatch.setattr(
        intmod.subprocess, "run", lambda *a, **k: _pr_json(payload)
    )

    prs = intmod.open_horus_prs(tmp_path)

    assert prs == [{"branch": "horus/chore-continuity", "url": "https://gh/pr/7", "title": "Continuity"}]


def test_open_horus_prs_non_repo_returns_none_without_gh(tmp_path, monkeypatch):
    def unexpected_run(*a, **k):  # pragma: no cover
        raise AssertionError("gh must not be invoked outside a git repo")

    monkeypatch.setattr(intmod.subprocess, "run", unexpected_run)
    assert intmod.open_horus_prs(tmp_path) is None


def test_open_horus_prs_unknowable_states_return_none(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    # gh errors (no remote / unauthenticated) -> None, never raises.
    monkeypatch.setattr(intmod.subprocess, "run", lambda *a, **k: _fail("no git remotes"))
    assert intmod.open_horus_prs(tmp_path) is None

    # gh missing entirely -> None.
    def raise_oserror(*a, **k):
        raise OSError("gh not found")

    monkeypatch.setattr(intmod.subprocess, "run", raise_oserror)
    assert intmod.open_horus_prs(tmp_path) is None

    # Garbage stdout -> None.
    monkeypatch.setattr(intmod.subprocess, "run", lambda *a, **k: _pr_json("not-json"))
    assert intmod.open_horus_prs(tmp_path) is None


def test_continuity_pr_findings_warn_per_open_pr(tmp_path, monkeypatch):
    monkeypatch.setattr(
        intmod, "open_horus_prs",
        lambda root: [{"branch": "horus/chore-x", "url": "https://gh/pr/7", "title": "x"}],
    )
    findings = intmod.continuity_pr_findings(tmp_path)
    assert len(findings) == 1
    assert findings[0].level == "warn"
    assert "https://gh/pr/7" in findings[0].message and "Allow auto-merge" in findings[0].message

    # None (unknowable) and empty both produce no findings.
    monkeypatch.setattr(intmod, "open_horus_prs", lambda root: None)
    assert intmod.continuity_pr_findings(tmp_path) == []


def test_cli_doctor_project_prints_open_continuity_pr_warn(tmp_path, monkeypatch, capsys):
    from horus.cli import main

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    from horus import initialize
    initialize.init_project(tmp_path, assume_yes=True)
    monkeypatch.setattr(
        intmod, "open_horus_prs",
        lambda root: [{"branch": "horus/chore-continuity", "url": "https://gh/pr/7", "title": "Continuity"}],
    )

    rc = main(["doctor", "project", "--path", str(tmp_path)])

    out = capsys.readouterr().out
    assert "Horus continuity PR still open: https://gh/pr/7" in out
    assert rc == 1  # warn flips the project-section exit code (existing semantics)
