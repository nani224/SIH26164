# ECDAT — root project rules

Repo: `nani224/SIH26164`. ECDAT (Enterprise Cryptographic Discovery &
Analysis Tool): scans code/binaries for cryptographic assets, scores
quantum risk (Mosca), recommends PQC replacements, exports CycloneDX 1.6
CBOM. Backend (`backend/`) and frontend (`frontend/`) were built by two
separate agent tracks and merged onto `main`; this file is the shared
reference for anyone (human or agent) working across both halves.

Read `backend/CLAUDE.md` and `frontend/CLAUDE.md` (if present) for
track-specific detail. This file only holds what both tracks must agree on.

## Risk formula (do not alter without a written ADR in docs/decisions/)

```
Score = 100 x V x F x U x E x K ; M = X + Y - Z
U = clamp(0.5 + M/(2Z), 0.05, 1) ; U = 1 if classically broken
Bands: critical >= 60 * high 35-59 * medium 15-34 * low < 15
Unencrypted private key outside test paths -> score >= 90
Confidence shown beside score, never multiplied in; < 0.75 -> needsReview
```

Detection and scoring are deterministic — no ML/LLM decides whether crypto
exists or how risky it is. Air-gapped at runtime: no external calls, no
telemetry, no CDN-loaded fonts/assets.

## Folder map

```
backend/    FastAPI app, detection engine, SQLite persistence, bench/
frontend/   Next.js app, 10 screens, MSW mocks for dev only
contracts/  openapi.yaml (source of truth) + CHANGELOG.md
docs/decisions/{backend,frontend}/   ADRs
```

`contracts/openapi.yaml` is the single source of truth for the API shape.
Any change to it is a separate `contract:` commit with a CHANGELOG entry,
and must be followed in the SAME fix cycle (not "later") by regenerating
frontend TS types and re-running the frontend gate.

## Definition of Done (condensed — see task prompt for full version)

- Backend: ruff, mypy --strict, pytest+coverage, hypothesis, bench scripts
  (real numbers, not quoted from README), hostile-input tests, CBOM strict
  validation, rescore perf budget, sandboxed ingest, security scanners.
- Frontend: typecheck, lint, knip, vitest, playwright, build; every screen
  hits the real contract API (not a static mock import); MSW-off with no
  backend gives clean empty/error states; no risk-formula reimplementation
  in frontend code; fonts genuinely self-hosted.
- Contract: FastAPI's generated OpenAPI has zero drift against
  `contracts/openapi.yaml`; frontend generated types match the CURRENT
  merged contract.
- Real end-to-end integration: real backend + real frontend (MSW off)
  actually running together and exercised through the full scan -> triage
  -> export flow. This had never been done as of the last audit — treat it
  as the highest-priority unverified claim in the project.

## Known bookkeeping hazard

`backend/PROGRESS.md` has gone stale before (described Phase 0 state while
`main` had commits through "Phase 10"). **Update PROGRESS.md and PLAN.md
every session**, with what's actually true, not what a commit title
claims. Never mark an item done in these files without the command output
that proves it, generated in that session.

## Verification discipline

Never mark anything PASS without the command output or evidence in the
same message. Never apply the same fix twice — if a check fails again for
the same root cause, stop, write the hypothesis, change approach. A commit
message, badge, or existing PROGRESS.md line is not evidence by itself —
re-derive it.
