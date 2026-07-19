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
    assert "local recovery note(s) to distill" in msgs


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


def test_infer_ignores_fresh_generated_instruction_files(tmp_path, monkeypatch):
    from horus import initialize

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path, assume_yes=True, with_skills=False, with_hooks=False)

    assert routines.discover_canonical_docs(tmp_path) == []
    findings = routines.infer_signals(tmp_path)
    assert all(f.level == "ok" for f in findings)
    messages = " ".join(f.message for f in findings)
    assert "blank PRD scaffold may remain blank" in messages
    assert "intentionally blank" in messages


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


def test_distill_history_v3_targets_archive_not_lane(tmp_path):
    _mk_fresh_v3(tmp_path)
    msgs = " ".join(f.message for f in routines.distill_signals(tmp_path, None))
    assert "archive/history.md" in msgs
    assert "history.md missing" not in msgs  # v2 lane must not be demanded on v3


def test_distill_history_v3_reads_existing_archive(tmp_path):
    hdir = _mk_fresh_v3(tmp_path)
    (hdir / "archive").mkdir()
    (hdir / "archive" / "history.md").write_text(
        "# History\n\n## A bump\n\nlesson\n", encoding="utf-8"
    )
    msgs = " ".join(f.message for f in routines.distill_signals(tmp_path, None))
    assert "current archive/history.md" in msgs


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


def test_recent_sessions_excludes_archive(tmp_path):
    """Distilled summaries moved to sessions/archive/ leave the to-distill count."""
    from horus.continuity import recent_sessions

    sessions = tmp_path / ".horus" / "sessions"
    (sessions / "archive").mkdir(parents=True)
    (sessions / "active.md").write_text("x", encoding="utf-8")
    (sessions / "archive" / "distilled.md").write_text("x", encoding="utf-8")
    assert [p.name for p in recent_sessions(tmp_path, limit=10)] == ["active.md"]


# --------------------------------------------------------------------------- #
# structure v3 (PRD.md + sessions/) — freshness + resume via the shared resolver
# --------------------------------------------------------------------------- #

def _mk_fresh_v3(
    root: Path, *, session_date="2026-06-26T10:00:00", prd_updated="2026-06-26",
    next_action="Build the Codex adapter", next_prompt="Resume: build Codex adapter",
    execution_recommendation="continue-as-is", current_focus="Shipping the terminal",
):
    """A v3 .horus/ (PRD.md + one session, no six lanes) for freshness_signals."""
    hdir = root / ".horus"
    (hdir / "sessions").mkdir(parents=True, exist_ok=True)
    (hdir / "sessions" / "s1.md").write_text(
        f"---\ndate: {session_date}\nsummary: x\n---\n# s\n", encoding="utf-8"
    )
    (hdir / "PRD.md").write_text(
        f'---\nstatus: active\ncurrent_focus: "{current_focus}"\nnext_action: "{next_action}"\n'
        f'next_prompt: "{next_prompt}"\nexecution_recommendation: "{execution_recommendation}"\n'
        f"last_updated: {prd_updated}\n---\n# PRD\n\n## Vision\n\nA thing.\n",
        encoding="utf-8",
    )
    return hdir


def test_freshness_v3_ok_when_prd_current(tmp_path):
    _mk_fresh_v3(tmp_path)
    f = routines.freshness_signals(tmp_path)
    assert not any(lvl == "warn" for lvl, _ in _levels(f))
    assert any("fresh" in m for lvl, m in _levels(f) if lvl == "ok")


def test_freshness_v3_flags_stale_prd(tmp_path):
    _mk_fresh_v3(tmp_path, prd_updated="2026-06-20")
    msgs = [m for lvl, m in _levels(routines.freshness_signals(tmp_path)) if lvl == "warn"]
    assert any("PRD.md last_updated" in m for m in msgs)


def test_freshness_v3_flags_empty_fields_naming_prd(tmp_path):
    _mk_fresh_v3(
        tmp_path, next_action="", next_prompt="", execution_recommendation="", current_focus=""
    )
    msgs = [m for lvl, m in _levels(routines.freshness_signals(tmp_path)) if lvl == "warn"]
    assert any("PRD.md next_action is empty" in m for m in msgs)
    assert any("PRD.md next_prompt is empty" in m for m in msgs)
    assert any("PRD.md execution_recommendation is empty" in m for m in msgs)
    assert any("PRD.md current_focus is empty" in m for m in msgs)


