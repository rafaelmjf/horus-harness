"""Cached usage snapshot substrate — TTL, negative caching, and failure paths."""

import json

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
