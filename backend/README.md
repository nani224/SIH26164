# ECDAT Backend

Backend for the Enterprise Cryptographic Discovery & Analysis Tool
(SIH26164). **Phase 0 only** right now: a contract-exact FastAPI stub, no
real detection engine, no persistence, no auth. See `PLAN.md` for what's
next and `docs/decisions/backend/001-phase0-skeleton.md` for why.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) for dependency management

## Run

```bash
cd backend
uv sync
uv run uvicorn api.main:app --reload
```

The API is served under `/api/v1` (e.g. `http://127.0.0.1:8000/api/v1/health`).
Interactive docs at `http://127.0.0.1:8000/docs`.

All data is in-memory (`api/store.py`, `api/stub_data.py`) and resets on
restart — there is no database yet (Phase 2).

## Test / gates

```bash
cd backend
uv run ruff check .
uv run mypy --strict .
uv run pytest --cov=api --cov=engine --cov=scripts --cov-report=term-missing
uv run python scripts/contract_diff.py
```

## Env vars

None yet. Phase 2+ will add `DATABASE_URL` (SQLite default, Postgres via
config) and Phase 10 will add JWT/CORS-related settings.

## Offline / air-gap

No runtime network calls. The one build-time download this phase needed
(the CycloneDX 1.6 JSON schema, for a CBOM-validation test) is vendored at
`tests/fixtures/cyclonedx/` with its SHA-256 recorded in `TOOLBELT.md` —
`uv sync` plus the vendored fixtures is enough to run every gate above with
no network access.

## Layout

```
backend/
  engine/        # detection/risk/recommendation engine (Phase 1+; empty in Phase 0)
  api/           # FastAPI app, Pydantic models, in-memory stub data/store
  scripts/       # contract_diff.py (contract-keeper check)
  tests/
contracts/
  openapi.yaml   # source of truth API contract (OpenAPI 3.1)
  PROPOSALS.md   # frontend-driven contract change requests
  CHANGELOG.md
docs/decisions/backend/   # ADRs
```
