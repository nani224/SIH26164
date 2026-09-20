# 018 — Go bare function-value references (M6)

## Status

Accepted

## Context

M4 closed Python's OO `key.sign()`/`key.verify()` cluster but left a
smaller, related Go gap fully documented and untouched: Go's registry/
callback idiom passes a crypto constructor function *by value*, never
calling it at the reference site --
`gorilla_securecookie.go`'s `hashFunc: sha256.New,` (a struct field
literal) and `s.BlockFunc(aes.NewCipher)` (a bare call argument). The
existing Go detector's query only matches `call_expression` nodes, so
neither line produced a detection despite both being genuine, real
usages -- the referenced function is later invoked as the hash/cipher
constructor it names.

Python already solved the identical problem (`hashlib.sha256` assigned
without a call, ADR/PROGRESS history predating this session) via a
dedicated `attr.node` query capture plus a check to avoid double-firing
when the same attribute IS the callee of an enclosing call. This is a
direct port of that mechanism to Go's AST, not new research.

## Decision

- `engine/queries/go_crypto.scm` gained a second pattern: every
  `pkg.Func`-shaped `selector_expression`, called or not. This
  necessarily also matches the selector *inside* a real call (the same
  node the existing `call_expression` pattern already captures) --
  `engine/source_go.py` filters those out by checking whether the
  selector is the `function` field of an immediately enclosing
  `call_expression`.
- `_resolve_pkg_fn(pkg, fn)` factors the existing pkg/fn -> family/
  function/display/symbol/confidence table out of the old inline
  `_classify`, shared by both the real-call path (`_classify_call`,
  which layers on argument-derived extras: key_size, curve, underlying
  hash) and the new bare-reference path (`_classify_bare_reference`,
  which has no call arguments to read and reports at a slightly lower
  confidence, `-0.05`, to reflect that). The referenced function's own
  role IS the usage's role -- `sha256.New` referenced as a hash
  constructor is a digest usage whether or not it's invoked at this
  exact line, same principle as the M4 Python fix reusing the
  constructor's own family rather than guessing from the reference
  site.
- Real false-positive risk found and fixed during implementation, not
  after: the existing `test_go_hmac_with_underlying_hash` fixture
  (`hmac.New(sha256.New, key)`) passes `sha256.New` as a bare argument
  -- exactly the new pattern's target shape. Without a guard, this
  produced **two** findings for one line (the HMAC detection, which
  already captures `sha256` via `underlying_hash_family`, *and* a
  separate standalone SHA-2 "reference" finding) -- a real duplicate,
  not two distinct facts. `_is_hmac_new_hash_argument` checks whether a
  bare reference is specifically the first (hash-constructor) positional
  argument of an `hmac.New(...)` call and, if so, skips it -- the
  information is already on the HMAC detection.

## Consequences

- Real-world (HOLD) recall 0.8125 -> 0.875 (28/32): both target false
  negatives (`gorilla_securecookie.go:139` SHA-2 digest, `:148` AES
  encrypt) now detected, at their real lines, matching the existing
  truth.json labels exactly. **Zero new false positives** -- precision
  holds at 1.0. Verified via `uv run python bench/real_world/evaluate.py`.
- Layer A stays 56/56, unaffected -- no existing fixture exercises this
  pattern; 5 new dedicated unit tests added instead (struct-field
  reference, call-argument reference, the HMAC-argument double-count
  guard as its own named regression test, and an unrecognized-package
  negative case proving no guessing).
- Remaining real-world misses (4, unchanged by this fix, see updated
  `tests/test_bench_real_world.py` docstring): `gorilla_securecookie.go`'s
  `cipher.NewCTR(block, iv)` (generic `cipher.Block` interface parameter,
  the concrete constructor several calls removed -- needs real
  dataflow) and the two pyjwt gaps M4 already left open (project-
  specific type alias, verify-on-local-variable).
