"""App-side Cloudflare Access gate for the dashboard's exposed mode.

Two independent checks, both fail-closed, composed by :func:`authorized`:

1. The owner-identity header (``Cf-Access-Authenticated-User-Email``) must equal
   the configured owner email. Cheap, and it catches a header-only probe.
2. A verified Cloudflare Access RS256 JWT (``Cf-Access-Jwt-Assertion``). This is
   the real gate: pure stdlib, verification-only. It never decrypts padding and
   parses it — it constructs the expected EMSA-PKCS1-v1.5 block and compares it
   against the RSA-decrypted signature with ``hmac.compare_digest``. The alg is
   pinned to RS256 unconditionally; a token's own ``alg`` header is never trusted
   to select the routine, which forecloses alg-confusion (``none``/HS256/etc.).

This is a *second* layer behind Cloudflare Access at the edge — never the only
one. Any parse or verification failure is treated as "deny".

Ported from horus-hub (``access_jwt.py`` + ``auth.py``); kept dependency-free so
the harness stays stdlib-only.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
import urllib.request
from typing import Callable

from horus.config import AccessConfig, DashboardAccess


ACCESS_EMAIL_HEADER = "Cf-Access-Authenticated-User-Email"
ACCESS_JWT_HEADER = "Cf-Access-Jwt-Assertion"

_JWKS_TTL_SECONDS = 600.0
_CLOCK_LEEWAY_SECONDS = 60

# DER prefix for a SHA-256 DigestInfo (RFC 8017 Appendix A.2.4 / RFC 9579).
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


class AccessJWTError(Exception):
    """Raised for any Access JWT parse or verification failure. Fail closed."""


JWKSFetcher = Callable[[str], dict]


def fetch_jwks(url: str) -> dict:
    """Default JWKS fetcher. Tests must inject their own offline fetcher."""
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 (fixed https URL from config)
        return json.loads(response.read().decode("utf-8"))


class JWKSCache:
    """TTL-cached JWKS keyed by ``kid``, with one bounded refetch on a miss."""

    def __init__(self, jwks_url: str, fetcher: JWKSFetcher = fetch_jwks, ttl_seconds: float = _JWKS_TTL_SECONDS):
        self._jwks_url = jwks_url
        self._fetcher = fetcher
        self._ttl_seconds = ttl_seconds
        self._keys: dict[str, tuple[int, int]] = {}
        self._fetched_at: float = 0.0

    def get_key(self, kid: str, now: float | None = None) -> tuple[int, int] | None:
        if now is None:
            now = time.time()
        if not self._keys or (now - self._fetched_at) > self._ttl_seconds:
            self._refresh()
        if kid in self._keys:
            return self._keys[kid]
        # Single bounded refetch: JWKS may have rotated since our last fetch.
        self._refresh()
        return self._keys.get(kid)

    def _refresh(self) -> None:
        raw = self._fetcher(self._jwks_url)
        keys: dict[str, tuple[int, int]] = {}
        for jwk in raw.get("keys", []) if isinstance(raw, dict) else []:
            if not isinstance(jwk, dict) or jwk.get("kty") != "RSA":
                continue
            kid = jwk.get("kid")
            if not isinstance(kid, str) or not kid:
                continue
            try:
                n = _b64url_decode_int(jwk["n"])
                e = _b64url_decode_int(jwk["e"])
            except (KeyError, TypeError, ValueError, binascii.Error):
                continue
            keys[kid] = (n, e)
        self._keys = keys
        self._fetched_at = time.time()


def authorized(headers: object, dash_access: DashboardAccess, jwks_cache: JWKSCache) -> bool:
    """The composed exposed-mode gate: owner header AND a valid Access JWT.

    Owner check first (cheap, denies a header-only probe), then JWT. Both must
    pass. Any failure -> False (deny).
    """
    if not is_owner_request(headers, dash_access.owner_email):
        return False
    return is_valid_access_jwt_request(headers, dash_access.access, dash_access.owner_email, jwks_cache)


def is_owner_request(headers: object, owner_email: str) -> bool:
    """True iff the Access owner-identity header matches ``owner_email``."""
    if not owner_email:
        return False
    get_header = getattr(headers, "get", None)
    if get_header is None:
        return False
    presented = get_header(ACCESS_EMAIL_HEADER)
    if not isinstance(presented, str) or not presented.strip():
        return False
    return presented.strip().lower() == owner_email.strip().lower()


def is_valid_access_jwt_request(headers: object, access_config: AccessConfig, owner_email: str, jwks_cache: JWKSCache) -> bool:
    get_header = getattr(headers, "get", None)
    if get_header is None:
        return False
    token = get_header(ACCESS_JWT_HEADER)
    if not isinstance(token, str) or not token.strip():
        return False
    try:
        verify_access_jwt(
            token.strip(),
            access_config=access_config,
            jwks_cache=jwks_cache,
            owner_email=owner_email,
        )
    except AccessJWTError:
        return False
    return True


def verify_access_jwt(
    token: str,
    *,
    access_config: AccessConfig,
    jwks_cache: JWKSCache,
    owner_email: str,
    now: float | None = None,
) -> None:
    """Verify an Access JWT end to end. Raises AccessJWTError on any failure."""
    if now is None:
        now = time.time()

    parts = token.split(".")
    if len(parts) != 3:
        raise AccessJWTError("Malformed JWT structure.")
    header_b64, payload_b64, signature_b64 = parts

    header = _decode_json_segment(header_b64)
    payload = _decode_json_segment(payload_b64)

    # Alg is pinned to RS256 regardless of the header's claim — this is the
    # alg-confusion defense, not a negotiation.
    if header.get("alg") != "RS256":
        raise AccessJWTError(f"Unsupported alg: {header.get('alg')!r}")

    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise AccessJWTError("Missing kid.")

    key = jwks_cache.get_key(kid, now)
    if key is None:
        raise AccessJWTError("Unknown kid.")
    n, e = key

    try:
        signature = _b64url_decode(signature_b64)
    except (ValueError, binascii.Error) as exc:
        raise AccessJWTError("Invalid signature encoding.") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    if not _rsa_pkcs1_v15_verify(signing_input, signature, n, e):
        raise AccessJWTError("Signature verification failed.")

    _validate_claims(payload, access_config, owner_email, now)


def _validate_claims(payload: dict, access_config: AccessConfig, owner_email: str, now: float) -> None:
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or isinstance(exp, bool) or now > exp + _CLOCK_LEEWAY_SECONDS:
        raise AccessJWTError("Token expired.")

    nbf = payload.get("nbf")
    if nbf is not None:
        if not isinstance(nbf, (int, float)) or isinstance(nbf, bool) or now < nbf - _CLOCK_LEEWAY_SECONDS:
            raise AccessJWTError("Token not yet valid.")

    expected_iss = f"https://{access_config.team_domain}"
    if payload.get("iss") != expected_iss:
        raise AccessJWTError("Unexpected issuer.")

    aud_claim = payload.get("aud")
    auds = aud_claim if isinstance(aud_claim, list) else [aud_claim]
    if access_config.aud not in auds:
        raise AccessJWTError("Unexpected audience.")

    email = payload.get("email")
    if not isinstance(email, str) or email.strip().lower() != owner_email.strip().lower():
        raise AccessJWTError("Email claim mismatch.")


def _decode_json_segment(segment: str) -> dict:
    try:
        raw = _b64url_decode(segment)
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AccessJWTError("Malformed JWT segment.") from exc
    if not isinstance(data, dict):
        raise AccessJWTError("Malformed JWT segment.")
    return data


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _b64url_decode_int(segment: str) -> int:
    return int.from_bytes(_b64url_decode(segment), "big")


def _emsa_pkcs1_v15_encode_sha256(message: bytes, key_byte_length: int) -> bytes:
    digest_info = _SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(message).digest()
    padding_length = key_byte_length - len(digest_info) - 3
    if padding_length < 8:
        raise AccessJWTError("RSA key too small for SHA-256 EMSA encoding.")
    return b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info


def _rsa_pkcs1_v15_verify(message: bytes, signature: bytes, n: int, e: int) -> bool:
    key_byte_length = (n.bit_length() + 7) // 8
    if key_byte_length == 0 or len(signature) != key_byte_length:
        return False
    signature_int = int.from_bytes(signature, "big")
    if signature_int >= n:
        return False
    decrypted = pow(signature_int, e, n).to_bytes(key_byte_length, "big")
    try:
        expected = _emsa_pkcs1_v15_encode_sha256(message, key_byte_length)
    except AccessJWTError:
        return False
    return hmac.compare_digest(decrypted, expected)
