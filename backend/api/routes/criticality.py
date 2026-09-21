"""Business criticality and ownership classification endpoints (PS clause iii)."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api import store
from api.models import (
    AssetCriticality,
    AssetFacing,
    Criticality,
    CriticalityImportResponse,
    CriticalitySource,
)

router = APIRouter(tags=["criticality"])


@router.get("/criticality", response_model=list[AssetCriticality])
def list_criticalities(targetId: str | None = Query(default=None)) -> list[AssetCriticality]:  # noqa: B008
    """List asset business criticalities and ownership mappings."""
    return store.list_asset_criticalities(target_id=targetId)


@router.put("/criticality", response_model=AssetCriticality)
def set_criticality(criticality: AssetCriticality) -> AssetCriticality:
    """Set or update asset business criticality mapping."""
    return store.set_asset_criticality(criticality)


@router.post("/criticality/import", response_model=CriticalityImportResponse)
async def import_criticality_csv(file: UploadFile = File(...)) -> CriticalityImportResponse:  # noqa: B008
    """Import asset business criticalities from CSV (CMDB bulk load)."""
    try:
        content = await file.read()
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))

        records: list[AssetCriticality] = []
        for row in reader:
            target_id = row.get("targetId") or row.get("target_id") or ""
            path_pattern = row.get("pathPattern") or row.get("path_pattern") or "**"
            crit_raw = (row.get("criticality") or "medium").lower()
            if crit_raw == "critical":
                crit_val = Criticality.MISSION_CRITICAL
            elif crit_raw in ("mission-critical", "high", "medium", "low"):
                crit_val = Criticality(crit_raw)
            else:
                crit_val = Criticality.MEDIUM

            owner = row.get("businessOwner") or row.get("owner") or "SecOps"
            data_class = row.get("dataClassification") or row.get("classification") or "Confidential"
            facing_raw = (row.get("facing") or "internal").lower()
            facing_val = AssetFacing.EXTERNAL if facing_raw == "external" else AssetFacing.INTERNAL

            rec = AssetCriticality(
                targetId=target_id,
                pathPattern=path_pattern,
                criticality=crit_val,
                businessOwner=owner,
                dataClassification=data_class,
                facing=facing_val,
                source=CriticalitySource.IMPORT,
            )
            saved = store.set_asset_criticality(rec)
            records.append(saved)

        return CriticalityImportResponse(imported=len(records), records=records)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to import CSV: {exc}") from exc
