# 004 — Java crypto detection engine (M1, Track CC)

## Status

Accepted

## Context

Before this pass, `engine/` detected Python (tree-sitter) and Go
(tree-sitter) source, plus one binary AES S-box constant check. Java was
entirely uncovered, despite being one of the four target languages for
the eventual ~150-usage HOLD corpus (Track CC M3). `tree-sitter-java` was
unverified as an available/pinnable dependency going in.

## Decision

- Confirmed `tree-sitter-java==0.23.5` resolves via `uv add tree-sitter-java`
  and is MIT-licensed (same licence family as the existing
  `tree-sitter-python`/`tree-sitter-go` grammars) — no licence-gate issue.
  Pinned in `pyproject.toml`.
- New `engine/source_java.py` + `engine/queries/java_crypto.scm`, mirroring
  the existing Go/Python detectors' shape: the tree-sitter query captures
  the generic AST shapes (`obj.method(args)` method invocations, `new
  Type(args)` object creation) and all semantic matching (which class/
  method pairs are real crypto usages, transformation-string parsing)
  happens in Python, not query predicates — consistent with
  `source_python.py`'s documented rationale for the same choice.
- Covers the JCA/JCE surface named in the Track CC brief: `Cipher`,
  `KeyPairGenerator`, `KeyGenerator`, `MessageDigest`, `Signature`,
  `KeyAgreement`, `Mac`, `SSLContext`, `KeyStore`, `SecretKeySpec`, plus
  direct BouncyCastle lightweight-API class usage (`new SHA256Digest()`,
  `new AESEngine()`, `new RSAKeyPairGenerator()`, `new
  Ed25519KeyPairGenerator()`, ...) via a class-name lookup table. BC usage
  through the JCA `Provider` argument (`Cipher.getInstance("AES/GCM/
  NoPadding", "BC")`) is already covered by the transformation-string path
  since the extra provider arg doesn't change the call shape.
- Transformation-string parsing is genuinely per-class: `Cipher`'s
  `"AES/GCM/NoPadding"` splits on `/` (algorithm/mode/padding);
  `Signature`'s `"SHA256withRSA"` splits on the literal `with` into
  hash+family (hash recorded as `underlying_hash_family`, matching the
  existing HMAC convention); `Mac`'s `"HmacSHA256"` strips the `Hmac`
  prefix and looks up the remainder as a digest name.
- One piece of real (if deliberately narrow) intra-method dataflow:
  `KeyPairGenerator`/`KeyGenerator` don't carry key size or curve in their
  `getInstance(...)` call the way `Cipher`/`Signature` do — that comes
  from a *separate*, later `var.initialize(n)` / `var.init(n)` call on the
  same assigned variable. `_handle_call` tracks a `pending: dict[str,
  Detection]` keyed by variable name (recovered via
  `call_node.parent.type == "variable_declarator"`) between the
  `getInstance` call and its `initialize`/`init` call, in source order (a
  single sorted pass over all query matches by `start_byte`). If no
  matching `initialize`/`init` is ever found in the file, the pending
  detection is still emitted at end-of-file (without key_size/curve)
  rather than silently dropped — a detector that requires a specific
  follow-up call to fire at all would be a stealth recall regression.
  This is deliberately the single simplest case (same variable, same
  file, textual order) — not a general dataflow/points-to analysis.
- `SSLContext.getInstance("TLSv1.2")` and `KeyStore.getInstance("PKCS12")`
  are detected with `family=None` — there is no `Family` enum value for
  "TLS protocol version" or "keystore container format", and inventing one
  outside an ADR-approved schema change would violate the "never invent
  an enum value" rule. `engine/factors.py::_resolve_vulnerability` already
  handles `family=None` (V=0.5, not classically broken), so these still
  produce a real (if V-neutral) finding rather than being silently
  dropped — flagging "TLS is configured here" / "a keystore is loaded
  here" has standalone value for an inventory tool even without a quantum
  risk factor attached.
- 9 new fixture files under `bench/fixtures/` (`Java*.java`, one
  true-negative file), 25 new labelled entries in `bench/truth.json`
  (fixtures grew from 15 to 40 usages total) — written to exercise every
  implemented pattern plus common non-crypto object creations
  (`StringBuilder`, `ArrayList`, `Logger`) that must not fire, matching
  the existing Python fixture set's structure. `tests/test_source_java.py`
  adds 12 focused unit tests (one per pattern + the linkage cases + a
  true-negative case).
- `engine/scanner.py` wired `.java` into `_SOURCE_EXTENSIONS` and the
  per-file dispatch, same as `.go`.

## Consequences

- Layer A (`bench/evaluate.py`) stays precision 1.0 / recall 1.0 (now
  40/40 true positives, up from 15/15) — verified via
  `uv run python bench/evaluate.py`.
- `bench/real_world/` (the actual HOLD-methodology corpus) is unaffected
  by this change — no Java files exist there yet; that's M3.
- Java detections reuse the same `Detection`/risk-scoring/recommendation
  pipeline as Python/Go — no changes needed to `engine/factors.py`,
  `engine/recommend.py`, or the API/contract layer.
- Known gap, left honest rather than papered over: the
  `KeyPairGenerator`/`initialize` link only tracks the single most recent
  `getInstance` per variable name within one file (a `dict[str,
  Detection]`, not a stack or scope-aware structure) — a variable name
  reused across two unrelated methods in the same file with different
  algorithms would have the second `getInstance` silently overwrite the
  first's pending entry before its own `initialize` link. Not exercised by
  the current fixtures; worth a HOLD-corpus false-negative check in M3/M4
  if real Java code turns out to do this.
