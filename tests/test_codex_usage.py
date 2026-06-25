"""Tests for read-only Codex rollout usage signals."""

import json

from horus import codex_usage


def _write_rollout(home, *events):
    path = home / "sessions" / "2026" / "06" / "25" / "rollout-test.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def _turn(root):
    return {
        "timestamp": "2026-06-25T10:00:00Z",
        "type": "turn_context",
        "payload": {"cwd": str(root), "workspace_roots": [str(root)]},
    }


def _token(ts, total, window=1000, primary=12, secondary=34):
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "last_token_usage": {"total_tokens": total},
                "model_context_window": window,
            },
            "rate_limits": {
                "primary": {"used_percent": primary, "resets_at": 1782390000},
                "secondary": {"used_percent": secondary, "resets_at": 1782990000},
            },
        },
    }


def test_latest_usage_reads_matching_project_rollout(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(
        home,
        _turn(other),
        _token("2026-06-25T10:01:00Z", 990),
        _turn(project),
        _token("2026-06-25T10:02:00Z", 875, window=1000),
    )

    report = codex_usage.latest_usage(project, home=home)
    assert report is not None
    assert report.context_percent == 87.5
    assert report.primary_percent == 12


def test_usage_findings_warns_at_threshold(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex-home"
    _write_rollout(home, _turn(project), _token("2026-06-25T10:02:00Z", 910, window=1000))

    findings = codex_usage.usage_findings(project, threshold=90, home=home)
    assert findings[0].level == "warn"
    assert "Codex context 91.0%" in findings[0].message
    assert "closure ritual" in findings[0].message


def test_usage_findings_ok_when_absent(tmp_path):
    findings = codex_usage.usage_findings(tmp_path, home=tmp_path / "missing")
    assert findings[0].level == "ok"
    assert "no Codex usage signal" in findings[0].message
