"""`horus backlog --tree` — canonical branch/facet projection + receipts shelf."""

from __future__ import annotations

import json
from pathlib import Path

from horus import backlog_tree
from horus.cli import main


def _mk_card(
    root: Path,
    name: str,
    *,
    status="open",
    priority="",
    tier="",
    phase="",
    branch="",
    vision_facet="",
    readiness="ready",
    readiness_reason="",
    autonomy="eligible",
    body="",
    title="",
):
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}"]
    if priority:
        lines.append(f"priority: {priority}")
    if tier:
        lines.append(f"tier: {tier}")
    if phase:
        lines.append(f"phase: {phase}")
    if branch:
        lines.append(f"branch: {branch}")
    if vision_facet:
        lines.append(f'vision_facet: "{vision_facet}"')
    if readiness:
        lines.append(f"readiness: {readiness}")
    if readiness_reason:
        lines.append(f'readiness_reason: "{readiness_reason}"')
    if autonomy:
        lines.append(f"autonomy: {autonomy}")
    lines.append("created: 2026-07-17")
    lines.append("---")
    heading = title or name.replace("-", " ").title()
    text = "\n".join(lines) + f"\n# {heading}\n\n{body}"
    (hdir / f"{name}.md").write_text(text, encoding="utf-8")


def _mk_receipt(root: Path, filename: str, title: str) -> None:
    rdir = root / ".horus" / "research"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / filename).write_text(f"# {title}\n\nbody\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# build_tree — grouping by branch umbrella, then vision_facet
# ---------------------------------------------------------------------------


def test_build_tree_groups_children_under_their_branch_umbrella(tmp_path):
    _mk_card(
        tmp_path, "umbrella-a", priority="medium",
        body="## Acceptance\n\n- Converged when everything under it ships.\n",
        title="Umbrella A",
    )
    _mk_card(tmp_path, "child-1", priority="high", tier="sonnet", branch="umbrella-a")
    _mk_card(tmp_path, "child-2", priority="low", branch="umbrella-a")

    tree = backlog_tree.build_tree(tmp_path)

    assert len(tree.branches) == 1
    group = tree.branches[0]
    assert group.branch == "umbrella-a"
    assert group.title == "Umbrella A"
    assert group.resolved is True
    assert group.convergence == "Converged when everything under it ships."
    assert [c.name for c in group.children] == ["child-1", "child-2"]
    # priority sort: high before low
    assert group.children[0].name == "child-1"


def test_build_tree_umbrella_card_itself_never_appears_as_a_plain_card(tmp_path):
    _mk_card(tmp_path, "umbrella-a", title="Umbrella A")
    _mk_card(tmp_path, "child-1", branch="umbrella-a")

    tree = backlog_tree.build_tree(tmp_path)

    all_facet_names = {c.name for group in tree.facets for c in group.children}
    assert "umbrella-a" not in all_facet_names


def test_build_tree_unresolved_branch_reference_degrades_gracefully(tmp_path):
    """A `branch:` value with no matching umbrella card still groups its
    children — using the slug as the title — rather than crashing or losing
    the card."""
    _mk_card(tmp_path, "orphan-child", branch="ghost-branch")

    tree = backlog_tree.build_tree(tmp_path)

    assert len(tree.branches) == 1
    group = tree.branches[0]
    assert group.branch == "ghost-branch"
    assert group.resolved is False
    assert group.title == "ghost-branch"
    assert [c.name for c in group.children] == ["orphan-child"]


def test_build_tree_unbranched_cards_group_by_vision_facet(tmp_path):
    _mk_card(tmp_path, "a", vision_facet="Dashboard / cockpit")
    _mk_card(tmp_path, "b", vision_facet="Dashboard / cockpit")
    _mk_card(tmp_path, "c", vision_facet="Autonomous dispatch")
    _mk_card(tmp_path, "d")  # no facet at all

    tree = backlog_tree.build_tree(tmp_path)

    by_facet = {group.facet: {c.name for c in group.children} for group in tree.facets}
    assert by_facet["Dashboard / cockpit"] == {"a", "b"}
    assert by_facet["Autonomous dispatch"] == {"c"}
    assert by_facet[""] == {"d"}


def test_build_tree_no_branch_keys_anywhere_degrades_to_flat_population(tmp_path):
    """Forward-readability: a project that has never used `branch:` still
    projects every active card, just as one (or more) facet groups."""
    _mk_card(tmp_path, "a", vision_facet="Dashboard")
    _mk_card(tmp_path, "b")

    tree = backlog_tree.build_tree(tmp_path)

    assert tree.branches == ()
    all_names = {c.name for group in tree.facets for c in group.children}
    assert all_names == {"a", "b"}


def test_build_tree_excludes_done_and_shipped_cards(tmp_path):
    _mk_card(tmp_path, "open-one", status="open")
    _mk_card(tmp_path, "done-one", status="done")

    tree = backlog_tree.build_tree(tmp_path)

    all_names = {c.name for group in tree.facets for c in group.children}
    assert all_names == {"open-one"}


# ---------------------------------------------------------------------------
# sections_for — the configurable group-by lens (TUI grouped list)
# ---------------------------------------------------------------------------


def _cards(tmp_path):
    from horus import backlog
    return backlog.load_active_cards(tmp_path)


def test_sections_none_lens_returns_no_sections(tmp_path):
    # `none` = flat list; the caller renders cards without headers.
    _mk_card(tmp_path, "a")
    _mk_card(tmp_path, "b")
    assert backlog_tree.sections_for(_cards(tmp_path), "none") == []


def test_sections_readiness_lens_drops_empty_queues_and_orders_canonically(tmp_path):
    _mk_card(tmp_path, "ready-elig", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "ready-att", readiness="ready", autonomy="attended")
    _mk_card(tmp_path, "shaped", readiness="shaping", readiness_reason="tbd", autonomy="")

    sections = backlog_tree.sections_for(_cards(tmp_path), "readiness")
    labels = [s.label for s in sections]
    # canonical execution order, and empty queues (gated/deferred/unclassified) dropped
    assert labels == ["Ready—Autonomous eligible", "Ready—Attended", "Shaping"]
    assert all(s.children for s in sections)


def test_sections_facet_lens_matches_the_tree_projection(tmp_path):
    _mk_card(tmp_path, "umbrella-a", title="Umbrella A",
             body="## Acceptance\n\n- Converged when it all ships.\n")
    _mk_card(tmp_path, "child-1", branch="umbrella-a")
    _mk_card(tmp_path, "loose", vision_facet="Continuity core")

    cards = _cards(tmp_path)
    tree = backlog_tree.build_tree_from_cards(cards)
    sections = backlog_tree.sections_for(cards, "facet", tree)

    keys = [s.key for s in sections]
    assert "branch:umbrella-a" in keys and "facet:Continuity core" in keys
    branch_sec = next(s for s in sections if s.key == "branch:umbrella-a")
    assert branch_sec.label == "Umbrella A"
    assert branch_sec.subtitle == "converges: Converged when it all ships."


def test_sections_status_and_priority_lenses(tmp_path):
    _mk_card(tmp_path, "hi", priority="high", status="open")
    _mk_card(tmp_path, "lo", priority="low", status="open")
    _mk_card(tmp_path, "claimed-one", priority="medium", status="claimed")

    by_status = backlog_tree.sections_for(_cards(tmp_path), "status")
    # known statuses ordered open→claimed
    assert [s.label for s in by_status] == ["open", "claimed"]

    by_priority = backlog_tree.sections_for(_cards(tmp_path), "priority")
    assert [s.label for s in by_priority] == ["high", "medium", "low"]


def test_sections_priority_missing_value_buckets_last_as_none(tmp_path):
    _mk_card(tmp_path, "hi", priority="high")
    _mk_card(tmp_path, "unset", priority="")  # no priority line

    sections = backlog_tree.sections_for(_cards(tmp_path), "priority")
    assert [s.label for s in sections] == ["high", "(none)"]
    assert sections[-1].key == "priority:"


# ---------------------------------------------------------------------------
# filter_cards / ready_count — the readiness filter (list + board)
# ---------------------------------------------------------------------------


def _mixed_readiness(tmp_path):
    _mk_card(tmp_path, "elig", readiness="ready", autonomy="eligible")
    _mk_card(tmp_path, "att", readiness="ready", autonomy="attended")
    _mk_card(tmp_path, "shaped", readiness="shaping", readiness_reason="tbd", autonomy="")
    _mk_card(tmp_path, "gated-one", readiness="gated", readiness_reason="blocked", autonomy="")
    _mk_card(tmp_path, "deferred-one", readiness="deferred", readiness_reason="later", autonomy="")
    return _cards(tmp_path)


def test_filter_all_passes_everything(tmp_path):
    cards = _mixed_readiness(tmp_path)
    assert {c.name for c in backlog_tree.filter_cards(cards, "all")} == {
        "elig", "att", "shaped", "gated-one", "deferred-one",
    }


def test_filter_active_hides_gated_and_deferred(tmp_path):
    cards = _mixed_readiness(tmp_path)
    assert {c.name for c in backlog_tree.filter_cards(cards, "active")} == {"elig", "att", "shaped"}


def test_filter_ready_is_only_dispatchable(tmp_path):
    cards = _mixed_readiness(tmp_path)
    assert {c.name for c in backlog_tree.filter_cards(cards, "ready")} == {"elig", "att"}


def test_filter_parked_is_gated_and_deferred(tmp_path):
    cards = _mixed_readiness(tmp_path)
    assert {c.name for c in backlog_tree.filter_cards(cards, "parked")} == {"gated-one", "deferred-one"}


def test_ready_count_counts_dispatchable_only(tmp_path):
    cards = _mixed_readiness(tmp_path)
    assert backlog_tree.ready_count(cards) == 2  # elig + att, not shaping/gated/deferred


# ---------------------------------------------------------------------------
# render_json / render_text
# ---------------------------------------------------------------------------


def test_render_json_carries_schema_and_child_fields(tmp_path):
    _mk_card(tmp_path, "umbrella-a", title="Umbrella A")
    _mk_card(tmp_path, "child-1", priority="high", tier="opus", phase="explore", branch="umbrella-a")

    tree = backlog_tree.build_tree(tmp_path)
    data = json.loads(backlog_tree.render_json(tree))

    assert data["schema_version"] == 2
    assert [group["key"] for group in data["readiness"]] == list(backlog_tree.backlog.READINESS_QUEUE_ORDER)
    assert data["readiness"][0]["count"] == 2
    branch = data["branches"][0]
    assert branch["branch"] == "umbrella-a"
    assert branch["count"] == 1
    child = branch["children"][0]
    assert child == {
        "name": "child-1",
        "title": "Child 1",
        "status": "open",
        "priority": "high",
        "phase": "explore",
        "tier": "opus",
        "readiness": "ready",
        "readiness_queue": "ready-eligible",
        "readiness_reason": "",
        "autonomy": "eligible",
    }


def test_render_text_shows_branch_and_facet_sections(tmp_path):
    _mk_card(tmp_path, "umbrella-a", title="Umbrella A")
    _mk_card(tmp_path, "child-1", branch="umbrella-a")
    _mk_card(tmp_path, "lonely", vision_facet="Dashboard")

    text = backlog_tree.render_text(backlog_tree.build_tree(tmp_path))

    assert "Umbrella A (1 open)" in text
    assert "child-1" in text
    assert "Dashboard (1 open)" in text
    assert "lonely" in text


def test_render_text_no_cards_at_all(tmp_path):
    (tmp_path / ".horus" / "backlog").mkdir(parents=True)
    assert backlog_tree.render_text(backlog_tree.build_tree(tmp_path)) == "No open backlog cards.\n"


def test_render_text_reports_all_readiness_queues_and_reason(tmp_path):
    _mk_card(tmp_path, "eligible", readiness="ready", autonomy="eligible")
    _mk_card(
        tmp_path,
        "blocked",
        readiness="gated",
        readiness_reason="await upstream",
        autonomy="",
    )

    text = backlog_tree.render_text(backlog_tree.build_tree(tmp_path))

    for label in backlog_tree.backlog.READINESS_QUEUE_LABELS.values():
        assert label in text
    assert "readiness=Gated" in text
    assert "reason=await upstream" in text


# ---------------------------------------------------------------------------
# list_receipts
# ---------------------------------------------------------------------------


def test_list_receipts_sorted_newest_first(tmp_path):
    _mk_receipt(tmp_path, "2026-07-10-old.md", "Old receipt")
    _mk_receipt(tmp_path, "2026-07-17-new.md", "New receipt")

    receipts = backlog_tree.list_receipts(tmp_path)

    assert [r.title for r in receipts] == ["New receipt", "Old receipt"]
    assert receipts[0].date == "2026-07-17"


def test_list_receipts_missing_dir_returns_empty(tmp_path):
    assert backlog_tree.list_receipts(tmp_path) == []


def test_list_receipts_undated_file_still_listed_last(tmp_path):
    _mk_receipt(tmp_path, "2026-07-17-new.md", "New receipt")
    _mk_receipt(tmp_path, "notes.md", "Undated notes")

    receipts = backlog_tree.list_receipts(tmp_path)

    assert [r.title for r in receipts] == ["New receipt", "Undated notes"]
    assert receipts[1].date == ""


# ---------------------------------------------------------------------------
# CLI wiring — `horus backlog --tree [--json]`
# ---------------------------------------------------------------------------


def test_cmd_backlog_tree_text(tmp_path, capsys):
    _mk_card(tmp_path, "umbrella-a", title="Umbrella A")
    _mk_card(tmp_path, "child-1", branch="umbrella-a")

    rc = main(["backlog", "--tree", "--path", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "Umbrella A (1 open)" in out


def test_cmd_backlog_tree_json(tmp_path, capsys):
    _mk_card(tmp_path, "umbrella-a", title="Umbrella A")
    _mk_card(tmp_path, "child-1", branch="umbrella-a")

    rc = main(["backlog", "--tree", "--json", "--path", str(tmp_path)])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["branches"][0]["branch"] == "umbrella-a"


def test_cmd_backlog_no_subcommand_and_no_tree_errors(tmp_path, capsys):
    rc = main(["backlog", "--path", str(tmp_path)])

    assert rc == 2
    assert "error:" in capsys.readouterr().out


def test_cmd_backlog_list_still_works_unaffected(tmp_path, capsys):
    _mk_card(tmp_path, "a-card", priority="high")

    rc = main(["backlog", "list", "--path", str(tmp_path)])

    assert rc == 0
    assert "a-card" in capsys.readouterr().out
