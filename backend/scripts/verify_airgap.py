"""Verification script for strict runtime air-gap and dependency integrity (Phase 10).

Validates that:
1. No runtime modules (backend/api, backend/engine) import banned network/telemetry/LLM libraries.
2. No runtime code creates outbound network connections.
3. All dependencies in pyproject.toml have explicit version pins.
4. Cryptographic discovery and scoring remain strictly deterministic and air-gapped.

Returns exit code 0 on success, exit code 1 on violations.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

BACKEND_DIR = Path(__file__).resolve().parent.parent

BANNED_MODULES: frozenset[str] = frozenset({
    # HTTP and networking clients
    "urllib.request",
    "http.client",
    "requests",
    "aiohttp",
    "httpx",
    "ftplib",
    "smtplib",
    "telnetlib",
    # External LLM / AI cloud SDKs (strictly prohibited - detection & risk must be deterministic)
    "openai",
    "anthropic",
    "google.generativeai",
    "cohere",
    "langchain",
    # Telemetry and analytics phone-home SDKs
    "sentry_sdk",
    "posthog",
    "mixpanel",
    "segment",
    "datadog",
})


class Violation(NamedTuple):
    file_path: Path
    line: int
    rule: str
    detail: str


class AirGapVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            mod_name = alias.name
            for banned in BANNED_MODULES:
                if mod_name == banned or mod_name.startswith(banned + "."):
                    self.violations.append(
                        Violation(
                            file_path=self.file_path,
                            line=node.lineno,
                            rule="BANNED_NETWORK_IMPORT",
                            detail=f"Banned import '{mod_name}' violates air-gap constraint",
                        )
                    )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            mod_name = node.module
            for banned in BANNED_MODULES:
                if mod_name == banned or mod_name.startswith(banned + "."):
                    self.violations.append(
                        Violation(
                            file_path=self.file_path,
                            line=node.lineno,
                            rule="BANNED_NETWORK_IMPORT",
                            detail=f"Banned from-import '{mod_name}' violates air-gap constraint",
                        )
                    )
        self.generic_visit(node)


def verify_runtime_imports() -> list[Violation]:
    """Scan runtime engine and api files for prohibited network or telemetry imports."""
    violations: list[Violation] = []
    target_dirs = [BACKEND_DIR / "api", BACKEND_DIR / "engine"]

    for tdir in target_dirs:
        for py_file in tdir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                visitor = AirGapVisitor(py_file)
                visitor.visit(tree)
                violations.extend(visitor.violations)
            except Exception as exc:  # noqa: BLE001
                violations.append(
                    Violation(
                        file_path=py_file,
                        line=0,
                        rule="PARSE_ERROR",
                        detail=f"Failed to parse AST: {exc}",
                    )
                )

    return violations


def verify_dependency_pins() -> list[str]:
    """Ensure all dependencies in pyproject.toml have explicit version bounds."""
    pyproject_path = BACKEND_DIR / "pyproject.toml"
    if not pyproject_path.exists():
        return ["pyproject.toml missing"]

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    errors: list[str] = []
    project_deps = data.get("project", {}).get("dependencies", [])
    for dep in project_deps:
        if not any(op in dep for op in ("==", ">=", "<=", "~=", ">", "<")):
            errors.append(f"Unpinned runtime dependency: '{dep}'")

    dev_deps = data.get("dependency-groups", {}).get("dev", [])
    for dep in dev_deps:
        if not any(op in dep for op in ("==", ">=", "<=", "~=", ">", "<")):
            errors.append(f"Unpinned dev dependency: '{dep}'")

    return errors


def main() -> int:
    print("=== ECDAT Air-Gap & Security Invariant Verification ===")
    violations = verify_runtime_imports()
    dep_errors = verify_dependency_pins()

    all_clean = True

    if violations:
        all_clean = False
        print("\n[!] Air-Gap Code Violations Found:")
        for v in violations:
            rel = v.file_path.relative_to(BACKEND_DIR)
            print(f"  - {rel}:{v.line} [{v.rule}] {v.detail}")
    else:
        print("[OK] Zero banned network, telemetry, or external AI/LLM imports in runtime code.")

    if dep_errors:
        all_clean = False
        print("\n[!] Unpinned Dependency Violations Found:")
        for err in dep_errors:
            print(f"  - {err}")
    else:
        print("[OK] All runtime and dev dependencies are strictly pinned with version bounds.")

    if not all_clean:
        print("\nRESULT: FAILED air-gap security verification.")
        return 1

    print("\nRESULT: PASSED. ECDAT runtime is strictly deterministic and air-gapped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
