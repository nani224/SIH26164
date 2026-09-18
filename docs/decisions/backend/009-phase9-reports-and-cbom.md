# ADR 009: Phase 9 CycloneDX 1.6 CBOM Export & Multi-Page Executive PDF Report

Status: accepted
Date: 2026-09-18

## Context

SIH26164 requires:
1. Exporting an authoritative Cryptographic Bill of Materials (CBOM) compliant with the CycloneDX 1.6 specification.
2. Generating a publication-grade, multi-page Executive PDF Report detailing quantum risk exposure, Mosca factor breakdowns, and actionable post-quantum migration plans.
3. Operating strictly within an air-gapped environment with zero runtime internet access and zero non-deterministic machine learning dependencies.

## Decision

1. **CycloneDX 1.6 Cryptographic BOM (`backend/api/cbom.py`)**:
   - Mapped classical and quantum algorithms to standardized CycloneDX 1.6 `cryptographic-asset` components.
   - Enriched BOM metadata with scan parameters and properties (`ecdat:scanId`, `ecdat:policyId`, `ecdat:riskScore`).
   - Attached an on-the-fly computed `X-CBOM-SHA256` integrity header on `GET /api/v1/scans/{scan_id}/cbom`.
   - Verified strict validation against the vendored CycloneDX 1.6 JSON schema (`bom-1.6.schema.json`) for both stub data and real-world AST scanned findings.

2. **Pure-Python Multi-Page Executive PDF Generator (`backend/api/pdf_report.py`)**:
   - Developed a self-contained, zero-dependency PDF 1.4 document composer without external C/C++ libraries (such as Cairo/Pango) or unpinned packages.
   - Implemented a structured 3-page publication layout:
     - **Page 1: Executive Summary & Mosca Quantum Risk Scorecard**: Dark navy title banner, scan parameters, overall Mosca score (0–100) with risk band badges, breakdown metric cards (Critical, High, Medium, Low), and executive observations.
     - **Page 2: Detailed Mosca Risk Factor Analysis & Top Vulnerabilities**: Explains Mosca formulation ($Score = 100 \times V \times F \times U \times E \times K$), and presents a structured table of top vulnerabilities with location, line number, algorithm family, risk score, and severity band.
     - **Page 3: Actionable Remediation Roadmap & Standardized PQC Migration**: Table of recommended actions and targets aligned with NIST standards (FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA), accompanied by an air-gapped cryptographic SHA-256 attestation stamp.

3. **Integration**:
   - Replaced placeholder PDF stub with `build_executive_report_pdf` in `GET /api/v1/scans/{scan_id}/report.pdf`.
   - Maintained backward compatibility via `api/pdf_stub.py`.
   - Verified zero contract drift against `contracts/openapi.yaml`.

## Consequences

- Full compliance with CycloneDX 1.6 CBOM standards.
- Beautiful, high-density executive reporting ready for C-suite and security compliance presentation.
- 100% deterministic, instant execution with sub-second PDF generation and zero external network calls.
