"""Tests for native app hook installers."""

import json

from horus import native_hooks


def test_install_codex_usage_hook_creates_stop_hook(tmp_path):
    action = native_hooks.install_codex_usage_hook(tmp_path, threshold=80)

    assert action.status == "created"
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    handler = data["hooks"]["Stop"][0]["hooks"][0]
    assert handler["type"] == "command"
    assert "horus usage check --path . --threshold 80 --hook" in handler["command"]
    assert "commandWindows" in handler


def test_install_codex_usage_hook_preserves_other_hooks_and_replaces_horus_hook(tmp_path):
    hooks_file = tmp_path / ".codex" / "hooks.json"
    hooks_file.parent.mkdir()
    hooks_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "echo keep"}]},
                        {"hooks": [{"type": "command", "command": "python -m horus usage check --hook"}]},
                    ],
                    "PreToolUse": [{"hooks": [{"type": "command", "command": "echo pre"}]}],
                }
            }
        ),
        encoding="utf-8",
    )

    action = native_hooks.install_codex_usage_hook(tmp_path, threshold=70)

    assert action.status == "updated"
    data = json.loads(hooks_file.read_text(encoding="utf-8"))
    stop_commands = [
        handler["command"]
        for group in data["hooks"]["Stop"]
        for handler in group["hooks"]
    ]
    assert stop_commands == [
        "echo keep",
        "python -m horus usage check --path . --threshold 70 --hook",
    ]
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "echo pre"


def test_install_codex_usage_hook_is_idempotent(tmp_path):
    native_hooks.install_codex_usage_hook(tmp_path)
    action = native_hooks.install_codex_usage_hook(tmp_path)

    assert action.status == "exists"


def test_install_claude_usage_hook_creates_both_events(tmp_path):
    action = native_hooks.install_claude_usage_hook(tmp_path, threshold=85)

    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    for event in ("UserPromptSubmit", "Stop"):  # pre-task primary + post-turn safety net
        handler = data["hooks"][event][0]["hooks"][0]
        assert handler["type"] == "command"
        assert "usage check --target claude --hook --threshold 85" in handler["command"]


def test_install_claude_usage_hook_preserves_other_settings(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]}}), encoding="utf-8")

    native_hooks.install_claude_usage_hook(tmp_path)
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["model"] == "opus"  # untouched
    cmds = [h["command"] for g in data["hooks"]["Stop"] for h in g["hooks"]]
    assert "echo keep" in cmds
    assert any("usage check --target claude" in c for c in cmds)


def test_install_claude_usage_hook_idempotent(tmp_path):
    native_hooks.install_claude_usage_hook(tmp_path)
    assert native_hooks.install_claude_usage_hook(tmp_path).status == "exists"


def test_closure_sentinel_fires_once(tmp_path, monkeypatch):
    monkeypatch.setattr(native_hooks.tempfile, "gettempdir", lambda: str(tmp_path))
    sid = "sess-abc"
    assert native_hooks.closure_already_fired(sid) is False
    native_hooks.mark_closure_fired(sid)
    assert native_hooks.closure_already_fired(sid) is True
    # distinct sessions are independent
    assert native_hooks.closure_already_fired("other") is False


def test_closure_sentinel_rearms_after_window(tmp_path, monkeypatch):
    monkeypatch.setattr(native_hooks.tempfile, "gettempdir", lambda: str(tmp_path))
    sid = "rearm"
    native_hooks.mark_closure_fired(sid)
    assert native_hooks.closure_already_fired(sid) is True            # recent -> suppressed
    native_hooks._sentinel_path(sid).write_text("1", encoding="utf-8")  # 1970 -> beyond window
    assert native_hooks.closure_already_fired(sid) is False           # re-armed
