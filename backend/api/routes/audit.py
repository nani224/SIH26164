"""Audit log verification endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import col, select

from api import db
from api.db_models import AuditLogRecord
from api.models import AuditVerifyResponse, AuditVerifyStatus

router = APIRouter(tags=["audit"])


@router.get("/audit/verify", response_model=AuditVerifyResponse)
def verify_audit_chain() -> AuditVerifyResponse:
    """Verify the cryptographic SHA-256 hash integrity of the audit log chain."""
    with db.session_scope() as session:
        valid, error = db.verify_audit_log_integrity(session)
        records = session.exec(select(AuditLogRecord).order_by(col(AuditLogRecord.id).asc())).all()
        record_count = len(records)
        head_hash = records[-1].record_hash if records else "0" * 64

        return AuditVerifyResponse(
            status=AuditVerifyStatus.VALID if valid else AuditVerifyStatus.TAMPERED,
            recordCount=record_count,
            headHash=head_hash,
            details=error,
        )
