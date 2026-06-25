"""Integration tests driving commands through the CLI entry point."""

import json

from horus.cli import main
from horus.instructions import check_drift


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _write_codex_rollout(home, project, *, total=910, window=1000):
    path = home / "sessions" / "2026" / "06" / "25" / "rollout-test.jsonl"
    path.parent.mkdir(parents=True)
    events = [
        {
            "timestamp": "2026-06-25T10:00:00Z",
            "type": "turn_context",
            "payload": {"cwd": str(project), "workspace_roots": [str(project)]},
        },
        {
            "timestamp": "2026-06-25T10:01:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {"total_tokens": total},
                    "model_context_window": window,
                },
                "rate_limits": {
                    "primary": {"used_percent": 12, "resets_at": 1782390000},
                    "secondary": {"used_percent": 34, "resets_at": 1782990000},
                },
            },
        },
    ]
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_session_new_creates_file_from_template(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])

    rc = main(["session", "new", "My Title", "--path", str(tmp_path)])
    assert rc == 0
    files = list((tmp_path / ".horus" / "sessions").glob("*-my-title.md"))
    assert files, "session file not created"
    text = files[0].read_text(encoding="utf-8")
    assert "My Title" in text
    assert "status: in-progress" in text


def test_session_new_refuses_without_horus(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["session", "new", "X", "--path", str(tmp_path)]) == 1


def test_close_runs_and_returns_status(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["close", "--path", str(tmp_path)]) in (0, 1)


def test_usage_check_cli_warns_and_hook_mode_exits_clean(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_codex_rollout(codex_home, tmp_path)

    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90"]) == 1
    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90", "--hook"]) == 0


def test_hook_install_codex_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex"]) == 0
    hooks_text = (tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8")
    assert '"Stop"' in hooks_text
    assert "horus usage check" in hooks_text
    assert "commandWindows" in hooks_text


def test_app_cli_dispatches_to_companion(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_run(project_root, **kwargs):
        calls.append((project_root, kwargs))
        return 0

    monkeypatch.setattr("horus.cli.companion.run_companion", fake_run)
    # Don't re-exec under pythonw.exe during the test; exercise inline dispatch.
    monkeypatch.setattr("horus.cli.companion.relaunch_without_console", lambda: False)

    assert main(["app", "--path", str(tmp_path), "--port", "9999", "--no-dashboard"]) == 0
    assert calls[0][0] == tmp_path.resolve()
    assert calls[0][1]["port"] == 9999
    assert calls[0][1]["start_dashboard"] is False


def test_reconcile_cli_resolves_drift(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])

    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        claude.read_text(encoding="utf-8").replace("project continuity", "DRIFTED"),
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    assert check_drift(
        agents.read_text(encoding="utf-8"), "AGENTS.md",
        claude.read_text(encoding="utf-8"), "CLAUDE.md",
    ).status == "drift"

    assert main(["reconcile", "instructions", "--path", str(tmp_path)]) == 0
    assert check_drift(
        agents.read_text(encoding="utf-8"), "AGENTS.md",
        claude.read_text(encoding="utf-8"), "CLAUDE.md",
    ).status == "aligned"


def test_consolidate_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["consolidate", "--path", str(tmp_path)]) == 0


def test_distill_history_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["distill-history", "--path", str(tmp_path)]) == 0


def test_infer_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["infer", "--path", str(tmp_path)]) == 0


def test_routine_commands_reject_nonexistent_path(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    missing = str(tmp_path / "does-not-exist")
    assert main(["consolidate", "--path", missing]) == 2
    assert main(["infer", "--path", missing]) == 2
    assert main(["distill-history", "--path", missing]) == 2


def test_skill_install_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    assert not (tmp_path / ".claude").exists()  # --no-skills opted out at init
    assert main(["skill", "install", "--path", str(tmp_path)]) == 0
    assert (tmp_path / ".claude" / "skills" / "horus-consolidate" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "horus-consolidate" / "SKILL.md").exists()


def test_skill_install_codex_target_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    assert main(["skill", "install", "--path", str(tmp_path), "--target", "codex"]) == 0
    assert (tmp_path / ".agents" / "skills" / "horus-consolidate" / "SKILL.md").exists()
    assert not (tmp_path / ".claude").exists()


def _claude_hook_run(monkeypatch, tmp_path, capsys, *, percent, threshold, stdin):
    """Drive `usage check --target claude --hook` with a mocked usage report + stdin."""
    import io

    from horus import claude_usage, native_hooks

    monkeypatch.setattr(
        claude_usage, "latest_usage",
        lambda **k: claude_usage.UsageReport(percent, None, 0.0, None),
    )
    monkeypatch.setattr(native_hooks.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    rc = main(["usage", "check", "--target", "claude", "--hook", "--threshold", str(threshold)])
    return rc, capsys.readouterr().out


def test_claude_hook_injects_closure_over_threshold(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90,
        stdin='{"session_id":"s1","stop_hook_active":false}',
    )
    assert rc == 0
    payload = json.loads(out.strip())
    assert payload["decision"] == "block"
    assert "horus-consolidate" in payload["reason"]  # drives the context-aware skill


def test_claude_hook_userpromptsubmit_injects_context(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90,
        stdin='{"session_id":"u1","hook_event_name":"UserPromptSubmit"}',
    )
    assert rc == 0
    payload = json.loads(out.strip())
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "horus-consolidate" in ctx  # diverts the agent to closure before the task


def test_claude_hook_quiet_under_threshold(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=40.0, threshold=90,
        stdin='{"session_id":"s2"}',
    )
    assert rc == 0 and out.strip() == ""


def test_claude_hook_fires_once_per_session(tmp_path, monkeypatch, capsys):
    stdin = '{"session_id":"dup","stop_hook_active":false}'
    _, out1 = _claude_hook_run(monkeypatch, tmp_path, capsys, percent=92.0, threshold=90, stdin=stdin)
    _, out2 = _claude_hook_run(monkeypatch, tmp_path, capsys, percent=92.0, threshold=90, stdin=stdin)
    assert out1.strip() and out2.strip() == ""  # second call suppressed by sentinel


def test_claude_hook_respects_stop_hook_active(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=99.0, threshold=90,
        stdin='{"session_id":"s3","stop_hook_active":true}',
    )
    assert rc == 0 and out.strip() == ""


def test_forget_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["forget", str(tmp_path)]) == 0
    assert main(["forget", str(tmp_path)]) == 1  # already gone
