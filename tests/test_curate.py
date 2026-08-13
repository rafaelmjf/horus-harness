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
