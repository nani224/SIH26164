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
from api.db_models import FindingRecord, PolicyRecord, ScanEventRecord, ScanRecord
from api.filtering import band_counts
from api.models import Finding, Policy, Scan, ScanCreate, ScanStatus
from engine.models import ScanResult


def resolve_policy(payload: ScanCreate) -> Policy:
    """The policy a scan should score against: payload.policyId (falling
    back to the default policy) with payload.crqcYears applied as a
    per-scan override of the horizon (Z), if given.
    """
    with db.session_scope() as session:
        policy_id = payload.policyId or stub_data.DEFAULT_POLICY.id
        rec = session.get(PolicyRecord, policy_id)
        policy = db.record_to_policy(rec) if rec is not None else stub_data.DEFAULT_POLICY
    if payload.crqcYears is not None:
        policy = policy.model_copy(update={"crqcYears": payload.crqcYears})
    return policy


def create_scan_from_result(
    payload: ScanCreate,
    result: ScanResult,
    policy: Policy,
    *,
    scan_status: ScanStatus = ScanStatus.DONE,
    events: list[tuple[str, dict[str, object]]] | None = None,
) -> Scan:
    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)
    scan = Scan(
        id=scan_id,
        target=payload.path or "uploaded-artifact",
        status=scan_status,
        stats=result.stats,
        bands=band_counts(result.findings),
        policyId=policy.id,
        crqcYears=policy.crqcYears,
        startedAt=now,
        finishedAt=now,
    )
    all_events = list(events or [])
    final_type = "error" if scan_status == ScanStatus.FAILED else "done"
    all_events.append((final_type, {"scanId": scan_id, "findingCount": len(result.findings)}))

    with db.session_scope() as session:
        session.add(db.scan_to_record(scan))
        for finding in result.findings:
            session.add(db.finding_to_record(finding, scan_id=scan_id))
        for event_id, (event_type, event_payload) in enumerate(all_events, start=1):
            session.add(
                ScanEventRecord(scan_id=scan_id, event_id=event_id, type=event_type, payload=event_payload)
            )
        db.log_audit(
            session,
            action="scan.create",
            entity_type="scan",
            entity_id=scan_id,
            detail={"target": scan.target, "findingCount": len(result.findings)},
        )
        session.commit()
    return scan


def list_events(scan_id: str, after: int | None = None) -> list[ScanEventRecord]:
    with db.session_scope() as session:
        query = select(ScanEventRecord).where(ScanEventRecord.scan_id == scan_id)
        if after:
            query = query.where(ScanEventRecord.event_id > after)
        query = query.order_by(ScanEventRecord.event_id)  # type: ignore[arg-type]
        return list(session.exec(query).all())


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
