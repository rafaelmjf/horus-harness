"""Tests for the shared attended-launch orchestration (`horus.launch`)."""

from pathlib import Path

from horus import launch, launcher
from horus.registry import Registry


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_launch_interactive_tracks_running_session(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"] = argv
        captured["cwd"] = cwd
        return 4242

    monkeypatch.setattr(launcher, "open_terminal", fake_open)

    result = launch.launch_interactive(agent="fake", project_dir=tmp_path, account="demo")
    assert result.ok and result.pid == 4242 and result.account == "demo"
    assert "--session-id" in captured["argv"]
    assert captured["argv"][-1] != ""  # fresh: no trailing prompt positional

    recs = Registry.default().all()
    assert len(recs) == 1
    r = recs[0]
    assert r.status == "running" and r.pid == 4242 and r.agent == "fake"
    assert r.session_id == result.session_id


def test_launch_interactive_injects_prompt(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = {}

    def fake_open(argv, cwd, env=None):
        captured["argv"] = argv
        return 1

    monkeypatch.setattr(launcher, "open_terminal", fake_open)

    result = launch.launch_interactive(
        agent="fake", project_dir=tmp_path, prompt="continue the widget work",
    )
    assert result.ok
    assert captured["argv"][-1] == "continue the widget work"  # seeded into the session


def test_launch_interactive_unknown_agent(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    result = launch.launch_interactive(agent="nope", project_dir=tmp_path)
    assert not result.ok and "nope" in result.error
    assert Registry.default().all() == []  # nothing tracked on failure


def test_launch_interactive_reports_terminal_failure(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    def boom(argv, cwd, env=None):
        raise OSError("no console")

    monkeypatch.setattr(launcher, "open_terminal", boom)
    result = launch.launch_interactive(agent="fake", project_dir=tmp_path)
    assert not result.ok and "no console" in result.error
    assert Registry.default().all() == []
