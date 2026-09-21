"""Test structured logging coverage across API endpoints."""

from collections.abc import MutableMapping
from typing import Any

import structlog
from fastapi.testclient import TestClient

from api.main import app


def test_structured_logging_across_three_endpoints() -> None:
    """A real request to 3 different endpoints produces structured log events with consistent fields."""
    captured_logs: list[dict[str, object]] = []

    def capture_processor(
        _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        captured_logs.append(dict(event_dict))
        return event_dict

    # Temporarily configure structlog to capture events
    old_processors = structlog.get_config().get("processors", [])
    structlog.configure(processors=[capture_processor, structlog.processors.JSONRenderer()])

    try:
        client = TestClient(app)
        headers = {
            "Authorization": "Bearer ecdat-test-token-secret",
            "X-ECDAT-Actor": "audit-officer-42",
        }

        # 1. Endpoint 1: GET /api/v1/targets
        res1 = client.get("/api/v1/targets", headers=headers)
        assert res1.status_code == 200

        # 2. Endpoint 2: GET /api/v1/policies
        res2 = client.get("/api/v1/policies", headers=headers)
        assert res2.status_code == 200

        # 3. Endpoint 3: GET /api/v1/scans/non-existent-scan-id (404 failure logging)
        res3 = client.get("/api/v1/scans/non-existent-scan-id", headers=headers)
        assert res3.status_code == 404

        # Verify structured log lines were generated
        assert len(captured_logs) >= 3, f"Expected at least 3 log events, captured {len(captured_logs)}"

        # Check fields across endpoints
        endpoint_paths = [log.get("path") for log in captured_logs if "path" in log]
        assert "/api/v1/targets" in endpoint_paths
        assert "/api/v1/policies" in endpoint_paths
        assert "/api/v1/scans/non-existent-scan-id" in endpoint_paths

        # Check actor binding
        actors = [log.get("actor") for log in captured_logs if "actor" in log]
        assert all(a == "audit-officer-42" for a in actors)

        # Check completed / failed events have status_code and duration_ms
        completed_events = [
            log for log in captured_logs if log.get("event") in ("request_completed", "request_failed")
        ]
        assert len(completed_events) >= 3
        for evt in completed_events:
            assert "status_code" in evt
            assert "duration_ms" in evt
            assert "actor" in evt
            assert "method" in evt

        # Check that 404 was logged with request_failed
        failed_events = [log for log in captured_logs if log.get("event") == "request_failed"]
        assert any(e.get("status_code") == 404 for e in failed_events)

    finally:
        structlog.configure(processors=old_processors)
