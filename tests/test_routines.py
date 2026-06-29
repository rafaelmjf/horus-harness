"""Tests for the agent-delegated maintenance routines (consolidate, distill-history)."""

from pathlib import Path

from horus import routines


def _mk_fresh(
    root: Path, *, session_date="2026-06-26T10:00:00", proj_updated="2026-06-26",
    road_updated="2026-06-26", next_action="Build the Codex adapter", next_prompt="Resume: build Codex adapter",
    execution_recommendation="continue-as-is — narrow implementation", current_focus="Shipping the terminal", shipped=(),
):
    """A .horus/ with frontmatter + one session, for exercising freshness_signals."""
    hdir = root / ".horus"
    (hdir / "sessions").mkdir(parents=True, exist_ok=True)
    (hdir / "sessions" / "s1.md").write_text(
        f"---\ndate: {session_date}\nsummary: x\n---\n# s\n", encoding="utf-8"
    )
    (hdir / "project.md").write_text(
        f"---\nstatus: active\ncurrent_focus: \"{current_focus}\"\nlast_updated: {proj_updated}\n---\n# P\n",
        encoding="utf-8",
    )
    (hdir / "roadmap.md").write_text(
        f"---\nstatus: active\nnext_action: \"{next_action}\"\nnext_prompt: \"{next_prompt}\"\n"
        f"execution_recommendation: \"{execution_recommendation}\"\n"
        f"last_updated: {road_updated}\n---\n# Roadmap\n",
        encoding="utf-8",
    )
    rows = "".join(f"| {c} |  |  |\n" for c in shipped)
    (hdir / "features.md").write_text(
        "---\nstatus: active\n---\n# Features\n\n## Shipped\n\n| Capability | Since | Notes |\n|---|---|---|\n" + rows,
        encoding="utf-8",
    )
    return hdir


def _levels(findings):
    return [(f.level, f.message) for f in findings]


def test_freshness_ok_when_lanes_current(tmp_path):
    _mk_fresh(tmp_path)
    f = routines.freshness_signals(tmp_path)
    assert not any(lvl == "warn" for lvl, _ in _levels(f))
    assert any("fresh" in m for lvl, m in _levels(f) if lvl == "ok")


def test_freshness_flags_stale_lanes(tmp_path):
    _mk_fresh(tmp_path, proj_updated="2026-06-20", road_updated="2026-06-20")
    msgs = [m for lvl, m in _levels(routines.freshness_signals(tmp_path)) if lvl == "warn"]
    assert any("project.md last_updated" in m for m in msgs)
    assert any("roadmap.md last_updated" in m for m in msgs)


def test_freshness_flags_empty_next_and_focus(tmp_path):
    _mk_fresh(tmp_path, next_action="", next_prompt="", execution_recommendation="", current_focus="")
    msgs = [m for lvl, m in _levels(routines.freshness_signals(tmp_path)) if lvl == "warn"]
    assert any("next_action is empty" in m for m in msgs)
    assert any("next_prompt is empty" in m for m in msgs)
    assert any("execution_recommendation is empty" in m for m in msgs)
    assert any("current_focus is empty" in m for m in msgs)


def test_freshness_flags_next_pointing_at_shipped(tmp_path):
    # Strong overlap (≥3 shared tokens) -> flag; a passing mention would not.
    _mk_fresh(tmp_path, next_action="Finish the Codex adapter execution layer",
              shipped=["Codex adapter execution layer"])
    msgs = [m for lvl, m in _levels(routines.freshness_signals(tmp_path)) if lvl == "warn"]
    assert any("already-shipped work" in m for m in msgs)


def test_freshness_no_false_positive_on_context_mention(tmp_path):
    # next_action *mentions* a shipped capability as context -> not flagged (weak overlap).
    _mk_fresh(tmp_path, next_action="Build the Codex adapter; it makes the Control tab multi-agent",
              shipped=["Dashboard Control tab"])
    msgs = [m for lvl, m in _levels(routines.freshness_signals(tmp_path)) if lvl == "warn"]
    assert not any("already-shipped" in m for m in msgs)


def _mk_horus(root, *, roadmap_body="# Roadmap\n", features_body="", history=True):
    hdir = root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "roadmap.md").write_text(roadmap_body, encoding="utf-8")
    (hdir / "features.md").write_text(features_body, encoding="utf-8")
    if history:
        (hdir / "history.md").write_text("# History\n", encoding="utf-8")
    return hdir


