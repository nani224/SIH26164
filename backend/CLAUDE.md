# ECDAT Backend — session rules (condensed from the SIH26164 brief)

Read this at the start of every session, along with PLAN.md, PROGRESS.md,
LEARNINGS.md, and TOOLBELT.md.

## Mission

Backend + detection engine for ECDAT: scans source/binaries/libraries/images,
finds crypto assets, scores quantum risk (Mosca), recommends PQC
replacements, exports CycloneDX 1.6 CBOM. Correct first, fast second. Never
claim something works unless you ran it and saw the output.

## Non-negotiable domain rules

- Detection and risk scoring are **deterministic**. No ML/LLM decides
  whether crypto exists or how risky it is. An optional LLM may only
  produce labelled explanatory text.
- Air-gapped at runtime: no external calls, no telemetry. Build-time
  downloads pinned, hashed, vendored.
- Risk formula (change only with an ADR):
  ```
  Score = 100 x V x F x U x E x K ; M = X + Y - Z
  U = clamp(0.5 + M/(2Z), 0.05, 1) ; U = 1 if classically broken
  Bands: critical >= 60 * high 35-59 * medium 15-34 * low < 15
  Unencrypted private key outside test paths -> score >= 90
  Confidence beside score, never multiplied in; < 0.75 -> needsReview
  ```
  Implemented (formula only, not factor derivation) in `engine/risk.py`.
- Z is an analyst scenario (5-15 years), not a fact.
- Label anything not implemented `[Proposed]`. Never fabricate metrics or
  results.

## Measured floor

**None yet.** As of Phase 0 (this repo's initial state), there is no
detection engine and no bench corpus — see
`docs/decisions/backend/001-phase0-skeleton.md`. Do not repeat the brief's
example numbers (precision 1.000, recall 0.986, 4.9-17.3 MB/s, etc.) as if
they were measured here. Once Loop B1/B2/B5 actually run in this repo,
record real numbers here and treat them as the floor never to regress.

## Gates (paste real output every time)

```
uv run ruff check .
uv run mypy --strict .
uv run pytest --cov
uv run python scripts/contract_diff.py
```
Plus, once they exist: bench/evaluate.py (Layer A P>=0.99 R>=0.98), Layer B
floor, HOLD set result as-is, bench/hostile_tests.py, schemathesis, load
test, air-gap run, CBOM strict validation, security scanners.

## Do not

Add ML to detection or scoring; silently change risk weights; tune on
HOLD; copy code or rules whose licence forbids it; report unmeasured
numbers; call external services at runtime; edit `frontend/` or repo-root
files; weaken a gate to exit a loop.
