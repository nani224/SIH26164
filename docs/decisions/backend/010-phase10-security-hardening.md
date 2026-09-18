# ADR 010: Phase 10 Security Hardening, Audit Log Hash-Chaining & Air-Gap Verification

Status: accepted
Date: 2026-09-18

## Context

SIH26164 imposes strict enterprise security mandates:
1. **Air-Gap Invariant**: Strictly zero outbound network connections, zero external telemetry or cloud analytics, zero unpinned dependencies, and zero non-deterministic LLM/ML usage.
2. **Audit Integrity**: Tamper-evident logging of all cryptographic mutations and triage decisions so unauthorized database modifications are mathematically detectable.
3. **Resource Protection**: Defense against denial-of-service and CPU exhaustion attacks on resource-intensive endpoints (such as archive upload, scanning, and rescoring).

## Decision

1. **Cryptographic Audit Log Hash Chaining (`backend/api/db.py`, `backend/api/db_models.py`)**:
   - Upgraded `AuditLogRecord` with `prev_hash` and `record_hash` fields.
   - Chained records sequentially starting from a deterministic genesis block (`"0" * 64`).
   - Recomputed SHA-256 hash across canonicalized record properties:
     `record_hash = sha256(action|entity_type|entity_id|canonical_detail_json|prev_hash)`.
   - Provided verification engine `verify_audit_log_integrity(session)` that traverses the entire log sequence, detecting record alterations, deletions, or out-of-order insertions.

2. **Sliding-Window Rate Limiting Middleware (`backend/api/rate_limiter.py`)**:
   - Implemented thread-safe `SlidingWindowRateLimiter` and `RateLimitMiddleware`.
   - Protects mutating API endpoints (`POST`, `PATCH`, `PUT`, `DELETE` under `/api/v1/`).
   - Emits standard HTTP 429 Too Many Requests responses with compliant headers (`Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).

3. **Automated Air-Gap Verification Engine (`backend/scripts/verify_airgap.py`)**:
   - AST analysis of all runtime code (`api/` and `engine/`) ensuring zero prohibited network packages (`urllib.request`, `requests`, `aiohttp`, `httpx`, `socket`), telemetry trackers, or external AI/LLM SDKs.
   - Enforces explicit version bounds on all dependencies in `pyproject.toml`.
   - Integrated directly into the automated test suite (`tests/test_airgap.py`).

## Consequences

- Full assurance of mathematical auditability and tamper-evidence.
- Protection against DoS and resource starvation.
- Rigorously enforced air-gap compliance with zero contract drift.
