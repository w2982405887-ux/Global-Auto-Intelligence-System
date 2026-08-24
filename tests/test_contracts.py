import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def test_enums_yaml_is_parseable() -> None:
    payload = yaml.safe_load((ROOT / "spec" / "enums.yaml").read_text(encoding="utf-8"))
    assert payload["spec_version"] == "0.1.0"
    assert payload["enums"]["requirement_type"]["values"] == [
        "MANDATORY",
        "INCENTIVE_ONLY",
        "RULING_RECOMMENDED",
    ]


def test_database_schema_yaml_is_parseable() -> None:
    payload = yaml.safe_load(
        (ROOT / "spec" / "database_schema.yaml").read_text(encoding="utf-8")
    )
    assert payload["database"] == "postgresql"
    assert "customs_classification_unit" in payload["schemas"]["customs"]["tables"]
    assert "decision_trace" in payload["schemas"]["audit"]["tables"]


def test_calculation_dsl_schema_is_valid() -> None:
    payload = json.loads(
        (ROOT / "spec" / "calculation_dsl.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(payload)


def test_enterprise_part_has_no_final_hs_column() -> None:
    payload = yaml.safe_load(
        (ROOT / "spec" / "database_schema.yaml").read_text(encoding="utf-8")
    )
    columns = payload["schemas"]["enterprise"]["tables"]["enterprise_part"]["columns"]
    forbidden = {"hs6_code", "national_tariff_code", "final_hs_code"}
    assert forbidden.isdisjoint(columns)


def test_tariff_mapping_has_one_origin_regime_field() -> None:
    payload = yaml.safe_load(
        (ROOT / "spec" / "database_schema.yaml").read_text(encoding="utf-8")
    )
    columns = payload["schemas"]["customs"]["tables"]["tariff_mapping"]["columns"]
    assert "origin_regime" in columns
    assert "mfn_rate" not in columns
    assert "rcep_rate" not in columns
    assert "acfta_rate" not in columns
