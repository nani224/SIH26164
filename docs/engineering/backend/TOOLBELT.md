# ECDAT Backend — Toolbelt

Versions below are what `uv sync` resolved into `uv.lock` on 2026-09-17
(Python 3.12.3). Re-check this file whenever `uv.lock` changes materially.

| Tool | Version | Source | Licence | Why |
|---|---|---|---|---|
| uv | 0.8.17 | astral-sh/uv | MIT/Apache-2.0 | Dependency management + lockfile, per brief |
| Python | 3.12.3 | python.org | PSF | Brief-mandated runtime |
| fastapi | 0.141.1 | pypi | MIT | API framework, per brief |
| pydantic | 2.13.5 | pypi | MIT | Schema/validation, per brief |
| uvicorn | 0.53.0 | pypi | BSD-3-Clause | ASGI server, per brief |
| structlog | 26.1.0 | pypi | Apache-2.0/MIT | Structured logging, per brief |
| pyyaml | 6.0.3 | pypi | MIT | Parse contracts/openapi.yaml |
| pytest | 9.1.1 | pypi | MIT | Test runner, per brief |
| pytest-cov | 7.1.0 | pypi | MIT | Coverage gate |
| pytest-asyncio | 1.4.0 | pypi | Apache-2.0 | Async test support |
| httpx | 0.28.1 | pypi | BSD-3-Clause | FastAPI TestClient transport |
| websockets | 17.1 | pypi | BSD-3-Clause | WS TestClient support, manual WS smoke test |
| hypothesis | 6.168.0 | pypi | MPL-2.0 | Property tests for engine/risk.py, per brief |
| ruff | 0.16.8 | pypi | MIT | Lint, per brief |
| mypy | 2.3.1 | pypi | MIT | `--strict` typecheck, per brief |
| types-pyyaml | 6.0.12.20260906 | pypi | Apache-2.0 | mypy stubs |
| types-jsonschema | 4.26.0.20260518 | pypi | Apache-2.0 | mypy stubs |
| jsonschema | 4.26.0 | pypi | MIT | Validate stub CBOM against vendored CycloneDX 1.6 schema |
| openapi-spec-validator | 0.9.0 | pypi | Apache-2.0 | Validate contracts/openapi.yaml is real OpenAPI 3.1 |
| tree-sitter | 0.26.0 | pypi | MIT | AST parsing core, per brief |
| tree-sitter-python | 0.25.0 | pypi | MIT | Python grammar (compiled into wheel — see ADR 002, no separate vendoring needed) |
| tree-sitter-go | 0.25.0 | pypi | MIT | Go grammar for Phase 7 multi-language AST detection |
| sqlmodel | 0.0.42 | pypi | MIT | Persistence (scans/findings/policies/audit_log), per brief's stack |
| python-multipart | 0.0.32 | pypi | Apache-2.0 | Streaming multipart upload support for Phase 6 |

## Vendored spec files (build-time download, pinned by hash)

Fetched 2026-09-17 from `CycloneDX/specification` tag `1.6` via
`raw.githubusercontent.com` (through the environment's outbound proxy) and
committed at `backend/tests/fixtures/cyclonedx/`:

| File | SHA-256 |
|---|---|
| bom-1.6.schema.json | `3e92dddbc30cf7f6a02b80f0942b1a4cfd4fb1c26f1dfc4310afa9d613cafb93` |
| jsf-0.82.schema.json | `8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae` |

Used only by `tests/test_cbom.py` at test time (offline once vendored) —
never fetched at runtime, satisfying the air-gap rule.

## Deliberately not adopted

`tree-sitter-language-pack` — bundles many grammars but fetches them at
runtime on first use, violating the air-gap rule. Use official
per-language `tree-sitter-<lang>` PyPI packages instead (see ADR 002);
each ships its grammar compiled into the wheel, pinned via `uv.lock`, no
runtime fetch.

## Not yet adopted (Phase 3+ toolbelt, per the brief)

pyelftools, LIEF, pefile, liboqs/liboqs-python, cyclonedx-python-lib,
arq/Redis, bandit, semgrep, pip-audit, gitleaks, grype/trivy,
schemathesis, locust/k6, py-spy, bubblewrap/nsjail. None of these are used
yet; listed here so the next session doesn't have to re-derive the plan.
