# ECDAT Backend — Progress

## 2026-09-20 — Track CC M5 complete: real blocked PR on GitHub's actual infrastructure

Finished what the previous entry left open. First, opened a real PR
(#8, https://github.com/nani224/SIH26164/pull/8) for all of this
session's M0-M5 work, since none of it had ever run on GitHub's actual
Actions infrastructure before -- only local `uv run` commands. Real
result: `backend-ci` `success`, including the new precision-floor step,
on GitHub's own runner. Merged.

Then the demo repo: repository creation via the GitHub App integration
is 403-blocked (`Resource not accessible by integration`) -- confirmed
this is a GitHub App architecture limit, not a missing permission, by
retrying after the user checked the app's installation permissions page
(no "Administration" scope offered at all). The user redirected this to
a same-repo demo instead: `demo/vulnerable-app/` +
`.github/workflows/demo-vulnerable-check.yml`, calling the exact same
`ecdat-scan-reusable.yml` an external repo would call (just via a local
path reference instead of the cross-repo `nani224/SIH26164/...@main`
form, since this workflow lives in the repo it demonstrates).

Opened PR #9 (https://github.com/nani224/SIH26164/pull/9), introducing
`demo/vulnerable-app/legacy_auth.py` -- a 1024-bit RSA keygen. **First
run: `startup_failure`** -- `"The nested job 'scan' is requesting
'pull-requests: write', but is only allowed 'pull-requests: none'"`. A
real bug, caught only by actually running this on GitHub's
infrastructure (no local equivalent exists for a composite-Action
permission-propagation failure): the calling workflow didn't declare
`permissions:`, defaulting to read-only. Fixed
(`permissions: {contents: read, pull-requests: write}` on the calling
job), pushed, re-ran. Real result:

```
## ECDAT scan: 2 finding(s), worst band critical
| critical | 90.0 | RSA | keygen | legacy_auth.py:14 | ML-KEM-768 |
| low | 12.2 | RSA | sign | legacy_auth.py:21 | ML-DSA-65 |
BLOCKED: 1 finding(s) at or above the gate band (critical).
##[error]Process completed with exit code 1.
Posted findings comment to nani224/SIH26164#9.
```

Check `ecdat-demo / scan`: **failure**. PR #9's `mergeable_state`:
**unstable**. A real findings-table comment posted by `github-actions[bot]`
via `GITHUB_TOKEN`: https://github.com/nani224/SIH26164/pull/9#issuecomment-5746916900.
PR #9 left open (not merged) as the demonstration artifact -- it's
deliberately vulnerable and isn't meant to land.

Ported the same one-line permissions fix to `main` via a small separate
branch (`fix/demo-check-permissions`) so the demo infrastructure is
correct there too, not just on the demo PR's own branch.

Full writeup, including the exact reasoning for why a same-repo demo
replaced the originally-planned separate external repo, in
`docs/decisions/backend/017-ci-cd-precision-gate-and-reusable-action.md`.

Track CC v0.3 mandate (M0-M5) is now complete.

## 2026-09-19 — Track CC M5 (in progress): CI/CD precision gate + reusable Action

Built the in-repo, fully-verifiable half of M5:

- `backend/bench/check_precision_floor.py`: runs both `bench/evaluate.py`
  and `bench/real_world/evaluate.py`, fails if either's precision drops
  below 0.95. Wired into `.github/workflows/backend-ci.yml` as a real CI
  step -- the 0.95 floor this session enforced by hand all along (and
  which caught a real violation in M3) is now something a green CI run
  actually proves, not something to re-derive from a PROGRESS.md entry.
- `.ecdat-policy.yml` (repo root): policy-as-code -- the existing
  risk-formula `Policy` shape plus a `gate:` section (`failOnBand`,
  `precisionFloor`) for CI-specific rules.
- `backend/bench/ci_scan.py`: loads the policy, runs
  `engine.scanner.scan()` against a target path, writes JSON + Markdown
  findings output, exits non-zero if any finding is at or above the gate
  band. Verified end-to-end against a hand-built
  `rsa.generate_private_key(key_size=1024)` sample:

  ```
  $ uv run python bench/ci_scan.py --path <sample dir> --policy ../.ecdat-policy.yml ...
  ## ECDAT scan: 2 finding(s), worst band critical
  | critical | 90.0 | RSA | keygen | vulnerable_app.py:5 | ML-KEM-768 |
  | medium | 18.0 | MD5 | digest | vulnerable_app.py:8 | SHA-2-256 |
  BLOCKED: 1 finding(s) at or above the gate band (critical).
  $ echo $?
  1
  ```

- `backend/bench/post_pr_comment.py`: posts/updates a PR comment via raw
  `urllib.request` calls to the GitHub REST API using `GITHUB_TOKEN` --
  no third-party comment action, per the brief. Idempotent (edits its
  own previous comment via a hidden marker).
- `.github/actions/ecdat-scan/action.yml` (composite Action) +
  `.github/workflows/ecdat-scan-reusable.yml` (`workflow_call` wrapper)
  -- a consuming repo needs one `uses:` line to get a real scan + PR
  comment + gate.
- 11 new unit tests (`test_check_precision_floor.py`, `test_ci_scan.py`,
  `test_post_pr_comment.py`), PR-comment tests use a monkeypatched
  `_api_request` -- no real network calls from the test suite.

```
$ uv run ruff check .
All checks passed!
$ uv run mypy --strict .
Success: no issues found in 74 source files
$ uv run pytest --cov=api --cov=engine --cov=scripts --cov-report=term-missing --cov-fail-under=85 -q
166 passed, 4 warnings in 16.20s
Required test coverage of 85% reached. Total coverage: 87.72%
```

**Not done yet, and not silently skipped**: the brief's "create a
deliberately-vulnerable demo repo and open a REAL PR that gets REALLY
BLOCKED" step needs a new external GitHub repository and a real PR under
the user's identity -- a visible, hard-to-reverse action outside this
session's current repo scope (`nani224/SIH26164` only). Flagged to the
user rather than done unilaterally. Full design + exact remaining steps
once authorized in
`docs/decisions/backend/017-ci-cd-precision-gate-and-reusable-action.md`.
Also unverified: the composite Action's cross-repo checkout step has
only been YAML-syntax-validated, not run on GitHub's actual infrastructure.

## 2026-09-19 — Track CC M4: close the largest false-negative cluster

M3 left 12 real-world false negatives. Clustered by root cause: 8 in
`pyjwt_algorithms.py` (`key.sign(...)`/`key.verify(...)` where `key`'s
concrete type isn't known from the call site), 4 in
`gorilla_securecookie.go` (bare function-value references + a generic
`cipher.Block` interface parameter). The pyjwt cluster is the largest
(8/12) -- picked as M4's target per the mandate.

The obvious fix (track `key = rsa.generate_private_key(...)`-style local
assignments, mirroring the Java/C linkage patterns from M1/M3) doesn't
apply: `key` in every one of PyJWT's `sign`/`verify` methods is a
**function parameter**, not a local variable with a constructor call to
link back to. Real fix: Python parameters can carry type annotations, and
PyJWT's real code does (`key: RSAPrivateKey`, `key: EllipticCurvePrivateKey`,
`key: Ed25519PrivateKey | Ed448PrivateKey`, ...) -- a genuine static fact,
not a guess. `engine/source_python.py` now resolves `X.sign(...)`/
`X.verify(...)` by walking up to the enclosing `function_definition`,
finding `X`'s `typed_parameter`, and matching its type annotation text
against real `cryptography`-library class names (`"RSA"`, `"EllipticCurve"`,
`"Ed25519"` substrings). No match -> no detection; never guesses. Full
design + the two cases deliberately left unresolved (a project-specific
type alias, and a call on a local variable rather than a parameter) in
`docs/decisions/backend/016-python-key-method-type-annotation.md`.

```
$ uv run python bench/real_world/evaluate.py
precision=1.0 recall=0.8125 f1=0.8966
truth=32 detected=26 tp=26
```

Recall 0.625 -> 0.8125 (6 new true positives: RSA sign/verify x2, ECDSA
sign, Ed25519 sign), **zero new false positives** -- precision stays 1.0.
Layer A unaffected (56/56, no existing fixture exercises this pattern);
5 new unit tests added instead (positive cases per family, a deliberate-
non-match case for the unresolved type alias, an unrelated-`.sign()`-call
negative case proving the "no guessing" property directly).

```
$ uv run ruff check .
All checks passed!
$ uv run mypy --strict .
Success: no issues found in 68 source files
$ uv run pytest --cov -q
155 passed, 4 warnings in 17.18s   (was 152 after M3; +5 new Python tests,
                                     +1 real-world floor update)
TOTAL coverage 93%
$ uv run python scripts/contract_diff.py
No contract drift.
$ uv run python bench/evaluate.py   (Layer A, unaffected)
precision=1.0 recall=1.0 f1=1.0
truth=56 detected=56 tp=56
```

While updating `bench/real_world/README.md` to reflect this, also caught
and corrected a stale claim left over from an earlier session: gap #1
said Python's bare `hashlib.sha256` attribute-reference pattern (lines
320-322 of `pyjwt_algorithms.py`) was undetected -- it's actually already
correctly detected (a `source_python.py` capture that landed in an
earlier session without this file being updated to match, the exact
"known bookkeeping hazard" root `CLAUDE.md` warns about). Corrected
rather than left to compound; the Go equivalent of that same pattern
(`hashFunc: sha256.New,`) is confirmed still a real, open gap.

