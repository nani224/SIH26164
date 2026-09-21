# API Reference

`contracts/openapi.yaml` is the single source of truth for ECDAT's API
shape. This page is a human-readable index over it, not a replacement —
when the two disagree, the OpenAPI file wins (CI enforces zero drift
between it and the backend's own generated schema; see
[`SECURITY.md`](SECURITY.md) and [`docs/engineering/backend/PLAN.md`](engineering/backend/PLAN.md)).

## Regenerating

- **Interactive docs**: run the backend (`uv run uvicorn api.main:app`)
  and open `http://localhost:8000/docs` (Swagger UI) or `/redoc`.
- **Frontend TypeScript types**, from `frontend/`:
  ```bash
  pnpm codegen:api
  ```
  Regenerates `frontend/src/types/api.generated.ts` from
  `contracts/openapi.yaml`. Run this and re-run the frontend gate in the
  **same** commit as any contract change — the root `CLAUDE.md` treats a
  contract change followed by a stale frontend type as a drift bug, not a
  later cleanup task.
- **Contract-drift check**, from `backend/`:
  ```bash
  uv run python scripts/contract_diff.py
  ```
  Diffs FastAPI's own generated OpenAPI document against
  `contracts/openapi.yaml`; fails on any missing path or schema field.

## Endpoint map

All paths are under `/api/v1`.

### Scans

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | `/scans` | Scan a server-side path (real tree-sitter detection, synchronous) |
| POST | `/scans/upload` | Sandboxed multi-part upload + scan (zip/tar, hostile-input protected) |
| GET | `/scans` | List scans |
| GET | `/scans/{scan_id}` | Scan detail (status, stats, band counts) |
| WS | `/scans/{scan_id}/events` | Replay the scan's real recorded event log (stage/progress/finding/done), rate-limited, resumable via `?after=<eventId>` |
| GET | `/scans/{scan_id}/findings` | Paginated, filterable finding list (band/family/surface/source/confidence/needsReview/text search/sort) |
| POST | `/scans/{scan_id}/rescore` | Re-score every finding under a new CRQC horizon (Z), in-DB CTE, <200ms budget for 10k findings |
| GET | `/scans/{scan_id}/graph` | Estate graph (system → file → asset) built from this scan's real findings |
| GET | `/scans/{scan_id}/cbom` | CycloneDX 1.6 Cryptographic Bill of Materials |
| GET | `/scans/{scan_id}/plan` | PQC migration plan (recommendations + cost deltas) |
| GET | `/scans/{scan_id}/report.pdf` | Executive PDF report |

### Findings

| Method | Path | Purpose |
| :--- | :--- | :--- |
| PATCH | `/findings/{finding_id}/triage` | Set triage status (open/accepted-risk/remediated/false-positive) + note |

### Continuous operation (targets, drift, alerts)

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | `/targets` | Register a target (repo path + cron schedule) for unattended scanning |
| GET | `/targets` | List registered targets |
| GET | `/targets/{id}` | Target detail |
| POST | `/targets/{id}/scan-now` | Trigger an out-of-schedule scan immediately |
| GET | `/targets/{id}/snapshots` | Scan history for this target |
| GET | `/targets/{id}/drift` | Added/resolved/changed findings between the two most recent snapshots |
| GET | `/alerts` | List alerts (new-critical, cert-expiring, drift, probe-downgrade) |
| PATCH | `/alerts/{id}/acknowledge` | Acknowledge an alert |

### Estate analytics

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/estate/summary` | Aggregate targets/scans/findings/bands/unacknowledged-alerts |
| GET | `/estate/trend` | Per-day historical risk-score/finding-count/band trend |

### Live infrastructure probes

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | `/probes/tls` | Real TLS handshake against a `probes.guard`-allowlisted target; reconciles negotiated vs. supported ciphers into findings |
| POST | `/probes/ssh` | Real SSH server audit (`ssh-audit`) |
| GET | `/probes` | List past probe results |
| GET | `/hsm/inventory` | Real SoftHSM2/PKCS#11 key and slot inventory |

### Policy, catalog, audit, health

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET/PUT | `/policies`, `/policies/{policy_id}` | Mosca scoring policy (CRQC horizon, per-context shelf-life/migration/criticality/exposure) |
| GET | `/catalog/pqc` | Reference NIST FIPS 203/204/205 PQC parameter data |
| GET | `/audit/verify` | Verify the SHA-256 hash-chained audit log's integrity |
| GET | `/health` | Liveness check |

## Risk factor fields on a `Finding`

Every finding carries its full raw risk factor set (not just the
computed score), per the root `CLAUDE.md`'s "all raw risk factors
stored" requirement: `v f u e k x y z score band moscaMargin reason
classicallyBroken hndl needsReview`. See
[`docs/decisions/INDEX.md`](decisions/INDEX.md)'s Risk Scoring section
for how each is derived.
