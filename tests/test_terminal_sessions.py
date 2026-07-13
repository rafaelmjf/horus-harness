import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path

from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput

from horus import (
    claude_usage,
    cli,
    codex_usage,
    config,
    registry,
    terminal_app,
    terminal_sessions,
    terminal_tui,
    tmux_runner,
    usage_snapshot,
)
from horus.launch import LaunchResult
from horus.registry import Registry, SessionRecord


def _home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def _project(tmp_path: Path, name: str = "demo") -> Path:
    root = tmp_path / name
    hdir = root / ".horus"
    hdir.mkdir(parents=True)
    (hdir / "PRD.md").write_text(
        "---\nstatus: active\ncurrent_focus: Test focus\n"
        "next_action: Ship the terminal flow\nnext_prompt: Continue testing\n"
        "execution_recommendation: continue-as-is\nlast_updated: 2026-07-13\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    return root


def _card(root: Path, name: str, *, title: str, priority: str, type: str, detail: str) -> Path:
    path = root / ".horus" / "backlog" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nstatus: open\npriority: {priority}\ntype: {type}\ncreated: 2026-07-13\n---\n"
        f"\n# {title}\n\n{detail}\n",
        encoding="utf-8",
    )
    return path


def test_default_target_prefers_tmux_when_available(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("HORUS_TERMINAL_TARGET", raising=False)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    assert terminal_sessions.default_target() == "tmux"


def test_default_target_falls_back_without_tmux_or_inside_tmux(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("HORUS_TERMINAL_TARGET", raising=False)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: False)
    assert terminal_sessions.default_target() == "current"

    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setenv("TMUX", "/tmp/tmux")
    assert terminal_sessions.default_target() == "current"


def test_default_target_honors_explicit_override(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "current")
    assert terminal_sessions.default_target() == "current"

    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: False)
    monkeypatch.setenv("HORUS_TERMINAL_TARGET", "tmux")
    assert terminal_sessions.default_target() == "tmux"


def test_tmux_is_unavailable_on_native_windows(monkeypatch):
    monkeypatch.setattr(terminal_sessions.os, "name", "nt")
    monkeypatch.setattr(terminal_sessions.shutil, "which", lambda _name: "C:/tmux.exe")
    assert terminal_sessions.tmux_available() is False


def test_attachability_requires_horus_tmux_target():
    attachable = SessionRecord(
        session_id="12345678-1234-1234-1234-123456789abc",
        agent="fake",
        project="/tmp/demo",
        launch_target="tmux",
        target_ref="horus-123456781234",
    )
    direct = SessionRecord(
        session_id="87654321-1234-1234-1234-123456789abc",
        agent="fake",
        project="/tmp/demo",
        launch_target="current",
    )
    incomplete = SessionRecord(
        session_id="abcdefab-1234-1234-1234-123456789abc",
        agent="fake",
        project="/tmp/demo",
        launch_target="tmux",
    )
    assert terminal_sessions.is_attachable(attachable) is True
    assert terminal_sessions.access_label(attachable) == "attachable"
    assert terminal_sessions.is_attachable(direct) is False
    assert terminal_sessions.access_label(direct) == "original terminal only"
    assert terminal_sessions.is_attachable(incomplete) is False


def test_run_attached_tracks_final_status(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)

    class Proc:
        pid = 4242

        def wait(self):
            return 0

    captured = {}

    def fake_popen(argv, **kwargs):
        captured["argv"] = argv
        captured.update(kwargs)
        return Proc()

    monkeypatch.setattr(terminal_sessions.subprocess, "Popen", fake_popen)
    result = terminal_sessions.run_attached(agent="fake", project_dir=root, account="demo")
    assert result.ok and result.pid == 4242
    assert captured["cwd"] == str(root)
    assert captured["env"]["FAKE_AGENT_ACCOUNT"] == "demo"
    record = Registry.default().get(result.session_id)
    assert record.status == "exited" and record.returncode == 0
    assert record.launch_target == "current"


