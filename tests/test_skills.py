"""Tests for the bundled agent-skills layer (scaffold, version-aware install, doctor)."""

from horus import initialize, skills


def test_bundled_skills_have_version_markers():
    assert skills.SKILLS  # at least one shipped skill
    for s in skills.SKILLS:
        assert s.content.startswith("---")  # YAML frontmatter
        assert "name:" in s.content and "description:" in s.content
        assert skills.installed_version(s.content) == s.version


def test_write_skill_create_then_exists(tmp_path):
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path).status == "created"
    assert skills.skill_path(s, tmp_path).is_file()
    assert skills.write_skill(s, tmp_path).status == "exists"


def test_write_codex_skill_uses_agents_directory(tmp_path):
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path, target="codex").status == "created"
    assert (tmp_path / ".agents" / "skills" / s.name / "SKILL.md").is_file()
    assert not (tmp_path / ".claude").exists()


def test_write_skill_upgrades_older_version(tmp_path):
    s = skills.SKILLS[0]
    path = skills.skill_path(s, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("<!-- horus-skill-version: 0 -->\nstale body\n", encoding="utf-8")
    assert skills.write_skill(s, tmp_path).status == "updated"
    assert skills.installed_version(path.read_text(encoding="utf-8")) == s.version


def test_write_skill_skips_unversioned_without_force(tmp_path):
    s = skills.SKILLS[0]
    path = skills.skill_path(s, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("hand-written, no marker\n", encoding="utf-8")
    assert skills.write_skill(s, tmp_path).status == "skipped"
    assert skills.write_skill(s, tmp_path, force=True).status == "updated"


def test_expected_skills_registered():
    names = {s.name for s in skills.SKILLS}
    assert {"horus-consolidate", "horus-distill-history", "horus-infer", "horus-execution"} <= names


def test_delegation_decision_skills_registered():
    # Slice 2: the shared rubric + the two thin consumer skills.
    names = {s.name for s in skills.SKILLS}
    assert {"delegation-rubric", "execution-decision", "dispatch-decision"} <= names


def test_delegation_rubric_is_the_shared_single_source_of_truth():
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    # Reads the Slice 1 data-only surface, never a pick/router.
    assert "horus capabilities --models" in rubric.content
    assert "--for" in rubric.content  # explicitly forbids adding a pick mode
    assert "data-only" in rubric.content.lower()
    # Tier-trust ladder is data-driven, not hardcoded to a model.
    assert "tier-trust" in rubric.content.lower()
    assert "Proven" in rubric.content and "Unproven" in rubric.content
    assert "clean_count" in rubric.content and "last_outcomes" in rubric.content
    assert "quality_datums" in rubric.content
    assert "died_count" in rubric.content and "void_count" in rubric.content
    # The one lever sets BOTH the pick and the verification depth.
    assert "same tier-trust sets BOTH" in rubric.content or "SAME tier-trust" in rubric.content
    # Verification = observe a gate you didn't author; reproduction != re-run.
    assert "did NOT author" in rubric.content
    assert "Reproduction ≠ re-running" in rubric.content
    assert "CI check green on the" in rubric.content
    # Runtime/visual surface defaults to the owner.
    assert "asking the OWNER" in rubric.content
    # Owner caution/guard flags gate the pick without pinning a current model.
    assert "caution" in rubric.content and "guard" in rubric.content
    assert "token-headroom guard" in rubric.content and "ceiling is near" in rubric.content
    # Hard boundary held.
    assert "advisory" in rubric.content.lower()
    assert "research/omnigent.md" in rubric.content


def test_delegation_rubric_keeps_older_capable_models_in_roster():
    # Fold-in ask (delegation-matrix-display card): don't drop a model from the
    # ladder on recency alone — pick by capability-for-the-task and keep
    # gathering datums on it.
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    assert "older-but-capable" in rubric.content.lower()
    assert "not by release date" in rubric.content.lower() or "not recency" in rubric.content.lower()


def test_delegation_rubric_proves_dividend_before_model_selection():
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    assert rubric.version == 5
    assert rubric.content.index("prove delegation has a dividend") < rubric.content.index(
        "Read the calibration data"
    )
    assert "Cross-project scope, multiple phases" in rubric.content
    assert "Never manufacture work or a worker solely to earn a datum" in rubric.content
    assert "temporarily lifted" in rubric.content and "owner-provided" in rubric.content
    assert "today:" not in rubric.content
    for pinned_model in ("sonnet-5", "opus-4.8", "haiku-4.5", "gpt-5.6"):
        assert pinned_model not in rubric.content


def test_delegation_shape_tiers_and_verification_dial_are_structured_and_single_sourced():
    # `horus capabilities --matrix` reads these tables directly (see cli.py /
    # datums.py) instead of forking a duplicate copy of the rubric's mapping.
    shapes = {row["shape"] for row in skills.DELEGATION_SHAPE_TIERS}
    assert {"scoped-impl", "novel", "mechanical"} <= shapes
    for row in skills.DELEGATION_SHAPE_TIERS:
        assert row["tier_role"] and row["description"]

    trusts = {row["tier_trust"] for row in skills.DELEGATION_VERIFICATION_DIAL}
    assert {"proven", "unproven", "runtime"} <= trusts
    for row in skills.DELEGATION_VERIFICATION_DIAL:
        assert row["verification"] and row["description"]


def test_both_consumer_skills_import_the_shared_rubric():
    # The logic lives once, in the rubric; each skill loads it by relative path.
    for name in ("execution-decision", "dispatch-decision"):
        skill = next(s for s in skills.SKILLS if s.name == name)
        assert "../delegation-rubric/SKILL.md" in skill.content, name
        assert "restate or fork" in skill.content, name
        # The data-reading logic lives in the rubric, not forked here; each
        # consumer still names the calibration surface it defers to.
        assert "calibration" in skill.content, name
        # Advisory boundary held in each thin consumer.
        assert "never auto" in skill.content or "nothing here auto-runs" in skill.content, name


def test_execution_decision_skill_is_in_project_subagents():
    skill = next(s for s in skills.SKILLS if s.name == "execution-decision")
    assert skill.version == 2
    # Its mode vocabulary + the in-project verification specialization.
    assert "`inline`" in skill.content and "`subagent-plan`" in skill.content
    assert "RUNS the gate at the phase boundary" in skill.content
    assert "TRUSTS the code" in skill.content
    assert "execution_recommendation" in skill.content
    assert "horus datum close" in skill.content


def test_dispatch_decision_skill_is_cockpit_multiproject():
    skill = next(s for s in skills.SKILLS if s.name == "dispatch-decision")
    assert skill.version == 2
    # Its mode vocabulary, account routing, and the overseer verification note.
    assert "`inline-here`" in skill.content
    assert "`dispatched-worker`" in skill.content
    assert "`dispatched-plan`" in skill.content
    assert "away from the overseer account" in skill.content
    assert "horus usage check" in skill.content
    assert "Overseer usage is a cost to weigh, not a presumption" in skill.content
    assert "Cross-project scope alone is insufficient" in skill.content
    assert "Do not dispatch merely to collect a datum" in skill.content
    assert "owner-provided" in skill.content
    # Observe CI green on the merge SHA; do not re-run the suite.
    assert "required CI check green on the merge SHA" in skill.content
    assert "Do NOT re-run" in skill.content


def test_all_bundled_skills_keep_a_marked_v2_fallback_section():
    # Phase 3 (v3-tooling): every rewritten skill keeps the six-lane guidance
    # reachable under an explicit, clearly-marked fallback heading.
    for s in skills.SKILLS:
        assert "## v2 six-lane projects (fallback)" in s.content, s.name


def test_consolidate_skill_v3_covers_backlog_hygiene_checks():
    consolidate = next(s for s in skills.SKILLS if s.name == "horus-consolidate")
    assert consolidate.version == 10
    assert "PRD.md" in consolidate.content
    assert "no lane-routing/overlap warnings" in consolidate.content
    assert "~250-line cap" in consolidate.content
    assert "Stale frontmatter" in consolidate.content
    assert "Undistilled session notes" in consolidate.content
    assert "Duplicate backlog titles" in consolidate.content
    assert "Lingering done items" in consolidate.content
    assert "one line" in consolidate.content and "not a paragraph" in consolidate.content
    # sessions/ and temp/ handoff notes stay unchanged in v3.
    assert "temp/" in consolidate.content


def test_infer_skill_v3_reports_prd_skeleton_gaps():
    infer = next(s for s in skills.SKILLS if s.name == "horus-infer")
    assert infer.version == 3
    assert "Vision" in infer.content and "Backlog" in infer.content
    assert "Shipped" in infer.content and "Rules" in infer.content
    assert "PRD.md" in infer.content


def test_distill_history_skill_v3_targets_archive():
    distill = next(s for s in skills.SKILLS if s.name == "horus-distill-history")
    assert distill.version == 3
    assert ".horus/archive/history.md" in distill.content
    assert "PRD.md" in distill.content


def test_execution_skill_requires_real_delegation_for_model_separation():
    execution = next(s for s in skills.SKILLS if s.name == "horus-execution")
    assert execution.version == 9
    assert "testing model separation" in execution.content
    assert "do not implement" in execution.content
    assert "the delegated phase in the supervisor context" in execution.content
    assert "delegation_basis" in execution.content
    assert "worker_tier` is only the intended tier **if delegated**" in execution.content
    assert "A handoff" in execution.content
    assert "written by the supervisor after doing the work" in execution.content
    # Need-first delegation guard + honest review caveat.
    assert "require a concrete dividend" in execution.content
    assert "Do not enter this workflow" in execution.content
    assert "never pin durable guidance to current model names" in execution.content
    assert "safety guarantee" in execution.content  # honest review caveat
    assert "does not satisfy the workflow test" in execution.content
    # v5: cross-agent workers — mark a phase for the other CLI and spawn it tracked.
    assert "worker_agent: codex" in execution.content
    assert "horus run --agent codex" in execution.content
    assert "shares no conversation history" in execution.content
    assert "reproduce the gate yourself" in execution.content
    # v7: signal-based acceptance — required CI green counts as reproduction of the
    # test gate; one runtime probe stays with the supervisor; no proof narratives.
    assert "deterministic signal" in execution.content
    assert "required CI check green" in execution.content
    assert "one runtime probe" in execution.content
    assert "No proof narratives" in execution.content
    assert "pre-existing failure baseline" in execution.content
    # v8: orchestrator > supervisor > worker — the pilot's lessons, encoded.
    assert "orchestrator implements nothing" in execution.content
    assert "One git worktree per worker" in execution.content
    assert "--posture full-auto" in execution.content
    assert "Bounce protocol" in execution.content
    assert "Merge sequencing" in execution.content


def test_execution_template_carries_worker_agent_marking():
    from horus import templates

    doc = templates.execution_md("2026-07-03")
    assert "| worker_tier | worker_agent |" in doc  # Active Phases column
    assert "`worker_agent` marks which agent CLI runs a delegated phase" in doc
    assert "horus run --agent codex --account <alias>" in doc
    assert "cold reader" in doc


def test_missing_or_stale_and_findings(tmp_path):
    assert skills.missing_or_stale(tmp_path) == list(skills.SKILLS)
    assert any(f.level == "warn" for f in skills.skill_findings(tmp_path))

    skills.install_skills(tmp_path)
    assert skills.missing_or_stale(tmp_path) == []
    assert all(f.level == "ok" for f in skills.skill_findings(tmp_path))


def test_missing_or_stale_is_target_specific(tmp_path):
    skills.install_skills(tmp_path, targets=("codex",))
    assert skills.missing_or_stale(tmp_path, target="codex") == []
    assert skills.missing_or_stale(tmp_path, target="claude") == list(skills.SKILLS)


def test_stale_install_is_flagged(tmp_path):
    skills.install_skills(tmp_path)  # all current
    s = skills.SKILLS[0]
    skills.skill_path(s, tmp_path).write_text("<!-- horus-skill-version: 0 -->\n", encoding="utf-8")
    assert skills.missing_or_stale(tmp_path) == [s]  # only the downgraded one
    assert any("outdated" in f.message for f in skills.skill_findings(tmp_path))


def test_user_scope_uses_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path, user=True).status == "created"
    assert (tmp_path / "home" / ".claude" / "skills" / s.name / "SKILL.md").is_file()
    # project scope under tmp_path is untouched
    assert not (tmp_path / ".claude").exists()


def test_init_scaffolds_all_skills_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path / "a", assume_yes=True)
    for s in skills.SKILLS:
        assert (tmp_path / "a" / ".claude" / "skills" / s.name / "SKILL.md").exists()
        assert (tmp_path / "a" / ".agents" / "skills" / s.name / "SKILL.md").exists()


def test_init_no_skills_opts_out(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path / "b", assume_yes=True, with_skills=False, with_hooks=False)
    assert not (tmp_path / "b" / ".claude").exists()
