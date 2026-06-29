"""Tests for offboarding — clean removal of Horus from a project."""

import json
from pathlib import Path

from horus import config, initialize, native_hooks, offboard, skills
from horus.instructions import extract_block, remove_block


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _scaffold(tmp_path, monkeypatch):
    """A fully-onboarded project: .horus/ + managed blocks + skills + hooks + registered."""
    _home(tmp_path, monkeypatch)
    proj = tmp_path / "proj"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True, no_input=True)
    native_hooks.install_claude_usage_hook(proj)
    native_hooks.install_codex_usage_hook(proj)
    return proj


# --- remove_block ----------------------------------------------------------

def test_remove_block_strips_block_keeps_rest():
    block = __import__("horus.templates", fromlist=["shared_block"]).shared_block("CLAUDE.md")
    text = f"# Title\n\n{block}\n\n## Notes\n\n- keep me\n"
    new, removed = remove_block(text)
    assert removed is True
    assert not extract_block(new).found
    assert "# Title" in new and "- keep me" in new
    assert "\n\n\n" not in new  # gap collapsed


def test_remove_block_noop_without_block():
    new, removed = remove_block("# Just a file\n")
    assert removed is False and new == "# Just a file\n"


# --- offboard module -------------------------------------------------------

def test_offboard_dry_run_reports_without_removing(tmp_path, monkeypatch):
    proj = _scaffold(tmp_path, monkeypatch)
    actions = offboard.offboard_project(proj, apply=False)

    statuses = {a.status for a in actions}
    assert "would-remove" in statuses
    assert any(a.status == "kept" for a in actions)  # .horus kept, not removed, on dry run
    # Nothing actually changed:
    assert extract_block((proj / "AGENTS.md").read_text(encoding="utf-8")).found
    assert skills.skill_path(skills.SKILLS[0], proj, target="claude").parent.exists()
    assert config._as_key(proj) in config.load_projects()
    assert (proj / ".horus").is_dir()


def test_offboard_apply_removes_projected_keeps_horus(tmp_path, monkeypatch):
    proj = _scaffold(tmp_path, monkeypatch)
    offboard.offboard_project(proj, apply=True)

    # Managed block gone, but the file remains (other content preserved).
    assert (proj / "AGENTS.md").exists()
    assert not extract_block((proj / "AGENTS.md").read_text(encoding="utf-8")).found
    assert not extract_block((proj / "CLAUDE.md").read_text(encoding="utf-8")).found
    # Skills removed for both targets.
    for target in ("claude", "codex"):
        for s in skills.SKILLS:
            assert not skills.skill_path(s, proj, target=target).parent.exists()
    # Horus hooks removed.
    assert not native_hooks.file_has_horus_hooks(proj / ".claude" / "settings.json")
    assert not native_hooks.file_has_horus_hooks(proj / ".codex" / "hooks.json")
    # Unregistered.
    assert config._as_key(proj) not in config.load_projects()
    # .horus/ KEPT by default — the durable memory survives.
    assert (proj / ".horus").is_dir()


def test_offboard_purge_removes_horus(tmp_path, monkeypatch):
    proj = _scaffold(tmp_path, monkeypatch)
    offboard.offboard_project(proj, apply=True, purge=True)
    assert not (proj / ".horus").exists()


def test_offboard_keeps_non_horus_hooks(tmp_path, monkeypatch):
    proj = _scaffold(tmp_path, monkeypatch)
    settings = proj / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    # A user's own unrelated hook must survive offboarding.
    data["hooks"].setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": "echo mine"}]}
    )
    settings.write_text(json.dumps(data), encoding="utf-8")

    offboard.offboard_project(proj, apply=True)

    after = json.loads(settings.read_text(encoding="utf-8"))
    flat = json.dumps(after)
    assert "echo mine" in flat
    assert not native_hooks.file_has_horus_hooks(settings)
