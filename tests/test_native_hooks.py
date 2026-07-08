"""Tests for native app hook installers."""

import json
import os
import stat
import subprocess
import sys

import pytest

from horus import native_hooks


def test_install_codex_usage_hook_creates_stop_hook(tmp_path):
    action = native_hooks.install_codex_usage_hook(tmp_path, threshold=80)

    assert action.status == "created"
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    for event in ("UserPromptSubmit", "Stop"):
        handler = data["hooks"][event][0]["hooks"][0]
        assert handler["type"] == "command"
        assert "horus usage check --path . --threshold 80 --hook" in handler["command"]
        assert handler["command"].endswith("|| exit 0")  # missing CLI = silent no-op
        # Windows Codex hooks run through PowerShell (no `||` in PS 5.1) — own guard.
        assert "Get-Command horus" in handler["commandWindows"]
        assert "||" not in handler["commandWindows"]


def test_install_codex_usage_hook_preserves_other_hooks_and_replaces_horus_hook(tmp_path):
    hooks_file = tmp_path / ".codex" / "hooks.json"
    hooks_file.parent.mkdir()
    hooks_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "echo keep"}]},
                        {"hooks": [{"type": "command", "command": "python3 -m horus usage check --hook"}]},
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "echo prompt"}]},
                        {"hooks": [{"type": "command", "command": "python3 -m horus usage check --hook"}]},
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
        "horus usage check --path . --threshold 70 --hook || exit 0",
    ]
    prompt_commands = [
        handler["command"]
        for group in data["hooks"]["UserPromptSubmit"]
        for handler in group["hooks"]
    ]
    assert prompt_commands == [
        "echo prompt",
        "horus usage check --path . --threshold 70 --hook || exit 0",
    ]
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "echo pre"


def test_install_codex_usage_hook_rewrites_unguarded_generation(tmp_path):
    """The v0.0.7–v0.0.10 spelling (bare `horus …`, no guard) is matched by marker and
    rewritten in place, so `upgrade-project --apply` upgrades existing repos."""
    hooks_file = tmp_path / ".codex" / "hooks.json"
    hooks_file.parent.mkdir()
    hooks_file.write_text(
        json.dumps({"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "horus usage check --path . --threshold 90 --hook"}
        ]}]}}),
        encoding="utf-8",
    )

    action = native_hooks.install_codex_usage_hook(tmp_path)

    assert action.status == "updated"
    data = json.loads(hooks_file.read_text(encoding="utf-8"))
    handler = data["hooks"]["Stop"][0]["hooks"][0]
    assert handler["command"].endswith("|| exit 0")
    assert "Get-Command horus" in handler["commandWindows"]


def test_install_codex_usage_hook_is_idempotent(tmp_path):
    native_hooks.install_codex_usage_hook(tmp_path)
    action = native_hooks.install_codex_usage_hook(tmp_path)

    assert action.status == "exists"


def test_install_codex_merge_hook_creates_pretooluse_gate(tmp_path):
    action = native_hooks.install_codex_merge_hook(tmp_path)

    assert action.status == "created"
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    handler = group["hooks"][0]
    assert handler["command"] == "horus close --hook || exit 0"
    assert "Get-Command horus" in handler["commandWindows"]


def test_install_codex_usage_and_merge_hooks_coexist(tmp_path):
    native_hooks.install_codex_usage_hook(tmp_path)
    native_hooks.install_codex_merge_hook(tmp_path)
    native_hooks.install_codex_usage_hook(tmp_path)

    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in data["hooks"] and "Stop" in data["hooks"]
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "horus close --hook || exit 0"


def test_install_codex_merge_hook_idempotent(tmp_path):
    native_hooks.install_codex_merge_hook(tmp_path)
    assert native_hooks.install_codex_merge_hook(tmp_path).status == "exists"


def test_install_codex_guard_hook_creates_pretooluse_gate(tmp_path):
    action = native_hooks.install_codex_guard_hook(tmp_path)

    assert action.status == "created"
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    handler = group["hooks"][0]
    assert handler["command"] == "horus guard-host --hook || exit 0"
    assert "Get-Command horus" in handler["commandWindows"]


