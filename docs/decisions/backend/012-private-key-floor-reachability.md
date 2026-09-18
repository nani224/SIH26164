# 012 — Retarget the private-key >=90 floor to a reachable signal

## Status

Accepted

## Context

Root `CLAUDE.md`'s non-negotiable domain rule: "Unencrypted private key
outside test paths -> score >= 90." `engine/factors.py::derive_risk` had a
`forced_private_key` guard for this, and a green unit test
(`tests/test_factors.py`), but the whole-repo audit found it was dead code:
the guard fired on `detection.kind == "key"` -- and no real detector
(`engine/source_python.py`, `engine/source_go.py`) ever produces
`kind=FindingKind.KEY`. Every real detection is `kind=ALGORITHM` (or
`PROTOCOL` for HMAC). `kind=KEY` only ever appeared in `api/stub_data.py`'s
hand-built example data. The unit test passed because it hand-built a
`Detection(kind=FindingKind.KEY, ...)` directly, bypassing every real
detector -- it proved the guard's *logic* worked, not that any real scan
could ever trigger it.

There is currently no PEM/private-key-file parser in the engine (no
`FindingSource.PEM_PARSER`/`SSH_KEY_PARSER` producer exists) -- building one
is real, separate detector work, not a one-line fix, and is out of scope
here.

## Decision

Retarget the guard to the closest real signal a scan can actually produce
today: `detection.function == CryptoFunction.KEYGEN` combined with
`V == 1.0` (a Shor-broken asymmetric family -- RSA/DSA/DH/ECDH/ECDSA/
Ed25519/X25519, per `engine/families.py`). A `generate_private_key()` call
for one of these families is, in fact, a private key coming into existence
in the scanned code; treating it as the private-key case is a defensible,
reachable reading of the domain rule given the engine's current detection
surface -- not a new capability, just fixing which of today's real
detections the existing rule applies to.

`tests/test_factors.py`'s two unit tests were updated to construct
`Detection(kind=ALGORITHM, function=KEYGEN, family=RSA, ...)` (a shape a
real detector actually produces) instead of the unreachable
`kind=KEY, function=SIGN`. A new end-to-end test,
`tests/test_scans_real_engine.py::test_real_rsa_keygen_scan_triggers_private_key_floor`,
POSTs a real file through `POST /scans`, runs the real tree-sitter
detector, and asserts the floor applied on the *actual* returned finding --
proving the rule is reachable from a real scan, not just from a
hand-constructed `Detection`.

## Consequences

- The private-key floor rule is now genuinely reachable: any real RSA/DSA/
  DH/ECDH/ECDSA/Ed25519/X25519 keygen detection outside a `test`-exposure
  path scores >= 90 (critical), matching the domain rule.
- Still not covered: a private key sitting in an actual `.pem`/`.key` file
  (no bytes ever parsed, no keygen call in source). That needs a real
  file-content detector (`FindingSource.PEM_PARSER`) -- tracked as a gap,
  not silently dropped. `api/stub_data.py`'s `kind=KEY` example finding
  remains as documentation of that target shape for whoever builds it.
- No change to the risk formula itself (`engine/risk.py`) or to any other
  factor derivation.
