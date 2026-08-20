"""Account-scoped `usage check --account`: explicit mapping resolution, no ambient
fallback, overseer==worker collision advisory, and window/freshness rendering.

The check reads through the cache rather than forcing a live poll: a reading the
statusline already pushed is better evidence than a fresh poll of the experimental
OAuth endpoint, which 429s under any real polling. So these stub `cached_usage`
(what the check asks for) plus `read_cache_entry` (the provenance/age it renders).
"""

import argparse
import json
import time

from horus import claude_usage, cli, codex_usage, config, usage_snapshot
from horus.usage_snapshot import UsageSnapshot

FUTURE = "2099-01-01 00:00"
PAST = "2001-01-01 00:00"
_UNSET = object()


def _args(**kw):
    base = dict(target="claude", account="work", threshold=90.0, hook=False, path=".")
    base.update(kw)
    return argparse.Namespace(**base)


def _stub(monkeypatch, *, claude_dirs=None, codex_homes=None, snapshot=None,
          ambient_claude=None, ambient_codex=None, source=_UNSET, age=0.0,
          last_reading=_UNSET, session_claude=None, requested_claude=None):
    """Hermetic stubs: no real config, credentials, or network reads.

    ``snapshot`` is what a fresh read yields (``None`` = nothing fresh);
    ``last_reading`` is what remains cached at any age, for the fallback path.
    """
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: dict(claude_dirs or {}))
    monkeypatch.setattr(config, "load_account_codex_homes", lambda: dict(codex_homes or {}))
    monkeypatch.setattr(config, "alias_for", lambda ident: None)
    monkeypatch.setattr(claude_usage, "current_account", lambda path=None: ambient_claude)
    monkeypatch.setattr(
        claude_usage, "session_identity",
        lambda: session_claude or claude_usage.Identity(None, None),
    )
    monkeypatch.setattr(
        claude_usage, "identity_for_config",
        lambda path=None: requested_claude or claude_usage.Identity(None, None),
    )
    monkeypatch.setattr(codex_usage, "current_account", lambda home=None: ambient_codex)
    calls = []

    def fake_cached(agent, account=None, **kwargs):
        calls.append((agent, account))
        return snapshot

    held = snapshot if last_reading is _UNSET else last_reading
    resolved_source = (
        (usage_snapshot.SOURCE_OAUTH if (codex_homes is None) else usage_snapshot.SOURCE_ROLLOUT)
        if source is _UNSET else source
    )

    def fake_entry(agent, account=None):
        if held is None:
            return None
        return usage_snapshot._Cached(held, resolved_source, time.time() - age)

    monkeypatch.setattr(usage_snapshot, "cached_usage", fake_cached)
    monkeypatch.setattr(usage_snapshot, "read_cache_entry", fake_entry)
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
    assert "unknown account 'work'" in out
    assert "claude-other" in out  # names the known isolated accounts, canonically
    assert "Refusing the ambient-login fallback" in out
    assert calls == []  # no usage read at all — never the ambient account's


def test_account_with_hook_is_rejected(monkeypatch, capsys):
    calls = _stub(monkeypatch, claude_dirs={"work": "/isolated/work"})
    rc = cli.cmd_usage_check(_args(hook=True))
    assert rc == 2
    assert "--hook" in capsys.readouterr().out
    assert calls == []


def test_claude_overseer_collision_warns(monkeypatch, capsys):
    identity = claude_usage.Identity("acct-me", "org-me")
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(10.0, FUTURE),
        ambient_claude="someone-else@example.com",  # ambient login is irrelevant
        session_claude=identity,
        requested_claude=identity,
    )
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0  # advisory only — never changes the verdict
    assert "overseer==worker" in out
    assert "shares its rate-limit pool" in out


