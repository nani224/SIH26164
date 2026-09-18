"""Tests for Phase 10 Air-Gap and Dependency Integrity."""

from __future__ import annotations

from scripts.verify_airgap import verify_dependency_pins, verify_runtime_imports


def test_runtime_airgap_no_banned_imports() -> None:
    violations = verify_runtime_imports()
    assert not violations, "\n".join(f"{v.file_path}:{v.line} - {v.detail}" for v in violations)


def test_all_dependencies_strictly_pinned() -> None:
    errors = verify_dependency_pins()
    assert not errors, "\n".join(errors)
