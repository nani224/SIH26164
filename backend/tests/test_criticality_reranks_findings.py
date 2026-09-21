"""v1.0 PS clause (iii): explicit asset criticality must actually feed the
risk formula's K/E factor *inputs* (via Policy Context matching) -- not
just be stored inertly. Proves the exit criteria against a real scan of
real source, through the real HTTP API, not a hand-built Detection."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient


def test_importing_criticality_csv_visibly_reranks_a_real_finding(
    client: TestClient, tmp_path: Path
) -> None:
    # MD5 digest -- not subject to the "unencrypted private key" score
    # floor (that only fires for function=keygen), so a real K/E change
    # is visible in the score rather than masked by a different override.
    (tmp_path / "legacy_hash.py").write_text("import hashlib\nhashlib.md5(b'x')\n")

    target_resp = client.post(
        "/api/v1/targets",
        json={
            "name": "Criticality Rerank Target",
            "kind": "path",
            "uri": str(tmp_path),
            "policyId": "policy_default",
            "schedule": "0 0 * * *",
            "enabled": True,
        },
    )
    assert target_resp.status_code == 201
    target_id = target_resp.json()["id"]

    # Baseline scan: no explicit criticality set yet -> falls through to
    # the policy's own default Context (internal, medium).
    scan1_resp = client.post(f"/api/v1/targets/{target_id}/scan-now")
    assert scan1_resp.status_code == 201
    scan1 = scan1_resp.json()
    findings1 = client.get(f"/api/v1/scans/{scan1['id']}/findings").json()
    assert findings1["total"] == 1
    baseline_finding = findings1["items"][0]
    assert baseline_finding["family"] == "MD5"
    baseline_score = baseline_finding["risk"]["score"]
    baseline_k = baseline_finding["risk"]["K"]
    baseline_e = baseline_finding["risk"]["E"]

    # Import a CSV setting this target's whole tree to mission-critical,
    # externally facing -- the CMDB bulk-load path (M5's own exit
    # criterion), not the single-record PUT.
    csv_body = (
        "targetId,pathPattern,criticality,businessOwner,dataClassification,facing\n"
        f"{target_id},**,mission-critical,payments-team,pci,external\n"
    )
    import_resp = client.post(
        "/api/v1/criticality/import",
        files={"file": ("criticality.csv", io.BytesIO(csv_body.encode("utf-8")), "text/csv")},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["imported"] == 1

    # Re-scan the same target, same source, nothing else changed.
    scan2_resp = client.post(f"/api/v1/targets/{target_id}/scan-now")
    assert scan2_resp.status_code == 201
    scan2 = scan2_resp.json()
    findings2 = client.get(f"/api/v1/scans/{scan2['id']}/findings").json()
    assert findings2["total"] == 1
    reranked_finding = findings2["items"][0]
    assert reranked_finding["family"] == "MD5"

    # The real signal: K and E rose (mission-critical > medium, external >
    # internal), and the score rose with them -- imported criticality
    # visibly re-ranked a real finding, not just stored inertly.
    assert reranked_finding["risk"]["K"] > baseline_k
    assert reranked_finding["risk"]["E"] > baseline_e
    assert reranked_finding["risk"]["score"] > baseline_score


def test_estate_summary_reports_facing_as_a_first_class_split(client: TestClient) -> None:
    """PS clause (i): internal vs external facing reported as a first-class
    count, not buried inside individual AssetCriticality records only."""
    target_resp = client.post(
        "/api/v1/targets",
        json={
            "name": "Facing Split Target",
            "kind": "path",
            "uri": "/tmp/facing-split-target",
            "policyId": "policy_default",
            "schedule": "0 0 * * *",
            "enabled": True,
        },
    )
    target_id = target_resp.json()["id"]

    before = client.get("/api/v1/estate/summary").json()

    client.put(
        "/api/v1/criticality",
        json={
            "targetId": target_id,
            "pathPattern": "**/internal-api/**",
            "criticality": "high",
            "businessOwner": "platform-team",
            "dataClassification": "internal",
            "facing": "internal",
            "source": "manual",
        },
    )
    client.put(
        "/api/v1/criticality",
        json={
            "targetId": target_id,
            "pathPattern": "**/public-api/**",
            "criticality": "mission-critical",
            "businessOwner": "platform-team",
            "dataClassification": "pii",
            "facing": "external",
            "source": "manual",
        },
    )

    after = client.get("/api/v1/estate/summary").json()
    assert after["internalFacingAssets"] == before["internalFacingAssets"] + 1
    assert after["externalFacingAssets"] == before["externalFacingAssets"] + 1
