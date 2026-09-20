# bench/real_world/

A step toward Loop B1's DEV set: **real, unseen (never used to build or
tune the detector) third-party code**, not synthetic fixtures. Labelled by
reading the source *before* running the detector on it, per Loop B1's rule
("never inspect misses before labelling").

**This is still not the brief's full Loop B1 DEV/HOLD split** (that needs
>=150 labelled usages across 3 unseen projects, one Java, one Go, one C).
As of 2026-09-20 (M7, Track CC) this is **14 real files, 4 languages
(Python, Go, Java, C), 56 labelled usages** -- grown from a 32-usage/9-file
state by fetching 5 more real, unseen, permissively-licensed files (two
from golang.org/x/crypto, two from Django, one from Spring Security) and
blind-labelling them via a fresh `corpus-labeler` subagent per file (no
access to this repo's detector output). A sixth candidate (a permissively-
licensed project calling wolfSSL's C API) was searched for and not found
in the time available this session -- wolfSSL's own example repositories
are GPL-licensed like the library itself and not vendorable under the
licence gate; C stays represented by OpenSSL + mbedTLS only. Still well
short of the brief's 150-usage target, and honestly reported as such
rather than rounded up -- see "What's still missing" below.

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
| `okhttp_Util.java` | [square/okhttp `Util.java`](https://github.com/square/okhttp/blob/83090befcca69b44c257b96afb519ca66282ca63/okhttp/src/main/java/com/squareup/okhttp/Util.java) at a historical commit (last version with Java sources before the Kotlin rewrite), unmodified | Apache-2.0 |
| `jjwt_JcaTemplate.java` | [jwtk/jjwt `JcaTemplate.java`](https://github.com/jwtk/jjwt/blob/master/impl/src/main/java/io/jsonwebtoken/impl/security/JcaTemplate.java), unmodified. A real, heavily-used file with **zero** labelled usages (see gap #6 below) -- kept in the corpus deliberately, not swapped out, because that zero is itself the finding. | Apache-2.0 |
| `openssl_demo_aesgcm.c` | [openssl/openssl `demos/cipher/aesgcm.c`](https://github.com/openssl/openssl/blob/master/demos/cipher/aesgcm.c), unmodified | Apache-2.0 |
| `mbedtls_gen_key.c` | [Mbed-TLS/mbedtls `programs/pkey/gen_key.c`](https://github.com/Mbed-TLS/mbedtls/blob/master/programs/pkey/gen_key.c), unmodified | Apache-2.0 OR GPL-2.0-or-later (dual-licensed; treated as Apache-2.0) |
| `x_crypto_autocert.go` | [golang.org/x/crypto `acme/autocert/autocert.go`](https://cs.opensource.google/go/x/crypto/+/master:acme/autocert/autocert.go), unmodified. Automatic ACME/Let's Encrypt certificate manager. | BSD-3-Clause |
| `x_crypto_ssh_keys.go` | [golang.org/x/crypto `ssh/keys.go`](https://cs.opensource.google/go/x/crypto/+/master:ssh/keys.go), unmodified. SSH key wire-format parsing, signing, and verification -- the largest file in this corpus (1933 lines) and the source of two real detector gaps found this pass (see below). | BSD-3-Clause |
| `django_hashers.py` | [django/django `django/contrib/auth/hashers.py`](https://github.com/django/django/blob/main/django/contrib/auth/hashers.py), unmodified | BSD-3-Clause |
| `django_crypto.py` | [django/django `django/utils/crypto.py`](https://github.com/django/django/blob/main/django/utils/crypto.py), unmodified | BSD-3-Clause |
| `spring_security_Pbkdf2PasswordEncoder.java` | [spring-projects/spring-security `crypto/password/Pbkdf2PasswordEncoder.java`](https://github.com/spring-projects/spring-security/blob/main/crypto/src/main/java/org/springframework/security/crypto/password/Pbkdf2PasswordEncoder.java), unmodified. Labels to **zero** confidently-determinable usages (see gap #8 below) -- kept deliberately, same rationale as `jjwt_JcaTemplate.java`. | Apache-2.0 |

All licences here are on the licence gate's "OK to vendor" list
(`backend/CLAUDE.md`). **Note for whoever adds more files**: paramiko
(a natural next candidate -- SSH library, heavy RSA/Ed25519/ECDSA key
handling) was fetched and read during an earlier session's labelling
pass, but **discarded and never committed** -- it's LGPL-2.1, which the
licence gate only allows as an unmodified *dependency*, never vendored
into this repo as a copied file. (A later Track CC mandate reversed this
as "over-cautious" and said paramiko is usable via fetch-to-/tmp-only,
never committed -- not yet acted on.)

## Result (2026-09-20, M7 Track CC, 14 files / 56 usages / 4 languages)

```
$ uv run python bench/real_world/evaluate.py
precision=0.9583 recall=0.8214 f1=0.8846
truth=56 detected=48 tp=46
```

**46/56 true positives, 2 false positives, 10 false negatives.** Growing
the corpus from 32 to 56 usages this pass found two Go capability gaps
(closed before running the detector on the motivating files, per the
"extend for a real newly-found pattern before you label it" rule -- see
`docs/decisions/backend/019-m7-corpus-growth-and-aes-attribution.md`) and
three genuinely new false-negative gaps (below), plus more instances of
one already-known gap category. Precision dropped from 1.0 to 0.9583 --
**still above the 0.95 floor** (confirmed via
`bench/check_precision_floor.py`, PASS on both corpora) but closer to it
than at any point before. The 2 false positives are not classification
errors -- see gap #8 below for the real (and narrow) cause, a
label-attribution convention question rather than a detector defect. Per
"never tune on HOLD," neither the labels nor the detector were touched
after this run to make the number look better; it is recorded exactly as
measured.

Every remaining false negative is one of the gaps documented below -- see
`docs/engineering/backend/PROGRESS.md`'s dated entries for the full false-negative list.
This number is a floor (`tests/test_bench_real_world.py`), not a target
-- don't chase it back up by weakening the corpus or the labels; closing
the gaps below for real is what would honestly move it.

## What this did *not* find (real gaps, noted honestly, not silently fixed)

1. **Bare attribute/function references** -- fixed in both languages as
   of M6. `hashFunc: sha256.New,` and `s.BlockFunc(aes.NewCipher)` in
   `gorilla_securecookie.go` (139, 148) pass a function *value* without
   calling it; Go's query previously only matched direct call nodes, so
   this registry-style pattern was a false negative there. Fixed in M6
   (ADR 018) by porting the same `attr.node`-style capture Python
   already had (`source_python.py`, landed in an earlier session for
   `pyjwt_algorithms.py`'s `SHA256: ClassVar[HashlibHash] = hashlib.sha256`,
   lines 320-322 -- this file previously, incorrectly, claimed that
   pattern was still undetected in Python too; corrected per the
   project's "re-derive, don't quote" bookkeeping rule when this gap was
   revisited). Both languages now share the same mechanism.
2. **Intra-file type inference for `key.sign(...)`/`key.verify(...)`
   in `pyjwt_algorithms.py` is now mostly resolved** (M4, ADR 016): 6 of
   8 occurrences (RSA/ECDSA/Ed25519 sign, RSA verify x2) are detected by
   reading `key`'s type straight off the enclosing function's own
   parameter annotation (a real static fact, not inference in the
   dataflow sense). The 2 that remain unresolved, deliberately: line 777
   (`ECAlgorithm.verify`) types `key` as `AllowedECKeys`, a pyjwt-internal
   type alias the detector doesn't chase (would mean reading pyjwt's own
   source to learn a project-specific name, i.e. tuning on this exact
   HOLD file); line 1018 (`OKPAlgorithm.verify`) calls `.verify()` on a
   *local variable* (`public_key = key.public_key() if ... else key`),
   not a typed parameter, which needs real local dataflow tracking inside
   the function body -- a materially bigger feature, not attempted.
   Same root cause still applies to Go's `cipher.NewCTR(block, iv)`
   (`gorilla_securecookie.go`:402,420), which takes a generic
   `cipher.Block` interface with the concrete constructor
   (`aes.NewCipher`, via `BlockFunc`) several calls removed -- not
   addressed by the Python-specific type-annotation mechanism above,
   still open in Go. M7 added three more instances of the exact same
   category in `x_crypto_ssh_keys.go` (`ctr.XORKeyStream`:1516,
   `cbc.CryptBlocks`:1522, `stream.XORKeyStream`:1567) -- the concrete
   cipher (`aes.NewCipher`) is constructed several lines earlier and
   passed through a generic `cipher.Stream`/`cipher.BlockMode`-typed
   variable, same shape as `gorilla_securecookie.go`'s gap. Not a new gap
   type, just more real-world evidence it's worth fixing -- 5 known
   instances across 2 files now.
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
6. **Cross-file dataflow through a dispatcher class** -- `jjwt_JcaTemplate.java`
   is a real, heavily-used JCA wrapper: every `Cipher.getInstance(jcaName)`/
   `KeyPairGenerator.getInstance(jcaName)`/etc. call inside it uses a
   `jcaName` **variable**, supplied by a caller in a *different* file
   (e.g. `Jwts.SIG.HS256`-style algorithm constants live elsewhere in
   jjwt), never a literal algorithm string. Our Java detector only parses
   literal transformation strings (ADR 013) -- by design, since guessing
   a family from a variable name would be exactly the kind of unfounded
   inference the precision floor exists to prevent. This file
   legitimately labels to **zero** usages (confirmed by the blind
   labeler, not a labelling shortfall) and stays in the corpus as a
   documented example of a structural pattern (indirection through a
   generic engine-dispatcher class) no single-file static detector can
   resolve without real cross-file/interprocedural dataflow analysis --
   a materially bigger feature than anything else in this engine, not
   attempted.
7. **Family-ambiguous EC key generation** -- `mbedtls_gen_key.c` calls
   `mbedtls_ecp_gen_key((mbedtls_ecp_group_id) opt.ec_curve, ...)` with
   the generic `MBEDTLS_PK_ECKEY` type (not the ECDH-restricted
   `MBEDTLS_PK_ECKEY_DH` variant) and no downstream `mbedtls_ecdsa_*`/
   `mbedtls_ecdh_*` call to disambiguate -- the blind labeler correctly
   declined to guess ECDSA vs ECDH and excluded it, so this is not even a
   detector gap in the usual sense (there's no unambiguous ground truth
   to detect); noted here so it isn't mistaken for one later. Also: this
   engine doesn't implement `mbedtls_ecp_gen_key` at all yet (only
   `mbedtls_ecdsa_genkey`) -- a real, separate gap, but one this
   particular call site can't be used to measure either way.

8. **Two "false positives" that are a label-attribution question, not a
   detector defect.** `x_crypto_ssh_keys.go`:1509,1561 are real
   `aes.NewCipher(key)` calls -- the detector correctly finds them,
   exactly as it already does for `gorilla_securecookie.go`:148's
   `s.BlockFunc(aes.NewCipher)` bare reference (both are labelled AES/
   encrypt there). The blind labeler for `x_crypto_ssh_keys.go`
   deliberately chose, before any detector run, to attribute the AES
   usage to the downstream `XORKeyStream`/`CryptBlocks` call instead
   (see gap #2's three new entries) reasoning that "the encrypt/decrypt
   semantics live there," not at the constructor -- a defensible
   labelling call, but inconsistent with this corpus's own established
   convention of attributing Go block-cipher usage to the `aes.NewCipher`
   call/reference itself. Per "never tune on HOLD," the labels were
   **not** retroactively edited to add the constructor lines once this
   was discovered by running the detector -- that would be exactly the
   inspect-the-miss-then-relabel pattern the rule exists to prevent.
   Recorded here as a real methodology finding for the next corpus pass:
   **the convention for future files should state explicitly that
   `aes.NewCipher`/equivalent constructor calls are the canonical
   attribution point**, and label accordingly *before* running the
   detector, so this doesn't recur. See ADR 019.
9. **Python has no PBKDF2 API surface coverage at all.** `django_crypto.py`:93
   (`hashlib.pbkdf2_hmac(...)`) and `django_hashers.py`:333 (Django's own
   `pbkdf2()` wrapper, which itself calls `hashlib.pbkdf2_hmac`) are both
   real HMAC-based key-derivation calls with no detection rule at all --
   unlike Java, which gained `SecretKeyFactory`/PBKDF2 coverage this same
   session (see ADR 019). Found by reading source during this session's
   candidate-sourcing phase, *before* these two files were labelled or
   scored, so extending the Python detector for it now would have been
   legitimate "extend before you label" -- not done this pass because it
   was noticed only while assembling this report, after the one
   permitted detector run had already happened; left as an honest,
   documented gap for the next pass rather than fixed reactively.
10. **Attribute-based hash resolution.** `django_hashers.py`:514
    (`self.digest(password).digest()`) calls a hash function bound to an
    instance attribute (itself set via a bare `hashlib.sha256`/`sha256`
    class-attribute reference elsewhere in the same class, e.g. line 498)
    -- resolving it needs attribute-to-class-body dataflow, a different
    (and more general) mechanism than the existing parameter-type-
    annotation resolution used for `key.sign()`/`key.verify()` (ADR 016).
    Not attempted; the class-attribute *declaration* itself (line 498)
    is separately detected as a bare reference, so this is specifically
    about the later *call site* that reads it back through `self`.

Per Loop B1's cap-of-6-iterations process, the next iteration (not done
this pass -- explicitly deferred) would pick gap #1 (the largest, cheapest
cluster, and now confirmed to affect both Python and Go) and implement a
query + test for both languages.

## What's still missing to meet the brief's actual target

- **>=150 usages, not 56.** Growing this further means repeating this
  same process (find a real, unseen, permissively-licensed file with
  genuine crypto usage -- not a library's own class/algorithm
  *definitions*, which don't contain "usages" in the sense these queries
  detect -- read and label it before running the detector, commit the
  label, then run) across more real files, in all 4 languages. This
  session (and the ones before it) prioritized correctness of the
  methodology (real files, real licences, labelled blind, precision
  floor enforced even when it meant a mid-session detector redesign) over
  hitting a number. M7 grew usages 75% (32->56) but is still well short
  of 150; a wolfSSL-API C candidate was searched for and not found this
  pass (see the provenance note above) -- C stays at 2 files.
- **Java, Go, and C are all still thin.** Java has 3 files (`okhttp_Util.java`,
  `jjwt_JcaTemplate.java`, `spring_security_Pbkdf2PasswordEncoder.java`),
  Go has 4 (`go_crypto_sample.go`, `gorilla_securecookie.go`, plus the two
  new x/crypto files), C has 2 (unchanged this pass, see above). Python is
  the best-represented language now at 5 files (`itsdangerous_signer.py`,
  `cryptography_rsa_recipe.py`, `pyjwt_algorithms.py`, plus the two new
  Django files). Two-to-five files per language demonstrates the detector
  *works* on real code across a wider idiom space than before, not that
  it's well-measured against any one language's full API surface.
- **A genuine train/tune-blind HOLD split** (a DEV set the detector may
  be iterated against, and a separate HOLD set touched only once, at the
  end) doesn't exist yet -- every file here has only ever been run once
  against the detector (label first, run once, record honestly -- even
  when that one run found a real bug requiring a fix and a second,
  still-single, re-run), which is the right practice so far, but there's
  no formal DEV/HOLD partition documented as such.
