"""Integration tests driving commands through the CLI entry point."""

import json
import os

from horus import launcher, registry
from horus.cli import main
from horus.instructions import check_drift
from horus.registry import Registry, SessionRecord


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


def test_focus_running_session_calls_raiser(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    Registry.default().upsert(SessionRecord(
        session_id="abc12345def", agent="claude", project="/p",
        account="work", pid=os.getpid(), status="running",  # live pid -> stays running
    ))
    raised = {}
    monkeypatch.setattr(launcher, "focus_window_for_pid", lambda pid: raised.setdefault("pid", pid) or True)

    assert main(["focus", "abc123"]) == 0          # prefix match
    assert raised["pid"] == os.getpid()
    assert "Focused" in capsys.readouterr().out


def test_focus_unknown_and_not_running(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["focus", "nope"]) == 2            # no match
    assert "No session" in capsys.readouterr().out

    Registry.default().upsert(SessionRecord(
        session_id="dead0001", agent="claude", project="/p", pid=None, status="running",
    ))  # pid-less running -> reconcile -> orphaned -> not focusable
    assert main(["focus", "dead0001"]) == 1
    assert "not running" in capsys.readouterr().out


def test_focus_window_for_pid_safe_on_no_pid():
    assert launcher.focus_window_for_pid(None) is False
    assert launcher.focus_window_for_pid(0) is False


def test_sessions_cmd_lists_and_prunes(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus.registry import Registry, SessionRecord
    reg = Registry.default()  # ~/.horus/registry.json under the patched HOME
    reg.upsert(SessionRecord(session_id="abc123", agent="claude", project="/proj", pid=None, status="running"))

    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert "abc123" in out
    assert "orphaned" in out  # reconcile flipped pid-less "running" -> orphaned

    assert main(["sessions", "--prune"]) == 0
    assert reg.all() == []


def test_session_new_records_alias_not_email(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")
    main(["init", str(tmp_path), "--yes"])

    assert main(["session", "new", "Alias Test", "--path", str(tmp_path)]) == 0
    text = list((tmp_path / ".horus" / "sessions").glob("*-alias-test.md"))[0].read_text(encoding="utf-8")
    assert "rafael@example.com" not in text  # raw email never written
    assert "account: acct-" in text          # aliased instead


def test_session_new_uses_configured_alias(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")
    config.set_account_alias("rafael@example.com", "rafa-personal")
    main(["init", str(tmp_path), "--yes"])

    main(["session", "new", "Named", "--path", str(tmp_path)])
    text = list((tmp_path / ".horus" / "sessions").glob("*-named.md"))[0].read_text(encoding="utf-8")
    assert "account: rafa-personal" in text


def test_account_command_show_and_set(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")

    assert main(["account", "--set", "rafa-personal"]) == 0
    assert config.load_account_aliases()["rafael@example.com"] == "rafa-personal"

    capsys.readouterr()
    assert main(["account"]) == 0
    out = capsys.readouterr().out
    assert "rafa-personal" in out and "rafael@example.com" in out  # show reveals both locally


def test_run_fake_adapter_tracks_session(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus.registry import Registry

    rc = main(["run", "hello there", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "(fake) hello there" in out and "exited" in out
    recs = Registry.default().all()
    assert len(recs) == 1 and recs[0].agent == "fake"  # spawned session was tracked


def test_run_resume_uses_session_id(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["run", "continue", "--agent", "fake", "--resume", "prev-99", "--path", str(tmp_path)])
    assert rc == 0
    assert "session prev-99" in capsys.readouterr().out  # resumed the given id


def test_open_launches_and_tracks_running_session(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import launcher
    from horus.registry import Registry

    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 9999)
    rc = main(["open", str(tmp_path), "--agent", "fake", "--account", "demo"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Opened fake session" in out and "demo" in out

    recs = Registry.default().all()
    assert len(recs) == 1
    r = recs[0]
    assert r.status == "running" and r.pid == 9999 and r.account == "demo" and r.agent == "fake"


def test_run_account_mismatch_refuses(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    import json
    from horus import config

    cfgdir = tmp_path / "work-dir"
    cfgdir.mkdir()
    (cfgdir / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"emailAddress": "real@work.com"}}), encoding="utf-8"
    )
    config.set_account_alias("real@work.com", "actually-work")
    config.set_account_config_dir("work", str(cfgdir))  # "work" maps to a dir logged in as someone else

    rc = main(["run", "hi", "--agent", "claude", "--account", "work", "--path", str(tmp_path)])
    assert rc == 2  # guard refused before any subprocess
    assert "Refusing to run" in capsys.readouterr().out


def test_account_set_dir_maps_config_dir(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")
    config.set_account_alias("rafael@example.com", "rafa-personal")

    assert main(["account", "--set-dir", "/home/rafa/.claude-personal"]) == 0
    assert config.load_account_config_dirs() == {"rafa-personal": "/home/rafa/.claude-personal"}

    capsys.readouterr()
    assert main(["account"]) == 0
    assert "/home/rafa/.claude-personal" in capsys.readouterr().out  # surfaced in show


def test_close_runs_and_returns_status(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["close", "--path", str(tmp_path)]) in (0, 1)


def test_close_check_gates_on_freshness(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from tests.test_routines import _mk_fresh

    # Fresh lanes (current last_updated, authored NEXT/focus), non-git tmp -> gate passes.
    _mk_fresh(tmp_path)
    assert main(["close", "--check", "--path", str(tmp_path)]) == 0
    assert "Fresh" in capsys.readouterr().out

    # Stale lanes (last_updated older than the session) -> gate fails non-zero.
    _mk_fresh(tmp_path, proj_updated="2026-06-01", road_updated="2026-06-01")
    assert main(["close", "--check", "--path", str(tmp_path)]) == 1
    assert "Stale" in capsys.readouterr().out


def test_usage_check_cli_warns_and_codex_stop_hook_blocks_with_json(tmp_path, monkeypatch, capsys):
    import io

    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_codex_rollout(codex_home, tmp_path)
    monkeypatch.setattr("horus.native_hooks.tempfile.gettempdir", lambda: str(tmp_path))

    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90"]) == 1
    capsys.readouterr()
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id":"codex-stop","hook_event_name":"Stop"}'))
    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90", "--hook"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "horus-consolidate" in payload["reason"]


def test_codex_userpromptsubmit_hook_injects_context(tmp_path, monkeypatch, capsys):
    import io

    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_codex_rollout(codex_home, tmp_path)
    monkeypatch.setattr("horus.native_hooks.tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"session_id":"codex-prompt","hook_event_name":"UserPromptSubmit"}'),
    )

    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90", "--hook"]) == 0
    payload = json.loads(capsys.readouterr().out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    assert "horus-consolidate" in hso["additionalContext"]


def test_hook_install_codex_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex"]) == 0
    hooks_text = (tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8")
    assert '"Stop"' in hooks_text
    assert "horus usage check" in hooks_text
    assert "commandWindows" in hooks_text


def test_hook_install_codex_merge_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex", "--kind", "merge"]) == 0
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    assert group["hooks"][0]["command"] == "python -m horus close --hook"
    assert group["hooks"][0]["commandWindows"] == "py -m horus close --hook"


def test_hook_install_codex_guard_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex", "--kind", "guard"]) == 0
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    assert group["hooks"][0]["command"] == "python -m horus guard-host --hook"
    assert group["hooks"][0]["commandWindows"] == "py -m horus guard-host --hook"


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


# --- pre-merge closure gate (`horus close --hook`, a PreToolUse hook) ---

def _merge_hook_run(monkeypatch, capsys, *, tool_input, findings):
    from pathlib import Path

    from horus import cli
    from horus.continuity import Finding

    monkeypatch.setattr(cli, "_read_hook_stdin", lambda: tool_input)
    monkeypatch.setattr(cli.closure, "freshness_gate",
                        lambda root: [Finding(*f) for f in findings])
    rc = cli._close_merge_hook(Path("."))
    return rc, capsys.readouterr().out


def test_merge_hook_blocks_merge_when_lanes_stale(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Bash", "tool_input": {"command": "gh pr merge 15 --squash"}},
        findings=[("warn", "lanes stale")],
    )
    assert rc == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "horus-consolidate" in hso["permissionDecisionReason"]


def test_merge_hook_allows_merge_when_fresh(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Bash", "tool_input": {"command": "gh pr merge 15"}},
        findings=[("ok", "fresh")],
    )
    assert rc == 0 and out.strip() == ""


def test_merge_hook_ignores_non_merge_bash(monkeypatch, capsys):
    # Stale lanes, but the command isn't a merge -> never blocked.
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Bash", "tool_input": {"command": "git status"}},
        findings=[("fail", "lanes stale")],
    )
    assert rc == 0 and out.strip() == ""


def test_merge_hook_ignores_non_bash_tool(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Edit", "tool_input": {"command": "gh pr merge"}},
        findings=[("fail", "lanes stale")],
    )
    assert rc == 0 and out.strip() == ""


# --- hosted-session self-restart guard (`horus guard-host --hook`) ---

def _guard_hook_run(monkeypatch, capsys, *, command, hosted=True, host_pid="4242", tool="Bash"):
    from pathlib import Path

    from horus import cli

    if hosted:
        monkeypatch.setenv("HORUS_HOSTED_SESSION", "1")
        monkeypatch.setenv("HORUS_PTY_HOST_PID", host_pid)
    else:
        monkeypatch.delenv("HORUS_HOSTED_SESSION", raising=False)
        monkeypatch.delenv("HORUS_PTY_HOST_PID", raising=False)
    monkeypatch.setattr(cli, "_read_hook_stdin",
                        lambda: {"tool_name": tool, "tool_input": {"command": command}})
    rc = cli._guard_host_hook(Path("."))
    return rc, capsys.readouterr().out


def _assert_denied(rc, out):
    assert rc == 0
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "hosted" in hso["permissionDecisionReason"].lower()


def test_guard_blocks_app_relaunch_when_hosted(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="horus app"))


def test_guard_blocks_dashboard_relaunch_via_module(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="python -m horus dashboard"))


def test_guard_blocks_taskkill_of_python(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="taskkill /F /IM python.exe"))


def test_guard_blocks_kill_of_host_pid(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="kill -9 4242", host_pid="4242"))


def test_guard_blocks_kill_of_host_by_name(monkeypatch, capsys):
    for cmd in ("pkill -f horus", "taskkill /F /FI \"WINDOWTITLE eq horus dashboard\""):
        _assert_denied(*_guard_hook_run(monkeypatch, capsys, command=cmd))


def test_guard_allows_benign_command_when_hosted(monkeypatch, capsys):
    for cmd in ("git commit -m x", "ls -la", "gh pr merge 15", "kill -9 999"):
        rc, out = _guard_hook_run(monkeypatch, capsys, command=cmd, host_pid="4242")
        assert rc == 0 and out.strip() == "", cmd


def test_guard_noop_outside_hosted_session(monkeypatch, capsys):
    # The very commands that would be blocked inside a host are untouched elsewhere.
    rc, out = _guard_hook_run(monkeypatch, capsys, command="horus app", hosted=False)
    assert rc == 0 and out.strip() == ""


def test_guard_ignores_non_bash_tool(monkeypatch, capsys):
    rc, out = _guard_hook_run(monkeypatch, capsys, command="horus app", tool="Edit")
    assert rc == 0 and out.strip() == ""
