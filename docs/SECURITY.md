# Security

## Threat model

ECDAT's core job is ingesting and parsing **untrusted input**: arbitrary
source trees, uploaded archives, and — for the continuous-operation
surface — live TLS/SSH handshakes and container registry layers from
operator-specified targets. The primary threat isn't "an attacker reads
the database"; it's **the scanner itself becoming the attack surface**
via a malicious repo, archive, or probe target designed to exploit the
tool that's scanning it.

Concretely, in priority order:

1. **A hostile archive upload escapes its sandbox** (path traversal,
   symlink escape, decompression bomb) during `POST /scans/upload`.
2. **A crafted source file exploits the detection engine itself**
   (tree-sitter parser, not the app) rather than merely producing a
   false finding.
3. **A probe target abuses the live-network surface** — SSRF via a
   crafted hostname/redirect, or a probe destination outside the
   intended allowlist.
4. **The audit log is tampered with** outside the application layer
   (direct DB access) to hide a triage change or a scan result.
5. **A dependency ships a real vulnerability** into either app.

Out of scope by design: ECDAT is not a secrets manager, doesn't
authenticate end users today (see Known Gaps in `README.md`), and
assumes whoever can reach its API is already trusted at the network
level (air-gapped, no public exposure implied).

## Hardening, by threat

### 1. Sandboxed ingest (`backend/engine/ingest.py`)

Every archive entry is validated **before** extraction: suspicious-path
check (`../`, absolute paths, drive letters), symlink-target escape
check, decompression-bomb check (uncompressed-size cap, file-count cap),
and per-entry compression-ratio check. `zipfile` has no built-in
extraction filter (unlike `tarfile`'s PEP 706 `filter="data"`, used on
the tar path) — the pre-validation loop *is* the mitigation, which is
why `zf.extractall(target_dir)` carries a `# nosec B202` at
`engine/ingest.py:193`: bandit's static rule can't recognize a
pre-validation pattern as a mitigation, so this was verified both by
code review and by a real hostile-archive upload (path-traversal zip,
`../../etc/evil_escaped.txt`) that was correctly rejected with a 400 and
left nothing on disk — see
[ADR 015](decisions/backend/015-sandboxed-ingest.md).

### 2. Live probe destinations (`backend/probes/guard.py`)

Every real network probe (TLS, SSH, registry) validates its destination
against an allowlist (localhost / approved test/demo containers) before
connecting — `SecurityException` on anything else, proven against real
external hostnames (`quay.io`, `ghcr.io`) in
`backend/tests/test_probes_adapters.py`. `backend/probes/webhook.py` is
the one documented exception (an operator-configured
`ALERT_WEBHOOK_URL`, not attacker-controlled input) — see
`backend/scripts/verify_airgap.py`'s `ALLOWED_UNGUARDED_NETWORK_FILES`.

### 3. Air-gap / deterministic-scoring enforcement

`backend/scripts/verify_airgap.py` AST-scans `api/`, `engine/`, and
`scheduler/` for any network-capable import at all (zero tolerance), and
`probes/` for a network-capable import used without importing
`probes.guard` or being explicitly listed as a documented exception.
Both rules have been proven with real, deliberately-introduced
violations (a temporary `import httpx` in `engine/scanner.py`; a
temporary un-listing of `webhook.py`) and reverted. Run:

```bash
cd backend
uv run pytest tests/test_airgap.py
```

### 4. Tamper-evident audit log

Every mutation (scan create, triage change, policy update, rescore) is
recorded in a SHA-256 hash-chained `audit_log` table. `GET
/api/v1/audit/verify` walks the chain and reports the first broken link
if any row was altered outside the application layer — proven against a
real raw-SQL `UPDATE` tamper in this project's own finale verification
pass. See [`OPERATIONS.md`](OPERATIONS.md).

### 5. Dependency scanning

`gitleaks` (full history), `bandit` (static analysis), `pip-audit`, and
`trivy` (filesystem + image scanning) are all run as part of this
project's release verification; results and their disposition below.

## Bandit findings and their justification

Three `# nosec B608` (possible SQL injection) annotations in
`backend/api/store.py`, all the same pattern: an f-string containing a
literal placeholder **token** (`{ph}`, resolved at call time to `?` or
`%s` depending on dialect), never an interpolated value — every real
value is a bound parameter passed separately:

```python
cur.execute(f"SELECT id FROM scans WHERE id = {ph}", (scan_id,))  # api/store.py:242
```

Bandit's static rule flags any f-string inside a `.execute()` call
regardless of what's actually interpolated; these were verified false
positives by code review (the interpolated value is always the
placeholder character, never user input) and by live testing. One
further B608 finding, in a larger multi-line CTE string, could not be
suppressed via any `# nosec` placement tried (a bandit line-attribution
limitation on multi-line f-strings) and is instead documented via a
comment block directly above it — a known, accepted tooling gap, not an
unreviewed finding.

One `# nosec B202` (unsafe `extractall`) in `backend/engine/ingest.py`,
covered above under sandboxed ingest.

## gitleaks: 8 hits, all false positives

A full-history scan (`gitleaks detect --log-opts="--all"`, 75 commits)
found 8 matches, all manually verified as false positives on review: type
annotations that read like key names (`key: Ed25519PrivateKey | Ed448PrivateKey`
in test signatures), a Go algorithm-name constant
(`KeyAlgoED25519`), and fabricated test/mock key material with literal
`"..."`/`"SECRET"` placeholder text (`backend/tests/test_hsm_inventory.py`,
`frontend/src/mocks/data.ts`) that's obviously synthetic, not truncated
real key material. No real secret has ever been committed to this repo.

## Known, accepted dependency exception

`cryptography` carries 3 real HIGH-severity CVEs (CVE-2026-69247,
CVE-2026-69249, GHSA-537c-gmf6-5ccf) at the version this repo is pinned
to. Not fixable today without an unverified compatibility gamble — the
transitive dependency that pulls it in (`sslyze`, the real TLS probe
library) hard-pins `cryptography<47`, and every fix for these CVEs lands
at `>=47`. Full exposure assessment and the exact unblock condition:
[ADR 017](decisions/backend/017-cryptography-cve-exception.md).

## Reporting

This is a project repository, not a product with a public disclosure
process. If you find a real issue, open it as a GitHub issue or PR
against `nani224/SIH26164` with reproduction steps.
