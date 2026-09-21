"""ECDAT In-process Scheduler Engine using APScheduler.

Operates strictly in-process with zero external message brokers (no Redis/Celery).
Supports Cron trigger evaluations per Target, target scan-now execution,
automatic snapshot creation, and background job scheduling.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

from api import store
from api.models import Scan, ScanCreate, ScanStats, ScanStatus, Target
from engine.models import ScanResult
from engine.scanner import scan as engine_scan

logger = logging.getLogger("ecdat.scheduler")

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
    return _scheduler


def start_scheduler() -> None:
    sched = get_scheduler()
    if not sched.running:
        sched.start()
        sync_all_target_jobs()
        logger.info("ECDAT scheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("ECDAT scheduler stopped")
    _scheduler = None


def _parse_trigger(schedule_expr: str) -> Any:
    """Parses a schedule expression into an APScheduler trigger.

    Supports:
    - 5-part cron syntax (e.g., '0 0 * * *', '*/15 * * * *')
    - Shorthands like '@daily', '@hourly'
    - Interval syntax (e.g., 'every 10 minutes', 'every 30 seconds', '10m', '30s')
    """
    expr = schedule_expr.strip()

    # Handle standard cron
    parts = expr.split()
    if len(parts) == 5:
        return CronTrigger.from_crontab(expr, timezone="UTC")

    if expr == "@hourly":
        return CronTrigger.from_crontab("0 * * * *", timezone="UTC")
    if expr == "@daily":
        return CronTrigger.from_crontab("0 0 * * *", timezone="UTC")
    if expr == "@weekly":
        return CronTrigger.from_crontab("0 0 * * 0", timezone="UTC")

    # Handle interval fallback
    if expr.startswith("every "):
        rest = expr.removeprefix("every ").strip()
        tokens = rest.split()
        if len(tokens) == 2 and tokens[0].isdigit():
            count = int(tokens[0])
            unit = tokens[1].lower()
            if "sec" in unit:
                return IntervalTrigger(seconds=count, timezone="UTC")
            if "min" in unit:
                return IntervalTrigger(minutes=count, timezone="UTC")
            if "hour" in unit:
                return IntervalTrigger(hours=count, timezone="UTC")
            if "day" in unit:
                return IntervalTrigger(days=count, timezone="UTC")

    # Default fallback: 1 hour interval
    return IntervalTrigger(hours=1, timezone="UTC")


def schedule_target_job(target: Target) -> None:
    sched = get_scheduler()
    job_id = f"target_scan_{target.id}"

    # Remove existing job if any
    if sched.get_job(job_id):
        sched.remove_job(job_id)

    if not target.enabled:
        return

    try:
        trigger = _parse_trigger(target.schedule)
        sched.add_job(
            execute_target_scan,
            trigger=trigger,
            id=job_id,
            name=f"Scan Target {target.name} ({target.id})",
            args=[target.id],
            replace_existing=True,
        )
        logger.info("Scheduled target scan job: targetId=%s schedule=%s", target.id, target.schedule)
    except Exception as exc:
        logger.error("Failed to schedule target job: targetId=%s schedule=%s error=%s", target.id, target.schedule, exc)


def remove_target_job(target_id: str) -> None:
    sched = get_scheduler()
    job_id = f"target_scan_{target_id}"
    if sched.get_job(job_id):
        sched.remove_job(job_id)
        logger.info("Removed target scan job: targetId=%s", target_id)


def sync_all_target_jobs() -> None:
    targets = store.list_targets()
    for target in targets:
        if target.enabled:
            schedule_target_job(target)
        else:
            remove_target_job(target.id)


def execute_target_scan(target_id: str) -> Scan:
    """Core target scan pipeline:

    1. Retrieves target details
    2. Runs scanner on target URI
    3. Persists scan & findings in store
    4. Automatically creates ScanSnapshot
    5. Updates target.lastScanId & target.lastScanAt
    6. Triggers alert rule evaluations (M4)
    """
    target = store.get_target(target_id)
    if target is None:
        raise ValueError(f"Target not found: {target_id}")

    policy = store.resolve_policy(ScanCreate(path=target.uri, policyId=target.policyId), target_id=target.id)
    now = datetime.now(UTC)

    # Perform real engine scan if path/repo exists, otherwise create empty/stub result
    target_path = Path(target.uri)
    if not target_path.is_absolute():
        target_path = target_path.resolve()

    initial_scan = store.create_initial_scan(
        payload=ScanCreate(path=target.uri, policyId=target.policyId, crqcYears=policy.crqcYears),
        policy=policy,
        target_override=target.name,
    )

    result: ScanResult
    scan_status = ScanStatus.DONE
    try:
        if target_path.exists():
            result = engine_scan(target_path, policy=policy)
        else:
            result = ScanResult(
                findings=[],
                stats=ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0),
            )
    except Exception as exc:
        logger.warning("Target scan path execution exception: %s", exc)
        result = ScanResult(
            findings=[],
            stats=ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0),
        )
        scan_status = ScanStatus.FAILED

    scan = store.create_scan_from_result(
        payload=ScanCreate(path=target.uri, policyId=target.policyId, crqcYears=policy.crqcYears),
        result=result,
        policy=policy,
        scan_status=scan_status,
        target_override=target.name,
        scan_id_override=initial_scan.id,
    )

    # Update target last scan tracking
    store.update_target_last_scan(target.id, scan.id, now)

    # Automatically persist ScanSnapshot
    findings = store.list_findings(scan.id)
    snapshot = store.create_snapshot(target.id, scan, findings)

    # Hook for Alert Rule Evaluation (Milestone 4)
    try:
        from api.alerts.rules import evaluate_scan_alerts

        evaluate_scan_alerts(target=target, scan=scan, snapshot=snapshot, findings=findings)
    except Exception as e:
        logger.warning("Alert evaluation failed during target scan: %s", e)

    return scan
