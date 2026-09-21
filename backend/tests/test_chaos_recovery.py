"""Chaos recovery test: Scan interrupted mid-run and recovered on startup."""

from sqlmodel import select

from api import db, store
from api.db_models import AuditLogRecord
from api.models import ScanCreate, ScanStatus, TargetCreate, TargetKind
from scheduler.engine import execute_target_scan, shutdown_scheduler, start_scheduler


def test_interrupted_scan_recovery_on_startup() -> None:
    """Mid-run interrupted scan is not left in 'done' state and is cleanly recovered to 'failed' on restart."""
    policy = store.resolve_policy(ScanCreate(path="test-corpus", policyId="default"))

    # 1. Target registered
    target = store.create_target(
        TargetCreate(
            name="chaos-target",
            kind=TargetKind.PATH,
            uri="test-corpus",
            policyId=policy.id,
            schedule="0 0 * * *",
        )
    )

    # 2. Simulate scan starting and being in progress
    in_flight_scan = store.create_initial_scan(
        payload=ScanCreate(path=target.uri, policyId=target.policyId),
        policy=policy,
        target_override=target.name,
    )

    # Verify that in-flight scan is in SCANNING state, NEVER in DONE state
    fetched_before = store.get_scan(in_flight_scan.id)
    assert fetched_before is not None
    assert fetched_before.status == ScanStatus.SCANNING
    assert fetched_before.finishedAt is None

    # 3. Simulate process kill / mid-run crash (execution halted while in SCANNING)
    # On restart, recovery runs during lifespan startup
    recovered_ids = store.recover_interrupted_scans()
    assert in_flight_scan.id in recovered_ids

    # 4. Verify post-restart state: cleanly marked FAILED, not corrupt or DONE
    fetched_after = store.get_scan(in_flight_scan.id)
    assert fetched_after is not None
    assert fetched_after.status == ScanStatus.FAILED
    assert fetched_after.finishedAt is not None

    # 5. Verify audit log recorded the interrupted scan recovery
    with db.session_scope() as session:
        audit_logs = session.exec(
            select(AuditLogRecord).where(
                AuditLogRecord.entity_id == in_flight_scan.id,
                AuditLogRecord.action == "scan.recovery",
            )
        ).all()
        assert len(audit_logs) >= 1
        assert audit_logs[0].detail.get("previous_status") == ScanStatus.SCANNING.value

    # 6. Verify scheduler starts and resumes normally without corruption
    try:
        start_scheduler()
        # Normal scan after recovery succeeds cleanly
        subsequent_scan = execute_target_scan(target.id)
        assert subsequent_scan.status == ScanStatus.DONE
    finally:
        shutdown_scheduler()
