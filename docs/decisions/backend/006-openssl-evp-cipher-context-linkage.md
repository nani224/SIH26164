# 006 — OpenSSL EVP cipher-context linkage (M3 precision-floor fix)

## Status

Accepted

## Context

M2 shipped `EVP_CIPHER_fetch(ctx, "AES-256-GCM", propq)` firing as a
standalone ENCRYPT detection at the fetch call site, on the theory that a
fetched cipher handle is close enough to "AES is used here" (same
heuristic style as Java's `Cipher.getInstance` and Go's `aes.NewCipher`,
which also self-fire at their own call site).

Growing the HOLD corpus (M3) to include a real, blind-labelled file --
OpenSSL's own `demos/cipher/aesgcm.c` -- exposed this as wrong in a way
those other two heuristics aren't: `EVP_CIPHER_fetch` is a pure algorithm
*lookup*, with the actual encrypt/decrypt transformation happening in a
*separate*, later call (`EVP_EncryptUpdate`/`EVP_DecryptUpdate`) on a
*different* object (the `EVP_CIPHER_CTX`, not the fetched `EVP_CIPHER`).
The blind labeler (given no access to the detector or its output)
independently reached the same conclusion, explicitly excluding the fetch
calls: "obtains an algorithm handle/implementation lookup; performs no
cryptographic transformation itself."

Running the detector against this file (after committing the labels,
never before) confirmed the real damage: **precision 0.8889, below the
0.95 CI floor** -- two false positives, both at `EVP_CIPHER_fetch` call
sites, because the same cipher handle is fetched once for an encrypt
block and again for a decrypt block in that file, and the fetch heuristic
had no way to know which. Per root `CLAUDE.md`'s Track CC rules ("Any
rule that raises recall but drops precision below 0.95 is wrong -- fix
the rule's specificity or drop it, never ship it anyway"), this could not
ship as-is, dependency-ordered milestones or not.

## Decision

Replaced the standalone fetch/getter-fires-directly heuristic (for
*ciphers* specifically -- digests are unaffected, see below) with real
call-sequence linkage matching OpenSSL's actual EVP API contract:

1. `EVP_CIPHER_fetch(...)` no longer emits a detection itself. If
   assigned to a variable (`cipher = EVP_CIPHER_fetch(...)` or
   `EVP_CIPHER *cipher = EVP_CIPHER_fetch(...)`, both handled via
   `_assigned_c_variable_name`, mirroring Java's
   `_assigned_variable_name`), its (family, key_size, mode) is recorded
   against that variable name, pending consumption.
2. `EVP_{Encrypt,Decrypt}Init{_ex,_ex2}(ctx, cipher_arg, ...)` resolves
   `cipher_arg` -- either a nested zero-arg getter call
   (`EVP_aes_128_cbc()`, classified from the function name via
   `_lookup_cipher_getter`, no ambiguity since it's inline) or an
   identifier matching a pending fetched variable -- and binds the `ctx`
   variable to (family, key_size, mode, direction). Consuming a fetched
   variable this way marks it consumed (no double-fire from the fetch's
   own fallback, see below).
3. The transformation itself is reported at the real operation:
   `EVP_{Encrypt,Decrypt}Update(ctx, out, ...)` when `out` is not the
   literal `NULL` (a `NULL` output means the call is feeding Additional
   Authenticated Data, not transforming anything -- tree-sitter-c
   conveniently gives `NULL` its own `null` node type, no macro
   expansion needed to detect this). AEAD tag retrieval
   (`EVP_CIPHER_CTX_get_params`, encrypt side) and tag verification
   (`EVP_DecryptFinal_ex`, decrypt side) are separate findings on top of
   the primary operation, gated to `mode in {GCM, CCM}` so a plain CBC
   context calling these same APIs for an unrelated reason (e.g. IV
   retrieval) doesn't spuriously produce a tag/verify finding.
4. **Never silently drop a real usage just because its consuming call
   isn't visible in this file/snippet** -- same principle as Java's
   `KeyPairGenerator`/`initialize` linkage (ADR 004). A cipher-fetch
   variable never consumed by an Init call, or a ctx binding never
   consumed by an Update call, is still reported once at end-of-file (or
   when a new Init/fetch overwrites it while still unconsumed) as a
   fallback, direction defaulting to ENCRYPT for an unconsumed fetch
   (consistent with the existing Go/Java "construction implies usage"
   convention) or as whatever direction its Init call established for an
   unconsumed ctx binding.
5. Digest getters (`EVP_sha256()`, `EVP_md5()`, ...) are **unaffected** --
   split out into their own `_classify_openssl_digest_getter`, still
   self-firing directly. A digest has no encrypt/decrypt direction to
   get wrong, so the same ambiguity never applied to them.

A real bug was caught and fixed during this work, before it ever reached
a committed benchmark number: the first implementation attempt used the
*Init* call's stored `common` (path/line/snippet) when finally emitting
the Update-triggered detection, instead of the Update call's own --
`EVP_EncryptUpdate`-triggered detections were landing at the `Init`
call's line. Caught immediately by re-running the exact real-world file
by hand and comparing line numbers against the committed truth labels
before trusting the aggregate precision/recall numbers; fixed by passing
the current call's `common` through explicitly rather than reading it
back off the stored binding. Five new regression tests
(`tests/test_source_c.py`) lock in both the original precision bug and
this line-attribution bug: fetch-alone-is-not-an-operation,
fetch-used-for-decrypt-not-misclassified-as-encrypt, full GCM
encrypt+tag lifecycle, full GCM decrypt+verify lifecycle, and
non-AEAD-mode-gets-no-tag-or-verify.

## Consequences

- Real-world (HOLD) precision restored to 1.0 (was 0.8889, violating the
  0.95 floor) -- verified via `uv run python bench/real_world/evaluate.py`.
- Real-world recall *improved* as a side effect (0.52 -> 0.625): the old
  design never found the real `EVP_EncryptUpdate`/`get_params`/
  `EVP_DecryptFinal_ex` operations at all (only the wrong fetch-site
  proxy), so fixing precision also closed 4 real false negatives in the
  same file.
- Layer A (`bench/fixtures/`) stays 56/56, unchanged -- verified every
  existing OpenSSL fixture (`openssl_fetch.c`, `openssl_keygen.c`,
  `openssl_legacy_getters.c`, `openssl_cpp_wrapper.cpp`) still produces
  its expected detections at its expected lines under the new design,
  via the same end-of-file/rebind fallback mechanism that handles the
  real-world file's "fetch never consumed" and "Init never followed by
  Update" edge cases.
- mbedTLS and wolfSSL detection is completely untouched (different code
  paths, no shared ambiguity).
- Known remaining simplification, not exercised by any current fixture or
  HOLD sample: `ctx`/cipher-handle tracking is per-variable-name within a
  single file, not scope-aware (same limitation class as ADR 004's Java
  `KeyPairGenerator` linkage) -- a variable name reused across two
  unrelated functions with different algorithms could have the second
  binding overwrite the first before its own consuming call is seen,
  though the rebind-flush logic means the first would still be reported
  once (at its own Init/fetch site) rather than silently lost, so this is
  a potential *line-attribution* imprecision, not a silent miss.
