"""Emergency git state-save — worker rescue-commit and main-checkout rescue ref.

Real ``git`` throughout, in throwaway repos, no network.
"""

import subprocess
from pathlib import Path

import pytest

from horus import rescue


def _git(root: Path, *args: str, env=None):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, env=env
    )


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("hi\n", encoding="utf-8")
    (root / ".horus").mkdir()
    (root / ".horus" / "PRD.md").write_text("prd v1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    return root


def _bare_remote(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True, text=True)
    return bare


# --------------------------------------------------------------------------- #
# Worker context: full-tree rescue-commit + push
# --------------------------------------------------------------------------- #

def test_worker_context_via_env_marker(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path / "repo")
    monkeypatch.setenv("HORUS_RUN_WORKER", "1")
    assert rescue.is_worker_context(repo) is True


def test_worker_context_via_linked_worktree(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path / "repo")
    monkeypatch.delenv("HORUS_RUN_WORKER", raising=False)
    wt = tmp_path / "repo-wt"
    _git(repo, "worktree", "add", "-b", "wbranch", str(wt))
    assert rescue.is_worker_context(repo) is False  # the main checkout
    assert rescue.is_worker_context(wt) is True      # the linked worktree


def test_rescue_worker_commits_full_tree_and_pushes(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path / "repo")
    remote = _bare_remote(tmp_path)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")
    # uncommitted product + continuity changes
    (repo / "feature.py").write_text("print('wip')\n", encoding="utf-8")
    (repo / ".horus" / "PRD.md").write_text("prd v2 dirty\n", encoding="utf-8")
    monkeypatch.setenv("HORUS_RUN_WORKER", "1")

    result = rescue.emergency_rescue(repo, session_id="sess-1")
    assert result.mode == "worker"
    assert result.committed is True
    assert result.pushed is True
    # the rescue commit is HEAD and carries the marker subject
    subject = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
    assert subject.startswith("horus rescue:")
    # the full tree was captured (product file included), and pushed to origin
    tracked = _git(repo, "ls-files").stdout
    assert "feature.py" in tracked
    remote_head = _git(repo, "rev-parse", "origin/main").stdout.strip()
    local_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert remote_head == local_head


def test_rescue_worker_pushes_branch_with_no_upstream(tmp_path, monkeypatch):
    """The kit's primary case: a fresh worker branch (no upstream) that never pushed.

    A bare ``git push`` would fail with 'no upstream branch'; the rescue must fall back
    to an explicit push so the commit still reaches origin."""
    repo = _init_repo(tmp_path / "repo")
    remote = _bare_remote(tmp_path)
    _git(repo, "remote", "add", "origin", str(remote))
    # A worker-style branch with NO upstream configured (like `git worktree add -b`).
    _git(repo, "checkout", "-q", "-b", "wbranch")
    upstream = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "wbranch@{upstream}"],
        capture_output=True, text=True,
    )
    assert upstream.returncode != 0  # no upstream set — bare push would fail
    (repo / "wip.py").write_text("print('unsaved')\n", encoding="utf-8")
    monkeypatch.setenv("HORUS_RUN_WORKER", "1")

    result = rescue.emergency_rescue(repo, session_id="sess-noups")
    assert result.committed is True
    assert result.pushed is True  # explicit-push fallback carried it to origin
    # the rescue commit is present on origin's wbranch
    remote_head = _git(repo, "rev-parse", "origin/wbranch").stdout.strip()
    local_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert remote_head == local_head


def test_rescue_worker_push_failure_is_tolerated(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path / "repo")  # no remote configured
    (repo / "wip.py").write_text("x\n", encoding="utf-8")
    monkeypatch.setenv("HORUS_RUN_WORKER", "1")

    result = rescue.emergency_rescue(repo, session_id="sess-2")
    assert result.committed is True
    assert result.pushed is False  # push failed (no origin), but the commit stands
    assert "push FAILED" in result.detail


def test_rescue_worker_clean_tree_reports_nothing_to_save(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path / "repo")
    monkeypatch.setenv("HORUS_RUN_WORKER", "1")
    result = rescue.emergency_rescue(repo, session_id="sess-3")
    assert result.committed is False
    assert "nothing to rescue" in result.detail


# --------------------------------------------------------------------------- #
# Main checkout: .horus-only rescue ref, index/HEAD/worktree untouched
# --------------------------------------------------------------------------- #

def test_rescue_main_leaves_index_head_worktree_untouched(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path / "repo")
    monkeypatch.delenv("HORUS_RUN_WORKER", raising=False)

    # Dirty the tree: a staged product change, an unstaged .horus change, an untracked file.
    (repo / "src.py").write_text("staged change\n", encoding="utf-8")
    _git(repo, "add", "src.py")
    (repo / ".horus" / "PRD.md").write_text("prd dirty continuity\n", encoding="utf-8")
    (repo / "scratch.txt").write_text("untracked\n", encoding="utf-8")

    head_before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    status_before = _git(repo, "status", "--porcelain").stdout
    index_before = _git(repo, "diff", "--cached", "--stat").stdout

    result = rescue.emergency_rescue(repo, session_id="sess-main")
    assert result.mode == "main"
    assert result.committed is True
    assert result.ref.startswith("refs/horus/rescue/")

    # Nothing moved: HEAD, index, and working-tree status are byte-identical.
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == head_before
    assert _git(repo, "status", "--porcelain").stdout == status_before
    assert _git(repo, "diff", "--cached", "--stat").stdout == index_before

    # The rescue ref exists, is parented on HEAD, and holds the dirty .horus snapshot.
    commit = _git(repo, "rev-parse", result.ref).stdout.strip()
    assert _git(repo, "rev-parse", f"{result.ref}^").stdout.strip() == head_before
    blob = _git(repo, "show", f"{commit}:.horus/PRD.md").stdout
    assert blob == "prd dirty continuity\n"
    # ...and it does NOT carry the product change (only .horus was snapshotted).
    files = _git(repo, "ls-tree", "-r", "--name-only", commit).stdout
    assert ".horus/PRD.md" in files
    assert "src.py" not in files


def test_rescue_main_without_horus_dir_is_a_noop(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "init")
    monkeypatch.delenv("HORUS_RUN_WORKER", raising=False)

    result = rescue.emergency_rescue(repo, session_id="s")
    assert result.mode == "main"
    assert result.committed is False
    assert "no .horus/" in result.detail


def test_emergency_rescue_outside_git_repo_is_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("HORUS_RUN_WORKER", raising=False)
    result = rescue.emergency_rescue(tmp_path, session_id="s")
    assert result.mode == "skipped"
    assert result.committed is False
