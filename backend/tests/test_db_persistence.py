from __future__ import annotations

from sqlmodel import select

from api import db, store
from api.db_models import AuditLogRecord
from api.models import Context, Criticality, Exposure, Policy, ScanCreate, Triage, TriageStatus
from engine.models import ScanResult


def test_finding_mutation_survives_a_refetch() -> None:
    finding = store.get_finding("finding_006")
    assert finding is not None
    updated = finding.model_copy(update={"triage": Triage(status=TriageStatus.FIXED, note="patched by test")})
    store.replace_finding("finding_006", updated, action="finding.triage")

    refetched = store.get_finding("finding_006")
    assert refetched is not None
    assert refetched.triage.status == "fixed"
    assert refetched.triage.note == "patched by test"


def test_replace_finding_missing_id_raises_keyerror() -> None:
    finding = store.get_finding("finding_001")
    assert finding is not None
    try:
        store.replace_finding("does-not-exist", finding)
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_audit_log_records_scan_creation() -> None:
    payload = ScanCreate(path="/tmp/audit-test")
    scan = store.create_scan_from_result(payload, ScanResult(), store.resolve_policy(payload))
    with db.session_scope() as session:
        rows = session.exec(
            select(AuditLogRecord).where(AuditLogRecord.entity_id == scan.id)
        ).all()
    assert len(rows) == 1
    assert rows[0].action == "scan.create"


def test_audit_log_records_triage_patch() -> None:
    finding = store.get_finding("finding_005")
    assert finding is not None
    updated = finding.model_copy(update={"triage": Triage(status=TriageStatus.ACCEPTED_RISK)})
    store.replace_finding("finding_005", updated, action="finding.triage")

    with db.session_scope() as session:
        rows = session.exec(
            select(AuditLogRecord).where(
                AuditLogRecord.entity_id == "finding_005", AuditLogRecord.action == "finding.triage"
            )
        ).all()
    assert len(rows) >= 1


def test_audit_log_records_policy_put() -> None:
    policy = Policy(
        id="policy_audit_test", name="audit test", crqcYears=7,
        default=Context(exposure=Exposure.INTERNAL, criticality=Criticality.LOW, shelfLifeYears=1, migrationYears=1),
        contexts=[],
    )
    store.put_policy(policy)
    with db.session_scope() as session:
        rows = session.exec(
            select(AuditLogRecord).where(
                AuditLogRecord.entity_id == "policy_audit_test", AuditLogRecord.action == "policy.put"
            )
        ).all()
    assert len(rows) == 1


def test_new_scan_starts_with_no_findings() -> None:
    payload = ScanCreate(path="/tmp/empty-scan")
    scan = store.create_scan_from_result(payload, ScanResult(), store.resolve_policy(payload))
    assert store.list_findings(scan.id) == []


def test_init_db_reseed_is_idempotent() -> None:
    db.init_db()
    db.init_db()
    assert store.get_scan("scan_stub_001") is not None
    assert len(store.list_findings("scan_stub_001")) == 6


def test_scan_timestamps_survive_db_round_trip_as_utc() -> None:
    """Regression: SQLite drops tzinfo on stored datetimes; api.db._as_utc
    must reattach UTC on read so API responses keep their 'Z' suffix
    (caught manually by booting a real server and restarting it)."""
    scan = store.get_scan("scan_stub_001")
    assert scan is not None
    assert scan.startedAt.tzinfo is not None
    assert scan.finishedAt is not None
    assert scan.finishedAt.tzinfo is not None
