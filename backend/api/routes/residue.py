"""Crypto debt ledger residue cluster endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api import store
from api.models import ResidueCluster, ResidueClusterPatch, ResidueClusterState

router = APIRouter(tags=["debt"])


@router.get("/residue", response_model=list[ResidueCluster])
def list_residue_clusters(
    state: ResidueClusterState | None = Query(default=None),  # noqa: B008
    targetId: str | None = Query(default=None),  # noqa: B008
) -> list[ResidueCluster]:
    """List crypto debt residue clusters across scans and targets."""
    return store.list_residue_clusters(state=state, target_id=targetId)


@router.get("/residue/{id}", response_model=ResidueCluster)
def get_residue_cluster(id: str) -> ResidueCluster:
    """Get details of a specific crypto debt residue cluster."""
    cluster = store.get_residue_cluster(id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="residue cluster not found")
    return cluster


@router.patch("/residue/{id}", response_model=ResidueCluster)
def patch_residue_cluster(id: str, patch: ResidueClusterPatch) -> ResidueCluster:
    """Transition state of a residue cluster (open -> promoted | excluded | accepted)."""
    # Validation per Track A1 M3 rules:
    # Excluding REQUIRES a justification and an owner (reject without them).
    if patch.state == ResidueClusterState.EXCLUDED:
        if not patch.justification or not patch.justification.strip():
            raise HTTPException(status_code=400, detail="Exclusion requires a non-empty justification")
        if not patch.owner or not patch.owner.strip():
            raise HTTPException(status_code=400, detail="Exclusion requires a non-empty owner")

    cluster = store.patch_residue_cluster(id, patch)
    if cluster is None:
        raise HTTPException(status_code=404, detail="residue cluster not found")
    return cluster