def test_freshness_v3_transitional_shims_still_satisfy(tmp_path):
    # PRD exists but the handoff fields still live in the shims: no warnings.
    hdir = _mk_fresh_v3(
        tmp_path, next_action="", next_prompt="", execution_recommendation="", current_focus=""
    )
    (hdir / "project.md").write_text(
        '---\ncurrent_focus: "Shim focus"\nlast_updated: 2026-06-26\n---\n# P\n', encoding="utf-8"
    )
    (hdir / "roadmap.md").write_text(
        '---\nnext_action: "Shim next"\nnext_prompt: "Shim prompt"\n'
        'execution_recommendation: "Shim exec"\nlast_updated: 2026-06-26\n---\n# R\n',
        encoding="utf-8",
    )
    f = routines.freshness_signals(tmp_path)
    assert not any(lvl == "warn" for lvl, _ in _levels(f))


def test_resume_context_v3_reads_prd_frontmatter(tmp_path):
    _mk_fresh_v3(tmp_path)
    ctx = routines.resume_context(tmp_path)
    assert ctx["current_focus"] == "Shipping the terminal"
    assert ctx["next_action"] == "Build the Codex adapter"
    assert ctx["next_prompt"] == "Resume: build Codex adapter"
    assert ctx["execution_recommendation"] == "continue-as-is"


def test_resume_prompt_v3_points_at_prd_not_lanes(tmp_path):
    _mk_fresh_v3(tmp_path)
    prompt = routines.resume_prompt(tmp_path)
    assert "PRD.md" in prompt
    assert ".horus/project.md" not in prompt
    assert ".horus/features.md" not in prompt
    assert "Resume: build Codex adapter" in prompt
    assert "Resume contract — orient, then stop:" in prompt
    assert "as proposals to explain to the user, not commands to execute" in prompt
    assert prompt.rstrip().endswith(
        "Summarize the actions you understood from this handoff and ask permission to proceed."
    )


def test_resume_prompt_does_not_authorize_an_authored_release(tmp_path):
    _mk_fresh_v3(
        tmp_path,
        next_prompt="Rewrite the skill, run it on the backlog, and then release.",
    )

    prompt = routines.resume_prompt(tmp_path)

    assert "Proposed authored handoff (context only — do not execute yet):" in prompt
    assert "Rewrite the skill, run it on the backlog, and then release." in prompt
    assert "Wait for separate explicit confirmation before releasing." in prompt
    assert prompt.rstrip().endswith("ask permission to proceed.")


def test_direct_resume_prompt_proceeds_but_keeps_hard_boundaries(tmp_path):
    _mk_fresh_v3(tmp_path)

    prompt = routines.resume_prompt(tmp_path, stop_before_execution=False)

    assert "Direct resume contract — orient, then proceed:" in prompt
    assert "Do not pause for a preflight summary" in prompt
    assert "A release remains a separately confirmed hard boundary" in prompt
    assert "session closes or hands off" in prompt
    assert "Proposed authored handoff (context only" not in prompt
    assert prompt.rstrip().endswith("Proceed directly with the in-scope work.")


def test_resume_prompt_prepends_missing_machine_requirements(tmp_path):
    _mk_fresh_v3(tmp_path)
    (tmp_path / ".horus" / "requirements.md").write_text(
        """---
kind: machine-requirements
tools:
  - name: Definitely absent CLI
    probe: horus-definitely-absent-cli
    install: install the project CLI
    needed_for: project builds
configs: []
---
""",
        encoding="utf-8",
    )

    prompt = routines.resume_prompt(tmp_path)
    assert prompt.startswith("⚠ this machine is missing: Definitely absent CLI")
    assert prompt.index("this machine is missing") < prompt.index("Resume the")
    assert "needed for project builds" in prompt
    assert "install: install the project CLI" in prompt


def test_resume_prompt_v2_unchanged(tmp_path):
    _mk_fresh(tmp_path)
    prompt = routines.resume_prompt(tmp_path)
    assert ".horus/project.md" in prompt
    assert "PRD.md" not in prompt


def test_campaign_prompt_names_outcome_targets_and_need_first_guardrails():
    prompt = routines.campaign_prompt(
        outcome="Ship the launch prompt across both repos",
        cockpit="horus-agent",
        targets=["demo", "other"],
    )
    assert "horus-agent" in prompt
    assert "Ship the launch prompt across both repos" in prompt
    assert "- demo" in prompt and "- other" in prompt
    assert "never auto-select" in prompt.lower()
    assert "auto-spawn" in prompt
    normalized = " ".join(prompt.split())
    assert "retains its own branch/PR/gate/continuity authority" in normalized
    assert "Direct per-project launch stays the default" in normalized