def test_claude_overseer_collision_does_not_infer_from_ambient_login(monkeypatch, capsys):
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(10.0, FUTURE),
        ambient_claude="same-as-requested@example.com",
        session_claude=claude_usage.Identity("acct-session", "org-shared"),
        requested_claude=claude_usage.Identity("acct-requested", "org-shared"),
    )
    rc = cli.cmd_usage_check(_args())
    assert rc == 0
    assert "overseer==worker" not in capsys.readouterr().out


def test_default_claude_check_reads_unregistered_desktop_session_history(
    tmp_path, monkeypatch, capsys
):
    """CLI-shaped acceptance: no registered alias and no usable ambient login, but
    the measured desktop session org has a sampled local reading with an honest age."""
    support = tmp_path / "Claude"
    session_id = "local-session"
    account = "acct-session"
    org = "org-session"
    session_dir = support / "claude-code-sessions" / account / org
    session_dir.mkdir(parents=True)
    (session_dir / f"{session_id}.json").write_text("{}", encoding="utf-8")

    base = 1_800_000_000.0
    captured = base + 4 * 3600
    samples = [
        {"t": int(base * 1000), "org": org, "u": {"fh": 90, "sd": 80}},
        {"t": int((base + 300) * 1000), "org": org, "u": {"fh": 0, "sd": 0}},
        {"t": int(captured * 1000), "org": org, "u": {"fh": 42, "sd": 12}},
    ]
    (support / "plan-usage-history.json").write_text(
        json.dumps({"version": 2, "samples": samples}), encoding="utf-8"
    )

    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "claude-desktop")
    monkeypatch.setenv("CLAUDE_CODE_HOST_SESSION_ID", session_id)
    monkeypatch.setattr(claude_usage, "desktop_support_dir", lambda: support)
    monkeypatch.setattr(
        claude_usage, "identity_for_config", lambda path=None: claude_usage.Identity(None, None)
    )
    monkeypatch.setattr(config, "load_account_config_dirs", dict)
    monkeypatch.setattr(claude_usage.time, "time", lambda: captured + 60)
    monkeypatch.setattr(
        claude_usage, "fetch_usage",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not fetch ambient usage")),
    )

    rc = cli.cmd_usage_check(_args(account=None, threshold=90.0))
    out = capsys.readouterr().out
    assert rc == 0
    assert "desktop app record 60s old" in out
    assert "5h limit 42%" in out
    assert "weekly limit 12%" in out


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
    _stub(monkeypatch, claude_dirs={"work": "/isolated/work"}, snapshot=None, last_reading=None)
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "no usage reading available" in out


def test_no_signal_does_not_assert_a_cause_it_never_diagnosed(monkeypatch, capsys):
    """It used to say "missing/expired credentials, offline, or no telemetry yet" —
    naming only causes that were not true. The live failure here was rate limiting,
    which sent the owner hunting for a credentials problem that did not exist."""
    _stub(monkeypatch, claude_dirs={"work": "/isolated/work"}, snapshot=None, last_reading=None)
    cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert "missing/expired credentials" not in out
    assert "Cause not diagnosed here" in out
    assert "horus usage record" in out  # points at the surface that cannot be limited


def test_a_failed_fresh_read_falls_back_to_the_last_reading_with_its_age(monkeypatch, capsys):
    """A previous reading is better evidence than claiming to know nothing — but it
    must never be presented as current."""
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=None,
        last_reading=UsageSnapshot(64.0, FUTURE),
        source=usage_snapshot.SOURCE_STATUSLINE,
        age=4200,
    )
    rc = cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "5h window: 64%" in out
    assert "statusline" in out and "70m ago" in out
    assert "a fresh read failed" in out


def test_a_statusline_reading_is_named_as_such(monkeypatch, capsys):
    _stub(
        monkeypatch,
        claude_dirs={"work": "/isolated/work"},
        snapshot=UsageSnapshot(42.0, FUTURE),
        source=usage_snapshot.SOURCE_STATUSLINE,
    )
    cli.cmd_usage_check(_args())
    out = capsys.readouterr().out
    assert "recorded from Claude Code's statusline" in out
    assert "OAuth" not in out  # the endpoint was never consulted


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