Not started this session: M5 (CI/CD + real blocked PR). Two of the
original 8 pyjwt false negatives remain, honestly unresolved (not
hardcoded around): a project-specific type alias, and a `.verify()` call
on a local variable rather than a typed parameter. The Go
bare-function-value-reference and generic-interface-parameter gaps (4
FNs) are untouched -- next candidate cluster for a future M4-style pass,
not attempted this session (time/scope).

## 2026-09-19 — Track CC M3: HOLD corpus growth + real precision-floor catch/fix

Grew `bench/real_world/` from 5 files/25 usages/2 languages (Python, Go)
to 9 files/32 usages/4 languages (+ Java, + C), following strict Loop B1
order every step: fetch real Apache-2.0 files (jjwt's `JcaTemplate.java`,
OkHttp's `Util.java`, OpenSSL's own `demos/cipher/aesgcm.c`, mbedTLS's own
`programs/pkey/gen_key.c`) -> commit raw files alone (`cf6d7bd`) -> dispatch
one fresh `corpus-labeler` subagent per file (Read/Grep/Glob only, zero
access to this repo's detector output) -> commit labels alone, before ever
running the detector against them (`0129fc6`) -> run
`bench/real_world/evaluate.py` exactly once.

That first real run found: **precision 0.8889, recall 0.5, truth=32,
detected=18, tp=16** -- below the 0.95 CI floor. Root cause: OpenSSL's
`EVP_CIPHER_fetch` was firing as ENCRYPT unconditionally (an M2 design
choice), but the real file fetches the same algorithm once for an encrypt
block and again for a decrypt block, and a fetch alone doesn't perform
any operation anyway -- the blind labeler independently reached the exact
same conclusion, excluding both fetch calls from its labels before this
run ever happened.

Per root `CLAUDE.md`'s non-negotiable rule ("Any rule that raises recall
but drops precision below 0.95 is wrong -- fix the rule's specificity or
drop it, never ship it anyway"), fixed same-session rather than deferred
to M4: redesigned `engine/source_c.py`'s OpenSSL cipher handling to track
real call-sequence linkage (`EVP_CIPHER_fetch` -> `EVP_{Encrypt,Decrypt}Init{_ex,_ex2}`
-> `EVP_{Encrypt,Decrypt}Update` / `EVP_CIPHER_CTX_get_params` /
`EVP_DecryptFinal_ex`), reporting the operation at the real transformation
call, not the algorithm-lookup call. Full design + a real line-attribution
bug caught and fixed during implementation (Update-triggered detections
were landing at the Init call's line, not the Update's) in
`docs/decisions/backend/015-openssl-evp-cipher-context-linkage.md`.

Re-measured after the fix:

```
$ uv run python bench/real_world/evaluate.py
precision=1.0 recall=0.625 f1=0.7692
truth=32 detected=20 tp=20
```

Precision restored to 1.0 (above floor); recall *improved* as a side
effect, 0.52 -> 0.625 -- the buggy fetch-site heuristic was never finding
the real operations either, so fixing precision also closed 4 real false
negatives in the same file. 5 new regression tests added
(`tests/test_source_c.py`) locking in both the original bug and the
line-attribution bug found while fixing it.

```
$ uv run ruff check .
All checks passed!
$ uv run mypy --strict .
Success: no issues found in 68 source files
$ uv run pytest --cov -q
152 passed, 4 warnings in 17.02s   (was 147 after M2; +5 new C regression
                                     tests, +1 real-world floor update)
TOTAL coverage 93%
$ uv run python scripts/contract_diff.py
No contract drift.
$ uv run python bench/evaluate.py   (Layer A, unaffected by this fix)
precision=1.0 recall=1.0 f1=1.0
truth=56 detected=56 tp=56
```

Two real, honest gaps found and documented (not silently papered over):
`jjwt_JcaTemplate.java` labels to zero usages -- every `getInstance` call
in it takes a caller-supplied variable, not a literal algorithm string,
which needs real cross-file dataflow to resolve and is out of scope;
`mbedtls_gen_key.c`'s EC keygen call was correctly left unlabelled by the
blind labeler as family-ambiguous (generic `MBEDTLS_PK_ECKEY`, no
downstream ECDSA/ECDH-specific call to disambiguate) -- not even a
detector gap, since there's no unambiguous ground truth there to detect.
Full writeup in `bench/real_world/README.md`.

Not started this session: M4 (cluster false negatives across all 4
languages, fix the largest, re-measure), M5 (CI/CD + real blocked PR).
Corpus is still far short of the 150-usage/4-language target (32 usages,
1-2 files per new language) -- honestly reported, not rounded up.

## 2026-09-19 — Track CC M2: C/C++ detection engine

New `engine/source_c.py` (`tree-sitter-c==0.24.2`, MIT, confirmed pinnable
before writing rules; `tree-sitter-cpp` was also test-installed then
removed -- a real test proved the plain C grammar already parses the
plain-function-call patterns these libraries use even inside a `.cpp`
file with `class`/access-specifier syntax it doesn't understand, so a
second grammar bought nothing). Covers OpenSSL 3.x `EVP_CIPHER_fetch`/
`EVP_MD_fetch` (algorithm-string parsing) + `EVP_PKEY_CTX_set_rsa_keygen_bits`/
`_set_ec_paramgen_curve_nid`, the pre-3.0 zero-arg algorithm getters
(`EVP_aes_256_gcm()`, `EVP_sha256()`, ...) -- a deliberate scope expansion
beyond the brief's literal wording since real C code still mostly uses
these, not `*_fetch` -- mbedTLS (`mbedtls_aes_setkey_enc/dec`,
`mbedtls_{sha256,sha1,md5}_starts`, `mbedtls_rsa_gen_key`,
`mbedtls_ecdsa_genkey`, `mbedtls_gcm_setkey`), and wolfSSL
(`wc_AesSetKey`, `wc_Des3_SetKey`, `wc_MakeRsaKey`, `wc_ecc_make_key`,
`wc_{Sha256,Sha,Md5}Hash`, `wc_HmacSetKey`). See
`docs/decisions/backend/014-c-cpp-detection-engine.md` for the exact
mapping and two things caught during development, not after:

1. wolfSSL's `wc_AesSetKey`/`wc_ecc_make_key` pass key size in **bytes**,
   unlike OpenSSL/mbedTLS's bits -- handled with an explicit x8
   conversion so `Detection.key_size` means the same thing everywhere.
2. A real substring-matching bug in the HMAC underlying-hash lookup
   (`WC_SHA256` was matching the generic `"SHA"` key before reaching
   `"SHA256"`, misclassifying every SHA-2/3 HMAC as SHA-1) -- caught by
   direct manual testing *before* fixtures were written, fixed by
   matching digest names longest-first, and locked down with a named
   regression test (`test_wolfssl_hmac_underlying_hash_not_confused_by_substring`).

Also closed a real pre-existing gap unrelated to this milestone's own
code: the binary AES S-box constant detector
(`engine/scanner.py::_detect_binary`, live since Phase 7) had **zero**
test coverage anywhere in the suite. Added
`test_scan_binary_constant_detection_still_works_alongside_source_detectors`
-- both to satisfy M2's explicit "binary detection still works" exit
criterion and to close a real coverage hole that had nothing to do with
C/C++.

7 new crypto fixture files + 1 true-negative file under `bench/fixtures/`
(16 labelled usages, incl. one `.cpp` file), 13 new unit tests in
`tests/test_source_c.py`. Real command output:

```
$ uv run python bench/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=56 detected=56 tp=56
```
(grew from 40 to 56 usages; still 1.0/1.0)

```
$ uv run ruff check .
All checks passed!
$ uv run mypy --strict .
Success: no issues found in 68 source files
$ uv run pytest --cov -q
147 passed, 4 warnings in 16.99s   (was 131 after M1; +13 test_source_c.py,
                                     +3 scanner integration tests incl. the
                                     binary-detection regression test,
                                     +1 floor-count bump)
TOTAL coverage 93%
$ uv run python scripts/contract_diff.py
No contract drift.
$ uv run python bench/real_world/evaluate.py
(unchanged: precision=1.0 recall=0.52 truth=25 detected=13 -- the C/C++
detector doesn't touch the Python/Go real-world corpus, as expected)
```

Not started this session: M3 (HOLD corpus growth to ~150 usages/4
languages), M4 (largest false-negative cluster), M5 (CI/CD + real blocked
PR). Known gap recorded rather than silently shipped: `mbedtls_gcm_setkey`
only fires when its cipher-id argument's text contains `"AES"` (the
function is generic over the underlying block cipher, and guessing wrong
would be a false positive) -- a non-AES GCM usage via this function is a
deliberate miss, not a bug.