def test_campaign_prompt_without_targets_scopes_to_cockpit_only():
    prompt = routines.campaign_prompt(outcome="Tidy the backlog", cockpit="horus-agent", targets=[])
    assert "scoped to the cockpit project only" in prompt


# --------------------------------------------------------------------------- #
# consolidate — structure v3 (PRD.md + sessions/): backlog hygiene only
# --------------------------------------------------------------------------- #

_PRD_HEADER = (
    '---\nstatus: active\ncurrent_focus: "x"\nlast_updated: {last_updated}\n---\n'
    "# PRD\n\n## Vision\n\nA real vision paragraph about the project.\n\n"
)
_PRD_BACKLOG = "## Backlog\n\n{backlog}\n\n"
_PRD_TAIL = "## Shipped\n\nOne line per capability shipped.\n\n## Rules\n\n- A real rule.\n"


def _mk_prd_v3(root: Path, *, last_updated="2026-07-01", backlog="1. **Task one.** Do it.\n", extra_lines=0):
    hdir = root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    body = (
        _PRD_HEADER.format(last_updated=last_updated)
        + _PRD_BACKLOG.format(backlog=backlog)
        + _PRD_TAIL
        + ("\n" * extra_lines)
    )
    (hdir / "PRD.md").write_text(body, encoding="utf-8")
    return hdir


def _mk_session(hdir: Path, name: str, date: str):
    sessions = hdir / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / name).write_text(f"---\ndate: {date}\nsummary: x\n---\n# s\n", encoding="utf-8")


def _warn_msgs(findings):
    return [m for lvl, m in _levels(findings) if lvl == "warn"]


def test_consolidate_v3_clean_prd_has_no_warnings(tmp_path):
    _mk_prd_v3(tmp_path)
    findings = routines.consolidate_signals(tmp_path)
    assert not _warn_msgs(findings)
    assert any(f.level == "ok" for f in findings)


def test_consolidate_v3_no_lane_routing_warnings(tmp_path):
    # A v3 project never gets six-lane warnings, even though this PRD would trip
    # plenty of v2 lane checks if it were mistakenly run through that path.
    _mk_prd_v3(tmp_path)
    findings = routines.consolidate_signals(tmp_path)
    msgs = " ".join(f.message for f in findings)
    assert "features.md missing" not in msgs
    assert "overlap:" not in msgs
    assert "roadmap↔features" not in msgs


def test_consolidate_v3_warns_approaching_line_cap(tmp_path):
    _mk_prd_v3(tmp_path, extra_lines=220)
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert any("approaching the ~250-line cap" in m for m in msgs)
    assert not any("over the ~250-line cap" in m for m in msgs)


def test_consolidate_v3_warns_over_line_cap(tmp_path):
    _mk_prd_v3(tmp_path, extra_lines=260)
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert any("over the ~250-line cap" in m for m in msgs)


def test_consolidate_v3_under_cap_has_no_size_warning(tmp_path):
    _mk_prd_v3(tmp_path)
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert not any("line cap" in m for m in msgs)


def test_consolidate_v3_warns_stale_frontmatter(tmp_path):
    hdir = _mk_prd_v3(tmp_path, last_updated="2026-06-20")
    _mk_session(hdir, "s1.md", "2026-07-01T10:00:00")
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert any("last_updated" in m and "newest session note" in m for m in msgs)


def test_consolidate_v3_fresh_frontmatter_no_warning(tmp_path):
    hdir = _mk_prd_v3(tmp_path, last_updated="2026-07-01")
    _mk_session(hdir, "s1.md", "2026-06-20T10:00:00")
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert not any("last_updated" in m for m in msgs)


def test_consolidate_v3_warns_too_many_undistilled_sessions(tmp_path):
    hdir = _mk_prd_v3(tmp_path)
    for i in range(13):
        _mk_session(hdir, f"s{i}.md", "2026-06-01")
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert any("distill older ones to" in m and "sessions/archive" in m for m in msgs)


def test_consolidate_v3_few_sessions_no_warning(tmp_path):
    hdir = _mk_prd_v3(tmp_path)
    for i in range(5):
        _mk_session(hdir, f"s{i}.md", "2026-06-01")
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert not any("distill older ones to" in m for m in msgs)


def test_consolidate_v3_archived_sessions_excluded_from_count(tmp_path):
    hdir = _mk_prd_v3(tmp_path)
    (hdir / "sessions" / "archive").mkdir(parents=True)
    for i in range(20):
        (hdir / "sessions" / "archive" / f"a{i}.md").write_text("x", encoding="utf-8")
    for i in range(3):
        _mk_session(hdir, f"s{i}.md", "2026-06-01")
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert not any("distill older ones to" in m for m in msgs)


