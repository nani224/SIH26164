# ECDAT v0.3 — 7-Minute Jury Demo Script

Story: **ECDAT doesn't just scan once — it watches.** Register a target, walk
away, and it keeps finding new weak crypto, alerting on it, and proving its
own audit trail can't be silently tampered with. Every step below was run
for real against a live stack during this release's verification pass
(`docs/decisions/`, `CHANGELOG.md`) — nothing here is aspirational.

**Setup, before the jury arrives** (not part of the 7 minutes):
```bash
make demo    # or the native Option 2 in README.md
```
Confirm `http://localhost:3000` loads and `http://localhost:8000/api/v1/health`
returns `{"status":"ok"}`.

---

## Minute 0–1 — Register a real target, continuous operation begins

**Say**: "Most scanners are one-shot. ECDAT registers a target and keeps
watching it — here's a real repo, on a 1-minute cron."

**Do**: On the Launcher screen, register a local repo path with a 1-minute
schedule (`POST /targets`). Show the response includes a real `id` and
`schedule`.

**Fallback if live registration misbehaves**: use the pre-seeded demo
target instead and narrate "this one's already been running for N minutes"
— point at its `lastScanAt` timestamp updating live.

## Minute 1–2 — It scans unattended

**Say**: "I'm not clicking scan. The scheduler already did."

**Do**: Navigate to `/estate`. Point at the target's `lastScanAt` — younger
than "just now" if you waited the full minute, or already populated from
setup. Open `/targets/{id}/snapshots` (or the Estate detail panel) to show
more than one snapshot exists, each with its own timestamp — proof the
scheduler fired more than once, unprompted.

## Minute 2–3 — Drift: a real new weak algorithm, caught automatically

**Say**: "Now watch what happens when the codebase actually changes."

**Do**: (Pre-stage, before the demo, a one-line edit adding an MD5 call to
the watched repo, or trigger it live if time allows.) After the next
scheduled scan fires, open `/drift`. Point at the new finding in
`added[]` — a real MD5 call, with a real file/line location — and note
`resolved[]` is empty (nothing spurious).

**Say the one sentence that matters**: "This exact path — drift catching a
new weak algorithm between two real scheduled scans — is where we found
and fixed a real bug during this release's own verification: two distinct
findings on different lines of the same file were colliding under the old
identity check, which would have made a new weak algorithm silently vanish
from this exact screen. Unit tests never would have caught it; only
running two real scans did."

## Minute 3–4 — Alert fires, webhook delivers

**Do**: Navigate to `/alerts`. Show the new-critical alert raised from the
drift above. If a webhook receiver is visible (a terminal tail or a second
browser tab on a local receiver), point at the real delivered payload.

## Minute 4–5 — Live infrastructure probes: negotiated ≠ supported

**Say**: "ECDAT doesn't just read code — it can also probe what's actually
running."

**Do**: On `/certificates` or the probe panel, run the weak-TLS probe
against the demo target (`localhost:8443`). Show the UI distinguishing
**supported** ciphers (everything the server's config lists) from
**negotiated** (what the live handshake actually picked) — and that the
matching static Finding now shows `negotiated: true`.

## Minute 5–6 — Mosca: move the CRQC horizon, watch risk react honestly

**Do**: On `/mosca`, drag the Z slider (CRQC horizon) from 15 down to 5
years. Point at the band-changed list updating from a real `POST /rescore`
call — and at a classically-broken finding (an MD5 or DES row) that does
**not** move, because `U = 1.0` is pinned regardless of `Z`. This is the
formula's own invariant, visibly holding under a real UI interaction.

## Minute 6–6:30 — Audit integrity: tamper it, and it tells you

**Say**: "Every mutation in this system is hash-chained. If anyone — even
someone with raw DB access — edits a row after the fact, this catches it."

**Do**: Show `GET /audit/verify` returning `valid: true`. (Pre-staged, not
live during the demo unless time allows) run one raw SQL `UPDATE` against
an audit row, re-call `/audit/verify` — show it now returns `valid: false`
with the exact broken entry identified.

## Minute 6:30–7 — Export a real CBOM

**Do**: From the Inventory or a scan detail screen, export CBOM. Either
open the downloaded JSON directly or state: "This validates against the
real CycloneDX 1.6 strict JSON Schema — checked in CI on every scan."

**Close**: "Everything you just saw — the scheduler, the drift, the alert,
the probe, the tamper-catch — ran against a real backend and a real
frontend, MSW mocks off, for the first time in this project's history this
release. The full evidence is in the repo's own commit history and ADRs,
not just this script."

---

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
