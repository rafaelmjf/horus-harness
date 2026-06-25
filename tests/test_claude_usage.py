"""Tests for the Claude OAuth usage signal (no network: fetch is monkeypatched)."""

import json

from horus import claude_usage as cu

_PAYLOAD = {
    "five_hour": {"utilization": 92.0, "resets_at": "2026-06-25T17:50:00+00:00"},
    "seven_day": {"utilization": 50.0, "resets_at": "2026-06-28T21:00:00+00:00"},
}


def test_latest_usage_parses_windows(monkeypatch):
    monkeypatch.setattr(cu, "fetch_usage", lambda **k: _PAYLOAD)
    r = cu.latest_usage()
    assert r.five_hour_percent == 92.0 and r.seven_day_percent == 50.0
    assert r.five_hour_resets_at.startswith("2026-06-25")


def test_latest_usage_none_when_no_payload(monkeypatch):
    monkeypatch.setattr(cu, "fetch_usage", lambda **k: None)
    assert cu.latest_usage() is None


def test_findings_warn_over_threshold():
    r = cu.UsageReport(92.0, "2026-06-25T17:50:00+00:00", 50.0, "2026-06-28T21:00:00+00:00")
    findings = cu.usage_findings(threshold=90.0, report=r)
    assert findings[0].level == "warn"
    assert "5h limit 92%" in findings[0].message


def test_findings_ok_under_threshold():
    r = cu.UsageReport(37.0, None, 50.0, None)
    findings = cu.usage_findings(threshold=90.0, report=r)
    assert findings[0].level == "ok"


def test_findings_ok_when_unavailable():
    assert cu.usage_findings(threshold=90.0, report=None)[0].level == "ok"


def test_is_over_threshold():
    r = cu.UsageReport(37.0, None, 95.0, None)
    assert cu.is_over_threshold(90.0, r) is True   # weekly over
    assert cu.is_over_threshold(96.0, r) is False
    assert cu.is_over_threshold(90.0, None) is False


def test_oauth_token_reads_valid(tmp_path):
    cred = tmp_path / ".credentials.json"
    cred.write_text(json.dumps({"claudeAiOauth": {"accessToken": "tok123", "expiresAt": 9_999_999_999_000}}), encoding="utf-8")
    assert cu._oauth_token(cred) == "tok123"


def test_oauth_token_none_when_expired(tmp_path):
    cred = tmp_path / ".credentials.json"
    cred.write_text(json.dumps({"claudeAiOauth": {"accessToken": "tok", "expiresAt": 1_000}}), encoding="utf-8")
    assert cu._oauth_token(cred) is None


def test_oauth_token_none_when_missing(tmp_path):
    assert cu._oauth_token(tmp_path / "nope.json") is None