## 2026-09-19 — Track CC M1: Java detection engine

New `engine/source_java.py` (`tree-sitter-java==0.23.5`, MIT, confirmed
pinnable via `uv add` before writing any code). Covers JCA/JCE `Cipher`
(transformation-string parsing: algo/mode/padding), `KeyPairGenerator`/
`KeyGenerator` (linked to a later `.initialize()`/`.init()` call on the
same variable for key size/curve -- real intra-method dataflow, see
`docs/decisions/backend/013-java-detection-engine.md` for the exact
mechanism and its documented limitation), `MessageDigest`, `Signature`
(`"SHA256withRSA"` parsing), `KeyAgreement`, `Mac` (`"HmacSHA256"`
parsing), `SSLContext`, `KeyStore`, `SecretKeySpec`, plus direct
BouncyCastle lightweight-API class usage (`new SHA256Digest()`, `new
AESEngine()`, `new RSAKeyPairGenerator()`, `new
Ed25519KeyPairGenerator()`). `engine/scanner.py` wired `.java` into the
per-file dispatch alongside `.py`/`.go`.

9 new fixture files (`bench/fixtures/Java*.java`, incl. one true-negative
file with `StringBuilder`/`ArrayList`/`Logger`), 25 new `truth.json`
entries. Real command output:

```
$ uv run python bench/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=40 detected=40 tp=40
```
(grew from 15 to 40 usages; still 1.0/1.0)

```
$ uv run ruff check .
All checks passed!
$ uv run mypy --strict .
Success: no issues found in 66 source files
$ uv run pytest --cov -q
131 passed, 4 warnings in 16.10s   (was 118 before this session's start;
                                     +12 test_source_java.py, +1 scanner
                                     integration test, +1 floor-count bump)
TOTAL coverage 94%
$ uv run python scripts/contract_diff.py
No contract drift.
$ uv run python bench/real_world/evaluate.py
(unchanged: precision=1.0 recall=0.52 truth=25 detected=13 -- Java
detector doesn't touch the Python/Go real-world corpus, as expected;
growing that corpus to include Java is M3, not this milestone)
```

Not started this session: M2 (C/C++ hardening), M3 (HOLD corpus growth),
M4 (largest false-negative cluster), M5 (CI/CD + real blocked PR). Known
limitation recorded in the ADR rather than silently shipped: the
`KeyPairGenerator`/`initialize` variable link is a single-slot `dict`, not
scope-aware -- a reused variable name across two methods with different
algorithms in the same file would lose the first link. Not exercised by
current fixtures.

## 2026-09-19 — Functional proof for Phase 9 (PDF) and Phase 10 (audit chain)

A passing test count doesn't prove a feature does something real for a
user -- the same session that found the contract-fabrication defect (a
test suite that stayed green around a fictional API shape) means
"112/117 tests pass" isn't, by itself, proof either Phase 9 or Phase 10
does anything real. Got actual functional proof for both.

