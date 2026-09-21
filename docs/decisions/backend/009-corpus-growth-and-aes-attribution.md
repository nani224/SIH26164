# 009 — M7 real-world corpus growth: 2 capability extensions, 1 labelling-convention finding

## Status

Accepted (Track CC, 2026-09-20).

## Context

M7's mandate: grow `bench/real_world/` toward 150 usages, preferring
breadth of idiom over volume, strictly following Loop B1's label-before-run
discipline (corpus-labeler labels blind, detector not run -> commit labels
alone -> run the detector exactly once -> record numbers as measured, no
further detector or label changes to make that specific run's numbers look
better).

Five new files were sourced (two golang.org/x/crypto files, two Django
files, one Spring Security file — see `bench/real_world/README.md`'s
provenance table) and read manually during sourcing, before any labelling
began. That reading surfaced two real API-coverage gaps in files about to
become HOLD candidates: Go's `crypto/dsa` package (`dsa.Sign`/`dsa.Verify`,
used by `x_crypto_ssh_keys.go` for legacy `ssh-dss` host keys) and Java's
`javax.crypto.SecretKeyFactory` (used by
`spring_security_Pbkdf2PasswordEncoder.java` for PBKDF2 key derivation).

## Decision 1: extend detector capability for both patterns before labelling

Both gaps were real, generalizable API surface (not one-off HOLD-specific
hacks) and were found by reading source, not by running the detector and
reacting to a miss — no detector run against either motivating file had
happened yet. Per the established precedent from this same session (Go
`rsa`/`ecdsa`/`ed25519` sign/verify, added after reading `x_crypto_ssh_keys.go`
but before labelling it), this is legitimate capability development, not
tuning on HOLD. Both were implemented, tested with dedicated fixtures/unit
tests, and committed in their own commits *before* the corpus-labeler
subagents were dispatched for the files that motivated them.

- `engine/source_go.py`: `dsa.Sign` -> `Family.DSA`/`SIGN`, `dsa.Verify` ->
  `Family.DSA`/`VERIFY`, same table-driven shape as the existing RSA/ECDSA/
  Ed25519 entries.
- `engine/source_java.py`: `SecretKeyFactory` added to `_GET_INSTANCE_CLASSES`;
  transformation strings of the form `PBKDF2WithHmacSHA*` resolve to
  `Family.HMAC`/`KEYDERIVE` (PBKDF2 is itself HMAC-based — there is no
  distinct `Family` enum value for it, and none was added, since `Family`
  is contract-owned and Track CC does not edit `backend/api/`). Legacy
  `PBEWith...` names are left unmapped rather than guessed at.

Neither extension, as it turned out, changed this run's real_world numbers
directly: `x_crypto_ssh_keys.go`'s two `SecretKeyFactory.getInstance(...)`
calls in the *other* new file both take a runtime-configurable argument
(an enum's `.name()`), not a literal, so the labeler correctly left them
unlabelled regardless of the extension — see gap #8 in the README. The
extensions still stand on their own merits as real, correct API coverage
that will matter for other files (present or future).

## Decision 2: the two `aes.NewCipher` "false positives" are not code defects — labels stay as measured

Running `bench/real_world/evaluate.py` once, as required, produced 2 false
positives, both in `x_crypto_ssh_keys.go`: `aes.NewCipher(key)` at lines
1509 and 1561. The detector's behavior here is correct and consistent with
existing, already-accepted labels elsewhere in this same corpus —
`gorilla_securecookie.go`:148's `s.BlockFunc(aes.NewCipher)` bare reference
is labelled `AES`/`encrypt` in `truth.json` today, using exactly the same
`aes.NewCipher`-is-the-attribution-point convention.

The `x_crypto_ssh_keys.go` corpus-labeler subagent, working blind and
before any detector run, made a different (and independently defensible)
choice: it attributed the AES usage to the downstream
`XORKeyStream`/`CryptBlocks` call instead of the `aes.NewCipher` constructor
call, reasoning (in its own report) that "the encrypt/decrypt semantics
live there." That produced 3 new false-negative entries (the downstream
calls, which the detector cannot yet reach — see README gap #2, same root
cause as `gorilla_securecookie.go`'s pre-existing `cipher.NewCTR` gap) and,
as a side effect, left the constructor calls themselves unlabelled, which
the detector's real (and, per existing convention, correct) hit against
then registers as 2 false positives.

**Decision: the labels are not edited after the fact to add the
constructor lines.** Doing so — recognizing a detector-flagged line as a
"real" usage and adding it to `truth.json` only after seeing that the
detector already found it — is exactly the inspect-the-miss-then-relabel
pattern Loop B1's "never tune on HOLD" rule exists to prevent, even though
the underlying reasoning (this corpus already treats `aes.NewCipher` as
the attribution point) is sound and traceable to a labelling choice made
independently of this specific run. The measured numbers
(precision=0.9583, recall=0.8214) are recorded exactly as produced by the
one permitted run, with this note explaining the 2 false positives'
real cause.

**Forward-looking convention, for the next corpus pass**: state explicitly
in the corpus-labeler prompt that for Go/C block-cipher APIs where
construction and use are separate calls, the *constructor* (`aes.NewCipher`,
`EVP_CIPHER_fetch`, `mbedtls_aes_setkey_enc`, etc.) is this corpus's
canonical attribution point, not the downstream mode operation — matching
what every prior file already does. This avoids relitigating the same
question on the next file without ever touching an already-scored one.

## Consequences

- Real_world corpus: 32 -> 56 usages, 9 -> 14 files, precision 1.0 ->
  0.9583 (still above the 0.95 floor), recall 0.875 -> 0.8214.
- 2 new detector capabilities shipped (Go DSA sign/verify, Java
  SecretKeyFactory/PBKDF2), both verified via dedicated unit tests and
  Layer A regression (64/64, unaffected).
- 3 new documented false-negative gap categories for a future pass: no
  Python PBKDF2 API coverage at all (`hashlib.pbkdf2_hmac`, Django's own
  `pbkdf2()` wrapper), attribute-bound hash resolution
  (`self.digest(...)` reading back a class attribute), and 3 more
  instances of the existing Go generic-`cipher.Stream`/`BlockMode`
  dataflow gap.
- No detector or label change was made in reaction to this run's own
  output — the discipline held under real pressure (a borderline-but-
  passing precision number), which is the point of enforcing it.
