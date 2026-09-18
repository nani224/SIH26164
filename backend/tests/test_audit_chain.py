"""Tests for Phase 10 Tamper-Evident Audit Log Cryptographic Hash Chaining."""

from __future__ import annotations

from sqlmodel import Session

from api import db


def test_audit_log_hash_chaining_on_mutations() -> None:
    with db.session_scope() as session:
        # Clear or inspect existing
        rec1 = db.log_audit(session, action="test_action_1", entity_type="scan", entity_id="s1")
        session.commit()
        session.refresh(rec1)

        assert rec1.record_hash != ""
        assert len(rec1.record_hash) == 64

        rec2 = db.log_audit(session, action="test_action_2", entity_type="scan", entity_id="s2")
        session.commit()
        session.refresh(rec2)

        assert rec2.prev_hash == rec1.record_hash
        assert rec2.record_hash != ""
        assert len(rec2.record_hash) == 64


def test_verify_audit_log_integrity_passes() -> None:
    with db.session_scope() as session:
        valid, error = db.verify_audit_log_integrity(session)
        assert valid is True
        assert error is None


def test_verify_audit_log_detects_tampering() -> None:
    with Session(db.engine) as session:
        # Create a small isolated chain in a test transaction
        rec = db.log_audit(
            session,
            action="legitimate_action",
            entity_type="policy",
            entity_id="p1",
            detail={"user": "admin"},
        )
        session.commit()
        session.refresh(rec)

        # Confirm it is valid before tampering
        valid, error = db.verify_audit_log_integrity(session)
        assert valid is True

        # Tamper with the detail field
        rec.detail = {"user": "attacker", "tampered": True}
        session.add(rec)
        session.commit()

        # Verification must fail and detect the tampered record
        valid, error = db.verify_audit_log_integrity(session)
        assert valid is False
        assert error is not None
        assert f"Tampered record at id={rec.id}" in error

        # Revert tampering to keep DB clean for other tests
        rec.detail = {"user": "admin"}
        session.add(rec)
        session.commit()
        valid, error = db.verify_audit_log_integrity(session)
        assert valid is True
