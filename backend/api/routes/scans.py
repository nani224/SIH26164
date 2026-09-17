from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from api import store, stub_data
from api.cbom import build_cbom
from api.filtering import band_counts, filter_findings, paginate
from api.models import (
    ErrorDetail,
    Finding,
    FindingPage,
    Graph,
    RemediationPlan,
    RemediationPlanItem,
    RescoreRequest,
    RescoreResult,
    RiskBand,
    Scan,
    ScanCreate,
)
from api.pdf_stub import build_stub_report_pdf
from engine.risk import rescore as rescore_formula

router = APIRouter()


def _get_scan_or_404(scan_id: str) -> Scan:
    scan = store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return scan


@router.post("/scans", response_model=Scan, status_code=201)
async def create_scan(payload: ScanCreate) -> Scan:
    return store.create_scan(payload)


@router.get("/scans", response_model=list[Scan])
async def list_scans() -> list[Scan]:
    return store.list_scans()


@router.get("/scans/{scan_id}", response_model=Scan, responses={404: {"model": ErrorDetail}})
async def get_scan(scan_id: str) -> Scan:
    return _get_scan_or_404(scan_id)


@router.get("/scans/{scan_id}/findings", response_model=FindingPage)
async def get_findings(
    scan_id: str,
    band: str | None = None,
    family: str | None = None,
    surface: str | None = None,
    source: str | None = None,
    minConfidence: float | None = Query(default=None, ge=0, le=1),
    needsReview: bool | None = None,
    q: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    sort: str | None = None,
) -> FindingPage:
    _get_scan_or_404(scan_id)
    filtered = filter_findings(
        stub_data.list_findings(),
        band=band,
        family=family,
        surface=surface,
        source=source,
        min_confidence=minConfidence,
        needs_review=needsReview,
        q=q,
        sort=sort,
    )
    return paginate(filtered, cursor=cursor, limit=limit)


@router.post("/scans/{scan_id}/rescore", response_model=RescoreResult)
async def rescore_scan(scan_id: str, payload: RescoreRequest) -> RescoreResult:
    _get_scan_or_404(scan_id)
    changed: list[Finding] = []
    for finding in stub_data.list_findings():
        if finding.risk is None:
            continue
        new_z = payload.crqcYears if payload.crqcYears is not None else finding.risk.Z
        score, u, band = rescore_formula(
            v=finding.risk.V,
            f=finding.risk.F,
            e=finding.risk.E,
            k=finding.risk.K,
            x=finding.risk.X,
            y=finding.risk.Y,
            z=new_z,
            classically_broken=finding.risk.classicallyBroken,
        )
        if band != finding.risk.band or score != finding.risk.score:
            updated_risk = finding.risk.model_copy(
                update={
                    "score": score,
                    "U": u,
                    "band": RiskBand(band),
                    "Z": new_z,
                    "moscaMargin": finding.risk.X + finding.risk.Y - new_z,
                }
            )
            updated = finding.model_copy(update={"risk": updated_risk})
            stub_data.replace_finding(finding.id, updated)
            changed.append(updated)
    return RescoreResult(bands=band_counts(stub_data.list_findings()), changed=changed)


@router.get("/scans/{scan_id}/graph", response_model=Graph)
async def get_graph(scan_id: str) -> Graph:
    _get_scan_or_404(scan_id)
    return Graph(nodes=stub_data.default_graph_nodes(), edges=stub_data.default_graph_edges())


@router.get("/scans/{scan_id}/cbom")
async def get_cbom(scan_id: str) -> dict[str, Any]:
    scan = _get_scan_or_404(scan_id)
    return build_cbom(scan, stub_data.list_findings())


@router.get("/scans/{scan_id}/plan", response_model=RemediationPlan)
async def get_plan(scan_id: str) -> RemediationPlan:
    _get_scan_or_404(scan_id)
    band_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings = [f for f in stub_data.list_findings() if f.recommendation is not None and f.risk is not None]
    findings.sort(key=lambda f: band_priority.get(f.risk.band, 99) if f.risk else 99)
    items = [
        RemediationPlanItem(
            findingId=f.id,
            band=f.risk.band,
            displayName=f.displayName,
            location=f.location,
            action=f.recommendation.action,
            target=f.recommendation.target,
        )
        for f in findings
        if f.risk is not None and f.recommendation is not None
    ]
    return RemediationPlan(scanId=scan_id, generatedAt=datetime.now(UTC), items=items)


@router.get("/scans/{scan_id}/report.pdf")
async def get_report_pdf(scan_id: str) -> Response:
    _get_scan_or_404(scan_id)
    pdf_bytes = build_stub_report_pdf(scan_id)
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.websocket("/scans/{scan_id}/events")
async def scan_events(websocket: WebSocket, scan_id: str) -> None:
    await websocket.accept()
    scan = store.get_scan(scan_id)
    if scan is None:
        await websocket.send_json({"type": "error", "eventId": "1", "message": "scan not found"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    events: list[dict[str, Any]] = [
        {"type": "stage", "stage": "ingesting"},
        {"type": "progress", "percent": 40},
        {"type": "stage", "stage": "scanning"},
        {"type": "finding", "findingId": "finding_001"},
        {"type": "finding", "findingId": "finding_003"},
        {"type": "stage", "stage": "scoring"},
        {"type": "done", "scanId": scan_id},
    ]
    try:
        for i, event in enumerate(events, start=1):
            await websocket.send_json({**event, "eventId": str(i)})
            await asyncio.sleep(0.02)
        await websocket.close()
    except WebSocketDisconnect:
        return
