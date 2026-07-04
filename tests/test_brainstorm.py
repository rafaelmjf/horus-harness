"""Tests for the shared brainstorm code path (`horus.brainstorm`)."""

import pytest

from horus import brainstorm, launch, launcher, registry
from horus.registry import Registry

_PRD = """---
status: active
current_focus: "x"
---

# Demo — PRD

## Vision

A lightweight continuity layer. Out of scope: multi-user SaaS.

## Backlog

### Now / next candidates

1. **Catalog niceties:** badge private repos.

## Shipped

- something already shipped.

## Rules (load-bearing)

- **Repo-local `.horus/` is the source of truth** — committed, vendor-neutral.
"""


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _project(tmp_path, prd: str | None = _PRD):
    root = tmp_path / "demo"
    (root / ".horus").mkdir(parents=True)
    if prd is not None:
        (root / ".horus" / "PRD.md").write_text(prd, encoding="utf-8")
    return root


def test_slugify_bounds_and_fallback():
    assert brainstorm.slugify("Offline-First Sync!") == "offline-first-sync"
    assert brainstorm.slugify("   ") == "session"
    assert brainstorm.slugify("!!!") == "session"
    long = brainstorm.slugify("word " * 40)
    assert len(long) <= 60 and not long.endswith("-")


def test_note_relpath_targets_temp():
    assert brainstorm.note_relpath("Sync now") == ".horus/temp/brainstorm-sync-now.md"


def test_build_prompt_carries_scoped_prd_context(tmp_path):
    root = _project(tmp_path)
    prompt = brainstorm.build_prompt(root, "offline-first sync")

    # The topic and each scoped PRD section land in the prompt.
    assert "offline-first sync" in prompt
    assert "A lightweight continuity layer" in prompt          # Vision
    assert "Catalog niceties" in prompt                        # Backlog
    assert "source of truth" in prompt                         # Rules (annotated heading)

    # Output contract: write to temp, never touch PRD.md, don't commit.
    assert ".horus/temp/brainstorm-offline-first-sync.md" in prompt
    assert "Do NOT edit `.horus/PRD.md`" in prompt
    assert "Do NOT commit" in prompt


def test_build_prompt_stays_minimal(tmp_path):
    # Minimal context by contract: it tells the session NOT to read sessions/archive,
    # and it does not inline the Shipped ledger.
    root = _project(tmp_path)
    prompt = brainstorm.build_prompt(root, "topic")
    assert "Do NOT" in prompt and "`.horus/sessions/`" in prompt and "`.horus/archive/`" in prompt
    assert "something already shipped" not in prompt


def test_build_prompt_degrades_without_prd(tmp_path):
    root = _project(tmp_path, prd=None)
    prompt = brainstorm.build_prompt(root, "topic")
    assert "(no Vision section recorded in PRD.md)" in prompt
    assert "(no Backlog section recorded in PRD.md)" in prompt
    assert "(no Rules section recorded in PRD.md)" in prompt


def test_start_brainstorm_empty_topic_raises(tmp_path):
    root = _project(tmp_path)
    with pytest.raises(ValueError):
        brainstorm.start_brainstorm(project_dir=root, topic="   ")


def test_start_brainstorm_tracks_session_and_seeds_prompt(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"] = argv
        captured["cwd"] = cwd
        return 5150

    monkeypatch.setattr(launcher, "open_terminal", fake_open)
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 5150)

    result = brainstorm.start_brainstorm(project_dir=root, topic="offline sync", agent="fake")

    assert result.ok and result.slug == "offline-sync"
    assert result.note_path == ".horus/temp/brainstorm-offline-sync.md"
    # The scoped prompt is seeded as the interactive session's initial prompt.
    assert captured["argv"][-1].startswith("Brainstorm session for the demo project.")
    assert "offline sync" in captured["argv"][-1]

    # The session is tracked exactly like any launch — running, real pid.
    recs = Registry.default().all()
    assert len(recs) == 1 and recs[0].status == "running" and recs[0].pid == 5150

    # The write target's parent exists so the session can drop its note.
    assert (root / ".horus" / "temp").is_dir()


def test_start_brainstorm_surfaces_launch_failure(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    result = brainstorm.start_brainstorm(project_dir=root, topic="topic", agent="nope")
    assert not result.ok and "nope" in result.launch.error
    assert Registry.default().all() == []  # nothing tracked on a failed launch


def test_start_brainstorm_uses_shared_launch_path(tmp_path, monkeypatch):
    # The CLI/dashboard twin both funnel through launch.launch_interactive.
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    seen = {}

    def fake_launch(**kwargs):
        seen.update(kwargs)
        return launch.LaunchResult(ok=True, agent=kwargs["agent"], project=kwargs["project_dir"], session_id="sid00001")

    result = brainstorm.start_brainstorm(
        project_dir=root, topic="topic", agent="claude", account=None,
        posture="plan", model="opus", launch_fn=fake_launch,
    )
    assert result.ok
    assert seen["agent"] == "claude" and seen["posture"] == "plan" and seen["model"] == "opus"
    assert seen["prompt"].startswith("Brainstorm session for the demo project.")
