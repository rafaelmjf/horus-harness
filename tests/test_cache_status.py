"""Tests for prompt-cache freshness estimates."""

import json
from datetime import datetime, timezone

from horus import cache_status


def _write_jsonl(path, *events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_codex_cache_status_reads_latest_project_turn(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex"
    rollout = home / "sessions" / "2026" / "06" / "29" / "rollout-test.jsonl"
    _write_jsonl(
        rollout,
        {
            "timestamp": "2026-06-29T10:00:00Z",
            "type": "turn_context",
            "payload": {"cwd": str(project), "workspace_roots": [str(project)]},
        },
        {
            "timestamp": "2026-06-29T10:01:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 80,
                        "output_tokens": 20,
                        "total_tokens": 200,
                    },
                    "model_context_window": 1000,
                },
            },
        },
    )

    status = cache_status.latest_codex_cache_status(project, home=home)
    assert status is not None
    assert status.agent == "codex"
    assert status.cached_input_tokens == 80
    assert status.total_tokens == 200
    assert status.state(now=datetime(2026, 6, 29, 10, 2, tzinfo=timezone.utc)) == "warm"
    assert status.state(now=datetime(2026, 6, 29, 10, 10, tzinfo=timezone.utc)) == "cold-risk"
    assert status.state(now=datetime(2026, 6, 29, 11, 2, tzinfo=timezone.utc)) == "expired"


def test_claude_cache_status_reads_cache_creation_and_read(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "claude"
    log = home / "projects" / "-tmp-project" / "session.jsonl"
    _write_jsonl(
        log,
        {
            "timestamp": "2026-06-29T10:01:00Z",
            "requestId": "req-1",
            "type": "assistant",
            "cwd": str(project),
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {
                    "input_tokens": 10,
                    "cache_creation_input_tokens": 20,
                    "cache_read_input_tokens": 30,
                    "output_tokens": 5,
                },
            },
        },
    )

    status = cache_status.latest_claude_cache_status(project, home=home)
    assert status is not None
    assert status.agent == "claude"
    assert status.cache_creation_input_tokens == 20
    assert status.cache_read_input_tokens == 30
    assert status.cache_tokens == 50
    assert status.total_tokens == 65
