from __future__ import annotations

from pathlib import Path

import yaml
from openapi_spec_validator import validate

CONTRACT_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "openapi.yaml"


def test_contract_is_valid_openapi() -> None:
    with CONTRACT_PATH.open() as fh:
        spec = yaml.safe_load(fh)
    validate(spec)
