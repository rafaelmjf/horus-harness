"""Tests for recording the usage reading Claude Code pushes to a statusline.

Claude Code hands a `rate_limits` block to every statusLine render — the official,
documented surface. Horus previously ignored it and polled the experimental OAuth
/usage endpoint instead, which answers 429 under any real polling and then reports
the failure as "missing/expired credentials".
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time

import pytest

from horus import cli, config, usage_snapshot


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "horus-home")
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return tmp_path


def _payload(five=23.5, seven=41.2, *, five_reset=4102444800, seven_reset=4102531200):
    """The documented statusline shape: percentages 0-100, resets in epoch SECONDS."""
    limits = {}
    if five is not None:
        limits["five_hour"] = {"used_percentage": five, "resets_at": five_reset}
    if seven is not None:
        limits["seven_day"] = {"used_percentage": seven, "resets_at": seven_reset}
    return {"cwd": "/x", "model": {"display_name": "Opus"}, "rate_limits": limits}


# --- parsing the pushed payload ---------------------------------------------


def test_reads_both_windows_from_the_statusline_payload():
    snap = usage_snapshot.snapshot_from_claude_statusline(_payload())
    assert snap.percent == 23.5
    assert snap.weekly_percent == 41.2
    # Epoch seconds are rendered into the same reset format the rest of the module
    # parses back out, so `without_expired_windows` keeps working on these.
    assert snap.resets_at is not None
    assert usage_snapshot._reset_timestamp(snap.resets_at) == pytest.approx(4102444800, abs=60)


def test_missing_rate_limits_is_normal_not_an_error():
    """Absent on non-Pro/Max plans and until a session's first API response."""
    assert usage_snapshot.snapshot_from_claude_statusline({"cwd": "/x"}) is None
    assert usage_snapshot.snapshot_from_claude_statusline({"rate_limits": {}}) is None
    assert usage_snapshot.snapshot_from_claude_statusline("not a dict") is None
    assert usage_snapshot.snapshot_from_claude_statusline(None) is None


def test_one_window_alone_still_records():
    assert usage_snapshot.snapshot_from_claude_statusline(_payload(seven=None)).percent == 23.5
    assert usage_snapshot.snapshot_from_claude_statusline(_payload(five=None)).weekly_percent == 41.2


def test_malformed_windows_are_ignored_not_fatal():
    for limits in ({"five_hour": "nope"}, {"five_hour": {"used_percentage": "x"}},
                   {"five_hour": {"used_percentage": True}}):
        assert usage_snapshot.snapshot_from_claude_statusline({"rate_limits": limits}) is None


def test_a_bad_reset_keeps_the_percent():
    snap = usage_snapshot.snapshot_from_claude_statusline(
        {"rate_limits": {"five_hour": {"used_percentage": 12, "resets_at": "garbage"}}}
    )
    assert snap.percent == 12 and snap.resets_at is None


# --- recording into the cache every consumer already reads -------------------


def test_recorded_reading_is_served_to_existing_consumers_without_a_live_read(monkeypatch):
    """The whole point: a pushed reading satisfies the TTL, so nothing calls the
    rate-limited endpoint."""
    def _explode(*a, **k):
        raise AssertionError("a recorded reading must not trigger a live read")

    monkeypatch.setattr(usage_snapshot, "_read_live", _explode)
    snap = usage_snapshot.snapshot_from_claude_statusline(_payload())
    usage_snapshot.record_snapshot("claude", "personal", snap)
    served = usage_snapshot.cached_usage("claude", "personal")
    assert served.percent == 23.5 and served.weekly_percent == 41.2


def test_record_writes_the_same_file_a_live_read_would():
    snap = usage_snapshot.snapshot_from_claude_statusline(_payload())
    path = usage_snapshot.record_snapshot("claude", "personal", snap)
    assert path == usage_snapshot._cache_path("claude", "personal")
    assert json.loads(path.read_text())["ok"] is True


def test_recording_is_scoped_per_account():
    usage_snapshot.record_snapshot(
        "claude", "personal", usage_snapshot.snapshot_from_claude_statusline(_payload(five=10))
    )
    usage_snapshot.record_snapshot(
        "claude", "work", usage_snapshot.snapshot_from_claude_statusline(_payload(five=90))
    )
    assert usage_snapshot.read_cache_only("claude", "personal").percent == 10
    assert usage_snapshot.read_cache_only("claude", "work").percent == 90


# --- the CLI, as a statusline actually invokes it ----------------------------


def _run_record(monkeypatch, stdin_text, **overrides):
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    args = argparse.Namespace(account=None, verbose=False)
    for k, v in overrides.items():
        setattr(args, k, v)
    return cli.cmd_usage_record(args)


def test_cli_records_from_stdin(monkeypatch):
    assert _run_record(monkeypatch, json.dumps(_payload()), account="personal") == 0
    assert usage_snapshot.read_cache_only("claude", "personal").percent == 23.5


