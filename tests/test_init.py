"""Tests for `horus init` scaffolding behavior (no-clobber, block injection)."""

from horus import closure, initialize
from horus.continuity import check_project
from horus.instructions import extract_block


def test_init_creates_structure(tmp_path, monkeypatch):
    # Keep the user config out of the real home directory.
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    actions = initialize.init_project(tmp_path, assume_yes=True)
    statuses = {a.message: a.status for a in actions}

    # A fresh project gets structure v3: PRD.md + sessions/, not the six v2 lanes.
    assert (tmp_path / ".horus" / "PRD.md").exists()
    # The fresh PRD carries the structure-version floor stamp (Lever B pairing data).
    from horus import versioning

    prd_text = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert f"{versioning.MIN_VERSION_KEY}: {versioning.MIN_CLI_VERSION}" in prd_text
    assert not (tmp_path / ".horus" / "project.md").exists()
    assert not (tmp_path / ".horus" / "roadmap.md").exists()
    assert not (tmp_path / ".horus" / "decisions.md").exists()
    assert not (tmp_path / ".horus" / "features.md").exists()
    assert not (tmp_path / ".horus" / "execution.md").exists()
    assert not (tmp_path / ".horus" / "history.md").exists()
    assert (tmp_path / ".horus" / "sessions").is_dir()
    assert (tmp_path / ".horus" / "sessions" / ".gitkeep").exists()
    assert (tmp_path / ".horus" / "backlog" / ".gitkeep").exists()
    assert (tmp_path / ".horus" / "temp").is_dir()
    assert (tmp_path / ".horus" / "temp" / ".gitkeep").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    gitignore = (tmp_path / ".horus" / ".gitignore").read_text(encoding="utf-8")
    assert "sessions/*.md" in gitignore
    assert "!sessions/.gitkeep" in gitignore
    assert "temp/*" in gitignore
    assert "!temp/.gitkeep" in gitignore
    assert ".consolidated-to" in gitignore
    assert "backlog/.claim.lock" in gitignore
    assert "backlog/.*.sw?" in gitignore
    assert not (tmp_path / ".gitignore").exists()  # no root .gitignore managed
    assert any(s == "created" for s in statuses.values())
    # Native hooks are part of the init projection set, so onboarding commits the
    # complete surface at once (they used to arrive later and land untracked).
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".codex" / "hooks.json").exists()


def test_init_scaffolds_blank_tracked_backlog_dir(tmp_path, monkeypatch):
    """Card-per-file backlog is the fleet standard: `horus init` on a fresh
    project tracks a blank `.horus/backlog/` without inventing work, and the
    PRD's `## Backlog` is a thin pointer, not an inline list."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    from horus import backlog

    actions = initialize.init_project(tmp_path, assume_yes=True)

    bdir = tmp_path / ".horus" / "backlog"
    assert bdir.is_dir()
    cards = list(bdir.glob("*.md"))
    assert cards == []
    assert (bdir / ".gitkeep").is_file()
    assert any(a.status == "created" and "backlog" in a.message for a in actions)

    loaded = backlog.load_cards(tmp_path)
    assert loaded == []

    prd_text = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    assert "one card per item" in prd_text
    assert "Now / next candidates" not in prd_text
    assert "Blank Horus scaffold" in prd_text
    assert "Run `horus infer`" not in prd_text


def test_init_never_clobbers_populated_backlog_dir(tmp_path, monkeypatch):
    """A project that already has real cards remains unchanged."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True)
    bdir = tmp_path / ".horus" / "backlog"
    for card in bdir.glob("*.md"):
        card.unlink()
    (bdir / "real-card.md").write_text(
        "---\nstatus: open\npriority: high\ntype: task\ncreated: 2026-07-12\n---\n# Real card\n",
        encoding="utf-8",
    )

    initialize.init_project(tmp_path, assume_yes=True)

    cards = sorted(p.name for p in bdir.glob("*.md"))
    assert cards == ["real-card.md"]


def test_init_fresh_prd_scaffold_passes_close_check(tmp_path, monkeypatch):
    """A freshly scaffolded PRD.md must clear the freshness gate immediately —
    its bootstrap frontmatter values are non-empty (no session exists yet to be
    stale against)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True)
    findings = closure.freshness_gate(tmp_path)
    assert not any(f.level in ("warn", "fail") for f in findings)


def test_init_on_existing_v2_project_unchanged(tmp_path, monkeypatch):
    """`init` on a project already carrying the six v2 lanes (marked by project.md,
    no PRD.md) must keep scaffolding those lanes, never switch it to v3."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "project.md").write_text(
        '---\nproject: demo\nstatus: planning\ncurrent_focus: "hand-authored"\n---\n# demo\n',
        encoding="utf-8",
    )

    initialize.init_project(tmp_path, assume_yes=True)

    assert not (hdir / "PRD.md").exists()
    assert (hdir / "roadmap.md").exists()
    assert (hdir / "features.md").exists()
    assert (hdir / "decisions.md").exists()
    assert (hdir / "history.md").exists()
    assert (hdir / "execution.md").exists()
    # never-clobber: the hand-authored project.md is untouched.
    assert "hand-authored" in (hdir / "project.md").read_text(encoding="utf-8")


