# bench/

`evaluate.py` runs `engine.scanner.scan()` over `fixtures/` and checks the
result against `truth.json`, printing real precision/recall/F1.

**This is a small, hand-built starter fixture set (17 files, 40 labelled
usages), not the brief's Layer A/B corpus or the Loop B1 DEV/HOLD split**
(>=150 labelled usages across 3 unseen real projects, see
`bench/real_world/` for that separate, honestly-smaller-than-target
effort). That corpus doesn't exist yet -- building it means sourcing and
hand-labelling real third-party codebases, which is future work (see
`backend/PLAN.md`, M3). Treat the numbers here as a sanity floor for the
specific rules that exist today (Python: hashlib digests, hmac.new, RSA/EC
keygen via `cryptography`, symmetric cipher construction; Java: JCA/JCE
`Cipher`/`KeyPairGenerator`/`KeyGenerator`/`MessageDigest`/`Signature`/
`KeyAgreement`/`Mac`/`SSLContext`/`KeyStore`/`SecretKeySpec` plus direct
BouncyCastle lightweight-API classes), not a claim about accuracy on
arbitrary code -- these fixtures were written to exercise exactly the
patterns the detector implements, so 1.0/1.0 here is expected by
construction, not evidence of general recall (that's what
`bench/real_world/` measures).

Run: `uv run python bench/evaluate.py` (from `backend/`).

Last measured (2026-09-19, M1 Track CC -- added the Java rule set):
precision 1.0, recall 1.0, F1 1.0 (40/40 true positives, 0 false
positives/negatives) -- see `backend/PROGRESS.md` for the exact command
output. Prior measurement (2026-09-17, Python-only): 15/15.
