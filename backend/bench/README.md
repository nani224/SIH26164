# bench/

`evaluate.py` runs `engine.scanner.scan()` over `fixtures/` and checks the
result against `truth.json`, printing real precision/recall/F1.

**This is a small, hand-built starter fixture set (8 files, 15 labelled
usages), not the brief's Layer A/B corpus or the Loop B1 DEV/HOLD split**
(>=150 labelled usages across 3 unseen real projects). That corpus doesn't
exist yet -- building it means sourcing and hand-labelling real third-party
codebases, which is future work (see `backend/PLAN.md`). Treat the numbers
here as a sanity floor for the specific rules that exist today (Python:
hashlib digests, hmac.new, RSA/EC keygen via `cryptography`, symmetric
cipher construction), not a claim about accuracy on arbitrary code.

Run: `uv run python bench/evaluate.py` (from `backend/`).

Last measured (2026-09-17, this rule set): precision 1.0, recall 1.0, F1
1.0 (15/15 true positives, 0 false positives/negatives) -- see
`backend/PROGRESS.md` for the exact command output.
