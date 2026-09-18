from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from api import store, stub_data
from api.cbom import build_cbom
from api.filtering import filter_findings, paginate
from api.models import (
    ErrorDetail,
    FindingPage,
    Graph,
    RemediationPlan,
    RemediationPlanItem,
    RescoreRequest,
    RescoreResult,
    Scan,
    ScanCreate,
    ScanStatus,
)
from api.pdf_report import build_executive_report_pdf
from engine.ingest import (
    IngestError,
    async_compute_stream_hash_and_save,
    safe_extract_archive,
)
from engine.models import ScanResult
from engine.scanner import scan as run_scan

router = APIRouter()


def _get_scan_or_404(scan_id: str) -> Scan:
    scan = store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return scan


@router.post("/scans", response_model=Scan, status_code=201)
async def create_scan(payload: ScanCreate) -> Scan:
    if not payload.path:
        raise HTTPException(status_code=400, detail="path is required (upload support is not implemented yet)")
    target = Path(payload.path)
    if not target.exists():
        raise HTTPException(status_code=400, detail=f"path does not exist: {payload.path}")

    policy = store.resolve_policy(payload)
    collected_events: list[tuple[str, dict[str, Any]]] = []

    def on_event(event_type: str, event_payload: dict[str, Any]) -> None:
        collected_events.append((event_type, event_payload))

    try:
        result = run_scan(target, policy, on_event=on_event)
        scan_status = ScanStatus.DONE
    except OSError:
        result = ScanResult()
        scan_status = ScanStatus.FAILED
    return store.create_scan_from_result(
        payload, result, policy, scan_status=scan_status, events=collected_events
    )


@router.post("/scans/upload", response_model=Scan, status_code=201)
async def upload_scan(
    file: UploadFile = File(...),  # noqa: B008
    policyId: str | None = Form(None),  # noqa: B008
    crqcYears: int | None = Form(10),  # noqa: B008
) -> Scan:
    filename = file.filename or "uploaded.zip"
    payload = ScanCreate(path=filename, policyId=policyId, crqcYears=crqcYears)
    policy = store.resolve_policy(payload)
    collected_events: list[tuple[str, dict[str, Any]]] = []

    def on_event(event_type: str, event_payload: dict[str, Any]) -> None:
        collected_events.append((event_type, event_payload))

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        archive_dest = tmp_path / Path(filename).name
        extract_dir = tmp_path / "sandbox"

        async def chunk_stream() -> AsyncIterator[bytes]:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

        try:
            bundle_hash, _ = await async_compute_stream_hash_and_save(chunk_stream(), archive_dest)
            safe_extract_archive(archive_dest, extract_dir)
        except IngestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            result = run_scan(extract_dir, policy, on_event=on_event)
            scan_status = ScanStatus.DONE
        except OSError:
            result = ScanResult()
            scan_status = ScanStatus.FAILED

        return store.create_scan_from_result(
            payload,
            result,
            policy,
            scan_status=scan_status,
            events=collected_events,
            bundle_hash=bundle_hash,
            target_override=filename,
        )


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
        store.list_findings(scan_id),
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
async def rescore_scan(scan_id: str, payload: RescoreRequest) -> Response:
    bands, content_bytes = store.rescore_scan_findings(scan_id, payload.crqcYears)
    if bands is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return Response(
        content=content_bytes,
        media_type="application/json",
    )


@router.get("/scans/{scan_id}/graph", response_model=Graph)
async def get_graph(scan_id: str) -> Graph:
    _get_scan_or_404(scan_id)
    return Graph(nodes=stub_data.default_graph_nodes(), edges=stub_data.default_graph_edges())


@router.get("/scans/{scan_id}/cbom")
async def get_cbom(scan_id: str, response: Response) -> dict[str, Any]:
    scan = _get_scan_or_404(scan_id)
    findings = store.list_findings(scan_id)
    cbom = build_cbom(scan, findings)
    cbom_bytes = json.dumps(cbom, sort_keys=True).encode("utf-8")
    response.headers["X-CBOM-SHA256"] = hashlib.sha256(cbom_bytes).hexdigest()
    return cbom


@router.get("/scans/{scan_id}/plan", response_model=RemediationPlan)
async def get_plan(scan_id: str) -> RemediationPlan:
    _get_scan_or_404(scan_id)
    band_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings = [f for f in store.list_findings(scan_id) if f.recommendation is not None and f.risk is not None]
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
    scan = _get_scan_or_404(scan_id)
    findings = store.list_findings(scan_id)
    pdf_bytes = build_executive_report_pdf(scan, findings)
    headers = {
        "Content-Disposition": f'inline; filename="ecdat-report-{scan_id}.pdf"',
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


_MAX_EVENTS_PER_SEC = 10


@router.websocket("/scans/{scan_id}/events")
async def scan_events(websocket: WebSocket, scan_id: str, after: int = 0) -> None:
    """Replays the real, stored event log for a scan (see engine.scanner's
    on_event callback + store.create_scan_from_result). Scanning is
    synchronous, so this always replays a completed scan's history rather
    than streaming one live -- pass `after=<last eventId you saw>` to
    resume without re-receiving events already delivered.
    """
    await websocket.accept()
    scan = store.get_scan(scan_id)
    if scan is None:
        await websocket.send_json({"type": "error", "eventId": "1", "message": "scan not found"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    events = store.list_events(scan_id, after=after or None)
    try:
        for i, event in enumerate(events):
            frame: dict[str, Any] = {"type": event.type, "eventId": str(event.event_id), **event.payload}
            await websocket.send_json(frame)
            if i < len(events) - 1:
                await asyncio.sleep(1 / _MAX_EVENTS_PER_SEC)
        await websocket.close()
    except WebSocketDisconnect:
        return