**Phase 9 (CBOM + executive PDF report)**: ran a real scan
(`POST /scans` against a 2-line real file with an `hashlib.md5(...)` call
and a real `rsa.generate_private_key(public_exponent=65537, key_size=2048)`
call -- `scan_7f992921ce0e`), fetched `GET /scans/{id}/report.pdf` for
real, and extracted its text with `pypdf` rather than trusting that a
200 response with the right content-type means the content is real.
It is: page 1's "Overall Mosca Quantum Risk Score: 90.0 / 100 CRITICAL"
and band counts (Critical 1 / Medium 1 / High 0 / Low 0) exactly match
`GET /scans/{id}/findings`'s real data; page 2's table row
`RSA key generation | vulnerable_app.py:8 | RSA | keygen | 90.0 | CRITICAL`
and `hashlib.md5 digest | vulnerable_app.py:5 | MD5 | digest | 18.0 | MEDIUM`
match the two real findings exactly (displayName, location, family,
function, score, band); page 3's remediation cost deltas
(`PKBYTESDELTA=928 WIREBYTESDELTA=832 OPMSDELTA=0.04` for the RSA->ML-KEM-768
migration) match `recommendation.cost` in the API response byte-for-byte.
Not lorem ipsum, not a placeholder -- genuinely this scan's data, correctly
laid out. (Bonus: this same scan is what caught the private-key floor fix
from earlier this session working live outside its unit test -- the RSA
keygen finding really did get forced to score >=90 with the "forced to
score >= 90 per policy" reason text showing up verbatim in the PDF.)

**Phase 10 (tamper-evident audit chaining)**: took the real, file-backed
`ecdat.db` this session's live backend was writing to, verified the chain
was intact (`verify_audit_log_integrity` -> `(True, None)`), then tampered
with a real row directly via `sqlite3` -- bypassing the FastAPI app, the
SQLModel ORM, and Python entirely (`UPDATE audit_log SET entity_id =
'scan_ATTACKER_MODIFIED' WHERE id = 2`, executed from a separate raw
`sqlite3` connection, the actual threat model for a tamper-evident log:
an attacker or misbehaving script with direct file access). Re-verified:
`(False, "Tampered record at id=2: stored hash=0296810b...4c6 != computed
eb944917...0f")` -- caught immediately and precisely. Restored the row and
confirmed the chain reports intact again. This exact scenario (raw-SQL
tamper against a real on-disk file, not an ORM-mediated mutation in an
in-memory test DB) wasn't covered by the existing test suite -- the two
existing tests both tamper by going through the SQLModel session
(`rec.detail = {...}; session.add(rec); session.commit()`), which is a
meaningfully different (weaker) attack model. Added
`tests/test_audit_chain.py::test_verify_audit_log_detects_tampering_via_raw_sql`
as a permanent regression for the real threat model, against a real temp
SQLite file. **118 tests now pass** (up from 117).

**Real gap found, not fixed this pass**: `verify_audit_log_integrity` is
never called from any HTTP route (`grep -rn "verify_audit_log_integrity"
api/routes/`) -- it's real, correct, and unit-tested, but there is
currently no way for an operator to actually invoke this check against a
running deployment without writing a one-off Python script the way this
verification did. Worth a `GET /api/v1/audit/verify` (or similar) admin
endpoint in a future pass -- noted here rather than silently left implied
by the passing tests.

## 2026-09-19 — Resolution pass: real-world benchmark corpus was too small to trust

A review of the 2026-09-18 audit found the "F1 1.000 (Synthetic & Real-World)"
claim wasn't well-supported: only 7 real-world usages across 3 files,
smaller than even the original task brief's own honest reference point
(31 real usages scoring 0.964/0.774 -- a lower, more credible number than
a perfect 1.0 on a sample this thin), and nowhere near the brief's actual
target (>=150 usages across 3 unseen projects, one Java/Go/C each).

**What's actually in `bench/` right now** (verified by listing, not
assumed): `bench/fixtures/` = 8 hand-written synthetic files, 15 labelled
usages (`bench/evaluate.py`, unchanged, still legitimately 1.0/1.0 on its
own small synthetic set -- not touched this pass). `bench/real_world/samples/`
had 3 files / 7 usages before this session.

**Git history search** (`git log --all -S "150"/"HOLD"/"Layer A" -- backend/`,
across both branches that exist in this repo) found **no evidence a
larger corpus or a genuine HOLD set was ever built and then lost** --
it never existed. That's a real, permanent gap, not something reduced.
Also found: `backend/PLAN.md`'s Phase 1 entry already documents the
brief's original "~70 usages, 0.986 recall" reference honestly as
unmeasured-in-this-repo, so this gap was known, just not closed.

**Grew the corpus properly**, per Loop B1's methodology (label from
reading the code, before running the detector, commit the labels first):
fetched two more real, unseen, permissively-licensed files --
`jwt/algorithms.py` (jpadilla/pyjwt, MIT -- previously flagged in this
project's own README as a known gap source and explicitly not vendored,
now vendored) and `securecookie.go` (gorilla/securecookie, BSD-3-Clause).
Hand-labelled 18 new usages (12 Python, 6 Go) by reading both files in
full, committed as `0545dbd` before ever running the detector on them.
(A third candidate, paramiko's key-handling modules, was fetched and read
but discarded unvendored -- LGPL-2.1, and the licence gate only allows
LGPL as an unmodified dependency, never vendored into this repo.)

Corpus is now **5 files / 2 languages / 25 usages** -- still well short
of >=150/3-languages, and said plainly rather than rounded up. Java and C
have zero detector coverage (`engine/` only has `source_python.py` and
`source_go.py`), so a HOLD set in either language would only demonstrate
that, not detection quality -- not attempted, recorded as a gap instead.

**Real result** (`uv run python bench/real_world/evaluate.py`, run once,
after committing labels):
```
precision=1.0 recall=0.52 f1=0.6842
truth=25 detected=13 tp=13
  false negative: ('gorilla_securecookie.go', 'AES', 'decrypt', 420)
  false negative: ('gorilla_securecookie.go', 'AES', 'encrypt', 148)
  false negative: ('gorilla_securecookie.go', 'AES', 'encrypt', 402)
  false negative: ('gorilla_securecookie.go', 'SHA-2', 'digest', 139)
  false negative: ('pyjwt_algorithms.py', 'ECDSA', 'sign', 761)
  false negative: ('pyjwt_algorithms.py', 'ECDSA', 'verify', 777)
  false negative: ('pyjwt_algorithms.py', 'Ed25519', 'sign', 994)
  false negative: ('pyjwt_algorithms.py', 'Ed25519', 'verify', 1018)
  false negative: ('pyjwt_algorithms.py', 'RSA', 'sign', 683)
  false negative: ('pyjwt_algorithms.py', 'RSA', 'sign', 914)
  false negative: ('pyjwt_algorithms.py', 'RSA', 'verify', 688)
  false negative: ('pyjwt_algorithms.py', 'RSA', 'verify', 926)
```
**This is a genuinely more informative number than the old 1.0/1.0.** Zero
false positives (the detector doesn't hallucinate crypto). Every single
false negative is one of two already-documented gaps, not a surprise:
(1) OO `key.sign()`/`key.verify()` calls where the key's concrete type
isn't known from the call site (no intra-file type inference -- listed as
future work since Phase 7), and (2) Go's generic `cipher.NewCTR(block, iv)`
taking a `cipher.Block` interface rather than a literal `aes.X(...)` call,
same root cause. Interestingly, the Python bare-attribute-reference
detector (Phase 7) and both direct `hmac.new`/`hmac.New` calls *did* get
found correctly (not in the false-negative list) -- confirms that specific
Phase 7 claim was real, not just the real-world recall number.

