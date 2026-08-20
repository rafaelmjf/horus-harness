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

    def fake_latest(*, cred_path=None, timeout=8.0, require_session_attribution=True):
        return claude_usage.UsageReport(40.0, "2026-07-04T21:10:00Z", 96.0, "2026-07-11T09:00:00Z")

    monkeypatch.setattr(claude_usage, "latest_usage", fake_latest)
    snap = usage_snapshot._read_claude(None, timeout=5.0)
    assert snap.percent == 40.0
    assert snap.weekly_percent == 96.0
    assert snap.weekly_resets_at is not None  # formatted, not raw ISO


def test_claude_reader_carries_desktop_capture_time_and_source(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage

    def fake_latest(*, cred_path=None, timeout=8.0, require_session_attribution=True):
        return claude_usage.UsageReport(
            40.0, "2099-01-01T00:00:00Z", 20.0, "2099-01-02T00:00:00Z", 900.0
        )

    monkeypatch.setattr(claude_usage, "latest_usage", fake_latest)
    snap = usage_snapshot.cached_usage("claude", now=1000.0)
    assert snap.captured_at == 900.0
    entry = usage_snapshot.read_cache_entry("claude")
    assert entry is not None
    assert entry.source == usage_snapshot.SOURCE_DESKTOP_HISTORY


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

    def fake_latest(*, cred_path=None, timeout=8.0, require_session_attribution=True):
        seen["cred_path"] = cred_path
        seen["require_session_attribution"] = require_session_attribution
        return claude_usage.UsageReport(90.0, "2026-07-04T21:10:00Z", None, None)

    monkeypatch.setattr(claude_usage, "latest_usage", fake_latest)
    snap = usage_snapshot._read_claude("work", timeout=5.0)
    assert snap.percent == 90.0
    assert seen["cred_path"] == tmp_path / "wcfg" / ".credentials.json"
    # The isolated dir's token IS this account's, so the reading is that account's by
    # construction and no session-attribution claim is being made.
    assert seen["require_session_attribution"] is False


def test_claude_reader_keeps_the_attribution_check_on_the_ambient_fallback(tmp_path, monkeypatch):
    """No isolated dir means ambient credentials — the path that used to pass another
    account's figure off as the session's, so the check must stay on there."""
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config

    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {})
    seen = {}

    def fake_latest(*, cred_path=None, timeout=8.0, require_session_attribution=True):
        seen["require_session_attribution"] = require_session_attribution
        return claude_usage.UsageReport(90.0, "2026-07-04T21:10:00Z", None, None)

    monkeypatch.setattr(claude_usage, "latest_usage", fake_latest)
    usage_snapshot._read_claude("work", timeout=5.0)
    assert seen["require_session_attribution"] is True


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


def test_codex_reader_carries_the_rollout_capture_time_not_now(tmp_path, monkeypatch):
    """Codex reports capacity only when it takes a turn, so an idle account's newest
    rollout can be hours old while this read happens right now. Presenting that as
    current is what let a stale reading hard-refuse a valid dispatch."""
    _home(tmp_path, monkeypatch)
    from horus import codex_usage

    report = codex_usage.UsageReport(
        rollout=tmp_path / "r.jsonl", timestamp="2026-07-04T21:10:00Z",
        context_tokens=1, context_window=100, context_percent=1.0,
        primary_percent=99.0, primary_resets_at=1, secondary_percent=None, secondary_resets_at=None,
    )
    monkeypatch.setattr(codex_usage, "latest_account_usage", lambda home=None: report)

    snap = usage_snapshot._read_codex(None)

    from datetime import datetime, timezone
    expected = datetime(2026, 7, 4, 21, 10, tzinfo=timezone.utc).timestamp()
    assert snap.captured_at == expected
    # An hour later that reading can still warn, but can no longer refuse.
    assert not snap.is_authoritative_for_refusal(now=expected + 3 * 3600)
    assert snap.is_authoritative_for_refusal(now=expected + 60)


def test_capture_time_round_trips_through_the_cache(tmp_path, monkeypatch):
    """Without this the refusal gate would trust a cache hit as freshly captured."""
    _home(tmp_path, monkeypatch)
    path = tmp_path / "usage-cache.json"
    captured = 1_780_000_000.0

    usage_snapshot._write_cache(
        path, UsageSnapshot(99.0, "2026-07-04 21:10", captured_at=captured), now=captured + 5,
    )
    loaded = usage_snapshot._load_cache(path, ttl=None, now=captured + 5)

    assert loaded.snapshot.captured_at == captured


def test_a_cache_written_before_capture_tracking_reads_as_unknown_age(tmp_path, monkeypatch):
    """Back-compat: an old cache file has no `captured_at`, which must read as "the
    source didn't say" and keep the pre-existing refusal behavior."""
    _home(tmp_path, monkeypatch)
    path = tmp_path / "usage-cache.json"
    path.write_text(
        '{"ts": 1780000000, "ok": true, "source": "rollout", "percent": 99.0,'
        ' "resets_at": "2026-07-04 21:10"}',
        encoding="utf-8",
    )

    snap = usage_snapshot._load_cache(path, ttl=None, now=1_780_000_005).snapshot

    assert snap.captured_at is None
    assert snap.reading_age_seconds(now=1_780_000_005) is None
    assert snap.is_authoritative_for_refusal(now=1_780_000_005)


def test_expiring_a_window_preserves_the_capture_time(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = 1_780_000_000.0
    snap = UsageSnapshot(99.0, "2020-01-01 00:00", 50.0, "2099-01-01 00:00", captured)

    fresh = snap.without_expired_windows(now=captured)

    assert fresh.percent is None          # the past-reset window was blanked
    assert fresh.captured_at == captured  # ...without losing how old the reading is
