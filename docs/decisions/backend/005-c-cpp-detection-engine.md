# 005 — C/C++ crypto detection engine (M2, Track CC)

## Status

Accepted

## Context

Before this pass, `engine/` had zero *source-level* C/C++ detection --
only a binary AES S-box constant check (`engine/scanner.py::_detect_binary`)
existed for C-family code, and it had no regression test at all despite
being live since Phase 7. M2's brief asks for OpenSSL 3.x, mbedTLS, and
wolfSSL source detection, plus confirmation the binary path still works.

## Decision

- Confirmed `tree-sitter-c==0.24.2` resolves via `uv add` and is MIT
  (same author/licence family as the existing grammars). Initially also
  added `tree-sitter-cpp`, then removed it: OpenSSL/mbedTLS/wolfSSL are
  all free-function C APIs with identical call-expression shape whether
  the surrounding file is `.c` or `.cpp` -- a real test
  (`test_cpp_class_wrapper_still_parses_calls`) confirmed the plain C
  grammar locally recovers around C++-only syntax (`class`, access
  specifiers) it doesn't understand and still finds the call inside. A
  second, C++-specific grammar would only pay for itself once patterns
  that need real C++ parsing (templates, namespaced calls, overloads)
  are added -- not yet the case, so not vendored to avoid dependency
  bloat with no behavioral benefit.
- New `engine/source_c.py` + `engine/queries/c_crypto.scm`, same "capture
  broad AST shape, classify in Python" split as the other three
  detectors. Since all three target libraries are free functions (no
  method-call syntax, unlike Java's JCA), a single bare `name(args)`
  query pattern covers everything; dispatch is a `dict[str, handler]`
  keyed by exact function name, not per-class heuristics.
- **OpenSSL**: `EVP_CIPHER_fetch`/`EVP_MD_fetch` (3.x, algorithm-name-
  string parsing, e.g. `"AES-256-GCM"` -> family/key_size/mode via
  regex), `EVP_PKEY_CTX_set_rsa_keygen_bits`/`_set_ec_paramgen_curve_nid`
  (keygen params, each self-contained in one call -- no cross-call
  linkage needed here, unlike Java's `KeyPairGenerator`). Also covers the
  pre-3.0 zero-arg algorithm getters (`EVP_aes_256_gcm()`, `EVP_sha256()`,
  ...) classified from the function name alone via regex -- a deliberate
  scope decision beyond the brief's literal "modern EVP_*_fetch API"
  wording: real-world OpenSSL C code still overwhelmingly uses the
  getter+`EVP_EncryptInit_ex` pattern, not `*_fetch` (a 3.0+-only API),
  so excluding it would sacrifice most real recall for the sake of
  matching the brief's phrasing exactly. Recorded as a scope decision,
  not a silent deviation.
- **mbedTLS**: `mbedtls_aes_setkey_enc/dec`, `mbedtls_des_setkey_enc/dec`,
  `mbedtls_des3_set{2,3}key_enc/dec`, `mbedtls_{sha256,sha1,md5}_starts[_ret]`,
  `mbedtls_rsa_gen_key`, `mbedtls_ecdsa_genkey`, `mbedtls_gcm_setkey`
  (only when its cipher-id argument's text contains `"AES"`, since the
  function is generic over the underlying block cipher and guessing
  wrong would be a false positive).
- **wolfSSL**: `wc_AesSetKey`, `wc_Des3_SetKey`, `wc_MakeRsaKey`,
  `wc_ecc_make_key`, `wc_Sha256Hash`/`wc_ShaHash`/`wc_Md5Hash`,
  `wc_HmacSetKey`. wolfSSL's `wc_AesSetKey`/`wc_ecc_make_key` pass key
  size in **bytes** (`len`/`keysize` params), unlike OpenSSL/mbedTLS which
  use bits directly -- both handlers multiply by 8 before setting
  `Detection.key_size`, so the field means the same thing (bits)
  regardless of which library a finding came from. Covered by
  `test_wolfssl_aes_setkey_byte_to_bit_conversion`.
- Real bug caught by direct testing before fixtures were written: the
  wolfSSL HMAC underlying-hash lookup did substring matching against
  `_DIGEST_NAME_FAMILY` in dict insertion order, so `WC_SHA256` matched
  the generic `"SHA"` key (itself a substring of `"SHA256"`) before ever
  reaching `"SHA256"`, misclassifying every SHA-2/SHA-3 HMAC as SHA-1.
  Fixed by matching against digest names longest-first
  (`_DIGEST_NAMES_BY_LENGTH_DESC`). Regression test:
  `test_wolfssl_hmac_underlying_hash_not_confused_by_substring`.
- `engine/scanner.py`: `_C_FAMILY_EXTENSIONS = {.c, .h, .cpp, .cc, .cxx,
  .hpp, .hxx}` wired into the per-file dispatch, after the `.java` branch
  and before the binary branch -- order matters only in that it must not
  shadow the existing `.bin`/`.elf`/`.so` branch, confirmed by a new
  `test_scan_binary_constant_detection_still_works_alongside_source_detectors`
  (no prior test covered the binary path at all, despite it being live
  since Phase 7 -- gap closed here, not just guarded against regression).
- 7 new crypto fixture files + 1 true-negative file (16 labelled usages)
  under `bench/fixtures/`, including one `.cpp` file specifically to
  prove the C-grammar-on-C++-file decision above. 13 new focused unit
  tests in `tests/test_source_c.py`.

## Consequences

- Layer A (`bench/evaluate.py`) stays precision 1.0 / recall 1.0, now
  56/56 true positives (was 40/40 after M1) -- verified via
  `uv run python bench/evaluate.py`.
- `bench/real_world/` (HOLD corpus) unaffected -- no C/C++ files exist
  there yet; that's M3.
- Known gap, left honest: `mbedtls_des_setkey_enc/dec` has no `key_size`
  extraction (the mbedTLS DES API takes a fixed 8-byte key with no
  explicit size parameter) -- `key_size` stays `None` for these, which is
  correct (nothing to extract), not a bug.
