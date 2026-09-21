# 007 — Python `key.sign()`/`key.verify()` via parameter type annotation (M4)

## Status

Accepted

## Context

M3's real-world HOLD run (`bench/real_world/`) left 8 false negatives in
`pyjwt_algorithms.py`, all the same shape: PyJWT's `RSAAlgorithm`/
`ECAlgorithm`/`OKPAlgorithm` classes implement `sign(self, msg, key)`/
`verify(self, msg, key, sig)` methods that call `key.sign(...)`/
`key.verify(...)` -- a real, direct signing/verification operation, but
one where the detector's existing `object.attribute(...)` matching (only
recognizes a fixed set of module names like `hashlib`/`hmac`/`rsa`/`ec`)
has no way to know `key`'s concrete type from the call site alone. This
was the single largest false-negative cluster in the corpus (8 of 12
total misses), so it's the target for M4's "close the largest cluster."

The obvious-looking fix -- track `key = rsa.generate_private_key(...)`
style local assignments and propagate the family to later `.sign()`/
`.verify()` calls on the same variable, mirroring the Java
`KeyPairGenerator`/`initialize` linkage (ADR 004) and the OpenSSL EVP
ctx linkage (ADR 006) -- doesn't apply here: `key` in every one of these
methods is a **function parameter**, not a locally-constructed variable.
There is no constructor call to link back to within this file at all.

## Decision

Python function parameters can carry type annotations
(`key: RSAPrivateKey`), and pyjwt's real code does exactly that on every
one of these methods. This is a genuine static fact available right at
the call site's enclosing function signature -- no guessing, no
cross-file dataflow, no runtime behavior inference.

`engine/source_python.py`: any `X.sign(...)`/`X.verify(...)` call (the
existing `object.attribute(...)` query already captures this shape, no
new query pattern needed) now additionally checks whether `X` matches a
parameter name in the *enclosing* `function_definition`
(`_find_enclosing_function` walks up the tree; `_resolve_param_type_family`
finds the matching `typed_parameter`, reads its `type` annotation node,
and matches its text against a small substring table of real, stable
`cryptography`-library public class names: `"RSA"` -> RSA, `"EllipticCurve"`
-> ECDSA, `"Ed25519"` -> ED25519). If `X` isn't a parameter, has no type
annotation, or the annotation doesn't match a known key class, no
detection fires -- there is no fallback guess, unlike the Java/C linkage
patterns' "still emit once, unresolved" fallback, because here an
unresolved case genuinely means "this isn't a recognized crypto key
type," not "the same known operation, just missing one detail."

**Deliberately not implemented**: pyjwt's own type alias
`AllowedECKeys = Union[EllipticCurvePrivateKey, EllipticCurvePublicKey]`
(used by `ECAlgorithm.verify`'s `key` parameter) is not resolved --
doing so would mean reading pyjwt's own source to learn a project-
specific alias name, which is tuning the detector to this exact HOLD
file rather than building a generalizable rule (the root `CLAUDE.md`'s
"never tune on HOLD" rule, applied to *design decisions* discovered via a
HOLD file, not just to withholding a literal label change). Similarly not
implemented: `OKPAlgorithm.verify`'s call is on a **local variable**
(`public_key = key.public_key() if ... else key`) rather than a typed
parameter directly -- resolving that needs real local dataflow tracking
inside the function body, a materially different (and materially larger)
feature than reading a signature, left as a known, documented gap rather
than attempted under this ADR's narrower scope.

## Consequences

- Real-world (HOLD) recall improved 0.625 -> 0.8125 (added 6 true
  positives: RSA sign/verify x2 each occurrence, ECDSA sign, Ed25519
  sign) with **zero new false positives** -- precision stays 1.0.
  Verified via `uv run python bench/real_world/evaluate.py`.
- Layer A (`bench/fixtures/`) stays 56/56, unaffected -- this pattern
  isn't exercised by any existing Python starter fixture; added new,
  dedicated unit tests instead (`tests/test_source_python.py`): one
  positive case per family (RSA/ECDSA/Ed25519, sign and verify), one
  negative case for the deliberately-unresolved type-alias scenario, one
  negative case for an untyped/unrelated `.sign()` call (proving the "no
  guessing" property directly, not just by omission).
- General mechanism, not pyjwt-specific: any real Python code using
  `cryptography`-library key classes as typed parameters and calling
  `.sign()`/`.verify()` on them benefits, not just this one HOLD file.
- Two of the original 8 false negatives remain, both honestly
  irresolvable by this mechanism (see Context) -- recorded in
  `bench/real_world/README.md`, not silently dropped from tracking.
