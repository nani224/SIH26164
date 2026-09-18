# Contract Changelog

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
`docs/decisions/backend/001-phase0-skeleton.md`.
