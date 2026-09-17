"""scan(target, policy) -> ScanResult: the Phase 1 engine entry point.

Walks a directory for *.py files, runs the Python detector over each, and
attaches risk scoring + a recommendation to every raw Detection to produce
full api.models.Finding objects. Not wired into the API yet -- that's
Phase 3.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from api.models import Finding, Location, Policy, ScanStats, Triage
from engine import source_python
from engine.factors import derive_risk
from engine.models import Detection, ScanResult
from engine.recommend import recommend

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache"}


def _iter_python_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix == ".py" else []
    return [
        p
        for p in sorted(target.rglob("*.py"))
        if not any(part in _SKIP_DIRS for part in p.parts)
    ]


def _to_finding(detection: Detection, policy: Policy) -> Finding:
    return Finding(
        id=f"finding_{uuid.uuid4().hex[:12]}",
        kind=detection.kind,
        surface=detection.surface,
        family=detection.family,
        displayName=detection.display_name,
        keySize=detection.key_size,
        mode=detection.mode,
        curve=detection.curve,
        function=detection.function,
        location=Location(path=detection.path, line=detection.line, offset=None, layer=None),
        symbol=detection.symbol,
        snippet=detection.snippet,
        source=detection.source,
        confidence=detection.confidence,
        risk=derive_risk(detection, policy),
        recommendation=recommend(detection),
        triage=Triage(),
    )


def scan(target: Path, policy: Policy) -> ScanResult:
    start = time.monotonic()
    files = _iter_python_files(target)
    total_bytes = 0
    errors = 0
    findings: list[Finding] = []

    for file_path in files:
        try:
            source = file_path.read_bytes()
        except OSError:
            errors += 1
            continue
        total_bytes += len(source)
        rel_path = str(file_path.relative_to(target)) if target.is_dir() else file_path.name
        for detection in source_python.detect(rel_path, source):
            findings.append(_to_finding(detection, policy))

    elapsed = max(time.monotonic() - start, 1e-9)
    stats = ScanStats(
        files=len(files),
        bytes=total_bytes,
        seconds=round(elapsed, 4),
        mbPerSec=round((total_bytes / 1_000_000) / elapsed, 4),
        errors=errors,
        skippedPrefilter=0,
    )
    return ScanResult(findings=findings, stats=stats)
