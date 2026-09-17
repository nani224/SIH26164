# Contract Proposals & Modifications Log

This file tracks RFCs and change proposals from the frontend (`Antigravity`) to the backend contract (`contracts/openapi.yaml`).

## Process
1. Frontend identifies missing endpoints or fields required for analyst workflow.
2. Frontend logs the proposal below with justification, affected screen, and proposed schema.
3. Backend (`Claude`) reviews and merges into `contracts/openapi.yaml` via PR.
4. Frontend consumes changes upon rebase.

---

### [PROPOSED] RFC-001: Executive PDF Report Stream
- **Endpoint**: `GET /api/v1/scans/{id}/report.pdf`
- **Status**: Proposed (Marked as `[Proposed]` in Migration Plan / Overview UI)
- **Requested By**: Screen 9 (Migration Plan) & Screen 2 (Overview)
- **Justification**: Senior intelligence officers require printable, offline cryptographic risk briefs.
- **Proposed Response**: Binary application/pdf with cryptographic hash verification header `X-CBOM-Signature-SHA256`.
