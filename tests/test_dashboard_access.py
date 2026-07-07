"""Dashboard exposed mode: [access] config loading + fail-closed handler gate.

Verifies that when an [access] block is configured, every route but /health
demands the owner header + a verified Access JWT (403 otherwise), that the
absent-block case is unchanged local behavior, and that _same_origin tightens
in exposed mode. Tokens are signed offline (access_fixtures); JWKS is injected.
"""

from pathlib import Path
from io import BytesIO
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from horus import config, dashboard
from horus.access_gate import JWKSCache

from access_fixtures import AUD, OWNER_EMAIL, TEAM_DOMAIN, jwks_dict, make_token, valid_payload


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _write_config(tmp_path, body: str):
    cfg_dir = Path(tmp_path) / "home" / ".horus"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.toml").write_text(body, encoding="utf-8")


_ACCESS_BLOCK = (
    "[access]\n"
    f'owner_email = "{OWNER_EMAIL}"\n'
    f'team_domain = "{TEAM_DOMAIN}"\n'
    f'aud = "{AUD}"\n'
    'jwks_url = "https://example.invalid/certs"\n'
)


# --------------------------------------------------------------------------- #
# config.load_dashboard_access
# --------------------------------------------------------------------------- #

def test_load_access_absent_returns_none(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _write_config(tmp_path, 'projects = ["/x"]\n')
    assert config.load_dashboard_access() is None


def test_load_access_missing_file_returns_none(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_dashboard_access() is None


def test_load_access_complete_block(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _write_config(tmp_path, _ACCESS_BLOCK)
    da = config.load_dashboard_access()
    assert da is not None
    assert da.owner_email == OWNER_EMAIL
    assert da.access.team_domain == TEAM_DOMAIN
    assert da.access.aud == AUD
    assert da.access.jwks_url == "https://example.invalid/certs"


def test_load_access_partial_block_fails_closed(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _write_config(tmp_path, '[access]\nowner_email = "rafa@example.com"\n')  # missing team_domain/aud/jwks_url
    with pytest.raises(config.ConfigError):
        config.load_dashboard_access()


def test_load_access_owner_email_lowercased(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    _write_config(tmp_path, _ACCESS_BLOCK.replace(OWNER_EMAIL, OWNER_EMAIL.upper()))
    da = config.load_dashboard_access()
    assert da.owner_email == OWNER_EMAIL  # normalized to lower


# --------------------------------------------------------------------------- #
# Handler gate
# --------------------------------------------------------------------------- #

def _arm_exposed(monkeypatch):
    da = config.DashboardAccess(
        owner_email=OWNER_EMAIL,
        access=config.AccessConfig(team_domain=TEAM_DOMAIN, aud=AUD, jwks_url="https://example.invalid/certs"),
    )
    monkeypatch.setattr(dashboard, "_DASH_ACCESS", da)
    monkeypatch.setattr(dashboard, "_JWKS_CACHE", JWKSCache(da.access.jwks_url, fetcher=lambda url: jwks_dict()))


def _run(method: str, path: str, headers: dict | None = None) -> dict:
    handler = object.__new__(dashboard._Handler)
    handler.path = path
    handler.headers = {"Host": "horus.example.com"}
    if headers:
        handler.headers.update(headers)
    handler.rfile = BytesIO(b"")
    handler.wfile = BytesIO()
    response: dict = {"headers": []}
    handler.send_response = lambda status: response.__setitem__("status", status)
    handler.send_header = lambda k, v: response["headers"].append((k, v))
    handler.end_headers = lambda: response.__setitem__("ended", True)
    getattr(dashboard._Handler, method)(handler)
    response["body"] = handler.wfile.getvalue().decode("utf-8", "replace")
    return response


def _valid_headers() -> dict:
    return {
        "Cf-Access-Authenticated-User-Email": OWNER_EMAIL,
        "Cf-Access-Jwt-Assertion": make_token(payload=valid_payload()),
        "Origin": "https://horus.example.com",
    }


def test_get_denied_without_auth_in_exposed_mode(monkeypatch):
    _arm_exposed(monkeypatch)
    resp = _run("do_GET", "/nope")
    assert resp["status"] == 403


def test_get_allowed_through_with_valid_auth(monkeypatch):
    # Authorized -> gate lets it reach routing; unknown path -> 404 (not 403).
    _arm_exposed(monkeypatch)
    resp = _run("do_GET", "/nope", _valid_headers())
    assert resp["status"] == 404


def test_health_public_in_exposed_mode(monkeypatch):
    _arm_exposed(monkeypatch)
    resp = _run("do_GET", "/health")
    assert resp["status"] == 200
    assert "horus-dashboard" in resp["body"]


def test_post_denied_without_auth_in_exposed_mode(monkeypatch):
    _arm_exposed(monkeypatch)
    resp = _run("do_POST", "/launch")
    assert resp["status"] == 403


def test_owner_header_only_denied(monkeypatch):
    _arm_exposed(monkeypatch)
    resp = _run("do_GET", "/nope", {"Cf-Access-Authenticated-User-Email": OWNER_EMAIL})
    assert resp["status"] == 403


def test_local_mode_unchanged_when_no_access_block(monkeypatch):
    monkeypatch.setattr(dashboard, "_DASH_ACCESS", None)
    monkeypatch.setattr(dashboard, "_JWKS_CACHE", None)
    resp = _run("do_GET", "/nope")  # no auth headers at all
    assert resp["status"] == 404  # gate is off -> reaches routing -> unknown path 404


# --------------------------------------------------------------------------- #
# _same_origin tightening
# --------------------------------------------------------------------------- #

def _same_origin(headers: dict) -> bool:
    handler = object.__new__(dashboard._Handler)
    handler.headers = headers
    return dashboard._Handler._same_origin(handler)


def test_same_origin_absent_origin_allowed_local(monkeypatch):
    monkeypatch.setattr(dashboard, "_DASH_ACCESS", None)
    assert _same_origin({"Host": "127.0.0.1:8765"}) is True


def test_same_origin_absent_origin_rejected_exposed(monkeypatch):
    _arm_exposed(monkeypatch)
    assert _same_origin({"Host": "horus.example.com"}) is False


def test_same_origin_matching_origin_allowed_exposed(monkeypatch):
    _arm_exposed(monkeypatch)
    assert _same_origin({"Host": "horus.example.com", "Origin": "https://horus.example.com"}) is True


def test_same_origin_cross_origin_rejected_exposed(monkeypatch):
    _arm_exposed(monkeypatch)
    assert _same_origin({"Host": "horus.example.com", "Origin": "https://evil.com"}) is False
