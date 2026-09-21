# ECDAT Backend — Learnings

## 2026-09-17 — Phase 0

- The repo (`nani224/SIH26164`) was completely empty at session start (no
  branches, no commits, GitHub API `size: 0`) despite the task brief
  describing a substantial pre-existing engine. Always verify repo state
  independently (`git branch -r`, or the GitHub API) before trusting a
  brief's description of "what already exists" — briefs can describe an
  aspirational/template state rather than the actual one.
- CycloneDX 1.6's cryptographic-asset `cryptoProperties.assetType` enum is
  `algorithm | certificate | protocol | related-crypto-material` — note it's
  `related-crypto-material`, not `key`, for the "key" Finding.kind. Fetched
  and vendored the real schema (`bom-1.6.schema.json` +
  `jsf-0.82.schema.json`, draft-07 based) from
  `CycloneDX/specification@1.6` rather than guessing field names from
  memory — memory of the exact enum/field names was not reliable enough to
  skip this.
- FastAPI's `@app.on_event("startup")` is legacy; current guidance is the
  `lifespan` async context manager on `FastAPI(lifespan=...)`.
- Outbound HTTPS to raw.githubusercontent.com works through the
  environment's proxy without any special handling — useful for vendoring
  spec files with a recorded SHA-256.

## 2026-09-17 — Phase 1

- Current `tree-sitter` (0.26.0) + `tree-sitter-python` (0.25.0) API,
  verified by running it (training data on tree-sitter's Python bindings
  is stale — the API has changed across 0.2x releases):
  `tree_sitter.Language(tree_sitter_python.language())`,
  `tree_sitter.Parser(lang)`, `tree_sitter.Query(lang, query_str)`,
  `tree_sitter.QueryCursor(query).matches(root_node)` ->
  `list[tuple[int, dict[str, list[Node]]]]`. `Node.sexp()` no longer
  exists; walk `.children` manually instead.
- `keyword_argument` nodes expose `name`/`value` via `child_by_field_name`
  — confirmed empirically before relying on it in `engine/source_python.py`.
- Python's `fnmatch.fnmatch` treats `*` as `.*` (matches `/`), so
  `"**/prod/**"`-style globs from `Policy.contexts[].glob` work well
  enough without a purpose-built gitignore-style matcher — good enough for
  Phase 1, worth revisiting if a glob edge case bites later.
- Writing detection semantics (which `module.attr(...)` pairs matter) in
  plain Python after a single broad tree-sitter query, rather than
  encoding per-pattern logic into tree-sitter query predicates, kept the
  detector both easier to test and easier to extend — recommend the same
  approach for the next language.

## 2026-09-18 — Phase 2

- SQLite + SQLAlchemy/SQLModel silently strips `tzinfo` from stored
  `datetime` values, even with `Column(DateTime(timezone=True))` — that
  flag mostly matters for backends with a real `TIMESTAMPTZ` type
  (Postgres); SQLite has no native timezone-aware datetime storage.
  Verified empirically with a throwaway script before trusting it. Fix:
  reattach `tzinfo=UTC` on read (`api/db._as_utc()`), since every
  timestamp this app writes is already UTC by convention. Found this via
  the "boot a real server, restart it, check the data" manual
  verification step -- the automated test suite alone (in-memory SQLite,
  one shared connection for the whole session) didn't surface it until a
  regression test was added afterward targeting it directly. Lesson: for
  persistence work, a real restart-the-process check catches things an
  in-memory test DB can paper over.
- `create_engine("sqlite://", ...)` gives every new connection its own
  separate empty in-memory database unless you force a single shared
  connection via `poolclass=StaticPool` -- confirmed empirically before
  relying on it for the test suite's shared seeded database.
