"""Tests for the machine-local escalation channel (`horus/notify.py`).

The acceptance the card pins, at the unit layer:

- with no sink configured, escalation is a silent no-op (pull-only unchanged);
- an event that is not enabled is skipped, not sent;
- a clean run never pushes a `success` ping unless it is opted in;
- a sink that fails NEVER raises — the run it reports on always continues;
- no config is read from anywhere but the machine-local `~/.horus/config.toml`.
"""

from __future__ import annotations

import argparse

import pytest

from horus import cli, config, notify, schedule


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """Point config.toml at a throwaway file so no test reads the real ~/.horus."""
    cfg = tmp_path / "config.toml"
    monkeypatch.setattr(config, "config_path", lambda: cfg)
    return cfg


def _write(cfg, text: str) -> None:
    cfg.write_text(text, encoding="utf-8")


def _esc(event=notify.SUPERVISE_GATE, **kw) -> notify.Escalation:
    base = dict(project="horus-harness", summary="a gate went red")
    base.update(kw)
    return notify.Escalation(event=event, **base)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def test_missing_file_is_pull_only():
    cfg = notify.load_notify_config()
    assert cfg.sink == "none"
    assert cfg.events == notify.DEFAULT_EVENTS


def test_no_notify_block_is_pull_only(_isolated_config):
    _write(_isolated_config, "workspace_root = '/x'\n")
    assert notify.load_notify_config().sink == "none"


def test_malformed_config_degrades_to_none(_isolated_config):
    _write(_isolated_config, "this is not = = valid toml [[[")
    assert notify.load_notify_config().sink == "none"


def test_telegram_block_parses_and_stringifies_chat_id(_isolated_config):
    _write(
        _isolated_config,
        "[notify]\nsink = 'telegram'\ntoken = 'abc:def'\nchat_id = 123456789\n",
    )
    cfg = notify.load_notify_config()
    assert cfg.sink == "telegram"
    assert cfg.token == "abc:def"
    assert cfg.chat_id == "123456789"  # int in TOML -> str for the API payload


def test_hermes_and_webhook_blocks_parse(_isolated_config):
    _write(_isolated_config, "[notify]\nsink = 'hermes'\ntarget = 'telegram:-100:7'\n")
    assert notify.load_notify_config().target == "telegram:-100:7"
    _write(_isolated_config, "[notify]\nsink = 'webhook'\nurl = 'https://h/x'\n")
    assert notify.load_notify_config().url == "https://h/x"


def test_events_default_to_the_three_failure_events(_isolated_config):
    _write(_isolated_config, "[notify]\nsink = 'telegram'\n")
    cfg = notify.load_notify_config()
    assert cfg.events == notify.DEFAULT_EVENTS
    assert not cfg.enabled(notify.SUCCESS)  # success is opt-in


def test_events_override_makes_success_opt_in(_isolated_config):
    _write(
        _isolated_config,
        "[notify]\nsink = 'telegram'\nevents = ['delivery-failed', 'success']\n",
    )
    cfg = notify.load_notify_config()
    assert cfg.enabled(notify.SUCCESS)
    assert cfg.enabled(notify.DELIVERY_FAILED)
    assert not cfg.enabled(notify.SUPERVISE_GATE)


# --------------------------------------------------------------------------- #
# escalate() — gating and best-effort contract
# --------------------------------------------------------------------------- #


def test_no_sink_is_a_silent_skip():
    result = notify.escalate(_esc(), cfg=notify.NotifyConfig(sink="none"))
    assert not result.delivered
    assert result.skipped and "no sink" in result.skipped


def test_disabled_event_is_skipped_not_sent():
    sent = []
    cfg = notify.NotifyConfig(sink="telegram", events=frozenset({notify.DELIVERY_FAILED}))
    result = notify.escalate(
        _esc(event=notify.SUCCESS), cfg=cfg, sender=lambda c, e: sent.append(e),
    )
    assert not result.delivered
    assert result.skipped and "not enabled" in result.skipped
    assert sent == []  # transport never touched


def test_force_bypasses_the_event_gate():
    sent = []
    cfg = notify.NotifyConfig(sink="telegram", events=frozenset())
    result = notify.escalate(
        _esc(event=notify.SUCCESS), cfg=cfg, force=True, sender=lambda c, e: sent.append(e),
    )
    assert result.delivered
    assert len(sent) == 1


def test_delivered_when_sender_succeeds():
    cfg = notify.NotifyConfig(sink="telegram", events=notify.DEFAULT_EVENTS)
    result = notify.escalate(_esc(), cfg=cfg, sender=lambda c, e: None)
    assert result.delivered
    assert result.error is None


