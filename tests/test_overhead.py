"""Tests for Horus token overhead estimation."""

import json

from horus import overhead
from horus.cli import main


def _write_jsonl(path, *events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _codex_turn(root):
    return {
        "type": "turn_context",
        "payload": {"cwd": str(root), "workspace_roots": [str(root)]},
    }


def _codex_call(command):
    return {
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "exec_command",
            "arguments": json.dumps({"cmd": command}),
        },
    }


def _codex_tokens(total, input_tokens=0, output_tokens=0):
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total,
                },
                "model_context_window": 100000,
            },
        },
    }


def _claude_event(root, request_id, usage, content):
    return {
        "requestId": request_id,
        "type": "assistant",
        "cwd": str(root),
        "message": {
            "role": "assistant",
            "content": content,
            "usage": usage,
        },
    }


def test_static_footprint_includes_managed_block_and_skills():
    items = overhead.static_footprint()
    names = {item.name for item in items}
    assert "managed instruction block" in names
    assert "horus-consolidate skill" in names
    assert all(item.estimated_tokens > 0 for item in items)


def test_codex_overhead_counts_horus_related_turns(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex"
    rollout = home / "sessions" / "2026" / "06" / "28" / "rollout-test.jsonl"
    _write_jsonl(
        rollout,
        _codex_turn(project),
        _codex_call("python3 -m horus doctor"),
        _codex_tokens(100, input_tokens=80, output_tokens=20),
        _codex_call("uv run pytest -q"),
        _codex_tokens(300, input_tokens=250, output_tokens=50),
    )

    summary = overhead.codex_overhead(project, home=home)
    assert summary.turns == 2
    assert summary.horus_turns == 1
    assert summary.total.total_tokens == 400
    assert summary.horus.total_tokens == 100
    assert summary.horus.input_tokens == 80


def test_claude_overhead_dedupes_request_ids(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "claude"
    log = home / "projects" / "-tmp-project" / "session.jsonl"
    usage = {
        "input_tokens": 10,
        "cache_creation_input_tokens": 20,
        "cache_read_input_tokens": 30,
        "output_tokens": 40,
    }
    _write_jsonl(
        log,
        _claude_event(project, "req-1", usage, [{"type": "tool_use", "name": "Bash", "input": {"command": "horus close --check"}}]),
        _claude_event(project, "req-1", usage, [{"type": "text", "text": "same request rendered as text"}]),
        _claude_event(project, "req-2", {"input_tokens": 5, "output_tokens": 5}, [{"type": "text", "text": "normal work"}]),
    )

    summary = overhead.claude_overhead(project, home=home)
    assert summary.turns == 2
    assert summary.horus_turns == 1
    assert summary.total.total_tokens == 110
    assert summary.horus.total_tokens == 100


def test_overhead_cli_reports_both_agents(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    codex_home = tmp_path / "codex"
    claude_home = tmp_path / "claude"
    _write_jsonl(
        codex_home / "sessions" / "2026" / "06" / "28" / "rollout-test.jsonl",
        _codex_turn(project),
        _codex_call("horus doctor"),
        _codex_tokens(42),
    )
    _write_jsonl(
        claude_home / "projects" / "-tmp-project" / "session.jsonl",
        _claude_event(project, "req-1", {"input_tokens": 4, "output_tokens": 6}, [{"type": "text", "text": ".horus updated"}]),
    )

    rc = main([
        "overhead",
        "--path",
        str(project),
        "--codex-home",
        str(codex_home),
        "--claude-home",
        str(claude_home),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Static prompt footprint" in out
    assert "codex: 1/1 Horus-related turns" in out
    assert "claude: 1/1 Horus-related turns" in out
