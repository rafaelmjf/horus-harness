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


_STRUCTURED = ('{"desc":"A test project.","sessions":{"s1":{"context":"did CURATED_CTX",'
               '"segments":[{"title":"main","text":"built it"}],"discussed":[],"decided":[],'
               '"shipped":["shipped it"],"left_open":[]}}}')


def test_interpret_writes_structured_json_and_records_state(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_runner(prompt, *, model, account=None, cwd=None):
        calls.append(prompt)
        return "Here is the summary:\n```json\n" + _STRUCTURED + "\n```\nHope that helps!"

    outcome = curate.interpret(out, manifest=manifest, runner=fake_runner)
    assert len(outcome["curated"]) == 1 and not outcome["errors"]
    slug = outcome["curated"][0]
    data = json.loads((out / "curation" / f"{slug}.json").read_text(encoding="utf-8"))
    assert data["desc"] == "A test project."
    assert data["sessions"]["s1"]["context"] == "did CURATED_CTX"
    # Whole prompt rides on stdin: bundle wrapped as DATA, instruction (with ids) last.
    assert "build the thing" in calls[0]
    assert calls[0].index("build the thing") < calls[0].index("Session ids: s1")


def test_interpret_skips_unchanged_but_reruns_on_force(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)
    runs = {"n": 0}

    def fake_runner(prompt, *, model, account=None, cwd=None):
        runs["n"] += 1
        return _STRUCTURED

    curate.interpret(out, manifest=manifest, runner=fake_runner)
    second = curate.interpret(out, manifest=manifest, runner=fake_runner)
    assert second["skipped"] and not second["curated"]  # watermark skip
    assert runs["n"] == 1

    forced = curate.interpret(out, manifest=manifest, runner=fake_runner, force=True)
    assert forced["curated"] and runs["n"] == 2


def test_interpret_records_runner_errors_without_crashing(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)

    def boom(prompt, *, model, account=None, cwd=None):
        raise RuntimeError("cli not authenticated")

    outcome = curate.interpret(out, manifest=manifest, runner=boom)
    assert outcome["errors"] and not outcome["curated"]
    assert "cli not authenticated" in outcome["errors"][0]


def test_parse_model_json_tolerates_prose_and_fences():
    # leading prose + fence
    assert curate._parse_model_json('Sure!\n```json\n{"a":1}\n```')["a"] == 1
    # trailing prose after a valid object (the pbi-ecosystem failure)
    assert curate._parse_model_json('{"a":{"b":2}}\nHope that helps!')["a"]["b"] == 2
    # braces inside strings don't fool the matcher
    assert curate._parse_model_json('{"a":"has } brace"}')["a"] == "has } brace"


def test_interpret_records_malformed_json_as_error(tmp_path, monkeypatch):
    out, manifest = _capture_one(tmp_path, monkeypatch)
    outcome = curate.interpret(
        out, manifest=manifest,
        runner=lambda p, *, model, account=None, cwd=None: "not json at all")
    assert outcome["errors"] and not outcome["curated"]


# --- Phase 3: portfolio git-of-record + local view --------------------------

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
                     runner=lambda p, *, model, account=None, cwd=None: _STRUCTURED)
    return out, manifest


def test_portfolio_repo_has_no_raw_turn_text(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"
    curate.assemble_portfolio(out, portfolio, manifest=manifest)

    # The repo carries curation + skeleton; the raw turn text never enters it.
    blob = "\n".join(p.read_text(encoding="utf-8") for p in portfolio.rglob("*")
                     if p.is_file() and p.suffix in {".md", ".json"})
    assert "CURATED_CTX" in blob
    assert "SENTINEL_RAW_TURN" not in blob
    # No HTML is committed to the repo — the rich view is local only.
    assert not list(portfolio.rglob("*.html"))


def test_portfolio_is_a_git_repo_and_regeneratable(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"

    first = curate.assemble_portfolio(out, portfolio, manifest=manifest)
    assert (portfolio / ".git").is_dir()
    assert first["git"] == "committed"
    slug = sorted(manifest["projects"])[0]
    assert (portfolio / "projects" / slug / "curation.json").exists()
    assert (portfolio / "projects" / slug / "skeleton.json").exists()

    import shutil
    shutil.rmtree(portfolio / "projects")
    (portfolio / "index.md").unlink()
    curate.assemble_portfolio(out, portfolio, manifest=manifest)
    assert (portfolio / "projects" / slug / "curation.json").exists()
    assert f"[{manifest['projects'][slug]['name']}]" in (portfolio / "index.md").read_text(encoding="utf-8")


def test_local_view_is_real_design_with_raw_drilldown(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"
    outcome = curate.assemble_portfolio(out, portfolio, manifest=manifest)

    view = Path(outcome["view"]).read_text(encoding="utf-8")
    assert "Session Portfolio" in view            # the real title
    assert "const DATA=" in view and "RAW=" in view
    assert "did CURATED_CTX" in view              # structured curation embedded
    assert "SENTINEL_RAW_TURN" in view            # raw drill-down IS embedded — local only
    assert 'src="http' not in view and 'href="http' not in view  # self-contained, no network


def test_render_view_without_raw_omits_transcripts(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    html = curate.render_real_view(manifest, out, include_raw=False)
    assert "did CURATED_CTX" in html              # curation still present
    assert "SENTINEL_RAW_TURN" not in html        # raw omitted when include_raw=False


def test_account_label_maps_to_four_slots():
    assert curate.account_label("codex-ambient") == "codex"
    assert curate.account_label("claude-claude-personal") == "personal"
    assert curate.account_label("claude-claude-work") == "work"
    assert curate.account_label("claude-ambient") == "shared"


def test_portfolio_push_without_remote_reports_how_to_set_one(tmp_path, monkeypatch):
    out, manifest = _capture_and_curate(tmp_path, monkeypatch)
    portfolio = tmp_path / "portfolio"
    outcome = curate.assemble_portfolio(out, portfolio, manifest=manifest, push=True)
    assert outcome["pushed"] is False
    assert "origin" in outcome["push_error"]