def test_install_codex_usage_merge_and_guard_hooks_coexist(tmp_path):
    native_hooks.install_codex_usage_hook(tmp_path)
    native_hooks.install_codex_merge_hook(tmp_path)
    native_hooks.install_codex_guard_hook(tmp_path)
    native_hooks.install_codex_usage_hook(tmp_path)
    native_hooks.install_codex_merge_hook(tmp_path)

    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in data["hooks"] and "Stop" in data["hooks"]
    commands = {g["hooks"][0]["command"] for g in data["hooks"]["PreToolUse"]}
    assert "horus close --hook || exit 0" in commands
    assert "horus guard-host --hook || exit 0" in commands


def test_install_codex_guard_hook_idempotent(tmp_path):
    native_hooks.install_codex_guard_hook(tmp_path)
    assert native_hooks.install_codex_guard_hook(tmp_path).status == "exists"


def test_install_claude_usage_hook_creates_both_events(tmp_path):
    action = native_hooks.install_claude_usage_hook(tmp_path, threshold=85)

    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    for event in ("UserPromptSubmit", "Stop"):  # pre-task primary + post-turn safety net
        handler = data["hooks"][event][0]["hooks"][0]
        assert handler["type"] == "command"
        assert "usage check --target claude --hook --threshold 85" in handler["command"]
        assert handler["command"].endswith("|| exit 0")  # missing CLI = silent no-op
        # Claude's hook schema is a single command string (sh / Git Bash on Windows).
        assert "commandWindows" not in handler


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


def test_install_claude_merge_hook_creates_pretooluse_gate(tmp_path):
    action = native_hooks.install_claude_merge_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    # Both Claude shell tools: agents on Windows issue git/gh through PowerShell,
    # and a Bash-only matcher never fires there. The command filters for the merge.
    assert group["matcher"] == "Bash|PowerShell"
    assert group["hooks"][0]["command"] == "horus close --hook || exit 0"


def test_install_claude_merge_hook_idempotent(tmp_path):
    native_hooks.install_claude_merge_hook(tmp_path)
    assert native_hooks.install_claude_merge_hook(tmp_path).status == "exists"


def test_usage_and_merge_hooks_coexist_without_clobber(tmp_path):
    native_hooks.install_claude_usage_hook(tmp_path)
    native_hooks.install_claude_merge_hook(tmp_path)
    # Re-running usage install must not wipe the merge gate (distinct events + markers).
    native_hooks.install_claude_usage_hook(tmp_path)
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in data["hooks"] and "Stop" in data["hooks"]
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "horus close --hook || exit 0"


def test_install_claude_guard_hook_creates_pretooluse_gate(tmp_path):
    action = native_hooks.install_claude_guard_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash|PowerShell"
    assert group["hooks"][0]["command"] == "horus guard-host --hook || exit 0"


def test_install_claude_guard_hook_idempotent(tmp_path):
    native_hooks.install_claude_guard_hook(tmp_path)
    assert native_hooks.install_claude_guard_hook(tmp_path).status == "exists"


def test_install_claude_fetch_check_hook_creates_sessionstart_hook(tmp_path):
    action = native_hooks.install_claude_fetch_check_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    handler = data["hooks"]["SessionStart"][0]["hooks"][0]
    assert handler["command"] == "horus fetch-check --hook || exit 0"


def test_install_claude_fetch_check_hook_idempotent(tmp_path):
    native_hooks.install_claude_fetch_check_hook(tmp_path)
    assert native_hooks.install_claude_fetch_check_hook(tmp_path).status == "exists"


def test_fetch_check_hook_is_in_claude_installer_set():
    # upgrade-project projects HOOK_INSTALLERS — the fetch-check hook must ride it
    # so satellites get the session-start signal on their next refresh.
    assert native_hooks.install_claude_fetch_check_hook in native_hooks.HOOK_INSTALLERS["claude"]


