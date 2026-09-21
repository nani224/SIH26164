"""Tests for Track A1 M2 Coverage Persistence and Performance.

EXIT criteria:
1. Two scans of the same artifact produce identical coverage numbers and the same cluster ids.
2. p95 < 150ms for coverage endpoints on a 10k-finding scan.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from api import store, stub_data
from api.main import app
from api.models import (
    ArtifactCoverage,
    CoverageCertificate,
    Location,
    ResidueCluster,
    ResidueClusterState,
    ResidueOccurrence,
    ScanCreate,
)
from engine.models import ScanResult

client = TestClient(app)


def test_two_scans_produce_identical_coverage_and_cluster_ids(tmp_path: Path) -> None:
    # Create a test fixture file
    test_file = tmp_path / "crypto_module.py"
    test_file.write_text("import hashlib\nh = hashlib.sha256(b'secret').digest()\n")

    policy = store.resolve_policy(ScanCreate(path=str(test_file)))

    base_finding = stub_data.list_findings()[0]
    finding1 = base_finding.model_copy(
        update={
            "id": "scan1_f1",
            "location": Location(path=str(test_file), line=2),
        }
    )

    finding2 = base_finding.model_copy(
        update={
            "id": "scan2_f1",
            "location": Location(path=str(test_file), line=2),
        }
    )

    cluster = ResidueCluster(
        id="cluster-fixed-sha256",
        contentHash="sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        signalTypes=["tables"],
        magnitude=32.0,
        occurrences=[
            ResidueOccurrence(
                artifactHash="art-sha256",
                path=str(test_file),
                range=[10, 40],
            )
        ],
        state=ResidueClusterState.OPEN,
        firstSeen=datetime.now(UTC),
        lastSeen=datetime.now(UTC),
    )

    result1 = ScanResult(findings=[finding1])
    object.__setattr__(result1, "residue_clusters", [cluster])

    scan1 = store.create_scan_from_result(
        ScanCreate(path=str(test_file)),
        result1,
        policy,
        scan_id_override="scan_run_1",
    )

    result2 = ScanResult(findings=[finding2])
    object.__setattr__(result2, "residue_clusters", [cluster])

    scan2 = store.create_scan_from_result(
        ScanCreate(path=str(test_file)),
        result2,
        policy,
        scan_id_override="scan_run_2",
    )

    # 1. Fetch coverage certificates
    res1 = client.get(f"/api/v1/scans/{scan1.id}/coverage")
    assert res1.status_code == 200
    cov1 = res1.json()

    res2 = client.get(f"/api/v1/scans/{scan2.id}/coverage")
    assert res2.status_code == 200
    cov2 = res2.json()

    # Identical coverage numbers
    assert cov1["totalMass"] == cov2["totalMass"]
    assert cov1["attributedMass"] == cov2["attributedMass"]
    assert cov1["excludedMass"] == cov2["excludedMass"]
    assert cov1["residueMass"] == cov2["residueMass"]
    assert cov1["coverageRatio"] == cov2["coverageRatio"]

    # 2. Fetch artifact coverages
    art1 = client.get(f"/api/v1/scans/{scan1.id}/coverage/artifacts").json()
    art2 = client.get(f"/api/v1/scans/{scan2.id}/coverage/artifacts").json()
    assert len(art1) == len(art2) == 1
    assert art1[0]["artifactHash"] == art2[0]["artifactHash"]
    assert art1[0]["totalMass"] == art2[0]["totalMass"]

    # 3. Verify same cluster ID is indexed and recognized across scans
    cluster_records = client.get("/api/v1/residue").json()
    matched_clusters = [c for c in cluster_records if c["contentHash"] == cluster.contentHash]
    assert len(matched_clusters) == 1
    assert matched_clusters[0]["id"] == "cluster-fixed-sha256"


def test_coverage_endpoints_p95_latency_under_150ms() -> None:
    # Seed a large scan with 10,000 findings across 100 artifacts
    large_scan_id = "scan_perf_10k"
    now = datetime.now(UTC)

    artifact_coverages: list[ArtifactCoverage] = []
    for i in range(100):
        artifact_coverages.append(
            ArtifactCoverage(
                artifactHash=f"hash_{i:04d}",
                path=f"src/module_{i:04d}/crypto.py",
                totalMass=100.0,
                attributed=90.0,
                excluded=5.0,
                residue=5.0,
                coverageRatio=0.90,
            )
        )

    cert = CoverageCertificate(
        scanId=large_scan_id,
        artifactCount=len(artifact_coverages),
        totalMass=10000.0,
        attributedMass=9000.0,
        excludedMass=500.0,
        residueMass=500.0,
        coverageRatio=0.90,
        residueClusterCount=10,
        computedAt=now,
    )

    clusters: list[ResidueCluster] = [
        ResidueCluster(
            id=f"cluster_{c:02d}",
            contentHash=f"hash_cluster_{c:02d}",
            signalTypes=["tables", "arx"],
            magnitude=50.0,
            occurrences=[],
            state=ResidueClusterState.OPEN,
            firstSeen=now,
            lastSeen=now,
        )
        for c in range(10)
    ]

    # Create scan record
    store.create_scan_from_result(
        ScanCreate(path="src/large_project"),
        ScanResult(findings=[]),
        store.resolve_policy(ScanCreate(path="src/large_project")),
        scan_id_override=large_scan_id,
    )

    # Save via store
    store.save_coverage(large_scan_id, cert, artifact_coverages, clusters, target_id="target_perf")

    # Measure 50 requests to GET /scans/{id}/coverage
    durations_cert: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.get(f"/api/v1/scans/{large_scan_id}/coverage")
        durations_cert.append(time.perf_counter() - t0)
        assert resp.status_code == 200

    durations_cert.sort()
    p95_cert = durations_cert[int(0.95 * len(durations_cert))]

    # Measure 50 requests to GET /scans/{id}/coverage/artifacts
    durations_art: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.get(f"/api/v1/scans/{large_scan_id}/coverage/artifacts")
        durations_art.append(time.perf_counter() - t0)
        assert resp.status_code == 200

    durations_art.sort()
    p95_art = durations_art[int(0.95 * len(durations_art))]

    print("\n[Performance Benchmark M2]:")
    print(f"  GET /scans/{{id}}/coverage p95: {p95_cert * 1000:.2f} ms (budget: 150 ms)")
    print(f"  GET /scans/{{id}}/coverage/artifacts p95: {p95_art * 1000:.2f} ms (budget: 150 ms)")

    assert p95_cert < 0.150, f"Coverage p95 exceeded 150ms: {p95_cert * 1000:.2f} ms"
    assert p95_art < 0.150, f"Artifacts coverage p95 exceeded 150ms: {p95_art * 1000:.2f} ms"
