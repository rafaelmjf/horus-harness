"""Tests for the Codex adapter.

parse_event fixtures are real JSONL lines captured from ``codex exec --json``
(probed live on this machine during adapter development).
"""

import json
from pathlib import Path

import pytest

from horus import config
from horus.adapters import CodexAdapter, EventType, PermissionPosture, SpawnSpec, get_adapter


def _spec(**kw) -> SpawnSpec:
    base = {"prompt": "do the thing", "project_dir": Path("/proj")}
    base.update(kw)
    return SpawnSpec(**base)


# --- build_command -----------------------------------------------------------

def test_build_command_spawn_structure():
    argv = CodexAdapter().build_command(_spec())
    # codex exec --json [FLAGS] <prompt>
    assert argv[:3] == ["codex", "exec", "--json"]
    assert argv[-1] == "do the thing"   # prompt is the last positional
    assert "exec" not in argv[3:]        # no nested "resume"


def test_build_command_spawn_model():
    argv = CodexAdapter().build_command(_spec(model="o4-mini"))
    assert ["-m", "o4-mini"] == [argv[argv.index("-m")], argv[argv.index("-m") + 1]]


def test_build_command_spawn_permission_flags():
    plan = CodexAdapter().build_command(_spec(posture=PermissionPosture.PLAN))
    assert "--sandbox" in plan and "read-only" in plan

    auto = CodexAdapter().build_command(_spec(posture=PermissionPosture.FULL_AUTO))
    assert "--dangerously-bypass-approvals-and-sandbox" in auto
    assert "--sandbox" not in auto

    default = CodexAdapter().build_command(_spec(posture=PermissionPosture.DEFAULT))
    assert "--sandbox" not in default
    assert "--dangerously-bypass-approvals-and-sandbox" not in default


def test_build_command_resume_structure():
    argv = CodexAdapter().build_command(_spec(prompt="continue"), resume_id="thread-uuid")
    # codex exec resume --json [FLAGS] <session_id> [prompt]
    assert argv[:4] == ["codex", "exec", "resume", "--json"]
    assert "thread-uuid" in argv
    assert "continue" == argv[-1]
    # prompt after session id
    assert argv.index("thread-uuid") < argv.index("continue")


def test_build_command_resume_no_sandbox_flag():
    # exec resume does not accept --sandbox; only full bypass is forwarded.
    argv = CodexAdapter().build_command(_spec(posture=PermissionPosture.AUTO_EDIT), resume_id="x")
    assert "--sandbox" not in argv

    full = CodexAdapter().build_command(_spec(posture=PermissionPosture.FULL_AUTO), resume_id="x")
    assert "--dangerously-bypass-approvals-and-sandbox" in full


def test_build_command_effort_flag_spawn():
    # Codex has no dedicated --effort flag (probed via `codex exec --help`); the
    # documented mechanism is the generic config override, confirmed live against
    # this machine's own ~/.codex/config.toml (`model_reasoning_effort = "high"`).
    argv = CodexAdapter().build_command(_spec(effort="high"))
    assert "-c" in argv
    assert "model_reasoning_effort=high" == argv[argv.index("-c") + 1]


def test_build_command_effort_flag_resume():
    argv = CodexAdapter().build_command(_spec(effort="low"), resume_id="thread-uuid")
    assert "-c" in argv
    assert "model_reasoning_effort=low" == argv[argv.index("-c") + 1]


def test_build_command_no_effort_flag_by_default():
    # Default behavior unchanged when --effort is omitted.
    assert "-c" not in CodexAdapter().build_command(_spec())
    assert "-c" not in CodexAdapter().build_command(_spec(), resume_id="thread-uuid")


def test_build_command_resume_empty_prompt_not_appended():
    argv = CodexAdapter().build_command(_spec(prompt=""), resume_id="x")
    # Empty prompt should not be appended; session id is the last arg.
    assert argv[-1] == "x"


# --- permission_flags (pure) -------------------------------------------------

def test_permission_flags_cover_every_posture():
    a = CodexAdapter()
    assert a.permission_flags(PermissionPosture.PLAN) == ["--sandbox", "read-only"]
    assert a.permission_flags(PermissionPosture.READ_ONLY) == ["--sandbox", "read-only"]
    assert a.permission_flags(PermissionPosture.DEFAULT) == []
    assert a.permission_flags(PermissionPosture.AUTO_EDIT) == ["--sandbox", "workspace-write"]
    assert a.permission_flags(PermissionPosture.FULL_AUTO) == ["--dangerously-bypass-approvals-and-sandbox"]


# --- build_env ---------------------------------------------------------------

def test_build_env_sets_codex_home_per_account():
    a = CodexAdapter(codex_homes={"work": "/home/work/.codex"})
    assert a.build_env(_spec(account="work")) == {"CODEX_HOME": str(Path("/home/work/.codex"))}
    assert a.build_env(_spec(account="personal")) == {}   # unmapped → ambient login
    assert a.build_env(_spec()) == {}


# --- interactive_command -----------------------------------------------------

def test_interactive_command_no_exec_subcommand():
    argv = CodexAdapter().interactive_command(_spec(model="o3"), session_id="uuid-1")
    assert argv[0] == "codex"
    assert "exec" not in argv        # interactive TUI, not exec
    assert "--json" not in argv      # no JSON output in TUI mode
    assert ["-m", "o3"] == [argv[argv.index("-m")], argv[argv.index("-m") + 1]]


