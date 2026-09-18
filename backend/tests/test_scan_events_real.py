from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def _post_scan_with_two_findings(client: TestClient, tmp_path: Path) -> str:
    (tmp_path / "auth.py").write_text('import hashlib\nhashlib.md5(b"x")\nhashlib.sha1(b"y")\n')
    resp = client.post("/api/v1/scans", json={"path": str(tmp_path)})
    assert resp.status_code == 201
    scan_id: str = resp.json()["id"]
    return scan_id


def test_ws_replays_real_events_for_a_completed_scan(client: TestClient, tmp_path: Path) -> None:
    scan_id = _post_scan_with_two_findings(client, tmp_path)

    with client.websocket_connect(f"/api/v1/scans/{scan_id}/events") as ws:
        events = []
        while True:
            msg = ws.receive_json()
            events.append(msg)
            if msg["type"] == "done":
                break

    types = [e["type"] for e in events]
    assert types[0] == "stage"
    assert types[-1] == "done"
    assert "scanning" in [e.get("stage") for e in events if e["type"] == "stage"]
    assert all("eventId" in e for e in events)
    # eventIds are the real, sequential, stored ids -- strictly increasing
    ids = [int(e["eventId"]) for e in events]
    assert ids == sorted(ids)
    assert ids == list(range(1, len(events) + 1))

    finding_events = [e for e in events if e["type"] == "finding"]
    assert len(finding_events) == 2
    assert {e["family"] for e in finding_events} == {"MD5", "SHA-1"}

    # the finding ids in the event log are real -- they show up in /findings
    findings_resp = client.get(f"/api/v1/scans/{scan_id}/findings").json()
    real_ids = {f["id"] for f in findings_resp["items"]}
    assert {e["findingId"] for e in finding_events} <= real_ids

    done_event = events[-1]
    assert done_event["scanId"] == scan_id
    assert done_event["findingCount"] == 2


def test_ws_resume_with_after_only_returns_later_events(client: TestClient, tmp_path: Path) -> None:
    scan_id = _post_scan_with_two_findings(client, tmp_path)

    with client.websocket_connect(f"/api/v1/scans/{scan_id}/events") as ws:
        full_events = []
        while True:
            msg = ws.receive_json()
            full_events.append(msg)
            if msg["type"] == "done":
                break

    midpoint = int(full_events[1]["eventId"])
    with client.websocket_connect(f"/api/v1/scans/{scan_id}/events?after={midpoint}") as ws:
        resumed_events = []
        while True:
            msg = ws.receive_json()
            resumed_events.append(msg)
            if msg["type"] == "done":
                break

    resumed_ids = [int(e["eventId"]) for e in resumed_events]
    assert all(i > midpoint for i in resumed_ids)
    assert resumed_ids == [int(e["eventId"]) for e in full_events if int(e["eventId"]) > midpoint]


def test_ws_scan_not_found_still_returns_error_and_closes(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/scans/does-not-exist/events") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_failed_scan_status_logs_error_event_not_done() -> None:
    """POST /scans can't deterministically trigger engine.scanner's OSError
    path across environments (running as root defeats permission-based
    triggers), so this exercises store.create_scan_from_result's
    FAILED-status branch directly -- the same code path the route uses.
    """
    from api import store
    from api.models import ScanCreate, ScanStatus
    from engine.models import ScanResult

    payload = ScanCreate(path="/tmp/wont-be-scanned")
    policy = store.resolve_policy(payload)
    scan = store.create_scan_from_result(payload, ScanResult(), policy, scan_status=ScanStatus.FAILED)

    events = store.list_events(scan.id)
    assert events[-1].type == "error"
    assert events[-1].payload["scanId"] == scan.id
