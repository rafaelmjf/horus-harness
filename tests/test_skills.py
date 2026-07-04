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


def test_all_bundled_skills_keep_a_marked_v2_fallback_section():
    # Phase 3 (v3-tooling): every rewritten skill keeps the six-lane guidance
    # reachable under an explicit, clearly-marked fallback heading.
    for s in skills.SKILLS:
        assert "## v2 six-lane projects (fallback)" in s.content, s.name


def test_consolidate_skill_v3_covers_backlog_hygiene_checks():
    consolidate = next(s for s in skills.SKILLS if s.name == "horus-consolidate")
    assert consolidate.version == 9
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
    assert execution.version == 7
    assert "testing model separation" in execution.content
    assert "do not implement" in execution.content
    assert "the delegated phase in the supervisor context" in execution.content
    assert "delegation_basis" in execution.content
    assert "worker_tier` is only the intended tier **if delegated**" in execution.content
    assert "A handoff" in execution.content
    assert "written by the supervisor after doing the work" in execution.content
    # v4: the volume × ambiguity × runtime delegation rubric + honest review caveat.
    assert "volume × ambiguity" in execution.content
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