def test_interactive_command_session_id_accepted_but_not_forwarded():
    # session_id is Horus's internal tracking id; Codex has no --session-id flag.
    argv = CodexAdapter().interactive_command(_spec(), session_id="horus-track-id")
    assert "horus-track-id" not in argv


def test_interactive_command_prompt_seeded():
    argv = CodexAdapter().interactive_command(_spec(prompt="resume the project"), session_id="s1")
    assert argv[-1] == "resume the project"

    fresh = CodexAdapter().interactive_command(_spec(prompt=""), session_id="s1")
    assert "resume the project" not in fresh


def test_interactive_command_carries_effort_flag():
    # The TUI's attended launch path needs the reasoning-effort override too,
    # not just headless `codex exec` runs.
    argv = CodexAdapter().interactive_command(_spec(effort="high"), session_id="s1")
    assert "-c" in argv
    assert "model_reasoning_effort=high" == argv[argv.index("-c") + 1]
    assert "-c" not in CodexAdapter().interactive_command(_spec(), session_id="s1")


def test_known_models_are_the_gpt_family_roster():
    # The TUI's per-account model picker reads this directly — never a list of
    # its own — and it must stay disjoint from Claude's family aliases so a
    # codex account never offers a claude model.
    assert CodexAdapter.KNOWN_MODELS == ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5")


def test_interactive_command_full_auto_bypasses():
    argv = CodexAdapter().interactive_command(
        _spec(posture=PermissionPosture.FULL_AUTO), session_id="s1"
    )
    assert "--dangerously-bypass-approvals-and-sandbox" in argv

    # Other postures don't add bypass in interactive mode.
    default_argv = CodexAdapter().interactive_command(_spec(), session_id="s1")
    assert "--dangerously-bypass-approvals-and-sandbox" not in default_argv


# --- parse_event (real fixtures) ---------------------------------------------

# Captured from `codex exec --json --skip-git-repo-check "Say hello in one word."`
_THREAD_STARTED = '{"type":"thread.started","thread_id":"019f047f-5ca5-7903-bb7f-8b123ab0c75b"}'
_TURN_STARTED = '{"type":"turn.started"}'
_ITEM_MSG = '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Hello"}}'
_TURN_COMPLETED = '{"type":"turn.completed","usage":{"input_tokens":13764,"cached_input_tokens":10112,"output_tokens":5,"reasoning_output_tokens":0}}'


def test_parse_thread_started_is_session_started():
    evs = CodexAdapter().parse_event(_THREAD_STARTED)
    assert len(evs) == 1
    assert evs[0].type is EventType.SESSION_STARTED
    assert evs[0].session_id == "019f047f-5ca5-7903-bb7f-8b123ab0c75b"


def test_parse_turn_started_is_ignored():
    assert CodexAdapter().parse_event(_TURN_STARTED) == []


def test_parse_agent_message_is_assistant_text():
    evs = CodexAdapter().parse_event(_ITEM_MSG)
    assert len(evs) == 1
    assert evs[0].type is EventType.ASSISTANT_TEXT
    assert evs[0].text == "Hello"


def test_parse_turn_completed_is_result():
    evs = CodexAdapter().parse_event(_TURN_COMPLETED)
    assert len(evs) == 1
    assert evs[0].type is EventType.RESULT


def test_parse_tool_call_item():
    line = json.dumps({
        "type": "item.completed",
        "item": {"id": "item_1", "type": "tool_call", "name": "shell", "arguments": "ls"},
    })
    evs = CodexAdapter().parse_event(line)
    assert len(evs) == 1
    assert evs[0].type is EventType.TOOL_USE
    assert evs[0].tool == "shell"


def test_parse_tool_output_item():
    line = json.dumps({
        "type": "item.completed",
        "item": {"id": "item_2", "type": "tool_output", "output": "file.txt\n"},
    })
    evs = CodexAdapter().parse_event(line)
    assert len(evs) == 1
    assert evs[0].type is EventType.TOOL_RESULT


def test_parse_approval_request_item():
    line = json.dumps({
        "type": "item.completed",
        "item": {"id": "item_3", "type": "approval_request", "command": "rm -rf /tmp/x"},
    })
    evs = CodexAdapter().parse_event(line)
    assert len(evs) == 1
    assert evs[0].type is EventType.PERMISSION_REQUEST
    assert evs[0].tool == "rm -rf /tmp/x"


def test_parse_blank_and_garbage():
    a = CodexAdapter()
    assert a.parse_event("   ") == []
    raw = a.parse_event("not json at all")
    assert raw[0].type is EventType.RAW and raw[0].text == "not json at all"


def test_parse_unknown_item_type_skipped():
    line = json.dumps({"type": "item.completed", "item": {"type": "unknown_future_type"}})
    assert CodexAdapter().parse_event(line) == []


# --- get_adapter registration ------------------------------------------------

def test_get_adapter_resolves_codex():
    assert isinstance(get_adapter("codex"), CodexAdapter)


# --- config integration (codex_homes from accounts.toml) --------------------

def test_codex_homes_default_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    config.set_account_codex_home("work", "/home/work/.codex")
    assert CodexAdapter().codex_homes == {"work": "/home/work/.codex"}
