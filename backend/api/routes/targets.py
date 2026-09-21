from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from api import store
from api.models import (
    Drift,
    Scan,
    ScanSnapshot,
    Target,
    TargetCreate,
    TargetPatch,
)
from scheduler.engine import execute_target_scan, remove_target_job, schedule_target_job

log = structlog.get_logger("ecdat.api.targets")
router = APIRouter(tags=["targets"])


@router.get("/targets", response_model=list[Target])
def list_targets() -> list[Target]:
    targets = store.list_targets()
    log.info("targets_listed", count=len(targets))
    return targets


@router.post("/targets", response_model=Target, status_code=status.HTTP_201_CREATED)
def create_target(payload: TargetCreate) -> Target:
    target = store.create_target(payload)
    log.info("target_created", target_id=target.id, name=target.name)
    schedule_target_job(target)
    return target


@router.get("/targets/{id}", response_model=Target)
def get_target(id: str) -> Target:
    target = store.get_target(id)
    if target is None:
        log.warning("target_not_found", target_id=id)
        raise HTTPException(status_code=404, detail=f"Target {id} not found")
    log.info("target_fetched", target_id=id)
    return target


@router.patch("/targets/{id}", response_model=Target)
def patch_target(id: str, patch: TargetPatch) -> Target:
    target = store.patch_target(id, patch)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {id} not found")
    schedule_target_job(target)
    return target


@router.delete("/targets/{id}")
def delete_target(id: str) -> dict[str, bool]:
    deleted = store.delete_target(id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Target {id} not found")
    remove_target_job(id)
    return {"ok": True}


@router.post("/targets/{id}/scan-now", response_model=Scan, status_code=status.HTTP_201_CREATED)
def scan_target_now(id: str) -> Scan:
    target = store.get_target(id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {id} not found")
    scan = execute_target_scan(id)
    return scan


@router.get("/targets/{id}/snapshots", response_model=list[ScanSnapshot])
def list_target_snapshots(id: str) -> list[ScanSnapshot]:
    target = store.get_target(id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {id} not found")
    return store.list_snapshots(id)


@router.get("/targets/{id}/drift", response_model=Drift)
def get_target_drift(
    id: str,
    from_snapshot: str = Query(..., alias="from", description="Baseline snapshot ID"),
    to_snapshot: str = Query(..., alias="to", description="Target snapshot ID"),
) -> Drift:
    target = store.get_target(id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {id} not found")

    drift = store.calculate_drift(id, from_snapshot, to_snapshot)
    if drift is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Drift computation failed: snapshot '{from_snapshot}' or '{to_snapshot}' "
                f"not found for target '{id}'"
            ),
        )

    try:
        from api.alerts.rules import check_drift_alerts
        check_drift_alerts(id, drift)
    except Exception:
        pass

    return drift
