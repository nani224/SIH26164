# Q&A Pack

Short, direct answers to the questions this project gets asked most,
each with a file or number a skeptical reader can go check. Not a pitch
deck — every claim here should survive someone actually running the
command.

---

**Why not use an LLM/ML for detection or scoring?**
Determinism and auditability: the same input must always produce the
same finding and the same score, with a reason a reviewer can trace back
to a fixed rule (`backend/engine/families.py`'s V-table,
`backend/engine/risk.py`'s formula), not a model's internal state that
can drift between runs or providers. `scripts/verify_airgap.py` enforces
this mechanically — zero LLM/AI-SDK imports permitted anywhere in
`api/`/`engine/`/`scheduler/`.

**Why report recall 0.8214 instead of a rounder, higher number?**
Because it's real, measured today (2026-09-20) against 56 hand-labelled
usages in unseen third-party code
(`uv run python bench/real_world/evaluate.py`), with every miss
individually explained in `backend/bench/real_world/README.md` — not a
number chosen to look good. A tool that claims 100% on a corpus nobody
can independently re-run is making an unfalsifiable claim; 0.8214 with
an itemized false-negative list is a claim you can go verify or
disprove yourself in five minutes.

**Do you cover C/C++ and firmware?**
C/C++ source: yes — `backend/engine/source_c.py`, real precision/recall
in the per-language table (`docs/BENCHMARK.md`), 1.0/1.0 on the 5-usage
real-world C sample. Compiled binaries/firmware: partial — static
byte-signature/ELF-constant detection exists (e.g. a stripped-binary AES
S-box match, see `docs/engineering/backend/PROGRESS.md`'s Finding B
history) but has no measured precision/recall floor and is not claimed
as a general firmware-analysis capability.

**How is this different from CBOMkit or sonar-cryptography?**
Both are real, comparable open-source CBOM/crypto-detection projects;
we haven't run a head-to-head benchmark against either and won't claim
one without doing that work first. What we can say concretely about
*this* project: risk scoring beyond bare detection (the Mosca formula,
`backend/engine/risk.py`) is not something either of those tools does
as their core focus, and every accuracy number in this repo is measured
against a real, versioned, git-committed corpus a reader can re-run
(`docs/BENCHMARK.md`), not asserted.

**What did you deliberately NOT build, and why?**
Multi-tenant RBAC/SSO, cloud KMS integration, Kubernetes cluster
discovery, SIEM export, ticketing-system integration, and a distributed
agent fleet — all listed honestly in `README.md`'s Known Gaps &
Roadmap, none silently implied to exist. The reusable CI Action has
only been proven calling itself *within* this repo, not from a genuinely
external consuming repository — blocked on a one-time human action
(creating that repo), not a technical gap:
[ADR 021](decisions/backend/021-external-repo-proof-blocked.md).

**Why does `U` (urgency) get pinned to 1.0 for classically broken
primitives instead of following the same clamp formula as everything
else?**
Because Mosca's `X+Y>Z` margin reasoning models *quantum* risk timing —
it doesn't apply to something already broken by classical cryptanalysis
today (MD5, SHA-1, DES, RC4). Moving the CRQC horizon shouldn't change
urgency for a primitive that's already exploitable now; the risk formula
in root `CLAUDE.md` encodes this explicitly (`U = 1 if classically
broken`), and `backend/tests/test_risk_formula.py` pins it as an
invariant.

**Is the "10,000 findings in <200ms" rescore number real, or a
synthetic best case?**
Real, but the specific figure varies cold vs. warm (149.26ms cold /
~84ms warm — see the Track A1 P7 investigation cited in
`README.md`'s Measured Verification Results) due to normal OS/DB cache
state, not inconsistent measurement. Separately, this project's own
finale pass found and fixed a real regression in a *different* endpoint
(`GET /findings`, 710ms→8.34ms) — see
[ADR 014](decisions/backend/014-rescore-performance.md)'s neighbor
commit in `CHANGELOG.md` for that story, which is exactly the kind of
thing a "trust nothing unverified" pass is supposed to catch.

**How do I verify any of this myself instead of taking the README's
word for it?**
Every number cited across `docs/` names the exact command that produced
it. Clone the repo, run that command, compare. If it disagrees with what's
written here, the number in this repo is wrong and should be treated as a
bug, not the other way around.
