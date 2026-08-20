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


def test_config_paths_respect_claude_config_dir(monkeypatch, tmp_path):
    acct = tmp_path / "acct"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(acct))
    assert cu.config_path() == acct / ".claude.json"
    assert cu.credentials_path() == acct / ".credentials.json"


def test_config_paths_fall_back_to_home(monkeypatch):
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert cu.config_path().name == ".claude.json"
    assert cu.credentials_path().parts[-2:] == (".claude", ".credentials.json")


def test_current_account_reads_email(tmp_path):
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({"oauthAccount": {"emailAddress": "a@b.com", "accountUuid": "uuid"}}), encoding="utf-8")
    assert cu.current_account(cfg) == "a@b.com"


def test_current_account_none_when_absent(tmp_path):
    assert cu.current_account(tmp_path / "nope.json") is None
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({"numStartups": 3}), encoding="utf-8")
    assert cu.current_account(cfg) is None


# --------------------------------------------------------------------------- #
# Account attribution
# --------------------------------------------------------------------------- #
# Built from fixtures, not from the endpoint: the defect is that a *valid* token for
# the wrong account produces a confident number, so the regression must reproduce the
# mismatch (two orgs in the desktop session store, credentials resolving to the other
# one) without depending on the undocumented /usage endpoint being reachable or on
# which account the machine running the suite happens to be logged into.

_WORK_ORG = "39b76ea7-d63a-4c14-aec5-e738e3297c27"
_PERSONAL_ORG = "ceeaba38-4417-4a3e-bfda-c4c22aaa6f6f"
_HOST_SESSION = "local_8e3be0b3-59b8-4d77-9666-47177c3bc140"


def _desktop_session(support_dir, *, org: str, session_id: str = _HOST_SESSION, account: str = "acct-uuid"):
    """File a session the way the desktop app does: <accountUuid>/<orgUuid>/<id>.json."""
    d = support_dir / "claude-code-sessions" / account / org
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{session_id}.json").write_text("{}", encoding="utf-8")
    return d


def _login(dir_path, org: str, account: str | None = None):
    """A Claude login config carrying the identity its credentials report for."""
    dir_path.mkdir(parents=True, exist_ok=True)
    oauth = {"emailAddress": "a@b.com", "organizationUuid": org}
    if account:
        oauth["accountUuid"] = account
    cfg = dir_path / ".claude.json"
    cfg.write_text(json.dumps({"oauthAccount": oauth}), encoding="utf-8")
    return cfg


def _desktop_session_env(monkeypatch, support_dir):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "claude-desktop")
    monkeypatch.setenv("CLAUDE_CODE_HOST_SESSION_ID", _HOST_SESSION)
    monkeypatch.setattr(cu, "desktop_support_dir", lambda: support_dir)


def _write_history(support_dir, samples):
    (support_dir / "plan-usage-history.json").write_text(
        json.dumps({"version": 2, "samples": samples}), encoding="utf-8"
    )


def _sample(ts, org, *, fh, sd):
    return {"t": int(ts * 1000), "org": org, "u": {"fh": fh, "sd": sd}}


def test_session_org_measured_from_desktop_session_store(monkeypatch, tmp_path):
    _desktop_session(tmp_path, org=_PERSONAL_ORG)
    _desktop_session(tmp_path, org=_WORK_ORG, session_id="local_other", account="other-acct")
    _desktop_session_env(monkeypatch, tmp_path)
    assert cu.session_org() == _PERSONAL_ORG


def test_session_org_none_when_session_not_filed(monkeypatch, tmp_path):
    _desktop_session(tmp_path, org=_WORK_ORG, session_id="local_someone_else")
    _desktop_session_env(monkeypatch, tmp_path)
    assert cu.session_org() is None


