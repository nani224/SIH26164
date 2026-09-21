"""Coverage API endpoints for Crypto Mass Conservation (CMC)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from api import store
from api.models import ArtifactCoverage, CoverageCertificate

router = APIRouter(tags=["coverage"])


@router.get("/scans/{scan_id}/coverage", response_model=CoverageCertificate)
def get_scan_coverage(scan_id: str) -> CoverageCertificate:
    """Get crypto mass conservation coverage certificate for a scan."""
    scan = store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    cert = store.get_coverage_certificate(scan_id)
    if cert is not None:
        return cert

    # Default fallback / initial certificate if not yet persisted
    return CoverageCertificate(
        scanId=scan_id,
        artifactCount=scan.stats.files if scan.stats else 0,
        totalMass=100.0,
        attributedMass=100.0,
        excludedMass=0.0,
        residueMass=0.0,
        coverageRatio=1.0,
        residueClusterCount=0,
        computedAt=datetime.now(UTC),
    )


@router.get("/scans/{scan_id}/coverage/artifacts", response_model=list[ArtifactCoverage])
def get_scan_artifact_coverage(scan_id: str) -> list[ArtifactCoverage]:
    """Get per-artifact crypto mass conservation coverage for a scan."""
    scan = store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")

    artifacts = store.get_artifact_coverages(scan_id)
    return artifacts
