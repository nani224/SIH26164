from __future__ import annotations

from fastapi.testclient import TestClient

STUB_SCAN_ID = "scan_stub_001"


def test_create_and_list_scan(client: TestClient) -> None:
    resp = client.post("/api/v1/scans", json={"path": "/tmp/example"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["target"] == "/tmp/example"
    assert created["status"] == "done"

    listed = client.get("/api/v1/scans").json()
    ids = {s["id"] for s in listed}
    assert created["id"] in ids
    assert STUB_SCAN_ID in ids


def test_get_scan_404(client: TestClient) -> None:
    resp = client.get("/api/v1/scans/does-not-exist")
    assert resp.status_code == 404


def test_findings_band_filter(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/findings", params={"band": "critical"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(f["risk"]["band"] == "critical" for f in body["items"])


def test_findings_needs_review_filter(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/findings", params={"needsReview": True})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["risk"]["needsReview"] is True


def test_findings_search_and_pagination(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/findings", params={"limit": 2})
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["cursor"] == "2"

    resp2 = client.get(
        f"/api/v1/scans/{STUB_SCAN_ID}/findings", params={"limit": 2, "cursor": body["cursor"]}
    )
    body2 = resp2.json()
    assert body2["items"][0]["id"] != body["items"][0]["id"]


def test_findings_sort_by_score(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/findings", params={"sort": "score"})
    scores = [f["risk"]["score"] for f in resp.json()["items"]]
    assert scores == sorted(scores, reverse=True)


def test_rescore_lower_horizon_can_raise_urgency(client: TestClient) -> None:
    resp = client.post(f"/api/v1/scans/{STUB_SCAN_ID}/rescore", json={"crqcYears": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert "bands" in body
    assert isinstance(body["changed"], list)


def test_graph(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) > 0
    assert len(body["edges"]) > 0


def test_cbom(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/cbom")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bomFormat"] == "CycloneDX"
    assert body["specVersion"] == "1.6"
    assert len(body["components"]) > 0


def test_plan(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/plan")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scanId"] == STUB_SCAN_ID
    assert len(body["items"]) > 0
    bands = [item["band"] for item in body["items"]]
    priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    assert [priority[b] for b in bands] == sorted(priority[b] for b in bands)


def test_report_pdf(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/report.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-1.4")
    assert resp.content.rstrip().endswith(b"%%EOF")


def test_triage_patch(client: TestClient) -> None:
    resp = client.patch(
        "/api/v1/findings/finding_006/triage",
        json={"status": "accepted-risk", "note": "reviewed, low risk accepted"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["triage"]["status"] == "accepted-risk"
    assert body["triage"]["note"] == "reviewed, low risk accepted"


def test_triage_patch_404(client: TestClient) -> None:
    resp = client.patch("/api/v1/findings/nope/triage", json={"status": "fixed"})
    assert resp.status_code == 404


def test_policies_list_and_get(client: TestClient) -> None:
    resp = client.get("/api/v1/policies")
    assert resp.status_code == 200
    policies = resp.json()
    assert any(p["id"] == "policy_default" for p in policies)

    resp2 = client.get("/api/v1/policies/policy_default")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Default NTRO baseline"


def test_policies_put(client: TestClient) -> None:
    payload = {
        "id": "policy_custom",
        "name": "Custom",
        "crqcYears": 8,
        "default": {
            "exposure": "internal",
            "criticality": "medium",
            "shelfLifeYears": 4,
            "migrationYears": 2,
        },
        "contexts": [],
    }
    resp = client.put("/api/v1/policies/policy_custom", json=payload)
    assert resp.status_code == 200
    assert client.get("/api/v1/policies/policy_custom").json()["crqcYears"] == 8


def test_policies_put_id_mismatch(client: TestClient) -> None:
    payload = {
        "id": "other-id",
        "name": "Custom",
        "crqcYears": 8,
        "default": {
            "exposure": "internal",
            "criticality": "medium",
            "shelfLifeYears": 4,
            "migrationYears": 2,
        },
        "contexts": [],
    }
    resp = client.put("/api/v1/policies/policy_custom", json=payload)
    assert resp.status_code == 400


def test_pqc_catalog(client: TestClient) -> None:
    resp = client.get("/api/v1/catalog/pqc")
    assert resp.status_code == 200
    families = {e["family"] for e in resp.json()}
    assert families == {"ML-KEM", "ML-DSA", "SLH-DSA"}


def test_scan_events_websocket(client: TestClient) -> None:
    with client.websocket_connect(f"/api/v1/scans/{STUB_SCAN_ID}/events") as ws:
        events = []
        for _ in range(7):
            events.append(ws.receive_json())
    types = [e["type"] for e in events]
    assert types[0] == "stage"
    assert types[-1] == "done"
    assert all("eventId" in e for e in events)


def test_scan_events_websocket_404(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/scans/does-not-exist/events") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
