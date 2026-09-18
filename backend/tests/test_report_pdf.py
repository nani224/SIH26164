"""Tests for Phase 9 Executive PDF Report and CBOM Exports."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from api.pdf_report import build_executive_report_pdf
from api.stub_data import default_scan, list_findings
from tests.test_cbom import _validator

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

STUB_SCAN_ID = "scan_stub_001"


def test_report_pdf_endpoint_returns_valid_multipage_pdf(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/report.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "Content-Disposition" in resp.headers
    assert f"ecdat-report-{STUB_SCAN_ID}.pdf" in resp.headers["Content-Disposition"]

    content = resp.content
    assert content.startswith(b"%PDF-1.4")
    assert content.rstrip().endswith(b"%%EOF")
    assert b"/Count 3" in content  # 3-page executive report
    assert b"/Type /Pages" in content
    assert b"ECDAT" in content
    assert b"Mosca" in content
    assert b"ML-KEM" in content
    assert b"Report Integrity SHA-256" in content


def test_report_pdf_404_for_unknown_scan(client: TestClient) -> None:
    resp = client.get("/api/v1/scans/nonexistent_scan_xyz/report.pdf")
    assert resp.status_code == 404


def test_cbom_endpoint_returns_integrity_sha256_header(client: TestClient) -> None:
    resp = client.get(f"/api/v1/scans/{STUB_SCAN_ID}/cbom")
    assert resp.status_code == 200
    assert "x-cbom-sha256" in resp.headers
    header_hash = resp.headers["x-cbom-sha256"]

    cbom_data = resp.json()
    calculated_hash = hashlib.sha256(json.dumps(cbom_data, sort_keys=True).encode("utf-8")).hexdigest()
    assert header_hash == calculated_hash


def test_executive_pdf_builder_direct_unit() -> None:
    scan = default_scan()
    findings = list_findings()
    pdf_bytes = build_executive_report_pdf(scan, findings)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert b"xref" in pdf_bytes
    assert b"trailer" in pdf_bytes


def test_real_scan_cbom_strict_cyclonedx_validation(client: TestClient) -> None:
    # Trigger a real scan on an existing fixture/source dir
    resp = client.post("/api/v1/scans", json={"path": "engine"})
    assert resp.status_code == 201
    real_scan_id = resp.json()["id"]

    cbom_resp = client.get(f"/api/v1/scans/{real_scan_id}/cbom")
    assert cbom_resp.status_code == 200
    cbom = cbom_resp.json()

    # Validate against strict CycloneDX 1.6 schema
    errors = list(_validator().iter_errors(cbom))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)
    assert cbom["metadata"]["tools"]["components"][0]["version"] == "0.1.0"
    assert "x-cbom-sha256" in cbom_resp.headers
