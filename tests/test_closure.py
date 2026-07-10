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


def test_projected_artifacts_are_continuity(tmp_path, monkeypatch):
    """Hook/skill projections count as continuity: an untracked .claude/settings.json
    warns and `close --commit` commits it (the gym-coach 2026-07-02 finding)."""
    _setup(tmp_path, monkeypatch)
    (tmp_path / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    assert any("uncommitted continuity" in m for m in _msgs(tmp_path))
    did, _ = closure.commit_continuity(tmp_path, "test closure")
    assert did
    status = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        capture_output=True, text=True,
    ).stdout
    assert ".claude/settings.json" not in status


def test_commit_continuity_survives_missing_artifact_paths(tmp_path, monkeypatch):
    """A repo without hooks/skills installed: `git add` must not fail wholesale on
    pathspecs that match nothing."""
    _setup(tmp_path, monkeypatch)
    import shutil
    for rel in (".claude", ".agents", ".codex"):
        shutil.rmtree(tmp_path / rel, ignore_errors=True)
    _run(tmp_path, "add", "-A")
    _run(tmp_path, "commit", "-m", "drop projections")
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    did, detail = closure.commit_continuity(tmp_path, "test closure")
    assert did and "committed" in detail


def _checkpoint_msgs(root):
    return [(f.level, f.message) for f in closure.checkpoint_gate(root)]


def test_checkpoint_gate_clean_tree_no_upstream(tmp_path, monkeypatch):
    """Fresh committed repo, no remote: tree clean, and the unpushed check is skipped
    (no upstream to push to) — so the gate is healthy."""
    _setup(tmp_path, monkeypatch)
    msgs = _checkpoint_msgs(tmp_path)
    assert any("working tree clean" in m for _, m in msgs)
    assert all(level == "ok" for level, _ in msgs)


def test_checkpoint_gate_warns_on_dirty_tree(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / "scratch.py").write_text("x = 1\n", encoding="utf-8")  # untracked = dirty
    msgs = _checkpoint_msgs(tmp_path)
    assert any(level == "warn" and "uncommitted change" in m for level, m in msgs)


def test_checkpoint_gate_warns_on_unpushed_commits(tmp_path, monkeypatch):
    a, _ = _setup_two_clones(tmp_path, monkeypatch)
    # a is at origin/master; make a local commit that is not pushed.
    (a / "work.py").write_text("y = 2\n", encoding="utf-8")
    _run(a, "add", "work.py")
    _run(a, "commit", "-m", "local work")
    msgs = _checkpoint_msgs(a)
    assert any(level == "warn" and "not pushed" in m for level, m in msgs)
    # After pushing, the unpushed warning clears.
    _run(a, "push", "origin", "HEAD")
    msgs = _checkpoint_msgs(a)
    assert not any("not pushed" in m for _, m in msgs)


def test_checkpoint_gate_push_opt_out(tmp_path, monkeypatch):
    """`enforce_push: false` in PRD frontmatter skips the unpushed-commits check."""
    a, _ = _setup_two_clones(tmp_path, monkeypatch)
    (a / "work.py").write_text("y = 2\n", encoding="utf-8")
    _run(a, "add", "work.py")
    _run(a, "commit", "-m", "local work")
    prd = a / ".horus" / "PRD.md"
    prd.write_text("---\nenforce_push: false\n---\n# PRD\n", encoding="utf-8")
    msgs = _checkpoint_msgs(a)
    assert not any("not pushed" in m for _, m in msgs)
    # The dirty-tree half still applies even when push is opted out.
    assert any(level == "warn" and "uncommitted change" in m for level, m in msgs)


def test_checkpoint_gate_silent_outside_repo(tmp_path):
    assert closure.checkpoint_gate(tmp_path) == []


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
    # Fresh init scaffolds structure v3 (PRD.md, not roadmap.md); use the lane
    # file that is actually tracked from the initial commit on both clones.
    # machine A closes and pushes newer lanes
    (a / ".horus" / "PRD.md").write_text("from machine a\n", encoding="utf-8")
    did, _ = closure.commit_continuity(a, "close on a", push=True)
    assert did
    # machine B, unaware, tries to close --commit --push: refused, nothing committed
    (b / ".horus" / "PRD.md").write_text("from machine b\n", encoding="utf-8")
    did, detail = closure.commit_continuity(b, "close on b", push=True)
    assert not did and "pull" in detail and "newer continuity" in detail
    assert closure.remote_lane_divergence(b) == 1
    # after pulling (theirs wins for the test), the push goes through
    _run(b, "checkout", "--", ".")
    _run(b, "pull", "--ff-only")
    (b / ".horus" / "PRD.md").write_text("merged on b\n", encoding="utf-8")
    did, detail = closure.commit_continuity(b, "close on b", push=True)
    assert did and "pushed" in detail


