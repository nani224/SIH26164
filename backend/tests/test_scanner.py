from __future__ import annotations

from pathlib import Path

from api.models import Context, Criticality, Exposure, Policy
from engine.scanner import scan

_POLICY = Policy(
    id="p", name="p", crqcYears=10,
    default=Context(exposure=Exposure.INTERNAL, criticality=Criticality.MEDIUM, shelfLifeYears=5, migrationYears=3),
    contexts=[],
)


def test_scan_walks_directory_and_produces_findings(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('import hashlib\nhashlib.md5(b"x")\n')
    (tmp_path / "b.py").write_text("x = 1\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("import hashlib\nhashlib.sha1(b'y')\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.py").write_text('hashlib.md5(b"should-not-be-scanned")\n')

    result = scan(tmp_path, _POLICY)

    assert result.stats.files == 3  # a.py, b.py, sub/c.py -- not .git/ignored.py
    assert result.stats.errors == 0
    paths = {f.location.path for f in result.findings}
    assert paths == {"a.py", "sub/c.py"}
    for f in result.findings:
        assert f.risk is not None
        assert f.triage.status == "open"


def test_scan_single_file(tmp_path: Path) -> None:
    file_path = tmp_path / "only.py"
    file_path.write_text('rsa.generate_private_key(key_size=2048)\n')
    result = scan(file_path, _POLICY)
    assert result.stats.files == 1
    assert len(result.findings) == 1
    assert result.findings[0].location.path == "only.py"


def test_scan_empty_directory_produces_no_findings(tmp_path: Path) -> None:
    result = scan(tmp_path, _POLICY)
    assert result.findings == []
    assert result.stats.files == 0
