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


def test_missing_or_stale_and_findings(tmp_path):
    s = skills.SKILLS[0]
    assert skills.missing_or_stale(tmp_path) == list(skills.SKILLS)
    assert any(f.level == "warn" for f in skills.skill_findings(tmp_path))

    skills.write_skill(s, tmp_path)
    assert skills.missing_or_stale(tmp_path) == []
    assert all(f.level == "ok" for f in skills.skill_findings(tmp_path))


def test_stale_install_is_flagged(tmp_path):
    s = skills.SKILLS[0]
    path = skills.skill_path(s, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("<!-- horus-skill-version: 0 -->\n", encoding="utf-8")
    assert skills.missing_or_stale(tmp_path) == [s]
    assert any("outdated" in f.message for f in skills.skill_findings(tmp_path))


def test_user_scope_uses_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path, user=True).status == "created"
    assert (tmp_path / "home" / ".claude" / "skills" / s.name / "SKILL.md").is_file()
    # project scope under tmp_path is untouched
    assert not (tmp_path / ".claude").exists()


def test_init_scaffolds_skill_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path / "a", assume_yes=True)
    assert (tmp_path / "a" / ".claude" / "skills" / "horus-consolidate" / "SKILL.md").exists()


def test_init_no_skills_opts_out(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path / "b", assume_yes=True, with_skills=False)
    assert not (tmp_path / "b" / ".claude").exists()
