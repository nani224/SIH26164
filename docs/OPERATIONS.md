# Operations

Day-to-day tasks for someone running ECDAT, not developing it. See
[`INSTALL.md`](INSTALL.md) to get a stack up first, and
[`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for a guided walkthrough of the
same flow.

## Run a one-shot scan

**UI**: Launcher screen (`/launcher`) — enter a server-side path or
upload an archive, submit.

**API**:
```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/repo", "policyId": "policy_default"}'
```
Returns a `Scan` with `status: done` (scanning is synchronous — see
[ADR 001](decisions/backend/001-contract-and-api-skeleton.md)) and real
band counts. Fetch findings with `GET /api/v1/scans/{id}/findings`.

## Register a target for continuous scanning

**UI**: Launcher screen, "Register Target" — path + cron schedule.

**API**:
```bash
curl -X POST http://localhost:8000/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "my-service", "kind": "repo", "uri": "/path/to/repo", "policyId": "policy_default", "schedule": "*/5 * * * *"}'
```
The scheduler (`backend/scheduler/`) picks this up and re-scans on the
given cron expression, unattended — no further action needed. Confirm
it's actually firing via `GET /api/v1/targets/{id}/snapshots`: each real
scheduled run adds a new snapshot with its own timestamp.

## Read drift

**UI**: Drift screen (`/drift`) for a target — `Added`, `Resolved`,
`Changed` tabs.

**API**: `GET /api/v1/targets/{id}/drift` — compares the two most recent
snapshots. `added[]` is a real new finding (e.g. a newly introduced weak
algorithm); `resolved[]` is a finding present in the older snapshot but
gone from the newer one; `changed[]` is a finding whose risk band moved.
An empty `resolved[]` alongside a populated `added[]` is expected and
correct — it means nothing regressed, something new appeared.

## Respond to an alert

**UI**: Alerts screen (`/alerts`) — new-critical, cert-expiring, drift,
and probe-downgrade alerts, each with an acknowledge action.

**API**:
```bash
curl -X PATCH http://localhost:8000/api/v1/alerts/{id}/acknowledge
```
If `ALERT_WEBHOOK_URL` is set, the same alert was already delivered to
that endpoint at raise time (Slack/Discord-compatible payload, fails
closed on delivery error — see
[ADR 016](decisions/backend/016-security-hardening.md)).

## Rescore under a different quantum-risk horizon

**UI**: Mosca screen (`/mosca`) — drag the CRQC-horizon (Z) slider.

**API**:
```bash
curl -X POST http://localhost:8000/api/v1/scans/{scan_id}/rescore \
  -H "Content-Type: application/json" -d '{"crqcYears": 5}'
```
Recomputes every finding's score under the new `Z` in one in-DB
operation (budget: <200ms for 10,000 findings — see
[ADR 014](decisions/backend/014-rescore-performance.md)). Classically
broken primitives (`U = 1.0`) never move regardless of `Z` — if they do,
that's a formula-invariant bug, not expected behavior.

## Export a CBOM

```bash
curl http://localhost:8000/api/v1/scans/{scan_id}/cbom -o cbom.json
```
Strictly valid CycloneDX 1.6 JSON — validated in CI against the vendored
schema.

## Backup / restore

The backend's entire state lives in one SQLite file
(`DATABASE_URL`, default `sqlite:///./ecdat.db`). Back it up like any
SQLite database:

```bash
sqlite3 ecdat.db ".backup 'ecdat-backup-$(date +%Y%m%d).db'"
```

To restore, stop `api`, replace the database file, restart. There is no
separate blob/object store to back up alongside it — uploaded scan
archives are extracted into a sandboxed temp directory and discarded
after scanning (see [ADR 015](decisions/backend/015-sandboxed-ingest.md)),
not retained.

## Upgrade / rollback

1. Pull the new backend/frontend code.
2. **Backend**: `uv sync`, then start `api.main:app` — `api/db.py`'s
   `init_db()` runs an idempotent, additive schema migration on startup
   (non-destructive `ALTER TABLE` for new columns). No separate migration
   command exists today; a schema change that isn't purely additive would
   need a manual data migration (none has been needed as of this
   writing).
3. **Frontend**: rebuild (`pnpm build`) with `NEXT_PUBLIC_ENABLE_MSW=false`
   set at build time, restart `pnpm start`.
4. **Rollback**: check out the previous commit/tag and repeat — the
   database schema has never had a breaking (non-additive) change, so a
   rollback doesn't need a down-migration as of this writing. If that
   ever changes, it will be called out in `CHANGELOG.md`.

## Verifying the audit trail hasn't been tampered with

```bash
curl http://localhost:8000/api/v1/audit/verify
```
Returns `{"valid": true, "totalRecords": N}` if the SHA-256 hash chain is
intact, or `{"valid": false, ...}` naming the first broken entry if any
row was altered outside the application layer (e.g. a raw `UPDATE`).
