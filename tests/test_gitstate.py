"""Tests for the git freshness signal (uses a real throwaway repo)."""

import subprocess

from horus import gitstate


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_non_repo_returns_none(tmp_path):
    assert gitstate.git_state(tmp_path) is None


def test_reports_branch_commit_and_dirty(tmp_path):
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "f.txt").write_text("hi", encoding="utf-8")
    _git(tmp_path, "add", "f.txt")
    _git(tmp_path, "commit", "-m", "first commit")

    s = gitstate.git_state(tmp_path)
    assert s is not None
    assert s["branch"] == "main"
    assert s["commit"]["subject"] == "first commit"
    assert s["dirty"] is False
    assert s["upstream"] is None  # no remote configured
    assert "main" in gitstate.summary(s)
    assert s["detached"] is False
    assert s["own_upstream_gone"] is False
    assert s["default_branch"] is None  # no origin -> nothing to compare against

    # working-tree change -> dirty
    (tmp_path / "f.txt").write_text("changed", encoding="utf-8")
    assert gitstate.git_state(tmp_path)["dirty"] is True


# --- fleet-truth signals: default-branch relationship, gone upstream, detached ---


def _bare_origin_and_clone(tmp_path):
    """A bare origin plus one clone with an initial commit on the default branch —
    the minimal fixture for exercising origin/HEAD, ahead/behind-of-default, and
    upstream-gone detection against a real remote (not a mock)."""
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


def test_default_branch_resolved_from_origin_head(tmp_path):
    _origin, clone = _bare_origin_and_clone(tmp_path)
    s = gitstate.git_state(clone)
    assert s["default_branch"] == "main"
    assert s["default_ahead"] == 0
    assert s["default_behind"] == 0


def test_own_upstream_gone_after_branch_merged_and_deleted(tmp_path):
    origin, clone = _bare_origin_and_clone(tmp_path)
    _git(clone, "checkout", "-b", "feature")
    (clone / "f.txt").write_text("feature work", encoding="utf-8")
    _git(clone, "commit", "-am", "feature commit")
    _git(clone, "push", "-u", "origin", "feature")

    s = gitstate.git_state(clone)
    assert s["branch"] == "feature"
    assert s["own_upstream_gone"] is False
    assert s["default_ahead"] == 1  # one unmerged commit vs origin/main
    assert "⚠ upstream gone" not in gitstate.summary(s)

    # Simulate the PR-merged-and-branch-deleted scenario: the remote ref for
    # `feature` is deleted (as GitHub does on merge) while the local checkout
    # still sits on it.
    subprocess.run(["git", "-C", str(origin), "branch", "-D", "feature"], check=True, capture_output=True)
    _git(clone, "fetch", "--prune")

    s = gitstate.git_state(clone)
    assert s["branch"] == "feature"
    assert s["own_upstream_gone"] is True
    summary = gitstate.summary(s)
    assert "⚠ upstream gone" in summary
    assert "vs main: +1/-0" in summary


def test_detached_head_reported(tmp_path):
    _origin, clone = _bare_origin_and_clone(tmp_path)
    commit = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _git(clone, "checkout", commit)

    s = gitstate.git_state(clone)
    assert s["detached"] is True
    assert s["branch"] == "?"
    assert gitstate.summary(s).startswith(f"detached@{s['commit']['hash']}")


def test_staleness_hint_fires_when_default_branch_meaningfully_behind_origin():
    state = {"branch": "main", "default_branch": "main", "behind": 5, "detached": False}
    hint = gitstate.staleness_hint(state)
    assert "continuity may be stale" in hint
    assert "5 commit(s) behind" in hint


def test_staleness_hint_silent_below_threshold_or_off_default_or_detached():
    assert gitstate.staleness_hint(None) == ""
    assert gitstate.staleness_hint({"branch": "main", "default_branch": "main", "behind": 1}) == ""
    assert gitstate.staleness_hint(
        {"branch": "feature", "default_branch": "main", "behind": 9}
    ) == ""
    assert gitstate.staleness_hint(
        {"branch": "?", "default_branch": "main", "behind": 9, "detached": True}
    ) == ""