def test_consolidate_v3_warns_duplicate_backlog_titles(tmp_path):
    _mk_prd_v3(
        tmp_path,
        backlog=(
            "1. **Ship the widget.** Do it.\n"
            "2. **Other thing:** blah.\n"
            "3. **ship the widget** again, differently worded.\n"
        ),
    )
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert any("duplicate backlog title" in m and "ship the widget" in m.lower() for m in msgs)


def test_consolidate_v3_distinct_backlog_titles_no_warning(tmp_path):
    _mk_prd_v3(
        tmp_path,
        backlog="1. **Ship the widget.** Do it.\n2. **Ship the gadget.** Do it too.\n",
    )
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert not any("duplicate backlog title" in m for m in msgs)


def test_consolidate_v3_warns_lingering_checked_item(tmp_path):
    _mk_prd_v3(
        tmp_path,
        backlog="- [x] **Old task.** Already shipped.\n- [ ] **Open task.** Still pending.\n",
    )
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert any("Old task" in m and "delete it" in m for m in msgs)
    assert not any("Open task" in m and "delete it" in m for m in msgs)


def test_consolidate_v3_warns_lingering_done_prefix(tmp_path):
    _mk_prd_v3(
        tmp_path,
        backlog="1. DONE: ship the thing.\n2. Done: another one.\n3. Still open work.\n",
    )
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert sum("delete it" in m for m in msgs) == 2
    assert not any("Still open work" in m for m in msgs)


def test_consolidate_v3_result_pass_continuation_is_not_a_done_marker(tmp_path):
    # A "**Result ... PASS**" line inside an item, without its own list marker, is a
    # wrapped continuation of the item above — not a separate done item.
    _mk_prd_v3(
        tmp_path,
        backlog=(
            "1. **Big feature.** Long description spanning more than one line.\n"
            "   **Result (rerun 2026-07-03): PASS.** Zero failure flags.\n"
        ),
    )
    msgs = _warn_msgs(routines.consolidate_signals(tmp_path))
    assert not any("delete it" in m for m in msgs)


def test_consolidate_v2_still_unchanged_after_v3_branch_added(tmp_path):
    # Sanity: the v2 path (no PRD.md) still exercises the original lane-routing
    # signals, unaffected by the new v3 branch.
    _mk_horus(
        tmp_path,
        roadmap_body="# Roadmap\n\n## Now\n\n- [ ] parquet export compaction to prod\n",
        features_body="## Planned\n\n| Capability | Notes |\n|---|---|\n| parquet export compaction | x |\n",
    )
    findings = routines.consolidate_signals(tmp_path)
    overlaps = [f for f in findings if f.message.startswith("overlap:")]
    assert len(overlaps) == 1


# --------------------------------------------------------------------------- #
# infer — structure v3: report PRD skeleton gaps instead of six-lane placeholders
# --------------------------------------------------------------------------- #

def test_infer_v3_reports_prd_skeleton_gaps(tmp_path):
    (tmp_path / "README.md").write_text("# real project\n\ndoes things\n", encoding="utf-8")
    _mk_prd_v3(tmp_path)
    hdir = tmp_path / ".horus"
    # Overwrite with a placeholder Vision and a missing Rules section.
    (hdir / "PRD.md").write_text(
        '---\nstatus: active\nlast_updated: 2026-07-01\n---\n# PRD\n\n'
        "## Vision\n\nTODO describe the vision.\n\n"
        "## Backlog\n\n1. **Task.** Do it.\n\n"
        "## Shipped\n\nOne line per capability.\n",
        encoding="utf-8",
    )
    msgs = " ".join(f.message for f in routines.infer_signals(tmp_path))
    assert "PRD skeleton section(s) empty/placeholder" in msgs
    assert "Vision" in msgs
    assert "Rules" in msgs
    assert "canonical docs above" in msgs


def test_infer_v3_all_sections_populated(tmp_path):
    (tmp_path / "README.md").write_text("# real project\n\ndoes things\n", encoding="utf-8")
    _mk_prd_v3(tmp_path)
    msgs = " ".join(f.message for f in routines.infer_signals(tmp_path))
    assert "PRD skeleton sections" in msgs and "populated" in msgs
    assert "placeholder/empty lanes" not in msgs


