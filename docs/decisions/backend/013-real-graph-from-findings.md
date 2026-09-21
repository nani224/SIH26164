# 013 — Build the Estate Graph from real findings, not a static stub

## Status

Accepted

## Context

During the whole-repo cross-track audit (frontend + backend + contract
reconciliation pass), `GET /scans/{scan_id}/graph` was found to always
return the same hand-built Phase 0 stub (`stub_data._GRAPH_NODES` /
`_GRAPH_EDGES`) regardless of `scan_id` — a scan with zero findings and a
scan with a thousand findings produced byte-identical graph responses.
This was never fixed when the engine was wired into `POST /scans` (Phase
3) or later phases; the graph endpoint was simply never revisited.

Separately, the contract audit found the frontend's `GraphNode` TypeScript
type (generated from a stale, never-actually-regenerated file) was missing
the `band`/`score` fields that `contracts/openapi.yaml` and the backend's
`GraphNode` Pydantic model already declared — so `frontend/src/app/graph/page.tsx`
had grown its own client-side reimplementation of the Mosca band
thresholds as a workaround. Once the frontend types are regenerated from
the real contract, `band`/`score` are available for real and that
workaround is unnecessary — but only if the backend actually populates
them from real data, which it didn't.

## Decision

Added `api/graph.py::build_graph(scan, findings) -> Graph`: a system root
node (the scan target) → one file node per distinct `location.path` →
one asset node per finding. `band`/`score` on root and file nodes are the
worst band / highest score among the findings they aggregate; `occurrences`
is a real count, not a fabricated one. `GET /scans/{scan_id}/graph` now
calls this against `store.list_findings(scan_id)` instead of returning the
canned stub. The now-dead `stub_data.default_graph_nodes/_edges` and their
backing fixture data were deleted.

## Consequences

- The Estate Graph screen now genuinely varies per scan (verified by
  `tests/test_graph_real.py`, including a same-corpus-different-scan
  diff test) instead of always drawing the same six-node example.
- The frontend no longer needs to reimplement band thresholds for graph
  nodes now that `band`/`score` are real (see the companion frontend fix
  in the same pass).
- No contract change was needed — `GraphNode.band`/`.score` already
  existed in `contracts/openapi.yaml`; only the backend's implementation
  and the frontend's stale generated types needed to catch up to it.