def test_a_failing_sink_never_raises_and_reports_the_error():
    def boom(_cfg, _esc):
        raise RuntimeError("bot is dead")

    cfg = notify.NotifyConfig(sink="telegram", events=notify.DEFAULT_EVENTS)
    result = notify.escalate(_esc(), cfg=cfg, sender=boom)  # must not raise
    assert not result.delivered
    assert result.error == "bot is dead"


def test_unknown_sink_is_an_error_not_a_crash():
    cfg = notify.NotifyConfig(sink="carrier-pigeon", events=notify.DEFAULT_EVENTS)
    result = notify.escalate(_esc(), cfg=cfg)
    assert not result.delivered
    assert result.error and "unknown sink" in result.error


# --------------------------------------------------------------------------- #
# Sinks
# --------------------------------------------------------------------------- #


def test_telegram_sink_success(monkeypatch):
    seen = {}

    def fake_post(url, payload):
        seen["url"] = url
        seen["payload"] = payload
        return 200, '{"ok":true,"result":{}}'

    monkeypatch.setattr(notify, "_post_json", fake_post)
    cfg = notify.NotifyConfig(sink="telegram", token="T:K", chat_id="42")
    result = notify.escalate(_esc(summary="boom"), cfg=cfg)
    assert result.delivered
    assert "botT:K/sendMessage" in seen["url"].replace("bot", "bot")  # token in path
    assert seen["payload"]["chat_id"] == "42"
    assert "boom" in seen["payload"]["text"]


def test_telegram_sends_body_only_no_subject_duplication(monkeypatch):
    """A phone message must not print the summary twice. Telegram sends body() (which
    folds the project into its header), never subject()+body()."""
    seen = {}
    monkeypatch.setattr(notify, "_post_json", lambda u, p: (seen.setdefault("p", p), (200, '{"ok":true}'))[1])
    cfg = notify.NotifyConfig(sink="telegram", token="T:K", chat_id="42")
    esc = _esc(summary="batch b done (2/2)", details=("✓ a: delivered · PR #1", "✗ b: blocked"))
    assert notify.escalate(esc, cfg=cfg).delivered
    text = seen["p"]["text"]
    assert text == esc.body()                 # body only — not subject + body
    assert text.count("batch b done (2/2)") == 1  # summary appears exactly once
    assert "horus-harness · batch b done" in text  # project folded into the header
    assert "[horus] horus-harness:" not in text    # no separate subject line
    assert "✓ a: delivered · PR #1" in text and "✗ b: blocked" in text  # details render once


def test_telegram_sink_non_ok_status_is_an_error(monkeypatch):
    monkeypatch.setattr(notify, "_post_json", lambda u, p: (403, '{"ok":false}'))
    cfg = notify.NotifyConfig(sink="telegram", token="T:K", chat_id="42")
    result = notify.escalate(_esc(), cfg=cfg)
    assert not result.delivered and result.error


def test_telegram_requires_token_and_chat_id():
    cfg = notify.NotifyConfig(sink="telegram", token="T:K", chat_id=None)
    result = notify.escalate(_esc(), cfg=cfg)
    assert not result.delivered
    assert result.error and "chat_id" in result.error


def test_webhook_posts_the_escalation_as_json(monkeypatch):
    captured = {}

    def fake_post(url, payload):
        captured["url"], captured["payload"] = url, payload
        return 204, ""

    monkeypatch.setattr(notify, "_post_json", fake_post)
    cfg = notify.NotifyConfig(sink="webhook", url="https://hook/x")
    result = notify.escalate(_esc(pr=7, sha="deadbeef"), cfg=cfg)
    assert result.delivered
    assert captured["url"] == "https://hook/x"
    assert captured["payload"]["event"] == notify.SUPERVISE_GATE
    assert captured["payload"]["pr"] == 7


def test_hermes_sink_missing_binary_degrades(monkeypatch):
    def no_hermes(*a, **k):
        raise FileNotFoundError("hermes")

    monkeypatch.setattr(notify.subprocess, "run", no_hermes)
    cfg = notify.NotifyConfig(sink="hermes")
    result = notify.escalate(_esc(), cfg=cfg)
    assert not result.delivered
    assert result.error and "not installed" in result.error


def test_hermes_sink_nonzero_exit_is_an_error(monkeypatch):
    class R:
        returncode = 1
        stderr = "no such target"
        stdout = ""

    monkeypatch.setattr(notify.subprocess, "run", lambda *a, **k: R())
    cfg = notify.NotifyConfig(sink="hermes", target="telegram:bad")
    result = notify.escalate(_esc(), cfg=cfg)
    assert not result.delivered
    assert result.error and "no such target" in result.error


