"""Access gate: RS256 JWT verification + owner header + composed authorize.

Offline: tokens are signed with a test-only RSA key (access_fixtures) and the
JWKS is injected, so nothing touches the network.
"""

from pathlib import Path
import hashlib
import hmac
import json
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from horus.access_gate import (
    AccessJWTError,
    JWKSCache,
    authorized,
    is_owner_request,
    is_valid_access_jwt_request,
    verify_access_jwt,
)
from horus.config import AccessConfig, DashboardAccess

from access_fixtures import (
    AUD,
    OWNER_EMAIL,
    TEAM_DOMAIN,
    TEST_KID,
    TEST_RSA_N,
    b64url_encode,
    jwks_dict,
    make_token,
    valid_payload,
)


class AccessJwtVerifyTests(unittest.TestCase):
    def setUp(self):
        self.access_config = AccessConfig(team_domain=TEAM_DOMAIN, aud=AUD, jwks_url="https://example.invalid/certs")
        self.fetch_calls = 0

    def _fetcher(self, url):
        self.fetch_calls += 1
        return jwks_dict()

    def _cache(self):
        return JWKSCache(self.access_config.jwks_url, fetcher=self._fetcher)

    def _verify(self, token, cache=None):
        verify_access_jwt(
            token,
            access_config=self.access_config,
            jwks_cache=cache if cache is not None else self._cache(),
            owner_email=OWNER_EMAIL,
        )

    def test_valid_token_passes(self):
        self._verify(make_token(payload=valid_payload()))

    def test_tampered_payload_fails(self):
        token = make_token(payload=valid_payload())
        header_b64, _payload_b64, sig_b64 = token.split(".")
        tampered_payload_b64 = b64url_encode(json.dumps(valid_payload(email="attacker@evil.com")).encode())
        tampered = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"
        with self.assertRaises(AccessJWTError):
            self._verify(tampered)

    def test_wrong_kid_fails_after_one_refetch(self):
        cache = self._cache()
        token = make_token(payload=valid_payload(), kid="unknown-kid")
        with self.assertRaises(AccessJWTError):
            self._verify(token, cache=cache)
        self.assertEqual(self.fetch_calls, 2)

    def test_alg_none_rejected(self):
        header = {"alg": "none", "typ": "JWT", "kid": TEST_KID}
        token = make_token(header=header, payload=valid_payload(), unsigned=True)
        with self.assertRaises(AccessJWTError):
            self._verify(token)

    def test_alg_hs256_rejected_even_with_valid_looking_signature(self):
        # Alg-confusion attempt: HMAC-sign with the RSA modulus as the "secret".
        header = {"alg": "HS256", "typ": "JWT", "kid": TEST_KID}
        header_b64 = b64url_encode(json.dumps(header).encode())
        payload_b64 = b64url_encode(json.dumps(valid_payload()).encode())
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        secret = str(TEST_RSA_N).encode()
        signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
        token = f"{header_b64}.{payload_b64}.{b64url_encode(signature)}"
        with self.assertRaises(AccessJWTError):
            self._verify(token)

    def test_expired_token_fails(self):
        with self.assertRaises(AccessJWTError):
            self._verify(make_token(payload=valid_payload(exp=time.time() - 1000)))

    def test_future_nbf_fails(self):
        with self.assertRaises(AccessJWTError):
            self._verify(make_token(payload=valid_payload(nbf=time.time() + 1000)))

    def test_wrong_aud_fails(self):
        with self.assertRaises(AccessJWTError):
            self._verify(make_token(payload=valid_payload(aud=["some-other-aud"])))

    def test_wrong_iss_fails(self):
        with self.assertRaises(AccessJWTError):
            self._verify(make_token(payload=valid_payload(iss="https://not-my-team.cloudflareaccess.com")))

    def test_email_mismatch_fails(self):
        with self.assertRaises(AccessJWTError):
            self._verify(make_token(payload=valid_payload(email="someone-else@example.com")))

    def test_email_match_is_case_insensitive(self):
        self._verify(make_token(payload=valid_payload(email=OWNER_EMAIL.upper())))

    def test_malformed_structure_fails(self):
        with self.assertRaises(AccessJWTError):
            self._verify("not-a-jwt")


class IsValidAccessJwtRequestTests(unittest.TestCase):
    def setUp(self):
        self.access_config = AccessConfig(team_domain=TEAM_DOMAIN, aud=AUD, jwks_url="https://example.invalid/certs")

    def _cache(self):
        return JWKSCache(self.access_config.jwks_url, fetcher=lambda url: jwks_dict())

    def test_missing_header_denied(self):
        self.assertFalse(is_valid_access_jwt_request({}, self.access_config, OWNER_EMAIL, self._cache()))

    def test_garbage_token_denied(self):
        headers = {"Cf-Access-Jwt-Assertion": "garbage.not.a-jwt"}
        self.assertFalse(is_valid_access_jwt_request(headers, self.access_config, OWNER_EMAIL, self._cache()))

    def test_valid_token_allowed(self):
        headers = {"Cf-Access-Jwt-Assertion": make_token(payload=valid_payload())}
        self.assertTrue(is_valid_access_jwt_request(headers, self.access_config, OWNER_EMAIL, self._cache()))


class OwnerHeaderTests(unittest.TestCase):
    def test_matching_owner_allowed_case_insensitive(self):
        headers = {"Cf-Access-Authenticated-User-Email": OWNER_EMAIL.upper()}
        self.assertTrue(is_owner_request(headers, OWNER_EMAIL))

    def test_missing_header_denied(self):
        self.assertFalse(is_owner_request({}, OWNER_EMAIL))

    def test_wrong_email_denied(self):
        headers = {"Cf-Access-Authenticated-User-Email": "someone-else@example.com"}
        self.assertFalse(is_owner_request(headers, OWNER_EMAIL))

    def test_empty_owner_denied(self):
        headers = {"Cf-Access-Authenticated-User-Email": OWNER_EMAIL}
        self.assertFalse(is_owner_request(headers, ""))


class AuthorizedTests(unittest.TestCase):
    def setUp(self):
        self.dash = DashboardAccess(
            owner_email=OWNER_EMAIL,
            access=AccessConfig(team_domain=TEAM_DOMAIN, aud=AUD, jwks_url="https://example.invalid/certs"),
        )

    def _cache(self):
        return JWKSCache(self.dash.access.jwks_url, fetcher=lambda url: jwks_dict())

    def _headers(self, *, email=OWNER_EMAIL, token=True):
        h = {}
        if email is not None:
            h["Cf-Access-Authenticated-User-Email"] = email
        if token:
            h["Cf-Access-Jwt-Assertion"] = make_token(payload=valid_payload())
        return h

    def test_owner_and_valid_jwt_allowed(self):
        self.assertTrue(authorized(self._headers(), self.dash, self._cache()))

    def test_owner_header_only_denied(self):
        self.assertFalse(authorized(self._headers(token=False), self.dash, self._cache()))

    def test_valid_jwt_without_owner_header_denied(self):
        self.assertFalse(authorized(self._headers(email=None), self.dash, self._cache()))

    def test_wrong_owner_denied_even_with_valid_jwt(self):
        self.assertFalse(authorized(self._headers(email="evil@example.com"), self.dash, self._cache()))


if __name__ == "__main__":
    unittest.main()
