from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import dotenv_values
from jsonschema import Draft202012Validator
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]


def database_url() -> str:
    values = dotenv_values(ROOT / ".env")
    password = values.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is missing")
    return (
        f"postgresql+psycopg://{quote_plus(str(values.get('POSTGRES_USER', 'gais')))}:"
        f"{quote_plus(str(password))}@{values.get('POSTGRES_HOST', '127.0.0.1')}:"
        f"{values.get('POSTGRES_PORT', '5432')}/{values.get('POSTGRES_DB', 'global_auto')}"
    )


def main() -> None:
    schema = json.loads(
        (ROOT / "spec" / "calculation_dsl.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    engine = create_engine(database_url(), pool_pre_ping=True)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT scenario_code, calculation_dsl
                FROM rules.tax_scenario_model
                WHERE scenario_code LIKE 'SCN-MY-CBU-%-2025'
                   OR scenario_code LIKE 'SCN-MY-LOCAL-%'
                   OR scenario_code LIKE 'SCN-MY-ROUTE-%'
                ORDER BY scenario_code
                """
            )
        ).mappings()
        failures: list[str] = []
        count = 0
        for row in rows:
            count += 1
            errors = sorted(
                validator.iter_errors(row["calculation_dsl"]),
                key=lambda error: list(error.path),
            )
            if errors:
                failures.append(f"{row['scenario_code']}: {errors[0].message}")
        if failures:
            raise AssertionError("; ".join(failures))
        if count < 11:
            raise AssertionError(f"Expected at least 11 scenarios, found {count}")
    print(f"Vehicle scenario DSL validation PASS: {count} scenarios")


if __name__ == "__main__":
    main()
