"""Tests for the CI-facing scan+gate+report script (M5, Track CC)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.ci_scan import main


@pytest.fixture
def policy_file(tmp_path: Path) -> Path:
    p = tmp_path / "policy.yml"
    p.write_text(
        "crqcYears: 10\n"
        "default:\n"
        "  exposure: internal\n"
        "  criticality: medium\n"
        "  shelfLifeYears: 5\n"
        "  migrationYears: 3\n"
        "contexts: []\n"
        "gate:\n"
        "  failOnBand: critical\n"
        "  precisionFloor: 0.95\n"
    )
    return p


def test_ci_scan_blocks_on_critical_finding(tmp_path: Path, policy_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src"
    target.mkdir()
    (target / "app.py").write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n"
        "rsa.generate_private_key(public_exponent=65537, key_size=1024)\n"
    )
    json_out = tmp_path / "findings.json"
    monkeypatch.setattr(
        "sys.argv",
        ["ci_scan.py", "--path", str(target), "--policy", str(policy_file), "--json-output", str(json_out)],
    )
    exit_code = main()
    assert exit_code == 1
    payload = json.loads(json_out.read_text())
    assert payload["passed"] is False
    assert payload["blockingCount"] == 1
    assert payload["findings"][0]["family"] == "RSA"


def test_ci_scan_passes_with_no_findings(tmp_path: Path, policy_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src"
    target.mkdir()
    (target / "app.py").write_text("x = 1\n")
    monkeypatch.setattr("sys.argv", ["ci_scan.py", "--path", str(target), "--policy", str(policy_file)])
    assert main() == 0


def test_ci_scan_passes_when_findings_are_below_gate_band(
    tmp_path: Path, policy_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "src"
    target.mkdir()
    (target / "app.py").write_text('import hashlib\nhashlib.sha256(b"x")\n')
    monkeypatch.setattr("sys.argv", ["ci_scan.py", "--path", str(target), "--policy", str(policy_file)])
    assert main() == 0


def test_ci_scan_writes_markdown_table(tmp_path: Path, policy_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src"
    target.mkdir()
    (target / "app.py").write_text('import hashlib\nhashlib.md5(b"x")\n')
    md_out = tmp_path / "findings.md"
    monkeypatch.setattr(
        "sys.argv",
        ["ci_scan.py", "--path", str(target), "--policy", str(policy_file), "--markdown-output", str(md_out)],
    )
    main()
    content = md_out.read_text()
    assert "MD5" in content
    assert "ECDAT scan" in content
