"""M2 Verification: CORS Hardening tests.

Proves:
1. Unlisted origins do not receive Access-Control-Allow-Origin header.
2. Listed origins receive Access-Control-Allow-Origin and Access-Control-Allow-Credentials headers.
3. Preflight OPTIONS requests from unlisted origins are rejected / do not get CORS headers.
4. ECDAT_CORS_ORIGINS environment variable correctly configures allowed origins.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.cors import get_cors_origins
from api.main import app


def test_cors_listed_origin_allowed() -> None:
    """Requests from listed origins must receive CORS allow headers."""
    client = TestClient(app)
    headers = {
        "Origin": "http://localhost:3000",
        "Authorization": "Bearer ecdat-test-token-secret",
    }
    resp = client.get("/api/v1/health", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_unlisted_origin_denied() -> None:
    """Requests from unlisted origins must NOT receive Access-Control-Allow-Origin."""
    client = TestClient(app)
    headers = {
        "Origin": "http://unlisted-malicious-site.com",
        "Authorization": "Bearer ecdat-test-token-secret",
    }
    resp = client.get("/api/v1/health", headers=headers)
    assert resp.status_code == 200
    # The browser enforces CORS: if access-control-allow-origin is missing or does not match, request is blocked
    assert "access-control-allow-origin" not in resp.headers


def test_cors_preflight_listed_origin() -> None:
    """Preflight OPTIONS from listed origin must return 200 with allow headers."""
    client = TestClient(app)
    headers = {
        "Origin": "http://127.0.0.1:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }
    resp = client.options("/api/v1/scans", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_unlisted_origin() -> None:
    """Preflight OPTIONS from unlisted origin must not receive allow-origin."""
    client = TestClient(app)
    headers = {
        "Origin": "http://evil-attacker.io",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }
    resp = client.options("/api/v1/scans", headers=headers)
    assert "access-control-allow-origin" not in resp.headers


def test_get_cors_origins_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """ECDAT_CORS_ORIGINS parses comma-separated origins cleanly."""
    monkeypatch.setenv("ECDAT_CORS_ORIGINS", " https://ecdat.agency.gov, https://portal.agency.gov ")
    origins = get_cors_origins()
    assert origins == ["https://ecdat.agency.gov", "https://portal.agency.gov"]
