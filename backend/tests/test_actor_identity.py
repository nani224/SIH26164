"""M3 Verification: Actor identity on the audit chain tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from api import db
from api.db_models import AuditLogRecord
from api.main import app


def test_write_without_actor_header_is_rejected() -> None:
    """State-changing write requests without X-ECDAT-Actor must return 400."""
    client = TestClient(app, headers={"Authorization": "Bearer ecdat-test-token-secret"})
    # Explicitly pass empty/no X-ECDAT-Actor header
    resp = client.post(
        "/api/v1/targets",
        json={
            "name": "test-target",
            "kind": "repo",
            "uri": "https://example.com/repo",
            "policyId": "pol_default",
            "schedule": "0 0 * * *",
        },
        headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": ""},
    )
    assert resp.status_code == 400
    assert "X-ECDAT-Actor header is required" in resp.json().get("detail", resp.json().get("message", ""))


def test_read_without_actor_header_succeeds() -> None:
    """Read requests (GET) must succeed without X-ECDAT-Actor header."""
    client = TestClient(app, headers={"Authorization": "Bearer ecdat-test-token-secret"})
    resp = client.get(
        "/api/v1/targets",
        headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": ""},
    )
    assert resp.status_code == 200


def test_write_with_actor_records_in_audit_log() -> None:
    """A write with X-ECDAT-Actor must record the actor in the audit log and verify cleanly."""
    actor_name = "operator-shravan-42"
    client = TestClient(app, headers={"Authorization": "Bearer ecdat-test-token-secret"})

    resp = client.post(
        "/api/v1/targets",
        json={
            "name": "audit-test-target",
            "kind": "repo",
            "uri": "https://example.com/audit-test",
            "policyId": "pol_default",
            "schedule": "0 0 * * *",
        },
        headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": actor_name},
    )
    assert resp.status_code == 201
    target_id = resp.json()["id"]

    # Verify the audit log record in the database
    with Session(db.engine) as session:
        audit_rec = session.exec(
            select(AuditLogRecord)
            .where(AuditLogRecord.entity_type == "target", AuditLogRecord.entity_id == target_id)
            .order_by(col(AuditLogRecord.id).desc())
        ).first()

        assert audit_rec is not None
        assert audit_rec.actor == actor_name
        assert audit_rec.action == "target.create"

        # Verify hash integrity of the chain
        valid, err = db.verify_audit_log_integrity(session)
        assert valid is True, f"Audit log integrity check failed: {err}"
