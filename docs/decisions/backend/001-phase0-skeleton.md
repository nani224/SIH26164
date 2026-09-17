# ADR 001: Phase 0 scope, stub-data honesty, and branch-naming deviation

Status: accepted
Date: 2026-09-17

## Context

The ECDAT backend brief describes a substantial pre-existing `ecdat` engine
(~1,340 lines, measured precision/recall floor, bench suite, CLI). On
starting this session, `nani224/SIH26164` was verified via the GitHub API to
be a brand-new, completely empty repository (no branches, no commits,
`size: 0`). None of that engine, bench suite, or measured floor exists.

Per the brief's own rules ("never fabricate results", "label anything not
implemented [Proposed]"), this session does not pretend that code exists.
Phases 1–10 (real engine, persistence, PQC catalog, security hardening,
etc.) are **not started**. This ADR documents the decisions made to
deliver Phase 0 honestly from a clean slate.

## Decisions

1. **Scope**: this session implements Phase 0 only — repo skeleton,
   `contracts/openapi.yaml`, an in-memory FastAPI stub implementing every
   contract endpoint, and CI (ruff/mypy/pytest/contract-diff) — per the
   brief's own instruction to do Phase 0 first, merge, then stop and report.

2. **Stub data honesty**: `backend/api/stub_data.py` contains six hand-built
   example `Finding`s, one example `Scan`, and one example `Policy`. Their
   risk scores are computed by hand against the ADR-locked formula
   (`Score = 100 * V * F * U * E * K`) so the numbers are internally
   consistent, but they are **not** measured detector output — there is no
   detector yet. `GET /catalog/pqc` is the one exception: it returns real
   public reference data (FIPS 203/204/205 parameter names and byte sizes),
   not detector output, so it is not similarly caveated.

3. **`engine/risk.py` introduced early**: the Phase 0 `/rescore` endpoint
   needed to do something more real than return a canned response, so the
   pure Mosca scoring formula (score/urgency/band computation only — no
   factor derivation from signals) was implemented now rather than waiting
   for Phase 1. This does not pull forward any detection logic.

4. **Branch naming deviation**: the brief's own git rules say Phase 0 work
   goes on a branch named `contract/v1`. The hosting harness for this
   session pins work to `claude/inspiring-hamilton-p6ig7n` and forbids
   pushing elsewhere without explicit permission. The harness constraint
   takes precedence; work is committed and pushed on
   `claude/inspiring-hamilton-p6ig7n`, and the PR is titled `contract: v1
   API` as instructed.

5. **CBOM schema vendoring**: `tests/fixtures/cyclonedx/bom-1.6.schema.json`
   and `jsf-0.82.schema.json` are vendored (with SHA-256 hashes recorded in
   `backend/TOOLBELT.md`) from the official CycloneDX specification repo to
   strictly validate the stub CBOM in `tests/test_cbom.py`, per the
   air-gap/vendoring rule (build-time download, pinned, vendored).

6. **No auth/CORS/persistence yet**: Phase 0 stub has no authentication,
   no CORS allowlist, and no database — all in-memory. This is explicitly
   `[Proposed]` for Phases 2 and 10, called out in `backend/README.md`.

## Consequences

- Every "measured" number the brief's context block cites (precision
  1.000, recall 0.986, 4.9-17.3 MB/s, etc.) does not apply to this
  session's output and must not be repeated as if it does.
- Phase 1 (real engine) starts from zero: no existing `scanner.py`,
  `source.py`, `binary.py`, etc. The next session's first task is building
  that from scratch, not "packaging" something that already exists.
