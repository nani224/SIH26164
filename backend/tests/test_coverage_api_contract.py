"""Tests for Track A1 M1 Contract v1.0.0 endpoints and schemas."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from api import store
from api.main import app
from api.models import (
    CoverageCertificate,
    ResidueCluster,
    ResidueClusterState,
    ResidueOccurrence,
)

client = TestClient(app)


def test_coverage_endpoints() -> None:
    # 1. Get existing scan
    res = client.get("/api/v1/scans")
    assert res.status_code == 200
    scans = res.json()
    assert len(scans) > 0
    scan_id = scans[0]["id"]

    # 2. GET /scans/{id}/coverage
    res_cov = client.get(f"/api/v1/scans/{scan_id}/coverage")
    assert res_cov.status_code == 200
    cov = res_cov.json()
    assert cov["scanId"] == scan_id
    assert "coverageRatio" in cov
    assert "totalMass" in cov
    assert "attributedMass" in cov
    assert "excludedMass" in cov
    assert "residueMass" in cov
    assert "residueClusterCount" in cov
    assert "computedAt" in cov

    # 3. GET /scans/{id}/coverage/artifacts
    res_art = client.get(f"/api/v1/scans/{scan_id}/coverage/artifacts")
    assert res_art.status_code == 200
    assert isinstance(res_art.json(), list)

    # 4. 404 for nonexistent scan
    res_404 = client.get("/api/v1/scans/nonexistent-scan-id/coverage")
    assert res_404.status_code == 404


def test_residue_ledger_endpoints() -> None:
    # Create a test cluster via store
    cluster = ResidueCluster(
        id="test-cluster-1",
        contentHash="sha256:abc123def456",
        signalTypes=["tables", "entropy"],
        magnitude=42.5,
        occurrences=[
            ResidueOccurrence(
                artifactHash="art-1",
                path="crypto/custom_sbox.c",
                range=[100, 200],
            )
        ],
        state=ResidueClusterState.OPEN,
        firstSeen=datetime.now(UTC),
        lastSeen=datetime.now(UTC),
    )
    store.save_coverage(
        scan_id="scan-test",
        cert=CoverageCertificate.model_validate(
            client.get(f"/api/v1/scans/{client.get('/api/v1/scans').json()[0]['id']}/coverage").json()
        ),
        artifacts=[],
        clusters=[cluster],
        target_id="target-1",
    )

    # 1. GET /residue
    res = client.get("/api/v1/residue")
    assert res.status_code == 200
    clusters = res.json()
    assert len(clusters) > 0
    found = next((c for c in clusters if c["id"] == "test-cluster-1"), None)
    assert found is not None
    assert found["contentHash"] == "sha256:abc123def456"
    assert found["state"] == "open"

    # 2. GET /residue/{id}
    res_one = client.get("/api/v1/residue/test-cluster-1")
    assert res_one.status_code == 200
    assert res_one.json()["id"] == "test-cluster-1"

    # 3. PATCH /residue/{id} - invalid exclusion without justification/owner
    res_invalid = client.patch(
        "/api/v1/residue/test-cluster-1",
        json={"state": "excluded"},
    )
    assert res_invalid.status_code == 400
    assert "justification" in res_invalid.json()["message"]

    # 4. PATCH /residue/{id} - valid transition to accepted
    res_patch = client.patch(
        "/api/v1/residue/test-cluster-1",
        json={"state": "accepted", "justification": "Tolerated legacy fixture", "owner": "secops"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["state"] == "accepted"
    assert res_patch.json()["owner"] == "secops"


def test_criticality_endpoints() -> None:
    # 1. PUT /criticality
    payload = {
        "targetId": "target-critical-1",
        "pathPattern": "src/auth/**",
        "criticality": "mission-critical",
        "businessOwner": "Identity Team",
        "dataClassification": "Restricted",
        "facing": "external",
        "source": "manual",
    }
    res_put = client.put("/api/v1/criticality", json=payload)
    assert res_put.status_code == 200
    data = res_put.json()
    assert data["targetId"] == "target-critical-1"
    assert data["criticality"] == "mission-critical"
    assert data["facing"] == "external"

    # 2. GET /criticality
    res_list = client.get("/api/v1/criticality?targetId=target-critical-1")
    assert res_list.status_code == 200
    crits = res_list.json()
    assert len(crits) >= 1
    assert crits[0]["businessOwner"] == "Identity Team"

    # 3. POST /criticality/import (CSV)
    csv_data = (
        "targetId,pathPattern,criticality,businessOwner,dataClassification,facing\n"
        "target-csv-1,api/**,high,Backend Team,Confidential,external\n"
        "target-csv-2,db/**,mission-critical,DBA,Restricted,internal\n"
    )
    res_import = client.post(
        "/api/v1/criticality/import",
        files={"file": ("criticality.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )
    assert res_import.status_code == 200
    import_data = res_import.json()
    assert import_data["imported"] == 2
    assert len(import_data["records"]) == 2


def test_cloud_keys_endpoints() -> None:
    # GET /cloud/keys
    res = client.get("/api/v1/cloud/keys")
    assert res.status_code == 200
    data = res.json()
    assert "keys" in data
    assert "roadmap" in data
    assert "[Roadmap]" in data["roadmap"]
    assert "AWS KMS" in data["roadmap"]


def test_estate_coverage_endpoints() -> None:
    # GET /estate/coverage
    res = client.get("/api/v1/estate/coverage")
    assert res.status_code == 200
    data = res.json()
    assert "overallCoverageRatio" in data
    assert "totalMass" in data
    assert "attributedMass" in data
    assert "excludedMass" in data
    assert "residueMass" in data
    assert "totalClusters" in data
    assert "targets" in data
    assert isinstance(data["targets"], list)