def test_cli_never_breaks_a_statusline(monkeypatch, capsys):
    """It runs inside the owner's statusline: a non-zero exit or stray stdout
    would corrupt what they see, so every bad input is silently a no-op."""
    for text in ("", "not json at all", "[]", json.dumps({"cwd": "/x"})):
        assert _run_record(monkeypatch, text) == 0
        assert capsys.readouterr().out == ""


def test_cli_resolves_the_account_from_the_ambient_config_dir(monkeypatch, tmp_path):
    """The payload names no account, but the statusline inherits the agent's env."""
    acct_dir = tmp_path / "accounts" / "claude-personal"
    acct_dir.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(acct_dir))
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"personal": str(acct_dir)})
    assert _run_record(monkeypatch, json.dumps(_payload())) == 0
    assert usage_snapshot.read_cache_only("claude", "personal").percent == 23.5


def test_an_unmapped_config_dir_records_against_the_default_key(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "somewhere-else"))
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"personal": "/x/personal"})
    assert _run_record(monkeypatch, json.dumps(_payload())) == 0
    assert usage_snapshot.read_cache_only("claude", None).percent == 23.5


def test_account_flag_beats_the_ambient_dir(monkeypatch, tmp_path):
    acct_dir = tmp_path / "claude-personal"
    acct_dir.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(acct_dir))
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {"personal": str(acct_dir)})
    assert _run_record(monkeypatch, json.dumps(_payload()), account="work") == 0
    assert usage_snapshot.read_cache_only("claude", "work").percent == 23.5
    assert usage_snapshot.read_cache_only("claude", "personal") is None


def test_verbose_reports_what_it_recorded(monkeypatch, capsys):
    _run_record(monkeypatch, json.dumps(_payload()), account="personal", verbose=True)
    out = capsys.readouterr().out
    assert "personal" in out and "weekly 41%" in out


def test_recorded_reading_ages_out_like_any_other(monkeypatch):
    """A pushed reading is not privileged: a passed reset still means no capacity
    evidence, and a stale entry still yields to a live read."""
    snap = usage_snapshot.snapshot_from_claude_statusline(_payload())
    now = time.time()
    usage_snapshot.record_snapshot("claude", "personal", snap, now=now - 3600)
    monkeypatch.setattr(usage_snapshot, "_read_live", lambda *a, **k: None)
    assert usage_snapshot.cached_usage("claude", "personal", now=now) is None


# --- provenance and age: a number must say where it came from and how old ----


def test_cache_entry_carries_source_and_age():
    snap = usage_snapshot.snapshot_from_claude_statusline(_payload())
    usage_snapshot.record_snapshot("claude", "personal", snap, now=time.time() - 120)
    entry = usage_snapshot.read_cache_entry("claude", "personal")
    assert entry.source == usage_snapshot.SOURCE_STATUSLINE
    assert 110 < entry.age_seconds() < 130


def test_a_live_read_is_recorded_as_such(monkeypatch):
    monkeypatch.setattr(
        usage_snapshot, "_read_live", lambda *a, **k: usage_snapshot.UsageSnapshot(5.0, None)
    )
    usage_snapshot.cached_usage("claude", "personal")
    assert usage_snapshot.read_cache_entry("claude", "personal").source == usage_snapshot.SOURCE_OAUTH


def test_codex_live_reads_are_labelled_rollout(monkeypatch):
    monkeypatch.setattr(
        usage_snapshot, "_read_live", lambda *a, **k: usage_snapshot.UsageSnapshot(5.0, None)
    )
    usage_snapshot.cached_usage("codex", "personal")
    assert usage_snapshot.read_cache_entry("codex", "personal").source == usage_snapshot.SOURCE_ROLLOUT


def test_source_labels_name_the_surface():
    assert "statusline" in usage_snapshot.source_label(usage_snapshot.SOURCE_STATUSLINE)
    assert "OAuth" in usage_snapshot.source_label(usage_snapshot.SOURCE_OAUTH)
    assert usage_snapshot.source_label("something-new") == "unknown source"


def test_a_cache_written_before_provenance_reads_as_unknown_not_a_crash(tmp_path):
    """Forward/backward-readable, like the session registry."""
    path = usage_snapshot._cache_path("claude", "personal")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ts": time.time(), "ok": True, "percent": 12.0}))
    entry = usage_snapshot.read_cache_entry("claude", "personal")
    assert entry.snapshot.percent == 12.0
    assert entry.source == usage_snapshot.SOURCE_UNKNOWN


def test_age_phrase_reads_naturally():
    assert cli._age_phrase(3) == "just now"
    assert cli._age_phrase(45) == "45s ago"
    assert cli._age_phrase(600) == "10m ago"
    assert cli._age_phrase(7200) == "2h ago"
    assert cli._age_phrase(200000) == "2d ago"
    assert cli._age_phrase(None) == "age unknown"
