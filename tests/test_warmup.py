"""Tests for `horus warmup` — starting the Claude 5h usage window on demand."""

from __future__ import annotations

import argparse

import pytest

from horus import cli, config, notify_listen, warmup


@pytest.fixture
def _accounts(monkeypatch):
    monkeypatch.setattr(
        config, "load_account_config_dirs",
        lambda: {"personal": "/x/personal", "work": "/x/work"},
    )


def _recording_runner():
    calls: list[dict] = []

    def run(account, config_dir, *, prompt, model, timeout):
        calls.append({"account": account, "config_dir": config_dir, "prompt": prompt, "model": model})
        return warmup.WarmupResult(account, True, "window started")

    return run, calls


def test_warmup_warms_every_configured_account(_accounts):
    run, calls = _recording_runner()
    results = warmup.warmup(runner=run)
    assert {r.account for r in results} == {"personal", "work"}
    # each account is warmed under its OWN isolated config dir — never crossed
    by_account = {c["account"]: c["config_dir"] for c in calls}
    assert by_account == {"personal": "/x/personal", "work": "/x/work"}


def test_warmup_can_target_one_account(_accounts):
    run, calls = _recording_runner()
    results = warmup.warmup(["work"], runner=run)
    assert [r.account for r in results] == ["work"]
    assert calls[0]["config_dir"] == "/x/work"


def test_warmup_falls_back_to_default_login_when_none_configured(monkeypatch):
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {})
    run, calls = _recording_runner()
    results = warmup.warmup(runner=run)
    assert [r.account for r in results] == ["default"]
    assert calls[0]["config_dir"] is None  # the ambient ~/.claude


def test_warm_one_builds_the_claude_turn_and_injects_config_dir(monkeypatch):
    captured: dict = {}

    class _Ok:
        returncode = 0
        stdout = "hello"
        stderr = ""

    def _fake_run(argv, *, capture_output, text, timeout, env):
        captured["argv"] = argv
        captured["env"] = env
        return _Ok()

    monkeypatch.setattr(warmup.subprocess, "run", _fake_run)
    result = warmup._warm_one("work", "/x/work", prompt="hi", model="haiku", timeout=60)
    assert result.ok and result.detail == "window started"
    assert captured["argv"] == ["claude", "-p", "hi", "--model", "haiku"]
    assert captured["env"]["CLAUDE_CONFIG_DIR"] == "/x/work"


def test_warm_one_reports_a_missing_claude_cli(monkeypatch):
    def _fake_run(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(warmup.subprocess, "run", _fake_run)
    result = warmup._warm_one("work", "/x/work", prompt="hi", model=None, timeout=60)
    assert result.ok is False and "not found" in result.detail


def test_warm_one_reports_a_nonzero_exit(monkeypatch):
    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "not logged in"

    monkeypatch.setattr(warmup.subprocess, "run", lambda *a, **k: _Fail())
    result = warmup._warm_one("work", "/x/work", prompt="hi", model=None, timeout=60)
    assert result.ok is False and "not logged in" in result.detail


def test_grammar_warmup_maps_to_horus_warmup():
    calls: list[list[str]] = []
    notify_listen.dispatch("warmup", runner=lambda argv: calls.append(argv) or "")
    assert calls == [["warmup"]]


def test_cli_warmup_prints_per_account_result(_accounts, monkeypatch, capsys):
    monkeypatch.setattr(
        warmup, "warmup",
        lambda accounts=None, **k: [
            warmup.WarmupResult("personal", True, "window started"),
            warmup.WarmupResult("work", False, "not logged in"),
        ],
    )
    rc = cli.cmd_warmup(argparse.Namespace(account=None, model=warmup.DEFAULT_MODEL))
    out = capsys.readouterr().out
    assert rc == 0  # at least one warmed
    assert "personal: window started" in out and "work: not logged in" in out
    assert "1/2 account(s) warmed" in out
