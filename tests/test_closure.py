"""Tests for the git-aware closure routine."""

import os
import subprocess

from horus import closure, initialize


def _run(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    _run(tmp_path, "init")
    _run(tmp_path, "config", "user.email", "t@example.com")
    _run(tmp_path, "config", "user.name", "Tester")
    initialize.init_project(tmp_path, assume_yes=True)
    _run(tmp_path, "add", "-A")
    _run(tmp_path, "commit", "-m", "init")
    return tmp_path


def _msgs(root):
    return [f.message for f in closure.closure_status(root)]


def test_is_git_repo(tmp_path, monkeypatch):
    assert not closure.is_git_repo(tmp_path)
    _setup(tmp_path, monkeypatch)
    assert closure.is_git_repo(tmp_path)


def test_clean_after_commit(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert any("continuity files committed" in m for m in _msgs(tmp_path))


def test_uncommitted_continuity_warns(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    assert any("uncommitted continuity" in m for m in _msgs(tmp_path))


def test_work_commit_since_summary(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / "foo.py").write_text("x = 1\n", encoding="utf-8")
    _run(tmp_path, "add", "foo.py")
    _run(tmp_path, "commit", "-m", "work")
    ct = int(
        subprocess.run(
            ["git", "-C", str(tmp_path), "log", "-1", "--format=%ct"],
            capture_output=True, text=True,
        ).stdout.strip()
    )
    sess = tmp_path / ".horus" / "sessions" / "2026-06-24-x.md"
    sess.write_text("---\ndate: 2026-06-24\nsummary: x\n---\n# x\n", encoding="utf-8")

    os.utime(sess, (ct - 100, ct - 100))  # summary older than the work commit
    assert any("since the latest session summary" in m for m in _msgs(tmp_path))

    os.utime(sess, (ct + 100, ct + 100))  # summary newer than the work commit
    assert not any("since the latest session summary" in m for m in _msgs(tmp_path))


def test_commit_continuity(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    did, detail = closure.commit_continuity(tmp_path, "test closure")
    assert did and "committed" in detail
    did2, detail2 = closure.commit_continuity(tmp_path)
    assert not did2 and "nothing to commit" in detail2


def _setup_two_clones(tmp_path, monkeypatch):
    """A bare origin with two clones — the one-person-two-machines scenario."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    a, b = tmp_path / "machine-a", tmp_path / "machine-b"
    for clone in (a, b):
        subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True)
        _run(clone, "config", "user.email", "t@example.com")
        _run(clone, "config", "user.name", "Tester")
    initialize.init_project(a, assume_yes=True)
    _run(a, "add", "-A")
    _run(a, "commit", "-m", "init")
    _run(a, "push", "origin", "HEAD")
    _run(b, "pull", "origin", "master")
    return a, b


def test_push_refused_when_remote_lanes_newer(tmp_path, monkeypatch):
    a, b = _setup_two_clones(tmp_path, monkeypatch)
    # machine A closes and pushes newer lanes
    (a / ".horus" / "roadmap.md").write_text("from machine a\n", encoding="utf-8")
    did, _ = closure.commit_continuity(a, "close on a", push=True)
    assert did
    # machine B, unaware, tries to close --commit --push: refused, nothing committed
    (b / ".horus" / "roadmap.md").write_text("from machine b\n", encoding="utf-8")
    did, detail = closure.commit_continuity(b, "close on b", push=True)
    assert not did and "pull" in detail and "newer continuity" in detail
    assert closure.remote_lane_divergence(b) == 1
    # after pulling (theirs wins for the test), the push goes through
    _run(b, "checkout", "--", ".")
    _run(b, "pull", "--ff-only")
    (b / ".horus" / "roadmap.md").write_text("merged on b\n", encoding="utf-8")
    did, detail = closure.commit_continuity(b, "close on b", push=True)
    assert did and "pushed" in detail


def test_push_allowed_without_upstream_or_remote(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)  # plain repo, no remote at all
    assert closure.remote_lane_divergence(tmp_path) == 0
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    did, detail = closure.commit_continuity(tmp_path, "close", push=True)
    assert did  # the guard errs toward allowing; only the push itself fails
    assert "push failed" in detail
