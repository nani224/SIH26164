# ECDAT v1.0 — 7-Minute Coverage & Continuous Operation Demo Script

Story: **ECDAT tells you what it found, and proves what it couldn't explain.**
Most scanners hide unmodelled crypto behind an illusion of 100% safety. ECDAT pairs every scan with a **Coverage Certificate** and a **Debt Ledger of Residue Clusters**. If hand-rolled crypto enters the codebase, coverage falls and residue rises. Promoting that residue to a rule closes the debt, raises coverage, and turns blind spots into managed findings.

Every step below was executed and verified against the live, unmocked stack (`release/v1.0.0`) on 2026-09-21.

**Setup before jury arrives**:
```bash
make demo    # or Option 2 native in README.md
```
Confirm `http://localhost:3000` loads and `http://localhost:8000/api/v1/health` returns `{"status":"ok"}`.

---

## Minute 0–1 — Blocked PR & Scheduled Scanning

**Say**: "Most scanners are one-shot scanners that run once and forget. ECDAT blocks weak crypto at the PR gate, registers the target, and watches it continuously."

**Do**: Show the blocked PR terminal check (`python bench/ci_scan.py`). Navigate to `/launcher` and register a repo target with an automated 1-minute schedule.

**Fallback**: If live registration delays, point to the pre-seeded target on `/estate` and show its live updating `lastScanAt` timestamp.

---

## Minute 1–2 — Overview: Coverage Certificate as a First-Class Metric

**Say**: "Look at the Overview console. Coverage isn't a footnote — it has the exact same visual weight as findings. If a scan has 247 findings but 7 unexplained clusters, an analyst knows immediately that the scan is an open question."

**Do**: Navigate to `/overview`. Point to the **Coverage Certificate Card**:
- Mass Conservation Bar: Attributed (teal), Excluded (slate), Residue (vermilion).
- Ratio metric: 44.8% coverage, 5-scan trend sparkline.
- Prominent Residue CTA: *"7 unexplained clusters — review"*.

**Fallback**: If sparkline animation is paused, click the card to open `/residue`.

---

## Minute 2–3 — Drift with Coverage Drop

**Say**: "When a developer introduces unmodelled crypto — like a hand-rolled ARX cipher without recognisable names — traditional scanners report zero new findings. In ECDAT, coverage visibly drops."

**Do**: Navigate to `/drift`. Point to the **Coverage Shift Card**:
- Net coverage change: `Coverage -4.2%`.
- New unexplained residue clusters listed directly in the drift breakdown.

**Fallback**: If viewing historical drift, select the prior snapshot comparison from the snapshot dropdown.

---

## Minute 3–4 — Residue Explorer: Exact Bytes at the Exact Range

**Say**: "Never report uncertainty without a location. Let's see the exact bytes that triggered this residue."

**Do**: Click the residue cluster to navigate to `/residue` (Screen 16).
- Select cluster `c8d35ec6...` (magnitude 32.0).
- Open the Occurrence drawer: show the split **Hex & Source Range Viewer** highlighting the exact byte range `[offset, offset+len]`.
- Point out the extractor signals (`arx.source_rotate_xor`, `table.bijection_256`).

**Fallback**: Toggle between Hex and Source tabs using keyboard shortcuts (`H` / `S`).

---

## Minute 4–5 — Debt Ledger Workflow: Promote to Rule & Exclude Guard

**Say**: "How do you close cryptographic debt? You can promote it to a rule, or exclude it with strict accountability."

**Do**:
1. Click **Exclude Cluster**: Attempt to submit with an empty justification. Show that the UI and API strictly block submission (*"Justification must be at least 10 characters"*). Fill in owner and reason to demonstrate valid exclusion.
2. Click **Promote to Rule**: Show the generated AST/byte detection rule scaffold with its test fixture.

**Fallback**: If modal is dismissed, click **History** tab to inspect prior audit-logged transitions.

---

## Minute 5–6 — Re-Scan: Coverage Rises & Finding Appears

**Say**: "Now that the rule is registered, the engine re-scans. The residue mass drops to zero, coverage rises, and the hand-rolled cipher is now a first-class finding with a quantum risk score."

**Do**: Show the post-promotion scan:
- Residue mass drops by exactly 32.0 units.
- Coverage ratio increases.
- The item now appears in `/inventory` with Mosca risk factor breakdown ($V, F, U, E, K$).

**Fallback**: Show the CLI verification proof from `tests/test_debt_closure.py` proving the exact 32.0 mass transfer.

---

## Minute 6–7 — Proof Surfaces: Attestation, CBOM & Benchmark

**Say**: "How does an auditor verify this? Not by taking our word for it, but by verifying cryptographic proof."

**Do**:
1. On `/overview`, click **Verify Attestation**: Display the signed CycloneDX 1.6 CBOM SHA-256 digest, run manifest, and click **Verify Cryptographic Attestation** (green verified badge).
2. Click **Public Benchmark**: Show language-by-language precision/recall and mean coverage ratio, openly disclosing lower-performing edge cases.

**Close**: "This is ECDAT v1.0: coverage as prominent as findings, mathematical mass conservation, zero-drift contracts, and an air-gapped, verifiable audit trail."
 "Everything you just saw — the scheduler, the drift, the alert,
the probe, the tamper-catch — ran against a real backend and a real
frontend, MSW mocks off, for the first time in this project's history this
release. The full evidence is in the repo's own commit history and ADRs,

## If something misbehaves live

- **Scheduler hasn't fired yet**: narrate the cron interval and switch to
  the pre-seeded target's history instead of waiting.
- **Drift/alert panel empty**: use the pre-staged second target
  (`g3-run2-target` or equivalent) which already has multiple snapshots.
- **TLS probe times out**: the demo weak-TLS container may need a restart
  (`docker compose --profile demo restart demo-weak-tls`); fall back to
  showing a previously-captured probe result already in the findings list.
- **CBOM export button unresponsive**: `curl` the endpoint directly and
  show the raw JSON — the point is the schema validity, not the click.
