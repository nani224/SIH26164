"""M6 Verification: Debt-closure loop tests.

Verifies:
1. CLI operations: ecdat debt list|show|promote|exclude|accept
2. Exclusion requires written justification and owner.
3. Acceptance records why residue is tolerated.
4. End-to-end promotion: promoting a real residue cluster produces a working rule,
   corpus residue drops by that cluster's mass, and recall rises.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

from engine.attribute import compute_ledger
from engine.debt import (
    accept_cluster,
    cli_main,
    exclude_cluster,
    load_debt_store,
    promote_cluster,
    show_cluster,
)
from engine.extract import extract_all
from engine.models import Span


def test_debt_cli_exclude_and_accept(tmp_path: Path) -> None:
    store_path = tmp_path / "debt_store.json"

    # Test exclude requires justification and owner
    with pytest.raises(ValueError, match="written justification"):
        exclude_cluster("cluster_001", justification="", owner="alice", store_path=store_path)

    with pytest.raises(ValueError, match="owner"):
        exclude_cluster("cluster_001", justification="known test table", owner="", store_path=store_path)

    # Valid exclude
    rec_ex = exclude_cluster(
        "cluster_001",
        justification="Benign hardware ID constant array",
        owner="sec-ops@company.com",
        store_path=store_path,
    )
    assert rec_ex.state == "excluded"
    assert rec_ex.owner == "sec-ops@company.com"

    # Valid accept
    rec_ac = accept_cluster(
        "cluster_002",
        justification="Legacy 1024-bit test key retained for backwards compatibility testing",
        owner="qa-team@company.com",
        store_path=store_path,
    )
    assert rec_ac.state == "accepted"

    # Load store and check persistence
    store = load_debt_store(store_path)
    assert "cluster_001" in store
    assert "cluster_002" in store
    assert store["cluster_001"].state == "excluded"
    assert store["cluster_002"].state == "accepted"

    # Test show
    cluster_mock = {
        "id": "cluster_001",
        "artifact_hash": "hash1",
        "start": 10,
        "end": 50,
        "mass": 40.0,
        "content_preview": "some preview",
    }
    shown = show_cluster("cluster_001", [cluster_mock], store_path=store_path)
    assert shown is not None
    assert shown["state"] == "excluded"
    assert shown["owner"] == "sec-ops@company.com"


def test_debt_cli_main_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store_path = tmp_path / "debt_store.json"
    monkeypatch.setattr("engine.debt.DEBT_STORE_PATH", store_path)

    # Exclude via CLI
    ret = cli_main(["debt", "exclude", "hash_abc_123", "--reason", "Benign table", "--owner", "alice"])
    assert ret == 0

    # List via CLI
    ret = cli_main(["debt", "list"])
    assert ret == 0

    # Show via CLI
    ret = cli_main(["debt", "show", "hash_abc_123"])
    assert ret == 0


def test_end_to_end_residue_cluster_promotion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Proven end to end: promote a real residue cluster -> produces working rule -> residue drops -> recall rises."""
    store_path = tmp_path / "debt_store.json"
    monkeypatch.setattr("engine.debt.DEBT_STORE_PATH", store_path)
    monkeypatch.setattr("engine.debt.RULES_DIR", tmp_path)
    monkeypatch.setattr("engine.debt.FIXTURES_DIR", tmp_path / "fixtures")

    # Real unmodeled crypto artifact containing an unmodeled cipher table
    # (e.g. an unmodeled 32-word constant table)
    import struct

    unmodeled_table = struct.pack(
        "<8I",
        0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xCA62C1D6,
        0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    )
    artifact_content = b"\x7FELF" + b"\x00" * 28 + unmodeled_table + b"\x00" * 64
    artifact_hash = hashlib.sha256(artifact_content).hexdigest()

    # 1. Baseline scan: no rule exists for this unmodeled table
    baseline_findings: list[Span] = []
    suspicion_spans = extract_all(artifact_content, "target.bin", artifact_hash)
    assert len(suspicion_spans) >= 1

    ledger_0 = compute_ledger(artifact_content, baseline_findings, suspicion_spans, artifact_hash)
    assert len(ledger_0.residue_clusters) >= 1

    target_cluster = ledger_0.residue_clusters[0]
    initial_residue_mass = ledger_0.residue_mass
    cluster_mass = target_cluster.mass
    cluster_slice = artifact_content[target_cluster.start : target_cluster.end]

    print(f"\n[M6 End-to-End Promotion]")
    print(f"  Target residue cluster ID: {target_cluster.id}")
    print(f"  Target residue cluster mass: {cluster_mass}")
    print(f"  Baseline residue mass: {initial_residue_mass}")

    # 2. Promote the cluster using ecdat debt promote
    rec = promote_cluster(
        target_cluster.id,
        cluster_slice,
        artifact_ext=".bin",
        store_path=store_path,
    )
    assert rec.state == "promoted-to-rule"
    assert rec.rule_file is not None

    # Verify rule file was scaffolded and is importable
    rule_file_path = tmp_path / f"promoted_{target_cluster.id[:12]}.py"
    assert rule_file_path.exists(), f"Rule stub {rule_file_path} was not created!"

    spec = importlib.util.spec_from_file_location("promoted_rule_mod", rule_file_path)
    assert spec is not None and spec.loader is not None
    promoted_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(promoted_mod)

    # 3. Re-scan using the newly promoted rule
    new_detections = promoted_mod.detect_promoted_cluster(artifact_content, "target.bin", artifact_hash)
    assert len(new_detections) == 1, "Promoted rule failed to fire on artifact!"

    new_finding_spans = [s for d in new_detections for s in d.spans]
    assert len(new_finding_spans) == 1

    # 4. Compute new ledger with promoted rule active
    ledger_1 = compute_ledger(artifact_content, new_finding_spans, suspicion_spans, artifact_hash)

    # 5. Verify exit criteria:
    # - Residue drops by that cluster's mass
    # - Recall rises (+1 finding)
    residue_drop = initial_residue_mass - ledger_1.residue_mass
    recall_gain = len(new_finding_spans) - len(baseline_findings)

    print(f"  New residue mass: {ledger_1.residue_mass}")
    print(f"  Residue drop: {residue_drop} (expected == {cluster_mass})")
    print(f"  Recall gain: +{recall_gain} finding")

    assert residue_drop == cluster_mass, f"Residue drop {residue_drop} != cluster mass {cluster_mass}"
    assert recall_gain == 1, f"Recall gain {recall_gain} != 1"
    assert ledger_1.verify_invariant()