def test_init_on_existing_v3_project_never_creates_six_lanes(tmp_path, monkeypatch):
    """`init` on a project already carrying PRD.md must never overwrite it and
    must never scaffold the six v2 lanes alongside it."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "PRD.md").write_text(
        '---\nstatus: active\ncurrent_focus: "hand-authored"\n---\n# PRD\n', encoding="utf-8"
    )

    initialize.init_project(tmp_path, assume_yes=True)

    assert "hand-authored" in (hdir / "PRD.md").read_text(encoding="utf-8")
    for lane in ("project.md", "roadmap.md", "features.md", "decisions.md", "history.md", "execution.md"):
        assert not (hdir / lane).exists()
    # An existing v3 project without a backlog/ dir yet also gets scaffolded.
    assert (hdir / "backlog" / ".gitkeep").is_file()
    assert list((hdir / "backlog").glob("*.md")) == []


def test_init_v3_scaffold_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True)
    before = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")
    actions = initialize.init_project(tmp_path, assume_yes=True)
    after = (tmp_path / ".horus" / "PRD.md").read_text(encoding="utf-8")

    assert before == after
    assert any(a.status == "exists" and "PRD.md" in a.message for a in actions)


def test_init_no_hooks_skips_hook_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True, with_hooks=False)

    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".codex" / "hooks.json").exists()


def test_init_ci_scaffolds_gate_with_lfs_step(tmp_path, monkeypatch):
    """A repo that already tracks LFS objects (.gitattributes declares an lfs
    filter) gets a generated gate that includes the `git lfs fsck` step."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    (tmp_path / ".gitattributes").write_text(
        "*.psd filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8"
    )

    actions = initialize.init_project(tmp_path, assume_yes=True, ci=True)

    workflow = tmp_path / ".github" / "workflows" / "horus-gate.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")
    assert "horus doctor project" in text
    assert "git lfs fsck" in text
    assert "lfs: true" in text
    assert any(a.status == "created" and "horus-gate.yml" in a.message for a in actions)


def test_init_ci_scaffolds_doctor_only_gate_for_plain_repo(tmp_path, monkeypatch):
    """A plain docs/vault repo with no LFS and no Makefile test target still gets
    a gate — doctor-only, but green (no lfs/build steps fabricated)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True, ci=True)

    workflow = tmp_path / ".github" / "workflows" / "horus-gate.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")
    assert "horus doctor project" in text
    assert "git lfs fsck" not in text
    assert "make test" not in text


def test_init_ci_detects_makefile_test_target(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    (tmp_path / "Makefile").write_text("test:\n\tpytest -q\n", encoding="utf-8")

    initialize.init_project(tmp_path, assume_yes=True, ci=True)

    text = (tmp_path / ".github" / "workflows" / "horus-gate.yml").read_text(encoding="utf-8")
    assert "make test" in text


def test_init_without_ci_flag_skips_workflow(tmp_path, monkeypatch):
    """Opt-in only: a repo that doesn't ask for --ci is left without the workflow
    file — existing repos and repos that opt out are untouched."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))

    initialize.init_project(tmp_path, assume_yes=True)

    assert not (tmp_path / ".github" / "workflows" / "horus-gate.yml").exists()


def test_init_ci_never_clobbers_existing_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    existing = "name: hand-written\n"
    (workflows / "horus-gate.yml").write_text(existing, encoding="utf-8")

    actions = initialize.init_project(tmp_path, assume_yes=True, ci=True)

    assert (workflows / "horus-gate.yml").read_text(encoding="utf-8") == existing
    assert any(a.status == "exists" and "horus-gate.yml" in a.message for a in actions)


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
    assert (tmp_path / ".horus" / ".gitignore").read_text(encoding="utf-8").count(
        ".consolidated-to"
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
    assert any(f.level == "ok" and "recovery notes (optional)" in f.message for f in findings)
    assert not any(f.level == "warn" and "session" in f.message for f in findings)


def test_doctor_v3_prd_project_needs_no_lanes(tmp_path):
    # Structure v3: PRD.md + sessions/ — the six lanes must not be required.
    hdir = tmp_path / ".horus"
    (hdir / "sessions").mkdir(parents=True)
    (hdir / "PRD.md").write_text(
        '---\nstatus: active\ncurrent_focus: "Ship it"\n---\n# PRD\n\n## Vision\n', encoding="utf-8"
    )
    (hdir / "sessions" / "s1.md").write_text("---\ndate: 2026-07-03\n---\n# s\n", encoding="utf-8")

    findings = check_project(tmp_path)
    assert not any(f.level == "fail" for f in findings)
    assert not any("missing" in f.message for f in findings)
    assert any("PRD.md present" in f.message for f in findings)


def test_doctor_v3_warns_on_missing_focus(tmp_path):
    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "PRD.md").write_text("---\nstatus: active\n---\n# PRD\n", encoding="utf-8")

    findings = check_project(tmp_path)
    assert any(f.level == "warn" and "no current_focus" in f.message for f in findings)
