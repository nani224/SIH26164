"""scan(target, policy) -> ScanResult: the Phase 1 engine entry point.

Walks a directory for *.py files, runs the Python detector over each, and
attaches risk scoring + a recommendation to every raw Detection to produce
full api.models.Finding objects. Wired into POST /scans as of Phase 3.

Phase 4 adds an optional `on_event` callback so a caller can build a real
event log (stage transitions, per-surface progress counters, per-finding
events) from an actual scan run instead of faking one -- see
api/routes/scans.py and api/store.py. `scan()` is still fully synchronous;
the callback fires inline, not concurrently.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from api.models import (
    CryptoFunction,
    Family,
    Finding,
    FindingKind,
    FindingSource,
    Location,
    Policy,
    ScanStats,
    Surface,
    Triage,
)
from engine import binary, source_c, source_csharp, source_go, source_java, source_python, source_rust
from engine.factors import derive_risk
from engine.models import Detection, ScanResult, Span
from engine.recommend import recommend

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache"}
_C_FAMILY_EXTENSIONS = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"}
_BINARY_EXTENSIONS = {".bin", ".elf", ".so", ".exe", ".dll", ".sys", ".dylib", ".macho"}
_SOURCE_EXTENSIONS = {".py", ".go", ".java", ".rs", ".cs"} | _C_FAMILY_EXTENSIONS | _BINARY_EXTENSIONS
# Per-file cap: engine/ingest.py bounds the whole archive (5 GB uncompressed,
# 50k files), but nothing previously bounded a single pathological file --
# one huge source/binary file could still exhaust memory since read_bytes()
# loads it whole. 100 MB is generous for any single source/binary file this
# engine's detectors are meant to parse.
_MAX_FILE_BYTES = 100 * 1024 * 1024

_AES_SBOX_16 = bytes([
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
    0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
])


def _detect_binary(source: bytes, rel_path: str, artifact_hash: str | None = None) -> list[Detection]:
    if artifact_hash is None:
        artifact_hash = hashlib.sha256(source).hexdigest()
    detections: list[Detection] = []
    if _AES_SBOX_16 in source:
        offset = source.find(_AES_SBOX_16)
        span = Span(
            artifact_hash=artifact_hash,
            kind="byte",
            start=offset,
            end=offset + 256,
            producing_rule="binary.aes_sbox",
        )
        detections.append(
            Detection(
                kind=FindingKind.ALGORITHM,
                surface=Surface.BINARY,
                family=Family.AES,
                display_name="AES S-box constant in stripped binary",
                function=CryptoFunction.ENCRYPT,
                path=rel_path,
                line=None,
                symbol="AES_SBOX",
                snippet=f"AES S-box table found at byte offset 0x{offset:04x} (256-byte static substitution box)",
                source=FindingSource.BINARY_CONSTANT,
                confidence=0.95,
                key_size=128,
                spans=[span],
            )
        )
    return detections

# How often (in files processed) to emit a progress event for large scans,
# beyond the always-emitted first/last file -- keeps event volume bounded.
_PROGRESS_EVERY_N_FILES = 25

EventCallback = Callable[[str, dict[str, Any]], None]


def _iter_source_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix in _SOURCE_EXTENSIONS else []
    files: list[Path] = []
    extensions = tuple(f"*{ext}" for ext in sorted(_SOURCE_EXTENSIONS))
    for ext in extensions:
        files.extend(target.rglob(ext))
    return [
        p
        for p in sorted(files)
        if not any(part in _SKIP_DIRS for part in p.parts)
    ]


def _to_finding(detection: Detection, policy: Policy) -> Finding:
    offset = detection.spans[0].start if detection.spans else None
    finding = Finding(
        id=f"finding_{uuid.uuid4().hex[:12]}",
        kind=detection.kind,
        surface=detection.surface,
        family=detection.family,
        displayName=detection.display_name,
        keySize=detection.key_size,
        mode=detection.mode,
        curve=detection.curve,
        function=detection.function,
        location=Location(path=detection.path, line=detection.line, offset=offset, layer=None),
        symbol=detection.symbol,
        snippet=detection.snippet,
        source=detection.source,
        confidence=detection.confidence,
        risk=derive_risk(detection, policy),
        recommendation=recommend(detection),
        triage=Triage(),
    )
    object.__setattr__(finding, "spans", list(detection.spans))
    return finding


def scan(target: Path, policy: Policy, on_event: EventCallback | None = None) -> ScanResult:
    def emit(event_type: str, **payload: Any) -> None:
        if on_event is not None:
            on_event(event_type, payload)

    start = time.monotonic()
    files = _iter_source_files(target)
    emit("stage", stage="ingesting")

    total_bytes = 0
    errors = 0
    skipped_oversized = 0
    findings: list[Finding] = []
    by_surface: dict[str, int] = {}
    spans_by_finding: dict[str, list[Span]] = {}

    for i, file_path in enumerate(files, start=1):
        if i == 1:
            emit("stage", stage="scanning")
        try:
            if file_path.stat().st_size > _MAX_FILE_BYTES:
                skipped_oversized += 1
                continue
            source = file_path.read_bytes()
        except OSError:
            errors += 1
            continue
        total_bytes += len(source)
        rel_path = (
            file_path.relative_to(target).as_posix() if target.is_dir() else file_path.name
        )
        artifact_hash = hashlib.sha256(source).hexdigest()
        if file_path.suffix == ".go":
            detections = source_go.detect_code(source, rel_path, artifact_hash)
        elif file_path.suffix == ".java":
            detections = source_java.detect_code(source, rel_path, artifact_hash)
        elif file_path.suffix in _C_FAMILY_EXTENSIONS:
            detections = source_c.detect_code(source, rel_path, artifact_hash)
        elif file_path.suffix == ".rs":
            detections = source_rust.detect_code(source, rel_path, artifact_hash)
        elif file_path.suffix == ".cs":
            detections = source_csharp.detect_code(source, rel_path, artifact_hash)
        elif file_path.suffix in _BINARY_EXTENSIONS:
            detections = binary.scan_binary(source, rel_path, artifact_hash)
        else:
            detections = source_python.detect(rel_path, source, artifact_hash)
        for detection in detections:
            finding = _to_finding(detection, policy)
            findings.append(finding)
            spans_by_finding[finding.id] = list(detection.spans)
            by_surface[finding.surface.value] = by_surface.get(finding.surface.value, 0) + 1
            emit("finding", findingId=finding.id, family=finding.family.value if finding.family else None)

        if i == 1 or i == len(files) or i % _PROGRESS_EVERY_N_FILES == 0:
            emit("progress", filesProcessed=i, totalFiles=len(files), bySurface=dict(by_surface))

    emit("stage", stage="scoring")

    elapsed = max(time.monotonic() - start, 1e-9)
    stats = ScanStats(
        files=len(files),
        bytes=total_bytes,
        seconds=round(elapsed, 4),
        mbPerSec=round((total_bytes / 1_000_000) / elapsed, 4),
        errors=errors,
        skippedPrefilter=skipped_oversized,
    )
    return ScanResult(findings=findings, stats=stats, spans_by_finding=spans_by_finding)