def test_launch_tmux_creates_unique_tracked_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.delenv("TMUX", raising=False)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(terminal_sessions.subprocess, "run", fake_run)
    first = terminal_sessions.launch_tmux(
        agent="fake", project_dir=root, attach=False, cols=39, rows=24,
    )
    second = terminal_sessions.launch_tmux(agent="fake", project_dir=root, attach=False)
    assert first.ok and second.ok and first.session_id != second.session_id
    records = Registry.default().all()
    assert {record.session_id for record in records} == {first.session_id, second.session_id}
    assert all(record.launch_target == "tmux" for record in records)
    assert all(record.target_ref.startswith("horus-") for record in records)
    assert first.target_ref and first.target_ref.startswith("horus-")
    assert calls[0][0][:8] == ["tmux", "new-session", "-d", "-x", "39", "-y", "24", "-s"]


def test_launch_window_opens_tmux_viewer_when_supported(tmp_path, monkeypatch):
    root = _project(tmp_path)
    launched = LaunchResult(
        True,
        "fake",
        root,
        session_id="12345678-1234-1234-1234-123456789abc",
        target_ref="horus-123456781234",
    )
    monkeypatch.setattr(terminal_sessions, "default_target", lambda: "tmux")
    monkeypatch.setattr(terminal_sessions, "launch_tmux", lambda **_kwargs: launched)
    opened = {}

    def fake_open(argv, cwd, env=None):
        opened.update(argv=argv, cwd=cwd, env=env)
        return 5150

    monkeypatch.setattr(terminal_sessions.launcher, "open_terminal", fake_open)
    result = terminal_sessions.launch_window(agent="fake", project_dir=root)
    assert result.ok and result.pid == 5150
    assert opened["argv"] == ["tmux", "attach-session", "-t", "horus-123456781234"]
    assert opened["cwd"] == root


def test_launch_window_preserves_direct_fallback(tmp_path, monkeypatch):
    root = _project(tmp_path)
    captured = {}
    monkeypatch.setattr(terminal_sessions, "default_target", lambda: "current")

    def fake_launch(**kwargs):
        captured.update(kwargs)
        return LaunchResult(True, kwargs["agent"], Path(kwargs["project_dir"]), session_id="direct")

    monkeypatch.setattr(terminal_sessions.launch, "launch_interactive", fake_launch)
    result = terminal_sessions.launch_window(agent="codex", project_dir=root, account="work")
    assert result.ok and result.session_id == "direct"
    assert captured["agent"] == "codex" and captured["account"] == "work"


def test_launch_window_rolls_back_tmux_when_viewer_fails(tmp_path, monkeypatch):
    root = _project(tmp_path)
    launched = LaunchResult(
        True,
        "fake",
        root,
        session_id="12345678-1234-1234-1234-123456789abc",
        target_ref="horus-123456781234",
    )
    stopped = []
    monkeypatch.setattr(terminal_sessions, "default_target", lambda: "tmux")
    monkeypatch.setattr(terminal_sessions, "launch_tmux", lambda **_kwargs: launched)
    monkeypatch.setattr(
        terminal_sessions.launcher,
        "open_terminal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("no window")),
    )
    monkeypatch.setattr(
        terminal_sessions,
        "stop_session",
        lambda session_id, reg=None: stopped.append((session_id, reg)),
    )
    result = terminal_sessions.launch_window(agent="fake", project_dir=root)
    assert not result.ok and "no window" in result.error
    assert stopped == [(launched.session_id, None)]


