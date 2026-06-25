"""Tests for the Claude Code adapter.

parse_event fixtures are real lines captured from `claude -p --output-format
stream-json --verbose` (Claude Code 2.1.191), trimmed for size.
"""

import json
from pathlib import Path

from horus.adapters import ClaudeAdapter, EventType, PermissionPosture, SpawnSpec, get_adapter


def _spec(**kw) -> SpawnSpec:
    base = {"prompt": "do the thing", "project_dir": Path("/proj")}
    base.update(kw)
    return SpawnSpec(**base)


# --- build_command -----------------------------------------------------------

def test_build_command_spawn():
    argv = ClaudeAdapter().build_command(_spec())
    assert argv[:6] == ["claude", "-p", "do the thing", "--output-format", "stream-json", "--verbose"]
    assert "--resume" not in argv
    assert ["--permission-mode", "default"] == [argv[argv.index("--permission-mode")], argv[argv.index("--permission-mode") + 1]]


def test_build_command_resume_and_model_and_tools():
    argv = ClaudeAdapter().build_command(
        _spec(model="haiku", allowed_tools=("Read", "Glob"), disallowed_tools=("Bash",)),
        resume_id="sess-7",
    )
    assert "--resume" in argv and "sess-7" in argv
    assert ["--model", "haiku"] == [argv[argv.index("--model")], argv[argv.index("--model") + 1]]
    assert argv[argv.index("--allowedTools") + 1] == "Read,Glob"
    assert argv[argv.index("--disallowedTools") + 1] == "Bash"


def test_permission_flags_map_every_posture():
    a = ClaudeAdapter()
    assert a.permission_flags(PermissionPosture.PLAN) == ["--permission-mode", "plan"]
    assert a.permission_flags(PermissionPosture.AUTO_EDIT) == ["--permission-mode", "acceptEdits"]
    assert a.permission_flags(PermissionPosture.FULL_AUTO) == ["--permission-mode", "bypassPermissions"]
    for posture in PermissionPosture:  # all covered, none raise
        assert a.permission_flags(posture)


def test_build_env_sets_config_dir_per_account():
    a = ClaudeAdapter(config_dirs={"work": "/home/work/.claude"})
    assert a.build_env(_spec(account="work")) == {"CLAUDE_CONFIG_DIR": str(Path("/home/work/.claude"))}
    assert a.build_env(_spec(account="personal")) == {}  # unmapped -> ambient login
    assert a.build_env(_spec()) == {}


# --- parse_event (real fixtures) ---------------------------------------------

_INIT = '{"type":"system","subtype":"init","cwd":"C:\\\\x","session_id":"abc-123","model":"claude-haiku-4-5-20251001","permissionMode":"default"}'
_THINKING = '{"type":"assistant","message":{"content":[{"type":"thinking","thinking":"hmm"}]},"session_id":"abc-123"}'
_TEXT = '{"type":"assistant","message":{"content":[{"type":"text","text":"PONG"}]},"session_id":"abc-123"}'
_RATE = '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed"},"session_id":"abc-123"}'
_RESULT = '{"type":"result","subtype":"success","is_error":false,"result":"PONG","session_id":"abc-123"}'


def test_parse_init_is_session_started():
    evs = ClaudeAdapter().parse_event(_INIT)
    assert len(evs) == 1 and evs[0].type is EventType.SESSION_STARTED and evs[0].session_id == "abc-123"


def test_parse_text_and_thinking():
    assert ClaudeAdapter().parse_event(_THINKING) == []  # thinking is not surfaced
    evs = ClaudeAdapter().parse_event(_TEXT)
    assert [e.type for e in evs] == [EventType.ASSISTANT_TEXT]
    assert evs[0].text == "PONG" and evs[0].session_id == "abc-123"


def test_parse_assistant_multiple_blocks_yields_multiple_events():
    line = json.dumps({
        "type": "assistant",
        "session_id": "abc-123",
        "message": {"content": [
            {"type": "text", "text": "running it"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
        ]},
    })
    evs = ClaudeAdapter().parse_event(line)
    assert [e.type for e in evs] == [EventType.ASSISTANT_TEXT, EventType.TOOL_USE]
    assert evs[1].tool == "Bash"


def test_parse_tool_result_from_user_message():
    line = json.dumps({
        "type": "user", "session_id": "abc-123",
        "message": {"content": [{"type": "tool_result", "is_error": False, "content": "ok"}]},
    })
    evs = ClaudeAdapter().parse_event(line)
    assert [e.type for e in evs] == [EventType.TOOL_RESULT]


def test_parse_result_and_noise():
    evs = ClaudeAdapter().parse_event(_RESULT)
    assert evs[0].type is EventType.RESULT and evs[0].text == "PONG" and evs[0].is_error is False
    assert ClaudeAdapter().parse_event(_RATE) == []     # rate_limit_event ignored
    assert ClaudeAdapter().parse_event("   ") == []
    assert ClaudeAdapter().parse_event("not json")[0].type is EventType.RAW


def test_get_adapter_resolves_claude():
    assert isinstance(get_adapter("claude"), ClaudeAdapter)
