"""Tests for the git-aware closure routine."""

import os
import subprocess

from horus import closure, initialize
from horus.continuity import Finding


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


def test_pr_diff_freshness_never_blocks_a_merge_on_prose(tmp_path, monkeypatch):
    """One universal rule (2026-07-19): the commit is the durable delivery receipt and
    canonical prose folds at the next real boundary. There is no granularity knob that
    can turn a missing PRD update into a merge-blocking failure."""
    _setup(tmp_path, monkeypatch)
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _work_commit(tmp_path, "feature.py", "SHIPPED = True\n", "source only")

    findings = closure.pr_diff_freshness(tmp_path, base)

    assert findings[0].level == "ok"
    assert "durable in git" in findings[0].message
    assert "next real boundary" in findings[0].message
    assert not any(finding.level == "fail" for finding in findings)


def test_pr_diff_freshness_still_reports_included_continuity(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _work_commit(tmp_path, "feature.py", "SHIPPED = True\n", "source only")
    prd = tmp_path / ".horus" / "PRD.md"
    prd.write_text(prd.read_text(encoding="utf-8") + "\n<!-- closed -->\n", encoding="utf-8")
    _run(tmp_path, "add", ".horus/PRD.md")
    _run(tmp_path, "commit", "-m", "close continuity")

    findings = closure.pr_diff_freshness(tmp_path, base)

    assert findings[0].level == "ok"
    assert "canonical continuity" in findings[0].message


def test_project_frontmatter_can_no_longer_enforce_a_stricter_mode(tmp_path, monkeypatch):
    """A committed `continuity_granularity` is inert — the axis is gone, so a stale
    frontmatter key from an older project cannot resurrect a blocking gate."""
    _setup(tmp_path, monkeypatch)
    prd = tmp_path / ".horus" / "PRD.md"
    prd.write_text(
        prd.read_text(encoding="utf-8").replace(
            "---\n", "---\ncontinuity_granularity: delivery\n", 1,
        ),
        encoding="utf-8",
    )
    _run(tmp_path, "add", ".horus/PRD.md")
    _run(tmp_path, "commit", "-m", "stale strict continuity key")
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _work_commit(tmp_path, "feature.py", "SHIPPED = True\n", "source only")

    assert not hasattr(closure, "continuity_granularity")
    findings = closure.pr_diff_freshness(tmp_path, base)
    assert findings[0].level == "ok"


def test_pr_freshness_gate_batches_card_archival_to_the_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(closure.routines, "freshness_signals", lambda root: [])
    monkeypatch.setattr(
        closure.backlog,
        "hygiene_findings",
        lambda root: [Finding("warn", "done card awaits archive")],
    )
    monkeypatch.setattr(
        closure, "pr_diff_freshness", lambda root, base_ref: [Finding("ok", "diff ok")]
    )

    findings = closure.pr_freshness_gate(tmp_path, "origin/main")

    # Card archival is canonical continuity too, so it batches with the rest of the
    # prose rather than nagging on every PR.
    assert [finding.message for finding in findings] == ["diff ok"]


def test_pending_delivery_commits_are_portable_git_history_signal(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    _work_commit(tmp_path, "feature.py", "SHIPPED = True\n", "feat: first delivery")
    _work_commit(tmp_path, "second.py", "MORE = True\n", "feat: second delivery")

    pending = closure.pending_delivery_commits(tmp_path)
    assert [subject for _sha, subject in pending] == ["feat: first delivery", "feat: second delivery"]
    assert "2 delivery commit(s) pending" in closure.pending_delivery_findings(tmp_path)[0].message

    prd = tmp_path / ".horus" / "PRD.md"
    prd.write_text(prd.read_text(encoding="utf-8") + "\n<!-- boundary checkpoint -->\n", encoding="utf-8")
    _run(tmp_path, "add", ".horus/PRD.md")
    _run(tmp_path, "commit", "-m", "Update Horus continuity at handoff")

    assert closure.pending_delivery_commits(tmp_path) == []
    assert closure.pending_delivery_findings(tmp_path)[0].level == "ok"


def test_pr_diff_freshness_allows_continuity_only_and_fails_unknown_base(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    card = tmp_path / ".horus" / "backlog" / "finding.md"
    card.write_text("---\nstatus: open\n---\n", encoding="utf-8")
    _run(tmp_path, "add", ".horus/backlog/finding.md")
    _run(tmp_path, "commit", "-m", "continuity only")
    assert closure.pr_diff_freshness(tmp_path, base)[0].level == "ok"
    assert closure.pr_diff_freshness(tmp_path, "missing/ref")[0].level == "fail"


def test_clean_after_commit(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert any("continuity files committed" in m for m in _msgs(tmp_path))


def test_uncommitted_continuity_warns(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    assert any("uncommitted continuity" in m for m in _msgs(tmp_path))


def test_work_commit_since_recovery_note_does_not_create_closure_warning(tmp_path, monkeypatch):
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
    assert not any("since the latest session summary" in m for m in _msgs(tmp_path))

    os.utime(sess, (ct + 100, ct + 100))  # summary newer than the work commit
    assert not any("since the latest session summary" in m for m in _msgs(tmp_path))


def test_commit_continuity(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    (tmp_path / ".horus" / "roadmap.md").write_text("changed\n", encoding="utf-8")
    did, detail = closure.commit_continuity(tmp_path, "test closure")
    assert did and "committed" in detail
    did2, detail2 = closure.commit_continuity(tmp_path)
    assert not did2 and "nothing to commit" in detail2


def test_commit_continuity_harvests_work_then_seals_closing_commit(tmp_path, monkeypatch):
    """The closing commit must never be appended into the note it just committed."""
    _setup(tmp_path, monkeypatch)
    note = _session_note(tmp_path)
    _work_commit(tmp_path, "app.py", "print(1)\n", "feat: work before close")
    (tmp_path / ".horus" / "PRD.md").write_text("closing state\n", encoding="utf-8")

    did, detail = closure.commit_continuity(tmp_path, "close this session")

    assert did and "committed" in detail
    text = note.read_text(encoding="utf-8")
    assert "feat: work before close" in text
    assert "close this session" not in text
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    marker = tmp_path / ".horus" / closure.CHECKPOINT_MARKER
    assert marker.read_text(encoding="utf-8").strip() == head
    assert closure.harvest_checkpoint(tmp_path) == (0, None)


def test_commit_continuity_surfaces_residual_dirty_path_and_skips_push(tmp_path, monkeypatch):
    """Mimic a post-commit hook edit: the close reports the exact stranded path."""
    _setup(tmp_path, monkeypatch)
    prd = tmp_path / ".horus" / "PRD.md"
    prd.write_text("closing state\n", encoding="utf-8")
    original_git = closure._git
    calls = []

    def injecting_git(root, *args):
        calls.append(args)
        result = original_git(root, *args)
        if args and args[0] == "commit" and result is not None:
            prd.write_text("edited after commit\n", encoding="utf-8")
        return result

    monkeypatch.setattr(closure, "_git", injecting_git)
    did, detail = closure.commit_continuity(tmp_path, "close", push=True)

    assert did  # the commit happened, but the closure is not clean
    assert "residual dirty continuity after commit" in detail
    assert ".horus/PRD.md" in detail
    assert "push skipped" in detail
    assert not any(args and args[0] == "push" for args in calls)
    assert closure.continuity_dirty_paths(tmp_path) == [".horus/PRD.md"]


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


def test_checkpoint_gate_ignores_tracked_marker_rewritten_by_harvest(tmp_path, monkeypatch):
    """A legacy tracked marker must not make the checkpoint hook warn about itself."""
    _setup(tmp_path, monkeypatch)
    marker = tmp_path / ".horus" / closure.CHECKPOINT_MARKER
    marker.write_text("legacy\n", encoding="utf-8")
    _run(tmp_path, "add", "-f", ".horus/.consolidated-to")
    _run(tmp_path, "commit", "-m", "track legacy marker")
    _work_commit(tmp_path, "app.py", "print(1)\n", "work after legacy closure")

    closure.harvest_checkpoint(tmp_path)

    assert " M .horus/.consolidated-to" in subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--short"],
        capture_output=True, text=True, check=True,
    ).stdout
    msgs = _checkpoint_msgs(tmp_path)
    assert any(level == "ok" and "working tree clean" in message for level, message in msgs)
    assert not any(level == "warn" and "uncommitted change" in message for level, message in msgs)


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


def test_harvest_does_not_autocreate_note_when_none(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert closure.recent_sessions(tmp_path, limit=1) == []
    _work_commit(tmp_path, "app.py", "1\n", "feat: x")
    n, note = closure.harvest_checkpoint(tmp_path)
    assert (n, note) == (0, None)
    assert closure.recent_sessions(tmp_path, limit=1) == []
    assert (tmp_path / ".horus" / closure.CHECKPOINT_MARKER).is_file()


def test_harvest_existing_note_never_affects_closure_freshness(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    note = _session_note(tmp_path)
    old = note.stat().st_mtime - 3600  # backdate so the work commit is "newer"
    os.utime(note, (old, old))
    _work_commit(tmp_path, "app.py", "1\n", "feat: work")
    assert not any("work commit(s) since" in m for m in _msgs(tmp_path))
    closure.harvest_checkpoint(tmp_path)
    assert not any("work commit(s) since" in m for m in _msgs(tmp_path))


def test_continuity_dirty_tracks_horus_changes_only(tmp_path, monkeypatch):
    root = _setup(tmp_path, monkeypatch)
    assert not closure.continuity_dirty(root)

    (root / "unrelated.py").write_text("x = 1\n", encoding="utf-8")
    assert not closure.continuity_dirty(root)  # non-continuity files don't count

    card = root / ".horus" / "backlog" / "some-card.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text("---\nstatus: open\n---\n\n# Some card\n", encoding="utf-8")
    assert closure.continuity_dirty(root)

    _run(root, "add", ".horus")
    _run(root, "commit", "-m", "card")
    assert not closure.continuity_dirty(root)

    card.unlink()
    assert closure.continuity_dirty(root)  # tracked deletions count too
    assert closure.continuity_dirty_paths(root) == [".horus/backlog/some-card.md"]


def test_continuity_dirty_false_outside_git(tmp_path):
    assert not closure.continuity_dirty(tmp_path)


# --- one-act acceptance: target continuity freshness probe (2026-07-14) -----

def _write_prd(root, *, last_updated):
    hdir = root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "PRD.md").write_text(
        f"---\nstatus: active\nlast_updated: {last_updated}\n---\n\n# PRD\n", encoding="utf-8"
    )


def _write_session(root, *, date, name="note.md"):
    sessions = root / ".horus" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / name).write_text(f"---\ndate: {date}\n---\n\n# Session\n", encoding="utf-8")


def test_target_continuity_staleness_none_without_completed_at(tmp_path):
    _write_prd(tmp_path, last_updated="2026-01-01")
    assert closure.target_continuity_staleness(tmp_path, completed_at=None) is None


def test_target_continuity_staleness_none_without_target_prd(tmp_path):
    assert closure.target_continuity_staleness(tmp_path, completed_at="2026-07-14T12:00:00+00:00") is None


def test_target_continuity_staleness_fresh_when_last_updated_matches_completion(tmp_path):
    _write_prd(tmp_path, last_updated="2026-07-14")
    warning = closure.target_continuity_staleness(tmp_path, completed_at="2026-07-14T12:00:00+00:00")
    assert warning is None


def test_target_continuity_staleness_warns_when_prd_predates_completion(tmp_path):
    _write_prd(tmp_path, last_updated="2026-07-10")
    warning = closure.target_continuity_staleness(tmp_path, completed_at="2026-07-14T12:00:00+00:00")
    assert warning is not None
    assert "stale" in warning and "2026-07-10" in warning and "2026-07-14" in warning


def test_target_continuity_staleness_uses_freshest_of_prd_and_session_note(tmp_path):
    # PRD itself is stale, but a session note landed the same day the run
    # completed -- the freshest of the two signals wins, so no warning fires.
    _write_prd(tmp_path, last_updated="2026-07-01")
    _write_session(tmp_path, date="2026-07-14")
    warning = closure.target_continuity_staleness(tmp_path, completed_at="2026-07-14T12:00:00+00:00")
    assert warning is None


def test_target_continuity_staleness_never_auto_fixes(tmp_path):
    # This probe is print-only: it must never write to the target's continuity.
    _write_prd(tmp_path, last_updated="2026-07-01")
    before = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    closure.target_continuity_staleness(tmp_path, completed_at="2026-07-14T12:00:00+00:00")
    after = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert before == after


# --- parallel-delivery reconciliation (item 5) -------------------------------

from horus import registry as _registry  # noqa: E402


def _rec(session_id, project, status="running", agent="claude"):
    return _registry.SessionRecord(session_id=session_id, agent=agent, project=project, status=status)


def _fake_reg(records):
    class _Reg:
        @classmethod
        def default(cls):
            r = cls()
            return r
        def snapshot(self):
            return records
    return _Reg


def test_parallel_deliveries_names_a_live_cosession(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([_rec("sibling-1", str(tmp_path))]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: False)  # skip PR probe
    signals, pr_checked = closure.parallel_deliveries(tmp_path)
    assert pr_checked is False
    assert [s.kind for s in signals] == ["live-session"]
    assert "sibling-1"[:8] in signals[0].detail


def test_parallel_deliveries_excludes_self(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([_rec("me-123", str(tmp_path))]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: False)
    monkeypatch.setenv("HORUS_RUN_SESSION_ID", "me-123")
    signals, _ = closure.parallel_deliveries(tmp_path)
    assert signals == []


def test_parallel_deliveries_ignores_a_non_running_session(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([_rec("done-1", str(tmp_path), status="exited")]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: False)
    signals, _ = closure.parallel_deliveries(tmp_path)
    assert signals == []


def _gh_stub(open_prs, merged_prs):
    def stub(root, *args):
        state = args[args.index("--state") + 1] if "--state" in args else ""
        return {"open": open_prs, "merged": merged_prs}.get(state)
    return stub


def test_parallel_deliveries_flags_open_sibling_pr_not_current_branch(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: True)
    monkeypatch.setattr(closure, "_git", lambda root, *a: "my-branch" if a[:1] == ("rev-parse",) else "")
    monkeypatch.setattr(closure, "_canonical_checkpoint", lambda root: "checkpointsha")
    monkeypatch.setattr(closure, "_gh_json", _gh_stub(
        open_prs=[
            {"number": 7, "headRefName": "other-branch", "title": "sibling"},
            {"number": 8, "headRefName": "my-branch", "title": "mine — skip"},
        ],
        merged_prs=[],
    ))
    signals, pr_checked = closure.parallel_deliveries(tmp_path)
    assert pr_checked is True
    kinds = [(s.kind, s.ref) for s in signals]
    assert ("open-pr", "7") in kinds
    assert ("open-pr", "8") not in kinds  # current branch is not "parallel"


def test_parallel_deliveries_flags_only_uncovered_merged_pr(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: True)
    monkeypatch.setattr(closure, "_git", lambda root, *a: "my-branch")
    monkeypatch.setattr(closure, "_canonical_checkpoint", lambda root: "checkpointsha")
    # covered → ancestor True (skip); uncovered → False (flag); unknown → None (skip)
    ancestry = {"coveredsha": True, "uncoveredsha": False, "unknownsha": None}
    monkeypatch.setattr(closure, "_is_ancestor", lambda root, sha, of: ancestry[sha])
    monkeypatch.setattr(closure, "_gh_json", _gh_stub(
        open_prs=[],
        merged_prs=[
            {"number": 1, "mergeCommit": {"oid": "coveredsha"}},
            {"number": 2, "mergeCommit": {"oid": "uncoveredsha"}},
            {"number": 3, "mergeCommit": {"oid": "unknownsha"}},
        ],
    ))
    signals, _ = closure.parallel_deliveries(tmp_path)
    refs = [s.ref for s in signals if s.kind == "merged-pr"]
    assert refs == ["2"]  # only the uncovered merge


def test_findings_are_empty_when_gh_unavailable_and_no_cosession(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: True)
    monkeypatch.setattr(closure, "_git", lambda root, *a: "my-branch")
    monkeypatch.setattr(closure, "_gh_json", lambda root, *a: None)  # gh absent/offline
    findings = closure.parallel_delivery_findings(tmp_path)
    assert findings == []  # no false "all clear"


def test_findings_report_ok_when_checked_and_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(_registry, "Registry", _fake_reg([]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: True)
    monkeypatch.setattr(closure, "_git", lambda root, *a: "my-branch")
    monkeypatch.setattr(closure, "_canonical_checkpoint", lambda root: "cp")
    monkeypatch.setattr(closure, "_gh_json", _gh_stub(open_prs=[], merged_prs=[]))
    findings = closure.parallel_delivery_findings(tmp_path)
    assert len(findings) == 1 and findings[0].level == "ok"


def test_boundary_gate_includes_parallel_findings(tmp_path, monkeypatch):
    monkeypatch.setattr(closure, "freshness_gate", lambda root: [])
    monkeypatch.setattr(closure, "pending_delivery_commits", lambda root: [])
    monkeypatch.setattr(closure, "parallel_deliveries",
                        lambda root, **k: ([closure.ParallelSignal("open-pr", "9", "PR #9 open on x")], True))
    findings = closure.boundary_freshness_gate(tmp_path)
    assert any("parallel delivery pending" in f.message and "PR #9" in f.message for f in findings)


def test_parallel_delivery_findings_are_info_not_warn(tmp_path, monkeypatch):
    """A named sibling PR must PRINT but never count toward warn/fail aggregation —
    the signal is advisory, not a close-blocking gate (see parallel-signal-informational-not-verdict)."""
    monkeypatch.setattr(_registry, "Registry", _fake_reg([]))
    monkeypatch.setattr(closure, "is_git_repo", lambda root: True)
    monkeypatch.setattr(closure, "_git", lambda root, *a: "my-branch")
    monkeypatch.setattr(closure, "_canonical_checkpoint", lambda root: "checkpointsha")
    monkeypatch.setattr(closure, "_gh_json", _gh_stub(
        open_prs=[{"number": 117, "headRefName": "other-branch", "title": "sibling"}],
        merged_prs=[],
    ))
    findings = closure.parallel_delivery_findings(tmp_path)
    assert len(findings) == 1
    assert findings[0].level == "info"
    assert "PR #117" in findings[0].message
    assert findings[0].level not in ("warn", "fail")
