"""`.horus/backlog/` card parsing + claim-time overlap check."""

import threading
from pathlib import Path

import pytest

from horus import backlog, cli


def _mk_card(
    root: Path,
    name: str,
    *,
    status="open",
    parallel="",
    surface="",
    type="",
    readiness="",
    readiness_reason="",
    autonomy="",
    last_refined="",
    depends_on="",
    order="",
    priority="later",
    body="Card body.\n",
):
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}", f"priority: {priority}", "tier: sonnet", "created: 2026-07-11"]
    if order != "":
        lines.append(f"order: {order}")
    if parallel:
        lines.append(f"parallel: {parallel}")
    if surface:
        lines.append(f"surface: {surface}")
    if type:
        lines.append(f"type: {type}")
    if readiness:
        lines.append(f"readiness: {readiness}")
    if readiness_reason:
        lines.append(f'readiness_reason: "{readiness_reason}"')
    if autonomy:
        lines.append(f"autonomy: {autonomy}")
    if last_refined:
        lines.append(f"last_refined: {last_refined}")
    if depends_on:
        lines.append(f"depends-on: {depends_on}")
    lines.append("---")
    text = "\n".join(lines) + f"\n# {name.replace('-', ' ').title()}\n\n{body}"
    (hdir / f"{name}.md").write_text(text, encoding="utf-8")


def test_load_cards_reads_new_optional_fields(tmp_path):
    _mk_card(
        tmp_path,
        "a",
        parallel="exclusive",
        surface="horus/dashboard.py, horus/pty_*",
        readiness="ready",
        autonomy="eligible",
        last_refined="2026-07-19",
    )
    cards = backlog.load_cards(tmp_path)
    assert len(cards) == 1
    c = cards[0]
    assert c.name == "a"
    assert c.parallel == "exclusive"
    assert c.surface == ("horus/dashboard.py", "horus/pty_*")
    assert c.readiness == "ready"
    assert c.autonomy == "eligible"
    assert c.last_refined == "2026-07-19"


def test_load_cards_records_raw_frontmatter_fields(tmp_path):
    _mk_card(tmp_path, "a", parallel="exclusive", type="feature")
    card = backlog.load_cards(tmp_path)[0]

    # Every key the card carries, in file order — what the TUI field picker offers.
    assert [key for key, _value in card.fields] == [
        "status", "priority", "tier", "created", "parallel", "type",
    ]
    assert card.field_value("tier") == "sonnet"
    assert card.field_value("parallel") == "exclusive"
    assert card.field_value("topic") == ""  # absent reads as empty, never raises


def test_cards_stay_hashable_with_raw_fields(tmp_path):
    _mk_card(tmp_path, "a")
    _mk_card(tmp_path, "b")
    assert len(set(backlog.load_cards(tmp_path))) == 2


def test_load_cards_back_compat_no_new_fields(tmp_path):
    _mk_card(tmp_path, "old-style")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].parallel == ""
    assert cards[0].surface == ()
    assert cards[0].readiness == ""
    assert backlog.readiness_queue(cards[0]) == backlog.QUEUE_UNCLASSIFIED


def test_load_cards_reads_topic_and_ignores_legacy_grouping_keys(tmp_path):
    hdir = tmp_path / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "c.md").write_text(
        '---\nstatus: open\ntopic: "po-lifecycle"\nvision_facet: legacy\nphase: explore\n---\n# C\n',
        encoding="utf-8",
    )
    card = backlog.load_cards(tmp_path)[0]
    assert card.topic == "po-lifecycle"


def test_card_topic_defaults_to_empty(tmp_path):
    _mk_card(tmp_path, "d")
    card = backlog.load_cards(tmp_path)[0]
    assert card.topic == ""


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
    findings = backlog.hygiene_findings(tmp_path)
    assert not any("lingering done" in finding.message for finding in findings)


