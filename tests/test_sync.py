"""`horus sync` — the explicit fast-forward remedy for fetch-first.

The refusal matrix is the whole safety story, so it is tested as a pure decision
against `git_state` mappings (no repo needed), plus one live probe on a real
throwaway repo pair proving a fast-forward actually moves the checkout and that a
dirty tree is refused without being touched.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from horus import sync


def _state(**over):
    base = {
        "branch": "main",
        "commit": {"hash": "abc123", "subject": "x"},
        "dirty": False,
        "upstream": "origin/main",
        "behind": 0,
        "ahead": 0,
        "remote_url": "git@example:o/r.git",
        "detached": False,
    }
    base.update(over)
    return base


# --- the refusal matrix -----------------------------------------------------

def test_no_state_refuses():
    assert sync.plan(None)[0] == sync.REFUSED
    assert "work tree" in sync.plan(None)[1]


def test_detached_head_refuses():
    outcome, reason = sync.plan(_state(detached=True))
    assert outcome == sync.REFUSED
    assert "detached" in reason


def test_no_upstream_refuses():
    outcome, reason = sync.plan(_state(upstream=None))
    assert outcome == sync.REFUSED
    assert "upstream" in reason


def test_already_current_is_success_not_refusal():
    outcome, reason = sync.plan(_state(behind=0))
    assert outcome == sync.CURRENT
    assert "current" in reason


def test_current_but_unpushed_still_success_and_says_so():
    outcome, reason = sync.plan(_state(behind=0, ahead=3))
    assert outcome == sync.CURRENT
    assert "3 local commit" in reason


def test_behind_and_dirty_refuses_without_touching_anything():
    outcome, reason = sync.plan(_state(behind=2, dirty=True))
    assert outcome == sync.REFUSED
    assert "uncommitted" in reason


def test_diverged_refuses_because_fast_forward_is_impossible():
    outcome, reason = sync.plan(_state(behind=2, ahead=1))
    assert outcome == sync.REFUSED
    assert "diverged" in reason
    assert "fast-forward is impossible" in reason


def test_behind_clean_and_no_local_commits_is_the_only_sync_case():
    outcome, reason = sync.plan(_state(behind=4))
    assert outcome == sync.SYNCED
    assert "4 commit" in reason


def test_dirty_wins_over_diverged_so_the_message_names_the_first_fix():
    # Both problems present: the actionable one is the dirty tree.
    outcome, reason = sync.plan(_state(behind=2, ahead=1, dirty=True))
    assert outcome == sync.REFUSED
    assert "uncommitted" in reason


# --- one live probe --------------------------------------------------------

def _git(root: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return r.stdout.strip()


def _repo_pair(tmp_path: Path) -> tuple[Path, Path]:
    """An upstream with two commits and a clone parked one commit behind."""
    up = tmp_path / "up"
    up.mkdir()
    _git(up, "init", "-q", "-b", "main")
    _git(up, "config", "user.email", "t@example.com")
    _git(up, "config", "user.name", "T")
    (up / "f.txt").write_text("one\n")
    _git(up, "add", "f.txt")
    _git(up, "commit", "-qm", "one")

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(up), str(clone))
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "T")

    (up / "f.txt").write_text("two\n")
    _git(up, "commit", "-qam", "two")
    _git(clone, "fetch", "-q", "origin")
    return up, clone


def test_live_fast_forward_moves_the_checkout(tmp_path):
    _, clone = _repo_pair(tmp_path)
    before = _git(clone, "rev-parse", "HEAD")

    ok, _ = sync.fast_forward(clone, "origin/main")

    assert ok
    assert _git(clone, "rev-parse", "HEAD") != before
    assert (clone / "f.txt").read_text() == "two\n"


def test_live_fast_forward_refuses_a_real_divergence(tmp_path):
    """--ff-only must fail rather than create a merge commit."""
    _, clone = _repo_pair(tmp_path)
    (clone / "local.txt").write_text("mine\n")
    _git(clone, "add", "local.txt")
    _git(clone, "commit", "-qm", "local")
    head = _git(clone, "rev-parse", "HEAD")

    ok, message = sync.fast_forward(clone, "origin/main")

    assert not ok
    assert message  # the git error is surfaced, never swallowed
    assert _git(clone, "rev-parse", "HEAD") == head  # nothing moved
