# bench/real_world/

A small, honest first step toward Loop B1's DEV set: **real, unseen
(never used to build or tune the detector) third-party Python code**,
not synthetic fixtures. Labelled by reading the source *before* running
the detector on it, per Loop B1's rule ("never inspect misses before
labelling").

**This is not the brief's full Loop B1 DEV/HOLD split** (that needs
>=150 labelled usages across 3 unseen projects, one Java/Go/C each, once
those languages have detectors). It's two small real files, Python only,
labelled by hand, run once. Treat it as a sanity check on real code, not
a statistically meaningful accuracy claim.

## Provenance & licence

| File | Source | Licence |
|---|---|---|
| `itsdangerous_signer.py` | [pallets/itsdangerous `src/itsdangerous/signer.py`](https://github.com/pallets/itsdangerous/blob/main/src/itsdangerous/signer.py), unmodified | BSD-3-Clause |
| `cryptography_rsa_recipe.py` | [pyca/cryptography RSA docs](https://github.com/pyca/cryptography/blob/main/docs/hazmat/primitives/asymmetric/rsa.rst), the official `generate_private_key` doctest recipe, transcribed from the `.. doctest::` block | Apache-2.0 / BSD (dual-licensed) |

Both licences are on the licence gate's "OK" list (`backend/CLAUDE.md`) --
safe to vendor verbatim.

## Result (2026-09-18, this rule set)

```
$ uv run python bench/real_world/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=4 detected=4 tp=4
```

**4/4** -- every usage within the detector's current scope was found,
zero false positives, on code the detector was never tuned against.

## What this did *not* find (real gaps, noted honestly, not silently fixed)

Reading `itsdangerous_signer.py` and a broader real file
([PyJWT's `jwt/algorithms.py`](https://github.com/jpadilla/pyjwt/blob/master/jwt/algorithms.py),
MIT, not vendored here) surfaced real detector limitations, tracked in
`backend/PLAN.md` rather than fixed in this pass:

1. **Bare attribute references aren't detected**, only calls. PyJWT does
   `SHA256: ClassVar[HashlibHash] = hashlib.sha256` (assigning the
   function object, never calling it directly in that line) -- our
   query only matches `hashlib.sha256(...)` call nodes, so this
   registry-style pattern is a false negative. `FindingSource.AST_REFERENCE`
   already exists in the schema for exactly this case but nothing
   populates it yet.
2. **No intra-file type inference**, so `key.sign(...)`, `key.verify(...)`,
   `load_pem_private_key(...)` where `key`'s type isn't known from the
   call site alone are missed entirely. This is explicitly listed as
   future work in the brief's own Phase 7 ("intra-file type inference for
   key.sign/verify/exchange").
3. `hmac.compare_digest(...)` is correctly *not* flagged -- it's a
   timing-safe comparison utility, not a keygen/encrypt/digest primitive,
   so it's out of scope by design, not a gap.

Per Loop B1's cap-of-6-iterations process, the next iteration (not done
this pass -- explicitly deferred) would pick gap #1 (the largest,
cheapest cluster) and implement a query + test.
