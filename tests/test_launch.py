"""Tests for the shared attended-launch orchestration (`horus.launch`)."""

from pathlib import Path

from horus import config, launch, launcher, registry
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
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 4242)

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


def test_prepare_interactive_threads_model_and_effort(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    prepared, error = launch.prepare_interactive(
        agent="claude", project_dir=tmp_path, model="sonnet", effort="xhigh",
    )
    assert error is None and prepared is not None
    assert ["--model", "sonnet"] == [prepared.argv[prepared.argv.index("--model")], prepared.argv[prepared.argv.index("--model") + 1]]
    assert ["--effort", "xhigh"] == [prepared.argv[prepared.argv.index("--effort")], prepared.argv[prepared.argv.index("--effort") + 1]]


def test_prepare_interactive_enables_remote_control_by_default(tmp_path, monkeypatch):
    # The whole point is catching the sessions you FORGOT to enable it on: with no
    # per-launch override, a Claude launch reads the global default (on).
    _home(tmp_path, monkeypatch)
    prepared, error = launch.prepare_interactive(agent="claude", project_dir=tmp_path)
    assert error is None and prepared is not None
    assert "--remote-control" in prepared.argv


def test_prepare_interactive_per_launch_override_beats_global_default(tmp_path, monkeypatch):
    # Explicit False wins over the on-by-default global; explicit True wins over an off global.
    _home(tmp_path, monkeypatch)
    off, _ = launch.prepare_interactive(agent="claude", project_dir=tmp_path, remote_control=False)
    assert off is not None and "--remote-control" not in off.argv

    config.set_remote_control_default(False)
    still_off, _ = launch.prepare_interactive(agent="claude", project_dir=tmp_path)
    assert still_off is not None and "--remote-control" not in still_off.argv
    forced_on, _ = launch.prepare_interactive(agent="claude", project_dir=tmp_path, remote_control=True)
    assert forced_on is not None and "--remote-control" in forced_on.argv


def test_prepare_interactive_remote_control_is_claude_only(tmp_path, monkeypatch):
    # A non-Claude adapter ignores the request even with the global default on —
    # the launch layer gates it on the adapter's `supports_remote_control`.
    _home(tmp_path, monkeypatch)
    prepared, error = launch.prepare_interactive(
        agent="fake", project_dir=tmp_path, remote_control=True,
    )
    assert error is None and prepared is not None
    assert "--remote-control" not in prepared.argv


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
