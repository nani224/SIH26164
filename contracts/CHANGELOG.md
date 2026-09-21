# Contract Changelog

## 1.0.0-cmc — 2026-09-21

Major contract update for ECDAT v1.0 Crypto Mass Conservation (CMC) Engine & Track A1:
- **Schemas added**:
  - `CoverageCertificate`: Scan-level crypto mass conservation metrics (scanId, artifactCount, totalMass, attributedMass, excludedMass, residueMass, coverageRatio, residueClusterCount, computedAt).
  - `ArtifactCoverage`: Per-file crypto mass breakdown (artifactHash, path, totalMass, attributed, excluded, residue, coverageRatio).
  - `ResidueCluster`, `ResidueOccurrence`, `ResidueClusterPatch`, `ResidueClusterState`: Content-hash indexed crypto debt ledger clusters and state machine (open, promoted, excluded, accepted).
  - `AssetCriticality`, `AssetFacing`, `CriticalitySource`, `CriticalityImportResponse`: PS clause (iii) business criticality classification, owner mapping, and CSV bulk import.
  - `CloudKeyRecord`, `CloudKeysResponse`: PS clause (i) cloud key discovery (AWS KMS via LocalStack).
  - `TargetCoverageSummary`, `EstateCoverage`: Estate-wide coverage aggregation and debt trend metrics.
- **Schema extensions**:
  - `ScanSnapshot`: added `coverageRatio: number | null` and `residueMass: number | null`.
  - `DriftSummary`: added `coverageDelta: number | null` and `residueMassDelta: number | null`.
  - `AlertType`: added `residue-rise` enum value.
- **Paths added**:
  - `GET /api/v1/scans/{scan_id}/coverage`
  - `GET /api/v1/scans/{scan_id}/coverage/artifacts`
  - `GET /api/v1/residue`
  - `GET /api/v1/residue/{id}`
  - `PATCH /api/v1/residue/{id}`
  - `GET /api/v1/criticality`
  - `PUT /api/v1/criticality`
  - `POST /api/v1/criticality/import`
  - `GET /api/v1/cloud/keys`
  - `GET /api/v1/estate/coverage`
- **Proposals updated**:
  - RFC-003: ACCEPTED via LocalStack AWS KMS (zero external cost, air-gap safe).

## 0.3.0-continuous-operation — 2026-09-19

Additive update for continuous operation (Track A1):
- **Schemas added**: `Target`, `TargetCreate`, `TargetPatch`, `ScanSnapshot`, `Drift`, `DriftChangedItem`, `DriftSummary`, `Alert`, `ProbeResult`, `ProbeRequest`, `HsmKey`, `HsmSlot`, `HsmInventory`, `EstateSummary`, `EstateTrendPoint`, `EstateTrend`, `AuditVerifyResponse`.
- **Schema extensions**:
  - `Finding`: added `negotiated: boolean | null` field for probe reconciliation.
  - `Surface`: added `hardware-hsm` enum value (RFC-002).
- **Paths added**:
  - `GET|POST /api/v1/targets`
  - `GET|PATCH|DELETE /api/v1/targets/{id}`
  - `POST /api/v1/targets/{id}/scan-now`
  - `GET /api/v1/targets/{id}/snapshots`
  - `GET /api/v1/targets/{id}/drift`
  - `GET /api/v1/alerts`
  - `PATCH /api/v1/alerts/{id}/acknowledge`
  - `POST /api/v1/probes/tls`
  - `POST /api/v1/probes/ssh`
  - `GET /api/v1/probes`
  - `GET /api/v1/hsm/inventory`
  - `GET /api/v1/estate/summary`
  - `GET /api/v1/estate/trend`
  - `GET /api/v1/audit/verify`
- **Proposals audited**: Annotated RFC-001 (ACCEPTED), RFC-002 (ACCEPTED), RFC-003 (DECLINED per air-gap and no-cloud policy), RFC-004 (ACCEPTED).

## 0.3.0-phase6-ingest — 2026-09-18

Additive update: added `POST /api/v1/scans/upload` endpoint for sandboxed streaming multipart upload of archive bundles (.zip, .tar, .tar.gz, .tgz) with bundleHash computation, zip-slip/symlink defense, and 2GB ceiling. Added optional `bundleHash` property to `Scan` schema.

## 0.2.0-phase4-events — 2026-09-18

Additive, documentation-only update to `ScanEvent` (the WS frame shape for
`/scans/{scan_id}/events`, unreachable from any `paths` operation since
OpenAPI 3.1 has no native WS support -- `contract_diff.py` doesn't enforce
it either way): replaced the placeholder `percent` field with the real
fields the Phase 4 event log actually produces (`filesProcessed`,
`totalFiles`, `bySurface`, `family`, `findingCount`), constrained `stage`
to its real enum values, and documented the new `after` query param for
resuming a WS connection by `eventId`. No endpoint paths or other schemas
changed.

## 0.1.0-phase0 — 2026-09-17

Initial contract: full Phase 0 endpoint/schema set (scans, findings, rescore,
graph, cbom, plan, report.pdf, findings triage, policies, PQC catalog,
health, WS scan events). Implemented by an in-memory stub backend — see
`docs/decisions/backend/001-contract-and-api-skeleton.md`.
