"""Tests for Phase 10 Air-Gap and Dependency Integrity."""

from __future__ import annotations

import ast

from scripts.verify_airgap import (
    ALLOWED_UNGUARDED_NETWORK_FILES,
    AirGapVisitor,
    verify_dependency_pins,
    verify_runtime_imports,
)


def test_runtime_airgap_no_banned_imports() -> None:
    violations = verify_runtime_imports()
    assert not violations, "\n".join(f"{v.file_path}:{v.line} - {v.detail}" for v in violations)


def test_all_dependencies_strictly_pinned() -> None:
    errors = verify_dependency_pins()
    assert not errors, "\n".join(errors)


def test_network_import_outside_probes_is_a_violation() -> None:
    """G4 regression: api/engine/scheduler must never make outbound connections,
    even though probes/ legitimately does. A network-capable import (httpx here)
    outside probes/ must be caught, not silently allowed the way it was before
    verify_runtime_imports() only ever scanned api/ and engine/."""
    from pathlib import Path

    tree = ast.parse("import httpx\n", filename="engine/fake_module.py")
    visitor = AirGapVisitor(Path("engine/fake_module.py"))
    visitor.visit(tree)
    assert visitor.network_imports == [(1, "httpx")]
    assert not visitor.violations  # httpx alone isn't in ALWAYS_BANNED_MODULES


def test_probes_network_import_requires_guard_or_allowlist() -> None:
    """G4 regression: a probes/ module using a network-capable import must
    either import probes.guard or be explicitly listed in
    ALLOWED_UNGUARDED_NETWORK_FILES with a reason -- reproduces exactly the
    two manual proofs run during the G4 pass (a stray httpx import in
    engine/scanner.py, and temporarily un-listing probes/webhook.py)."""
    from pathlib import Path

    guarded = ast.parse("from probes.guard import validate_probe_destination\nimport httpx\n")
    visitor = AirGapVisitor(Path("probes/fake_probe.py"))
    visitor.visit(guarded)
    assert visitor.imports_guard is True
    assert visitor.network_imports == [(2, "httpx")]

    unguarded = ast.parse("import httpx\n")
    visitor2 = AirGapVisitor(Path("probes/fake_unguarded.py"))
    visitor2.visit(unguarded)
    assert visitor2.imports_guard is False
    assert visitor2.network_imports == [(1, "httpx")]
    # This is exactly the shape verify_runtime_imports() flags as
    # UNGUARDED_PROBE_NETWORK_IMPORT unless the relative path is listed below.
    assert "probes/fake_unguarded.py" not in ALLOWED_UNGUARDED_NETWORK_FILES


def test_webhook_is_the_only_documented_unguarded_probe_exception() -> None:
    """Pins down exactly which file is allowed to skip the guard check, and
    why -- if this list grows, it should grow deliberately, not by accident."""
    assert set(ALLOWED_UNGUARDED_NETWORK_FILES) == {"probes/webhook.py"}
    assert len(ALLOWED_UNGUARDED_NETWORK_FILES["probes/webhook.py"]) > 0
