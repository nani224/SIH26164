"""Tests for estate analytics (summary, trends) and audit log chain verification endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import col, select

from api import db
from api.db_models import AuditLogRecord
from api.main import app
from api.models import AuditVerifyStatus


def test_audit_verify_endpoint_valid_chain() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == AuditVerifyStatus.VALID
    assert data["recordCount"] >= 1
    assert len(data["headHash"]) == 64
    assert data["details"] is None


def test_audit_verify_endpoint_detects_tampering() -> None:
    client = TestClient(app)

    # Tamper with an existing audit log record
    with db.session_scope() as session:
        first_rec = session.exec(select(AuditLogRecord).order_by(col(AuditLogRecord.id).asc())).first()
        assert first_rec is not None
        orig_hash = first_rec.record_hash
        first_rec.record_hash = "deadbeef" * 8
        session.add(first_rec)
        session.commit()

        # Call endpoint - should detect tampering
        resp = client.get("/api/v1/audit/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == AuditVerifyStatus.TAMPERED
        assert "Tampered record" in (data["details"] or "")

        # Restore original hash
        first_rec.record_hash = orig_hash
        session.add(first_rec)
        session.commit()


def test_estate_summary_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/v1/estate/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert "totalTargets" in data
    assert "totalScans" in data
    assert "totalFindings" in data
    assert "criticalFindings" in data
    assert "pqcReadinessScore" in data
    assert "activeAlerts" in data

    assert data["totalScans"] >= 1
    assert data["totalFindings"] >= 1
    assert 0.0 <= data["pqcReadinessScore"] <= 100.0


def test_estate_trend_endpoint() -> None:
    client = TestClient(app)

    # 1. Default 30 days
    resp = client.get("/api/v1/estate/trend")
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 30
    assert len(data["points"]) == 30
    for pt in data["points"]:
        assert "date" in pt
        assert "avgRiskScore" in pt
        assert "criticalCount" in pt
        assert "totalFindings" in pt

    # 2. Custom 7 days
    resp7 = client.get("/api/v1/estate/trend?days=7")
    assert resp7.status_code == 200
    data7 = resp7.json()
    assert data7["days"] == 7
    assert len(data7["points"]) == 7

    # Every point's avgRiskScore must stay within the formula's own 0-100
    # scale, regardless of how many snapshots landed on that day -- this is
    # the value-level check the two assertions above never made (shape only).
    for pt in data["points"]:
        assert 0.0 <= pt["avgRiskScore"] <= 100.0, (
            f"avgRiskScore {pt['avgRiskScore']} on {pt['date']} is outside 0-100"
        )


def test_estate_trend_multiple_snapshots_same_day_stays_in_range(client: TestClient) -> None:
    """Regression test (G3 functional-proof pass): a real scheduled target
    that scans multiple times in one day used to blow avgRiskScore far past
    100 (400.0 observed with 5 same-day critical snapshots) because the
    aggregation summed each snapshot's weighted score across the day instead
    of averaging them. Reproduces the same shape directly against the store,
    without waiting on a real cron."""
    from datetime import UTC, datetime

    from api import store
    from api.models import (
        CryptoFunction,
        Finding,
        FindingKind,
        FindingSource,
        Location,
        Risk,
        RiskBand,
        ScanCreate,
        ScanStats,
        Surface,
        TargetCreate,
        TargetKind,
        Triage,
    )
    from engine.models import ScanResult

    target = store.create_target(
        TargetCreate(
            name="Trend Regression Target",
            kind=TargetKind.PATH,
            uri="/dummy/trend-path",
            policyId="default",
            schedule="0 0 * * *",
            enabled=True,
        )
    )
    policy = store.resolve_policy(ScanCreate(path="/dummy/trend-path"))
    empty_stats = ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0)

    def critical_finding(idx: int) -> Finding:
        return Finding(
            id=f"trend_find_{idx}",
            kind=FindingKind.ALGORITHM,
            surface=Surface.SOURCE,
            family=None,
            displayName="RSA-1024",
            function=CryptoFunction.KEYGEN,
            location=Location(path="app.py", line=idx),
            symbol="rsa.generate",
            snippet="rsa.generate(1024)",
            source=FindingSource.AST,
            confidence=0.9,
            risk=Risk(
                score=90.0, band=RiskBand.CRITICAL,
                V=1.0, F=1.0, U=1.0, E=1.0, K=1.0, X=5.0, Y=10.0, Z=10.0,
                moscaMargin=5.0, reason="Unencrypted private key", classicallyBroken=False,
                hndl=False, needsReview=False,
            ),
            triage=Triage(),
        )

    # 5 same-day scans, each with exactly 1 critical finding -- the exact
    # shape that produced avgRiskScore=400.0 before the fix.
    for i in range(5):
        scan = store.create_scan_from_result(
            payload=ScanCreate(path="/dummy/trend-path"),
            result=ScanResult(findings=[critical_finding(i)], stats=empty_stats),
            policy=policy,
            target_override=target.name,
        )
        store.create_snapshot(target.id, scan, [critical_finding(i)])

    resp = client.get("/api/v1/estate/trend?days=1")
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 1
    today = points[0]
    assert today["date"] == datetime.now(UTC).date().isoformat()
    assert 0.0 <= today["avgRiskScore"] <= 100.0, (
        f"avgRiskScore {today['avgRiskScore']} is outside 0-100 with 5 same-day critical snapshots"
    )
    # Every snapshot here is 100% critical (1 critical / 1 finding each), so
    # the per-snapshot weighted score is exactly 80.0 (the critical-band
    # weight) for all 5, and the day average must equal that exactly.
    assert today["avgRiskScore"] == 80.0
