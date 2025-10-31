from __future__ import annotations

import os
import time
import jwt
import pytest

from factory_agents.archivist import extra_endpoints as xtra


def _make_token(secret: str, sub: str = "tester", lifetime_s: int = 60) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        "nbf": now - 1,
        "exp": now + lifetime_s,
        "iss": "unit-test",
        "aud": "archivist",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_decode_valid_jwt(monkeypatch):
    monkeypatch.setenv("FEDERATION_JWT_SECRET", "unit-secret")
    tok = _make_token("unit-secret")
    claims = xtra._decode_jwt(tok)
    assert claims["sub"] == "tester"
    assert claims["iss"] == "unit-test"


def test_decode_expired_jwt(monkeypatch):
    monkeypatch.setenv("FEDERATION_JWT_SECRET", "unit-secret")
    tok = _make_token("unit-secret", lifetime_s=-1)
    with pytest.raises(Exception):
        xtra._decode_jwt(tok)