def test_install_claude_merge_hook_rehomes_stale_bash_matcher(tmp_path):
    # A repo scaffolded before the PowerShell fix carries the handler under a
    # "Bash"-only group; re-install must move it under the two-tool matcher, or the
    # fix never reaches satellites via `upgrade-project`.
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "horus close --hook || exit 0"}]},
    ]}}), encoding="utf-8")

    action = native_hooks.install_claude_merge_hook(tmp_path)

    assert action.status == "updated"
    groups = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert len(groups) == 1
    assert groups[0]["matcher"] == native_hooks.SHELL_TOOL_MATCHER
    assert groups[0]["hooks"][0]["command"] == "horus close --hook || exit 0"


def test_matcher_rehome_leaves_foreign_handlers_under_their_matcher(tmp_path):
    # Only the Horus handler moves; a user's own hook sharing the stale group keeps
    # its matcher untouched.
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [
            {"type": "command", "command": "horus close --hook || exit 0"},
            {"type": "command", "command": "echo user-hook"},
        ]},
    ]}}), encoding="utf-8")

    native_hooks.install_claude_merge_hook(tmp_path)

    groups = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    by_matcher = {g["matcher"]: [h["command"] for h in g["hooks"]] for g in groups}
    assert by_matcher["Bash"] == ["echo user-hook"]
    assert by_matcher[native_hooks.SHELL_TOOL_MATCHER] == ["horus close --hook || exit 0"]


def test_usage_merge_and_guard_hooks_coexist_without_clobber(tmp_path):
    native_hooks.install_claude_usage_hook(tmp_path)
    native_hooks.install_claude_merge_hook(tmp_path)
    native_hooks.install_claude_guard_hook(tmp_path)
    # Re-running each install must not wipe the others (distinct markers + groups).
    native_hooks.install_claude_usage_hook(tmp_path)
    native_hooks.install_claude_merge_hook(tmp_path)
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in data["hooks"] and "Stop" in data["hooks"]
    commands = {g["hooks"][0]["command"] for g in data["hooks"]["PreToolUse"]}
    assert "horus close --hook || exit 0" in commands
    assert "horus guard-host --hook || exit 0" in commands


def test_install_claude_usage_guard_hook_creates_broad_pretooluse_gate(tmp_path):
    action = native_hooks.install_claude_usage_guard_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == ""  # empty matcher -> fires on every tool call
    assert group["hooks"][0]["command"] == "horus usage guard --target claude --hook || exit 0"


def test_install_claude_usage_guard_hook_idempotent(tmp_path):
    native_hooks.install_claude_usage_guard_hook(tmp_path)
    assert native_hooks.install_claude_usage_guard_hook(tmp_path).status == "exists"


def test_install_codex_usage_guard_hook_creates_broad_pretooluse_gate(tmp_path):
    action = native_hooks.install_codex_usage_guard_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == ""
    handler = group["hooks"][0]
    assert handler["command"] == "horus usage guard --target codex --hook || exit 0"
    assert "Get-Command horus" in handler["commandWindows"]  # PS 5.1-safe guard


def test_usage_guard_coexists_with_merge_and_host_guard_hooks(tmp_path):
    native_hooks.install_claude_merge_hook(tmp_path)
    native_hooks.install_claude_guard_hook(tmp_path)
    native_hooks.install_claude_usage_guard_hook(tmp_path)
    # Re-running each install must not wipe the others (distinct markers).
    native_hooks.install_claude_merge_hook(tmp_path)
    native_hooks.install_claude_guard_hook(tmp_path)
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = {g["hooks"][0]["command"] for g in data["hooks"]["PreToolUse"]}
    assert "horus close --hook || exit 0" in commands
    assert "horus guard-host --hook || exit 0" in commands
    assert "horus usage guard --target claude --hook || exit 0" in commands


def test_offboard_strips_the_usage_guard_hook(tmp_path):
    native_hooks.install_claude_usage_guard_hook(tmp_path)
    assert native_hooks.file_has_horus_hooks(native_hooks.claude_settings_path(tmp_path)) is True
    native_hooks.remove_claude_hooks(tmp_path)
    assert native_hooks.file_has_horus_hooks(native_hooks.claude_settings_path(tmp_path)) is False