def test_push_allowed_without_upstream_or_remote(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)  # plain repo, no remote at all
    assert closure.remote_lane_divergence(tmp_path) == 0
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    did, detail = closure.commit_continuity(tmp_path, "close", push=True)
    assert did  # the guard errs toward allowing; only the push itself fails
    assert "push failed" in detail


# --------------------------------------------------------------------------- #
# Checkpoint harvest — incremental consolidation
# --------------------------------------------------------------------------- #

def _session_note(root, name="2026-07-10-120000-test.md"):
    p = root / ".horus" / "sessions" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ndate: 2026-07-10T12:00:00\nproject: x\nstatus: in-progress\nsummary: t\n---\n\n# Test\n",
        encoding="utf-8",
    )
    return p


def _work_commit(root, fname, content, msg):
    (root / fname).write_text(content, encoding="utf-8")
    _run(root, "add", "-A")
    _run(root, "commit", "-m", msg)


def test_harvest_appends_commit_to_note(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    note = _session_note(tmp_path)
    _work_commit(tmp_path, "app.py", "print(1)\n", "feat: add app entry point")
    n, out = closure.harvest_checkpoint(tmp_path)
    assert n == 1 and out == note
    text = note.read_text(encoding="utf-8")
    assert "feat: add app entry point" in text and closure._HARVEST_HEADING in text
    assert (tmp_path / ".horus" / closure.CHECKPOINT_MARKER).is_file()


def test_harvest_idempotent(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _session_note(tmp_path)
    _work_commit(tmp_path, "app.py", "print(1)\n", "feat: one")
    closure.harvest_checkpoint(tmp_path)
    n, out = closure.harvest_checkpoint(tmp_path)
    assert n == 0 and out is None
    note = closure.recent_sessions(tmp_path, limit=1)[0]
    assert note.read_text(encoding="utf-8").count("feat: one") == 1


def test_harvest_first_run_takes_tip_only(tmp_path, monkeypatch):
    # No marker yet → harvest just the tip commit, not the whole history.
    _setup(tmp_path, monkeypatch)
    _session_note(tmp_path)
    _work_commit(tmp_path, "a.py", "1\n", "feat: first")
    _work_commit(tmp_path, "b.py", "2\n", "feat: second")
    n, _ = closure.harvest_checkpoint(tmp_path)
    assert n == 1


def test_harvest_multiple_commits_since_marker_in_order(tmp_path, monkeypatch):
    # With a marker, a later harvest catches every commit since it, oldest first
    # (the missed-commit / multi-commit-per-op path).
    _setup(tmp_path, monkeypatch)
    _session_note(tmp_path)
    _work_commit(tmp_path, "a.py", "1\n", "feat: first")
    closure.harvest_checkpoint(tmp_path)  # marker → 'first'
    _work_commit(tmp_path, "b.py", "2\n", "feat: second")
    _work_commit(tmp_path, "c.py", "3\n", "feat: third")
    n, note = closure.harvest_checkpoint(tmp_path)
    assert n == 2
    text = note.read_text(encoding="utf-8")
    assert text.index("feat: second") < text.index("feat: third")


def test_harvest_autocreates_note_when_none(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert closure.recent_sessions(tmp_path, limit=1) == []
    _work_commit(tmp_path, "app.py", "1\n", "feat: x")
    n, note = closure.harvest_checkpoint(tmp_path)
    assert n == 1 and note is not None and note.exists()


def test_harvest_clears_summary_freshness(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    note = _session_note(tmp_path)
    old = note.stat().st_mtime - 3600  # backdate so the work commit is "newer"
    os.utime(note, (old, old))
    _work_commit(tmp_path, "app.py", "1\n", "feat: work")
    assert any("work commit(s) since" in m for m in _msgs(tmp_path))
    closure.harvest_checkpoint(tmp_path)
    assert not any("work commit(s) since" in m for m in _msgs(tmp_path))