def test_hygiene_still_flags_done_markers_outside_reviews_section(tmp_path):
    _mk_card(tmp_path, "drifted", body="- [x] DONE: shipped it\n\n## Reviews\n\n### 2026-07-14 — rafa (manual)\nVerdict: ok\n")
    findings = backlog.hygiene_findings(tmp_path)
    assert any("lingering done" in f.message for f in findings)


def test_readiness_groups_render_all_six_queues_in_canonical_order(tmp_path):
    _mk_card(tmp_path, "eligible-high", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "eligible-low", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "attended", readiness="ready", autonomy="attended")
    _mk_card(tmp_path, "shaping", readiness="shaping", readiness_reason="needs scope")
    _mk_card(tmp_path, "gated", readiness="gated", readiness_reason="wait for API")
    _mk_card(tmp_path, "deferred", readiness="deferred", readiness_reason="owner review")
    _mk_card(tmp_path, "legacy")

    groups = backlog.readiness_groups(backlog.load_active_cards(tmp_path))

    assert [group.key for group in groups] == list(backlog.READINESS_QUEUE_ORDER)
    assert [len(group.cards) for group in groups] == [2, 1, 1, 1, 1, 1]
    assert [card.name for card in groups[0].cards] == ["eligible-high", "eligible-low"]


def test_scheduler_candidate_gate_accepts_only_ready_eligible(tmp_path):
    _mk_card(tmp_path, "eligible", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "attended", readiness="ready", autonomy="attended")
    _mk_card(tmp_path, "shaping", readiness="shaping", readiness_reason="needs scope")
    _mk_card(tmp_path, "gated", readiness="gated", readiness_reason="wait for API")
    _mk_card(tmp_path, "deferred", readiness="deferred", readiness_reason="owner review")
    _mk_card(tmp_path, "legacy")
    cards = {card.name: card for card in backlog.load_active_cards(tmp_path)}

    assert backlog.is_autonomous_candidate(cards["eligible"])
    assert backlog.autonomy_block_reason(cards["eligible"]) == ""
    for name in ("attended", "shaping", "gated", "deferred", "legacy"):
        assert not backlog.is_autonomous_candidate(cards[name])
        assert backlog.autonomy_block_reason(cards[name])
    assert "owner presence" in backlog.autonomy_block_reason(cards["attended"])
    assert "wait for API" in backlog.autonomy_block_reason(cards["gated"])
    assert "backlog-refine" in backlog.autonomy_block_reason(cards["legacy"])


def test_readiness_validation_warns_without_inference(tmp_path):
    _mk_card(tmp_path, "ready-missing-autonomy", readiness="ready")
    _mk_card(tmp_path, "shaping-missing-reason", readiness="shaping")
    _mk_card(
        tmp_path,
        "gated-with-autonomy",
        readiness="gated",
        readiness_reason="blocked",
        autonomy="eligible",
    )
    _mk_card(tmp_path, "invalid", readiness="eventually")
    cards = {card.name: card for card in backlog.load_active_cards(tmp_path)}

    findings = {name: backlog.readiness_findings(card) for name, card in cards.items()}
    assert any("missing autonomy" in item.message for item in findings["ready-missing-autonomy"])
    assert any("without readiness_reason" in item.message for item in findings["shaping-missing-reason"])
    assert any("autonomy belongs only" in item.message for item in findings["gated-with-autonomy"])
    assert any("invalid readiness" in item.message for item in findings["invalid"])
    assert all(backlog.readiness_queue(card) == backlog.QUEUE_UNCLASSIFIED for card in (
        cards["ready-missing-autonomy"], cards["invalid"],
    ))


def test_card_writers_preserve_readiness_fields(tmp_path):
    _mk_card(
        tmp_path,
        "preserved",
        readiness="ready",
        autonomy="eligible",
        last_refined="2026-07-19",
    )
    path = backlog.backlog_dir(tmp_path) / "preserved.md"

    backlog.set_priority(path, "high")
    backlog.claim(tmp_path, "preserved")

    card = backlog.find_card(tmp_path, "preserved")
    assert (card.readiness, card.autonomy, card.last_refined) == (
        "ready", "eligible", "2026-07-19",
    )


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