def test_launch_tmux_refuses_nested_attach(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setenv("TMUX", "/tmp/tmux")
    result = terminal_sessions.launch_tmux(agent="fake", project_dir=root)
    assert not result.ok and "already inside tmux" in result.error
    assert Registry.default().all() == []


def test_attach_and_stop_use_horus_generated_tmux_name(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "12345678-1234-1234-1234-123456789abc"
    Registry.default().upsert(
        SessionRecord(
            session_id=sid,
            agent="fake",
            project=root.as_posix(),
            pid=os.getpid(),
            launch_target="tmux",
            target_ref="horus-123456781234",
        )
    )
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.delenv("TMUX", raising=False)
    calls = []
    monkeypatch.setattr(
        terminal_sessions.subprocess,
        "run",
        lambda argv, **kwargs: calls.append(argv) or subprocess.CompletedProcess(argv, 0),
    )
    assert terminal_sessions.attach_session("12345678") is None
    assert terminal_sessions.stop_session("12345678") is None
    assert calls == [
        ["tmux", "attach-session", "-t", "horus-123456781234"],
        ["tmux", "kill-session", "-t", "horus-123456781234"],
    ]
    assert Registry.default().get(sid).status == "exited"


def _fake_list_sessions(rows):
    listing = "\n".join(f"{name}\t{attached}\t{activity}" for name, attached, activity in rows)

    def fake_run(argv, **kwargs):
        if argv[:2] == ["tmux", "list-sessions"]:
            return subprocess.CompletedProcess(argv, 0, listing, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    return fake_run


def test_reap_orphans_returns_nothing_without_tmux(monkeypatch):
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: False)
    assert terminal_sessions.reap_orphans() == []


def test_reap_orphans_skips_attached_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        _fake_list_sessions([("horus-abc123456789", "1", "9000")]),
    )
    calls = []
    monkeypatch.setattr(terminal_sessions, "_kill_tmux_session", lambda name: calls.append(name))
    assert terminal_sessions.reap_orphans() == []
    assert calls == []


def test_reap_orphans_skips_recently_active_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        _fake_list_sessions([("horus-abc123456789", "0", "9700")]),  # idle 300s < grace
    )
    calls = []
    monkeypatch.setattr(terminal_sessions, "_kill_tmux_session", lambda name: calls.append(name))
    assert terminal_sessions.reap_orphans() == []
    assert calls == []


def test_reap_orphans_skips_live_session_backed_by_a_running_process(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "12345678-1234-1234-1234-123456789abc"
    Registry.default().upsert(
        SessionRecord(
            session_id=sid, agent="fake", project=root.as_posix(), pid=4242,
            status="running", launch_target="tmux", target_ref="horus-abc123456789",
        )
    )
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        _fake_list_sessions([("horus-abc123456789", "0", "9000")]),  # idle 1000s, unattached
    )
    monkeypatch.setattr(terminal_sessions.registry, "process_alive", lambda pid: True)
    calls = []
    monkeypatch.setattr(terminal_sessions, "_kill_tmux_session", lambda name: calls.append(name))
    assert terminal_sessions.reap_orphans() == []
    assert calls == []
    assert Registry.default().get(sid).status == "running"


def test_reap_orphans_kills_provably_orphaned_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "12345678-1234-1234-1234-123456789abc"
    Registry.default().upsert(
        SessionRecord(
            session_id=sid, agent="fake", project=root.as_posix(), pid=4242,
            status="stale", launch_target="tmux", target_ref="horus-abc123456789",
        )
    )
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        _fake_list_sessions([("horus-abc123456789", "0", "9000")]),  # idle 1000s, unattached
    )
    monkeypatch.setattr(terminal_sessions.registry, "process_alive", lambda pid: False)
    calls = []
    monkeypatch.setattr(terminal_sessions, "_kill_tmux_session", lambda name: calls.append(name))
    assert terminal_sessions.reap_orphans() == ["horus-abc123456789"]
    assert calls == ["horus-abc123456789"]
    assert Registry.default().get(sid).status == "orphaned"


def test_reap_orphans_never_touches_a_session_with_no_registry_record(tmp_path, monkeypatch):
    # An absent record is not positive evidence of anything (it could just mean a
    # stale/foreign/rebuilt registry looking at a real tmux server) — reap_orphans
    # must leave it alone even though it's idle and unattached.
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        _fake_list_sessions([("horus-untracked00000", "0", "9000")]),
    )
    calls = []
    monkeypatch.setattr(terminal_sessions, "_kill_tmux_session", lambda name: calls.append(name))
    assert terminal_sessions.reap_orphans() == []
    assert calls == []


def test_reap_orphans_kills_a_running_record_whose_tracked_pid_is_dead(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "12345678-1234-1234-1234-123456789abc"
    Registry.default().upsert(
        SessionRecord(
            session_id=sid, agent="fake", project=root.as_posix(), pid=4242,
            status="running", launch_target="tmux", target_ref="horus-abc123456789",
        )
    )
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        _fake_list_sessions([("horus-abc123456789", "0", "9000")]),  # idle 1000s, unattached
    )
    monkeypatch.setattr(terminal_sessions.registry, "process_alive", lambda pid: False)
    calls = []
    monkeypatch.setattr(terminal_sessions, "_kill_tmux_session", lambda name: calls.append(name))
    assert terminal_sessions.reap_orphans() == ["horus-abc123456789"]
    assert calls == ["horus-abc123456789"]
    assert Registry.default().get(sid).status == "orphaned"


