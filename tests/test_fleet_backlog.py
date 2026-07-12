"""`horus fleet --backlog` — deterministic fleet-wide backlog card roll-up."""

from __future__ import annotations

import json
from pathlib import Path

from horus import fleet_backlog
from horus.cli import main


def _mk_card(root: Path, name: str, *, status="open", priority="", tier="", type="", surface="", body="Body.\n"):
    bdir = root / ".horus" / "backlog"
    bdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}"]
    if priority:
        lines.append(f"priority: {priority}")
    if tier:
        lines.append(f"tier: {tier}")
    if type:
        lines.append(f"type: {type}")
    if surface:
        lines.append(f"surface: {surface}")
    lines.append("created: 2026-01-01")
    lines.append("---")
    text = "\n".join(lines) + f"\n# {name.replace('-', ' ').title()}\n\n{body}"
    (bdir / f"{name}.md").write_text(text, encoding="utf-8")


def _mk_prd(root: Path, backlog_section: str) -> None:
    (root / ".horus").mkdir(parents=True, exist_ok=True)
    (root / ".horus" / "PRD.md").write_text(
        f"---\nstatus: active\n---\n# Proj\n\n## Backlog\n\n{backlog_section}\n\n## Rules\n\nn/a\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# load_project_rollup / load_fleet_rollup — mode detection + resilience
# ---------------------------------------------------------------------------


def test_load_project_rollup_cards_mode_reads_all_cards(tmp_path):
    _mk_card(tmp_path, "a-bug", priority="high", type="bug")
    _mk_card(tmp_path, "a-feature", priority="medium", type="feature")

    rollup = fleet_backlog.load_project_rollup(str(tmp_path))

    assert rollup.mode == "cards"
    assert {c.name for c in rollup.cards} == {"a-bug", "a-feature"}


def test_load_project_rollup_excludes_stray_done_cards(tmp_path):
    """The structure contract deletes a card on completion; a project that left
    a `status: done` card behind is data-hygiene drift, not open work — the
    roll-up must exclude it rather than counting it as "open"."""
    _mk_card(tmp_path, "still-open", status="open")
    _mk_card(tmp_path, "left-behind-done", status="done")

    rollup = fleet_backlog.load_project_rollup(str(tmp_path))

    assert [c.name for c in rollup.cards] == ["still-open"]


def test_load_project_rollup_hides_shipped_cards_unless_requested(tmp_path):
    _mk_card(tmp_path, "still-open", status="open")
    _mk_card(tmp_path, "already-shipped", status="shipped")

    assert [c.name for c in fleet_backlog.load_project_rollup(str(tmp_path)).cards] == ["still-open"]
    assert [c.name for c in fleet_backlog.load_project_rollup(
        str(tmp_path), include_shipped=True,
    ).cards] == ["already-shipped", "still-open"]


def test_load_project_rollup_inline_not_migrated_degrades_with_note(tmp_path):
    _mk_prd(tmp_path, "- [bug] fix the widget\n- [feature] add the gadget")

    rollup = fleet_backlog.load_project_rollup(str(tmp_path))

    assert rollup.mode == "inline"
    assert rollup.cards == []
    assert "2 item(s)" in rollup.note
    assert "horus backlog migrate" in rollup.note


def test_load_project_rollup_inline_already_migrated_is_zero_cards(tmp_path):
    from horus import templates

    _mk_prd(tmp_path, templates.backlog_pointer_block())

    rollup = fleet_backlog.load_project_rollup(str(tmp_path))

    assert rollup.mode == "cards"
    assert rollup.cards == []


def test_load_project_rollup_no_prd_no_backlog_degrades_without_erroring(tmp_path):
    (tmp_path / ".horus").mkdir(parents=True)
    (tmp_path / ".horus" / "project.md").write_text("# Six-lane project\n", encoding="utf-8")

    rollup = fleet_backlog.load_project_rollup(str(tmp_path))

    assert rollup.mode == "none"
    assert rollup.cards == []
    assert rollup.note


def test_load_project_rollup_missing_horus_dir_degrades_without_erroring(tmp_path):
    rollup = fleet_backlog.load_project_rollup(str(tmp_path))
    assert rollup.mode == "unreadable"
    assert "no .horus/" in rollup.note


def test_load_project_rollup_nonexistent_path_degrades_without_erroring(tmp_path):
    gone = tmp_path / "gone"
    rollup = fleet_backlog.load_project_rollup(str(gone))
    assert rollup.mode == "unreadable"
    assert "not found" in rollup.note


def test_load_fleet_rollup_sorts_projects_by_name(tmp_path):
    zeta = tmp_path / "zeta"
    alpha = tmp_path / "alpha"
    _mk_card(zeta, "z-card")
    _mk_card(alpha, "a-card")

    rollups = fleet_backlog.load_fleet_rollup([str(zeta), str(alpha)])

    assert [r.name for r in rollups] == ["alpha", "zeta"]


# ---------------------------------------------------------------------------
# apply_filters — priority sort + type filter
# ---------------------------------------------------------------------------


def test_apply_filters_sorts_by_priority_then_name(tmp_path):
    _mk_card(tmp_path, "low-one", priority="low")
    _mk_card(tmp_path, "high-one", priority="high")
    _mk_card(tmp_path, "medium-one", priority="medium")
    _mk_card(tmp_path, "unstated", priority="")

    rollups = fleet_backlog.apply_filters(fleet_backlog.load_fleet_rollup([str(tmp_path)]))

    names = [c.name for c in rollups[0].cards]
    assert names == ["high-one", "medium-one", "low-one", "unstated"]


def test_apply_filters_sorts_now_next_before_high_and_later_after(tmp_path):
    """Regression: 'now' and 'next' priorities must sort FIRST (most urgent),
    and 'later'/'deferred' must sort LAST. The urgency order is:
    now < next < high < medium < low < later < deferred."""
    _mk_card(tmp_path, "later-card", priority="later")
    _mk_card(tmp_path, "now-card", priority="now")
    _mk_card(tmp_path, "high-card", priority="high")
    _mk_card(tmp_path, "next-card", priority="next")
    _mk_card(tmp_path, "deferred-card", priority="deferred")

    rollups = fleet_backlog.apply_filters(fleet_backlog.load_fleet_rollup([str(tmp_path)]))

    names = [c.name for c in rollups[0].cards]
    assert names == ["now-card", "next-card", "high-card", "later-card", "deferred-card"]


def test_apply_filters_type_filter_narrows_cards(tmp_path):
    _mk_card(tmp_path, "a-bug", type="bug")
    _mk_card(tmp_path, "a-feature", type="feature")

    rollups = fleet_backlog.apply_filters(
        fleet_backlog.load_fleet_rollup([str(tmp_path)]), type_filter="bug"
    )

    assert [c.name for c in rollups[0].cards] == ["a-bug"]


# ---------------------------------------------------------------------------
# render_text / render_json — output shape
# ---------------------------------------------------------------------------


def test_render_json_is_valid_and_carries_schema(tmp_path):
    _mk_card(tmp_path, "a-bug", priority="high", type="bug", surface="horus/cli.py")

    rollups = fleet_backlog.apply_filters(fleet_backlog.load_fleet_rollup([str(tmp_path)]))
    text = fleet_backlog.render_json(rollups)
    data = json.loads(text)

    assert data["schema_version"] == 1
    assert data["projects"][0]["cards"][0]["name"] == "a-bug"
    assert data["projects"][0]["cards"][0]["surface"] == ["horus/cli.py"]


def test_render_text_shows_project_note_for_degraded_row(tmp_path):
    _mk_prd(tmp_path, "- [bug] fix the widget")

    rollups = fleet_backlog.load_fleet_rollup([str(tmp_path)])
    text = fleet_backlog.render_text(rollups)

    assert "note:" in text
    assert "horus backlog migrate" in text


def test_render_text_no_projects_registered():
    assert fleet_backlog.render_text([]) == "No fleet projects registered.\n"


# ---------------------------------------------------------------------------
# CLI wiring — `horus fleet --backlog`
# ---------------------------------------------------------------------------


def test_cmd_fleet_backlog_stdout_emits_valid_json_for_mixed_registry(tmp_path, monkeypatch, capsys):
    cards_proj = tmp_path / "proj-cards"
    _mk_card(cards_proj, "hot-bug", priority="high", type="bug")
    _mk_card(cards_proj, "cold-chore", priority="low", type="chore")

    inline_proj = tmp_path / "proj-inline"
    _mk_prd(inline_proj, "- [feature] add the gadget")

    bare_proj = tmp_path / "proj-bare"
    (bare_proj / ".horus").mkdir(parents=True)

    projects = [str(cards_proj), str(inline_proj), str(bare_proj)]
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: projects)

    rc = main(["fleet", "--backlog", "--stdout"])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    by_name = {p["name"]: p for p in data["projects"]}
    assert by_name["proj-cards"]["mode"] == "cards"
    assert len(by_name["proj-cards"]["cards"]) == 2
    assert by_name["proj-inline"]["mode"] == "inline"
    assert by_name["proj-bare"]["mode"] == "none"


