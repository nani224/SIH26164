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

## Track CC (detection engine, corpus, CI/CD) — ownership and rules

Track CC owns EXCLUSIVELY `backend/engine/**`, `backend/bench/**`, and
`.github/workflows/**`. Never edit `backend/api/`, `backend/scheduler/`,
`backend/probes/`, `frontend/`, or `contracts/openapi.yaml` from this
track — a contract need goes into `contracts/PROPOSALS.md`, not a live
edit.

- **Precision floor: 0.95, enforced in CI.** A false positive wastes an
  analyst's time on a non-risk and destroys trust in the whole tool; a
  miss is just a documented, honest gap. Any rule that raises recall but
  drops precision below 0.95 is wrong — fix the rule's specificity or
  drop it, never ship it anyway.
- **Label before running, always.** For any HOLD/DEV corpus addition:
  read the source and write the truth-table labels first, commit the
  labels alone in their own commit, only then run the detector. Never
  invert this order — it's the only thing standing between a real
  accuracy number and tuning-on-HOLD.
- **Licence gate for `bench/`**: only MIT/Apache-2.0/BSD/ISC-licensed
  source gets committed into `backend/bench/`. Fetching an LGPL/GPL
  project to a scratch/temp path to read and hand-label against the
  detector is fine and is not "vendoring" — just never commit their
  source into this repo.
- **Honest numbers only.** A recall of 0.52 with the false negatives
  clustered and explained is worth more than a fabricated or
  cherry-picked 0.95. Never round a measured number up.

## Known bookkeeping hazard

`docs/engineering/backend/PROGRESS.md` has gone stale before (described Phase 0 state while
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
