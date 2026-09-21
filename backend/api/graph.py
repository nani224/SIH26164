"""Builds the Estate Graph (system -> file -> asset) from a scan's real,
persisted findings. Previously `GET /scans/{id}/graph` always returned the
same Phase 0 canned stub regardless of which scan was requested -- see
docs/decisions/backend/013-real-graph-from-findings.md for why this exists.
"""

from __future__ import annotations

import hashlib

from api.models import Finding, Graph, GraphEdge, GraphNode, GraphNodeType, RiskBand, Scan

_BAND_RANK: dict[RiskBand, int] = {
    RiskBand.LOW: 0,
    RiskBand.MEDIUM: 1,
    RiskBand.HIGH: 2,
    RiskBand.CRITICAL: 3,
}


def _worst_band(bands: list[RiskBand]) -> RiskBand | None:
    if not bands:
        return None
    return max(bands, key=lambda b: _BAND_RANK[b])


def _file_node_id(path: str) -> str:
    return "file_" + hashlib.sha256(path.encode()).hexdigest()[:16]


def build_graph(scan: Scan, findings: list[Finding]) -> Graph:
    """Real per-scan graph: one root system node (the scan target), one file
    node per distinct `location.path`, one asset node per finding. Band/score
    on a file or root node is the worst band / highest score among the
    findings it aggregates -- never fabricated, always derived from the
    findings actually passed in.
    """
    root_id = "sys_root"
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    files: dict[str, list[Finding]] = {}
    for f in findings:
        files.setdefault(f.location.path, []).append(f)

    root_bands = [f.risk.band for f in findings if f.risk is not None]
    root_scores = [f.risk.score for f in findings if f.risk is not None]
    nodes.append(
        GraphNode(
            id=root_id,
            type=GraphNodeType.SYSTEM,
            label=scan.target,
            band=_worst_band(root_bands),
            score=max(root_scores) if root_scores else None,
            occurrences=len(findings),
            parentId=None,
        )
    )

    for path, file_findings in sorted(files.items()):
        file_id = _file_node_id(path)
        file_bands = [f.risk.band for f in file_findings if f.risk is not None]
        file_scores = [f.risk.score for f in file_findings if f.risk is not None]
        nodes.append(
            GraphNode(
                id=file_id,
                type=GraphNodeType.FILE,
                label=path,
                band=_worst_band(file_bands),
                score=max(file_scores) if file_scores else None,
                occurrences=len(file_findings),
                parentId=root_id,
            )
        )
        edges.append(GraphEdge(source=root_id, target=file_id))

        for f in file_findings:
            nodes.append(
                GraphNode(
                    id=f.id,
                    type=GraphNodeType.ASSET,
                    label=f.displayName,
                    band=f.risk.band if f.risk is not None else None,
                    score=f.risk.score if f.risk is not None else None,
                    occurrences=1,
                    parentId=file_id,
                )
            )
            edges.append(GraphEdge(source=file_id, target=f.id))

    return Graph(nodes=nodes, edges=edges)
