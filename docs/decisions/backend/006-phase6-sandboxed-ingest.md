# ADR 006: Phase 6 Sandboxed Streaming Ingest & Archive Traversal Protection

Status: accepted
Date: 2026-09-18

## Context

The SIH26164 brief requires support for ingestion of archive bundles (`.zip`, `.tar`, `.tar.gz`, `.tgz`) up to 2GB in size, while ensuring strict isolation against malicious attacks such as Zip-Slip path traversals, malicious symbolic links escaping sandbox roots, and decompression bombs (both file count explosions and compression ratio bombs).

## Decision

1. **Contract Extension (`contracts/openapi.yaml`)**:
   - Added `POST /api/v1/scans/upload` accepting `multipart/form-data` with `file`, optional `policyId`, and `crqcYears`.
   - Added `bundleHash` (SHA-256 hex string) to `Scan` schema and persistence models (`ScanRecord`).
   - Defined `BadRequest` error response component.

2. **Sandboxed Ingest Engine (`backend/engine/ingest.py`)**:
   - **Streaming SHA-256 Hashing**: Streams upload chunks through SHA-256 hasher and writes directly to disk in 64KB increments, enforcing the 2GB upload limit immediately without loading archives into memory.
   - **Pre-Extraction Path Verification (Zip-Slip Defense)**: Pre-scans all archive entries before writing. Disallows entries starting with `/`, `\`, Windows drive letters, or containing `..`. Computes canonical target path and asserts `target.is_relative_to(sandbox_root)`.
   - **Symlink Traversal Defense**: Inspects symlink targets inside zip and tar archives. Disallows any symlink resolving outside the isolated sandbox directory or targeting system paths.
   - **Decompression Bomb Defense**: Enforces hard limits on total uncompressed bytes (5GB ceiling) and total file count (50,000 files).

3. **Isolated Temporary Extraction**:
   - Extracts into an ephemeral `tempfile.TemporaryDirectory()`.
   - Runs `engine.scanner.scan()` on the isolated directory.
   - Returns the created `Scan` and cleanly disposes of the temporary sandbox upon completion.

4. **Automated Hostile Test Suite (`backend/tests/test_ingest_sandbox.py` and `test_scans_upload.py`)**:
   - Verifies rejection of Zip-Slip archives (`../../evil.py`).
   - Verifies rejection of malicious symlinks (`../../outside`).
   - Verifies decompression bomb file count enforcement.
   - Verifies valid zip and tar.gz upload, SHA-256 bundle hash generation, and end-to-end AST scan findings.

## Consequences

- **Air-Gapped & Offline**: Standard library `zipfile` and `tarfile` combined with `python-multipart` handle all archive processing with zero runtime outbound network dependencies.
- **Contract Conformance**: Fully verified with `scripts/contract_diff.py` and OpenAPI 3.1 validator.
