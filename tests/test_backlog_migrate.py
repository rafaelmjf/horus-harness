"""`horus backlog migrate` — inline PRD `## Backlog` -> one card per item."""

from horus import backlog, backlog_migrate

_FIXTURE_PRD = """---
status: active
current_focus: "x"
next_action: "y"
next_prompt: "z"
execution_recommendation: "continue-as-is"
horus_min_version: 0.0.26
last_updated: 2026-07-12
---

# demo — PRD

## Vision

Some vision text.

## Backlog

Prioritized open work. Features and bugs in one list; jump order is allowed — this
list is a menu, not a contract. Mark bugs **[bug]**, ops chores **[ops]**.

### Now / next candidates

1. First concrete next step.
2. **[bug]** Fix the thing that broke.

### Open, unscheduled

- Direction noted, not yet scheduled.

### Deferred

- Direction noted, not scheduled; revisit later.

## Shipped

- Shipped thing one.

## Rules (load-bearing)

- **Rule one** — because reasons.
"""


def _write_prd(tmp_path, text=_FIXTURE_PRD):
    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "PRD.md").write_text(text, encoding="utf-8")
    return hdir


def test_migrate_requires_prd(tmp_path):
    actions = backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    assert len(actions) == 1
    assert actions[0].status == "error"


def test_migrate_requires_backlog_heading(tmp_path):
    _write_prd(tmp_path, "---\nstatus: active\n---\n\n# demo\n\n## Vision\n\nx\n")
    actions = backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    assert len(actions) == 1
    assert actions[0].status == "error"
    assert "Backlog" in actions[0].message


def test_migrate_dry_run_reports_without_writing(tmp_path):
    _write_prd(tmp_path)
    actions = backlog_migrate.migrate_inline_backlog(tmp_path, apply=False)
    assert any(a.status == "would-create" for a in actions)
    assert any(a.status == "would-update" for a in actions)
    assert not (tmp_path / ".horus" / "backlog").exists()
    prd_text = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert prd_text == _FIXTURE_PRD


def test_migrate_apply_creates_one_card_per_item(tmp_path):
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    cards = backlog.load_cards(tmp_path)
    assert len(cards) == 4
    titles = {c.title for c in cards}
    assert titles == {
        "First concrete next step",
        "Fix the thing that broke",
        "Direction noted, not yet scheduled",
        "Direction noted, not scheduled; revisit later",
    }


def test_migrate_preserves_item_text_byte_stably(tmp_path):
    """The original item text (marker stripped) must appear verbatim in its card
    — no reflow, no reformatting, no lost words."""
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    bug_card = next(c for c in backlog.load_cards(tmp_path) if c.type == "bug")
    text = bug_card.path.read_text(encoding="utf-8")
    assert "**[bug]** Fix the thing that broke." in text


def test_migrate_infers_type_from_bracket_tag(tmp_path):
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    cards = {c.title: c for c in backlog.load_cards(tmp_path)}
    assert cards["Fix the thing that broke"].type == "bug"
    assert cards["First concrete next step"].type == "task"


def test_migrate_infers_priority_from_bucket_heading(tmp_path):
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    cards = {c.title: c for c in backlog.load_cards(tmp_path)}
    assert cards["First concrete next step"].priority == "high"
    assert cards["Direction noted, not yet scheduled"].priority == "medium"


def test_migrate_replaces_backlog_section_with_pointer(tmp_path):
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    prd_text = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert "one card per item" in prd_text
    assert "Now / next candidates" not in prd_text
    assert "First concrete next step" not in prd_text


def test_migrate_preserves_leftover_intro_prose(tmp_path):
    """The intro sentence before any list item isn't a card — it must not be
    silently dropped; it lands in the replacement pointer section instead."""
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    prd_text = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert "Prioritized open work. Features and bugs in one list" in prd_text


def test_migrate_never_touches_other_sections(tmp_path):
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    prd_text = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert "Some vision text." in prd_text
    assert "Shipped thing one." in prd_text
    assert "**Rule one** — because reasons." in prd_text
    assert 'next_action: "y"' in prd_text


def test_migrate_is_idempotent(tmp_path):
    _write_prd(tmp_path)
    backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    prd_after_first = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    cards_after_first = sorted(p.name for p in (tmp_path / ".horus" / "backlog").glob("*.md"))

    actions = backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    prd_after_second = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    cards_after_second = sorted(p.name for p in (tmp_path / ".horus" / "backlog").glob("*.md"))

    assert len(actions) == 1
    assert actions[0].status == "noop"
    assert prd_after_first == prd_after_second
    assert cards_after_first == cards_after_second


def test_migrate_noop_on_fresh_thin_scaffold(tmp_path):
    """A fresh v3 scaffold's PRD (thin pointer from the start, no inline items)
    is already migrated — running the command must be a clean no-op."""
    from horus import templates

    prd = f"""---
status: active
---

# demo — PRD

## Backlog

{templates.backlog_pointer_block()}

## Shipped
"""
    _write_prd(tmp_path, prd)
    actions = backlog_migrate.migrate_inline_backlog(tmp_path, apply=True)
    assert len(actions) == 1
    assert actions[0].status == "noop"


def test_migrate_no_cockpit_all_flag_exists():
    """Owner decision (2026-07-12): `horus backlog migrate` stays per-project —
    no cockpit `--all` that writes to N repos from one overseer session."""
    import inspect

    sig = inspect.signature(backlog_migrate.migrate_inline_backlog)
    assert "all" not in sig.parameters


# ---------------------------------------------------------------------------
# inline_backlog_item_count — best-effort count for horus/fleet_backlog.py
# ---------------------------------------------------------------------------


def test_inline_backlog_item_count_counts_items(tmp_path):
    _write_prd(tmp_path, _FIXTURE_PRD)
    assert backlog_migrate.inline_backlog_item_count(tmp_path) == 4


def test_inline_backlog_item_count_zero_when_pointer_present(tmp_path):
    from horus import templates

    prd = f"""---
status: active
---

# demo — PRD

## Backlog

{templates.backlog_pointer_block()}

## Shipped
"""
    _write_prd(tmp_path, prd)
    assert backlog_migrate.inline_backlog_item_count(tmp_path) == 0


def test_inline_backlog_item_count_none_when_no_prd(tmp_path):
    assert backlog_migrate.inline_backlog_item_count(tmp_path) is None


def test_inline_backlog_item_count_none_when_no_backlog_heading(tmp_path):
    prd = """---
status: active
---

# demo — PRD

## Shipped
"""
    _write_prd(tmp_path, prd)
    assert backlog_migrate.inline_backlog_item_count(tmp_path) is None
