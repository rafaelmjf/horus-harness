"""Shared TEST-ONLY RSA fixture for Access gate tests.

This keypair was generated offline for tests only and is never used at
runtime. Do not reuse it for anything but signing tokens in this test suite.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time


TEST_RSA_N = 98432773694957003566106246260364941467443158296818218112353214037278069870524562269913729779275613413962496678080243351655921866680177505163682550896315879664265840519329761929002953145346076263571684955048329835946103085813106422425000170830610495066040321689783701265501372005113917422558561332769654789377
TEST_RSA_E = 65537
TEST_RSA_D = 51207210985487039070797051436606532407510368783614146639647382080152562890667324199008784398044200432360916150303917128207836796353113079040093273879777727458722368976610824978275971568750443302858381546928293747470483640104962770636791001526310927689332674284027536538106520486363646652354793090705132272153

TEST_KID = "test-key-1"
TEAM_DOMAIN = "myteam.cloudflareaccess.com"
AUD = "test-aud-tag"
OWNER_EMAIL = "rafa@example.com"

_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_int(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return b64url_encode(value.to_bytes(length, "big"))


def sign_rs256(signing_input: bytes) -> bytes:
    """Independently re-derives the EMSA-PKCS1-v1.5/SHA-256 block and signs
    with the test private key — deliberately not calling into
    horus.access_gate so a bug in the verifier's own encoding can't hide
    behind symmetric reuse."""
    key_byte_length = (TEST_RSA_N.bit_length() + 7) // 8
    digest_info = _SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(signing_input).digest()
    padding_length = key_byte_length - len(digest_info) - 3
    em = b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info
    em_int = int.from_bytes(em, "big")
    sig_int = pow(em_int, TEST_RSA_D, TEST_RSA_N)
    return sig_int.to_bytes(key_byte_length, "big")


def make_token(*, header=None, payload=None, kid=TEST_KID, corrupt_signature=False, unsigned=False) -> str:
    if header is None:
        header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    header_b64 = b64url_encode(json.dumps(header).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    if unsigned:
        signature_b64 = ""
    else:
        signature = sign_rs256(signing_input)
        if corrupt_signature:
            signature = bytes([signature[0] ^ 0xFF]) + signature[1:]
        signature_b64 = b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def valid_payload(**overrides) -> dict:
    now = time.time()
    payload = {
        "iss": f"https://{TEAM_DOMAIN}",
        "aud": [AUD],
        "email": OWNER_EMAIL,
        "exp": now + 3600,
        "nbf": now - 60,
    }
    payload.update(overrides)
    return payload


def jwks_dict() -> dict:
    return {
        "keys": [
            {
                "kid": TEST_KID,
                "kty": "RSA",
                "alg": "RS256",
                "n": b64url_int(TEST_RSA_N),
                "e": b64url_int(TEST_RSA_E),
            }
        ]
    }
