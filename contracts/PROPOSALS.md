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

---

### [PROPOSED] RFC-002: Hardware Security Module (HSM) Discovery Surface
- **Finding Surface**: `hardware-hsm`
- **Status**: Proposed (Marked as `[Proposed]` in Screen 4 Cryptographic Inventory)
- **Requested By**: Screen 4 (Inventory)
- **Justification**: Discovery of on-premise HSM firmware keys (PKCS#11, Luna HSM, YubiHSM) for defense communications.
- **Proposed Schema**: Extend `surface` enum in `components['schemas']['Finding']` with `"hardware-hsm"`.

---

### [PROPOSED] RFC-003: Cloud KMS & Sovereign Enclave Key Discovery Surface
- **Finding Surface**: `cloud-kms`
- **Status**: Proposed (Marked as `[Proposed]` in Screen 4 Cryptographic Inventory)
- **Requested By**: Screen 4 (Inventory)
- **Justification**: Visibility into sovereign cloud cryptographic assets (AWS KMS, Azure Key Vault, Google Cloud HSM enclaves).
- **Proposed Schema**: Extend `surface` enum in `components['schemas']['Finding']` with `"cloud-kms"`.

---

### [PROPOSED] RFC-004: Native WebSocket Progress Event Stream
- **Endpoint**: `ws://<host>/api/v1/scans/{id}/events`
- **Status**: Proposed / Implemented in Frontend WebSocket Client
- **Requested By**: Screen 1 (Scan Launcher)
- **Justification**: Real-time progress streaming for large repositories without polling `GET /scans/{id}`.
- **Proposed Message Payload**:
  ```json
  {
    "scanId": "string",
    "stage": "ingesting" | "scanning" | "scoring" | "done" | "failed",
    "files": 1420,
    "bytes": 28450190,
    "findings": 50,
    "progressPercent": 100
  }
  ```