def test_cmd_fleet_backlog_human_readable_default(tmp_path, monkeypatch, capsys):
    _mk_card(tmp_path, "a-bug", priority="high", type="bug")
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: [str(tmp_path)])

    rc = main(["fleet", "--backlog"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "a-bug" in out
    assert "priority=high" in out


def test_cmd_fleet_backlog_type_filter(tmp_path, monkeypatch, capsys):
    _mk_card(tmp_path, "a-bug", type="bug")
    _mk_card(tmp_path, "a-feature", type="feature")
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: [str(tmp_path)])

    rc = main(["fleet", "--backlog", "--stdout", "--type", "bug"])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    cards = data["projects"][0]["cards"]
    assert [c["name"] for c in cards] == ["a-bug"]


def test_cmd_fleet_backlog_project_filter_narrows_to_one_project(tmp_path, monkeypatch, capsys):
    a = tmp_path / "proj-a"
    b = tmp_path / "proj-b"
    _mk_card(a, "a-card")
    _mk_card(b, "b-card")
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: [str(a), str(b)])

    rc = main(["fleet", "--backlog", "--stdout", "--project", "proj-a"])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert [p["name"] for p in data["projects"]] == ["proj-a"]


def test_cmd_fleet_backlog_unknown_project_filter_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: [str(tmp_path / "proj-a")])

    rc = main(["fleet", "--backlog", "--project", "nope"])

    assert rc == 1
    assert "No registered project named" in capsys.readouterr().out


def test_cmd_fleet_backlog_no_projects_registered(monkeypatch, capsys):
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: [])

    rc = main(["fleet", "--backlog"])

    assert rc == 0
    assert "No projects registered" in capsys.readouterr().out


def test_cmd_fleet_plain_still_excludes_cockpit_backlog_flag_unaffected(tmp_path, monkeypatch, capsys):
    """Sanity: plain `horus fleet` (no --backlog) keeps its existing exclusion
    of the horus-agent cockpit — the new flag must not change that path."""
    horus_agent = tmp_path / "horus-agent"
    (horus_agent / ".horus").mkdir(parents=True)
    monkeypatch.setattr("horus.cli.config.load_projects", lambda: [str(horus_agent)])

    rc = main(["fleet"])

    assert rc == 0
    assert "excluded" in capsys.readouterr().out