Updated: `tests/test_bench_real_world.py` (floor is now precision 1.0 /
recall 0.52 / truth 25, not the old fabricated-looking 1.0/1.0/7 -- a
regression floor, not a target to force back up by weakening anything),
`bench/real_world/README.md` (was itself stale -- said "4/4, two Python
files" after a later commit had already made it 7/7 across three without
updating this file; rewritten to point at this dated entry instead of
quoting a number that will go stale again), `README.md`'s quality-gate
table (also corrected pytest count 112->117 and rescore perf number,
which was showing a stale 2.47s/300ms-kernel figure against the real
current `[PERF RESULT] 10,000 findings rescore time: 70.64 ms`).

Gates re-run after all of this: `ruff`, `mypy --strict`, `pytest`
(117 passed) all clean.

## 2026-09-18 — Whole-repo cross-track audit + fix pass

Backend and frontend were built by two separate agent tracks and merged
onto `main`; this pass re-verified every claim in this file against real
command output (not commit messages), found and fixed real defects, and
ran the first genuine backend+frontend end-to-end integration test this
project has had. See root `CLAUDE.md`, `.claude/agents/*.md` for the audit
methodology.

Real defects found and fixed:
- `GET /scans/{id}/graph` always returned the same Phase 0 canned stub
  regardless of scan id. Added `api/graph.py::build_graph()` -- a real
  system->file->asset graph derived from `store.list_findings(scan_id)`,
  with real band/score/occurrences. `tests/test_graph_real.py` (new)
  proves two different scans now produce different graphs.
