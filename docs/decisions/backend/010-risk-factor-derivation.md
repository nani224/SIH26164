# ADR 010: Phase 1 risk factor derivation (V/F/E/K/X/Y/Z)

Status: accepted
Date: 2026-09-17

## Context

Phase 0 built only the pure Mosca scoring formula (`engine/risk.py`):
`Score = 100 x V x F x U x E x K`, `U` from `X`, `Y`, `Z`. Nothing derived
those seven inputs from an actual detection + policy. Phase 1 needs that to
produce real `Risk` objects from `engine.scanner.scan()`. The brief doesn't
specify how each factor is derived beyond the formula itself, so this ADR
records the mapping this session chose, so it can be revised deliberately
rather than drifting.

## Decision

Implemented in `engine/factors.py` + `engine/families.py`:

- **X** (shelf-life) = the matched policy `Context.shelfLifeYears`.
- **Y** (migration time) = the matched policy `Context.migrationYears`.
- **Z** (CRQC horizon) = `Policy.crqcYears`.
- **Context matching**: first `Policy.contexts[].glob` (via `fnmatch`) that
  matches the finding's path, else `Policy.default`.
- **V** (quantum vulnerability), by family (`engine/families.py`):
  - Shor-broken asymmetric families (RSA, DSA, DH, ECDH, ECDSA, Ed25519,
    X25519): `V = 1.0` regardless of key size -- a CRQC breaks these in
    polynomial time once it exists.
  - Post-quantum families (ML-KEM, ML-DSA, SLH-DSA): `V = 0.0`.
  - Symmetric ciphers (AES, ChaCha20): `V = 0.1` at >=256-bit keys (Grover
    only halves effective security; 128 bits post-Grover is still strong),
    `V = 0.6` below 256 bits.
  - Already-broken/deprecated symmetric (3DES, DES, RC4, Blowfish):
    `V = 1.0`, `classicallyBroken = True` for DES/RC4/3DES (MD5/SHA-1 are
    the classically-broken *hashes*, see below; 3DES/DES/RC4 are broken or
    trivially brute-forced today, independent of quantum computing).
  - Hashes: MD5/SHA-1 `V = 1.0` + `classicallyBroken = True` (both have
    practical collision attacks today); SHA-2/SHA-3 `V = 0.05` (Grover
    halves preimage-resistance bits; 256+-bit digests stay comfortable).
  - HMAC: resolved via the underlying hash captured at detection time
    (`Detection.underlying_hash_family`); falls back to `V = 0.05` if
    unresolved.
  - Unknown family: `V = 0.5` (neutral) -- paired with low detector
    confidence so `needsReview` catches it.
- **F** (function criticality), by `CryptoFunction`: keygen 0.9, sign/
  decrypt 0.85, keyderive 0.8, encrypt 0.7, verify/tag 0.6, digest/unknown
  0.5. Rationale: compromising a signing/decryption/keygen operation is
  more consequential than a verify or digest call.
- **K** (key/asset criticality) = matched `Context.criticality` mapped
  mission-critical 1.0 / high 0.8 / medium 0.6 / low 0.4.
- **E** (exposure) = matched `Context.exposure` mapped external 1.0 /
  internal 0.6 / isolated 0.3 / test 0.1.
- **Private-key floor**: a `kind=key` finding whose function is sign/
  decrypt/keyderive (i.e. an unencrypted private key, not just a public
  key reference), in a context whose exposure isn't `test`, has its score
  floored at 90 and band recomputed -- the brief's explicit rule
  ("Unencrypted private key outside test paths -> score >= 90").
- `needsReview` unchanged from Phase 0: `confidence < 0.75`.

## Consequences

- These weights are a first cut, not measured/tuned against real-world
  data (no such corpus exists yet -- see `bench/README.md`). Expect Loop
  B2-style property tests to hold (score in [0,100], monotonic U, stable
  band for classically-broken findings) but not expect the *absolute*
  numbers to be final.
- Changing any table in this ADR is a scoring-behavior change and should
  come with a new ADR (or an explicit amendment to this one), same as the
  formula itself.
