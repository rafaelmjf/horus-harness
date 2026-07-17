"""`.horus/backlog/` card parsing + claim-time overlap check."""

import threading
from pathlib import Path

import pytest

from horus import backlog


def _mk_card(root: Path, name: str, *, status="open", parallel="", surface="", type="", body="Card body.\n"):
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}", "priority: later", "tier: sonnet", "created: 2026-07-11"]
    if parallel:
        lines.append(f"parallel: {parallel}")
    if surface:
        lines.append(f"surface: {surface}")
    if type:
        lines.append(f"type: {type}")
    lines.append("---")
    text = "\n".join(lines) + f"\n# {name.replace('-', ' ').title()}\n\n{body}"
    (hdir / f"{name}.md").write_text(text, encoding="utf-8")


def test_load_cards_reads_new_optional_fields(tmp_path):
    _mk_card(tmp_path, "a", parallel="exclusive", surface="horus/dashboard.py, horus/pty_*")
    cards = backlog.load_cards(tmp_path)
    assert len(cards) == 1
    c = cards[0]
    assert c.name == "a"
    assert c.parallel == "exclusive"
    assert c.surface == ("horus/dashboard.py", "horus/pty_*")


def test_load_cards_records_raw_frontmatter_fields(tmp_path):
    _mk_card(tmp_path, "a", parallel="exclusive", type="feature")
    card = backlog.load_cards(tmp_path)[0]

    # Every key the card carries, in file order — what the TUI field picker offers.
    assert [key for key, _value in card.fields] == [
        "status", "priority", "tier", "created", "parallel", "type",
    ]
    assert card.field_value("tier") == "sonnet"
    assert card.field_value("parallel") == "exclusive"
    assert card.field_value("vision_facet") == ""  # absent reads as empty, never raises


def test_cards_stay_hashable_with_raw_fields(tmp_path):
    _mk_card(tmp_path, "a")
    _mk_card(tmp_path, "b")
    assert len(set(backlog.load_cards(tmp_path))) == 2


def test_load_cards_back_compat_no_new_fields(tmp_path):
    _mk_card(tmp_path, "old-style")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].parallel == ""
    assert cards[0].surface == ()


def test_load_cards_reads_vision_facet_and_phase(tmp_path):
    hdir = tmp_path / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "c.md").write_text(
        '---\nstatus: open\nvision_facet: "PO lifecycle"\nphase: explore\n---\n# C\n',
        encoding="utf-8",
    )
    card = backlog.load_cards(tmp_path)[0]
    assert card.vision_facet == "PO lifecycle"
    assert card.phase == "explore"


def test_card_phase_defaults_to_converge_and_facet_empty(tmp_path):
    _mk_card(tmp_path, "d")
    card = backlog.load_cards(tmp_path)[0]
    assert card.phase == "converge"
    assert card.vision_facet == ""


def test_load_cards_type_defaults_to_task(tmp_path):
    _mk_card(tmp_path, "untyped")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].type == "task"


def test_load_cards_reads_explicit_type(tmp_path):
    _mk_card(tmp_path, "a-bug", type="bug")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].type == "bug"


def test_ship_stamps_provenance_preserves_content_and_moves_to_archive(tmp_path):
    _mk_card(tmp_path, "release-card", body="Keep this delivery context.\n")

    card = backlog.ship(tmp_path, "release-card", pr="42", sha="abc123")

    assert card is not None
    assert card.path == tmp_path / ".horus" / "backlog" / "archive" / "release-card.md"
    assert card.status == "shipped"
    assert card.shipped_pr == "42"
    assert card.shipped_sha == "abc123"
    assert not (tmp_path / ".horus" / "backlog" / "release-card.md").exists()
    assert "Keep this delivery context." in card.path.read_text(encoding="utf-8")
    assert backlog.find_card(tmp_path, "release-card") is None


