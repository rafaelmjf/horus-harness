import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput

from horus import (
    claude_usage,
    cli,
    codex_usage,
    config,
    datums,
    launch,
    registry,
    run_executor,
    runlog,
    terminal_app,
    terminal_sessions,
    terminal_tui,
    tmux_runner,
    usage_snapshot,
)
from horus.launch import LaunchResult, PreparedInteractive
from horus.adapters import FakeAdapter
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


def _card(
    root: Path,
    name: str,
    *,
    title: str,
    priority: str,
    type: str,
    detail: str,
    status: str = "open",
) -> Path:
    path = root / ".horus" / "backlog" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nstatus: {status}\npriority: {priority}\ntype: {type}\ncreated: 2026-07-13\n---\n"
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


def test_launch_tmux_enables_scoped_mouse_mode_before_attach(tmp_path, monkeypatch):
    """Regression pin (2026-07-13 report): launch_tmux used to create a session
    and attach with mouse mode left off, so wheel-up reached the attended agent
    as a raw terminal escape sequence (recalled shell/agent input history,
    triggering accidental commands/interrupts) instead of entering tmux
    scrollback. This asserts the `set-option ... mouse on` call exists, in the
    right order, scoped to only the new session — the exact mechanism report."""
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.delenv("TMUX", raising=False)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(terminal_sessions.subprocess, "run", fake_run)
    result = terminal_sessions.launch_tmux(agent="fake", project_dir=root, attach=True)
    assert result.ok, result.error
    tmux_name = result.target_ref

    # Command order: create the session, then scope mouse mode to it, then attach.
    assert [call[1] for call in calls] == ["new-session", "set-option", "attach-session"]
    mouse_call = calls[1]
    assert mouse_call == ["tmux", "set-option", "-t", tmux_name, "mouse", "on"]
    assert "-g" not in mouse_call  # never the tmux server/user default
    for call in calls[1:]:
        assert call[2] == "-t" and call[3] == tmux_name  # every follow-up call targets only the new session


