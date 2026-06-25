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
