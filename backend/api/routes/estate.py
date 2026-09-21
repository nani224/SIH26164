"""Estate-wide cryptographic inventory and posture analytics endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlmodel import col, select

from api import db
from api.db_models import (
    AlertRecord,
    AssetCriticalityRecord,
    FindingRecord,
    ScanRecord,
    ScanSnapshotRecord,
    TargetRecord,
)
from api.models import EstateCoverage, EstateSummary, EstateTrend, EstateTrendPoint

router = APIRouter(tags=["estate"])


@router.get("/estate/summary", response_model=EstateSummary)
def get_estate_summary() -> EstateSummary:
    """Compute an estate-wide cryptographic posture and inventory summary."""
    with db.session_scope() as session:
        total_targets = len(session.exec(select(TargetRecord)).all())
        total_scans = len(session.exec(select(ScanRecord)).all())

        findings = session.exec(select(FindingRecord)).all()
        total_findings = len(findings)

        critical_findings = sum(
            1 for f in findings
            if f.risk_band == "critical" or (f.risk_score is not None and f.risk_score >= 60.0)
        )

        active_alerts = len(
            session.exec(select(AlertRecord).where(AlertRecord.acknowledged == False)).all()  # noqa: E712
        )

        pqc_findings = sum(
            1 for f in findings
            if f.family in ("ML-KEM", "ML-DSA", "SLH-DSA") or (f.risk_score is not None and f.risk_score <= 15.0)
        )
        if total_findings == 0:
            pqc_readiness = 100.0
        else:
            pqc_readiness = round(max(0.0, min(100.0, (pqc_findings / total_findings) * 100.0)), 1)

        # v1.0 PS clause (i)/(iii): internal vs external facing reported as
        # a first-class split, from the explicit AssetCriticality ledger --
        # not inferred from Policy Context exposure (a separate, coarser
        # signal that existed before v1.0).
        criticalities = session.exec(select(AssetCriticalityRecord)).all()
        internal_facing = sum(1 for c in criticalities if c.facing == "internal")
        external_facing = sum(1 for c in criticalities if c.facing == "external")

        return EstateSummary(
            totalTargets=total_targets,
            totalScans=total_scans,
            totalFindings=total_findings,
            criticalFindings=critical_findings,
            pqcReadinessScore=pqc_readiness,
            activeAlerts=active_alerts,
            internalFacingAssets=internal_facing,
            externalFacingAssets=external_facing,
        )


@router.get("/estate/trend", response_model=EstateTrend)
def get_estate_trend(days: int = Query(default=30, ge=1, le=365)) -> EstateTrend:
    """Historical estate cryptographic risk trend over the requested number of days."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=days)

    with db.session_scope() as session:
        snapshots = session.exec(
            select(ScanSnapshotRecord)
            .where(ScanSnapshotRecord.taken_at >= cutoff)
            .order_by(col(ScanSnapshotRecord.taken_at).asc())
        ).all()

        # Group snapshots by YYYY-MM-DD
        by_date: dict[str, list[ScanSnapshotRecord]] = {}
        for s in snapshots:
            d_str = (s.taken_at.date() if s.taken_at else now.date()).isoformat()
            by_date.setdefault(d_str, []).append(s)

        # Build day-by-day continuous trend
        points: list[EstateTrendPoint] = []
        for offset in range(days):
            day_dt = (now - timedelta(days=days - 1 - offset)).date()
            d_str = day_dt.isoformat()

            day_snaps = by_date.get(d_str, [])
            if day_snaps:
                total_f = sum(s.total_findings for s in day_snaps) // len(day_snaps)
                crit = sum(s.bands.get("critical", 0) for s in day_snaps) // len(day_snaps)
                # Per-snapshot weighted score (critical/high bands, findings-weighted),
                # averaged across the day's snapshots. Found via the G3 functional-proof
                # pass: the previous version divided one day's SUM of per-snapshot
                # crit_weighted values by a single day-average total_f, producing scores
                # far outside the formula's intended 0-100 range (e.g. 400.0 for a day
                # with 5 snapshots) whenever more than one snapshot landed on the same
                # day -- exactly the real-scheduler scenario this endpoint exists for.
                # The existing unit test only checked the response shape, not the value,
                # so this never surfaced until a real multi-scan day was exercised.
                per_snapshot_scores = [
                    (s.bands.get("critical", 0) * 80.0 + s.bands.get("high", 0) * 40.0) / max(1, s.total_findings)
                    for s in day_snaps
                ]
                avg_score = round(sum(per_snapshot_scores) / len(day_snaps), 1)
            else:
                total_f = 0
                crit = 0
                avg_score = 0.0

            points.append(
                EstateTrendPoint(
                    date=d_str,
                    avgRiskScore=avg_score,
                    criticalCount=crit,
                    totalFindings=total_f,
                )
            )

        return EstateTrend(days=days, points=points)


@router.get("/estate/coverage", response_model=EstateCoverage)
def get_estate_coverage() -> EstateCoverage:
    """Get aggregated crypto coverage and debt trends across the estate."""
    from api import store
    return store.get_estate_coverage()

