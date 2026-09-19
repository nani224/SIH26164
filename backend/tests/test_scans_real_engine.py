from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_scan_of_directory_with_crypto_returns_scored_finding(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "key = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    )

    resp = client.post("/api/v1/scans", json={"path": str(tmp_path)})
    assert resp.status_code == 201
    scan = resp.json()
    assert scan["stats"]["files"] == 1
    assert sum(scan["bands"].values()) == 1

    findings = client.get(f"/api/v1/scans/{scan['id']}/findings").json()
    assert findings["total"] == 1
    finding = findings["items"][0]
    assert finding["family"] == "RSA"
    assert finding["keySize"] == 2048
    assert finding["risk"]["score"] > 0
    assert finding["risk"]["band"] in ("critical", "high", "medium", "low")
    assert finding["risk"]["V"] == 1.0  # RSA is Shor-vulnerable regardless of context


def test_real_rsa_keygen_scan_triggers_private_key_floor(client: TestClient, tmp_path: Path) -> None:
    """Real, end-to-end regression for the "unencrypted private key outside
    a test path -> score >= 90" domain rule (root CLAUDE.md) -- goes through
    an actual scan + the real tree-sitter detector, not a hand-built
    Detection, since a hand-built one can claim any kind/function combo
    whether or not any real detector ever produces it.
    """
    (tmp_path / "keyservice.py").write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "key = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    )

    resp = client.post("/api/v1/scans", json={"path": str(tmp_path)})
    assert resp.status_code == 201
    scan = resp.json()

    findings = client.get(f"/api/v1/scans/{scan['id']}/findings").json()
    finding = findings["items"][0]
    assert finding["family"] == "RSA"
    assert finding["function"] == "keygen"
    # Default policy's default context is exposure=internal (not test) --
    # see api/stub_data.DEFAULT_POLICY -- so the floor must apply.
    assert finding["risk"]["score"] >= 90.0
    assert finding["risk"]["band"] == "critical"


def test_scan_of_directory_with_no_python_files_is_empty(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("nothing to see here\n")

    resp = client.post("/api/v1/scans", json={"path": str(tmp_path)})
    assert resp.status_code == 201
    scan = resp.json()
    assert scan["stats"]["files"] == 0
    assert scan["bands"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}


def test_scan_of_single_file(client: TestClient, tmp_path: Path) -> None:
    file_path = tmp_path / "hash.py"
    file_path.write_text('import hashlib\nhashlib.sha1(b"x")\n')

    resp = client.post("/api/v1/scans", json={"path": str(file_path)})
    assert resp.status_code == 201
    scan = resp.json()
    assert scan["stats"]["files"] == 1

    findings = client.get(f"/api/v1/scans/{scan['id']}/findings").json()
    assert findings["total"] == 1
    assert findings["items"][0]["family"] == "SHA-1"


def test_scan_with_crqc_years_override_affects_score(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "key = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    )

    short_horizon = client.post("/api/v1/scans", json={"path": str(tmp_path), "crqcYears": 3}).json()
    long_horizon = client.post("/api/v1/scans", json={"path": str(tmp_path), "crqcYears": 40}).json()

    assert short_horizon["crqcYears"] == 3
    assert long_horizon["crqcYears"] == 40

    short_findings = client.get(f"/api/v1/scans/{short_horizon['id']}/findings").json()["items"]
    long_findings = client.get(f"/api/v1/scans/{long_horizon['id']}/findings").json()["items"]
    assert short_findings[0]["risk"]["score"] >= long_findings[0]["risk"]["score"]
