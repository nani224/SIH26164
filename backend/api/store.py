"""Phase 2: SQLModel-backed persistence for scans, findings, and policies.

Same public function signatures as the Phase 0/1 in-memory version (so
routes/contract are unaffected) -- now backed by api/db.py's SQLite
session instead of module-level dicts. Every mutation writes an
AuditLogRecord row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlmodel import select

from api import db, stub_data
from api.db_models import FindingRecord, PolicyRecord, ScanRecord
from api.models import BandCounts, Finding, Policy, Scan, ScanCreate, ScanStats, ScanStatus


def create_scan(payload: ScanCreate) -> Scan:
    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    with db.session_scope() as session:
        policy_id = payload.policyId or stub_data.DEFAULT_POLICY.id
        policy_rec = session.get(PolicyRecord, policy_id)
        policy = db.record_to_policy(policy_rec) if policy_rec is not None else stub_data.DEFAULT_POLICY

        scan = Scan(
            id=scan_id,
            target=payload.path or "uploaded-artifact",
            status=ScanStatus.DONE,
            stats=ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0),
            bands=BandCounts(),
            policyId=policy.id,
            crqcYears=payload.crqcYears or policy.crqcYears,
            startedAt=now,
            finishedAt=now,
        )
        session.add(db.scan_to_record(scan))
        db.log_audit(
            session, action="scan.create", entity_type="scan", entity_id=scan_id, detail={"target": scan.target}
        )
        session.commit()
        return scan


def list_scans() -> list[Scan]:
    with db.session_scope() as session:
        return [db.record_to_scan(r) for r in session.exec(select(ScanRecord)).all()]


def get_scan(scan_id: str) -> Scan | None:
    with db.session_scope() as session:
        rec = session.get(ScanRecord, scan_id)
        return db.record_to_scan(rec) if rec is not None else None


def list_findings(scan_id: str) -> list[Finding]:
    with db.session_scope() as session:
        records = session.exec(select(FindingRecord).where(FindingRecord.scan_id == scan_id)).all()
        return [db.record_to_finding(r) for r in records]


def get_finding(finding_id: str) -> Finding | None:
    with db.session_scope() as session:
        rec = session.get(FindingRecord, finding_id)
        return db.record_to_finding(rec) if rec is not None else None


def replace_finding(finding_id: str, updated: Finding, *, action: str = "finding.update") -> None:
    with db.session_scope() as session:
        existing = session.get(FindingRecord, finding_id)
        if existing is None:
            raise KeyError(finding_id)
        new_record = db.finding_to_record(updated, scan_id=existing.scan_id)
        for field in FindingRecord.model_fields:
            setattr(existing, field, getattr(new_record, field))
        session.add(existing)
        db.log_audit(session, action=action, entity_type="finding", entity_id=finding_id)
        session.commit()


def list_policies() -> list[Policy]:
    with db.session_scope() as session:
        return [db.record_to_policy(r) for r in session.exec(select(PolicyRecord)).all()]


def get_policy(policy_id: str) -> Policy | None:
    with db.session_scope() as session:
        rec = session.get(PolicyRecord, policy_id)
        return db.record_to_policy(rec) if rec is not None else None


def put_policy(policy: Policy) -> Policy:
    with db.session_scope() as session:
        session.merge(db.policy_to_record(policy))
        db.log_audit(session, action="policy.put", entity_type="policy", entity_id=policy.id)
        session.commit()
        return policy
