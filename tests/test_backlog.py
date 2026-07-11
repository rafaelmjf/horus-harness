"""`.horus/backlog/` card parsing + claim-time overlap check."""

from pathlib import Path

from horus import backlog


def _mk_card(root: Path, name: str, *, status="open", parallel="", surface="", body="Card body.\n"):
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}", "priority: later", "tier: sonnet", "created: 2026-07-11"]
    if parallel:
        lines.append(f"parallel: {parallel}")
    if surface:
        lines.append(f"surface: {surface}")
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


def test_surface_overlap_glob_matching():
    assert backlog.surface_overlap(("horus/pty_*",), ("horus/pty_host.py",))
    assert not backlog.surface_overlap(("horus/dashboard.py",), ("horus/pty_host.py",))