def test_readiness_count_summary_uses_canonical_labels():
    counts = {
        backlog.QUEUE_READY_ELIGIBLE: 2,
        backlog.QUEUE_READY_ATTENDED: 3,
        backlog.QUEUE_SHAPING: 39,
        backlog.QUEUE_GATED: 6,
        backlog.QUEUE_DEFERRED: 24,
        backlog.QUEUE_UNCLASSIFIED: 0,
    }
    labels = backlog.READINESS_QUEUE_LABELS
    ready, rest = backlog.readiness_count_summary(counts)

    assert ready == (
        f"{labels[backlog.QUEUE_READY_ELIGIBLE]} 2 · "
        f"{labels[backlog.QUEUE_READY_ATTENDED]} 3"
    )
    # Every rest-queue label comes from the canonical map, not a hardcoded copy.
    for key in (
        backlog.QUEUE_SHAPING,
        backlog.QUEUE_GATED,
        backlog.QUEUE_DEFERRED,
        backlog.QUEUE_UNCLASSIFIED,
    ):
        assert f"{labels[key]} {counts[key]}" in rest


# ---------------------------------------------------------------------------
# Sparse `order:` — the owner-approved execution sequence
# ---------------------------------------------------------------------------

def test_order_parses_as_int_and_absent_stays_unsequenced(tmp_path):
    _mk_card(tmp_path, "stamped", order="20")
    _mk_card(tmp_path, "bare")

    cards = {c.name: c for c in backlog.load_cards(tmp_path)}

    assert cards["stamped"].order == 20
    assert cards["bare"].order is None


def test_non_integer_order_is_unsequenced_not_coerced(tmp_path):
    """A malformed stamp must never be guessed into a position — it drops to the
    pool and says so, rather than silently reordering the owner's plan."""
    _mk_card(tmp_path, "vague", order="soon")
    _mk_card(tmp_path, "fractional", order="1.5")

    cards = {c.name: c for c in backlog.load_cards(tmp_path)}
    assert cards["vague"].order is None
    assert cards["fractional"].order is None

    messages = [f.message for f in backlog.order_findings(list(cards.values()))]
    assert any("non-integer order 'soon'" in m for m in messages)
    assert any("non-integer order '1.5'" in m for m in messages)


def test_ordered_cards_sort_by_order_ahead_of_the_unsequenced_pool(tmp_path):
    # Deliberately adversarial: alphabetical order, priority, and `order:` all
    # disagree, so only the documented sort key produces this sequence.
    _mk_card(tmp_path, "zebra", order="10", priority="low", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "alpha", order="20", priority="high", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "beta", priority="high", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "yak", priority="low", readiness="ready", autonomy="eligible")

    names = [c.name for c in sorted(backlog.load_cards(tmp_path), key=backlog.readiness_sort_key)]

    # Stamped cards first in stamp order; the pool keeps today's priority ordering.
    assert names == ["zebra", "alpha", "beta", "yak"]


def test_order_sequences_within_a_queue_not_across_queues(tmp_path):
    """Every renderer prints per readiness queue, so `order` is a per-queue
    sequence: a Deferred card stamped 10 never outranks a Ready card stamped 20."""
    _mk_card(tmp_path, "ready-later", order="20", readiness="ready", autonomy="eligible")
    _mk_card(
        tmp_path, "deferred-first", order="10",
        readiness="deferred", readiness_reason="waiting on the owner",
    )

    names = [c.name for c in sorted(backlog.load_cards(tmp_path), key=backlog.readiness_sort_key)]

    assert names == ["ready-later", "deferred-first"]


