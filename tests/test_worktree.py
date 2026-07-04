"""Worktree plumbing for `horus run --worktree` — unit + a real `git worktree` pass."""

import subprocess
from pathlib import Path

import pytest

from horus import worktree
from horus.worktree import WorktreeError, ensure_worktree, branch_slug, worktree_path


def _git(root: Path, *args: str):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("hi\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    return root


def test_branch_slug_normalizes():
    assert branch_slug("feat/run-worktree") == "feat-run-worktree"
    assert branch_slug("Fix/UPPER_Case") == "fix-upper-case"
    assert branch_slug("///") == "worktree"  # degenerate name still yields a usable slug


def test_worktree_path_is_repo_sibling(tmp_path):
    repo = _init_repo(tmp_path / "myrepo")
    p = worktree_path(repo, "feat/x")
    assert p == repo.parent / "myrepo-wt-feat-x"


def test_ensure_creates_worktree_on_new_branch(tmp_path):
    """Real `git worktree` integration: a fresh branch is created off HEAD."""
    repo = _init_repo(tmp_path / "repo")
    res = ensure_worktree(repo, "probe-branch")
    assert res.created is True
    assert res.branch == "probe-branch"
    assert res.path == repo.parent / "repo-wt-probe-branch"
    assert res.path.is_dir()
    assert (res.path / "README.md").exists()  # checked out from HEAD
    # git tracks it as a worktree on the requested branch
    listing = _git(repo, "worktree", "list", "--porcelain").stdout
    assert str(res.path.resolve()) in listing
    assert "branch refs/heads/probe-branch" in listing


def test_ensure_reuses_existing_worktree(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    first = ensure_worktree(repo, "probe-branch")
    (first.path / "scratch.txt").write_text("keep me\n", encoding="utf-8")  # prove it's untouched
    second = ensure_worktree(repo, "probe-branch")
    assert second.created is False
    assert second.path == first.path
    assert (second.path / "scratch.txt").read_text(encoding="utf-8") == "keep me\n"


def test_ensure_uses_existing_branch(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    _git(repo, "branch", "already-here")
    res = ensure_worktree(repo, "already-here")
    assert res.created is True
    listing = _git(repo, "worktree", "list", "--porcelain").stdout
    assert "branch refs/heads/already-here" in listing


def test_refuses_when_target_exists_and_is_not_a_worktree(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    target = worktree_path(repo, "probe-branch")
    target.mkdir(parents=True)
    (target / "unrelated.txt").write_text("mine\n", encoding="utf-8")
    with pytest.raises(WorktreeError, match="not a worktree of this repo"):
        ensure_worktree(repo, "probe-branch")


def test_refuses_non_git_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(WorktreeError, match="not a git"):
        ensure_worktree(plain, "probe-branch")


def test_refuses_bare_repository(tmp_path):
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True, text=True)
    with pytest.raises(WorktreeError, match="bare"):
        ensure_worktree(bare, "probe-branch")


def test_surfaces_git_add_failure(tmp_path):
    """A branch already checked out in the main worktree can't be added again —
    the git error is surfaced as a polite refusal, not a traceback."""
    repo = _init_repo(tmp_path / "repo")  # main worktree is on `main`
    with pytest.raises(WorktreeError, match="could not create worktree"):
        ensure_worktree(repo, "main")
