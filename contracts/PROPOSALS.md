# Contract Proposals & Modifications Log

This file tracks RFCs and change proposals from the frontend (`Antigravity`) to the backend contract (`contracts/openapi.yaml`).

## Process
1. Frontend identifies missing endpoints or fields required for analyst workflow.
2. Frontend logs the proposal below with justification, affected screen, and proposed schema.
3. Backend (`Claude`) reviews and merges into `contracts/openapi.yaml` via PR.
4. Frontend consumes changes upon rebase.

---

### [ACCEPTED] RFC-001: Executive PDF Report Stream
- **Endpoint**: `GET /api/v1/scans/{id}/report.pdf`
- **Status**: ACCEPTED — Implemented in v0.2.0-phase9 via `api/pdf_report.py` with `X-CBOM-SHA256` integrity header.
- **Requested By**: Screen 9 (Migration Plan) & Screen 2 (Overview)
- **Justification**: Senior intelligence officers require printable, offline cryptographic risk briefs.
- **Proposed Response**: Binary application/pdf with cryptographic hash verification header `X-CBOM-Signature-SHA256`.

---

### [ACCEPTED] RFC-002: Hardware Security Module (HSM) Discovery Surface
- **Finding Surface**: `hardware-hsm`
- **Status**: ACCEPTED — Integrated into v0.3 Continuous Operation schema. Added `hardware-hsm` to `Surface` enum and `GET /api/v1/hsm/inventory` endpoint.
- **Requested By**: Screen 4 (Inventory)
- **Justification**: Discovery of on-premise HSM firmware keys (PKCS#11, Luna HSM, YubiHSM) for defense communications.
- **Proposed Schema**: Extend `surface` enum in `components['schemas']['Finding']` with `"hardware-hsm"`.

---

### [ACCEPTED] RFC-003: Cloud KMS & Sovereign Enclave Key Discovery Surface
- **Finding Surface**: `cloud-kms` / `GET /api/v1/cloud/keys`
- **Status**: ACCEPTED — Resolved in v1.0 via self-hosted LocalStack AWS KMS (`backend/probes/cloud_kms.py`), satisfying PS clause (i) while adhering to zero-cost and air-gap constraints (no external outbound HTTP, local mock/container only). Other cloud providers documented honestly under [Roadmap].
- **Requested By**: Screen 4 (Inventory) & PS clause (i)
- **Justification**: Visibility into sovereign cloud cryptographic assets and key rotation lifecycle.
- **Proposed Schema**: `GET /api/v1/cloud/keys` returning `CloudKeysResponse` with `CloudKeyRecord` and roadmap transparency.


---

### [ACCEPTED] RFC-004: Native WebSocket Progress Event Stream
- **Endpoint**: `ws://<host>/api/v1/scans/{id}/events`
- **Status**: ACCEPTED — Merged and implemented in v0.2.0-phase4-events with stored event replay and resume via `?after=<eventId>`.
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
