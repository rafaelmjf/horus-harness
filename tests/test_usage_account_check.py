"""Account-scoped `usage check --account`: explicit mapping resolution, no ambient
fallback, overseer==worker collision advisory, and window/freshness rendering."""

import argparse

from horus import claude_usage, cli, codex_usage, config, usage_snapshot
from horus.usage_snapshot import UsageSnapshot

FUTURE = "2099-01-01 00:00"
PAST = "2001-01-01 00:00"


def _args(**kw):
    base = dict(target="claude", account="work", threshold=90.0, hook=False, path=".")
    base.update(kw)
    return argparse.Namespace(**base)


def _stub(monkeypatch, *, claude_dirs=None, codex_homes=None, snapshot=None,
          ambient_claude=None, ambient_codex=None):
    """Hermetic stubs: no real config, credentials, or network reads."""
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: dict(claude_dirs or {}))
    monkeypatch.setattr(config, "load_account_codex_homes", lambda: dict(codex_homes or {}))
    monkeypatch.setattr(config, "alias_for", lambda ident: None)
    monkeypatch.setattr(claude_usage, "current_account", lambda path=None: ambient_claude)
    monkeypatch.setattr(codex_usage, "current_account", lambda home=None: ambient_codex)
    calls = []

    def fake_refresh(agent, account=None, **kwargs):
        calls.append((agent, account))
        return snapshot

    monkeypatch.setattr(usage_snapshot, "refresh_usage", fake_refresh)
    return calls


def test_claude_account_reports_windows(monkeypatch, capsys):
    calls = _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(42.0, FUTURE, 12.0, FUTURE),
    )
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert calls == [("claude", "work")]
    assert "account: work (claude; CLAUDE_CONFIG_DIR /isolated/work)" in out
    assert "live OAuth /usage read" in out
    assert "5h window: 42%" in out
    assert "weekly window: 12%" in out
    assert "overseer==worker" not in out


def test_codex_account_reports_source_and_windows(monkeypatch, capsys):
    calls = _stub(
        monkeypatch,
        codex_homes={"work-codex": "/isolated/codex"},
        snapshot=UsageSnapshot(10.0, FUTURE, None, None),
    )
    rc = cli.cmd_usage_check(_args(target="codex", account="work-codex"))
    out = capsys.readouterr().out
    assert rc == 0
    assert calls == [("codex", "work-codex")]
    assert "account: work-codex (codex; CODEX_HOME /isolated/codex)" in out
    assert "rollout telemetry" in out
    assert "weekly window: no reading" in out


def test_unknown_alias_fails_without_ambient_fallback(monkeypatch, capsys):
    calls = _stub(monkeypatch, claude_dirs={"other": "/isolated/other"})
    rc = cli.cmd_usage_check(_args(account="work"))
    out = capsys.readouterr().out
    assert rc == 2
    assert "Unknown claude account alias 'work'" in out
    assert "other" in out  # names the known isolated accounts
    assert "Refusing the ambient-login fallback" in out
    assert calls == []  # no usage read at all — never the ambient account's


def test_account_with_hook_is_rejected(monkeypatch, capsys):
    calls = _stub(monkeypatch, claude_dirs={"work": "/isolated/work"})
    rc = cli.cmd_usage_check(_args(hook=True))
    assert rc == 2
    assert "--hook" in capsys.readouterr().out
    assert calls == []


def test_claude_overseer_collision_warns(monkeypatch, capsys):
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(10.0, FUTURE),
        ambient_claude="me@example.com",  # ambient and mapped dir resolve identically
    )
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0  # advisory only — never changes the verdict
    assert "overseer==worker" in out
    assert "shares its rate-limit pool" in out


def test_codex_overseer_collision_warns(monkeypatch, capsys):
    _stub(
        monkeypatch,
        codex_homes={"cx": "/isolated/cx"},
        snapshot=UsageSnapshot(10.0, FUTURE),
        ambient_codex="acct-123",
    )
    rc = cli.cmd_usage_check(_args(target="codex", account="cx"))
    assert rc == 0
    assert "overseer==worker" in capsys.readouterr().out


def test_no_signal_is_labelled_not_silent(monkeypatch, capsys):
    _stub(monkeypatch, claude_dirs={"work": "/isolated/work"}, snapshot=None)
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "no usage signal for this account" in out


def test_stale_window_is_marked_stale(monkeypatch, capsys):
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(70.0, PAST),
    )
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0  # a stale reading is unknown capacity, not a warning
    assert "5h window: snapshot stale" in out


def test_over_threshold_exits_nonzero(monkeypatch, capsys):
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(96.0, FUTURE),
    )
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "at/over the 90% threshold" in out
