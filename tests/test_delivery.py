"""Tests for horus.delivery — the failed-but-delivered receipt.

Git probes run against a real throwaway bare-origin + clone (same pattern as
test_gitstate.py); the gh probe is monkeypatched via horus.integration's own
subprocess.run seam (same pattern as test_integration.py), so no real GitHub
call ever happens.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from horus import delivery, integration as intmod


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _commit_at(root: Path, message: str, iso_time: str) -> str:
    """Commit whatever is staged with an explicit author/committer date, so
    attribution tests can control commit timestamps precisely instead of
    racing real wall-clock resolution."""
    env = {**os.environ, "GIT_AUTHOR_DATE": iso_time, "GIT_COMMITTER_DATE": iso_time}
    subprocess.run(
        ["git", "-C", str(root), "commit", "-am", message], check=True, capture_output=True, env=env,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()


def _bare_origin_and_clone(tmp_path: Path) -> tuple[Path, Path]:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@t.com")
    _git(clone, "config", "user.name", "t")
    (clone / "f.txt").write_text("hi", encoding="utf-8")
    _git(clone, "add", "f.txt")
    _git(clone, "commit", "-m", "first commit")
    _git(clone, "push", "origin", "main")
    return origin, clone


def _pr_json(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _patch_gh(monkeypatch, handler) -> None:
    """Fake only ``gh`` calls; every ``git`` subprocess passes through to the real
    ``subprocess.run`` — ``intmod.subprocess`` IS the process-wide ``subprocess``
    module (same object every ``import subprocess`` binds to), so a blanket
    monkeypatch here would also swallow this test's own git fixture setup."""
    real_run = subprocess.run

    def fake(cmd, *a, **k):
        if cmd and cmd[0] == "gh":
            return handler(cmd, *a, **k)
        return real_run(cmd, *a, **k)

    monkeypatch.setattr(intmod.subprocess, "run", fake)


def _no_pr(monkeypatch) -> None:
    _patch_gh(monkeypatch, lambda *a, **k: _pr_json("[]"))


# --- pushed_sha ---------------------------------------------------------------


