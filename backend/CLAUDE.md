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

**Starter fixtures only** (`bench/fixtures/`, 17 files, 40 labelled
Python + Java crypto usages — see `bench/README.md`): precision 1.000,
recall 1.000, F1 1.000, measured 2026-09-19 via
`uv run python bench/evaluate.py`. Grew from 15 (Python-only) to 40 usages
in M1 (Track CC) when the Java detector (`engine/source_java.py`) shipped.

This is **not** the brief's Layer A/B corpus or a Loop B1 DEV/HOLD result
— those don't exist yet (no real third-party projects have been sourced or
labelled). Do not repeat the brief's original example numbers (precision
1.000, recall 0.986 on "70 usages", 4.9-17.3 MB/s, etc.) as if they were
measured in this repo — they weren't. Treat the number above as the floor
for `bench/fixtures/` specifically: `tests/test_bench_evaluate.py` fails if
it regresses. Once a real DEV/HOLD corpus exists (Loop B1), replace this
section with that result instead.

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
numbers; call external services at runtime; weaken a gate to exit a loop.

(The original "don't edit frontend/ or repo-root files" restriction only
applied while two separate agent tracks were building backend/frontend in
parallel. Once both are merged, see the root `CLAUDE.md` instead -- it's
the shared reference for whoever owns the whole repo at that point.)
