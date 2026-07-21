"""Tests for the Claude Code adapter.

parse_event fixtures are real lines captured from `claude -p --output-format
stream-json --verbose` (Claude Code 2.1.191), trimmed for size.
"""

import json
from pathlib import Path

import pytest

from horus import claude_usage, config
from horus.adapters import AccountMismatch, ClaudeAdapter, EventType, PermissionPosture, SpawnSpec, get_adapter


def _spec(**kw) -> SpawnSpec:
    base = {"prompt": "do the thing", "project_dir": Path("/proj")}
    base.update(kw)
    return SpawnSpec(**base)


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _config_dir_with_email(tmp_path, name, email):
    """A fake CLAUDE_CONFIG_DIR containing a .claude.json logged in as `email`."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".claude.json").write_text(json.dumps({"oauthAccount": {"emailAddress": email}}), encoding="utf-8")
    return d


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


def test_build_command_effort_flag():
    # Claude Code's own CLI documents `--effort <level>` (probed live, 2.1.206) —
    # forwarded verbatim, no adapter-side translation.
    argv = ClaudeAdapter().build_command(_spec(effort="xhigh"))
    assert ["--effort", "xhigh"] == [argv[argv.index("--effort")], argv[argv.index("--effort") + 1]]


def test_build_command_no_effort_flag_by_default():
    # Default behavior unchanged when --effort is omitted.
    argv = ClaudeAdapter().build_command(_spec())
    assert "--effort" not in argv


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


# --- validate_model (provider-selector preflight) ----------------------------

def test_validate_model_rejects_calibration_key():
    err = ClaudeAdapter().validate_model("sonnet-5")
    assert err is not None
    assert "calibration key" in err
    assert "claude-sonnet-5" in err  # actionable full-selector correction
    assert "sonnet" in err  # actionable bare-alias correction


def test_validate_model_rejects_dotted_minor_calibration_key():
    err = ClaudeAdapter().validate_model("haiku-4.5")
    assert err is not None
    assert "claude-haiku-4-5" in err


@pytest.mark.parametrize("model", ["sonnet", "opus", "haiku", "fable", "claude-sonnet-5", "claude-haiku-4-5", None])
def test_validate_model_accepts_aliases_and_full_selectors_unchanged(model):
    assert ClaudeAdapter().validate_model(model) is None


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


def test_interactive_command_is_a_tui_with_preassigned_session():
    argv = ClaudeAdapter().interactive_command(_spec(model="haiku"), session_id="uuid-1")
    assert argv[0] == "claude"
    assert ["--session-id", "uuid-1"] == [argv[argv.index("--session-id")], argv[argv.index("--session-id") + 1]]
    assert ["--model", "haiku"] == [argv[argv.index("--model")], argv[argv.index("--model") + 1]]
    assert "-p" not in argv and "--output-format" not in argv  # interactive, not headless


def test_interactive_command_carries_effort_flag():
    # The TUI's attended launch path needs --effort too, not just headless -p runs.
    argv = ClaudeAdapter().interactive_command(_spec(effort="xhigh"), session_id="s1")
    assert ["--effort", "xhigh"] == [argv[argv.index("--effort")], argv[argv.index("--effort") + 1]]
    assert "--effort" not in ClaudeAdapter().interactive_command(_spec(), session_id="s1")


def test_interactive_command_carries_remote_control_flag():
    # Remote Control on the spec -> --remote-control at spawn, so the live
    # interactive session is reachable from the native app with no manual step.
    argv = ClaudeAdapter().interactive_command(_spec(remote_control=True), session_id="s1")
    assert "--remote-control" in argv
    # Off by default on the spec -> no flag (the launch layer decides the default).
    assert "--remote-control" not in ClaudeAdapter().interactive_command(_spec(), session_id="s1")


def test_claude_adapter_declares_remote_control_support():
    # The launch layer gates the request on this capability; Claude has it today.
    assert ClaudeAdapter.supports_remote_control is True


def test_known_models_are_the_bare_family_aliases():
    # The TUI's per-account model picker reads this directly — never a list of
    # its own — so it must carry the CLI-executable bare aliases, not the
    # dotted calibration-key spelling (see validate_model's rejection of those).
    assert ClaudeAdapter.KNOWN_MODELS == ("opus", "sonnet", "haiku", "fable")
    for model in ClaudeAdapter.KNOWN_MODELS:
        assert ClaudeAdapter().validate_model(model) is None


def test_interactive_command_carries_permission_posture():
    # Bypass posture -> the real Claude --permission-mode value (valid interactively).
    bypass = ClaudeAdapter().interactive_command(
        _spec(posture=PermissionPosture.FULL_AUTO), session_id="s1"
    )
    assert bypass[bypass.index("--permission-mode") + 1] == "bypassPermissions"
    # Default posture stays clean (no flag) so the TUI uses its normal prompts.
    assert "--permission-mode" not in ClaudeAdapter().interactive_command(_spec(), session_id="s1")


def test_interactive_command_injects_initial_prompt():
    # A non-empty prompt seeds the TUI as Claude's positional initial prompt;
    # an empty prompt leaves the session fresh (no trailing positional).
    seeded = ClaudeAdapter().interactive_command(_spec(prompt="resume the foo project"), session_id="s1")
    assert seeded[-1] == "resume the foo project"
    fresh = ClaudeAdapter().interactive_command(_spec(prompt=""), session_id="s1")
    assert fresh[-1] == "s1"  # ends at --session-id value; nothing appended


def test_get_adapter_resolves_claude():
    assert isinstance(get_adapter("claude"), ClaudeAdapter)


# --- multi-account isolation -------------------------------------------------

def test_config_dirs_default_from_config(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_account_config_dir("work", "/home/work/.claude")
    assert ClaudeAdapter().config_dirs == {"work": "/home/work/.claude"}  # picked up from accounts.toml


def test_verify_account_match(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    cfg = _config_dir_with_email(tmp_path, "work-dir", "rafa@work.com")
    config.set_account_alias("rafa@work.com", "work")
    adapter = ClaudeAdapter(config_dirs={"work": str(cfg)})

    check = adapter.verify_account("work")
    assert check.ok is True
    assert check.detected_email == "rafa@work.com"
    assert check.config_dir == str(cfg)


def test_verify_account_mismatch(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    cfg = _config_dir_with_email(tmp_path, "work-dir", "rafa@work.com")
    config.set_account_alias("rafa@work.com", "work")
    # "personal" points at a dir that is actually logged in as the "work" account.
    adapter = ClaudeAdapter(config_dirs={"personal": str(cfg)})

    check = adapter.verify_account("personal")
    assert check.ok is False
    assert check.detected_email == "rafa@work.com"


def test_verify_account_adopts_first_login_in_own_dir(tmp_path, monkeypatch):
    """The wizard maps alias→dir before the user signs in, so the login is invisible
    until a launch verifies it — the first (unaliased) login found in the account's
    own isolated dir is adopted, not refused. Regression: adding a second account
    and launching from the UI failed with 'login mismatch' on a correct setup."""
    _home(tmp_path, monkeypatch)
    cfg = _config_dir_with_email(tmp_path, "work-dir", "rafa@work.com")
    adapter = ClaudeAdapter(config_dirs={"work": str(cfg)})  # no email→alias row yet

    check = adapter.verify_account("work")
    assert check.ok is True
    assert config.load_account_aliases()["rafa@work.com"] == "work"  # learned for next time


def test_verify_account_never_adopts_into_ambient(tmp_path, monkeypatch):
    """No isolated dir mapped for the alias → nothing owns the ambient login; an
    unaliased ambient email must not be claimed by whatever account name was asked."""
    _home(tmp_path, monkeypatch)
    ambient = _config_dir_with_email(tmp_path, "home", "someone@example.com")
    monkeypatch.setattr(claude_usage, "config_path", lambda: ambient / ".claude.json")
    adapter = ClaudeAdapter(config_dirs={})

    check = adapter.verify_account("work")
    assert check.ok is False
    assert "someone@example.com" not in config.load_account_aliases()


def test_spawn_guard_refuses_account_mismatch(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    cfg = _config_dir_with_email(tmp_path, "work-dir", "rafa@work.com")
    config.set_account_alias("rafa@work.com", "work")
    adapter = ClaudeAdapter(config_dirs={"personal": str(cfg)})

    # The guard runs before any subprocess, so this raises without launching claude.
    with pytest.raises(AccountMismatch):
        adapter.spawn(_spec(account="personal"))