def test_feature_capabilities_extracts_first_column():
    body = (
        "## Shipped\n\n| Capability | Since | Notes |\n|---|---|---|\n"
        "| Bronze ingestion | 0.1 | x |\n| Silver transform |  | y |\n"
    )
    assert routines.feature_capabilities(body) == ["Bronze ingestion", "Silver transform"]


def test_feature_counts_by_section():
    body = (
        "## Shipped\n\n| Capability | Since | Notes |\n|---|---|---|\n| A |  |  |\n| B |  |  |\n\n"
        "## In progress\n\n| Capability | Notes |\n|---|---|\n| C |  |\n\n"
        "## Planned\n\n| Capability | Notes |\n|---|---|\n| D |  |\n| E |  |\n"
    )
    assert routines.feature_counts(body) == {"shipped": 2, "in_progress": 1, "planned": 2}


def test_consolidate_flags_real_overlap_only(tmp_path):
    _mk_horus(
        tmp_path,
        roadmap_body="# Roadmap\n\n## Now\n\n- [ ] parquet export compaction to prod\n- [ ] unrelated chore widget\n",
        features_body="## Planned\n\n| Capability | Notes |\n|---|---|\n| parquet export compaction | x |\n",
    )
    findings = routines.consolidate_signals(tmp_path)
    overlaps = [f for f in findings if f.message.startswith("overlap:")]
    assert len(overlaps) == 1
    assert "parquet" in overlaps[0].message


def test_consolidate_treats_cross_referenced_as_reconciled(tmp_path):
    # Once a roadmap item points at features.md, the split is intentional -> no warning.
    _mk_horus(
        tmp_path,
        roadmap_body="# Roadmap\n\n## Now\n\n- [ ] parquet export compaction — status in → features.md\n",
        features_body="## In progress\n\n| Capability | Notes |\n|---|---|\n| parquet export compaction | action points → roadmap.md |\n",
    )
    findings = routines.consolidate_signals(tmp_path)
    assert not any(f.message.startswith("overlap:") for f in findings)
    assert any("already split (cross-referenced)" in f.message for f in findings)


def test_consolidate_reports_no_overlap_when_disjoint(tmp_path):
    _mk_horus(
        tmp_path,
        roadmap_body="# Roadmap\n\n## Now\n\n- [ ] write onboarding docs\n",
        features_body="## Shipped\n\n| Capability | Since | Notes |\n|---|---|---|\n| metadata control layer |  |  |\n",
    )
    findings = routines.consolidate_signals(tmp_path)
    assert any(f.level == "ok" and "no roadmap" in f.message for f in findings)


def test_consolidate_counts_done_and_sessions(tmp_path):
    hdir = _mk_horus(
        tmp_path,
        roadmap_body="# Roadmap\n\n## Now\n\n- [x] shipped thing\n- [ ] open thing\n",
    )
    (hdir / "sessions").mkdir()
    (hdir / "sessions" / "2026-06-25-x.md").write_text("# x\n", encoding="utf-8")
    findings = routines.consolidate_signals(tmp_path)
    msgs = " ".join(f.message for f in findings)
    assert "done roadmap item" in msgs
    assert "session summary(ies) to distill" in msgs


def test_consolidate_counts_temp_worker_notes(tmp_path):
    hdir = _mk_horus(tmp_path)
    (hdir / "temp").mkdir()
    (hdir / "temp" / "1A.md").write_text("# phase 1A handoff\n", encoding="utf-8")
    findings = routines.consolidate_signals(tmp_path)
    msgs = " ".join(f.message for f in findings)
    assert "temp worker handoff note(s) to review/distill" in msgs


def test_consolidate_fails_without_horus(tmp_path):
    findings = routines.consolidate_signals(tmp_path)
    assert findings and findings[0].level == "fail"


def test_consolidate_warns_missing_recommended_lanes(tmp_path):
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
    msgs = " ".join(f.message for f in routines.consolidate_signals(tmp_path))
    assert "features.md missing" in msgs and "history.md missing" in msgs


def test_project_name_tokens_do_not_drive_overlap(tmp_path):
    # A project literally named "horus": the token "horus" must not match.
    proj = tmp_path / "horus"
    _mk_horus(
        proj,
        roadmap_body="# Roadmap\n\n- [ ] reframe horus as a project panel\n",
        features_body="## Shipped\n\n| Capability | Since | Notes |\n|---|---|---|\n| horus dashboard |  |  |\n",
    )
    findings = routines.consolidate_signals(proj)
    assert not any(f.message.startswith("overlap:") for f in findings)