- The "unencrypted private key -> score >= 90" domain rule
  (`engine/factors.py`) was unreachable from any real scan: it guarded on
  `kind=FindingKind.KEY`, which no real detector ever emits (only
  `api/stub_data.py`'s example data uses it). Retargeted to
  `function=KEYGEN` + a Shor-broken family (the real, reachable signal) --
  see `docs/decisions/backend/012-private-key-floor-reachability.md`. New
  end-to-end test `test_real_rsa_keygen_scan_triggers_private_key_floor`
  proves it now fires from an actual `POST /scans` + real detector run,
  not a hand-built `Detection`.
- `api/rate_limiter.py` trusted a client-supplied `X-Test-Client-Id` header
  unconditionally, letting any external caller bypass rate limiting by
  varying it. Gated behind `ECDAT_RATE_LIMIT_TRUST_TEST_HEADER=1`
  (test-only, set in `tests/conftest.py`), never trusted by default.
- `engine/ingest.py`: `MAX_COMPRESSION_RATIO` was declared but never
  enforced (per-entry for zip via `compress_size`, aggregate archive-size
  vs. total-uncompressed for tar, since tar's gzip wraps the whole stream
  not each member). Tar extraction now passes `filter="data"` (adopts
  Python 3.12's safer default early, silences the 3.14 deprecation
  warning).
- `engine/scanner.py` had no per-file size cap -- one pathological huge
  file could still be read whole into memory even though the aggregate
  archive quota was enforced. Added a 100 MB per-file cap, counted in
  `ScanStats.skippedPrefilter` (not `errors`, since it's a policy skip,
  not an I/O failure).

Real end-to-end integration (real `uvicorn` backend + real `next build &&
next start` frontend, MSW structurally cannot run in a production build):
verified via `frontend/e2e/finale-integration.spec.ts` (real upload -> WS
stage events -> Overview band counts matched against the API directly ->
real `POST /rescore` -> real finding drawer + triage PATCH persisted ->
real CBOM fetched and shape-checked -> real graph with 2D fallback), both
themes, run against the live backend, not mocks. Also manually verified a
hostile path-traversal tar.gz is rejected by the real running
`POST /scans/upload` (400, traversal target never created, backend stays
healthy afterward) -- see the matching frontend note for the UI-side gap
this surfaced (launcher never showed upload errors) and fix.

Security scanners run for real this session (previously blocked on no
network access): `bandit` (3 findings, all reviewed as false positives --
see below), `pip-audit` (clean), `gitleaks` (clean, 26 commits scanned).
Bandit's 2 SQL-injection warnings in `api/store.py` are on
`f"...{ph}..."` strings where `{ph}` is only the dialect placeholder
character (`?`/`%s`); the actual values are always passed as parameterized
query args, never interpolated -- bandit's static check can't distinguish
that pattern. Its `tarfile_unsafe_members` warning on `zf.extractall()` in
`engine/ingest.py` (zip path) is pre-mitigated by this file's own manual
zip-slip/symlink validation of every entry before extraction (zipfile has
no `filter=` parameter the way tarfile does in 3.12+); the tar path was
given `filter="data"` as belt-and-suspenders on top of the same manual
checks.

Gates: `ruff`, `mypy --strict`, `pytest` (117 passed, up from 112),
`contract_diff.py`, `verify_airgap.py`, `bandit`, `pip-audit`, `gitleaks`
all clean/reviewed.

## 2026-09-18 — Phase 10: Security Hardening, Audit Log Hash-Chaining & Air-Gap Verification

Completed enterprise security hardening, tamper-evident audit logging, and automated air-gap verification:
- Cryptographic hash-chaining on `AuditLogRecord` (`api/db.py`, `api/db_models.py`):
  - Every mutation links to the predecessor via SHA-256 hash chaining anchored at genesis `"0"*64`.
  - Added `verify_audit_log_integrity(session)` validating uninterrupted hash chains and detecting any record modifications, insertions, or deletions.
- Sliding-window rate limiting middleware (`api/rate_limiter.py`, `api/main.py`):
  - In-memory thread-safe rate limiter protecting mutating API endpoints (`POST`, `PATCH`, `PUT`, `DELETE`).
  - Emits compliant HTTP 429 responses with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.
- Air-gap validation tool (`scripts/verify_airgap.py`, `tests/test_airgap.py`):
  - Static AST inspection verifying zero banned network, telemetry, or external AI/LLM modules in runtime code.
  - Verifies explicit version constraints on all runtime and development dependencies in `pyproject.toml`.
- ADR 010 documented in `docs/decisions/backend/010-phase10-security-hardening.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (112 passed), `contract_diff.py`, and `verify_airgap.py` all clean.

## 2026-09-18 — Phase 9: CycloneDX 1.6 CBOM Export & Multi-Page Executive PDF Report

Implemented complete exports and executive reporting suite:
- Upgraded CycloneDX 1.6 Cryptographic BOM (`api/cbom.py`, `GET /api/v1/scans/{id}/cbom`) with metadata enrichment (`ecdat:scanId`, `ecdat:policyId`, `ecdat:riskScore`).
- Added on-the-fly computed SHA-256 header `X-CBOM-SHA256` for instant tamper detection.
- Verified strict validation against the vendored CycloneDX 1.6 JSON schema for both seed and live AST scan findings.
- Built a zero-dependency, pure-Python multi-page PDF 1.4 report generator (`api/pdf_report.py`, `GET /api/v1/scans/{id}/report.pdf`) without external C libraries (Cairo/Pango).
- 3-page publication layout:
  - Page 1: Executive Scorecard with large Mosca score, risk band badges, breakdown metric cards, and threat context.
  - Page 2: Detailed Mosca risk factor formulation and top vulnerable findings table.
  - Page 3: NIST FIPS 203/204/205 PQC migration roadmap and cryptographic air-gap integrity stamp.
- ADR 009 documented in `docs/decisions/backend/009-phase9-reports-and-cbom.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (105 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 8: PQC Catalog & Algorithm Agility Metrics

Implemented authoritative NIST FIPS 203/204/205 PQC catalog and deterministic agility delta metrics:
- Authoritative NIST specifications in `engine/pqc.py`:
  - FIPS 203: ML-KEM-512 (Cat 1), ML-KEM-768 (Cat 3), ML-KEM-1024 (Cat 5)
  - FIPS 204: ML-DSA-44 (Cat 2), ML-DSA-65 (Cat 3), ML-DSA-87 (Cat 5)
  - FIPS 205: SLH-DSA-SHA2-128s, SLH-DSA-SHAKE-128s (Cat 1)
  - Parameter sets define public key size, wire/ciphertext overhead, operation latency, and standards status.
- Upgraded `engine/recommend.py` to route to standardized PQC algorithms based on cryptographic function and security level (e.g. RSA >= 3072 upgrading to ML-KEM-1024; RSA/ECDSA signers to ML-DSA-65/87).
- Deterministic agility cost delta calculation (`compute_cost_delta`) evaluating key size ratios, wire overhead, and CPU delta to return `RiskCost` (`low`, `medium`, `high`).
- Dynamic catalog generation from `NIST_PQC_CATALOG` serving `GET /api/v1/catalog/pqc`.
- ADR 008 documented in `docs/decisions/backend/008-phase8-pqc-catalog.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (100 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 7: Engine Expansion & Multi-Language Detection

Expanded the AST engine with multi-language detection and real-world attribute analysis:
- Added Go standard library crypto AST detector (`engine/source_go.py`, `engine/queries/go_crypto.scm`) using pinned `tree-sitter-go==0.25.0` wheel (air-gapped, zero runtime network calls), detecting RSA, ECDSA, AES, 3DES, DES, MD5, SHA-1, SHA-2, and HMAC.
- Added Python bare attribute reference detection in `engine/source_python.py` (`engine/queries/python_crypto.scm`), allowing detection of `hashlib.X` arguments passed into functions or constructors without calling.
- Integrated multi-language file routing in `engine/scanner.py` supporting both `.py` and `.go`.
- Added `bench/real_world/samples/go_crypto_sample.go` and verified precision 1.000, recall 1.000, F1 1.000 in `bench/real_world/evaluate.py`.
- ADR 007 documented in `docs/decisions/backend/007-phase7-multi-language-detection.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (95 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 6: Sandboxed Streaming Ingest (`POST /scans/upload`)

Implemented streaming multipart upload archive ingestion with full hostile traversal defenses:
- OpenAPI 3.1 contract update: added `POST /api/v1/scans/upload` (`multipart/form-data`) and `bundleHash` to `Scan` schema, documented in `contracts/CHANGELOG.md` (`0.3.0-phase6-ingest`). Zero contract drift verified.
- `engine/ingest.py`: on-the-fly streaming SHA-256 calculation, 2GB upload limit, and safe archive extraction for `.zip` and `.tar.*`.
- Security defenses:
  - Zip-Slip / path traversal prevention rejecting relative `..`, absolute paths, and verifying canonical sandbox destination.
  - Symlink escape prevention inspecting link targets to disallow escapes or system directory references.
  - Decompression bomb quotas enforcing 5GB uncompressed size limit and 50,000 maximum file count.
- Route integration in `api/routes/scans.py` extracting into ephemeral sandbox directories, running AST detection, and attaching computed `bundleHash`.
- ADR 006 documented in `docs/decisions/backend/006-phase6-sandboxed-ingest.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (90 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Phase 5: Rescore Performance Budget (<200ms SLA for 10,000 findings)

Implemented in-database bulk vectorized Common Table Expression (CTE) UPDATE + RETURNING in `api/store.py` (`rescore_scan_findings`).
- Directly recomputes urgency $U$, margin $(X+Y-Z)$, score, and risk band inside SQLite/Postgres without loading 10,000 ORM entities into Python memory.
- Mathematical invariant pruning: classically broken algorithms ($U=1.0$ unconditionally) are excluded from the CTE calculation, cutting write locks and execution overhead while ensuring mathematical invariance.
- Direct JSON tuple serialization (~25ms vs ~85ms standard dumps), returning pre-encoded bytes directly to Starlette `Response`.
- Performance test gate in `tests/test_rescore_perf.py` asserts < 200ms round-trip latency on 10,000 seeded findings (measured: 105–135ms).
- ADR 005 documented in `docs/decisions/backend/005-phase5-rescore-performance.md`.
- Gates: `ruff`, `mypy --strict`, `pytest` (79 passed), and `contract_diff.py` all clean.

## 2026-09-18 — Loop B1 starter step: real, unseen, hand-labelled Python code

Small, fast pass (explicitly not the brief's full DEV/HOLD scale — see
`bench/real_world/README.md`): fetched 2 small real files never used to
build or tune the detector (`itsdangerous`'s signer, BSD-3-Clause, and
`cryptography`'s own official RSA keygen doctest recipe, Apache-2.0/BSD
-- both on the licence gate's "OK" list), hand-labelled their crypto
usage by reading the source first, then ran the detector.

```
$ uv run python bench/real_world/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=4 detected=4 tp=4
```

4/4, no false positives/negatives -- on real, unseen code, not just the
synthetic starter set. Reading a broader real file (PyJWT's
`algorithms.py`, not vendored) surfaced two real, honestly-documented
detector gaps (bare `hashlib.X` attribute references without a call; no
type inference for `key.sign()`-style OO calls -- the latter already
listed in the brief's own Phase 7) rather than silently ignoring them --
see `bench/real_world/README.md` and `PLAN.md`.

Gates: `uv run ruff check . && uv run mypy --strict .` clean (46 files),
`uv run pytest` 78/78 passed at 94% coverage, `contract_diff.py` clean
(no API changes this pass).

## 2026-09-18 — Phase 4: Real-Time Events (scoped: real event log, sync scanning)

User was asked to choose between (a) a real, stored per-scan event log
replayed after a still-synchronous `POST /scans` returns, with genuine
resume-by-eventId, or (b) making scanning fully asynchronous so a WS
client can watch it live. Chose (a) -- smaller, deterministic, no
async-timing test flakiness; full async scanning stays a documented gap
for later, not silently faked.

Preceded by a separate `contract: update ScanEvent schema...` PR (#5,
merged) per this repo's git rules (contract changes never land inside a
feature commit) -- replaced the placeholder `percent` field with the real
fields this phase's event log actually produces.

Built: `engine.scanner.scan()` takes an optional `on_event` callback and
emits real `stage`/`progress`/`finding` events as it runs (real stage
transitions, a real running per-surface finding counter, real finding
ids). `ScanEventRecord` + `store.list_events()` persist and replay that
log. `WS /scans/{id}/events` now sends the *actual* recorded events for
that scan (previously: a hardcoded canned sequence referencing fake
finding ids, regardless of what was scanned) -- rate-limited to <=10
msg/sec, with `?after=<eventId>` resume.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 43 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                       1183     64    95%
Required test coverage of 85% reached. Total coverage: 94.59%
77 passed, 3 warnings in 4.85s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual verification

Booted a real `uvicorn` server, wrote a file with `hashlib.md5(...)` +
`hmac.new(..., hashlib.sha1)`, `POST /scans`, then used a real Python
`websockets` client:
- Full replay: 7 real events in order (`stage:ingesting`,
  `stage:scanning`, 2x real `finding` events with real ids/families,
  `progress` with `bySurface: {"source": 2}`, `stage:scoring`, `done`
  with the right `findingCount`).
- Resume: reconnecting with `?after=4` returned only events 5-7 (the
  genuine tail) -- confirms resume is real, not decorative.

### Loops run

None of B1/B3-B6 apply. No risk-formula/factor change this phase.

### BLOCKED items

None. The one deliberate gap (live streaming during an in-flight scan)
is a scoped-out design decision, not a blocker -- see `PLAN.md`.

### Contract changes / PROPOSALS decisions

`contract: update ScanEvent schema for real Phase 4 event log` (PR #5,
merged before this feature PR) -- see `contracts/CHANGELOG.md`. No
PROPOSALS from the frontend agent yet.

### Next 3 tasks

See `PLAN.md`: (1) a real hand-labelled DEV/HOLD corpus (Loop B1) plus
broader Python detection coverage, (2) Phase 5 rescore performance
budget, (3) revisit async scanning if live-during-scan progress becomes
important before Phase 6.

## 2026-09-18 — Phase 3: Real API

Wired `engine.scanner.scan()` into `POST /scans`: it now scans the given
server-side `path` with the real Python detector and persists real,
risk-scored findings via `api/store.py` (new `store.create_scan_from_result`
+ `store.resolve_policy`, replacing the always-empty stub `create_scan`).
`payload.crqcYears` now genuinely overrides the scoring horizon for that
scan (a policy copy with the override is what gets passed to
`engine.factors.derive_risk`), not just a stored-but-unused metadata field.
Missing/nonexistent `path` -> 400; an `OSError` during scanning ->
`status=failed` rather than a 500. The API contract is unchanged — this
phase changes route *behavior*, not shapes — verified with
`scripts/contract_diff.py`.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 42 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                       1140     64    94%
Required test coverage of 85% reached. Total coverage: 94.39%
71 passed, 3 warnings in 3.24s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual verification

Booted a real `uvicorn` server, wrote a real file with `hashlib.sha1(...)`,
and:
- `POST /scans {"path": "/tmp/e2e_scan_target"}` -> real `stats.files=1`,
  a real `bands.medium=1`, not the old canned empty stub.
- `GET /scans/{id}/findings` -> one real finding: family `SHA-1`, a
  genuine risk score (18.0, band `medium`, `classicallyBroken: true`),
  and a real recommendation (`SHA-2-256`).
- `GET /scans/{id}/cbom` -> 1 CycloneDX component, matching the finding.
- `POST /scans {"path": "/does/not/exist"}` -> 400.
- `POST /scans {}` (no path) -> 400.

### Loops run

None of B1/B3-B6 apply. No formula/factor change this phase (only real
wiring) — `tests/test_risk_formula.py` and `tests/test_factors.py` still
pass unchanged.

### BLOCKED items

None.

### Contract changes / PROPOSALS decisions

None — verified via `contract_diff.py`.

### Next 3 tasks

See `PLAN.md`: (1) a real hand-labelled DEV/HOLD corpus (Loop B1) plus
extending Python detection coverage, (2) Phase 4 real-time WS scan
progress backed by the real engine run, (3) Phase 5 rescore performance
budget now that `POST /scans` can actually produce large finding sets.

## 2026-09-18 — Phase 2: Persistence

Replaced `api/store.py`'s in-memory dicts with SQLModel + SQLite
(`api/db.py`, `api/db_models.py`) per `PLAN.md`'s Phase 2 scope — see ADR
004. Every raw risk factor is stored as its own column (per the brief),
`Recommendation`/`Policy` nested data as JSON columns. Every mutating
store call now writes an `AuditLogRecord`. Routes switched from
`stub_data.*` to `store.*` for findings; `api/store.py`'s public function
signatures are unchanged from Phase 0/1, so the API contract is untouched
— `contract_diff.py` still reports zero drift.

Manual end-to-end verification (not just the test suite): booted a real
`uvicorn` server against a file-based SQLite DB, `POST /scans`, killed the
process, restarted it, re-fetched the scan — it was still there. This
caught a real bug: SQLite silently strips `tzinfo` from stored
`datetime`s, so `startedAt`/`finishedAt` lost their `Z` suffix after a
restart. Fixed in `api/db._as_utc()` (reattaches UTC on read) with a
regression test. See `docs/decisions/backend/004-phase2-persistence.md`
for the write-up — this is exactly the kind of bug an in-memory-only test
suite doesn't catch, which is why the manual restart check was worth doing.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 41 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                       1116     61    95%
Required test coverage of 85% reached. Total coverage: 94.53%
65 passed, 3 warnings in 3.23s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual verification

```
$ DATABASE_URL="sqlite:////tmp/phase2_test.db" uv run uvicorn api.main:app ...
$ curl -X POST .../api/v1/scans -d '{"path": "/tmp/persist-me"}'
  -> {"id": "scan_7c6b1e016d82", ..., "startedAt": "2026-09-18T00:23:52.606973Z"}
# killed the process, restarted uvicorn against the same DB file
$ curl .../api/v1/scans/scan_7c6b1e016d82
  -> {"startedAt": "2026-09-18T00:23:52.606973Z", ...}   # survived, Z intact after the fix
```

### Loops run

None of B1/B3-B6 apply. No Loop-B2-relevant formula change this phase
(only how factors reach storage, not the formula itself) — Phase 0's
`tests/test_risk_formula.py` still passes unchanged.

### BLOCKED items

None.

### Contract changes / PROPOSALS decisions

None — verified via `contract_diff.py`.

### Next 3 tasks

See `PLAN.md`: (1) Phase 3 — wire `engine.scanner.scan()` into
`POST /scans` so real findings actually get persisted, (2) a real
hand-labelled DEV/HOLD corpus (Loop B1), (3) Phase 4/5 real-time WS +
rescore performance budget now that findings live in an indexed DB.

## 2026-09-17 — Phase 1: Engine Packaging

Built a real Python detection engine per `PLAN.md`'s Phase 1 scope:
`engine/scanner.py` (walk + orchestrate), `engine/source_python.py` +
`engine/queries/python_crypto.scm` (tree-sitter detector: hashlib digests,
hmac.new incl. underlying-hash resolution, RSA/EC keygen via
`cryptography`, weak/symmetric cipher construction), `engine/families.py`
+ `engine/factors.py` (new V/F/E/K/X/Y/Z derivation feeding the Phase 0
formula — see ADR 002), `engine/recommend.py` (family -> PQC
recommendation). Added a `bench/` harness (`evaluate.py` + `truth.json` +
`fixtures/`) that produces the repo's first **real measured** number.

Explicitly not done this pass (see `PLAN.md`): the Loop B1 DEV/HOLD corpus
from real unseen projects (only synthetic starter fixtures exist), other
languages, and wiring the engine into the API (`POST /scans` still returns
Phase 0 stub data — that's Phase 3).

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 38 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov=bench --cov-report=term-missing --cov-fail-under=85
...
TOTAL                        957     61    94%
Required test coverage of 85% reached. Total coverage: 93.63%
57 passed, 3 warnings in 2.91s

$ uv run python scripts/contract_diff.py
No contract drift.

$ uv run python bench/evaluate.py
precision=1.0 recall=1.0 f1=1.0
truth=15 detected=15 tp=15
```

This precision/recall is the **first real measured number in this repo**
(Phase 0's `CLAUDE.md` said "None yet"). It is Phase 1's small synthetic
starter fixture set (8 files, 15 usages) — not the brief's Layer A/B
corpus. See `bench/README.md` for why, and `tests/test_bench_evaluate.py`
for the regression floor this sets.

### Manual verification

Ran `engine.source_python.detect()` directly against a hand-written
snippet exercising all 6 rule branches (md5, hashlib.new, hmac.new+SHA-1,
RSA keygen with key_size kwarg, EC keygen with curve, AES/3DES ciphers)
and confirmed every field (family, function, key_size, curve,
underlying_hash_family) before writing the fixture set — see
`backend/LEARNINGS.md` for the tree-sitter API details confirmed this way.

### Loops run

None of B1/B3-B6 apply yet (no real corpus, no fuzz targets, no API
change, no perf surface, no new external-facing security surface). A
Loop-B2-style property check exists from Phase 0
(`tests/test_risk_formula.py`) and still passes unchanged since the
formula itself didn't change this phase — only what feeds it did.

### BLOCKED items

None.

### Contract changes / PROPOSALS decisions

None — Phase 1 doesn't touch `contracts/openapi.yaml` by design (verified
via `contract_diff.py`, unchanged from Phase 0).

### Next 3 tasks

See `PLAN.md` "Next 3 tasks": (1) a real hand-labelled DEV/HOLD corpus,
(2) Phase 2 persistence (SQLModel), (3) Phase 3 wiring the engine into
`POST /scans` + extending Python detection coverage.

## 2026-09-17 — Phase 0: Contract & Skeleton

Repo (`nani224/SIH26164`) was verified empty at session start (GitHub API:
0 branches, `size: 0`) despite the brief describing a pre-existing engine.
Built Phase 0 from scratch: repo skeleton, `contracts/openapi.yaml` (OpenAPI
3.1, 13 HTTP paths + 1 WS-documented path, 38 generated component schemas),
an in-memory FastAPI stub implementing every contract endpoint, and CI.

### Gate output (real, run from `backend/`)

```
$ uv run ruff check .
All checks passed!

$ uv run mypy --strict .
Success: no issues found in 26 source files

$ uv run pytest --cov=api --cov=engine --cov=scripts --cov-report=term-missing --cov-fail-under=85
...
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
api/__init__.py                0      0   100%
api/cbom.py                   50      4    92%   42, 46, 54, 74
api/filtering.py              38      9    76%   29, 31, 33, 35, 39-40, 51, 53, 61
api/main.py                   20      0   100%
api/models.py                237      0   100%
api/pdf_stub.py                19      0   100%
api/routes/__init__.py         0      0   100%
api/routes/catalog.py           7      0   100%
api/routes/findings.py         12      0   100%
api/routes/health.py            7      0   100%
api/routes/policies.py         21      2    90%   16, 23
api/routes/scans.py            83      3    96%   96, 186, 188
api/store.py                   31      0   100%
api/stub_data.py               29      1    97%   343
engine/__init__.py              0      0   100%
engine/risk.py                  27      0   100%
scripts/__init__.py             0      0   100%
scripts/contract_diff.py       91     17    81%   84, 102, 104, 111, 113-114, 119, 125, 131-138, 142
--------------------------------------------------------
TOTAL                          672     36    95%
Required test coverage of 85% reached. Total coverage: 94.64%
33 passed, 3 warnings in 2.88s

$ uv run python scripts/contract_diff.py
No contract drift.
```

### Manual end-to-end check (real server, not just TestClient)

Booted `uv run uvicorn api.main:app` on 127.0.0.1:8123 and hit it with curl
+ a small Python `websockets` client:
- `GET /api/v1/health` -> 200, real JSON.
- `GET /api/v1/scans/scan_stub_001/findings` -> 200, real filtered/paginated JSON.
- `GET /api/v1/scans/scan_stub_001/cbom` -> 200, CycloneDX 1.6 JSON.
- `GET /api/v1/scans/scan_stub_001/report.pdf` -> 200, `content-type: application/pdf`;
  `file /tmp/report.pdf` confirmed: `PDF document, version 1.4, 1 page(s)`.
- `GET /api/v1/catalog/pqc` -> 200, real FIPS 203/204/205 reference entries.
- `WS /api/v1/scans/scan_stub_001/events` -> 7 frames received in order
  (stage, progress, stage, finding x2, stage, done), each with an `eventId`.
- `GET /openapi.json` -> 13 paths, 38 component schemas.

### Gates not yet applicable (no engine/bench/exports exist yet)

bench/evaluate.py (Layer A/B), HOLD set, bench/hostile_tests.py,
schemathesis, load test, air-gap run (no network calls exist to disable
yet — trivially true), full CBOM signing, security scanners (bandit/
semgrep/pip-audit/gitleaks/grype) — none run this session; nothing to
scan/measure yet beyond what ruff/mypy/pytest already cover.

### Contract changes / PROPOSALS decisions

Initial contract only — `contracts/CHANGELOG.md` 0.1.0-phase0 entry.
`contracts/PROPOSALS.md` created empty (no frontend proposals yet).

### Loops run

None of Loop B1-B6 apply yet (no detection engine, no persisted findings,
no load-bearing performance surface, no fuzz targets beyond what Phase 0
has). LOOP B2-style property tests were added early for `engine/risk.py`
(Hypothesis: score in [0,100], U non-decreasing in Y / non-increasing in Z,
classically-broken forces U=1 and a stable band regardless of Z,
rescore(original Z) reproduces the stored example score) since that
formula already exists — see `tests/test_risk_formula.py`. Not run to a
cap; there's only one small pure function to test right now.

### BLOCKED items

None. Everything attempted this session succeeded.

### Next 3 tasks

See `PLAN.md` "Next 3 tasks" (start of Phase 1: real `engine/scanner.py` +
one detection rule with fixture/truth/test; `bench/` harness; Phase 2
persistence wiring behind the existing contract).
