"""Tests for estate analytics (summary, trends) and audit log chain verification endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import col, select

from api import db
from api.db_models import AuditLogRecord
from api.main import app
from api.models import AuditVerifyStatus


def test_audit_verify_endpoint_valid_chain() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == AuditVerifyStatus.VALID
    assert data["recordCount"] >= 1
    assert len(data["headHash"]) == 64
    assert data["details"] is None


def test_audit_verify_endpoint_detects_tampering() -> None:
    client = TestClient(app)

    # Tamper with an existing audit log record
    with db.session_scope() as session:
        first_rec = session.exec(select(AuditLogRecord).order_by(col(AuditLogRecord.id).asc())).first()
        assert first_rec is not None
        orig_hash = first_rec.record_hash
        first_rec.record_hash = "deadbeef" * 8
        session.add(first_rec)
        session.commit()

        # Call endpoint - should detect tampering
        resp = client.get("/api/v1/audit/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == AuditVerifyStatus.TAMPERED
        assert "Tampered record" in (data["details"] or "")

        # Restore original hash
        first_rec.record_hash = orig_hash
        session.add(first_rec)
        session.commit()


def test_estate_summary_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/estate/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert "totalTargets" in data
    assert "totalScans" in data
    assert "totalFindings" in data
    assert "criticalFindings" in data
    assert "pqcReadinessScore" in data
    assert "activeAlerts" in data

    assert data["totalScans"] >= 1
    assert data["totalFindings"] >= 1
    assert 0.0 <= data["pqcReadinessScore"] <= 100.0


def test_estate_trend_endpoint() -> None:
    client = TestClient(app)

    # 1. Default 30 days
    resp = client.get("/api/v1/estate/trend")
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 30
    assert len(data["points"]) == 30
    for pt in data["points"]:
        assert "date" in pt
        assert "avgRiskScore" in pt
        assert "criticalCount" in pt
        assert "totalFindings" in pt

    # 2. Custom 7 days
    resp7 = client.get("/api/v1/estate/trend?days=7")
    assert resp7.status_code == 200
    data7 = resp7.json()
    assert data7["days"] == 7
    assert len(data7["points"]) == 7
