"""Contract-keeper check: diff the running FastAPI app's OpenAPI against
contracts/openapi.yaml.

This is a structural diff, not a byte-for-byte comparison -- FastAPI's
generator and a hand-authored spec will never match exactly (differing
$ref styles, ordering, etc). What must match:
  * every {path, method} in the hand-written contract exists in the
    generated schema, and vice versa (no drift in either direction);
  * every component schema name in the contract exists in the generated
    schema, and every field the contract declares is present in the
    generated schema's field set for that component (additive drift, e.g.
    FastAPI adding extra optional fields, is not itself a failure -- a
    contract field going missing is).

Exit code 0 = no drift. Exit code 1 = drift found, printed to stderr.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
CONTRACT_PATH = BACKEND_DIR.parent / "contracts" / "openapi.yaml"

JsonDict = dict[str, Any]


def _load_contract() -> JsonDict:
    with CONTRACT_PATH.open() as fh:
        loaded: JsonDict = yaml.safe_load(fh)
        return loaded


def _load_generated() -> JsonDict:
    sys.path.insert(0, str(BACKEND_DIR))
    from api.main import app  # noqa: PLC0415

    schema: JsonDict = app.openapi()
    return schema


def _path_method_set(spec: JsonDict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            if method in ("get", "post", "put", "patch", "delete"):
                out.add((path, method))
    return out


def _collect_schema_refs(node: object) -> set[str]:
    """Recursively collect '#/components/schemas/Name' refs anywhere under node."""
    refs: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.removeprefix("#/components/schemas/"))
        for value in node.values():
            refs |= _collect_schema_refs(value)
    elif isinstance(node, list):
        for item in node:
            refs |= _collect_schema_refs(item)
    return refs


def _reachable_schemas(contract: JsonDict) -> set[str]:
    """Schema names actually used by an operation (directly or transitively).

    Documentation-only schemas (e.g. ScanEvent, describing the WS payload
    shape for an endpoint OpenAPI 3.1 can't natively express as an
    operation) are deliberately excluded -- they can never appear in a
    FastAPI-generated schema because no route references them.
    """
    schemas = contract.get("components", {}).get("schemas", {})
    frontier = _collect_schema_refs(contract.get("paths", {}))
    seen: set[str] = set()
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in schemas:
            frontier |= _collect_schema_refs(schemas[name]) - seen
    return seen


def diff() -> list[str]:
    contract = _load_contract()
    generated = _load_generated()
    problems: list[str] = []

    contract_paths = _path_method_set(contract)
    generated_paths = _path_method_set(generated)

    missing_in_app = contract_paths - generated_paths
    extra_in_app = generated_paths - contract_paths
    for path, method in sorted(missing_in_app):
        problems.append(f"contract declares {method.upper()} {path}; app doesn't implement it")
    for path, method in sorted(extra_in_app):
        problems.append(f"app implements {method.upper()} {path} but it is not in the contract")

    contract_schemas = contract.get("components", {}).get("schemas", {})
    generated_schemas = generated.get("components", {}).get("schemas", {})
    for name in sorted(_reachable_schemas(contract)):
        schema = contract_schemas.get(name)
        if schema is None:
            continue
        if name not in generated_schemas:
            problems.append(f"schema '{name}' (used by an operation) has no generated counterpart")
            continue
        contract_fields = set(schema.get("properties", {}).keys())
        generated_fields = set(generated_schemas[name].get("properties", {}).keys())
        missing_fields = contract_fields - generated_fields
        for field in sorted(missing_fields):
            problems.append(f"schema '{name}' field '{field}' is missing from the generated schema")

        if "enum" in schema:
            generated_enum = set(generated_schemas[name].get("enum", []))
            missing_values = set(schema["enum"]) - generated_enum
            for value in sorted(missing_values, key=str):
                problems.append(f"schema '{name}' enum value '{value}' missing upstream")

    return problems


def main() -> int:
    problems = diff()
    if problems:
        print("Contract drift detected:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("No contract drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
