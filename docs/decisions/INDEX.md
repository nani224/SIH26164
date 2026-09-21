# Architecture Decision Records — Index

`backend/` ADRs were originally numbered by build phase (`001-phase0-...`
through `023-...`), which read as an internal process log rather than a
product reference. Renumbered sequentially by topic (repo-hygiene pass,
2026-09-21) so a reader can find "how does detection work" or "how is
risk scored" without knowing the project's phase history first. Every
citation across the repo (source comments, READMEs, PLAN/PROGRESS logs)
was updated to the new numbers in the same commit as the rename.

`frontend/` ADRs (`001-cipher-observatory-tokens`,
`002-api-contract-and-msw-remediation`) were already topic-named, not
phase-numbered, and are unchanged.

## By topic

**Foundation**
- [001 — Contract & API skeleton](backend/001-contract-and-api-skeleton.md)

**Detection engine**
- [002 — tree-sitter grammar vendoring](backend/002-tree-sitter-vendoring.md)
- [003 — Multi-language detection (Go)](backend/003-multi-language-detection-go.md)
- [004 — Java detection engine](backend/004-java-detection-engine.md)
- [005 — C/C++ detection engine](backend/005-c-cpp-detection-engine.md)
- [006 — OpenSSL EVP cipher-context linkage fix](backend/006-openssl-evp-cipher-context-linkage.md)
- [007 — Python key-method type-annotation fix](backend/007-python-key-method-type-annotation.md)
- [008 — Go bare function-value references fix](backend/008-go-bare-function-reference.md)
- [009 — Corpus growth & AES attribution fix](backend/009-corpus-growth-and-aes-attribution.md)

**Risk scoring**
- [010 — Risk factor derivation (V/F/E/K/X/Y/Z)](backend/010-risk-factor-derivation.md)
- [011 — Private-key ≥90 floor reachability fix](backend/011-private-key-floor-reachability.md)

**Persistence & API**
- [012 — Persistence design (SQLModel)](backend/012-persistence-sqlmodel.md)
- [013 — Estate graph from real findings](backend/013-real-graph-from-findings.md)

**Performance & security**
- [014 — Rescore performance budget](backend/014-rescore-performance.md)
- [015 — Sandboxed streaming ingest](backend/015-sandboxed-ingest.md)
- [016 — Security hardening (audit chain, air-gap)](backend/016-security-hardening.md)
- [017 — `cryptography` CVE exception (sslyze pin)](backend/017-cryptography-cve-exception.md)

**PQC & reporting**
- [018 — NIST PQC catalog](backend/018-pqc-catalog.md)
- [019 — CBOM export & PDF reports](backend/019-reports-and-cbom.md)

**CI/CD**
- [020 — CI/CD precision-floor gate & reusable Action](backend/020-ci-cd-precision-gate.md)
- [021 — External-repo proof — BLOCKED](backend/021-external-repo-proof-blocked.md)

**Release process**
- [022 — Real-stack verification (sandbox workarounds)](backend/022-real-stack-verification.md)
- [023 — Tag push blocked](backend/023-tag-push-blocked.md)

## Old → new number mapping

| Old | New | Old filename stem |
| :-: | :-: | :--- |
| 001 | 001 | phase0-skeleton |
| 002 | 010 | phase1-risk-factors |
| 003 | 002 | phase1-tree-sitter-vendoring |
| 004 | 012 | phase2-persistence |
| 005 | 014 | phase5-rescore-performance |
| 006 | 015 | phase6-sandboxed-ingest |
| 007 | 003 | phase7-multi-language-detection |
| 008 | 018 | phase8-pqc-catalog |
| 009 | 019 | phase9-reports-and-cbom |
| 010 | 016 | phase10-security-hardening |
| 011 | 013 | real-graph-from-findings |
| 012 | 011 | private-key-floor-reachability |
| 013 | 004 | java-detection-engine |
| 014 | 005 | c-cpp-detection-engine |
| 015 | 006 | openssl-evp-cipher-context-linkage |
| 016 | 007 | python-key-method-type-annotation |
| 017 | 020 | ci-cd-precision-gate-and-reusable-action |
| 018 | 008 | go-bare-function-reference |
| 019 | 009 | m7-corpus-growth-and-aes-attribution |
| 020 | 021 | m8a-external-repo-proof-blocked |
| 021 | 022 | g2-real-stack-verification |
| 022 | 017 | cryptography-cve-blocked-by-sslyze |
| 023 | 023 | tag-push-blocked |

A bare "ADR NNN" mention anywhere in the repo (source comments,
PLAN.md/PROGRESS.md session logs, README) refers to the number in effect
*at the time it was written*. Historical session logs (`docs/engineering/
backend/{PLAN,PROGRESS}.md`) were updated to the new numbers as part of
this same renumbering pass so every citation resolves to a real file
today; the table above is what to consult if you're instead reading a
git-blame'd historical diff, an old PR description, or anything else this
pass didn't touch.
