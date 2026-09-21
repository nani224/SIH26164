"""M1 Verification: Authentication & Bearer Token Hardening tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from api.auth import get_expected_token
from api.main import app


def test_health_endpoint_is_unauthenticated() -> None:
    """GET /api/v1/health must be accessible with no Authorization header."""
    client = TestClient(app, headers={"Authorization": ""})
    # Remove Authorization header explicitly
    resp = client.get("/api/v1/health", headers={"Authorization": ""})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_non_health_endpoints_reject_missing_token() -> None:
    """Every non-health endpoint must return 401 when Authorization header is missing."""
    client = TestClient(app, headers={"Authorization": ""})
    protected_endpoints = [
        "/api/v1/scans",
        "/api/v1/catalog/pqc",
        "/api/v1/policies",
        "/api/v1/targets",
        "/api/v1/residue",
        "/api/v1/probes",
        "/api/v1/estate/summary",
        "/api/v1/alerts",
    ]
    for endpoint in protected_endpoints:
        resp = client.get(endpoint, headers={"Authorization": ""})
        assert resp.status_code == 401, f"{endpoint} did not return 401 on missing token: {resp.status_code}"
        # Ensure no sensitive information leakage
        assert "unauthorized" in resp.text.lower()


def test_non_health_endpoints_reject_invalid_token() -> None:
    """Non-health endpoints must return 401 when bearer token is invalid."""
    client = TestClient(app, headers={"Authorization": "Bearer wrong-token-xyz"})
    resp = client.get("/api/v1/catalog/pqc", headers={"Authorization": "Bearer wrong-token-xyz"})
    assert resp.status_code == 401
    assert "unauthorized" in resp.text.lower()


def test_non_health_endpoints_reject_malformed_auth_header() -> None:
    """Non-health endpoints must return 401 when Authorization format is not Bearer."""
    client = TestClient(app, headers={"Authorization": "Basic dXNlcjpwYXNz"})
    resp = client.get("/api/v1/catalog/pqc", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401


def test_non_health_endpoints_accept_valid_token() -> None:
    """Non-health endpoints must succeed with 200 when valid bearer token is provided."""
    token = os.environ.get("ECDAT_API_TOKEN", "ecdat-test-token-secret")
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    resp = client.get("/api/v1/catalog/pqc", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_startup_fails_in_production_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """In production mode, get_expected_token() must raise RuntimeError if ECDAT_API_TOKEN is unset."""
    monkeypatch.delenv("ECDAT_API_TOKEN", raising=False)
    monkeypatch.delenv("ECDAT_DEV_MODE", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError, match="ECDAT_API_TOKEN environment variable must be set in production"):
        get_expected_token()
