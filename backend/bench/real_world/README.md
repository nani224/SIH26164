# bench/real_world/

A step toward Loop B1's DEV set: **real, unseen (never used to build or
tune the detector) third-party code**, not synthetic fixtures. Labelled by
reading the source *before* running the detector on it, per Loop B1's rule
("never inspect misses before labelling").

**This is still not the brief's full Loop B1 DEV/HOLD split** (that needs
>=150 labelled usages across 3 unseen projects, one Java, one Go, one C).
As of 2026-09-19 this is **5 real files, 2 languages (Python, Go), 25
labelled usages** -- a real, hand-verified expansion from an earlier
7-usage/3-file state, still well short of the brief's target, and
honestly reported as such rather than rounded up. **Java and C have zero
detector coverage at all** (`engine/` only has `source_python.py` and
`source_go.py`) -- a HOLD set in those languages would just measure "no
detector exists," not detection quality, so building one wasn't
attempted; that gap is recorded here, not silently dropped.

This file was found stale once already (it said "two files, Python only,
4/4" after a later commit added a third Go file and pushed the real score
to 7/7 without this file being updated) -- treat every number in it as
something to re-derive with `bench/real_world/evaluate.py`, not quote.

## Provenance & licence

| File | Source | Licence |
|---|---|---|
| `itsdangerous_signer.py` | [pallets/itsdangerous `src/itsdangerous/signer.py`](https://github.com/pallets/itsdangerous/blob/main/src/itsdangerous/signer.py), unmodified | BSD-3-Clause |
| `cryptography_rsa_recipe.py` | [pyca/cryptography RSA docs](https://github.com/pyca/cryptography/blob/main/docs/hazmat/primitives/asymmetric/rsa.rst), the official `generate_private_key` doctest recipe, transcribed from the `.. doctest::` block | Apache-2.0 / BSD (dual-licensed) |
| `go_crypto_sample.go` | **Provenance weaker than the others** -- added in the Phase 7 commit (`2c3357a`) with only the in-file comment "Sample from standard Go crypto recipe (BSD-3-Clause)" and no specific source URL, unlike every other file here. Cannot verify it was actually pulled from a real, unseen third-party project rather than hand-written to exercise the new Go detector. Flagged here rather than quietly counted as equivalent to the other, properly-sourced files. | Claimed BSD-3-Clause, unverified origin |
| `pyjwt_algorithms.py` | [jpadilla/pyjwt `jwt/algorithms.py`](https://github.com/jpadilla/pyjwt/blob/master/jwt/algorithms.py), unmodified. Previously identified in this file (before 2026-09-19) as a known gap source and explicitly *not* vendored -- now vendored and labelled. | MIT |
| `gorilla_securecookie.go` | [gorilla/securecookie `securecookie.go`](https://github.com/gorilla/securecookie/blob/main/securecookie.go), unmodified | BSD-3-Clause |

All licences here are on the licence gate's "OK to vendor" list
(`backend/CLAUDE.md`). **Note for whoever adds more files**: paramiko
(a natural next candidate -- SSH library, heavy RSA/Ed25519/ECDSA key
handling) was fetched and read during this session's labelling pass, but
**discarded and never committed** -- it's LGPL-2.1, which the licence
gate only allows as an unmodified *dependency*, never vendored into this
repo as a copied file.

## Result (2026-09-19, this rule set, 5 files / 25 usages)

```
$ uv run python bench/real_world/evaluate.py
precision=1.0 recall=0.52 f1=0.6842
truth=25 detected=13 tp=13
```

**13/25, zero false positives.** Every false negative is one of the two
documented gaps below (OO `key.sign()`/`key.verify()` type inference, or
Go's generic `cipher.Block` interface) -- see `backend/PROGRESS.md`'s
2026-09-19 entry for the full false-negative list and analysis. This
number is a floor (`tests/test_bench_real_world.py`), not a target --
don't chase it back to 1.0 by weakening the corpus or the labels; closing
the two gaps above for real is what would honestly move it.

## What this did *not* find (real gaps, noted honestly, not silently fixed)

1. **Bare attribute references aren't detected**, only calls. PyJWT does
   `SHA256: ClassVar[HashlibHash] = hashlib.sha256` (assigning the
   function object, never calling it) -- three such lines in
   `pyjwt_algorithms.py` (320-322), plus Go's `hashFunc: sha256.New,` and
   `s.BlockFunc(aes.NewCipher)` in `gorilla_securecookie.go` (139, 148,
   same pattern in Go: passing a function value, not calling it). Our
   queries only match direct call nodes, so this registry-style pattern
   is a false negative in both languages. `FindingSource.AST_REFERENCE`
   already exists in the schema for exactly this case but nothing
   populates it yet.
2. **No intra-file type inference**, so `key.sign(...)`, `key.verify(...)`
   in `pyjwt_algorithms.py` (RSA/ECDSA/Ed25519, lines 683/688/761/777/
   914/926/994/1018) where `key`'s concrete type isn't known from the
   call site alone are missed entirely. Same root cause in Go:
   `cipher.NewCTR(block, iv)` (`gorilla_securecookie.go`:402,420) takes a
   generic `cipher.Block` interface, not a literal `aes.X(...)` call, so
   there's nothing at that call site naming AES specifically even though
   it's AES in this program (the `New()` constructor defaults to
   `aes.NewCipher`). This is explicitly listed as future work in the
   brief's own Phase 7 ("intra-file type inference for key.sign/verify/
   exchange").
3. `hmac.compare_digest(...)` (Python) / `subtle.ConstantTimeCompare(...)`
   (Go, `gorilla_securecookie.go`:384) are correctly *not* flagged --
   timing-safe comparison utilities, not keygen/encrypt/digest primitives,
   out of scope by design in both languages, not a gap.
4. **Dynamic hash algorithm parameters** -- `hmac.new(key, msg,
   self.hash_alg)` (Python, `pyjwt_algorithms.py`:494) and
   `hmac.New(s.hashFunc, s.hashKey)` (Go, `gorilla_securecookie.go`:282,325)
   are both real, direct HMAC calls (the detector can find the call
   itself) but the underlying hash algorithm is a runtime-resolved field,
   not a literal `hashlib.sha256`/`sha256.New` at the call site -- the
   detector cannot determine *which* hash backs the HMAC without the same
   type inference gap as #2.
5. `cryptography.hazmat.primitives.hashes.Hash(hash_alg(), ...)`
   (`pyjwt_algorithms.py`:200) is a real digest computation through a
   completely different API surface than `hashlib` -- not attempted here
   as a labelled usage at all (excluded from truth.json, not silently
   missed) because the hash algorithm is itself a runtime parameter
   (`hash_alg`), making a single confident family label impossible to
   assign honestly without guessing.

Per Loop B1's cap-of-6-iterations process, the next iteration (not done
this pass -- explicitly deferred) would pick gap #1 (the largest, cheapest
cluster, and now confirmed to affect both Python and Go) and implement a
query + test for both languages.

## What's still missing to meet the brief's actual target

- **>=150 usages, not 25.** Growing this further means repeating this
  same process (find a real, unseen, permissively-licensed file with
  genuine crypto usage -- not a library's own class/algorithm
  *definitions*, which don't contain "usages" in the sense these queries
  detect -- read and label it before running the detector, commit the
  label, then run) across more real files. This session prioritized
  correctness of the methodology (real files, real licences, labelled
  blind) over hitting a number, per this pass's own instructions that "a
  lower, honest number is more valuable... than another inflated 1.0."
- **3 unseen projects, one Java/Go/C each.** Still Python + Go only.
  Java and C need their own detectors built first (`engine/` has none) --
  labelling a Java or C HOLD set before a detector exists for either
  language would only prove the detector finds nothing there, which is
  already known and doesn't need a 50-usage sample to demonstrate.
- **A genuine train/tune-blind HOLD split** (a DEV set the detector may
  be iterated against, and a separate HOLD set touched only once, at the
  end) doesn't exist yet -- every file here has only ever been run once,
  which is the right practice so far, but there's no formal DEV/HOLD
  partition documented as such.