def test_cmd_reap_reports_what_it_killed(monkeypatch, capsys):
    monkeypatch.setattr(terminal_sessions, "reap_orphans", lambda: ["horus-abc123456789"])
    assert cli.main(["reap"]) == 0
    assert "Reaped 1 orphaned tmux session(s): horus-abc123456789" in capsys.readouterr().out


def test_tmux_runner_executes_0600_spec_and_records_result(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "12345678-1234-1234-1234-123456789abc"
    path = terminal_sessions._runner_spec_path(sid)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "session_id": sid,
                "agent": "fake",
                "account": "demo",
                "project": root.as_posix(),
                "argv": [sys.executable, "-c", "raise SystemExit(0)"],
                "env": {"RUNNER_TEST": "1"},
            }
        ),
        encoding="utf-8",
    )
    Registry.default().upsert(
        SessionRecord(session_id=sid, agent="fake", project=root.as_posix(), pid=os.getpid(), launch_target="tmux")
    )
    assert tmux_runner.main([sid]) == 0
    record = Registry.default().get(sid)
    assert record.status == "exited" and record.returncode == 0
    assert not path.exists()


def test_terminal_app_lists_projects_and_quits(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    out = io.StringIO()
    assert terminal_app.run(input_fn=lambda _: "q", output=out) == 0
    text = out.getvalue()
    assert "HORUS — terminal" in text
    assert "demo" in text and "Ship the terminal flow" in text


def test_terminal_app_launches_selected_fresh_agent(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    monkeypatch.setattr(terminal_sessions, "default_target", lambda: "current")
    captured = {}

    def fake_launch(**kwargs):
        captured.update(kwargs)
        return LaunchResult(True, kwargs["agent"], Path(kwargs["project_dir"]), session_id="12345678-rest")

    monkeypatch.setattr(terminal_sessions, "run_attached", fake_launch)
    answers = iter(["1", "2", "b", "q"])
    out = io.StringIO()
    assert terminal_app.run(input_fn=lambda _: next(answers), output=out) == 0
    assert captured["agent"] == "claude" and captured["project_dir"] == root
    assert captured["prompt"] == "" and captured["account"] is None
    assert "Session 12345678 returned to Horus" in out.getvalue()


def test_terminal_app_labels_non_attachable_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    Registry.default().upsert(
        SessionRecord(
            session_id="12345678-1234-1234-1234-123456789abc",
            agent="codex",
            project=root.as_posix(),
            pid=os.getpid(),
            launch_target="current",
        )
    )
    answers = iter(["s", "1", "q"])
    out = io.StringIO()
    assert terminal_app.run(input_fn=lambda _: next(answers), output=out) == 0
    text = out.getvalue()
    assert "original terminal only" in text
    assert "cannot be attached here" in text


def test_terminal_tui_down_sequence_scrolls_selection_without_becoming_text(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    for index in range(12):
        config.register_project(_project(tmp_path, f"project-{index:02}"))

    ui = terminal_tui.TerminalUI()
    assert ui.selected == 0
    ui.move(8)
    assert ui.selected == 8
    content = ui.body.create_content(width=39, height=15)
    assert content.cursor_position.y > 15
    rendered = "".join(
        fragment[1]
        for line_number in range(content.line_count)
        for fragment in content.get_line(line_number)
    )
    assert "^[[B" not in rendered

    async def drive_real_input():
        with create_pipe_input() as pipe_input:
            driven = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            task = asyncio.create_task(driven.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_bytes(b"\x1b[B")
            await asyncio.sleep(0.02)
            pipe_input.send_text("q")
            assert await asyncio.wait_for(task, timeout=1) == "quit"
            return driven.selected

    assert asyncio.run(drive_real_input()) == 1


def test_terminal_tui_home_wraps_and_returns_account_rail_at_first_project(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    for index in range(12):
        config.register_project(_project(tmp_path, f"project-{index:02}"))

    ui = terminal_tui.TerminalUI()
    assert ui.body_window.wrap_lines() is True
    ui.move(8)
    ui.body_window.vertical_scroll = 20
    ui.move(-8)
    assert ui.selected == 0
    assert ui.body_window.vertical_scroll == 0


def test_terminal_tui_wide_home_uses_project_columns(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    for index in range(4):
        config.register_project(_project(tmp_path, f"project-{index:02}"))

    ui = terminal_tui.TerminalUI()
    monkeypatch.setattr(ui.application.output, "get_size", lambda: Size(rows=36, columns=120))
    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert any(
        "project-00" in line and "project-01" in line
        for line in rendered.splitlines()
    )


def test_terminal_tui_arrow_sequences_keep_conventional_direction(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    for index in range(3):
        config.register_project(_project(tmp_path, f"project-{index:02}"))

    async def drive():
        with create_pipe_input() as pipe_input:
            ui = terminal_tui.TerminalUI(
                input=pipe_input,
                output=DummyOutput(),
            )
            task = asyncio.create_task(ui.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_bytes(b"\x1b[B")
            await asyncio.sleep(0.02)
            selected_after_swipe_up = ui.selected
            pipe_input.send_bytes(b"\x1b[A")
            await asyncio.sleep(0.02)
            pipe_input.send_text("q")
            assert await asyncio.wait_for(task, timeout=1) == "quit"
            return selected_after_swipe_up, ui.selected

    assert asyncio.run(drive()) == (1, 0)


def test_terminal_tui_project_navigation_and_back(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    ui = terminal_tui.TerminalUI()
    ui.activate()
    assert ui.screen == "project" and ui.project == root
    ui.back()
    assert ui.screen == "projects"


def test_terminal_tui_distinguishes_attachable_sessions(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    direct = Registry.default().upsert(
        SessionRecord(
            session_id="12345678-1234-1234-1234-123456789abc",
            agent="codex",
            project=root.as_posix(),
            pid=os.getpid(),
            launch_target="current",
        )
    )
    managed = Registry.default().upsert(
        SessionRecord(
            session_id="87654321-1234-1234-1234-123456789abc",
            agent="claude",
            project=root.as_posix(),
            pid=os.getpid(),
            launch_target="tmux",
            target_ref="horus-876543211234",
        )
    )
    ui = terminal_tui.TerminalUI()
    ui._show("sessions")
    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "attachable · tmux" in rendered
    assert "original terminal only · current" in rendered

    ui.selected_session = direct
    ui._show("session")
    assert [kind for kind, _value in ui.items] == ["unavailable", "back"]
    assert "remains in its original terminal" in "".join(
        fragment[1] for fragment in ui._body_text()
    )

    ui.selected_session = managed
    ui._show("session")
    assert [kind for kind, _value in ui.items] == ["attach", "close", "back"]


def test_terminal_tui_names_ambient_accounts_and_combines_agents(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_account_alias("claude-personal-id", "personal")
    config.set_account_alias("codex-personal-id", "personal")
    config.set_account_config_dir("work", (tmp_path / "claude-work").as_posix())
    monkeypatch.setattr(claude_usage, "current_account", lambda *args, **kwargs: "claude-personal-id")
    monkeypatch.setattr(codex_usage, "current_account", lambda *args, **kwargs: "codex-personal-id")

    accounts = terminal_tui._launch_accounts()
    assert [(account.agent, account.alias, account.account) for account in accounts] == [
        ("claude", "personal", None),
        ("claude", "work", "work"),
        ("codex", "personal", None),
    ]


def test_terminal_tui_account_usage_uses_one_line_per_window(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui.accounts = [terminal_tui.LaunchAccount("claude", "personal", None)]
    ui.account_usage = {
        ("claude", "personal"): usage_snapshot.UsageSnapshot(
            None,
            None,
            83.0,
            "2026-07-17 09:59",
        )
    }

    rendered = "".join(fragment[1] for fragment in ui._account_summary_text())
    assert "Claude personal\n    5h --\n" in rendered
    assert "weekly 83%, resets 2026-07-17 09:59" in rendered
    assert "personal · 5h" not in rendered


def test_terminal_tui_resume_returns_ambient_personal_launch(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    config.set_account_alias("claude-personal-id", "personal")
    monkeypatch.setattr(claude_usage, "current_account", lambda *args, **kwargs: "claude-personal-id")
    monkeypatch.setattr(codex_usage, "current_account", lambda *args, **kwargs: None)

    async def drive():
        with create_pipe_input() as pipe_input:
            ui = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            task = asyncio.create_task(ui.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_bytes(b"\r\r\r")
            return await asyncio.wait_for(task, timeout=1)

    result = asyncio.run(drive())
    assert isinstance(result, terminal_tui._Launch)
    assert result.project == root and result.mode == "resume"
    assert result.agent == "claude" and result.account is None and result.card is None


def test_terminal_tui_project_kpis_and_backlog_card_resume(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    _card(root, "later-feature", title="Add a feature", priority="medium", type="feature", detail="Feature detail.")
    bug_path = _card(
        root,
        "urgent-bug",
        title="Fix the terminal",
        priority="high",
        type="bug",
        detail="Full bug description.\n\n- reproduce it\n- fix it",
    )
    config.register_project(root)
    ui = terminal_tui.TerminalUI()

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "backlog 2 · bugs 1" in rendered
    ui.activate()
    ui.move(2)
    ui.activate()
    assert ui.screen == "backlog"
    assert ui.items[0][1].title == "Fix the terminal"
    ui.activate()
    assert ui.screen == "card" and ui.card.path == bug_path
    card_text = "".join(fragment[1] for fragment in ui._body_text())
    assert "> Resume this card" in card_text
    assert "Full bug description" in card_text and "- reproduce it" in card_text
    assert "urgent-bug.md" in terminal_tui._card_prompt(root, ui.card)
    ui.activate()
    assert ui.screen == "accounts" and ui.pending_card.path == bug_path


def test_terminal_tui_inverts_only_mouse_scroll_for_ssh_touch_direction():
    natural = []
    inverted = []
    normal_control = terminal_tui._BodyControl(lambda: [], natural.append, invert_mouse_scroll=False)
    ssh_control = terminal_tui._BodyControl(lambda: [], inverted.append, invert_mouse_scroll=True)
    up = MouseEvent(Point(0, 0), MouseEventType.SCROLL_UP, MouseButton.NONE, frozenset())
    down = MouseEvent(Point(0, 0), MouseEventType.SCROLL_DOWN, MouseButton.NONE, frozenset())
    normal_control.mouse_handler(up)
    normal_control.mouse_handler(down)
    ssh_control.mouse_handler(up)
    ssh_control.mouse_handler(down)
    assert natural == [-1, 1]
    assert inverted == [1, -1]


def test_terminal_tui_does_not_auto_invert_narrow_ssh_scroll(monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "phone host")
    assert terminal_tui._invert_mobile_scroll() is False
    monkeypatch.setenv("HORUS_TUI_INVERT_SCROLL", "1")
    assert terminal_tui._invert_mobile_scroll() is True


def test_open_parser_exposes_scriptable_terminal_targets():
    args = cli.build_parser().parse_args(
        ["open", "/tmp/demo", "--agent", "codex", "--mode", "resume", "--target", "tmux", "--detach"]
    )
    assert args.agent == "codex" and args.mode == "resume"
    assert args.target == "tmux" and args.detach is True


def test_app_terminal_and_tui_share_the_terminal_surface(monkeypatch):
    calls = []
    monkeypatch.setattr(terminal_app, "run", lambda: calls.append("run") or 0)
    assert cli.main(["app", "--terminal"]) == 0
    assert cli.main(["tui"]) == 0
    assert calls == ["run", "run"]


def test_cmd_open_resume_tmux_uses_continuity_prompt(tmp_path, monkeypatch):
    root = _project(tmp_path)
    captured = {}

    def fake_tmux(**kwargs):
        captured.update(kwargs)
        return LaunchResult(True, kwargs["agent"], Path(kwargs["project_dir"]), session_id="12345678-rest")

    monkeypatch.setattr(terminal_sessions, "launch_tmux", fake_tmux)
    assert cli.main(["open", str(root), "--agent", "fake", "--mode", "resume", "--target", "tmux", "--detach"]) == 0
    assert "Resume the demo project" in captured["prompt"]
    assert captured["attach"] is False
