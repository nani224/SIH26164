from __future__ import annotations

from pathlib import Path

import pytest

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


def test_scan_emits_real_events_via_on_event_callback(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('import hashlib\nhashlib.md5(b"x")\n')

    events: list[tuple[str, dict[str, object]]] = []
    result = scan(tmp_path, _POLICY, on_event=lambda t, p: events.append((t, p)))

    types = [t for t, _ in events]
    assert types[0] == "stage"
    assert ("stage", {"stage": "ingesting"}) in events
    assert ("stage", {"stage": "scanning"}) in events
    assert ("stage", {"stage": "scoring"}) in events
    assert types[-1] == "stage"  # scoring is emitted last

    finding_events = [p for t, p in events if t == "finding"]
    assert len(finding_events) == 1
    assert finding_events[0]["findingId"] == result.findings[0].id
    assert finding_events[0]["family"] == "MD5"

    progress_events = [p for t, p in events if t == "progress"]
    assert len(progress_events) == 1
    assert progress_events[0] == {"filesProcessed": 1, "totalFiles": 1, "bySurface": {"source": 1}}


def test_scan_without_callback_still_works(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('import hashlib\nhashlib.md5(b"x")\n')
    result = scan(tmp_path, _POLICY)  # no on_event -- must not raise
    assert len(result.findings) == 1


def test_scan_go_files(tmp_path: Path) -> None:
    (tmp_path / "main.go").write_text(
        'package main\nimport "crypto/sha256"\nfunc run() { _ = sha256.New() }\n'
    )
    result = scan(tmp_path, _POLICY)
    assert result.stats.files == 1
    assert len(result.findings) == 1
    assert result.findings[0].family == "SHA-2"
    assert result.findings[0].location.path == "main.go"


def test_scan_skips_oversized_file_without_reading_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A pathological single huge file must be skipped (counted in
    skippedPrefilter), not read whole into memory -- see engine.scanner's
    _MAX_FILE_BYTES. Uses a tiny cap via monkeypatch instead of writing a
    real 100 MB fixture file.
    """
    import engine.scanner as scanner_module

    monkeypatch.setattr(scanner_module, "_MAX_FILE_BYTES", 10)
    (tmp_path / "huge.py").write_text('import hashlib\nhashlib.md5(b"x")\n')  # well over 10 bytes
    (tmp_path / "small.py").write_text("x=1")  # under 10 bytes, still scanned

    result = scan(tmp_path, _POLICY)
    assert result.stats.skippedPrefilter == 1
    assert result.stats.errors == 0
    assert len(result.findings) == 0  # the only finding-bearing file was skipped
