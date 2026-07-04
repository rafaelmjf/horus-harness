"""PreToolUse usage guard — JSON shape, never-deny invariant, re-arm markers,
and the emergency state-save wiring."""

import json
import uuid

from horus import cli, native_hooks, rescue, usage_snapshot
from horus.usage_snapshot import UsageSnapshot


def _sid() -> str:
    return "guard-" + uuid.uuid4().hex[:8]  # unique so tempdir sentinels don't collide


def _stub_snapshot(monkeypatch, percent, resets_at="2026-07-04 21:10"):
    monkeypatch.setattr(
        usage_snapshot, "cached_usage",
        lambda *a, **k: UsageSnapshot(percent, resets_at),
    )


def _stub_stdin(monkeypatch, session_id):
    monkeypatch.setattr(cli, "_read_hook_stdin", lambda: {"session_id": session_id})


def test_below_advisory_is_silent_pass(tmp_path, monkeypatch, capsys):
    _stub_snapshot(monkeypatch, 50.0)
    _stub_stdin(monkeypatch, _sid())
    rc = cli._usage_guard_hook(tmp_path, "claude")
    assert rc == 0
    assert capsys.readouterr().out == ""  # no JSON emitted below 90%


def test_unreadable_snapshot_is_silent_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(usage_snapshot, "cached_usage", lambda *a, **k: None)
    rc = cli._usage_guard_hook(tmp_path, "claude")
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_advisory_band_injects_pretooluse_context_once(tmp_path, monkeypatch, capsys):
    sid = _sid()
    _stub_snapshot(monkeypatch, 92.0)
    _stub_stdin(monkeypatch, sid)

    rc = cli._usage_guard_hook(tmp_path, "claude")
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "92%" in hso["additionalContext"]
    # never a deny — the advisory only adds context
    assert "permissionDecision" not in hso and "decision" not in payload

    # re-arm: a second fire in the same window stays quiet
    rc2 = cli._usage_guard_hook(tmp_path, "claude")
    assert rc2 == 0
    assert capsys.readouterr().out == ""


def test_emergency_runs_state_save_once_and_injects_context(tmp_path, monkeypatch, capsys):
    sid = _sid()
    _stub_snapshot(monkeypatch, 98.0)
    _stub_stdin(monkeypatch, sid)
    calls = {"n": 0}

    def fake_rescue(root, *, session_id=None):
        calls["n"] += 1
        return rescue.RescueResult("worker", "wbranch", True, True, "rescued the full worktree to branch wbranch and pushed it")

    monkeypatch.setattr(rescue, "emergency_rescue", fake_rescue)

    rc = cli._usage_guard_hook(tmp_path, "claude")
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "98%" in hso["additionalContext"]
    assert "rescued the full worktree" in hso["additionalContext"]
    # emergency never denies the tool call
    assert "permissionDecision" not in hso and "decision" not in payload
    assert calls["n"] == 1

    # once-per-window: a second emergency fire does not re-run the rescue or re-inject
    rc2 = cli._usage_guard_hook(tmp_path, "claude")
    assert rc2 == 0
    assert capsys.readouterr().out == ""
    assert calls["n"] == 1


def test_emergency_survives_a_rescue_exception(tmp_path, monkeypatch, capsys):
    sid = _sid()
    _stub_snapshot(monkeypatch, 99.0)
    _stub_stdin(monkeypatch, sid)

    def boom(*a, **k):
        raise RuntimeError("git exploded")

    monkeypatch.setattr(rescue, "emergency_rescue", boom)
    rc = cli._usage_guard_hook(tmp_path, "claude")
    assert rc == 0  # guard invariant: exit 0 even when the rescue fails
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload["hookSpecificOutput"]["additionalContext"].lower()


def test_guard_falls_back_to_env_session_id(tmp_path, monkeypatch, capsys):
    _stub_snapshot(monkeypatch, 91.0)
    monkeypatch.setattr(cli, "_read_hook_stdin", lambda: {})  # no session_id in stdin
    monkeypatch.setenv("HORUS_RUN_SESSION_ID", "env-" + uuid.uuid4().hex[:8])
    rc = cli._usage_guard_hook(tmp_path, "claude")
    assert rc == 0
    assert "hookSpecificOutput" in json.loads(capsys.readouterr().out)


def test_guard_hook_installers_are_wired_into_hook_set():
    assert native_hooks.install_claude_usage_guard_hook in native_hooks.HOOK_INSTALLERS["claude"]
    assert native_hooks.install_codex_usage_guard_hook in native_hooks.HOOK_INSTALLERS["codex"]
