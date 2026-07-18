"""Cached usage snapshot substrate — TTL, negative caching, and failure paths."""

import json
from datetime import datetime, timezone

from horus import usage_snapshot
from horus.usage_snapshot import UsageSnapshot


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def test_live_read_is_cached_within_ttl(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fake_live(agent, account, *, timeout):
        calls["n"] += 1
        return UsageSnapshot(83.0, "2026-07-04 21:10")

    monkeypatch.setattr(usage_snapshot, "_read_live", fake_live)

    first = usage_snapshot.cached_usage("claude", now=1000.0)
    second = usage_snapshot.cached_usage("claude", now=1030.0)  # within 60s TTL
    assert first == UsageSnapshot(83.0, "2026-07-04 21:10")
    assert second == first
    assert calls["n"] == 1  # only one live read; the second was served from cache


def test_stale_cache_triggers_a_fresh_read(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fake_live(agent, account, *, timeout):
        calls["n"] += 1
        return UsageSnapshot(float(calls["n"] * 10), None)

    monkeypatch.setattr(usage_snapshot, "_read_live", fake_live)

    usage_snapshot.cached_usage("claude", now=1000.0)
    later = usage_snapshot.cached_usage("claude", now=1000.0 + usage_snapshot.CACHE_TTL + 1)
    assert calls["n"] == 2  # TTL elapsed -> refetched
    assert later.percent == 20.0


def test_negative_result_is_cached_no_repeat_fetch(tmp_path, monkeypatch):
    """A machine with no usable signal must not pay the fetch on every tool call."""
    _home(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fake_live(agent, account, *, timeout):
        calls["n"] += 1
        return None

    monkeypatch.setattr(usage_snapshot, "_read_live", fake_live)

    assert usage_snapshot.cached_usage("claude", now=1000.0) is None
    assert usage_snapshot.cached_usage("claude", now=1020.0) is None  # cached negative
    assert calls["n"] == 1


def test_live_read_never_raises_on_underlying_failure(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("network down")

    # _read_live wraps the per-agent readers; force one to explode.
    monkeypatch.setattr(usage_snapshot, "_read_claude", boom)
    assert usage_snapshot._read_live("claude", None, timeout=5.0) is None


def test_cache_key_separates_agent_and_account(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    p_default = usage_snapshot._cache_path("claude", None)
    p_work = usage_snapshot._cache_path("claude", "work")
    p_codex = usage_snapshot._cache_path("codex", None)
    assert p_default.name == "usage-claude-default.json"
    assert p_work.name == "usage-claude-work.json"
    assert p_codex.name == "usage-codex-default.json"


def test_corrupt_cache_file_is_a_miss(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    path = usage_snapshot._cache_path("claude", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    def fake_live(agent, account, *, timeout):
        return UsageSnapshot(50.0, None)

    monkeypatch.setattr(usage_snapshot, "_read_live", fake_live)
    assert usage_snapshot.cached_usage("claude", now=1000.0).percent == 50.0
    # a well-formed cache was written over the corrupt one
    assert json.loads(path.read_text(encoding="utf-8"))["ok"] is True


def test_worst_picks_more_constraining_window():
    # Weekly higher -> weekly is the more-constraining window.
    snap = UsageSnapshot(40.0, "5h-reset", 96.0, "wk-reset")
    assert snap.worst() == (96.0, "wk-reset", "weekly")
    # 5h higher -> 5h wins.
    snap = UsageSnapshot(83.0, "5h-reset", 60.0, "wk-reset")
    assert snap.worst() == (83.0, "5h-reset", "5h")


def test_worst_ignores_absent_window_and_handles_none():
    # Only 5h known.
    assert UsageSnapshot(50.0, "5h-reset").worst() == (50.0, "5h-reset", "5h")
    # Only weekly known.
    assert UsageSnapshot(None, None, 70.0, "wk-reset").worst() == (70.0, "wk-reset", "weekly")
    # Neither known -> unknown.
    assert UsageSnapshot(None, None).worst() == (None, None, "5h")


def test_without_expired_windows_drops_each_window_independently():
    now = datetime(2026, 7, 4, 12, 0).timestamp()
    snap = UsageSnapshot(100.0, "2026-07-04 11:59", 96.0, "2026-07-11 09:00")
    assert snap.without_expired_windows(now=now) == UsageSnapshot(None, None, 96.0, "2026-07-11 09:00")

    snap = UsageSnapshot(96.0, "2026-07-04 21:10", 100.0, "2026-07-04 11:59")
    assert snap.without_expired_windows(now=now) == UsageSnapshot(96.0, "2026-07-04 21:10", None, None)


def test_expired_window_includes_exact_reset_time_and_accepts_iso():
    now = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc).timestamp()
    exact = UsageSnapshot(95.0, "2026-07-04T12:00:00+00:00")
    future = UsageSnapshot(95.0, "2026-07-04T12:00:01+00:00")

    assert exact.without_expired_windows(now=now).percent is None
    assert future.without_expired_windows(now=now).percent == 95.0


def test_weekly_fields_round_trip_through_cache(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    def fake_live(agent, account, *, timeout):
        return UsageSnapshot(40.0, "5h-reset", 96.0, "wk-reset")

    monkeypatch.setattr(usage_snapshot, "_read_live", fake_live)
    usage_snapshot.cached_usage("claude", now=1000.0)  # writes cache
    # Second call served from cache must preserve both windows.
    cached = usage_snapshot.cached_usage("claude", now=1030.0)
    assert cached == UsageSnapshot(40.0, "5h-reset", 96.0, "wk-reset")
    persisted = json.loads(usage_snapshot._cache_path("claude", None).read_text(encoding="utf-8"))
    assert persisted["weekly_percent"] == 96.0
    assert persisted["weekly_resets_at"] == "wk-reset"


def test_legacy_cache_without_weekly_fields_loads(tmp_path, monkeypatch):
    """A cache written before multi-window support has no weekly keys -> weekly None."""
    _home(tmp_path, monkeypatch)
    path = usage_snapshot._cache_path("claude", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ts": 1000.0, "ok": True, "percent": 50.0, "resets_at": "5h-reset"}), encoding="utf-8")
    snap = usage_snapshot.cached_usage("claude", now=1010.0)
    assert snap == UsageSnapshot(50.0, "5h-reset", None, None)


def test_claude_reader_carries_weekly_window(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage

    def fake_latest(*, cred_path=None, timeout=8.0):
        return claude_usage.UsageReport(40.0, "2026-07-04T21:10:00Z", 96.0, "2026-07-11T09:00:00Z")

    monkeypatch.setattr(claude_usage, "latest_usage", fake_latest)
    snap = usage_snapshot._read_claude(None, timeout=5.0)
    assert snap.percent == 40.0
    assert snap.weekly_percent == 96.0
    assert snap.weekly_resets_at is not None  # formatted, not raw ISO


def test_codex_reader_carries_secondary_window(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import codex_usage

    report = codex_usage.UsageReport(
        rollout=tmp_path / "r.jsonl", timestamp="2026-07-04T21:10:00Z",
        context_tokens=1, context_window=100, context_percent=1.0,
        primary_percent=40.0, primary_resets_at=1, secondary_percent=88.0, secondary_resets_at=2,
    )
    monkeypatch.setattr(codex_usage, "latest_account_usage", lambda home=None: report)
    snap = usage_snapshot._read_codex(None)
    assert snap.percent == 40.0
    assert snap.weekly_percent == 88.0


def test_claude_reader_uses_account_credentials_dir(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config

    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"work": str(tmp_path / "wcfg")})
    seen = {}

    def fake_latest(*, cred_path=None, timeout=8.0):
        seen["cred_path"] = cred_path
        return claude_usage.UsageReport(90.0, "2026-07-04T21:10:00Z", None, None)

    monkeypatch.setattr(claude_usage, "latest_usage", fake_latest)
    snap = usage_snapshot._read_claude("work", timeout=5.0)
    assert snap.percent == 90.0
    assert seen["cred_path"] == tmp_path / "wcfg" / ".credentials.json"


# --- all-accounts roll-up (fleet capacity glance / phone `usage` verb) --------


def test_all_account_targets_lists_configured_aliases_or_default(monkeypatch):
    from horus import config
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"work": "/x/w", "personal": "/x/p"})
    monkeypatch.setattr(config, "load_account_codex_homes", lambda: {})
    targets = usage_snapshot.all_account_targets()
    # every configured Claude alias (sorted), plus the Codex default when none set
    assert ("claude", "personal") in targets and ("claude", "work") in targets
    assert ("codex", None) in targets


def test_all_accounts_usage_reads_each_target_and_blanks_expired(monkeypatch):
    from horus import config
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"work": "/x/w"})
    monkeypatch.setattr(config, "load_account_codex_homes", lambda: {"main": "/x/c"})
    reads: list[tuple[str, str | None]] = []

    def fake_cached(agent, account=None, **k):
        reads.append((agent, account))
        return UsageSnapshot(42.0, None, 10.0, None)

    monkeypatch.setattr(usage_snapshot, "cached_usage", fake_cached)
    rows = usage_snapshot.all_accounts_usage(now=1000.0)
    assert {(r.agent, r.account) for r in rows} == {("claude", "work"), ("codex", "main")}
    assert ("claude", "work") in reads and ("codex", "main") in reads
    assert all(r.snapshot is not None for r in rows)


def test_all_accounts_usage_read_only_never_hits_network(monkeypatch):
    from horus import config
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"work": "/x/w"})
    monkeypatch.setattr(config, "load_account_codex_homes", lambda: {})

    def _boom(*a, **k):
        raise AssertionError("read_only must not do a live/cached network read")

    monkeypatch.setattr(usage_snapshot, "cached_usage", _boom)
    monkeypatch.setattr(usage_snapshot, "read_cache_only", lambda agent, account=None: UsageSnapshot(5.0, None))
    rows = usage_snapshot.all_accounts_usage(read_only=True)
    assert [(r.agent, r.account) for r in rows] == [("claude", "work"), ("codex", "default")]


def test_render_all_accounts_shows_percents_and_unknown():
    rows = [
        usage_snapshot.AccountUsage("claude", "work", UsageSnapshot(30.0, "9pm", 12.0, "Mon")),
        usage_snapshot.AccountUsage("codex", "default", None),
    ]
    out = usage_snapshot.render_all_accounts(rows)
    assert "claude/work" in out and "30%" in out and "weekly 12%" in out
    assert "codex/default  unknown" in out
