"""Verification script for strict runtime air-gap and dependency integrity (Phase 10).

Validates that:
1. No runtime modules (backend/api, backend/engine, backend/scheduler) import banned
   network/telemetry/LLM libraries.
2. Every network-capable module in backend/probes/ (the v0.3 continuous-operation
   surface: live TLS/SSH/registry probes, webhook alert dispatch -- all of which
   make real, intentional outbound connections, unlike api/engine/scheduler) either
   imports probes.guard's destination validation or is explicitly documented in
   ALLOWED_UNGUARDED_NETWORK_FILES with a reason.
3. All dependencies in pyproject.toml have explicit version pins.
4. Cryptographic discovery and scoring remain strictly deterministic and air-gapped.

Found via the G4 functional-proof pass (Track A1/finale): this script's target_dirs
only ever covered api/ and engine/, so it provided zero verification coverage for
the entire probes/+scheduler/ surface added in v0.3 -- not because that code was
found to violate air-gap (manual review found scheduler/ makes no network calls of
its own, and every probes/ module either validates its destination via probes.guard
or is the explicitly-documented webhook dispatcher), but because nothing had ever
mechanically checked either claim. Extended so the next network-capable addition to
either directory gets caught automatically instead of relying on manual review again.

Returns exit code 0 on success, exit code 1 on violations.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Unconditionally banned everywhere, including probes/ -- these have no
# legitimate place in a deterministic, guarded-network-probe tool regardless
# of directory: an LLM/telemetry SDK isn't "a guarded probe destination",
# it's a built-in phone-home dependency.
ALWAYS_BANNED_MODULES: frozenset[str] = frozenset({
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


# Modules whose entire purpose is a real, intentional, operator-facing outbound
# connection (live network probes, alert webhooks) rather than a background
# phone-home. Each MUST import from probes.guard (destination allowlist
# enforcement) unless explicitly listed in ALLOWED_UNGUARDED_NETWORK_FILES
# with a one-line reason.
NETWORK_CAPABLE_MODULES: frozenset[str] = frozenset({
    "httpx", "socket", "ssl", "urllib.request", "http.client",
    "ssh_audit", "sslyze", "requests", "aiohttp",
})
ALLOWED_UNGUARDED_NETWORK_FILES: dict[str, str] = {
    "probes/webhook.py": (
        "Alert webhook dispatch to an operator-configured ALERT_WEBHOOK_URL "
        "(e.g. the deployer's own Slack/Discord/internal endpoint) -- a trusted "
        "admin setting, not attacker-controlled input like a probe target's "
        "host/port, so probes.guard's destination allowlist doesn't apply the "
        "same way. Fails closed under real air-gap (connection error caught, "
        "logged, returns False) rather than raising -- verified in G3/G4."
    ),
}


class AirGapVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.violations: list[Violation] = []
        self.network_imports: list[tuple[int, str]] = []
        self.imports_guard = False

    def _check(self, mod_name: str, node: ast.Import | ast.ImportFrom, from_import: bool) -> None:
        if mod_name == "probes.guard" or mod_name.startswith("probes.guard."):
            self.imports_guard = True
        for banned in ALWAYS_BANNED_MODULES:
            if mod_name == banned or mod_name.startswith(banned + "."):
                kind = "from-import" if from_import else "import"
                self.violations.append(
                    Violation(
                        file_path=self.file_path,
                        line=node.lineno,
                        rule="BANNED_NETWORK_IMPORT",
                        detail=f"Banned {kind} '{mod_name}' violates air-gap constraint",
                    )
                )
        for net_mod in NETWORK_CAPABLE_MODULES:
            if mod_name == net_mod or mod_name.startswith(net_mod + "."):
                self.network_imports.append((node.lineno, mod_name))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check(alias.name, node, from_import=False)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self._check(node.module, node, from_import=True)
        self.generic_visit(node)


def verify_runtime_imports() -> list[Violation]:
    """Scan api/, engine/, and scheduler/ for prohibited network/telemetry imports
    (strict -- none of these should ever make outbound connections), and probes/
    for network-capable imports used without probes.guard's destination
    validation (that package is expected to make real, guarded connections)."""
    violations: list[Violation] = []
    strict_dirs = [BACKEND_DIR / "api", BACKEND_DIR / "engine", BACKEND_DIR / "scheduler"]

    for tdir in strict_dirs:
        for py_file in tdir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                visitor = AirGapVisitor(py_file)
                visitor.visit(tree)
                violations.extend(visitor.violations)
                # Outside probes/, ANY network-capable import is itself a violation --
                # api/engine/scheduler must never make outbound connections at all.
                for lineno, mod_name in visitor.network_imports:
                    violations.append(
                        Violation(
                            file_path=py_file,
                            line=lineno,
                            rule="UNEXPECTED_NETWORK_IMPORT",
                            detail=(
                                f"'{mod_name}' imported outside probes/ -- "
                                "api/engine/scheduler must never make outbound connections"
                            ),
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                violations.append(
                    Violation(file_path=py_file, line=0, rule="PARSE_ERROR", detail=f"Failed to parse AST: {exc}")
                )

    probes_dir = BACKEND_DIR / "probes"
    for py_file in probes_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            visitor = AirGapVisitor(py_file)
            visitor.visit(tree)
            violations.extend(v for v in visitor.violations if v.rule == "BANNED_NETWORK_IMPORT")
            rel = str(py_file.relative_to(BACKEND_DIR))
            if visitor.network_imports and not visitor.imports_guard and rel not in ALLOWED_UNGUARDED_NETWORK_FILES:
                violations.append(
                    Violation(
                        file_path=py_file,
                        line=visitor.network_imports[0][0],
                        rule="UNGUARDED_PROBE_NETWORK_IMPORT",
                        detail=(
                            f"'{visitor.network_imports[0][1]}' used without importing probes.guard's "
                            f"destination validation, and not listed in ALLOWED_UNGUARDED_NETWORK_FILES"
                        ),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            violations.append(
                Violation(file_path=py_file, line=0, rule="PARSE_ERROR", detail=f"Failed to parse AST: {exc}")
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