def test_desktop_usage_report_is_org_scoped_and_carries_capture_time(tmp_path):
    base = 1_800_000_000.0
    captured = base + 4 * 3600
    _write_history(tmp_path, [
        _sample(base, _PERSONAL_ORG, fh=90, sd=80),
        _sample(base + 300, _PERSONAL_ORG, fh=0, sd=0),  # observed reset
        _sample(captured, _PERSONAL_ORG, fh=42, sd=12),
        _sample(captured + 30, _WORK_ORG, fh=99, sd=99),
    ])

    report = cu.desktop_usage_report(
        identity=cu.Identity("acct-mine", _PERSONAL_ORG),
        support_dir=tmp_path,
        now=captured + 60,
    )
    assert report is not None
    assert report.five_hour_percent == 42
    assert report.seven_day_percent == 12
    assert report.captured_at == captured
    assert report.five_hour_resets_at is not None
    assert report.seven_day_resets_at is not None


def test_desktop_usage_report_expires_a_sample_that_predates_its_window_reset(tmp_path):
    base = 1_800_000_000.0
    weekly = 7 * 24 * 60 * 60
    captured = base + weekly - 60
    _write_history(tmp_path, [
        _sample(base, _PERSONAL_ORG, fh=90, sd=80),
        _sample(base + 300, _PERSONAL_ORG, fh=0, sd=0),
        _sample(captured - 3600, _PERSONAL_ORG, fh=90, sd=84),
        _sample(captured - 3300, _PERSONAL_ORG, fh=0, sd=84),
        _sample(captured, _PERSONAL_ORG, fh=35, sd=85),
    ])

    report = cu.desktop_usage_report(
        identity=cu.Identity("acct-mine", _PERSONAL_ORG),
        support_dir=tmp_path,
        now=base + weekly + 10,
    )
    assert report is not None
    assert report.five_hour_percent == 35
    assert report.seven_day_percent is None
    assert report.seven_day_resets_at is None


def test_desktop_usage_report_refuses_a_window_without_reset_evidence(tmp_path):
    now = 1_800_000_000.0
    _write_history(tmp_path, [_sample(now - 60, _PERSONAL_ORG, fh=42, sd=12)])
    assert cu.desktop_usage_report(
        identity=cu.Identity("acct-mine", _PERSONAL_ORG), support_dir=tmp_path, now=now
    ) is None


def test_attribution_refuses_when_token_belongs_to_another_account(monkeypatch, tmp_path):
    """The measured defect: desktop session on one org, ambient CLI login on another."""
    _desktop_session(tmp_path, org=_PERSONAL_ORG)
    _desktop_session_env(monkeypatch, tmp_path)
    cred = tmp_path / "cli" / ".credentials.json"
    _login(tmp_path / "cli", _WORK_ORG)

    attribution = cu.check_attribution(cred)
    assert attribution.ok is False
    assert attribution.session.org_uuid == _PERSONAL_ORG
    assert attribution.reading.org_uuid == _WORK_ORG
    assert "different account" in attribution.reason


def test_attribution_separates_two_members_of_one_team_org(monkeypatch, tmp_path):
    """A ``claude_team`` org holds several accounts, each with its own limit pool, so
    matching on the org alone would call two colleagues the same account."""
    _desktop_session(tmp_path, org=_WORK_ORG, account="acct-mine")
    _desktop_session_env(monkeypatch, tmp_path)
    cred = tmp_path / "colleague" / ".credentials.json"
    _login(tmp_path / "colleague", _WORK_ORG, account="acct-theirs")

    attribution = cu.check_attribution(cred)
    assert attribution.ok is False
    assert "different account" in attribution.reason

    _login(tmp_path / "colleague", _WORK_ORG, account="acct-mine")
    assert cu.check_attribution(cred).ok is True


def test_attribution_accepts_when_orgs_agree(monkeypatch, tmp_path):
    _desktop_session(tmp_path, org=_PERSONAL_ORG)
    _desktop_session_env(monkeypatch, tmp_path)
    cred = tmp_path / "acct" / ".credentials.json"
    _login(tmp_path / "acct", _PERSONAL_ORG)
    assert cu.check_attribution(cred).ok is True