def test_unordered_backlog_sorts_exactly_as_before(tmp_path):
    """Zero migration: with no `order:` anywhere the sequence is unchanged."""
    _mk_card(tmp_path, "b-card", priority="high", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "a-card", priority="low", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "c-card", priority="high", readiness="ready", autonomy="eligible")

    names = [c.name for c in sorted(backlog.load_cards(tmp_path), key=backlog.readiness_sort_key)]

    assert names == ["b-card", "c-card", "a-card"]  # priority, then filename


def test_duplicate_order_warns_within_a_queue_only(tmp_path):
    _mk_card(tmp_path, "first", order="20", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "second", order="20", readiness="ready", autonomy="eligible")
    _mk_card(
        tmp_path, "elsewhere", order="20",
        readiness="shaping", readiness_reason="still scoping",
    )

    messages = [f.message for f in backlog.order_findings(backlog.load_cards(tmp_path))]
    dupes = [m for m in messages if "duplicate order" in m]

    assert len(dupes) == 1
    assert "first, second" in dupes[0]
    assert "Ready—Autonomous eligible" in dupes[0]
    assert "elsewhere" not in dupes[0]  # a repeat in another queue is a separate sequence


def test_hygiene_findings_reports_duplicate_order(tmp_path):
    """The check rides consolidate and `close --check`, where card hygiene lives."""
    _mk_card(tmp_path, "one", order="10", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "two", order="10", readiness="ready", autonomy="eligible")

    messages = [f.message for f in backlog.hygiene_findings(tmp_path)]

    assert any("duplicate order 10" in m for m in messages)


