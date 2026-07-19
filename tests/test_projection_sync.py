"""Tests for horus/projection_sync.py — per-surface (Claude vs Codex) projection
sync, each compared only to the installed CLI, never to each other."""

from pathlib import Path

from horus import initialize, native_hooks, projection_sync, skills, templates

_ALL_HOOK_INSTALLERS = (
    native_hooks.install_claude_usage_hook,
    native_hooks.install_claude_merge_hook,
    native_hooks.install_claude_guard_hook,
    native_hooks.install_codex_usage_hook,
    native_hooks.install_codex_merge_hook,
    native_hooks.install_codex_guard_hook,
)


def _init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _fully_synced_project(tmp_path, monkeypatch) -> Path:
    """Scaffold a real project and install every projected artifact - instructions,
    skills (both come from `init_project`), and native hooks (opt-in via
    `horus hook-install`, so `init_project` alone leaves them missing and both
    surfaces "behind" for hooks). Installing everything gives a genuinely
    fully-synced baseline to mutate from in each test.
    """
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "proj"
    proj.mkdir()
    initialize.init_project(proj, assume_yes=True, no_input=True)
    for install in _ALL_HOOK_INSTALLERS:
        install(proj)
    return proj


def test_fresh_project_is_in_sync(tmp_path, monkeypatch):
    proj = _fully_synced_project(tmp_path, monkeypatch)

    state = projection_sync.sync_state(proj)

    assert state["verdict"] == "in_sync"
    assert state["claude"] == {"status": "current", "pending": 0}
    assert state["codex"] == {"status": "current", "pending": 0}


def test_codex_skill_behind_marks_codex_only(tmp_path, monkeypatch):
    proj = _fully_synced_project(tmp_path, monkeypatch)
    skill_md = proj / ".agents" / "skills" / "horus-consolidate" / "SKILL.md"
    version = next(s.version for s in skills.SKILLS if s.name == "horus-consolidate")
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8").replace(
            f"horus-skill-version: {version}", "horus-skill-version: 1"
        ),
        encoding="utf-8",
    )

    state = projection_sync.sync_state(proj)

    assert state["verdict"] == "codex_behind"
    assert state["codex"]["status"] == "behind"
    assert state["codex"]["pending"] >= 1
    assert state["claude"] == {"status": "current", "pending": 0}


def test_claude_hooks_missing_marks_claude_only(tmp_path, monkeypatch):
    proj = _fully_synced_project(tmp_path, monkeypatch)
    (proj / ".claude" / "settings.json").unlink()

    state = projection_sync.sync_state(proj)

    assert state["verdict"] == "claude_behind"
    assert state["claude"]["status"] == "behind"
    assert state["claude"]["pending"] >= 1
    assert state["codex"] == {"status": "current", "pending": 0}


def test_both_surfaces_behind(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    proj = tmp_path / "proj"
    proj.mkdir()
    # Opt out of hooks at init to simulate a repo behind on them (init installs
    # the full projection set by default since the onboard-artifacts change).
    initialize.init_project(proj, assume_yes=True, no_input=True, with_hooks=False)

    state = projection_sync.sync_state(proj)

    assert state["verdict"] == "behind"
    assert state["claude"]["status"] == "behind"
    assert state["codex"]["status"] == "behind"


def test_cli_outdated_when_managed_block_is_newer(tmp_path, monkeypatch):
    proj = _fully_synced_project(tmp_path, monkeypatch)
    claude_md = proj / "CLAUDE.md"
    higher = templates.BLOCK_VERSION + 1
    claude_md.write_text(
        claude_md.read_text(encoding="utf-8").replace(
            f"horus-block-version: {templates.BLOCK_VERSION}", f"horus-block-version: {higher}"
        ),
        encoding="utf-8",
    )

    state = projection_sync.sync_state(proj)

    assert state["verdict"] == "cli_outdated"
    assert state["claude"]["status"] == "ahead"
    assert state["claude"]["pending"] == 0
    # Codex's own file (AGENTS.md) was untouched - only Claude is ahead.
    assert state["codex"]["status"] == "current"


def test_broken_project_returns_unknown(tmp_path, monkeypatch):
    proj = _fully_synced_project(tmp_path, monkeypatch)
    claude_md = proj / "CLAUDE.md"
    claude_md.unlink()
    claude_md.mkdir()  # a directory where the CLI expects a file -> read raises

    state = projection_sync.sync_state(proj)

    assert state == {"verdict": "unknown"}


def test_never_raises_when_upgrade_project_blows_up(tmp_path, monkeypatch):
    proj = _fully_synced_project(tmp_path, monkeypatch)

    def _boom(root, **kw):
        raise RuntimeError("simulated projection failure")

    monkeypatch.setattr(projection_sync.upgrade, "upgrade_project", _boom)

    assert projection_sync.sync_state(proj) == {"verdict": "unknown"}
