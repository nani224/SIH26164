"""Tests for Target CRUD, APScheduler integration, snapshots, and drift detection."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from api import db, store
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
from scheduler.engine import (
    get_scheduler,
    schedule_target_job,
    shutdown_scheduler,
    start_scheduler,
)


@pytest.fixture(autouse=True)
def _clean_db() -> None:
    db.init_db()


def test_target_crud(client: TestClient) -> None:
    # 1. Create target
    payload = {
        "name": "Core Auth Service",
        "kind": "path",
        "uri": "backend/api",
        "policyId": "default",
        "schedule": "0 0 * * *",
        "enabled": True,
    }
    resp = client.post("/api/v1/targets", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"].startswith("target_")
    assert created["name"] == "Core Auth Service"
    assert created["kind"] == "path"
    assert created["uri"] == "backend/api"
    assert created["enabled"] is True
    target_id = created["id"]

    # 2. Get target by id
    resp = client.get(f"/api/v1/targets/{target_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == target_id

    # 3. List targets
    resp = client.get("/api/v1/targets")
    assert resp.status_code == 200
    targets = resp.json()
    assert any(t["id"] == target_id for t in targets)

    # 4. Patch target
    patch_payload = {"name": "Core Auth Service Renamed", "schedule": "*/30 * * * *", "enabled": False}
    resp = client.patch(f"/api/v1/targets/{target_id}", json=patch_payload)
    assert resp.status_code == 200
    patched = resp.json()
    assert patched["name"] == "Core Auth Service Renamed"
    assert patched["schedule"] == "*/30 * * * *"
    assert patched["enabled"] is False

    # 5. Delete target
    resp = client.delete(f"/api/v1/targets/{target_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # 6. Verify 404 after delete
    resp = client.get(f"/api/v1/targets/{target_id}")
    assert resp.status_code == 404


def test_target_scan_now_and_snapshots(client: TestClient) -> None:
    # Create target pointing to backend/api (exists locally)
    target = store.create_target(
        TargetCreate(
            name="ScanNow Target",
            kind=TargetKind.PATH,
            uri=str(Path("api").resolve()),
            policyId="default",
            schedule="0 12 * * *",
            enabled=True,
        )
    )

    # Trigger scan-now
    resp = client.post(f"/api/v1/targets/{target.id}/scan-now")
    assert resp.status_code == 201
    scan = resp.json()
    assert scan["id"].startswith("scan_")
    assert scan["target"] == "ScanNow Target"

    # Verify target's lastScanId & lastScanAt were updated
    refreshed_target = store.get_target(target.id)
    assert refreshed_target is not None
    assert refreshed_target.lastScanId == scan["id"]
    assert refreshed_target.lastScanAt is not None

    # Verify snapshot was created automatically
    resp = client.get(f"/api/v1/targets/{target.id}/snapshots")
    assert resp.status_code == 200
    snapshots = resp.json()
    assert len(snapshots) >= 1
    snapshot = snapshots[0]
    assert snapshot["targetId"] == target.id
    assert snapshot["scanId"] == scan["id"]
    assert "bands" in snapshot
    assert "totalFindings" in snapshot


def test_drift_detection(client: TestClient) -> None:
    # Create target
    target = store.create_target(
        TargetCreate(
            name="Drift Test Target",
            kind=TargetKind.PATH,
            uri="/dummy/path",
            policyId="default",
            schedule="0 0 * * *",
            enabled=True,
        )
    )

    policy = store.resolve_policy(ScanCreate(path="/dummy/path"))

    # Baseline scan: finding A (critical) and finding B (medium)
    f_a = Finding(
        id="find_a",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=None,
        displayName="RSA-1024",
        function=CryptoFunction.KEYGEN,
        location=Location(path="auth/token.py", line=10),
        symbol="rsa.generate",
        snippet="rsa.generate(1024)",
        source=FindingSource.AST,
        confidence=0.9,
        risk=Risk(
            score=80.0,
            band=RiskBand.CRITICAL,
            V=1.0, F=1.0, U=0.8, E=1.0, K=1.0, X=5.0, Y=10.0, Z=10.0,
            moscaMargin=5.0, reason="Legacy RSA", classicallyBroken=False, hndl=False, needsReview=False,
        ),
        triage=Triage(),
    )
    f_b = Finding(
        id="find_b",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=None,
        displayName="AES-128",
        function=CryptoFunction.ENCRYPT,
        location=Location(path="storage/enc.py", line=20),
        symbol="aes.new",
        snippet="aes.new(key)",
        source=FindingSource.AST,
        confidence=0.95,
        risk=Risk(
            score=25.0,
            band=RiskBand.MEDIUM,
            V=0.5, F=1.0, U=0.5, E=1.0, K=1.0, X=5.0, Y=5.0, Z=10.0,
            moscaMargin=0.0, reason="AES symmetric", classicallyBroken=False, hndl=False, needsReview=False,
        ),
        triage=Triage(),
    )

    from engine.models import ScanResult
    empty_stats = ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0)
    scan1 = store.create_scan_from_result(
        payload=ScanCreate(path="/dummy/path"),
        result=ScanResult(findings=[f_a, f_b], stats=empty_stats),
        policy=policy,
        target_override=target.name,
    )
    snap1 = store.create_snapshot(target.id, scan1, [f_a, f_b])

    # Second scan:
    # - finding A is RESOLVED (removed)
    # - finding B is CHANGED (upgraded to low risk or changed band)
    # - finding C is ADDED (new finding)
    f_b_changed = f_b.model_copy(deep=True)
    f_b_changed.id = "find_b_v2"
    assert f_b_changed.risk is not None
    f_b_changed.risk.band = RiskBand.LOW
    f_b_changed.risk.score = 10.0

    f_c = Finding(
        id="find_c",
        kind=FindingKind.ALGORITHM,
        surface=Surface.SOURCE,
        family=None,
        displayName="SHA-1",
        function=CryptoFunction.DIGEST,
        location=Location(path="hash/util.py", line=5),
        symbol="sha1",
        snippet="hashlib.sha1()",
        source=FindingSource.AST,
        confidence=1.0,
        risk=Risk(
            score=95.0,
            band=RiskBand.CRITICAL,
            V=1.0, F=1.0, U=1.0, E=1.0, K=1.0, X=5.0, Y=10.0, Z=10.0,
            moscaMargin=5.0, reason="Broken digest", classicallyBroken=True, hndl=False, needsReview=False,
        ),
        triage=Triage(),
    )

    scan2 = store.create_scan_from_result(
        payload=ScanCreate(path="/dummy/path"),
        result=ScanResult(findings=[f_b_changed, f_c], stats=empty_stats),
        policy=policy,
        target_override=target.name,
    )
    snap2 = store.create_snapshot(target.id, scan2, [f_b_changed, f_c])

    # Calculate drift via API
    resp = client.get(f"/api/v1/targets/{target.id}/drift?from={snap1.id}&to={snap2.id}")
    assert resp.status_code == 200
    drift = resp.json()
    assert drift["targetId"] == target.id
    assert drift["fromSnapshotId"] == snap1.id
    assert drift["toSnapshotId"] == snap2.id

    # Verify partitions
    # 1. Added finding C
    assert len(drift["added"]) == 1
    assert drift["added"][0]["displayName"] == "SHA-1"

    # 2. Resolved finding A
    assert len(drift["resolved"]) == 1
    assert drift["resolved"][0]["displayName"] == "RSA-1024"

    # 3. Changed finding B (from medium to low)
    assert len(drift["changed"]) == 1
    changed_item = drift["changed"][0]
    assert changed_item["finding"]["displayName"] == "AES-128"
    assert changed_item["fromBand"] == "medium"
    assert changed_item["toBand"] == "low"

    # 4. Summary counts
    assert drift["summary"]["addedCount"] == 1
    assert drift["summary"]["resolvedCount"] == 1
    assert drift["summary"]["changedCount"] == 1


def test_drift_reports_falling_coverage_when_unexplained_crypto_appears(client: TestClient) -> None:
    """v1.0 CMC M4: a repo change that adds unexplained crypto (residue,
    not a real Finding) must show up as falling coverage in drift --
    "3 findings added, coverage fell" is the operator's real signal that
    something new and unexplained entered the estate, proven against the
    real HTTP drift endpoint, not just the store function directly."""
    from api.models import CoverageCertificate
    from engine.models import ScanResult

    target = store.create_target(
        TargetCreate(
            name="Coverage Drift Target",
            kind=TargetKind.PATH,
            uri="/dummy/coverage-path",
            policyId="default",
            schedule="0 0 * * *",
            enabled=True,
        )
    )
    policy = store.resolve_policy(ScanCreate(path="/dummy/coverage-path"))
    empty_stats = ScanStats(files=0, bytes=0, seconds=0.0, mbPerSec=0.0, errors=0, skippedPrefilter=0)

    # Scan 1: fully explained, no residue.
    result1 = ScanResult(findings=[], stats=empty_stats)
    result1.coverage_certificate = CoverageCertificate(  # type: ignore[attr-defined]
        scanId="placeholder",
        artifactCount=10,
        totalMass=100.0,
        attributedMass=100.0,
        excludedMass=0.0,
        residueMass=0.0,
        coverageRatio=1.0,
        residueClusterCount=0,
        computedAt=datetime.now(UTC),
    )
    scan1 = store.create_scan_from_result(
        payload=ScanCreate(path="/dummy/coverage-path"),
        result=result1,
        policy=policy,
        target_override=target.name,
    )
    snap1 = store.create_snapshot(target.id, scan1, [])
    assert snap1.coverageRatio == 1.0
    assert snap1.residueMass == 0.0

    # Scan 2: a real code change introduced high-entropy/unexplained
    # crypto-suspicion evidence the engine couldn't attribute to a
    # concrete Finding -- coverage genuinely falls.
    result2 = ScanResult(findings=[], stats=empty_stats)
    result2.coverage_certificate = CoverageCertificate(  # type: ignore[attr-defined]
        scanId="placeholder",
        artifactCount=10,
        totalMass=100.0,
        attributedMass=75.8,
        excludedMass=0.0,
        residueMass=24.2,
        coverageRatio=0.758,
        residueClusterCount=1,
        computedAt=datetime.now(UTC),
    )
    scan2 = store.create_scan_from_result(
        payload=ScanCreate(path="/dummy/coverage-path"),
        result=result2,
        policy=policy,
        target_override=target.name,
    )
    snap2 = store.create_snapshot(target.id, scan2, [])
    assert snap2.coverageRatio == 0.758
    assert snap2.residueMass == 24.2

    resp = client.get(f"/api/v1/targets/{target.id}/drift?from={snap1.id}&to={snap2.id}")
    assert resp.status_code == 200
    drift = resp.json()
    summary = drift["summary"]

    # The real signal: coverage fell, residue mass rose -- unexplained
    # crypto appeared even though no new Finding was added this time.
    assert summary["coverageDelta"] == pytest.approx(0.758 - 1.0, abs=1e-4)
    assert summary["coverageDelta"] < 0
    assert summary["residueMassDelta"] == pytest.approx(24.2, abs=1e-4)
    assert summary["residueMassDelta"] > 0


def test_scheduler_in_process_execution() -> None:
    # Test that APScheduler runs target scan in background thread
    start_scheduler()
    sched = get_scheduler()
    assert sched.running is True

    target = store.create_target(
        TargetCreate(
            name="Scheduler Interval Target",
            kind=TargetKind.PATH,
            uri="/test/scheduler",
            policyId="default",
            schedule="every 1 seconds",
            enabled=True,
        )
    )

    schedule_target_job(target)
    job = sched.get_job(f"target_scan_{target.id}")
    assert job is not None

    # Wait up to 4.5 seconds for background execution
    max_wait = 4.5
    start_t = time.time()
    ran = False
    while time.time() - start_t < max_wait:
        t = store.get_target(target.id)
        if t is not None and t.lastScanId is not None:
            ran = True
            break
        time.sleep(0.3)

    assert ran is True, "Scheduled scan did not fire within timeout"

    # Clean up
    shutdown_scheduler()