def test_load_active_cards_excludes_terminal_root_cards_and_archive(tmp_path):
    _mk_card(tmp_path, "active")
    _mk_card(tmp_path, "stray-shipped", status="shipped")
    _mk_card(tmp_path, "stray-retired", status="retired")
    archive = backlog.archive_dir(tmp_path)
    archive.mkdir(parents=True)
    (archive / "archived.md").write_text(
        "---\nstatus: shipped\npriority: later\n---\n# Archived\n", encoding="utf-8",
    )

    assert [card.name for card in backlog.load_active_cards(tmp_path)] == ["active"]


def test_ship_refuses_to_destroy_existing_archive_card(tmp_path):
    _mk_card(tmp_path, "collision", body="Active copy.\n")
    archive = backlog.archive_dir(tmp_path)
    archive.mkdir(parents=True)
    archived = archive / "collision.md"
    archived.write_text("Archived copy.\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        backlog.ship(tmp_path, "collision", pr="42", sha="abc123")

    assert "Active copy." in (backlog.backlog_dir(tmp_path) / "collision.md").read_text(encoding="utf-8")
    assert archived.read_text(encoding="utf-8") == "Archived copy.\n"


def test_claim_no_other_in_progress_is_clean_even_without_fields(tmp_path):
    _mk_card(tmp_path, "solo")
    findings = backlog.claim_check(tmp_path, "solo")
    assert findings == []
    claimed, findings = backlog.claim(tmp_path, "solo")
    assert claimed
    assert findings == []
    assert backlog.find_card(tmp_path, "solo").status == "claimed"


def test_claim_overlapping_surface_warns_and_blocks(tmp_path):
    _mk_card(tmp_path, "a", status="claimed", surface="horus/dashboard.py")
    _mk_card(tmp_path, "b", surface="horus/dashboard.py, horus/pty_host.py")
    findings = backlog.claim_check(tmp_path, "b")
    assert any(f.level == "warn" and "overlap" in f.message for f in findings)
    claimed, findings = backlog.claim(tmp_path, "b")
    assert not claimed
    assert backlog.find_card(tmp_path, "b").status == "open"


def test_claim_overlapping_surface_force_proceeds(tmp_path):
    _mk_card(tmp_path, "a", status="claimed", surface="horus/dashboard.py")
    _mk_card(tmp_path, "b", surface="horus/dashboard.py")
    claimed, findings = backlog.claim(tmp_path, "b", force=True)
    assert claimed
    assert any(f.level == "warn" for f in findings)
    assert backlog.find_card(tmp_path, "b").status == "claimed"


def test_claim_non_overlapping_surface_proceeds_clean(tmp_path):
    _mk_card(tmp_path, "a", status="claimed", surface="horus/dashboard.py")
    _mk_card(tmp_path, "b", surface="horus/pty_host.py")
    findings = backlog.claim_check(tmp_path, "b")
    assert findings == []
    claimed, findings = backlog.claim(tmp_path, "b")
    assert claimed
    assert findings == []


def test_claim_exclusive_other_warns(tmp_path):
    _mk_card(tmp_path, "a", status="claimed", parallel="exclusive", surface="horus/foo.py")
    _mk_card(tmp_path, "b", surface="horus/bar.py")
    findings = backlog.claim_check(tmp_path, "b")
    assert any(f.level == "warn" and "exclusive" in f.message for f in findings)
    claimed, _ = backlog.claim(tmp_path, "b")
    assert not claimed


def test_claim_self_exclusive_warns(tmp_path):
    _mk_card(tmp_path, "a", status="claimed", surface="horus/foo.py")
    _mk_card(tmp_path, "b", parallel="exclusive", surface="horus/bar.py")
    findings = backlog.claim_check(tmp_path, "b")
    assert any(f.level == "warn" and "exclusive" in f.message for f in findings)


def test_claim_missing_surface_warns_cannot_verify(tmp_path):
    _mk_card(tmp_path, "a", status="claimed")  # no surface
    _mk_card(tmp_path, "b", surface="horus/bar.py")
    findings = backlog.claim_check(tmp_path, "b")
    assert any(f.level == "warn" and "can't be verified" in f.message for f in findings)
    claimed, _ = backlog.claim(tmp_path, "b")
    assert not claimed


def test_claim_unknown_card_fails(tmp_path):
    findings = backlog.claim_check(tmp_path, "nope")
    assert findings == [backlog.Finding("fail", "no backlog card named 'nope'")]
    claimed, findings = backlog.claim(tmp_path, "nope")
    assert not claimed
    assert any(f.level == "fail" for f in findings)


def test_claim_preserves_card_body_and_other_frontmatter(tmp_path):
    _mk_card(tmp_path, "solo", body="Some detail line.\nMore detail.\n")
    backlog.claim(tmp_path, "solo")
    text = (tmp_path / ".horus" / "backlog" / "solo.md").read_text(encoding="utf-8")
    assert "status: claimed" in text
    assert "priority: later" in text
    assert "Some detail line." in text


def test_claim_concurrent_overlapping_surface_is_serialized(tmp_path):
    """TOCTOU regression: two concurrent claims on overlapping-surface cards
    must never both succeed. Pre-fix, an unsynchronized load-check-write let
    both racers read the backlog before either wrote `status: claimed`, so
    the overlap check saw nothing in-progress and both claims went through
    (~17% of trials in manual repro). Run enough trials to make that failure
    mode near-certain if the lock regresses."""
    trials = 60
    name_a, name_b = "alpha", "gamma"
    for i in range(trials):
        # Fresh root per trial: a leftover `claimed` card from a prior trial
        # would itself overlap `src/alpha.py` and mask the race being tested.
        trial_root = tmp_path / f"trial{i}"
        _mk_card(trial_root, name_a, surface="src/alpha.py")
        _mk_card(trial_root, name_b, surface="src/alpha.py")

        results = {}
        barrier = threading.Barrier(2)

        def run(name):
            barrier.wait()
            claimed, _ = backlog.claim(trial_root, name)
            results[name] = claimed

        t1 = threading.Thread(target=run, args=(name_a,))
        t2 = threading.Thread(target=run, args=(name_b,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        claimed_count = sum(1 for v in results.values() if v)
        assert claimed_count == 1, f"trial {i}: expected exactly one claim, got {results}"

        statuses = {
            name_a: backlog.find_card(trial_root, name_a).status,
            name_b: backlog.find_card(trial_root, name_b).status,
        }
        assert sorted(statuses.values()) == ["claimed", "open"]


def test_surface_overlap_glob_matching():
    assert backlog.surface_overlap(("horus/pty_*",), ("horus/pty_host.py",))
    assert not backlog.surface_overlap(("horus/dashboard.py",), ("horus/pty_host.py",))


def test_claim_works_without_fcntl_like_windows(tmp_path, monkeypatch):
    """fcntl is Unix-only: a top-level `import fcntl` broke every `horus` CLI
    invocation on Windows (install-smoke, v0.0.36–v0.0.38). The claim lock must
    degrade to advisory when fcntl is unavailable, not fail to import."""
    import sys

    monkeypatch.setitem(sys.modules, "fcntl", None)  # `import fcntl` -> ImportError
    _mk_card(tmp_path, "win-card")
    claimed, findings = backlog.claim(tmp_path, "win-card")
    assert claimed
    assert findings == []
    assert backlog.find_card(tmp_path, "win-card").status == "claimed"


def test_add_review_creates_section_and_appends(tmp_path):
    _mk_card(tmp_path, "review-me")

    card = backlog.add_review(tmp_path, "review-me", author="rafa", verdict="approve", note="Looks right.")
    assert card is not None
    text = card.path.read_text(encoding="utf-8")
    assert "## Reviews" in text
    assert "— rafa (manual)" in text
    assert "Verdict: approve" in text
    assert text.rstrip().endswith("Looks right.")

    backlog.add_review(tmp_path, "review-me", author="sonnet", source="agent", note="Second pass.")
    text = card.path.read_text(encoding="utf-8")
    assert text.count("## Reviews") == 1  # one section, entries accumulate
    assert text.index("— rafa (manual)") < text.index("— sonnet (agent)")


def test_add_review_inserts_before_following_section(tmp_path):
    _mk_card(tmp_path, "sectioned", body="Body.\n\n## Reviews\n\n### 2026-07-01 — old (manual)\nVerdict: hold\n\n## Notes\n\nKeep me last.\n")

    backlog.add_review(tmp_path, "sectioned", author="rafa", note="Newer.")
    text = (tmp_path / ".horus" / "backlog" / "sectioned.md").read_text(encoding="utf-8")
    assert text.index("old (manual)") < text.index("Newer.") < text.index("## Notes")


def test_add_review_unknown_card_returns_none(tmp_path):
    _mk_card(tmp_path, "exists")
    assert backlog.add_review(tmp_path, "missing", author="rafa", note="x") is None


def test_add_review_preserves_frontmatter_and_body(tmp_path):
    _mk_card(tmp_path, "intact", status="claimed", surface="horus/cli.py")
    before = backlog.find_card(tmp_path, "intact")

    backlog.add_review(tmp_path, "intact", author="rafa", note="No side effects.")
    after = backlog.find_card(tmp_path, "intact")
    assert (after.status, after.surface, after.title) == (before.status, before.surface, before.title)


def test_hygiene_ignores_done_markers_inside_reviews_section(tmp_path):
    _mk_card(
        tmp_path,
        "reviewed",
        body="Body.\n\n## Reviews\n\n### 2026-07-14 — rafa (manual)\n\nDONE looks wrong here.\n- [x] I checked the repro\n",
    )
    assert backlog.hygiene_findings(tmp_path) == []


def test_hygiene_still_flags_done_markers_outside_reviews_section(tmp_path):
    _mk_card(tmp_path, "drifted", body="- [x] DONE: shipped it\n\n## Reviews\n\n### 2026-07-14 — rafa (manual)\nVerdict: ok\n")
    findings = backlog.hygiene_findings(tmp_path)
    assert any("lingering done" in f.message for f in findings)


# --- one-act acceptance: `horus datum close --card` (2026-07-14 frozen schema) --

def test_resolve_delivered_card_by_slug(tmp_path):
    _mk_card(tmp_path, "deliver-me")
    path = backlog.resolve_delivered_card("deliver-me", project_root=tmp_path)
    assert path == tmp_path / ".horus" / "backlog" / "deliver-me.md"


def test_resolve_delivered_card_by_slug_with_md_suffix(tmp_path):
    _mk_card(tmp_path, "deliver-me")
    path = backlog.resolve_delivered_card("deliver-me.md", project_root=tmp_path)
    assert path == tmp_path / ".horus" / "backlog" / "deliver-me.md"


def test_resolve_delivered_card_by_literal_path_wins_over_slug(tmp_path):
    # A literal existing path is used as-is — it can point at a card in a
    # DIFFERENT project than project_root, so it must never be re-resolved.
    other_project = tmp_path / "other"
    _mk_card(other_project, "elsewhere-card")
    literal = other_project / ".horus" / "backlog" / "elsewhere-card.md"
    path = backlog.resolve_delivered_card(str(literal), project_root=tmp_path)
    assert path == literal


def test_resolve_delivered_card_missing_raises_with_both_attempts_named(tmp_path):
    with pytest.raises(FileNotFoundError, match="no backlog card found"):
        backlog.resolve_delivered_card("nope", project_root=tmp_path)


def test_resolve_delivered_card_missing_no_project_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        backlog.resolve_delivered_card(str(tmp_path / "nope.md"), project_root=None)


def test_stamp_delivered_sets_status_done_and_shipped_date(tmp_path):
    _mk_card(tmp_path, "to-accept", surface="horus/foo.py")
    path = backlog.backlog_dir(tmp_path) / "to-accept.md"

    backlog.stamp_delivered(path, shipped_date="2026-07-14")

    card = backlog.find_card(tmp_path, "to-accept")
    assert card.status == "done"
    assert card.shipped == "2026-07-14"
    assert card.surface == ("horus/foo.py",)  # other frontmatter untouched


def test_stamp_delivered_preserves_body(tmp_path):
    _mk_card(tmp_path, "keep-body", body="Important detail.\n")
    path = backlog.backlog_dir(tmp_path) / "keep-body.md"
    backlog.stamp_delivered(path, shipped_date="2026-07-14")
    assert "Important detail." in path.read_text(encoding="utf-8")
