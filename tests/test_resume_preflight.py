"""Focused tests for the one-verb resume preflight projection."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from horus import cli, resume_preflight
from horus.continuity import Finding
from horus.datums import Datum
from horus.registry import Registry, SessionRecord


def _prd(root: Path, *, name: str = "demo") -> Path:
    hdir = root / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "sessions").mkdir()
    (hdir / "PRD.md").write_text(
        "---\n"
        "status: active\n"
        "current_focus: Focus now\n"
        "next_action: Do next\n"
        "next_prompt: Resume the card\n"
        "execution_recommendation: continue-as-is\n"
        "last_updated: 2026-07-14\n"
        "horus_min_version: 0.0.26\n"
        "---\n\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return root


def _git_state(**overrides):
    state = {
        "branch": "feature/x",
        "upstream": "origin/feature/x",
        "ahead": 2,
        "behind": 1,
        "dirty": True,
        "own_upstream_gone": False,
        "detached": False,
        "fetch_status": "ok",
        "default_branch": "main",
        "default_ahead": 2,
        "default_behind": 1,
    }
    state.update(overrides)
    return state


def _patch_machine(monkeypatch, *, datums=(), sessions=()):
    usage_calls = []

    def usage(*args, **kwargs):
        usage_calls.append((args, kwargs))
        return {
            "codex": {"freshness": "stale", "pct_5h": 97.0, "read_at": "then"},
            "claude": {"freshness": "fresh", "pct_5h": 42.0, "read_at": "now"},
        }

    monkeypatch.setattr(
        resume_preflight.datums,
        "capture_usage_snapshot",
        usage,
    )

    class Store:
        def all(self):
            return list(datums)

    class Reg:
        def snapshot(self):
            return list(sessions)

    monkeypatch.setattr(resume_preflight.datums.DatumStore, "default", lambda: Store())
    monkeypatch.setattr(resume_preflight.registry.Registry, "default", lambda: Reg())
    return usage_calls


def test_gather_projects_all_required_signals_and_renders_freshness(tmp_path, monkeypatch):
    root = _prd(tmp_path / "demo")
    monkeypatch.setattr(resume_preflight.fetchcheck, "fetch_and_state", lambda *a, **k: _git_state())
    monkeypatch.setattr(
        resume_preflight.closure,
        "freshness_gate",
        lambda root: [Finding("warn", "frontmatter stale")],
    )
    monkeypatch.setattr(resume_preflight.closure, "checkpoint_gate", lambda root: [])
    usage_calls = _patch_machine(
        monkeypatch,
        datums=[Datum(session_id="datum-open", model="sonnet-5", launched_at="2026-07-14T10:00:00+00:00")],
        sessions=[
            SessionRecord("run-a", "codex", str(root), pid=os.getpid(), status="running"),
            SessionRecord("run-b", "claude", str(root), pid=os.getpid(), status="running"),
        ],
    )

    digest = resume_preflight.gather(
        [root],
        installed="0.0.53",
        now=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
    )

    project = digest["projects"][0]
    assert project["git"] == {
        "available": True,
        "fetch": "ok",
        "branch": "feature/x",
        "upstream": "origin/feature/x",
        "compare_ref": "origin/feature/x",
        "ahead": 2,
        "behind": 1,
        "dirty": True,
        "upstream_gone": False,
        "detached": False,
    }
    assert project["version"] == {"installed": "0.0.53", "floor": "0.0.26", "meets_floor": True}
    assert project["handoff"]["next_prompt"] == "Resume the card"
    assert project["hygiene"] == [{"level": "warn", "message": "frontmatter stale"}]
    assert usage_calls[0][1]["persist_cache"] is False
    assert [item["session_id"] for item in digest["open_datums"]] == ["datum-open"]
    assert digest["collisions"] == [{"project": str(root), "count": 2, "sessions": ["run-a", "run-b"]}]

    rendered = resume_preflight.render_text(digest)
    assert "USAGE codex [STALE] 5h=97%" in rendered
    assert "USAGE claude [FRESH] 5h=42%" in rendered
    assert "HANDOFF demo | focus=Focus now | next=Do next" in rendered
    assert "DATUMS open=1 | datum-op:sonnet-5/pending" in rendered
    assert "SESSIONS running=2" in rendered
    assert "SESSIONS stale=0" in rendered
    assert "COLLISION [WARN]" in rendered


def test_no_fetch_uses_local_refs_and_json_is_tooling_safe(tmp_path, monkeypatch):
    root = _prd(tmp_path / "demo")
    monkeypatch.setattr(resume_preflight.gitstate, "git_state", lambda root: _git_state(fetch_status="ignored"))
    monkeypatch.setattr(resume_preflight.fetchcheck, "fetch_and_state", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(resume_preflight.closure, "freshness_gate", lambda root: [])
    monkeypatch.setattr(resume_preflight.closure, "checkpoint_gate", lambda root: [])
    _patch_machine(monkeypatch)

    digest = resume_preflight.gather([root], installed="0.0.53", do_fetch=False)
    assert digest["fetch"] == "skipped"
    assert digest["projects"][0]["git"]["fetch"] == "skipped"
    assert json.loads(resume_preflight.render_json(digest))["mode"] == "project"


def test_registry_snapshot_projects_stale_without_writing(tmp_path, monkeypatch):
    path = tmp_path / "registry.json"
    reg = Registry(path)
    reg.upsert(SessionRecord("dead", "codex", "/demo", pid=999999, status="running"))
    before = path.read_text(encoding="utf-8")

    projected = reg.snapshot()

    assert projected[0].status == "stale"
    assert path.read_text(encoding="utf-8") == before


def test_cli_fleet_stdout_wires_registered_projects(tmp_path, monkeypatch, capsys):
    first = _prd(tmp_path / "one")
    second = _prd(tmp_path / "two")
    monkeypatch.setattr(cli.config, "load_projects", lambda: [str(first), str(second)])
    seen = {}

    def fake_gather(roots, **kwargs):
        seen["roots"] = list(roots)
        seen.update(kwargs)
        return {"mode": "fleet", "projects": []}

    monkeypatch.setattr(cli.resume_preflight, "gather", fake_gather)
    monkeypatch.setattr(cli.resume_preflight, "render_json", lambda digest: '{"mode":"fleet"}\n')

    assert cli.main(["resume", "--preflight", "--fleet", "--no-fetch", "--stdout"]) == 0
    assert seen["roots"] == [first, second]
    assert seen["do_fetch"] is False and seen["mode"] == "fleet"
    assert json.loads(capsys.readouterr().out) == {"mode": "fleet"}
