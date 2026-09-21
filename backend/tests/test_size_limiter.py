"""M4 Verification: Request size limit middleware tests."""

from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from api.main import app


def test_oversized_json_request_rejected_with_413() -> None:
    """An oversized JSON request (> 1MB) to non-upload endpoint must be rejected with 413."""
    client = TestClient(app, headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": "test-operator"})

    # Create a ~1.2 MB JSON string
    large_padding = "x" * (1200 * 1024)
    payload = {"path": f"some/path/{large_padding}"}

    resp = client.post(
        "/api/v1/scans",
        json=payload,
        headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": "test-operator"},
    )
    assert resp.status_code == 413
    assert "PayloadTooLarge" in resp.text or "exceeds maximum allowed size" in resp.text


def test_normal_json_request_within_limit_succeeds() -> None:
    """A normal sized JSON request (< 1MB) must not be rejected with 413."""
    client = TestClient(app, headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": "test-operator"})

    resp = client.post(
        "/api/v1/targets",
        json={
            "name": "normal-target",
            "kind": "repo",
            "uri": "https://example.com/normal",
            "policyId": "pol_default",
            "schedule": "0 0 * * *",
        },
        headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": "test-operator"},
    )
    assert resp.status_code == 201


def test_upload_endpoint_bypasses_1mb_json_cap() -> None:
    """The /api/v1/scans/upload endpoint must bypass the 1MB JSON cap for legitimate archive uploads."""
    client = TestClient(app, headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": "test-operator"})

    # Create an in-memory zip archive > 1MB using ZIP_STORED
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("test.py", b"x = 1\n" + (b"# comment line\n" * 80000))
    buf.seek(0)
    zip_bytes = buf.getvalue()
    assert len(zip_bytes) > 1024 * 1024, f"Zip size is {len(zip_bytes)}, expected > 1MB"

    files = {"file": ("large_archive.zip", zip_bytes, "application/zip")}
    data = {"policyId": "pol_default", "crqcYears": "10"}

    resp = client.post(
        "/api/v1/scans/upload",
        files=files,
        data=data,
        headers={"Authorization": "Bearer ecdat-test-token-secret", "X-ECDAT-Actor": "test-operator"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "done"
