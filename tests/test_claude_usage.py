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


def test_findings_trigger_is_5h_only_not_weekly():
    # Weekly high but 5h low -> not actionable (closure triggers on the 5h window).
    r = cu.UsageReport(40.0, None, 95.0, None)
    findings = cu.usage_findings(threshold=90.0, report=r)
    assert findings[0].level == "ok"
    assert "weekly limit 95%" in findings[0].message  # still shown for context


def test_findings_ok_when_unavailable(monkeypatch):
    # report=None means "fetch the live one"; stub it to None so the test is hermetic
    # (otherwise a logged-in machine over its 5h limit would make this warn).
    monkeypatch.setattr(cu, "latest_usage", lambda **k: None)
    assert cu.usage_findings(threshold=90.0, report=None)[0].level == "ok"


def test_is_over_threshold_5h_only():
    assert cu.is_over_threshold(90.0, cu.UsageReport(92.0, None, 10.0, None)) is True   # 5h over
    assert cu.is_over_threshold(90.0, cu.UsageReport(40.0, None, 95.0, None)) is False  # only weekly over
    assert cu.is_over_threshold(90.0, cu.UsageReport(None, None, 99.0, None)) is False
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


def test_current_account_reads_email(tmp_path):
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({"oauthAccount": {"emailAddress": "a@b.com", "accountUuid": "uuid"}}), encoding="utf-8")
    assert cu.current_account(cfg) == "a@b.com"


def test_current_account_none_when_absent(tmp_path):
    assert cu.current_account(tmp_path / "nope.json") is None
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({"numStartups": 3}), encoding="utf-8")
    assert cu.current_account(cfg) is None


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def test_oauth_token_refreshes_and_persists_when_expired(tmp_path, monkeypatch):
    cred = tmp_path / ".credentials.json"
    cred.write_text(
        json.dumps({"claudeAiOauth": {
            "accessToken": "old", "refreshToken": "r-old",
            "expiresAt": 1_000, "subscriptionType": "pro",
        }}),
        encoding="utf-8",
    )
    payload = {"access_token": "new-access", "refresh_token": "r-new", "expires_in": 28800, "scope": "user:inference"}
    monkeypatch.setattr(cu.urllib.request, "urlopen", lambda req, timeout=0: _FakeResp(json.dumps(payload).encode()))

    assert cu._oauth_token(cred) == "new-access"

    saved = json.loads(cred.read_text(encoding="utf-8"))["claudeAiOauth"]
    assert saved["accessToken"] == "new-access"
    assert saved["refreshToken"] == "r-new"            # rotation persisted
    assert saved["expiresAt"] / 1000.0 > cu.time.time()  # no longer expired
    assert saved["subscriptionType"] == "pro"          # untouched fields preserved


def test_oauth_token_none_when_refresh_fails(tmp_path, monkeypatch):
    cred = tmp_path / ".credentials.json"
    cred.write_text(
        json.dumps({"claudeAiOauth": {"accessToken": "old", "refreshToken": "r-old", "expiresAt": 1_000}}),
        encoding="utf-8",
    )

    def boom(req, timeout=0):
        raise cu.urllib.error.HTTPError(cu.TOKEN_URL, 400, "bad", {}, None)

    monkeypatch.setattr(cu.urllib.request, "urlopen", boom)
    assert cu._oauth_token(cred) is None
    # file left untouched on failure
    assert json.loads(cred.read_text(encoding="utf-8"))["claudeAiOauth"]["accessToken"] == "old"
