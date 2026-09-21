"""Test real dependency status reporting in /health endpoint."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app


def test_health_reports_real_dependency_status_and_failure_recovery() -> None:
    """GET /health checks DB connectivity and reports version info; returns 503 if DB unreachable."""
    client = TestClient(app)

    # 1. Normal state: DB connected -> 200 OK
    res_ok = client.get("/api/v1/health")
    assert res_ok.status_code == 200
    data_ok = res_ok.json()
    assert data_ok["status"] == "ok"
    assert data_ok["database"] == "connected"
    assert data_ok["engine_version"] == "v1.0-cmc"
    assert data_ok["rule_set_version"] == "v1.0.1"
    assert "time" in data_ok

    # 2. Simulated DB failure / killed connection -> 503 Service Unavailable
    with patch("api.db.session_scope", side_effect=Exception("Database connection terminated")):
        res_down = client.get("/api/v1/health")
        assert res_down.status_code == 503
        data_down = res_down.json()
        assert data_down["status"] == "unavailable"
        assert data_down["database"] == "disconnected"
        assert data_down["engine_version"] == "v1.0-cmc"

    # 3. Restored DB connection -> 200 OK again
    res_restored = client.get("/api/v1/health")
    assert res_restored.status_code == 200
    data_restored = res_restored.json()
    assert data_restored["status"] == "ok"
    assert data_restored["database"] == "connected"
