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

    # working-tree change -> dirty
    (tmp_path / "f.txt").write_text("changed", encoding="utf-8")
    assert gitstate.git_state(tmp_path)["dirty"] is True