def test_launch_tmux_cleans_up_when_mouse_mode_configuration_fails(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.setattr(terminal_sessions.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.delenv("TMUX", raising=False)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[1] == "set-option":
            return subprocess.CompletedProcess(argv, 1, "", "no server running on socket")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(terminal_sessions.subprocess, "run", fake_run)
    result = terminal_sessions.launch_tmux(agent="fake", project_dir=root, attach=False)
    assert not result.ok
    assert "mouse" in result.error

    # New session created, mouse-mode configuration failed, and only that new
    # session was torn down — never left half-configured, never a live attach.
    assert [call[1] for call in calls] == ["new-session", "set-option", "kill-session"]
    tmux_name = result.target_ref
    assert calls[-1] == ["tmux", "kill-session", "-t", tmux_name]

    record = Registry.default().get(result.session_id)
    assert record.status == "failed"
    assert not terminal_sessions._runner_spec_path(result.session_id).exists()


def test_live_isolated_tmux_session_reports_mouse_on_and_leaves_global_untouched(tmp_path, monkeypatch):
    """A real, isolated tmux server proves ``launch_tmux`` actually leaves the new
    session with mouse mode on. Isolation is mandatory here (PRD Rules,
    2026-07-13 incident): every tmux subprocess call this module makes is routed
    through an explicit ``-S <path>`` socket for a throwaway server, so this can
    never see or touch the default tmux server / any real session on it."""
    if shutil.which("tmux") is None:
        pytest.skip("tmux is not installed")
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    socket_path = tmp_path / "horus-mouse-probe.sock"
    real_run = subprocess.run

    def isolated_run(argv, **kwargs):
        if argv and argv[0] == "tmux":
            argv = ["tmux", "-S", str(socket_path), *argv[1:]]
        return real_run(argv, **kwargs)

    monkeypatch.setattr(terminal_sessions.subprocess, "run", isolated_run)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.delenv("TMUX", raising=False)

    # A real, short-lived process to keep the pane (and session) alive long
    # enough to inspect it, without depending on any real agent CLI. Do not
    # inject anything into a live Codex/Claude session — this spawns its own.
    sleeper = [sys.executable, "-c", "import time; time.sleep(5)"]
    monkeypatch.setattr(
        launch,
        "prepare_interactive",
        lambda **kwargs: (
            PreparedInteractive(
                agent="fake",
                project=root,
                account=None,
                session_id="12345678-1234-1234-1234-123456789abc",
                argv=sleeper,
                env={},
            ),
            None,
        ),
    )

    try:
        result = terminal_sessions.launch_tmux(agent="fake", project_dir=root, attach=False)
        assert result.ok, result.error

        session_mouse = real_run(
            ["tmux", "-S", str(socket_path), "show-options", "-t", result.target_ref, "mouse"],
            capture_output=True, text=True, check=False,
        )
        assert session_mouse.returncode == 0
        assert session_mouse.stdout.strip() == "mouse on"

        global_mouse = real_run(
            ["tmux", "-S", str(socket_path), "show-options", "-g", "mouse"],
            capture_output=True, text=True, check=False,
        )
        assert "on" not in global_mouse.stdout  # the server/user default was never touched
    finally:
        real_run(["tmux", "-S", str(socket_path), "kill-server"], capture_output=True, check=False)


def test_live_isolated_detached_fake_run_keeps_terminal_receipt(tmp_path, monkeypatch):
    """Drive the real tmux runner while continuously reconciling its registry.

    The socket is explicit and throwaway: this probe cannot inspect or affect
    the user's tmux server. A fake adapter keeps it token-free while exercising
    the detached host, child/runner PID boundary, JSONL result, and datum store.
    """
    if shutil.which("tmux") is None:
        pytest.skip("tmux is not installed")
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    socket_path = tmp_path / "horus-detached-receipt-probe.sock"
    real_run = subprocess.run

    def isolated_run(argv, **kwargs):
        if argv and argv[0] == "tmux":
            argv = ["tmux", "-S", str(socket_path), *argv[1:]]
        return real_run(argv, **kwargs)

    monkeypatch.setattr(terminal_sessions.subprocess, "run", isolated_run)
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    monkeypatch.delenv("TMUX", raising=False)
    sid = "28345678-1234-1234-1234-123456789abc"
    request = run_executor.RunRequest(
        session_id=sid, agent="fake", project=root, prompt="isolated detached receipt probe",
        account=None, posture="auto-edit", model=None, effort=None, worker=True,
        resume=None, dispatch_base_sha=None, dispatch_pending=0,
    )

    try:
        result = terminal_sessions.launch_detached_run(request)
        assert result.ok, result.error
        deadline = time.monotonic() + 10
        record = Registry.default().get(sid)
        datum = datums.DatumStore.default().get(sid)
        while time.monotonic() < deadline:
            Registry.default().reconcile()
            record = Registry.default().get(sid)
            datum = datums.DatumStore.default().get(sid)
            if record and record.status == "exited" and datum and datum.runtime_seconds is not None:
                break
            time.sleep(0.02)

        assert record is not None and record.status == "exited"
        assert datum is not None and datum.exit == "completed" and datum.runtime_seconds is not None
        terminal_results = [
            event for event in runlog.read_events(sid)
            if event.get("event") == "result" and event.get("status") in {"exited", "failed", "stale"}
        ]
        assert [event["status"] for event in terminal_results] == ["exited"]
    finally:
        real_run(["tmux", "-S", str(socket_path), "kill-server"], capture_output=True, check=False)


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
    stopped = Registry.default().get(sid)
    assert stopped.status == "failed" and stopped.termination_reason == "stopped"


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
    reaped = Registry.default().get(sid)
    assert reaped.status == "failed" and reaped.termination_reason == "orphan-reaped"


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
    reaped = Registry.default().get(sid)
    assert reaped.status == "failed" and reaped.termination_reason == "orphan-reaped"


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


def test_detached_run_returns_only_after_runner_pid_handoff(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    request = run_executor.RunRequest(
        session_id="12345678-1234-1234-1234-123456789abc", agent="fake", project=root,
        prompt="do bounded work", account="isolated", posture="auto-edit", model="test-model",
        effort="high", worker=True, resume="native-resume", dispatch_base_sha="a" * 40,
        dispatch_pending=2,
    )
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    calls = []
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        lambda argv, **kwargs: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )

    def handoff(session_id, store, **_kwargs):
        store.update(session_id, pid=5150)
        terminal_sessions._runner_ready_path(session_id).write_text("5150\n", encoding="utf-8")
        return True

    monkeypatch.setattr(terminal_sessions, "_await_runner_handoff", handoff)
    result = terminal_sessions.launch_detached_run(request)

    assert result.ok and result.pid == 5150 and result.target_ref == "horus-12345678-123"
    record = Registry.default().get(request.session_id)
    assert record.launch_target == "tmux" and record.target_ref == result.target_ref
    assert record.agent_session_id == "native-resume"
    assert record.dispatch_base_sha == "a" * 40 and record.delivery_status == "unknown"
    payload = json.loads(terminal_sessions._runner_spec_path(request.session_id).read_text(encoding="utf-8"))
    assert payload["kind"] == "run" and payload["run"] == request.payload()
    assert calls[0][:6] == ["tmux", "new-session", "-d", "-s", result.target_ref, "-c"]
    assert calls[1] == ["tmux", "set-option", "-t", result.target_ref, "mouse", "on"]


def test_detached_run_handoff_failure_kills_only_its_new_tmux_host_and_cleans_files(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    request = run_executor.RunRequest(
        session_id="22345678-1234-1234-1234-123456789abc", agent="fake", project=root,
        prompt="do bounded work", account=None, posture="auto-edit", model=None, effort=None,
        worker=True, resume=None, dispatch_base_sha=None, dispatch_pending=0,
    )
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    calls = []
    monkeypatch.setattr(
        terminal_sessions.subprocess, "run",
        lambda argv, **kwargs: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""),
    )

    def failed_handoff(session_id, _store, **_kwargs):
        terminal_sessions._runner_ready_path(session_id).write_text("not-ready\n", encoding="utf-8")
        return False

    monkeypatch.setattr(terminal_sessions, "_await_runner_handoff", failed_handoff)
    result = terminal_sessions.launch_detached_run(request)

    assert not result.ok and "runner did not report" in result.error
    target = "horus-22345678-123"
    assert calls == [
        ["tmux", "new-session", "-d", "-s", target, "-c", str(root),
         f"{sys.executable} -m horus.tmux_runner {request.session_id}"],
        ["tmux", "set-option", "-t", target, "mouse", "on"],
        ["tmux", "kill-session", "-t", target],
    ]
    assert not terminal_sessions._runner_spec_path(request.session_id).exists()
    assert not terminal_sessions._runner_ready_path(request.session_id).exists()
    record = Registry.default().get(request.session_id)
    assert record.status == "failed" and record.termination_reason == "launch-error"


def test_foreground_executor_keeps_launcher_pid_until_adapter_child_replaces_it(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    observed = {}

    class InspectingFake(FakeAdapter):
        def spawn(self, spec):
            record = Registry.default().get(spec.run_session_id)
            observed["pid"] = record.pid
            observed["status"] = record.status
            run = super().spawn(spec)
            run.session.pid = 4242
            return run

    monkeypatch.setattr(run_executor.adapters, "get_adapter", lambda _agent: InspectingFake())
    request = run_executor.RunRequest(
        session_id="32345678-1234-1234-1234-123456789abc", agent="fake", project=tmp_path,
        prompt="foreground liveness", account=None, posture="default", model=None, effort=None,
        worker=False, resume=None, dispatch_base_sha=None, dispatch_pending=0,
    )

    assert run_executor.execute(request) == 0
    assert observed == {"pid": os.getpid(), "status": "running"}
    assert Registry.default().get(request.session_id).pid == 4242


def test_detached_executor_keeps_runner_pid_through_concurrent_completion_reconcile(tmp_path, monkeypatch):
    """The adapter child may exit while the tmux runner is still finalizing.

    A concurrent ``horus sessions`` used to see the dead child PID, append a
    stale/blocked result after the correct exited/delivery-ready result, and
    overwrite the precise runtime with null. The runner PID is the liveness
    authority for a detached run until its terminal receipt is durable.
    """
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "37345678-1234-1234-1234-123456789abc"
    Registry.default().upsert(SessionRecord(
        session_id=sid, agent="fake", project=root.as_posix(), pid=os.getpid(),
        launch_target="tmux", target_ref="horus-373456781234",
        dispatch_base_sha="base", delivery_expected=True,
    ))

    class ChildPidFake(FakeAdapter):
        def spawn(self, spec):
            run = super().spawn(spec)
            run.session.pid = 4242
            run.session.returncode = 0
            return run

    monkeypatch.setattr(run_executor.adapters, "get_adapter", lambda _agent: ChildPidFake())
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == os.getpid())
    evidence = run_executor.delivery.DeliveryEvidence(
        True, "2026-07-16T10:00:00+00:00", branch="worker/test", head_sha="head",
        pushed_sha="pushed", local_changes=False, continuity_closed=True,
        head_beyond_base=True, pushed_beyond_base=True,
    )
    reconciled = False

    def capture(*_args, **_kwargs):
        nonlocal reconciled
        if not reconciled:
            reconciled = True
            assert Registry.default().reconcile() == []
            assert Registry.default().get(sid).status == "running"
        return evidence

    monkeypatch.setattr(run_executor.delivery, "capture_delivery_evidence", capture)
    request = run_executor.RunRequest(
        session_id=sid, agent="fake", project=root, prompt="detached completion race",
        account=None, posture="auto-edit", model=None, effort=None, worker=True,
        resume=None, dispatch_base_sha="base", dispatch_pending=0, delivery_expected=True,
    )

    assert run_executor.execute(request) == 0

    record = Registry.default().get(sid)
    assert record.pid == os.getpid()
    assert record.status == "exited" and record.returncode == 0
    assert record.delivery_status == "delivery-ready"
    datum = datums.DatumStore.default().get(sid)
    assert datum.exit == "completed" and datum.runtime_seconds is not None
    assert datum.delivery_status == "delivery-ready"
    terminal_results = [
        event for event in runlog.read_events(sid)
        if event.get("event") == "result" and event.get("status") in {"exited", "failed", "stale"}
    ]
    assert [event["status"] for event in terminal_results] == ["exited"]


def test_expected_delivery_worker_exiting_cleanly_without_evidence_persists_noop(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    request = run_executor.RunRequest(
        session_id="42345678-1234-1234-1234-123456789abc", agent="fake", project=tmp_path,
        prompt="scripted expected delivery", account=None, posture="auto-edit", model=None, effort=None,
        worker=True, resume=None, dispatch_base_sha="base", dispatch_pending=0, delivery_expected=True,
    )
    evidence = run_executor.delivery.DeliveryEvidence(
        True, "2026-07-16T10:00:00+00:00", branch="worker/test", head_sha="base",
        pushed_sha=None, local_changes=False, continuity_closed=False,
        head_beyond_base=False, pushed_beyond_base=False,
    )
    monkeypatch.setattr(run_executor.delivery, "capture_delivery_evidence", lambda *_args, **_kwargs: evidence)

    assert run_executor.execute(request) == 0

    record = Registry.default().get(request.session_id)
    assert record.status == "exited" and record.delivery_expected is True
    assert record.delivery_status == "no-op" and record.delivery_pushed_sha is None
    result = runlog.read_events(request.session_id)[-1]
    assert result["delivery_status"] == "no-op" and result["delivery_expected"] is True
    datum = datums.DatumStore.default().get(request.session_id)
    assert datum.delivery_status == "no-op" and datum.delivery_checked_at == evidence.checked_at


def test_tmux_runner_routes_detached_run_to_shared_executor(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    sid = "12345678-1234-1234-1234-123456789abc"
    request = run_executor.RunRequest(
        session_id=sid, agent="fake", project=root, prompt="work", account=None,
        posture="auto-edit", model=None, effort=None, worker=True, resume=None,
        dispatch_base_sha=None, dispatch_pending=0,
    )
    path = terminal_sessions._runner_spec_path(sid)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"kind": "run", "run": request.payload()}), encoding="utf-8")
    Registry.default().upsert(SessionRecord(
        session_id=sid, agent="fake", project=root.as_posix(), pid=os.getpid(),
        launch_target="tmux", target_ref="horus-123456781234",
    ))
    seen = {}
    monkeypatch.setattr(run_executor, "execute", lambda received, watcher=None: seen.update(
        request=received, watcher=watcher,
    ) or 0)

    assert tmux_runner.main([sid]) == 0
    assert seen["request"] == request and callable(seen["watcher"])
    assert Registry.default().get(sid).pid == os.getpid()
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
    assert "Fleet Review" in rendered


def test_terminal_tui_fleet_review_is_optional_after_direct_projects(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    project = _project(tmp_path, "demo")
    curator = _project(tmp_path, "horus-agent")
    config.register_project(project)
    config.register_project(curator)
    record = terminal_tui.fleet_review.FleetReview(
        str(curator / "fleet.toml"),
        [
            terminal_tui.fleet_review.ProjectReview(
                "demo",
                "owner/demo",
                "active",
                terminal_tui.fleet_review.RemoteTruth(
                    available=True,
                    source="git",
                    ref="origin/main",
                    sha="abcdef123",
                    current_focus="Remote canonical focus",
                    capabilities=["One"],
                    backlog=[{"name": "bug"}],
                    source_commits_since_continuity=1,
                ),
                terminal_tui.fleet_review.LocalWorkingState(
                    available=True,
                    summary="feature/demo · uncommitted",
                ),
            )
        ],
    )
    calls = []
    monkeypatch.setattr(
        terminal_tui.fleet_review,
        "build",
        lambda projects: calls.append(projects) or record,
    )

    ui = terminal_tui.TerminalUI()
    assert ui.items[0] == ("project", project)
    assert ui.items[-1][0] == "campaign"
    fleet_review_index = next(index for index, item in enumerate(ui.items) if item[0] == "fleet_review")
    ui.move(fleet_review_index)
    ui.activate()
    assert ui.screen == "fleet_review" and calls == [[project.as_posix(), curator.as_posix()]]

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "Start curator session" in rendered
    assert "REMOTE SHIPPED TRUTH · git origin/main@abcdef12" in rendered
    assert "Remote canonical focus" in rendered
    assert "LOCAL WORKING STATE" in rendered and "feature/demo · uncommitted" in rendered
    assert "WARNING: 1 newer source commit" in rendered

    ui.activate()
    assert ui.screen == "accounts"
    assert ui.project == curator and ui.pending_mode == "resume"


def test_campaign_is_absent_without_a_registered_cockpit(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.register_project(_project(tmp_path, "demo"))

    ui = terminal_tui.TerminalUI()
    assert "campaign" not in {kind for kind, _value in ui.items}


def test_campaign_is_optional_and_distinct_from_fleet_review(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    project = _project(tmp_path, "demo")
    cockpit = _project(tmp_path, "horus-agent")
    config.register_project(project)
    config.register_project(cockpit)

    ui = terminal_tui.TerminalUI()
    kinds = [kind for kind, _value in ui.items]
    assert kinds.count("fleet_review") == 1
    assert kinds.count("campaign") == 1
    assert kinds.index("campaign") > kinds.index("fleet_review")

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "Campaign" in rendered
    assert "Fleet Review" in rendered

    campaign_index = kinds.index("campaign")
    ui.move(campaign_index)
    ui.application.exit = Mock()
    ui.activate()
    ui.application.exit.assert_called_once()
    assert isinstance(ui.application.exit.call_args.kwargs["result"], terminal_tui._Campaign)


def test_run_campaign_prompt_composes_bounded_brief_and_ignores_unknown_targets(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    demo = _project(tmp_path, "demo")
    other = _project(tmp_path, "other")
    cockpit = _project(tmp_path, "horus-agent")
    answers = iter(["Ship the launch prompt", "demo, other, bogus"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    printed: list[str] = []
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: printed.append(" ".join(str(a) for a in args)))

    result = terminal_tui._run_campaign_prompt([demo, other, cockpit])

    assert result is not None
    project, prompt = result
    assert project == cockpit
    assert "Ship the launch prompt" in prompt
    assert "demo" in prompt and "other" in prompt
    assert "bogus" not in prompt
    assert any("bogus" in line for line in printed)


def test_run_campaign_prompt_cancels_on_empty_outcome(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    cockpit = _project(tmp_path, "horus-agent")
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")

    assert terminal_tui._run_campaign_prompt([cockpit]) is None


def test_run_campaign_prompt_none_without_cockpit(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    demo = _project(tmp_path, "demo")

    def _fail_input(_prompt=""):
        raise AssertionError("must not prompt without a compatible cockpit")

    monkeypatch.setattr("builtins.input", _fail_input)
    assert terminal_tui._run_campaign_prompt([demo]) is None


def test_terminal_tui_projection_sync_reports_drift_and_launches_curator(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    project = _project(tmp_path, "demo")
    curator = _project(tmp_path, "horus-agent")
    config.register_project(project)
    config.register_project(curator)

    states = {
        project: {
            "verdict": "behind",
            "claude": {"status": "behind", "pending": 2},
            "codex": {"status": "behind", "pending": 1},
        },
        curator: {
            "verdict": "in_sync",
            "claude": {"status": "current", "pending": 0},
            "codex": {"status": "current", "pending": 0},
        },
    }
    monkeypatch.setattr(terminal_tui.projection_sync, "sync_state", states.__getitem__)

    ui = terminal_tui.TerminalUI()
    home = "".join(fragment[1] for fragment in ui._body_text())
    assert "Projection Sync" in home
    assert "1 stale · Claude/Codex vs installed CLI" in home

    ui.move(next(index for index, item in enumerate(ui.items) if item[0] == "projection_sync"))
    ui.activate()
    assert ui.screen == "projection_sync"
    report = "".join(fragment[1] for fragment in ui._body_text())
    assert "demo · behind" in report
    assert "Claude behind (2 pending) · Codex behind (1 pending)" in report
    assert "horus-agent · in sync" in report

    ui.activate()
    assert ui.screen == "accounts"
    assert ui.project == curator and ui.pending_origin == "projection_sync"
    assert "demo: behind" in ui.pending_prompt
    assert "use an isolated worktree" in ui.pending_prompt
    ui.back()
    assert ui.screen == "projection_sync"


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


def test_terminal_tui_project_screen_uses_canonical_focus_record(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    calls = []

    def resolve_focus(project):
        calls.append(project)
        return {"current_focus": "Protect durable continuity", "next_action": "Ship the TUI slice"}

    monkeypatch.setattr(terminal_tui.frontmatter, "resolve_focus", resolve_focus)
    ui = terminal_tui.TerminalUI()
    ui.activate()

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert calls == [root]
    assert rendered.index("Current focus") < rendered.index("Resume")
    assert rendered.index("Protect durable continuity") < rendered.index("Resume")
    assert rendered.index("Next action") < rendered.index("Resume")
    assert rendered.index("Ship the TUI slice") < rendered.index("Resume")


def test_terminal_tui_project_screen_warns_about_missing_machine_requirements(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    (root / ".horus" / "requirements.md").write_text(
        """---
kind: machine-requirements
tools:
  - name: Definitely absent CLI
    probe: horus-definitely-absent-cli
    install: install the project CLI
    needed_for: project builds
configs: []
---
""",
        encoding="utf-8",
    )
    config.register_project(root)
    calls = []
    original_inspect = terminal_tui.machine_requirements.inspect

    def inspect(project):
        calls.append(project)
        return original_inspect(project, which=lambda _name: None)

    monkeypatch.setattr(terminal_tui.machine_requirements, "inspect", inspect)
    ui = terminal_tui.TerminalUI()
    ui.activate()

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert calls == [root]
    assert rendered.index("this machine is missing: Definitely absent CLI") < rendered.index("Resume")
    assert "needed for project builds" in rendered
    assert "install: install the project CLI" in rendered


def test_terminal_tui_project_vision_and_capabilities_share_generated_record(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    calls = []
    record = {
        "generated_at": "2026-07-14T12:00:00+00:00",
        "project": {
            "vision": "A lightweight continuity layer for native coding agents.",
            "capabilities": [
                {
                    "text": "Resume a project from durable continuity.",
                    "related_commands": ["horus resume"],
                },
                {
                    "text": "Show active backlog cards.",
                    "related_commands": [],
                },
            ],
        },
    }

    def generate_project(path):
        calls.append(path)
        return json.dumps(record)

    monkeypatch.setattr(terminal_tui.capabilities, "generate_project", generate_project)
    monkeypatch.setattr(
        terminal_tui,
        "_capability_freshness",
        lambda root, generated_at: "generated 2h ago · 3 commits since",
    )

    ui = terminal_tui.TerminalUI()
    ui.activate()
    assert calls == [root.as_posix()]
    assert ui.screen == "project"
    project_text = "".join(fragment[1] for fragment in ui._body_text())
    assert "A lightweight continuity layer" in project_text
    assert "Capabilities" in project_text and "2 shipped capabilities" in project_text

    ui.move(3)
    ui.activate()
    assert ui.screen == "capabilities"
    assert calls == [root.as_posix()]  # screen renders the retained record; no second data path
    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "generated 2h ago · 3 commits since" in rendered
    assert "Resume a project from durable continuity." in rendered
    assert "commands: horus resume" in rendered
    assert "Show active backlog cards." in rendered
    ui.back()
    assert ui.screen == "project"


def test_terminal_tui_capabilities_failure_does_not_block_project_actions(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)

    def fail(_path):
        raise OSError("record unavailable")

    monkeypatch.setattr(terminal_tui.capabilities, "generate_project", fail)
    ui = terminal_tui.TerminalUI()
    ui.activate()
    assert ui.screen == "project"
    assert [kind for kind, _value in ui.items] == ["mode", "mode", "backlog", "capabilities", "receipts"]
    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "Capabilities unavailable: record unavailable" in rendered


def test_capability_freshness_reports_age_and_commits_since(tmp_path, monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "4\n", "")

    monkeypatch.setattr(terminal_tui.subprocess, "run", fake_run)
    rendered = terminal_tui._capability_freshness(
        tmp_path,
        "2026-07-14T10:00:00+00:00",
        now=terminal_tui.datetime.fromisoformat("2026-07-14T12:30:00+00:00"),
    )
    assert rendered == "generated 2h ago · 4 commits since"
    assert calls[0][0][-2:] == ["--since=2026-07-14T10:00:00+00:00", "HEAD"]


def test_terminal_tui_defaults_screen_lists_full_posture_vocabulary(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui._show("settings")
    assert [value for kind, value in ui.items if kind == "posture"] == list(config.LAUNCH_POSTURE_CHOICES)
    assert [value for kind, value in ui.items if kind == "continuity"] == list(
        config.CONTINUITY_GRANULARITY_CHOICES
    )
    assert ui.selected == config.LAUNCH_POSTURE_CHOICES.index("default")  # backward-compat default

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "full-auto" in rendered
    assert "bypass permissions" in rendered  # full-auto must read unambiguously as dangerous
    assert "Continuity checkpoint" in rendered
    assert "handoff" in rendered and "recommended" in rendered


def test_terminal_tui_defaults_persists_continuity_granularity(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui._show("settings")
    target = len(config.LAUNCH_POSTURE_CHOICES) + config.CONTINUITY_GRANULARITY_CHOICES.index("manual")
    ui.move(target - ui.selected)
    ui.activate()

    assert config.load_continuity_defaults() == {"granularity": "manual"}
    assert ui.selected == target
    assert "manual" in ui.status
    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "[current] manual" in rendered


def test_terminal_tui_warns_when_project_has_pending_continuity(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.register_project(root)
    monkeypatch.setattr(
        terminal_tui.closure,
        "pending_delivery_commits",
        lambda project: [("a" * 40, "feat: one"), ("b" * 40, "feat: two")],
    )
    ui = terminal_tui.TerminalUI()

    home = "".join(fragment[1] for fragment in ui._body_text())
    assert "continuity 2 pending" in home

    ui.project = root
    ui._load_project_focus()
    ui._show("project")
    project = "".join(fragment[1] for fragment in ui._body_text())
    assert "Continuity checkpoint pending · 2 delivery commits" in project


def test_terminal_tui_d_key_opens_defaults_from_home(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    async def drive():
        with create_pipe_input() as pipe_input:
            ui = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            task = asyncio.create_task(ui.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_text("d")
            await asyncio.sleep(0.02)
            pipe_input.send_text("q")
            assert await asyncio.wait_for(task, timeout=1) == "quit"
            return ui.screen

    # "d" is consumed as the Defaults shortcut, not typed into the underlying
    # terminal, and "q" back out lands on the settings screen's own quit binding.
    assert asyncio.run(drive()) == "settings"


def test_terminal_tui_defaults_screen_selection_persists_and_back_returns_home(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui._show("settings")

    target = config.LAUNCH_POSTURE_CHOICES.index("auto-edit")
    ui.move(target - ui.selected)
    assert ui.selected == target
    ui.activate()

    assert config.load_launch_defaults() == {"posture": "auto-edit"}
    assert "auto-edit" in ui.status
    assert ui.screen == "settings"  # stays put so the new selection is visible

    rendered = "".join(fragment[1] for fragment in ui._body_text())
    assert "[current] auto-edit" in rendered

    ui.back()
    assert ui.screen == "projects"


def test_terminal_tui_defaults_screen_reopens_with_persisted_selection(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.set_launch_default_posture("read-only")
    ui = terminal_tui.TerminalUI()
    ui._show("settings")
    assert ui.selected == config.LAUNCH_POSTURE_CHOICES.index("read-only")


def test_terminal_tui_run_applies_persisted_posture_to_new_launches(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    config.set_launch_default_posture("auto-edit")
    monkeypatch.setattr(terminal_sessions, "default_target", lambda: "current")
    captured = {}

    def fake_run_attached(**kwargs):
        captured.update(kwargs)
        return LaunchResult(True, kwargs["agent"], Path(kwargs["project_dir"]), session_id="12345678-rest")

    monkeypatch.setattr(terminal_sessions, "run_attached", fake_run_attached)

    results = iter([terminal_tui._Launch(root, "fake", "fresh", None, None), "quit"])

    class _StubApp:
        def run(self):
            return next(results)

    class _StubUI:
        def __init__(self, status=""):
            self.application = _StubApp()

    monkeypatch.setattr(terminal_tui, "TerminalUI", _StubUI)

    assert terminal_tui.run() == 0
    assert captured["posture"] == "auto-edit"  # the persisted default reached the launch call
    assert captured["agent"] == "fake" and captured["project_dir"] == root


def test_terminal_tui_run_prefers_bounded_prompt_override(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    monkeypatch.setattr(terminal_sessions, "default_target", lambda: "current")
    captured = {}

    def fake_run_attached(**kwargs):
        captured.update(kwargs)
        return LaunchResult(True, kwargs["agent"], Path(kwargs["project_dir"]), session_id="12345678-rest")

    monkeypatch.setattr(terminal_sessions, "run_attached", fake_run_attached)
    results = iter([
        terminal_tui._Launch(root, "fake", "resume", None, None, "bounded curator prompt"),
        "quit",
    ])

    class _StubApp:
        def run(self):
            return next(results)

    class _StubUI:
        def __init__(self, status=""):
            self.application = _StubApp()

    monkeypatch.setattr(terminal_tui, "TerminalUI", _StubUI)

    assert terminal_tui.run() == 0
    assert captured["prompt"] == "bounded curator prompt"


def test_terminal_tui_end_to_end_defaults_flow_via_real_application(tmp_path, monkeypatch):
    """Drives the real prompt_toolkit Application (not a stub) through the whole
    Defaults flow: open from home, move selection, save, back to home, quit."""
    _home(tmp_path, monkeypatch)

    async def drive():
        with create_pipe_input() as pipe_input:
            ui = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            task = asyncio.create_task(ui.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_text("d")  # open Defaults from home
            await asyncio.sleep(0.02)
            pipe_input.send_bytes(b"\x1b[B")  # one step down from "default"
            await asyncio.sleep(0.02)
            pipe_input.send_text("\r")  # save the new selection
            await asyncio.sleep(0.02)
            pipe_input.send_text("b")  # back to home
            await asyncio.sleep(0.02)
            pipe_input.send_text("q")
            assert await asyncio.wait_for(task, timeout=1) == "quit"
            return ui.screen

    assert asyncio.run(drive()) == "projects"
    assert config.load_launch_defaults()["posture"] == "auto-edit"  # one step down from "default"


def test_terminal_tui_run_default_posture_flows_into_claude_interactive_argv(tmp_path, monkeypatch):
    # One hop further than the plumbing test above: the persisted posture,
    # loaded exactly as `terminal_tui.run()` loads it, must turn into the real
    # adapter flag on the actual argv Claude would be launched with.
    _home(tmp_path, monkeypatch)
    config.set_launch_default_posture("full-auto")
    posture = config.load_launch_defaults()["posture"]
    prepared, error = launch.prepare_interactive(agent="claude", project_dir=tmp_path, posture=posture)
    assert error is None
    assert "bypassPermissions" in prepared.argv


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


def test_terminal_tui_manual_usage_refresh_updates_current_frame(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui._show("accounts")
    ui.selected = 4
    refreshed = [
        terminal_tui.LaunchAccount("claude", "personal", None),
        terminal_tui.LaunchAccount("codex", "work", "work"),
    ]
    snapshot = usage_snapshot.UsageSnapshot(42.0, "in 1h", 17.0, "in 3d")
    calls = []
    monkeypatch.setattr(terminal_tui, "_launch_accounts", lambda: refreshed)

    def refresh_usage(accounts):
        calls.append(accounts)
        return {("claude", "personal"): snapshot, ("codex", "work"): None}

    monkeypatch.setattr(terminal_tui, "_account_usage", refresh_usage)
    ui.refresh_account_usage()

    assert calls == [refreshed]
    assert ui.accounts == refreshed
    assert ui.account_usage[("claude", "personal")] == snapshot
    assert [value for _kind, value in ui.items] == refreshed
    assert ui.selected == 1  # old selection is clamped to the refreshed list
    assert ui.status == "Account usage refreshed from cache."


def test_terminal_tui_usage_refresh_key_and_footer_are_visible(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []
    original = terminal_tui.TerminalUI.refresh_account_usage

    def spy(self):
        calls.append(self.screen)
        original(self)

    monkeypatch.setattr(terminal_tui.TerminalUI, "refresh_account_usage", spy)

    async def drive():
        with create_pipe_input() as pipe_input:
            ui = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            footer = "".join(fragment[1] for fragment in ui._footer_text())
            task = asyncio.create_task(ui.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_text("u")
            await asyncio.sleep(0.02)
            pipe_input.send_text("q")
            assert await asyncio.wait_for(task, timeout=1) == "quit"
            return footer, ui.status

    footer, status = asyncio.run(drive())
    assert calls == ["projects"]
    assert "u refresh" in footer
    assert status == "Account usage refreshed from cache."


def test_terminal_tui_usage_refresh_reads_cache_only(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    account = terminal_tui.LaunchAccount("claude", "personal", None)
    snapshot = usage_snapshot.UsageSnapshot(31.0, None, 9.0, None)
    reads = []

    def read_cache_only(agent, alias):
        reads.append((agent, alias))
        return snapshot

    def live_call(*args, **kwargs):
        raise AssertionError("manual TUI refresh must not call a live usage endpoint")

    monkeypatch.setattr(terminal_tui.usage_snapshot, "read_cache_only", read_cache_only)
    monkeypatch.setattr(terminal_tui.claude_usage, "latest_usage", live_call)
    monkeypatch.setattr(terminal_tui.codex_usage, "latest_account_usage", live_call)

    assert terminal_tui._account_usage([account]) == {("claude", "personal"): snapshot}
    assert reads == [("claude", "personal")]


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
            # project -> mode -> account -> model (default) -> effort (default)
            pipe_input.send_bytes(b"\r\r\r\r\r")
            return await asyncio.wait_for(task, timeout=1)

    result = asyncio.run(drive())
    assert isinstance(result, terminal_tui._Launch)
    assert result.project == root and result.mode == "resume"
    assert result.agent == "claude" and result.account is None and result.card is None
    # Back-compat: accepting every default launches exactly as before —
    # the agent's own default model, no explicit reasoning effort.
    assert result.model is None and result.effort is None


def test_terminal_tui_model_and_effort_thread_into_the_launch(tmp_path, monkeypatch):
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
            pipe_input.send_bytes(b"\r")  # project
            await asyncio.sleep(0.02)
            pipe_input.send_bytes(b"\r")  # mode: resume
            await asyncio.sleep(0.02)
            pipe_input.send_bytes(b"\r")  # account: ambient personal
            await asyncio.sleep(0.02)
            assert ui.screen == "models"
            ui.selected = [value for _kind, value in ui.items].index("sonnet")
            pipe_input.send_bytes(b"\r")
            await asyncio.sleep(0.02)
            assert ui.screen == "effort"
            ui.selected = [value for _kind, value in ui.items].index("xhigh")
            pipe_input.send_bytes(b"\r")
            return await asyncio.wait_for(task, timeout=1)

    result = asyncio.run(drive())
    assert isinstance(result, terminal_tui._Launch)
    assert result.model == "sonnet" and result.effort == "xhigh"


def test_terminal_tui_models_screen_scoped_to_the_selected_account_agent(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()

    ui.pending_account = terminal_tui.LaunchAccount("claude", "personal", None)
    ui._show("models")
    claude_models = [value for _kind, value in ui.items]
    assert claude_models == [None, "opus", "sonnet", "haiku", "fable"]

    ui.pending_account = terminal_tui.LaunchAccount("codex", "personal", None)
    ui._show("models")
    codex_models = [value for _kind, value in ui.items]
    assert codex_models == [None, "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"]
    # A codex account never offers a claude model and vice-versa.
    assert not set(codex_models[1:]) & set(claude_models[1:])


def test_terminal_tui_effort_screen_offers_the_full_vocabulary(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    ui = terminal_tui.TerminalUI()
    ui._show("effort")
    assert [value for _kind, value in ui.items] == [None, "low", "medium", "high", "xhigh", "max"]


def test_terminal_tui_recommended_tag_present_for_tiered_resume_or_card_absent_for_fresh(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    card_path = _card(root, "tiered", title="Tiered card", priority="now", type="feature", detail="x")
    card_path.write_text(
        card_path.read_text(encoding="utf-8").replace("type: feature\n", "type: feature\ntier: sonnet\n"),
        encoding="utf-8",
    )
    config.register_project(root)
    ui = terminal_tui.TerminalUI()
    ui.project = root
    ui.pending_account = terminal_tui.LaunchAccount("claude", "personal", None)
    card = ui.project_cards[root][0]
    assert card.tier == "sonnet"

    # Card-launch (resume): the tier's model is tagged recommended.
    ui.pending_mode = "resume"
    ui.pending_card = card
    ui._show("models")
    rendered = "".join(text for _style, text in ui._body_text())
    assert "sonnet (recommended)" in rendered
    assert "opus (recommended)" not in rendered

    # Plain resume (no explicit card): falls back to the project's top open
    # card as the "next action" proxy — still recommended.
    ui.pending_card = None
    ui._show("models")
    rendered = "".join(text for _style, text in ui._body_text())
    assert "sonnet (recommended)" in rendered

    # Fresh launch: never recommends, even though a tiered card exists.
    ui.pending_mode = "fresh"
    ui._show("models")
    rendered = "".join(text for _style, text in ui._body_text())
    assert "(recommended)" not in rendered


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
        status="claimed",
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
    backlog_text = "".join(fragment[1] for fragment in ui._body_text())
    assert "[bug · claimed] Fix the terminal" in backlog_text
    assert "[feature] Add a feature" in backlog_text
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


def _card_screen_ui(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    path = _card(root, "review-me", title="Review me", priority="high", type="bug", detail="Detail.")
    config.register_project(root)
    ui = terminal_tui.TerminalUI()
    ui.activate()  # project
    ui.move(2)
    ui.activate()  # backlog
    ui.activate()  # card
    assert ui.screen == "card"
    return ui, root, path


def test_terminal_tui_e_and_r_keys_exit_with_edit_action_on_card_screen(tmp_path, monkeypatch):
    ui, root, path = _card_screen_ui(tmp_path, monkeypatch)

    async def drive(key):
        with create_pipe_input() as pipe_input:
            driven = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            driven.activate()
            driven.move(2)
            driven.activate()
            driven.activate()
            assert driven.screen == "card"
            task = asyncio.create_task(driven.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_text(key)
            return await asyncio.wait_for(task, timeout=1)

    edit = asyncio.run(drive("e"))
    assert isinstance(edit, terminal_tui._EditCard)
    assert edit.project == root and edit.card.path == path and edit.review is False

    review = asyncio.run(drive("r"))
    assert isinstance(review, terminal_tui._EditCard) and review.review is True

    footer = "".join(fragment[1] for fragment in ui._footer_text())
    assert "e edit" in footer and "r review" in footer


def test_terminal_tui_e_and_r_keys_inert_outside_card_screen(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    config.register_project(_project(tmp_path))

    async def drive():
        with create_pipe_input() as pipe_input:
            ui = terminal_tui.TerminalUI(input=pipe_input, output=DummyOutput())
            task = asyncio.create_task(ui.application.run_async())
            await asyncio.sleep(0.02)
            pipe_input.send_text("e")
            pipe_input.send_text("r")
            await asyncio.sleep(0.02)
            still_running = not task.done()
            pipe_input.send_text("q")
            assert await asyncio.wait_for(task, timeout=1) == "quit"
            return still_running, ui.screen

    still_running, screen = asyncio.run(drive())
    assert still_running and screen == "projects"


def test_editor_command_honors_visual_before_editor(monkeypatch):
    monkeypatch.setenv("VISUAL", "micro --softwrap off")
    monkeypatch.setenv("EDITOR", "nano")
    assert terminal_tui._editor_command() == ["micro", "--softwrap", "off"]


def test_editor_command_prefers_nano_then_falls_back_to_vi(monkeypatch):
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(terminal_tui.os, "name", "posix")
    monkeypatch.setattr(terminal_tui.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert terminal_tui._editor_command() == ["nano"]

    monkeypatch.setattr(terminal_tui.shutil, "which", lambda _name: None)
    assert terminal_tui._editor_command() == ["vi"]


def test_run_editor_explains_how_to_return_to_horus(tmp_path, monkeypatch, capsys):
    path = tmp_path / "card.md"
    path.write_text("# Card\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(terminal_tui, "_editor_command", lambda: ["nano"])
    monkeypatch.setattr(terminal_tui.subprocess, "run", lambda command, check: calls.append(command))

    assert terminal_tui._run_editor(path) is None
    assert calls == [["nano", str(path)]]
    notice = capsys.readouterr().out
    assert "external editor" in notice
    assert "Ctrl+X" in notice
    assert "return" in notice


def _git_project(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    root = _project(tmp_path)
    for args in (("init",), ("config", "user.email", "t@example.com"), ("config", "user.name", "Tester")):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    path = _card(root, "review-me", title="Review me", priority="high", type="bug", detail="Detail.")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", "init"], check=True, capture_output=True)
    from horus import backlog as backlog_mod

    return root, backlog_mod.find_card(root, "review-me")


def test_edit_card_flow_commits_on_confirm(tmp_path, monkeypatch):
    root, card = _git_project(tmp_path, monkeypatch)

    def fake_editor(path):
        path.write_text(path.read_text(encoding="utf-8") + "\nEdited line.\n", encoding="utf-8")
        return None

    monkeypatch.setattr(terminal_tui, "_run_editor", fake_editor)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    from horus import closure

    committed = {}
    monkeypatch.setattr(
        closure, "commit_continuity",
        lambda r, m, push=False: committed.update(root=r, message=m, push=push) or (True, "committed 1 file(s); pushed"),
    )
    status = terminal_tui._edit_card(root, card, review=False)
    assert committed["root"] == root and committed["push"] is True
    assert "edit via TUI" in committed["message"]
    assert status == "committed 1 file(s); pushed"


def test_edit_card_flow_decline_leaves_uncommitted(tmp_path, monkeypatch):
    root, card = _git_project(tmp_path, monkeypatch)

    def fake_editor(path):
        path.write_text(path.read_text(encoding="utf-8") + "\nEdited line.\n", encoding="utf-8")
        return None

    monkeypatch.setattr(terminal_tui, "_run_editor", fake_editor)
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    status = terminal_tui._edit_card(root, card, review=False)
    assert "uncommitted" in status
    assert "Edited line." in card.path.read_text(encoding="utf-8")


def test_edit_card_review_scaffolds_and_cancel_restores_card(tmp_path, monkeypatch):
    root, card = _git_project(tmp_path, monkeypatch)
    original = card.path.read_text(encoding="utf-8")
    seen = {}

    def untouched_editor(path):
        seen["text"] = path.read_text(encoding="utf-8")
        return None

    monkeypatch.setattr(terminal_tui, "_run_editor", untouched_editor)
    status = terminal_tui._edit_card(root, card, review=True)
    assert "## Reviews" in seen["text"]  # editor opened on the scaffolded entry
    assert terminal_tui._REVIEW_PLACEHOLDER in seen["text"]
    assert "cancelled" in status.lower()
    assert card.path.read_text(encoding="utf-8") == original  # scaffold reverted


def test_edit_card_no_change_reports_no_changes(tmp_path, monkeypatch):
    root, card = _git_project(tmp_path, monkeypatch)
    monkeypatch.setattr(terminal_tui, "_run_editor", lambda path: None)
    status = terminal_tui._edit_card(root, card, review=False)
    assert status == "No changes to review-me."
