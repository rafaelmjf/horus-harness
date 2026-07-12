"""`.horus/backlog/` card parsing + claim-time overlap check."""

import threading
from pathlib import Path

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


def test_load_cards_back_compat_no_new_fields(tmp_path):
    _mk_card(tmp_path, "old-style")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].parallel == ""
    assert cards[0].surface == ()


def test_load_cards_type_defaults_to_task(tmp_path):
    _mk_card(tmp_path, "untyped")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].type == "task"


def test_load_cards_reads_explicit_type(tmp_path):
    _mk_card(tmp_path, "a-bug", type="bug")
    cards = backlog.load_cards(tmp_path)
    assert cards[0].type == "bug"


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
