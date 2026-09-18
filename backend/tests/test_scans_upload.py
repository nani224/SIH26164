"""Tests for POST /scans/upload endpoint."""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_upload_valid_zip_creates_scan(client: TestClient) -> None:
    # Build a real in-memory zip archive with python crypto usage
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "app/crypto_test.py",
            "import hashlib\nhashlib.sha1(b'legacy-data')\n",
        )
    zip_bytes = zip_buf.getvalue()

    resp = client.post(
        "/api/v1/scans/upload",
        files={"file": ("project.zip", zip_bytes, "application/zip")},
        data={"crqcYears": "10"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "done"
    assert data["target"] == "project.zip"
    assert data["bundleHash"] is not None
    assert len(data["bundleHash"]) == 64  # SHA-256 hex
    assert sum(data["bands"].values()) == 1
    assert data["bands"]["medium"] == 1

    # Check findings endpoint
    scan_id = data["id"]
    findings_resp = client.get(f"/api/v1/scans/{scan_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()["items"]
    assert any(f["family"] == "SHA-1" for f in findings)


def test_upload_zip_slip_rejected(client: TestClient) -> None:
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("../../evil.py", "print('hacked')")
    zip_bytes = zip_buf.getvalue()

    resp = client.post(
        "/api/v1/scans/upload",
        files={"file": ("exploit.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 400
    assert "traversal" in resp.json()["message"].lower() or "suspicious" in resp.json()["message"].lower()


def test_upload_corrupted_archive_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/scans/upload",
        files={"file": ("corrupted.zip", b"not-a-zip", "application/zip")},
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["message"].lower() or "not found" in resp.json()["message"].lower()