def test_distill_history_detects_source_and_sizes(tmp_path):
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "history.md").write_text("# History\n\n## one\n\nlesson\n", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "HISTORY.md").write_text("# H\n\n" + "log line\n" * 50, encoding="utf-8")

    source = routines.find_source_log(tmp_path)
    assert source is not None and source.name == "HISTORY.md"
    msgs = " ".join(f.message for f in routines.distill_signals(tmp_path, source))
    assert "source log" in msgs and "current history.md" in msgs


def test_distill_history_no_source(tmp_path):
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "history.md").write_text("# History\n", encoding="utf-8")
    assert routines.find_source_log(tmp_path) is None
    assert any("no source log" in f.message for f in routines.distill_signals(tmp_path, None))


def test_infer_discovers_canonical_docs(tmp_path):
    (tmp_path / "README.md").write_text("# Proj\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# c\n", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "HISTORY.md").write_text("# H\n", encoding="utf-8")
    names = {p.name for p in routines.discover_canonical_docs(tmp_path)}
    assert {"README.md", "ROADMAP.md", "CLAUDE.md", "HISTORY.md"} <= names


def test_infer_flags_placeholder_lanes(tmp_path):
    from horus import templates

    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "project.md").write_text(templates.project_md("p", "2026-01-01"), encoding="utf-8")
    (hdir / "roadmap.md").write_text(templates.roadmap_md("2026-01-01"), encoding="utf-8")
    (hdir / "features.md").write_text(templates.features_md("2026-01-01"), encoding="utf-8")
    (hdir / "history.md").write_text(templates.history_md("2026-01-01"), encoding="utf-8")
    (tmp_path / "README.md").write_text("# real project\n\ndoes things\n", encoding="utf-8")

    msgs = " ".join(f.message for f in routines.infer_signals(tmp_path))
    assert "canonical doc(s) to distill from" in msgs
    assert "placeholder/empty lanes" in msgs
    for lane in ("project.md", "roadmap.md", "features.md", "history.md"):
        assert lane in msgs


def test_infer_history_placeholder_cleared_by_real_content_without_heading(tmp_path):
    # Regression: history.md should count as populated once it has real content,
    # even with no '## ' heading (the shipped template has none).
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "project.md").write_text(
        '---\ncurrent_focus: "ship it"\n---\n# p\n\nA real description of the thing.\n', encoding="utf-8"
    )
    (hdir / "roadmap.md").write_text("---\n---\n# Roadmap\n\n## Now\n\n- [ ] a real task\n", encoding="utf-8")
    (hdir / "features.md").write_text(
        "## Shipped\n\n| Capability | Since | Notes |\n|---|---|---|\n| Thing | 0.1 | x |\n", encoding="utf-8"
    )
    (hdir / "history.md").write_text(
        "---\n---\n# History\n\nWe corrupted data once; lesson: validate before delete.\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# real\n", encoding="utf-8")

    msgs = " ".join(f.message for f in routines.infer_signals(tmp_path))
    assert "all lanes already populated" in msgs
    assert "placeholder/empty lanes" not in msgs


def test_infer_notes_empty_decisions_without_pressuring(tmp_path):
    from horus import templates

    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "decisions.md").write_text(templates.decisions_md(), encoding="utf-8")
    (tmp_path / "README.md").write_text("# r\n", encoding="utf-8")
    findings = routines.infer_signals(tmp_path)
    note = [f for f in findings if "decisions.md is empty" in f.message]
    assert note and note[0].level == "ok"  # gentle, not a populate-warning


def test_infer_warns_without_horus(tmp_path):
    (tmp_path / "README.md").write_text("# x\n", encoding="utf-8")
    assert any("no .horus/" in f.message for f in routines.infer_signals(tmp_path))


def test_distill_history_explicit_source(tmp_path):
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "history.md").write_text("# History\n", encoding="utf-8")
    log = tmp_path / "BIGLOG.md"
    log.write_text("# big\n" + "x\n" * 10, encoding="utf-8")
    source = routines.find_source_log(tmp_path, "BIGLOG.md")
    assert source is not None and source.name == "BIGLOG.md"


def test_feature_items_groups_names_by_section():
    body = (
        "## Shipped\n| Capability | Since |\n|---|---|\n| Dashboard | v1 |\n| Closure | v1 |\n"
        "## In progress\n| Capability | Notes |\n|---|---|\n| Git awareness | wip |\n"
        "## Planned\n| Capability | Notes |\n|---|---|\n| Telegram | later |\n"
    )
    items = routines.feature_items(body)
    assert items["shipped"] == ["Dashboard", "Closure"]
    assert items["in_progress"] == ["Git awareness"]
    assert items["planned"] == ["Telegram"]
    assert routines.feature_counts(body) == {"shipped": 2, "in_progress": 1, "planned": 1}
