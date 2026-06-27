"""Tests for project-local Horus projection upgrades."""

import json

from horus import initialize, skills, templates, upgrade


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_upgrade_project_dry_run_reports_without_writing(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    agents = tmp_path / "AGENTS.md"
    old = agents.read_text(encoding="utf-8")
    agents.write_text(old.replace("Horus Project Continuity", "Old Horus Project Continuity"), encoding="utf-8")

    actions = upgrade.upgrade_project(tmp_path, apply=False, hooks=False, skills_=False)

    assert any(a.status == "would-update" and "AGENTS.md" in a.message for a in actions)
    assert "Old Horus Project Continuity" in agents.read_text(encoding="utf-8")


def test_upgrade_project_apply_refreshes_instruction_block(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        agents.read_text(encoding="utf-8").replace("Horus Project Continuity", "Old Horus Project Continuity"),
        encoding="utf-8",
    )

    actions = upgrade.upgrade_project(tmp_path, apply=True, hooks=False, skills_=False)

    assert any(a.status == "updated" and "AGENTS.md" in a.message for a in actions)
    assert templates.shared_block("CLAUDE.md") in agents.read_text(encoding="utf-8")


def test_upgrade_project_refreshes_stale_skills(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    path = skills.skill_path(skills.SKILLS[0], tmp_path, target="codex")
    path.write_text("<!-- horus-skill-version: 0 -->\nstale\n", encoding="utf-8")

    actions = upgrade.upgrade_project(tmp_path, apply=True, hooks=False, instructions=False, targets=("codex",))

    assert any(a.status == "updated" and skills.SKILLS[0].name in a.message for a in actions)
    assert f"horus-skill-version: {skills.SKILLS[0].version}" in path.read_text(encoding="utf-8")


def test_upgrade_project_apply_installs_codex_hooks(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)

    actions = upgrade.upgrade_project(
        tmp_path,
        apply=True,
        targets=("codex",),
        skills_=False,
        instructions=False,
    )

    assert any(a.status in ("created", "updated") and "Codex usage hook" in a.message for a in actions)
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert data["hooks"]["Stop"][0]["hooks"][0]["command"].startswith("python3 -m horus")
