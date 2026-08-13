"""Phase-1 deterministic capture: redaction scan, attribution self-flags, watermark."""

from __future__ import annotations

import json
from pathlib import Path

from horus import config, curate


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _fake_home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "home"
    monkeypatch.setattr(config, "config_dir", lambda: home / ".horus")
    return home


def test_redact_counts_and_masks():
    text, hits = curate.redact("token ntn_ABCDEFGHIJKLMNOPQRSTUV and pass secret=hunter2xy")
    assert hits >= 1
    assert "ntn_" not in text
    assert "[REDACTED" in text


def test_curate_redacts_secret_in_bundle(tmp_path, monkeypatch):
    home = _fake_home(tmp_path, monkeypatch)
    # A Claude session whose text carries a Notion token — the PoC's real finding.
    _write_jsonl(
        home / ".claude" / "projects" / "C--proj" / "s1.jsonl",
        [
            {"type": "user", "sessionId": "s1", "cwd": str(tmp_path / "gone"),
             "timestamp": "2026-08-13T10:00:00Z",
             "message": {"role": "user", "content": "here is ntn_ABCDEFGHIJKLMNOPQRSTUV please rotate"}},
            {"type": "assistant", "timestamp": "2026-08-13T10:01:00Z",
             "message": {"role": "assistant", "content": "rotated"}},
        ],
    )
    out = tmp_path / "out"
    manifest = curate.curate(out, home=home)

    assert manifest["projects_found"] == 1
    assert manifest["secrets_redacted"] >= 1
    bundle = next((out / "bundles").glob("*.txt")).read_text(encoding="utf-8")
    assert "ntn_" not in bundle
    assert "[REDACTED_NOTION_TOKEN]" in bundle


def test_attribution_flags_moved_checkout_and_non_project(tmp_path, monkeypatch):
    home = _fake_home(tmp_path, monkeypatch)
    _write_jsonl(
        home / ".claude" / "projects" / "C--gone" / "s2.jsonl",
        [{"type": "user", "sessionId": "s2", "cwd": str(tmp_path / "does-not-exist"),
          "timestamp": "2026-08-13T10:00:00Z",
          "message": {"role": "user", "content": "work here"}}],
    )
    manifest = curate.curate(tmp_path / "out", home=home)
    flags = [f for p in manifest["projects"].values() for f in p["attribution_flags"]]
    assert any("moved/deleted checkout" in f for f in flags)
    assert any("no git remote" in f for f in flags)


def test_watermark_marks_changed_then_unchanged(tmp_path, monkeypatch):
    home = _fake_home(tmp_path, monkeypatch)
    sess = home / ".codex" / "sessions" / "2026" / "08" / "13" / "rollout-x.jsonl"
    _write_jsonl(
        sess,
        [
            {"type": "session_meta", "payload": {"id": "cx1", "cwd": str(tmp_path / "repo"),
             "git": {"branch": "main"}}},
            {"type": "response_item", "timestamp": "2026-08-13T09:00:00Z",
             "payload": {"type": "message", "role": "user",
                         "content": [{"type": "input_text", "text": "first pass"}]}},
        ],
    )
    out = tmp_path / "out"

    first = curate.curate(out, home=home)
    s = first["projects"]["repo"]["sessions"][0]
    assert s["content_hash"]
    assert s["changed"] is True  # no prior manifest → everything is new

    second = curate.curate(out, home=home)  # same content, prior manifest exists now
    assert second["projects"]["repo"]["sessions"][0]["changed"] is False

    # Append a turn → content changes → watermark flips back to changed.
    with sess.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "response_item", "timestamp": "2026-08-13T09:05:00Z",
                                 "payload": {"type": "message", "role": "assistant",
                                             "content": [{"type": "output_text", "text": "second"}]}}) + "\n")
    third = curate.curate(out, home=home)
    assert third["projects"]["repo"]["sessions"][0]["changed"] is True


# --- Phase 2: interpretation (stubbed runner — no tokens spent) --------------

def _capture_one(tmp_path, monkeypatch) -> tuple[Path, dict]:
    home = _fake_home(tmp_path, monkeypatch)
    _write_jsonl(
        home / ".claude" / "projects" / "C--proj" / "s1.jsonl",
        [{"type": "user", "sessionId": "s1", "cwd": str(tmp_path / "gone"),
          "gitBranch": "main", "timestamp": "2026-08-13T10:00:00Z",
          "message": {"role": "user", "content": "build the thing"}}],
    )
    out = tmp_path / "out"
    return out, curate.curate(out, home=home)


