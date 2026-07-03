"""Tests for the agent-adapter contract, exercised through the FakeAdapter."""

from pathlib import Path

import pytest

from horus.adapters import (
    AgentEvent,
    EventType,
    FakeAdapter,
    PermissionPosture,
    SpawnSpec,
    get_adapter,
)
from horus.adapters.base import AgentRun, AgentSession


def _spec(**kw) -> SpawnSpec:
    base = {"prompt": "do the thing", "project_dir": Path("/proj")}
    base.update(kw)
    return SpawnSpec(**base)


# --- build_command (pure) ----------------------------------------------------

def test_build_command_spawn_includes_prompt_and_stream_format():
    argv = FakeAdapter().build_command(_spec())
    assert argv[:4] == ["fake-agent", "-p", "do the thing", "--output-format"]
    assert "stream-json" in argv
    assert "--resume" not in argv


def test_build_command_resume_adds_resume_id():
    argv = FakeAdapter().build_command(_spec(), resume_id="sess-42")
    assert "--resume" in argv and "sess-42" in argv


def test_build_command_threads_model_and_tools():
    argv = FakeAdapter().build_command(
        _spec(model="claude-opus-4-8", allowed_tools=("Read",), disallowed_tools=("Bash",), extra_args=("--verbose",))
    )
    assert ["--model", "claude-opus-4-8"] == argv[argv.index("--model"):argv.index("--model") + 2]
    assert "Read" in argv and "Bash" in argv and "--verbose" in argv


def test_permission_flags_cover_every_posture():
    fake = FakeAdapter()
    for posture in PermissionPosture:
        assert fake.permission_flags(posture)  # non-empty for each
    assert fake.permission_flags(PermissionPosture.FULL_AUTO) == ["--dangerously-skip-permissions"]


def test_build_env_isolates_by_account():
    assert FakeAdapter().build_env(_spec(account="rafa-personal")) == {"FAKE_AGENT_ACCOUNT": "rafa-personal"}
    assert FakeAdapter().build_env(_spec()) == {}


# --- parse_event (pure) ------------------------------------------------------

def test_parse_event_maps_each_kind():
    fake = FakeAdapter()
    assert fake.parse_event('{"event":"init","session_id":"s1"}') == [
        AgentEvent(EventType.SESSION_STARTED, session_id="s1", raw={"event": "init", "session_id": "s1"})
    ]
    assert fake.parse_event('{"event":"text","text":"hi"}')[0].type is EventType.ASSISTANT_TEXT
    assert fake.parse_event('{"event":"tool","tool":"Bash"}')[0].tool == "Bash"
    assert fake.parse_event('{"event":"result","ok":false}')[0].is_error is True
    assert fake.parse_event('{"event":"error","message":"boom"}')[0].type is EventType.ERROR


def test_parse_event_handles_blank_and_garbage():
    fake = FakeAdapter()
    assert fake.parse_event("   ") == []
    raw = fake.parse_event("not json")
    assert raw[0].type is EventType.RAW and raw[0].text == "not json"


# --- spawn / resume (shared orchestration via AgentRun) ----------------------

def test_spawn_streams_events_and_tracks_session():
    run = FakeAdapter(session_id="abc").spawn(_spec())
    events = run.drain()
    kinds = [e.type for e in events]
    assert kinds == [EventType.SESSION_STARTED, EventType.ASSISTANT_TEXT, EventType.RESULT]
    assert run.session.session_id == "abc"   # captured from the init event
    assert run.session.status == "exited"     # terminal, no error
    assert run.session.agent == "fake"


def test_resume_carries_the_session_id():
    run = FakeAdapter().resume("prev-session", _spec(prompt="continue"))
    run.drain()
    assert run.session.session_id == "prev-session"


def test_error_event_marks_run_failed():
    fake = FakeAdapter(script=[{"event": "init", "session_id": "x"}, {"event": "error", "message": "nope"}])
    run = fake.spawn(_spec())
    run.drain()
    assert run.session.status == "failed"


def _run_of(*events: AgentEvent) -> AgentRun:
    session = AgentSession(agent="fake", project_dir=Path("/proj"))
    return AgentRun(session, iter(events))


def test_failed_tool_result_does_not_fail_a_completed_run():
    # Regression: a failing tool call mid-run (denied permission, red test) used
    # to latch the whole run to failed even when it completed cleanly — registry
    # rows showed status=failed with returncode=0.
    run = _run_of(
        AgentEvent(EventType.SESSION_STARTED, session_id="s1"),
        AgentEvent(EventType.TOOL_RESULT, is_error=True),
        AgentEvent(EventType.RESULT, is_error=False),
    )
    run.drain()
    assert run.session.status == "exited"


def test_error_result_event_marks_run_failed():
    run = _run_of(AgentEvent(EventType.RESULT, is_error=True))
    run.drain()
    assert run.session.status == "failed"


def test_stream_error_recovered_by_successful_result_exits_clean():
    run = _run_of(
        AgentEvent(EventType.ERROR, text="transient", is_error=True),
        AgentEvent(EventType.RESULT, is_error=False),
    )
    run.drain()
    assert run.session.status == "exited"


def test_scripted_permission_request_surfaces():
    fake = FakeAdapter(script=[{"event": "permission", "tool": "Bash"}, {"event": "result", "ok": True}])
    types = [e.type for e in fake.spawn(_spec()).drain()]
    assert EventType.PERMISSION_REQUEST in types


def test_get_adapter_resolves_fake_and_rejects_unknown():
    assert isinstance(get_adapter("fake"), FakeAdapter)
    with pytest.raises(KeyError):
        get_adapter("nope")