def test_attribution_refuses_when_session_account_undeterminable(monkeypatch, tmp_path):
    """Cannot-tell is refused too — the defect is a confident number, not a wrong one."""
    _desktop_session_env(monkeypatch, tmp_path)  # nothing filed for this session id
    cred = tmp_path / "cli" / ".credentials.json"
    _login(tmp_path / "cli", _WORK_ORG)
    attribution = cu.check_attribution(cred)
    assert attribution.ok is False
    assert "could not be determined" in attribution.reason


def test_attribution_not_claimed_outside_a_claude_session(monkeypatch, tmp_path):
    """A human at a plain terminal: the ambient login is the subject and the answer."""
    monkeypatch.delenv("CLAUDECODE", raising=False)
    cred = tmp_path / "cli" / ".credentials.json"
    _login(tmp_path / "cli", _WORK_ORG)
    assert cu.check_attribution(cred).ok is True


def test_cli_session_attributes_to_its_own_login(monkeypatch, tmp_path):
    """Under the CLI the session and the login are the same thing by construction."""
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "acct"))
    _login(tmp_path / "acct", _WORK_ORG)
    assert cu.session_org() == _WORK_ORG
    assert cu.check_attribution(tmp_path / "acct" / ".credentials.json").ok is True


def test_latest_usage_refuses_a_reading_it_cannot_attribute(monkeypatch, tmp_path):
    """A valid token and a 200 are not enough: the number must be this session's."""
    _desktop_session(tmp_path, org=_PERSONAL_ORG)
    _desktop_session_env(monkeypatch, tmp_path)
    _login(tmp_path / "cli", _WORK_ORG)
    fetched = []
    monkeypatch.setattr(cu, "fetch_usage", lambda **k: fetched.append(k) or _PAYLOAD)

    cred = tmp_path / "cli" / ".credentials.json"
    assert cu.latest_usage(cred_path=cred) is None
    assert fetched == [], "must not even fetch a reading it could not attribute"

    # Explicitly scoped to a named account, so no claim about this session is made.
    assert cu.latest_usage(cred_path=cred, require_session_attribution=False) is not None


def test_latest_usage_falls_back_to_desktop_history_for_an_unregistered_session(monkeypatch):
    mine = cu.Identity("acct-mine", _PERSONAL_ORG)
    fallback = cu.UsageReport(
        17.0, "2099-01-01T00:00:00Z", 26.0, "2099-01-02T00:00:00Z", 1000.0
    )
    monkeypatch.setattr(
        cu, "check_attribution",
        lambda cred_path=None: cu.Attribution(False, mine, cu.Identity(None, None), "unregistered"),
    )
    monkeypatch.setattr(cu, "running_surface", lambda: "desktop")
    monkeypatch.setattr(cu, "desktop_usage_report", lambda **kwargs: fallback)
    monkeypatch.setattr(
        cu, "fetch_usage",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not fetch")),
    )
    assert cu.latest_usage() == fallback


def test_findings_render_desktop_history_age(monkeypatch):
    monkeypatch.setattr(cu.time, "time", lambda: 1120.0)
    report = cu.UsageReport(17.0, None, 26.0, None, 1000.0)
    message = cu.usage_findings(report=report)[0].message
    assert "desktop app record 2m old" in message


def test_findings_name_identity_as_the_cause(monkeypatch, tmp_path):
    _desktop_session(tmp_path, org=_PERSONAL_ORG)
    _desktop_session_env(monkeypatch, tmp_path)
    _login(tmp_path / "cli", _WORK_ORG)
    monkeypatch.setattr(cu, "fetch_usage", lambda **k: _PAYLOAD)

    findings = cu.usage_findings(cred_path=tmp_path / "cli" / ".credentials.json")
    assert findings[0].level == "ok"
    assert "no Claude usage signal for this session's account" in findings[0].message
    assert "92" not in findings[0].message, "the other account's number must not leak out"


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
