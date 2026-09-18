from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


def test_graph_reflects_real_scan_findings_not_a_static_stub(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "key = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    )

    resp = client.post("/api/v1/scans", json={"path": str(tmp_path)})
    assert resp.status_code == 201
    scan = resp.json()
    finding = client.get(f"/api/v1/scans/{scan['id']}/findings").json()["items"][0]

    graph = client.get(f"/api/v1/scans/{scan['id']}/graph").json()
    nodes_by_type: dict[str, list[dict[str, Any]]] = {}
    for n in graph["nodes"]:
        nodes_by_type.setdefault(n["type"], []).append(n)

    assert len(nodes_by_type["system"]) == 1
    root = nodes_by_type["system"][0]
    assert root["label"] == scan["target"]
    assert root["occurrences"] == 1
    assert root["band"] == finding["risk"]["band"]

    assert len(nodes_by_type["file"]) == 1
    file_node = nodes_by_type["file"][0]
    assert file_node["label"] == finding["location"]["path"]
    assert file_node["occurrences"] == 1

    assert len(nodes_by_type["asset"]) == 1
    asset_node = nodes_by_type["asset"][0]
    assert asset_node["id"] == finding["id"]
    assert asset_node["label"] == finding["displayName"]
    assert asset_node["score"] == finding["risk"]["score"]

    # root -> file, file -> asset
    edges = {(e["source"], e["target"]) for e in graph["edges"]}
    assert (root["id"], file_node["id"]) in edges
    assert (file_node["id"], asset_node["id"]) in edges


def test_graph_differs_between_two_distinct_scans(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("import hashlib\nhashlib.md5(b'x')\n")
    (tmp_path / "b.py").write_text("import hashlib\nhashlib.sha256(b'x')\n")

    scan_a = client.post("/api/v1/scans", json={"path": str(tmp_path / "a.py")}).json()
    scan_b = client.post("/api/v1/scans", json={"path": str(tmp_path / "b.py")}).json()
    assert scan_a["id"] != scan_b["id"]

    graph_a = client.get(f"/api/v1/scans/{scan_a['id']}/graph").json()
    graph_b = client.get(f"/api/v1/scans/{scan_b['id']}/graph").json()

    labels_a = {n["label"] for n in graph_a["nodes"] if n["type"] == "file"}
    labels_b = {n["label"] for n in graph_b["nodes"] if n["type"] == "file"}
    assert labels_a != labels_b


def test_graph_for_scan_with_zero_findings_has_only_root_node(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("nothing to see here\n")
    scan = client.post("/api/v1/scans", json={"path": str(tmp_path)}).json()

    graph = client.get(f"/api/v1/scans/{scan['id']}/graph").json()
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["type"] == "system"
    assert graph["nodes"][0]["occurrences"] == 0
    assert graph["edges"] == []
