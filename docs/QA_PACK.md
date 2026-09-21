# Q&A Pack

Short, direct answers to the questions this project gets asked most,
each with a file or number a skeptical reader can go check. Not a pitch
deck — every claim here should survive someone actually running the
command.

---

### Core Principles & CMC v1.0

**Why is coverage not recall?**
Recall measures what percentage of *known* ground-truth crypto in a curated benchmark was detected by rules ($TP / (TP + FN)$). Coverage measures what fraction of *all* extracted cryptographic suspicion evidence across an actual target codebase was accounted for ($M_{\text{attributed}} / M_{\text{total}}$). A tool can have 99% recall on known library patterns while achieving low coverage on proprietary, hand-rolled, or obfuscated crypto it has never seen.

**Why is a high residue number honest rather than embarrassing?**
High residue openly reports unmodeled, suspicious cryptographic evidence (unexplained S-boxes, ARX rotations, modular loops) instead of sweeping it under the rug. Hiding unexplained evidence produces an illusion of complete safety that misleads security officers. Presenting residue with exact byte ranges empowers engineering teams to investigate, promote to rules, or document debt.

**Why can't an ML-based tool produce a stable residue set?**
ML and LLM detectors rely on probabilistic token distributions that fluctuate across inference runs, temperatures, and model versions. Residue clusters require deterministic byte-level attribution and content-hash invariance to track cryptographic debt reliably across scans. If evidence shifts spuriously without underlying code changes, debt ledgers, drift tracking, and attestation digests become useless.

**What did we deliberately NOT build, and why?**
We deliberately did not build multi-tenant RBAC/SSO, automatic in-place code rewrites, or direct cloud KMS discovery for Azure Key Vault and GCP KMS (which are honestly marked `[Roadmap]` alongside our LocalStack AWS KMS). We do not perform unconstrained dynamic execution or symbolic execution of arbitrary stripped binaries. Our scope is focused strictly on deterministic, air-gapped discovery, mass conservation coverage, and quantum-risk scoring.

---

### Engineering & Methodology Details

**Why not use an LLM/ML for detection or scoring?**
Determinism and auditability: the same input must always produce the
same finding and the same score, with a reason a reviewer can trace back
to a fixed rule (`backend/engine/families.py`'s V-table,
`backend/engine/risk.py`'s formula), not a model's internal state that
can drift between runs or providers. `scripts/verify_airgap.py` enforces
this mechanically — zero LLM/AI-SDK imports permitted anywhere in
`api/`/`engine/`/`scheduler/`.

**Do you cover C/C++ and firmware?**
C/C++ source: yes — `backend/engine/source_c.py`, real precision/recall
in the per-language table (`docs/BENCHMARK.md`). Compiled binaries/firmware:
PE and Mach-O header parsing (`backend/engine/binary.py`), sandboxed Squashfs/CPIO
extraction (`backend/engine/firmware.py`), and byte-signature/table matching (e.g.
stripped-binary AES S-box matches) with hostile-input hardening verified in
`tests/test_hostile_inputs.py`.

**How do I verify any of this myself instead of taking the README's word for it?**
Every number cited across `docs/` names the exact command that produced
it. Clone the repo, run that command, compare. If it disagrees with what's
written here, the number in this repo is wrong and should be treated as a
bug, not the other way around.

