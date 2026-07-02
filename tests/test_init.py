"""Tests for `horus init` scaffolding behavior (no-clobber, block injection)."""

from horus import initialize
from horus.continuity import check_project
from horus.instructions import extract_block


def test_init_creates_structure(tmp_path, monkeypatch):
    # Keep the user config out of the real home directory.
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    actions = initialize.init_project(tmp_path, assume_yes=True)
    statuses = {a.message: a.status for a in actions}

    assert (tmp_path / ".horus" / "project.md").exists()
    assert (tmp_path / ".horus" / "roadmap.md").exists()
    assert (tmp_path / ".horus" / "decisions.md").exists()
    assert (tmp_path / ".horus" / "features.md").exists()
    assert (tmp_path / ".horus" / "execution.md").exists()
    assert (tmp_path / ".horus" / "history.md").exists()
    assert (tmp_path / ".horus" / "sessions").is_dir()
    assert (tmp_path / ".horus" / "sessions" / ".gitkeep").exists()
    assert (tmp_path / ".horus" / "temp").is_dir()
    assert (tmp_path / ".horus" / "temp" / ".gitkeep").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    gitignore = (tmp_path / ".horus" / ".gitignore").read_text(encoding="utf-8")
    assert "sessions/*.md" in gitignore
    assert "!sessions/.gitkeep" in gitignore
    assert "temp/*" in gitignore
    assert "!temp/.gitkeep" in gitignore
    assert not (tmp_path / ".gitignore").exists()  # no root .gitignore managed
    assert any(s == "created" for s in statuses.values())
    # Native hooks are part of the init projection set, so onboarding commits the
    # complete surface at once (they used to arrive later and land untracked).
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".codex" / "hooks.json").exists()


def test_init_no_hooks_skips_hook_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True, with_hooks=False)

    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".codex" / "hooks.json").exists()


def test_init_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True)
    before = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    actions = initialize.init_project(tmp_path, assume_yes=True)
    after = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    assert before == after  # no clobber, no duplicate blocks
    assert all(a.status in ("exists",) for a in actions if "CLAUDE" in a.message)
    # gitignore must not gain a duplicate rule.
    assert (tmp_path / ".horus" / ".gitignore").read_text(encoding="utf-8").count(
        "sessions/*.md"
    ) == 1
    assert (tmp_path / ".horus" / ".gitignore").read_text(encoding="utf-8").count(
        "temp/*"
    ) == 1


def test_init_preserves_existing_instruction_file_and_injects_block(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    existing = "# My Project\n\nHand-written guidance.\n"
    (tmp_path / "AGENTS.md").write_text(existing, encoding="utf-8")

    initialize.init_project(tmp_path, assume_yes=True)
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    assert "Hand-written guidance." in text  # original preserved
    assert extract_block(text).found  # block injected


def test_init_skips_injection_without_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    (tmp_path / "AGENTS.md").write_text("# Mine\n", encoding="utf-8")
    initialize.init_project(tmp_path, no_input=True)
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

    assert not extract_block(text).found  # left untouched
    assert text == "# Mine\n"


def test_doctor_passes_on_fresh_init(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True)
    findings = check_project(tmp_path)
    assert not any(f.level == "fail" for f in findings)
