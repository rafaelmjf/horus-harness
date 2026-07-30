"""Tests for the shared attended-launch orchestration (`horus.launch`)."""

from pathlib import Path

import json

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


def test_prepare_interactive_refuses_mismatched_codex_account_before_spawning(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "personal-codex"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text(
        json.dumps({"tokens": {"account_id": "acct-work"}}), encoding="utf-8"
    )
    config.set_account_codex_home("personal", str(codex_home))
    config.set_account_alias("acct-work", "work")

    prepared, error = launch.prepare_interactive(
        agent="codex", project_dir=tmp_path, account="personal"
    )

    assert prepared is None
    assert error is not None
    assert "personal" in error and "work" in error


def test_claude_interactive_launch_records_the_agents_own_thread_id(tmp_path, monkeypatch):
    """Without this, Horus cannot reopen a session it started: `claude --resume` needs
    the agent's thread id, and every interactive row ever written had it as None
    (checked against 237 real rows, 2026-07-30). Claude's is knowable at launch
    because `interactive_command` pre-assigns it via `--session-id`."""
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 4242)

    result = launch.launch_interactive(agent="claude", project_dir=tmp_path)

    assert result.ok
    record = Registry.default().get(result.session_id)
    assert record.agent_session_id == result.session_id


def test_codex_interactive_launch_records_no_thread_id_rather_than_a_wrong_one(tmp_path, monkeypatch):
    """Codex mints its own id and cannot be told one, so at launch there is nothing
    truthful to record. Writing Horus's own id here would be actively harmful: it
    would look like a resumable thread and reopen nothing."""
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 4243)

    result = launch.launch_interactive(agent="codex", project_dir=tmp_path)

    assert result.ok
    record = Registry.default().get(result.session_id)
    assert record.agent_session_id is None


def test_the_two_ids_are_never_assumed_equal(tmp_path, monkeypatch):
    """`session_id` is Horus's run identity, `agent_session_id` the agent's thread.
    They coincide for Claude and differ for Codex — verified against three real
    restored sessions on 2026-07-30 — so any code assuming they match is wrong
    exactly half the time on a two-adapter install."""
    from horus import adapters

    assert adapters.get_adapter("claude").assigns_interactive_thread_id is True
    assert adapters.get_adapter("codex").assigns_interactive_thread_id is False

    _home(tmp_path, monkeypatch)
    prepared, error = launch.prepare_interactive(agent="codex", project_dir=tmp_path)
    assert error is None and prepared.agent_session_id is None
    # ...and the id Codex is handed is still dropped from its argv, as before.
    assert prepared.session_id not in prepared.argv
