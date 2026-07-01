"""Tests for read-only session discovery (Claude + Codex transcripts)."""

import json

from horus import session_discovery


def _write_jsonl(path, *events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _claude_event(cwd, event_type, ts, session_id="sess-1"):
    return {
        "timestamp": ts,
        "sessionId": session_id,
        "type": event_type,
        "cwd": cwd,
        "message": {"role": event_type, "content": [{"type": "text", "text": "hi"}]},
    }


def test_discover_claude_sessions_happy_path(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "claude"
    log = home / "projects" / "-tmp-project" / "abc-uuid.jsonl"
    _write_jsonl(
        log,
        _claude_event(str(project), "user", "2026-06-29T10:00:00Z"),
        _claude_event(str(project), "assistant", "2026-06-29T10:01:00Z"),
        _claude_event(str(project), "assistant", "2026-06-29T10:05:00Z"),
    )

    sessions = session_discovery.discover_claude_sessions(project, claude_dir=home)
    assert len(sessions) == 1
    s = sessions[0]
    assert s.agent == "claude"
    assert s.session_id == "abc-uuid"
    assert s.message_count == 3
    assert s.started_at == "2026-06-29T10:00:00Z"
    assert s.last_activity == "2026-06-29T10:05:00Z"
    assert s.source_path == log


def test_discover_claude_sessions_ignores_other_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    home = tmp_path / "claude"
    log = home / "projects" / "-tmp-other" / "xyz.jsonl"
    _write_jsonl(log, _claude_event(str(other), "user", "2026-06-29T10:00:00Z"))

    assert session_discovery.discover_claude_sessions(project, claude_dir=home) == []


def test_discover_claude_sessions_skips_malformed_lines(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "claude"
    log = home / "projects" / "-tmp-project" / "abc.jsonl"
    log.parent.mkdir(parents=True)
    good = _claude_event(str(project), "user", "2026-06-29T10:00:00Z")
    log.write_text(
        "not json at all\n" + json.dumps(good) + "\n" + "{broken\n" + "\n",
        encoding="utf-8",
    )

    sessions = session_discovery.discover_claude_sessions(project, claude_dir=home)
    assert len(sessions) == 1
    assert sessions[0].message_count == 1


def test_discover_claude_sessions_missing_dir_returns_empty(tmp_path):
    assert session_discovery.discover_claude_sessions(tmp_path, claude_dir=tmp_path / "missing") == []


def _codex_meta(cwd, session_id, ts):
    return {
        "timestamp": ts,
        "type": "session_meta",
        "payload": {"session_id": session_id, "id": session_id, "cwd": cwd},
    }


def _codex_msg(kind, ts):
    return {
        "timestamp": ts,
        "type": "event_msg",
        "payload": {"type": kind, "message": "hello"},
    }


def test_discover_codex_sessions_happy_path(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex"
    rollout = home / "sessions" / "2026" / "06" / "29" / "rollout-test.jsonl"
    _write_jsonl(
        rollout,
        _codex_meta(str(project), "sess-codex-1", "2026-06-29T09:00:00Z"),
        _codex_msg("user_message", "2026-06-29T09:00:01Z"),
        _codex_msg("agent_message", "2026-06-29T09:00:05Z"),
        _codex_msg("agent_message", "2026-06-29T09:00:09Z"),
    )

    sessions = session_discovery.discover_codex_sessions(project, codex_home=home)
    assert len(sessions) == 1
    s = sessions[0]
    assert s.agent == "codex"
    assert s.session_id == "sess-codex-1"
    assert s.message_count == 3
    assert s.started_at == "2026-06-29T09:00:01Z"
    assert s.last_activity == "2026-06-29T09:00:09Z"
    assert s.source_path == rollout


def test_discover_codex_sessions_ignores_other_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    home = tmp_path / "codex"
    rollout = home / "sessions" / "2026" / "06" / "29" / "rollout-test.jsonl"
    _write_jsonl(
        rollout,
        _codex_meta(str(other), "sess-codex-2", "2026-06-29T09:00:00Z"),
        _codex_msg("user_message", "2026-06-29T09:00:01Z"),
    )

    assert session_discovery.discover_codex_sessions(project, codex_home=home) == []


def test_discover_codex_sessions_skips_malformed_lines(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "codex"
    rollout = home / "sessions" / "2026" / "06" / "29" / "rollout-test.jsonl"
    rollout.parent.mkdir(parents=True)
    good = [
        _codex_meta(str(project), "sess-codex-3", "2026-06-29T09:00:00Z"),
        _codex_msg("user_message", "2026-06-29T09:00:01Z"),
    ]
    rollout.write_text(
        "garbage\n" + "\n".join(json.dumps(e) for e in good) + "\n" + "{oops\n",
        encoding="utf-8",
    )

    sessions = session_discovery.discover_codex_sessions(project, codex_home=home)
    assert len(sessions) == 1
    assert sessions[0].message_count == 1


def test_discover_codex_sessions_missing_dir_returns_empty(tmp_path):
    assert session_discovery.discover_codex_sessions(tmp_path, codex_home=tmp_path / "missing") == []


def test_discover_sessions_combines_and_sorts_by_last_activity(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    claude_home = tmp_path / "claude"
    codex_home = tmp_path / "codex"

    claude_log = claude_home / "projects" / "-tmp-project" / "claude-uuid.jsonl"
    _write_jsonl(
        claude_log,
        _claude_event(str(project), "user", "2026-06-29T08:00:00Z"),
        _claude_event(str(project), "assistant", "2026-06-29T08:01:00Z"),
    )

    rollout = codex_home / "sessions" / "2026" / "06" / "29" / "rollout-test.jsonl"
    _write_jsonl(
        rollout,
        _codex_meta(str(project), "sess-codex-4", "2026-06-29T09:00:00Z"),
        _codex_msg("user_message", "2026-06-29T09:00:01Z"),
        _codex_msg("agent_message", "2026-06-29T10:00:00Z"),
    )

    sessions = session_discovery.discover_sessions(project, claude_dir=claude_home, codex_home=codex_home)
    assert [s.agent for s in sessions] == ["codex", "claude"]
    assert sessions[0].last_activity == "2026-06-29T10:00:00Z"
    assert sessions[1].last_activity == "2026-06-29T08:01:00Z"


def test_discover_sessions_empty_when_both_missing(tmp_path):
    assert (
        session_discovery.discover_sessions(
            tmp_path, claude_dir=tmp_path / "no-claude", codex_home=tmp_path / "no-codex"
        )
        == []
    )