def test_receipt_finds_pushed_sha_via_tracking_ref(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/feature")
    (clone / "f.txt").write_text("worker work", encoding="utf-8")
    _git(clone, "commit", "-am", "worker commit")
    _git(clone, "push", "-u", "origin", "worker/feature")
    head = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.branch == "worker/feature"
    assert receipt.pushed_sha == head
    assert receipt.has_signal is True


def test_receipt_falls_back_to_ls_remote_without_tracking_ref(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/feature")
    (clone / "f.txt").write_text("worker work", encoding="utf-8")
    _git(clone, "commit", "-am", "worker commit")
    # Push WITHOUT -u: the ref lands on the remote but this checkout has no
    # tracking branch configured for it — the worktree-without--u case.
    _git(clone, "push", "origin", "worker/feature")
    head = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.pushed_sha == head


def test_receipt_has_no_pushed_sha_when_branch_never_pushed(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/never-pushed")
    (clone / "f.txt").write_text("local only", encoding="utf-8")
    _git(clone, "commit", "-am", "local commit")

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.pushed_sha is None


# --- PR lookup -----------------------------------------------------------------


def test_receipt_includes_pr_for_branch(tmp_path, monkeypatch):
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/with-pr")
    payload = '[{"number": 4, "url": "https://gh/pr/4", "state": "OPEN", "title": "Worker PR"}]'
    _patch_gh(monkeypatch, lambda *a, **k: _pr_json(payload))

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.pr_number == 4
    assert receipt.pr_url == "https://gh/pr/4"
    assert receipt.pr_state == "OPEN"
    assert receipt.has_signal is True


# --- continuity closed ---------------------------------------------------------


def test_receipt_detects_continuity_closure_commit(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/closed-continuity")
    (clone / ".horus").mkdir()
    (clone / ".horus" / "PRD.md").write_text("# PRD\n", encoding="utf-8")
    _git(clone, "add", ".horus")
    _git(clone, "commit", "-m", "Update Horus continuity (closure)")

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.continuity_closed is True


def test_receipt_continuity_not_closed_without_matching_commit(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/no-closure")
    (clone / ".horus").mkdir()
    (clone / ".horus" / "PRD.md").write_text("# PRD\n", encoding="utf-8")
    _git(clone, "add", ".horus")
    _git(clone, "commit", "-m", "wip: touch continuity")

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.continuity_closed is False


# --- nothing delivered / degradation -------------------------------------------


def test_receipt_none_signal_when_nothing_delivered(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/nothing")

    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.has_signal is False
    assert delivery.render_receipt("failed", receipt) == ""


def test_delivery_receipt_none_for_missing_directory(tmp_path):
    assert delivery.delivery_receipt(tmp_path / "does-not-exist") is None


def test_delivery_receipt_none_for_non_git_directory(tmp_path):
    (tmp_path / "plain").mkdir()
    assert delivery.delivery_receipt(tmp_path / "plain") is None


def test_delivery_receipt_none_for_detached_head(tmp_path, monkeypatch):
    _no_pr(monkeypatch)
    _origin, clone = _bare_origin_and_clone(tmp_path)
    commit = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()
    _git(clone, "checkout", commit)

    assert delivery.delivery_receipt(clone) is None


def test_delivery_receipt_degrades_gracefully_when_gh_raises(tmp_path, monkeypatch):
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/gh-down")

    def raise_oserror(*a, **k):
        raise OSError("gh not found")

    _patch_gh(monkeypatch, raise_oserror)

    receipt = delivery.delivery_receipt(clone)  # must not raise

    assert receipt is not None
    assert receipt.pr_number is None


# --- shared-branch attribution (killed attempt + retry) ------------------------


def test_receipt_attributes_shared_branch_commits_by_session_time(tmp_path, monkeypatch):
    """A killed attempt and its retry pushing to the SAME branch each opened
    their own PR. Without time-correlation both sessions' delivery receipts
    would resolve to the branch's current tip (the retry's commit and PR),
    mis-attributing the retry's work to the killed session. Regression for the
    bug observed live on commit 77bcc321."""
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/shared-branch")

    killed_time = "2024-01-01T00:00:00+00:00"
    (clone / "f.txt").write_text("killed attempt work", encoding="utf-8")
    killed_sha = _commit_at(clone, "killed attempt commit", killed_time)
    _git(clone, "push", "origin", "worker/shared-branch")

    retry_time = "2024-01-01T01:00:00+00:00"
    (clone / "f.txt").write_text("retry work", encoding="utf-8")
    retry_sha = _commit_at(clone, "retry commit", retry_time)
    _git(clone, "push", "origin", "worker/shared-branch")

    assert killed_sha != retry_sha

    payload = (
        '[{"number": 5, "url": "https://gh/pr/5", "state": "CLOSED", "title": "killed attempt PR", '
        f'"headRefOid": "{killed_sha}"}}, '
        '{"number": 7, "url": "https://gh/pr/7", "state": "OPEN", "title": "retry PR", '
        f'"headRefOid": "{retry_sha}"}}]'
    )
    _patch_gh(monkeypatch, lambda *a, **k: _pr_json(payload))

    killed_session_end = datetime.fromisoformat(killed_time) + timedelta(seconds=5)
    retry_session_end = datetime.fromisoformat(retry_time) + timedelta(seconds=5)

    killed_receipt = delivery.delivery_receipt(clone, session_end=killed_session_end)
    retry_receipt = delivery.delivery_receipt(clone, session_end=retry_session_end)

    assert killed_receipt is not None
    assert retry_receipt is not None
    assert killed_receipt.pushed_sha == killed_sha
    assert killed_receipt.pr_number == 5
    assert retry_receipt.pushed_sha == retry_sha
    assert retry_receipt.pr_number == 7
    # The whole point: each session gets its OWN delivery, not both collapsing
    # onto the branch's current tip.
    assert killed_receipt.pushed_sha != retry_receipt.pushed_sha
    assert killed_receipt.pr_number != retry_receipt.pr_number


def test_receipt_without_session_end_falls_back_to_branch_tip(tmp_path, monkeypatch):
    """Documents the pre-fix behavior that's still correct when there's no
    session end to correlate against: plain branch-tip attribution."""
    _origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "worker/shared-branch")

    (clone / "f.txt").write_text("killed attempt work", encoding="utf-8")
    _commit_at(clone, "killed attempt commit", "2024-01-01T00:00:00+00:00")
    _git(clone, "push", "origin", "worker/shared-branch")

    (clone / "f.txt").write_text("retry work", encoding="utf-8")
    retry_sha = _commit_at(clone, "retry commit", "2024-01-01T01:00:00+00:00")
    _git(clone, "push", "origin", "worker/shared-branch")

    _no_pr(monkeypatch)
    receipt = delivery.delivery_receipt(clone)

    assert receipt is not None
    assert receipt.pushed_sha == retry_sha


# --- render_receipt / NONCLEAN_STATUSES ----------------------------------------


def test_render_receipt_composes_status_and_facts():
    receipt = delivery.DeliveryReceipt(
        branch="worker/x", pushed_sha="abc12345678", pr_number=4, pr_url="https://gh/pr/4",
        continuity_closed=True,
    )
    text = delivery.render_receipt("failed", receipt)
    assert text == "failed-but-delivered · pushed abc12345 · PR #4 · continuity closed"


def test_render_receipt_empty_for_none_or_no_signal():
    assert delivery.render_receipt("failed", None) == ""
    assert delivery.render_receipt("stale", delivery.DeliveryReceipt(branch="x")) == ""


def test_nonclean_statuses_are_failed_and_stale_only():
    assert delivery.NONCLEAN_STATUSES == frozenset({"failed", "stale"})
