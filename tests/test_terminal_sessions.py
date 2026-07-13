import io
import json
import os
import subprocess
import sys
from pathlib import Path

from horus import cli, config, registry, terminal_app, terminal_sessions, tmux_runner
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


def test_default_target_prefers_tmux_for_bare_ssh(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setenv("SSH_CONNECTION", "phone host")
    monkeypatch.setattr(terminal_sessions, "tmux_available", lambda: True)
    assert terminal_sessions.default_target() == "tmux"
    monkeypatch.setenv("TMUX", "/tmp/tmux")
    assert terminal_sessions.default_target() == "current"


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
    first = terminal_sessions.launch_tmux(agent="fake", project_dir=root, attach=False)
    second = terminal_sessions.launch_tmux(agent="fake", project_dir=root, attach=False)
    assert first.ok and second.ok and first.session_id != second.session_id
    records = Registry.default().all()
    assert {record.session_id for record in records} == {first.session_id, second.session_id}
    assert all(record.launch_target == "tmux" for record in records)
    assert all(record.target_ref.startswith("horus-") for record in records)
    assert calls[0][0][:4] == ["tmux", "new-session", "-d", "-s"]


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
