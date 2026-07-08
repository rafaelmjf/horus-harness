"""Tests for project-local Horus projection upgrades."""

import json

from horus import frontmatter, initialize, skills, templates, upgrade


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


def test_upgrade_backfills_min_version_stamp(tmp_path, monkeypatch):
    from horus import versioning

    _home(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    # A v3 PRD.md predating the stamp.
    (hdir / "PRD.md").write_text(
        "---\nstatus: active\nlast_updated: 2026-07-08\n---\n\n# P\n", encoding="utf-8"
    )

    dry = upgrade.upgrade_project(tmp_path, apply=False, hooks=False, skills_=False)
    assert any(a.status == "would-update" and versioning.MIN_VERSION_KEY in a.message for a in dry)
    assert versioning.MIN_VERSION_KEY not in (hdir / "PRD.md").read_text(encoding="utf-8")

    upgrade.upgrade_project(tmp_path, apply=True, hooks=False, skills_=False)
    doc = frontmatter.parse((hdir / "PRD.md").read_text(encoding="utf-8"))
    assert doc.front_matter[versioning.MIN_VERSION_KEY] == versioning.MIN_CLI_VERSION

    # Idempotent: a second apply reports "exists", not another write.
    again = upgrade.upgrade_project(tmp_path, apply=True, hooks=False, skills_=False)
    assert any(a.status == "exists" and versioning.MIN_VERSION_KEY in a.message for a in again)


def test_upgrade_does_not_lower_a_higher_stamp(tmp_path, monkeypatch):
    from horus import versioning

    _home(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "PRD.md").write_text(
        "---\nstatus: active\nhorus_min_version: 9.9.9\nlast_updated: 2026-07-08\n---\n\n# P\n",
        encoding="utf-8",
    )
    actions = upgrade.upgrade_project(tmp_path, apply=True, hooks=False, skills_=False)
    assert any(a.status == "exists" and versioning.MIN_VERSION_KEY in a.message for a in actions)
    doc = frontmatter.parse((hdir / "PRD.md").read_text(encoding="utf-8"))
    assert doc.front_matter[versioning.MIN_VERSION_KEY] == "9.9.9"


def test_upgrade_skips_stamp_for_v2_project(tmp_path, monkeypatch):
    from horus import versioning

    _home(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "project.md").write_text(
        "---\nstatus: active\nlast_updated: 2026-07-08\n---\n\n# P\n", encoding="utf-8"
    )
    actions = upgrade.upgrade_project(tmp_path, apply=True, hooks=False, skills_=False)
    assert not any(versioning.MIN_VERSION_KEY in a.message for a in actions)
