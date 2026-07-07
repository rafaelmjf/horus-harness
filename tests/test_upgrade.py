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
    initialize.init_project(tmp_path, assume_yes=True, with_hooks=False)

    actions = upgrade.upgrade_project(
        tmp_path,
        apply=True,
        targets=("codex",),
        skills_=False,
        instructions=False,
    )

    assert any(a.status in ("created", "updated") and "Codex usage hook" in a.message for a in actions)
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert data["hooks"]["Stop"][0]["hooks"][0]["command"].startswith("horus usage check")


def test_upgrade_refuses_to_downgrade_newer_block(tmp_path, monkeypatch):
    """An OLD installed CLI reading a NEWER pulled repo must not offer a downgrade
    'refresh' — it should say the CLI is what needs updating."""
    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    agents = tmp_path / "AGENTS.md"
    newer = agents.read_text(encoding="utf-8").replace(
        f"horus-block-version: {templates.BLOCK_VERSION}", "horus-block-version: 999"
    )
    agents.write_text(newer, encoding="utf-8")

    dry = upgrade.upgrade_project(tmp_path, apply=False, hooks=False, skills_=False)
    applied = upgrade.upgrade_project(tmp_path, apply=True, hooks=False, skills_=False)

    for actions in (dry, applied):
        flagged = [a for a in actions if "AGENTS.md" in a.message]
        assert flagged and flagged[0].status == "skipped"
        assert "newer than this CLI" in flagged[0].message
    assert "horus-block-version: 999" in agents.read_text(encoding="utf-8")  # untouched


def test_legacy_unversioned_block_still_refreshes(tmp_path, monkeypatch):
    """Blocks written before the version marker existed count as older."""
    from horus.instructions import block_version, extract_block

    _home(tmp_path, monkeypatch)
    initialize.init_project(tmp_path, assume_yes=True)
    agents = tmp_path / "AGENTS.md"
    legacy = agents.read_text(encoding="utf-8").replace(
        f"<!-- horus-block-version: {templates.BLOCK_VERSION} -->\n", ""
    )
    agents.write_text(legacy, encoding="utf-8")
    assert block_version(extract_block(legacy).raw or "") is None

    actions = upgrade.upgrade_project(tmp_path, apply=False, hooks=False, skills_=False)
    assert any(a.status == "would-update" and "AGENTS.md" in a.message for a in actions)


def test_shared_block_carries_version_marker():
    block = templates.shared_block("CLAUDE.md")
    assert f"<!-- horus-block-version: {templates.BLOCK_VERSION} -->" in block


def _write_v2_lanes(root):
    hdir = root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "project.md").write_text("---\nstatus: active\n---\n# Project\n\nVision.\n", encoding="utf-8")
    (hdir / "roadmap.md").write_text("---\nstatus: active\n---\n# Roadmap\n\n## Now\n\n- [ ] Task\n", encoding="utf-8")
    (hdir / "decisions.md").write_text("# Decisions\n\n- **Rule** — do it.\n", encoding="utf-8")
    return hdir


def test_pending_structure_migration_detects_v2(tmp_path):
    _write_v2_lanes(tmp_path)
    migration = upgrade.pending_structure_migration(tmp_path)
    assert migration is not None
    assert migration.key == "prd"
    assert migration.from_label == "six-lane (v2)" and migration.to_label == "PRD.md (v3)"


def test_pending_structure_migration_none_for_v3(tmp_path):
    _write_v2_lanes(tmp_path)
    (tmp_path / ".horus" / "PRD.md").write_text("---\nstatus: active\n---\n# PRD\n", encoding="utf-8")
    assert upgrade.pending_structure_migration(tmp_path) is None


def test_pending_structure_migration_none_when_required_lane_missing(tmp_path):
    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "project.md").write_text("# Project\n", encoding="utf-8")  # roadmap.md / decisions.md absent
    assert upgrade.pending_structure_migration(tmp_path) is None


def test_pending_structure_migration_none_without_horus_dir(tmp_path):
    assert upgrade.pending_structure_migration(tmp_path) is None


def test_structure_migration_by_key(tmp_path):
    assert upgrade.structure_migration_by_key("prd") is not None
    assert upgrade.structure_migration_by_key("nope") is None
