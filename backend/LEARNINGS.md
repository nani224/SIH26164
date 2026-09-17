# ECDAT Backend — Learnings

## 2026-09-17 — Phase 0

- The repo (`nani224/SIH26164`) was completely empty at session start (no
  branches, no commits, GitHub API `size: 0`) despite the task brief
  describing a substantial pre-existing engine. Always verify repo state
  independently (`git branch -r`, or the GitHub API) before trusting a
  brief's description of "what already exists" — briefs can describe an
  aspirational/template state rather than the actual one.
- CycloneDX 1.6's cryptographic-asset `cryptoProperties.assetType` enum is
  `algorithm | certificate | protocol | related-crypto-material` — note it's
  `related-crypto-material`, not `key`, for the "key" Finding.kind. Fetched
  and vendored the real schema (`bom-1.6.schema.json` +
  `jsf-0.82.schema.json`, draft-07 based) from
  `CycloneDX/specification@1.6` rather than guessing field names from
  memory — memory of the exact enum/field names was not reliable enough to
  skip this.
- FastAPI's `@app.on_event("startup")` is legacy; current guidance is the
  `lifespan` async context manager on `FastAPI(lifespan=...)`.
- Outbound HTTPS to raw.githubusercontent.com works through the
  environment's proxy without any special handling — useful for vendoring
  spec files with a recorded SHA-256.
