import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class CalculationDslValidator:
    """Validate a scenario DSL; this class does not execute expressions."""

    def __init__(self, schema_path: Path) -> None:
        self._schema_path = schema_path
        self._schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(self._schema)
        self._validator = Draft202012Validator(self._schema)

    def validate(self, payload: dict[str, Any]) -> None:
        self._validator.validate(payload)
