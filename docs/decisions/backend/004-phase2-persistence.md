# ADR 004: Phase 2 persistence design

Status: accepted
Date: 2026-09-18

## Context

Phases 0-1 kept everything in module-level Python dicts/lists
(`backend/api/store.py`, `backend/api/stub_data.py`) — nothing survived a
process restart, and there was nowhere for `engine.scanner.scan()`'s real
output to land. Phase 2 per the brief: "PERSISTENCE: scans, findings (all
raw risk factors stored), policies, triage, audit_log."

## Decision

- **SQLModel + SQLite** (`backend/api/db.py`, `backend/api/db_models.py`),
  matching the brief's stack ("SQLModel (SQLite default, Postgres via
  config)"). `DATABASE_URL` env var, default `sqlite:///./ecdat.db`.
  Postgres isn't exercised this pass (no code precludes it — SQLModel/
  SQLAlchemy's `create_engine` takes any valid URL — but it also isn't
  tested against a real Postgres instance).
- **Schema**: `FindingRecord` flattens every raw risk factor
  (V/F/U/E/K/X/Y/Z/score/band/moscaMargin/reason/classicallyBroken/hndl/
  needsReview) into real columns, per the brief's explicit "all raw risk
  factors stored," plus every field `api/filtering.py` filters/sorts on.
  `Recommendation` and `Policy.default`/`contexts` stay as JSON columns —
  nothing queries into them yet, so normalizing further isn't earning its
  keep. Every mutating `store.py` function writes one `AuditLogRecord` row
  (`scan.create`, `finding.triage`, `finding.rescore`, `policy.put`).
- **Store functions unchanged**: `api/store.py` keeps the exact public
  signatures from Phase 0/1 (`create_scan`, `list_scans`, `get_scan`,
  `list_policies`, `get_policy`, `put_policy`) plus new ones
  (`list_findings`, `get_finding`, `replace_finding`) that routes
  previously called on `stub_data` directly. Routes and the API contract
  are unaffected — `scripts/contract_diff.py` reports zero drift.
  `stub_data.py` stops being the runtime source of truth; `db.init_db()`
  reads it once to seed an empty database.
- **Test isolation**: `tests/conftest.py` sets `DATABASE_URL=sqlite://`
  before `api.db` is first imported, and `api/db.py` uses SQLAlchemy's
  `StaticPool` for in-memory URLs so every connection in the process
  shares one database (plain `sqlite://` would give each connection its
  own empty one). A session-scoped autouse fixture calls `db.init_db()`
  once so tests hitting `api.store` directly (not through a `TestClient`)
  still get a ready schema.

## A bug this design surfaced (and fixed)

Manual end-to-end verification (boot a real server against a file-based
SQLite DB, `POST /scans`, restart the process, re-fetch) caught that
timestamps lost their `Z`/timezone suffix after a DB round-trip: SQLite
has no native timezone-aware datetime type, so SQLAlchemy's default
`DateTime` column silently strips `tzinfo` on write and returns a naive
`datetime` on read (confirmed this isn't fixed by `DateTime(timezone=True)`
either, for the SQLite/pysqlite dialect specifically). Fixed by
`api/db._as_utc()`, which reattaches `tzinfo=UTC` on every read — safe
because every timestamp this app writes already comes from
`datetime.now(UTC)`. Regression test:
`tests/test_db_persistence.py::test_scan_timestamps_survive_db_round_trip_as_utc`.

## Consequences

- Any future datetime column needs the same `_as_utc()` treatment on read
  (or a Postgres backend, which does support `TIMESTAMPTZ` natively) — not
  automatic, easy to forget when adding a new table.
- `stub_data.py` is now purely seed data + the static example graph
  (`default_graph_nodes/edges`, not yet backed by real findings — out of
  scope for this phase).
- The engine still isn't wired to write findings into this store —
  `POST /scans` still creates an empty scan with zero findings. That's
  Phase 3.
