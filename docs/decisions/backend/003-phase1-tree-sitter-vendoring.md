# ADR 003: tree-sitter grammar vendoring approach

Status: accepted
Date: 2026-09-17

## Context

The brief says: "tree-sitter-language-pack downloads grammars on first use
-- vendor them," under the air-gap rule (no runtime network calls,
build-time downloads pinned/hashed/vendored).

## Decision

Phase 1 uses the official per-language PyPI packages (`tree-sitter`,
`tree-sitter-python`) instead of `tree-sitter-language-pack`. Verified
empirically this session: `tree-sitter-python` 0.25.0's wheel ships the
Python grammar already compiled into the package at *build* time -- there
is no runtime download, no network call, no separate grammar-fetching step
on first use. The dependency itself is pinned via `uv.lock` like any other
package, which already satisfies "pinned" and "no runtime download."
`tree-sitter-language-pack` is a different, bundling package that
dynamically fetches/loads many languages; that's the thing the brief is
warning about, not tree-sitter usage in general.

Both `tree-sitter` and `tree-sitter-python` are MIT-licensed (confirmed via
`pip show`), satisfying the licence gate.

## Consequences

- No separate "vendored grammar" files exist in the repo (e.g. no checked-in
  `.wasm` or generated `parser.c`) -- the grammar lives inside the installed
  wheel, reproducible from `uv.lock`'s pinned version + hash.
- Adding a new language later (Java, Go, C/C++, JS/TS per the brief's file
  list) means adding its official `tree-sitter-<lang>` package the same
  way -- not adopting `tree-sitter-language-pack` for convenience, since
  that would reintroduce the exact runtime-fetch problem this ADR avoids.
- If a future language's grammar is *not* available as a normal PyPI wheel
  (e.g. only via `tree-sitter-language-pack` or a source-only grammar
  repo), that will need its own ADR describing how it's vendored (source
  checked in + built at install time, with a recorded SHA-256) rather than
  silently reintroducing a runtime download.
