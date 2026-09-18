# ECDAT Backend

Backend for the Enterprise Cryptographic Discovery & Analysis Tool
(SIH26164). **Phases 0-2 done**: a contract-exact FastAPI app backed by
real SQLite persistence, plus a real, working Python detection engine with
a small starter bench harness — not yet wired together (`POST /scans`
still creates an empty scan; that's Phase 3). No auth. See `PLAN.md` for
what's next and `docs/decisions/backend/` for why things are built the
way they are.

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

Scans/findings/policies persist in SQLite (`api/db.py`, `api/store.py`) —
survives restarts. `api/stub_data.py` is now only the one-time seed data
loaded into an empty database.

## Test / gates

```bash
cd backend
uv run ruff check .
uv run mypy --strict .
uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing
uv run python scripts/contract_diff.py
uv run python bench/evaluate.py   # real precision/recall on the starter fixture set
```

## Env vars

- `DATABASE_URL` — default `sqlite:///./ecdat.db`. SQLModel/SQLAlchemy
  URL, so a Postgres URL should work in principle (untested against a
  real Postgres instance so far).

Phase 10 will add JWT/CORS-related settings.

## Offline / air-gap

No runtime network calls. The one build-time download this phase needed
(the CycloneDX 1.6 JSON schema, for a CBOM-validation test) is vendored at
`tests/fixtures/cyclonedx/` with its SHA-256 recorded in `TOOLBELT.md` —
`uv sync` plus the vendored fixtures is enough to run every gate above with
no network access.

## Layout

```
backend/
  engine/        # detection/risk/recommendation engine (Python detector so far)
  api/           # FastAPI app, Pydantic models, SQLModel persistence (db.py, db_models.py, store.py)
  bench/         # evaluate.py + starter fixtures (see bench/README.md)
  scripts/       # contract_diff.py (contract-keeper check)
  tests/
contracts/
  openapi.yaml   # source of truth API contract (OpenAPI 3.1)
  PROPOSALS.md   # frontend-driven contract change requests
  CHANGELOG.md
docs/decisions/backend/   # ADRs
```
