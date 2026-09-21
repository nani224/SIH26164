"""Tests for Track A1 M3 Debt Ledger Operations.

EXIT criteria:
1. An invalid transition is rejected with a clear error.
2. A real transition appears in the audit chain.
3. The residue-rise alert fires on a fixture.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from api import store
from api.alerts import rules
from api.main import app
from api.models import (
    AlertType,
    CoverageCertificate,
    ResidueCluster,
    ResidueClusterState,
    ResidueOccurrence,
    RiskBand,
)

client = TestClient(app)


def test_invalid_transitions_rejected_with_clear_error() -> None:
    cluster_id = "test-cluster-state-machine"
    cluster = ResidueCluster(
        id=cluster_id,
        contentHash="sha256:state_machine_hash",
        signalTypes=["tables"],
        magnitude=25.0,
        occurrences=[
            ResidueOccurrence(
                artifactHash="art-sm",
                path="crypto/cipher.c",
                range=[0, 100],
            )
        ],
        state=ResidueClusterState.OPEN,
        firstSeen=datetime.now(UTC),
        lastSeen=datetime.now(UTC),
    )

    cert = CoverageCertificate(
        scanId="scan_sm",
        artifactCount=1,
        totalMass=100.0,
        attributedMass=75.0,
        excludedMass=0.0,
        residueMass=25.0,
        coverageRatio=0.75,
        residueClusterCount=1,
        computedAt=datetime.now(UTC),
    )

    store.save_coverage("scan_sm", cert, [], [cluster], target_id="target_sm")

    # 1. Excluding requires justification
    res_no_just = client.patch(
        f"/api/v1/residue/{cluster_id}",
        json={"state": "excluded", "owner": "secops"},
    )
    assert res_no_just.status_code == 400
    assert "justification" in res_no_just.json()["message"]

    # 2. Excluding requires owner
    res_no_owner = client.patch(
        f"/api/v1/residue/{cluster_id}",
        json={"state": "excluded", "justification": "Known benign"},
    )
    assert res_no_owner.status_code == 400
    assert "owner" in res_no_owner.json()["message"]

    # 3. Promote cluster
    res_promote = client.patch(
        f"/api/v1/residue/{cluster_id}",
        json={"state": "promoted", "justification": "Created detection rule", "owner": "analyst"},
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["state"] == "promoted"

    # 4. Attempting to transition out of promoted state is rejected
    res_promoted_invalid = client.patch(
        f"/api/v1/residue/{cluster_id}",
        json={"state": "open"},
    )
    assert res_promoted_invalid.status_code == 400
    assert "cannot transition a cluster once promoted" in res_promoted_invalid.json()["message"]


def test_real_transition_appears_in_audit_chain() -> None:
    cluster_id = "test-cluster-audit"
    cluster = ResidueCluster(
        id=cluster_id,
        contentHash="sha256:audit_hash_test",
        signalTypes=["entropy"],
        magnitude=50.0,
        occurrences=[],
        state=ResidueClusterState.OPEN,
        firstSeen=datetime.now(UTC),
        lastSeen=datetime.now(UTC),
    )

    cert = CoverageCertificate(
        scanId="scan_audit",
        artifactCount=1,
        totalMass=100.0,
        attributedMass=50.0,
        excludedMass=0.0,
        residueMass=50.0,
        coverageRatio=0.50,
        residueClusterCount=1,
        computedAt=datetime.now(UTC),
    )
    store.save_coverage("scan_audit", cert, [], [cluster], target_id="target_audit")

    # Perform a valid transition to excluded with justification and owner
    res = client.patch(
        f"/api/v1/residue/{cluster_id}",
        json={
            "state": "excluded",
            "justification": "Benign JPEG metadata entropy block",
            "owner": "cryptographer-1",
        },
    )
    assert res.status_code == 200
    assert res.json()["state"] == "excluded"

    # Verify audit chain
    res_audit = client.get("/api/v1/audit/verify")
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data["status"] == "valid"
    assert audit_data["recordCount"] > 0
    assert len(audit_data["headHash"]) == 64  # SHA-256 hex string


def test_residue_rise_alert_fires_on_fixture() -> None:
    target_id = "tgt_residue_rise"

    # Baseline snapshot: residue = 10.0
    from_residue = 10.0
    # New snapshot: residue = 45.0 (delta = +35.0, exceeding default threshold 10.0)
    to_residue = 45.0

    alert = rules.check_residue_rise(
        target_id=target_id,
        from_residue_mass=from_residue,
        to_residue_mass=to_residue,
        threshold=10.0,
    )

    assert alert is not None
    assert alert.type == AlertType.RESIDUE_RISE
    assert alert.targetId == target_id
    assert alert.severity == RiskBand.HIGH
    assert "+35.0" in alert.message
    assert "New unexplained cryptographic suspicion appeared" in alert.message

    # Small change below threshold (+5.0 <= 10.0) -> No alert
    alert_none = rules.check_residue_rise(
        target_id=target_id,
        from_residue_mass=10.0,
        to_residue_mass=15.0,
        threshold=10.0,
    )
    assert alert_none is None