def _mk_archived(
    root: Path,
    name: str,
    *,
    created: str,
    pr: str = "",
    sha: str = "",
    status: str = "shipped",
) -> None:
    adir = root / ".horus" / "backlog" / "archive"
    adir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}", "priority: high", "tier: sonnet", f"created: {created}"]
    if pr:
        lines.append(f"shipped_pr: {pr}")
    if sha:
        lines.append(f"shipped_sha: {sha}")
    lines += ["---", "", f"# {name} — a delivered thing", ""]
    (adir / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def test_load_archived_cards_reads_the_previously_write_only_archive(tmp_path):
    # `ship` moved cards into archive/ and nothing could read them back, so the
    # delivery record was reachable only by opening files by hand.
    _mk_archived(tmp_path, "older", created="2026-07-01", pr="100", sha="a" * 40)
    _mk_archived(tmp_path, "newer", created="2026-07-30", pr="200", sha="b" * 40)

    cards = backlog.load_archived_cards(tmp_path)

    assert [c.name for c in cards] == ["newer", "older"]  # newest delivery first
    assert cards[0].shipped_pr == "200" and cards[0].shipped_sha == "b" * 40


def test_load_archived_cards_sorts_undated_last_and_tolerates_no_archive(tmp_path):
    assert backlog.load_archived_cards(tmp_path) == []
    _mk_archived(tmp_path, "dated", created="2026-07-01")
    _mk_archived(tmp_path, "undated", created="")

    assert [c.name for c in backlog.load_archived_cards(tmp_path)] == ["dated", "undated"]


def test_shelved_cards_leave_the_working_queue_but_stay_retrievable(tmp_path):
    """Shelving is not closing, and not deleting.

    `deferred` failed as the set-aside state: 26 cards carried it, all were screened
    twice on 2026-07-28, and none moved — "we'll get to it" is a queue that never
    drains. `shelved` says the owner declined to DECIDE, so the card leaves every
    working view while its file and text stay exactly where they were.
    """
    _mk_card(tmp_path, "live")
    _mk_card(tmp_path, "boxed", status=backlog.SHELVED_STATUS)

    # Gone from the working queue...
    assert [c.name for c in backlog.load_active_cards(tmp_path)] == ["live"]
    # ...but still on disk, unmoved, and readable on demand.
    assert (tmp_path / ".horus" / "backlog" / "boxed.md").is_file()
    assert [c.name for c in backlog.load_shelved_cards(tmp_path)] == ["boxed"]
    # And NOT in the archive: shelving is not an outcome, so it never enters the
    # closed ledger where it would be counted as decided.
    assert backlog.load_archived_cards(tmp_path) == []


def test_inactive_statuses_have_exactly_one_definition(tmp_path):
    """`fleet_review` kept a hand-copied duplicate of this list until 2026-08-01.

    A second copy is how a status gets added in one place and silently ignored in
    the other — the fleet digest would have gone on showing shelved cards as live
    work forever, and nothing would have failed.
    """
    from horus import fleet_review

    assert backlog.SHELVED_STATUS in backlog.INACTIVE_STATUSES
    assert set(fleet_review._INACTIVE_STATUSES) == set(backlog.INACTIVE_STATUSES)


def test_partition_archived_separates_delivered_from_killed(tmp_path):
    """The archive is the CLOSED ledger, not the delivery ledger.

    `ship` moves in work that merged; a convergence pass moves in work that was
    killed. Counting them together overstates delivery — on this repo 22 of 132
    archived cards had never shipped while the read-out headed all 132 "Shipped",
    which misled a planning session on 2026-08-01 into recording a retired card
    as delivered.
    """
    _mk_archived(tmp_path, "merged", created="2026-07-30", pr="200", sha="b" * 40)
    _mk_archived(tmp_path, "killed", created="2026-07-20", status="retired")
    _mk_archived(tmp_path, "absorbed", created="2026-07-10", status="folded-in")

    delivered, closed = backlog.partition_archived(backlog.load_archived_cards(tmp_path))

    assert [c.name for c in delivered] == ["merged"]
    assert sorted(c.name for c in closed) == ["absorbed", "killed"]
    # A killed card legitimately carries no delivery provenance, so delivery must
    # key on status rather than on shipped_pr/shipped_sha being present.
    assert all(not c.shipped_pr and not c.shipped_sha for c in closed)


def test_archived_listing_does_not_count_killed_cards_as_shipped(tmp_path, capsys):
    _mk_archived(tmp_path, "merged", created="2026-07-30", pr="200", sha="b" * 40)
    _mk_archived(tmp_path, "killed", created="2026-07-20", status="retired")

    rc = cli.main(["backlog", "list", "--archived", "--path", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "Shipped (1)" in out
    assert "Closed without shipping (1)" in out
    assert "Shipped (2)" not in out  # the defect this test exists for
    assert "killed" in out and "[retired]" in out


def test_archived_cards_are_still_absent_from_the_active_list(tmp_path):
    # The archive read path must not leak shipped work into the working queue.
    _mk_card(tmp_path, "live")
    _mk_archived(tmp_path, "done", created="2026-07-01")

    assert [c.name for c in backlog.load_active_cards(tmp_path)] == ["live"]
    assert [c.name for c in backlog.load_archived_cards(tmp_path)] == ["done"]


def test_a_bug_can_never_be_shelved(tmp_path):
    """The shelf is for work whose problem may never come; a bug's already did.

    Shelving a bug boxes a known real defect, and because the shelf is invisible
    to every working view
    the fleet row's bug count then cannot surface it — the count reads a
    reassuring zero while the defect is still there.
    """
    _mk_card(tmp_path, "boxed-bug", status=backlog.SHELVED_STATUS, type="bug")

    findings = backlog.hygiene_findings(tmp_path)
    offending = [f for f in findings if "cannot be shelved" in f.message]

    assert offending, "shelving a bug must be reported"
    # `fail`, not `warn`: `close_check_healthy` treats fail as blocking, so the
    # combination cannot reach main quietly.
    assert offending[0].level == "fail"
    assert "retire" in offending[0].message  # the legitimate alternative is named


def test_shelving_a_non_bug_is_silent(tmp_path):
    """The guard is about bugs specifically, not about shelving."""
    _mk_card(tmp_path, "boxed-idea", status=backlog.SHELVED_STATUS, type="feature")
    _mk_card(tmp_path, "boxed-spike", status=backlog.SHELVED_STATUS, type="chore")

    assert not [f for f in backlog.hygiene_findings(tmp_path) if "cannot be shelved" in f.message]


def test_a_shelved_bug_fails_the_close_gate(tmp_path):
    """End to end: the guard actually blocks, rather than printing into the void."""
    from horus import closure

    _mk_card(tmp_path, "live")
    assert closure.close_check_healthy(tmp_path, backlog.hygiene_findings(tmp_path))

    _mk_card(tmp_path, "boxed-bug", status=backlog.SHELVED_STATUS, type="bug")
    assert not closure.close_check_healthy(tmp_path, backlog.hygiene_findings(tmp_path))


def test_an_active_card_gated_on_a_shelved_blocker_is_reported(tmp_path):
    """A gate that can never lift is worse than either state on its own.

    `depends-on` only means something while the blocker can still move. When the
    2026-08-01 sweep shelved `account-login-verb`, the active bug
    `codex-isolated-config-leak` kept listing as open work that nothing could ever
    make schedulable — and three consecutive continuity closes carried it with no
    surface naming it. The sweep could not have shelved the bug itself
    (`test_a_bug_can_never_be_shelved`), so the defect entered one level up.
    """
    _mk_card(tmp_path, "blocker", status=backlog.SHELVED_STATUS, type="feature")
    _mk_card(tmp_path, "dependent", type="bug", depends_on="blocker")

    offending = [f for f in backlog.hygiene_findings(tmp_path) if "can never lift" in f.message]

    assert offending, "an active card gated on a shelved blocker must be reported"
    assert "dependent" in offending[0].message and "blocker" in offending[0].message
    # `warn`, not `fail`: first deterministic signal for this class, and a fail
    # would reach the required PR check, which never blocks a merge on prose.
    assert offending[0].level == "warn"


def test_a_retired_blocker_strands_a_dependent_too(tmp_path):
    """`retired` is decided-dead, which strands a dependent exactly like the shelf."""
    _mk_card(tmp_path, "blocker", status="retired", type="feature")
    _mk_card(tmp_path, "dependent", type="bug", depends_on="blocker")

    assert [f for f in backlog.hygiene_findings(tmp_path) if "can never lift" in f.message]


def test_a_delivered_blocker_satisfies_the_gate(tmp_path):
    """The opposite case: a shipped blocker LIFTED the gate — never report it."""
    _mk_card(tmp_path, "blocker", status="shipped", type="feature")
    _mk_card(tmp_path, "dependent", type="bug", depends_on="blocker")

    assert not [f for f in backlog.hygiene_findings(tmp_path) if "can never lift" in f.message]


def test_a_dangling_dependency_is_reported_but_an_archived_one_is_not(tmp_path):
    """A name that never existed is a typo; a name in the archive is delivered."""
    _mk_card(tmp_path, "typo-dep", type="bug", depends_on="no-such-card")
    _mk_card(tmp_path, "archived-dep", type="bug", depends_on="was-shipped")
    adir = tmp_path / ".horus" / "backlog" / "archive"
    adir.mkdir(parents=True, exist_ok=True)
    (adir / "was-shipped.md").write_text(
        "---\nstatus: shipped\npriority: later\ntier: sonnet\ncreated: 2026-07-11\n---\n# Was Shipped\n",
        encoding="utf-8",
    )

    dangling = [f for f in backlog.hygiene_findings(tmp_path) if "does not exist" in f.message]

    assert [f for f in dangling if "typo-dep" in f.message]
    assert not [f for f in dangling if "archived-dep" in f.message]


def test_an_inactive_card_gated_on_a_shelved_blocker_is_silent(tmp_path):
    """The defect is a card that still READS as open. A shelved dependent does not."""
    _mk_card(tmp_path, "blocker", status=backlog.SHELVED_STATUS, type="feature")
    _mk_card(tmp_path, "dependent", status=backlog.SHELVED_STATUS, type="feature", depends_on="blocker")

    assert not [f for f in backlog.hygiene_findings(tmp_path) if "can never lift" in f.message]