def test_interpret_writes_curation_and_records_state(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_runner(prompt, *, model, account=None):
        calls.append(prompt)
        return "## Context\nA test project.\n"

    outcome = curate.interpret(out, manifest=manifest, runner=fake_runner)
    assert len(outcome["curated"]) == 1 and not outcome["errors"]
    slug = outcome["curated"][0]
    assert (out / "curation" / f"{slug}.md").read_text(encoding="utf-8").startswith("## Context")
    # The bundle content reached the model.
    assert "build the thing" in calls[0]


def test_interpret_skips_unchanged_but_reruns_on_force(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)
    runs = {"n": 0}

    def fake_runner(prompt, *, model, account=None):
        runs["n"] += 1
        return "## Context\nx\n"

    curate.interpret(out, manifest=manifest, runner=fake_runner)
    second = curate.interpret(out, manifest=manifest, runner=fake_runner)
    assert second["skipped"] and not second["curated"]  # watermark skip
    assert runs["n"] == 1

    forced = curate.interpret(out, manifest=manifest, runner=fake_runner, force=True)
    assert forced["curated"] and runs["n"] == 2


def test_interpret_records_runner_errors_without_crashing(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)

    def boom(prompt, *, model, account=None):
        raise RuntimeError("cli not authenticated")

    outcome = curate.interpret(out, manifest=manifest, runner=boom)
    assert outcome["errors"] and not outcome["curated"]
    assert "cli not authenticated" in outcome["errors"][0]


# --- Phase 3: portfolio git-of-record ---------------------------------------

def _capture_and_curate(tmp_path, monkeypatch) -> tuple[Path, dict]:
    home = _fake_home(tmp_path, monkeypatch)
    _write_jsonl(
        home / ".claude" / "projects" / "C--proj" / "s1.jsonl",
        [{"type": "user", "sessionId": "s1", "cwd": str(tmp_path / "gone"),
          "gitBranch": "main", "timestamp": "2026-08-13T10:00:00Z",
          "message": {"role": "user", "content": "SENTINEL_RAW_TURN build it"}}],
    )
    out = tmp_path / "out"
    manifest = curate.curate(out, home=home)
    curate.interpret(out, manifest=manifest,
                     runner=lambda p, *, model, account=None: "## Context\ncurated summary\n")
    return out, manifest


def test_portfolio_has_no_raw_turn_text(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"
    curate.assemble_portfolio(out, portfolio, manifest=manifest)

    # The curated summary is present; the raw turn text never is.
    blob = "\n".join(p.read_text(encoding="utf-8") for p in portfolio.rglob("*")
                     if p.is_file() and p.suffix in {".md", ".json", ".html"})
    assert "curated summary" in blob
    assert "SENTINEL_RAW_TURN" not in blob


def test_portfolio_is_a_git_repo_and_regeneratable(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"

    first = curate.assemble_portfolio(out, portfolio, manifest=manifest)
    assert (portfolio / ".git").is_dir()
    assert first["git"] == "committed"
    slug = sorted(manifest["projects"])[0]
    index_before = (portfolio / "index.md").read_text(encoding="utf-8")
    assert (portfolio / "projects" / slug / "curation.md").exists()
    assert (portfolio / "projects" / slug / "skeleton.json").exists()

    # Delete-tomorrow: wipe content, regenerate, same project files come back.
    import shutil
    shutil.rmtree(portfolio / "projects")
    (portfolio / "index.md").unlink()
    curate.assemble_portfolio(out, portfolio, manifest=manifest)
    assert (portfolio / "projects" / slug / "curation.md").exists()
    # index differs only by timestamp line — the table content is stable.
    assert f"[{manifest['projects'][slug]['name']}]" in (portfolio / "index.md").read_text(encoding="utf-8")


def test_portfolio_push_without_remote_reports_how_to_set_one(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"
    outcome = curate.assemble_portfolio(out, portfolio, manifest=manifest, push=True)
    assert outcome["pushed"] is False
    assert "origin" in outcome["push_error"]