def test_install_claude_checkpoint_hook_creates_stop_hook(tmp_path):
    action = native_hooks.install_claude_checkpoint_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    group = data["hooks"]["Stop"][0]
    assert group["hooks"][0]["command"] == "horus checkpoint --hook || exit 0"


def test_install_claude_checkpoint_hook_idempotent(tmp_path):
    native_hooks.install_claude_checkpoint_hook(tmp_path)
    assert native_hooks.install_claude_checkpoint_hook(tmp_path).status == "exists"


def test_checkpoint_coexists_with_usage_stop_hook(tmp_path):
    """The Claude usage hook also lives on Stop — the two must not clobber each other
    (distinct markers)."""
    native_hooks.install_claude_usage_hook(tmp_path, threshold=90)
    native_hooks.install_claude_checkpoint_hook(tmp_path)
    native_hooks.install_claude_usage_hook(tmp_path, threshold=90)  # re-run must keep both
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = {g["hooks"][0]["command"] for g in data["hooks"]["Stop"]}
    assert "horus checkpoint --hook || exit 0" in commands
    assert any("horus usage check" in c for c in commands)


def test_install_codex_checkpoint_hook_creates_stop_hook(tmp_path):
    action = native_hooks.install_codex_checkpoint_hook(tmp_path)
    assert action.status == "created"
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    handler = data["hooks"]["Stop"][0]["hooks"][0]
    assert handler["command"] == "horus checkpoint --hook || exit 0"
    assert "Get-Command horus" in handler["commandWindows"]  # PS 5.1-safe guard


def test_codex_checkpoint_coexists_with_usage_stop_hook(tmp_path):
    native_hooks.install_codex_usage_hook(tmp_path, threshold=90)
    native_hooks.install_codex_checkpoint_hook(tmp_path)
    native_hooks.install_codex_usage_hook(tmp_path, threshold=90)
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    commands = {g["hooks"][0]["command"] for g in data["hooks"]["Stop"]}
    assert "horus checkpoint --hook || exit 0" in commands
    assert any("horus usage check" in c for c in commands)


def test_offboard_strips_the_checkpoint_hook(tmp_path):
    native_hooks.install_claude_checkpoint_hook(tmp_path)
    native_hooks.install_codex_checkpoint_hook(tmp_path)
    native_hooks.remove_claude_hooks(tmp_path)
    native_hooks.remove_codex_hooks(tmp_path)
    assert native_hooks.file_has_horus_hooks(native_hooks.claude_settings_path(tmp_path)) is False
    assert native_hooks.file_has_horus_hooks(native_hooks.codex_hooks_path(tmp_path)) is False


@pytest.mark.skipif(sys.platform == "win32", reason="exercises the POSIX guard under /bin/sh")
def test_guarded_hook_is_silent_noop_when_cli_missing(tmp_path):
    """A repo clone on a machine without Horus: the committed hook command must exit 0
    with no stdout (Claude hides stderr on exit 0), instead of erroring per tool call."""
    handler = native_hooks._claude_merge_hook_command()
    proc = subprocess.run(
        ["/bin/sh", "-c", handler["command"]],
        capture_output=True, text=True, input="{}",
        env={"PATH": str(tmp_path)},  # nothing on PATH — no horus
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


@pytest.mark.skipif(sys.platform == "win32", reason="exercises the POSIX guard under /bin/sh")
def test_guarded_hook_is_silent_when_cli_broken(tmp_path):
    """A horus that exists but dies (e.g. dead-on-import) must also be silenced — every
    real hook signals via stdout JSON with exit 0, so nonzero always means breakage."""
    fake = tmp_path / "horus"
    fake.write_text("#!/bin/sh\necho 'Traceback (most recent call last):' >&2\nexit 1\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    handler = native_hooks._claude_hook_command(90)
    proc = subprocess.run(
        ["/bin/sh", "-c", handler["command"]],
        capture_output=True, text=True, input="{}",
        env={"PATH": f"{tmp_path}{os.pathsep}/usr/bin:/bin"},
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


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