def test_hermes_sink_success_passes_target(monkeypatch):
    calls = {}

    class R:
        returncode = 0
        stderr = ""
        stdout = ""

    def fake_run(cmd, **k):
        calls["cmd"] = cmd
        return R()

    monkeypatch.setattr(notify.subprocess, "run", fake_run)
    cfg = notify.NotifyConfig(sink="hermes", target="telegram:-100:7")
    result = notify.escalate(_esc(), cfg=cfg)
    assert result.delivered
    assert "--to" in calls["cmd"] and "telegram:-100:7" in calls["cmd"]


# --------------------------------------------------------------------------- #
# Message shape + redaction
# --------------------------------------------------------------------------- #


def test_body_carries_the_essentials():
    esc = _esc(
        event=notify.DELIVERY_FAILED,
        summary="delivery blocked",
        session_id="sess-123",
        card="my-card",
        sha="abc123",
        pr=42,
        inspect="horus sessions",
    )
    text = esc.text()
    for token in ("horus-harness", "delivery blocked", "sess-123", "my-card", "abc123", "#42", "horus sessions"):
        assert token in text
    assert text.startswith("[horus] horus-harness:")


def test_success_uses_a_check_mark_not_a_warning():
    assert "✓" in _esc(event=notify.SUCCESS, summary="all clear").body()
    assert "⚠" in _esc(event=notify.DELIVERY_FAILED, summary="failed").body()


def test_render_config_redacts_the_token():
    cfg = notify.NotifyConfig(sink="telegram", token="1234567890:SECRETSECRET", chat_id="42")
    rendered = notify.render_config(cfg)
    assert "SECRETSECRET" not in rendered
    assert "chat_id: 42" in rendered


# --------------------------------------------------------------------------- #
# Pre-launch dispatch death escalates via `horus notify escalate`
# --------------------------------------------------------------------------- #


def test_dispatch_launch_failed_is_on_by_default():
    """A pre-launch death is actionable, so it escalates without opt-in — like the
    other failure events, unlike the opt-in `success` ping."""
    assert notify.DISPATCH_LAUNCH_FAILED == "dispatch-launch-failed"
    assert notify.DISPATCH_LAUNCH_FAILED in notify.DEFAULT_EVENTS


def _escalate_args(**kw):
    base = dict(event=None, card=None, unit=None, detail=None, path=".")
    base.update(kw)
    return argparse.Namespace(**base)


def test_escalate_with_no_sink_is_a_silent_noop(capsys):
    """No sink configured ⇒ behaves exactly as today: no escalation, no failure."""
    assert cli.cmd_notify_escalate(_escalate_args(card="c", unit="horus-sched-x.service")) == 0
    assert "skipped" in capsys.readouterr().out


def test_escalate_names_the_card_and_exit_code(_isolated_config, monkeypatch, capsys):
    _write(_isolated_config, '[notify]\nsink = "telegram"\ntoken = "t"\nchat_id = "1"\n')
    monkeypatch.setattr(schedule, "unit_exit_detail", lambda unit: "exit status 2, result: exit-code")
    sent = {}
    monkeypatch.setattr(notify, "_SINKS", {"telegram": lambda cfg, esc: sent.setdefault("esc", esc)})

    rc = cli.cmd_notify_escalate(_escalate_args(card="my-card", unit="horus-sched-abc.service"))
    assert rc == 0
    esc = sent["esc"]
    assert esc.event == notify.DISPATCH_LAUNCH_FAILED   # on by default, so the gate passes
    assert esc.card == "my-card"
    assert "exit status 2" in esc.summary
    assert esc.inspect == "journalctl --user -u horus-sched-abc.service"
    assert "delivered" in capsys.readouterr().out


def test_escalate_appends_an_explicit_detail(_isolated_config, monkeypatch):
    _write(_isolated_config, '[notify]\nsink = "telegram"\ntoken = "t"\nchat_id = "1"\n')
    sent = {}
    monkeypatch.setattr(notify, "_SINKS", {"telegram": lambda cfg, esc: sent.setdefault("esc", esc)})
    cli.cmd_notify_escalate(_escalate_args(card="c", detail="unrecognized arguments"))
    assert "unrecognized arguments" in sent["esc"].summary


def test_escalate_never_fails_even_when_the_sink_errors(_isolated_config, monkeypatch, capsys):
    """Best-effort by construction: a dead bot must never turn a pre-launch death into
    a second failure."""
    _write(_isolated_config, '[notify]\nsink = "telegram"\ntoken = "t"\nchat_id = "1"\n')

    def _boom(cfg, esc):
        raise RuntimeError("bot is down")

    monkeypatch.setattr(notify, "_SINKS", {"telegram": _boom})
    assert cli.cmd_notify_escalate(_escalate_args(card="c")) == 0
    assert "failed" in capsys.readouterr().out