def test_infer_v2_unaffected_by_v3_branch(tmp_path):
    from horus import templates

    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "project.md").write_text(templates.project_md("p", "2026-01-01"), encoding="utf-8")
    (hdir / "roadmap.md").write_text(templates.roadmap_md("2026-01-01"), encoding="utf-8")
    (hdir / "features.md").write_text(templates.features_md("2026-01-01"), encoding="utf-8")
    (hdir / "history.md").write_text(templates.history_md("2026-01-01"), encoding="utf-8")
    (tmp_path / "README.md").write_text("# real project\n\ndoes things\n", encoding="utf-8")

    msgs = " ".join(f.message for f in routines.infer_signals(tmp_path))
    assert "placeholder/empty lanes" in msgs
    assert "PRD skeleton" not in msgs




# --------------------------------------------------------------------------- #
# convergence read-out (v3): map cards onto Vision facets, phase-aware
# --------------------------------------------------------------------------- #

def _mk_prd_facets(root, *, vision_table=True):
    hdir = root / ".horus"
    (hdir / "backlog").mkdir(parents=True, exist_ok=True)
    vision = "## Vision\n\n"
    if vision_table:
        vision += (
            "| Facet | Definition of done |\n"
            "|---|---|\n"
            "| **Continuity core** | resumes. |\n"
            "| **PO lifecycle** | ships. |\n\n"
        )
    prd = (
        '---\nstatus: active\ncurrent_focus: "x"\nnext_action: "y"\n'
        'next_prompt: "z"\nexecution_recommendation: "continue-as-is"\n'
        "last_updated: 2026-07-16\n---\n\n# demo\n\n" + vision
        + "## Backlog\n\nmenu\n\n## Shipped\n\n- x\n\n## Rules\n\n- y\n"
    )
    (hdir / "PRD.md").write_text(prd, encoding="utf-8")
    return hdir


def _facet_card(hdir, name, *, facet="", phase="", status="open"):
    lines = ["---", f"status: {status}", "created: 2026-07-16"]
    if facet:
        lines.append(f'vision_facet: "{facet}"')
    if phase:
        lines.append(f"phase: {phase}")
    lines += ["---", f"# {name}", ""]
    (hdir / "backlog" / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def test_convergence_maps_cards_to_facets(tmp_path):
    hdir = _mk_prd_facets(tmp_path)
    _facet_card(hdir, "a", facet="PO lifecycle")
    _facet_card(hdir, "b", facet="Continuity core")
    msgs = " ".join(f.message for f in routines.consolidate_signals(tmp_path))
    assert "PO lifecycle (1)" in msgs
    assert "Continuity core (1)" in msgs


def test_convergence_reports_facets_with_no_open_cards(tmp_path):
    hdir = _mk_prd_facets(tmp_path)
    _facet_card(hdir, "a", facet="PO lifecycle")
    msgs = " ".join(f.message for f in routines.consolidate_signals(tmp_path))
    assert "no open cards" in msgs and "Continuity core" in msgs


def test_convergence_flags_off_vision_converge_card(tmp_path):
    hdir = _mk_prd_facets(tmp_path)
    _facet_card(hdir, "orphan")  # no facet, default converge phase
    warns = [f.message for f in routines.consolidate_signals(tmp_path) if f.level == "warn"]
    assert any("orphan" in m and "no vision_facet" in m for m in warns)


def test_convergence_exempts_explore_cards(tmp_path):
    hdir = _mk_prd_facets(tmp_path)
    _facet_card(hdir, "poc", phase="explore")  # no facet, but exploratory
    findings = routines.consolidate_signals(tmp_path)
    warns = [f.message for f in findings if f.level == "warn"]
    assert not any("poc" in m for m in warns)
    msgs = " ".join(f.message for f in findings)
    assert "exploratory" in msgs and "poc" in msgs


def test_convergence_flags_unknown_facet(tmp_path):
    hdir = _mk_prd_facets(tmp_path)
    _facet_card(hdir, "typo", facet="PO lifcycle")  # not a real facet
    warns = [f.message for f in routines.consolidate_signals(tmp_path) if f.level == "warn"]
    assert any("typo" in m and "unknown facet" in m for m in warns)


def test_convergence_facet_matching_is_case_insensitive(tmp_path):
    hdir = _mk_prd_facets(tmp_path)
    _facet_card(hdir, "a", facet="po lifecycle")  # lower-case variant
    findings = routines.consolidate_signals(tmp_path)
    assert not any(f.level == "warn" and "convergence" in f.message for f in findings)
    msgs = " ".join(f.message for f in findings)
    assert "PO lifecycle (1)" in msgs


def test_convergence_silent_without_a_facet_table(tmp_path):
    hdir = _mk_prd_facets(tmp_path, vision_table=False)
    _facet_card(hdir, "a")  # off-vision converge card, but no facets to converge against
    msgs = " ".join(f.message for f in routines.consolidate_signals(tmp_path))
    assert "convergence" not in msgs
