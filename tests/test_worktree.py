"""Worktree plumbing for `horus run --worktree` — unit + a real `git worktree` pass."""

import subprocess
from pathlib import Path

import pytest

from horus import worktree
from horus.worktree import WorktreeError, ensure_worktree, branch_slug, worktree_path, primary_checkout, remove_if_merged


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


# --- primary_checkout: resolve a linked worktree back to the main checkout ----

def test_primary_checkout_of_main_worktree_is_itself(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    assert primary_checkout(repo) == repo.resolve()


def test_primary_checkout_of_linked_worktree_resolves_to_main(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    wt = ensure_worktree(repo, "probe-branch")
    assert primary_checkout(wt.path) == repo.resolve()


def test_primary_checkout_of_non_git_dir_returns_itself(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert primary_checkout(plain) == plain.resolve()


# --- remove_if_merged: never destructive unless the branch looks merged -----

def test_remove_if_merged_refuses_unmerged_branch(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    wt = ensure_worktree(repo, "probe-branch")
    result = remove_if_merged(repo, wt.path)
    assert result.removed is False
    assert "does not look merged" in result.detail
    assert wt.path.is_dir()  # left untouched


def test_remove_if_merged_removes_when_upstream_gone(tmp_path):
    """The `[gone]` upstream-track signal (GitHub deleted the branch post-merge,
    the same signature `gitstate.git_state` already trusts) is enough on its
    own, without needing a real remote."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True, text=True)
    repo = _init_repo(tmp_path / "repo")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")

    wt = ensure_worktree(repo, "probe-branch")
    _git(wt.path, "push", "-u", "origin", "probe-branch")
    # Simulate GitHub deleting the remote branch after a merge.
    _git(repo, "push", "origin", "--delete", "probe-branch")
    _git(wt.path, "fetch", "--prune")

    result = remove_if_merged(repo, wt.path)
    assert result.removed is True
    assert not wt.path.exists()
    listing = _git(repo, "worktree", "list", "--porcelain").stdout
    assert str(wt.path.resolve()) not in listing
    branches = _git(repo, "branch", "--list").stdout
    assert "probe-branch" not in branches


def test_remove_if_merged_removes_when_ancestor_of_default(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True, text=True)
    repo = _init_repo(tmp_path / "repo")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")

    wt = ensure_worktree(repo, "probe-branch")
    # Branch tip already IS the default branch's tip (an ancestor of it) —
    # merged without needing to actually push/delete a remote ref.
    _git(repo, "fetch", "origin")
    _git(repo, "remote", "set-head", "origin", "-a")  # sets refs/remotes/origin/HEAD

    result = remove_if_merged(repo, wt.path)
    assert result.removed is True
    assert not wt.path.exists()


def test_remove_if_merged_missing_path_is_a_noop(tmp_path):
    repo = _init_repo(tmp_path / "repo")
    missing = tmp_path / "not-there"
    result = remove_if_merged(repo, missing)
    assert result.removed is False
    assert "does not exist" in result.detail
