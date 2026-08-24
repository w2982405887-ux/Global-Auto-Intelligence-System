from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import dotenv_values
from jsonschema import Draft202012Validator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.calculation_engine import (
    CalculationEngine,
    ComparisonRequest,
    ItemCostInput,
    PreferenceEligibility,
    ProfitInput,
)
from app.services.tariff_repository import TariffRepository

CCU_MAPPING_SELECTIONS = {
    "CCU-HV-BATTERY-PACK": {
        "MFN": "MAP-MY-PDK2025-8507603300-MFN",
        "ACFTA": "MAP-MY-ACFTA-2026-8507603300-CN",
        "RCEP": "MAP-MY-RCEP-2026-8507609000-CN",
    },
    "CCU-TRACTION-MOTOR": {
        "MFN": "MAP-MY-MFN-CCU-TRACTION-MOTOR-8501531000-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-TRACTION-MOTOR-8501531000",
        "RCEP": "MAP-MY-RCEP-2026-CCU-TRACTION-MOTOR-8501530000",
    },
    "CCU-TRACTION-INVERTER": {
        "MFN": "MAP-MY-MFN-CCU-TRACTION-INVERTER-8504404000-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-TRACTION-INVERTER-8504404000",
        "RCEP": "MAP-MY-RCEP-2026-CCU-TRACTION-INVERTER-8504404000",
    },
    "CCU-ONBOARD-CHARGER": {
        "MFN": "MAP-MY-MFN-CCU-ONBOARD-CHARGER-8504409000-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-ONBOARD-CHARGER-8504409000",
        "RCEP": "MAP-MY-RCEP-2026-CCU-ONBOARD-CHARGER-8504409000",
    },
    "CCU-DC-DC-CONVERTER": {
        "MFN": "MAP-MY-MFN-CCU-DC-DC-CONVERTER-8504409000-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-DC-DC-CONVERTER-8504409000",
        "RCEP": "MAP-MY-RCEP-2026-CCU-DC-DC-CONVERTER-8504409000",
    },
    "CCU-PASSENGER-BODY-SHELL": {
        "MFN": "MAP-MY-MFN-CCU-PASSENGER-BODY-SHELL-8707109000-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-PASSENGER-BODY-SHELL-8707109000",
        "RCEP": "MAP-MY-RCEP-2026-CCU-PASSENGER-BODY-SHELL-8707109000",
    },
    "CCU-ROAD-WHEEL": {
        "MFN": "MAP-MY-MFN-CCU-ROAD-WHEEL-8708703200-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-ROAD-WHEEL-8708703200",
        "RCEP": "MAP-MY-RCEP-2026-CCU-ROAD-WHEEL-8708703200",
    },
    "CCU-FOUNDATION-BRAKE": {
        "MFN": "MAP-MY-MFN-CCU-FOUNDATION-BRAKE-8708302900-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-FOUNDATION-BRAKE-8708302900",
        "RCEP": "MAP-MY-RCEP-2026-CCU-FOUNDATION-BRAKE-8708302900",
    },
    "CCU-STEERING-GEAR-COLUMN": {
        "MFN": "MAP-MY-MFN-CCU-STEERING-GEAR-COLUMN-8708949500-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-STEERING-GEAR-COLUMN-8708949500",
        "RCEP": "MAP-MY-RCEP-2026-CCU-STEERING-GEAR-COLUMN-8708949500",
    },
    "CCU-SHOCK-ABSORBER-STRUT": {
        "MFN": "MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708809200-R1",
        "ACFTA": "MAP-MY-ACFTA-2026-CCU-SHOCK-ABSORBER-STRUT-8708809200",
        "RCEP": "MAP-MY-RCEP-2026-CCU-SHOCK-ABSORBER-STRUT-8708809200",
    },
}


def database_url() -> str:
    values = dotenv_values(ROOT / ".env")
    user = values.get("POSTGRES_USER", "gais")
    password = values.get("POSTGRES_PASSWORD")
    database = values.get("POSTGRES_DB", "global_auto")
    port = values.get("POSTGRES_PORT", "5432")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is missing from the project .env")
    return (
        f"postgresql+psycopg://{quote_plus(str(user))}:"
        f"{quote_plus(str(password))}@127.0.0.1:{port}/{database}"
    )


def bom_values(session: Session) -> dict[str, Decimal]:
    rows = session.execute(
        text(
            """
            SELECT
              ccu.ccu_code,
              (line.quantity_per_vehicle * line.unit_value) AS customs_value
            FROM enterprise.bom_version bom
            JOIN enterprise.bom_line line
              ON line.bom_version_id = bom.bom_version_id
             AND line.included_flag
            JOIN enterprise.enterprise_part part
              ON part.enterprise_part_id = line.enterprise_part_id
            JOIN enterprise.enterprise_part_ccu_link link
              ON link.enterprise_part_id = part.enterprise_part_id
            JOIN customs.customs_classification_unit ccu
              ON ccu.ccu_id = link.ccu_id
            WHERE bom.bom_code = 'DEMO-MY-BEV-001-BOM'
              AND bom.version = 1
            ORDER BY ccu.ccu_code
            """
        )
    ).mappings()
    return {row["ccu_code"]: Decimal(str(row["customs_value"])) for row in rows}


def stored_totals(session: Session) -> dict[str, Decimal]:
    rows = session.execute(
        text(
            """
            SELECT run_code, gross_tax
            FROM calc.calculation_run
            WHERE run_code IN (
              'RUN-MY-GP-MFN',
              'RUN-MY-GP-ACFTA-ELIGIBLE-SIM',
              'RUN-MY-GP-RCEP-ELIGIBLE-SIM'
            )
            """
        )
    ).mappings()
    return {row["run_code"]: Decimal(str(row["gross_tax"])) for row in rows}


def validate_stored_dsl(session: Session) -> None:
    schema = json.loads(
        (ROOT / "spec" / "calculation_dsl.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    rows = session.execute(
        text(
            """
            SELECT scenario_code, calculation_dsl
            FROM rules.tax_scenario_model
            WHERE scenario_code LIKE 'SCN-MY-CKD-BEV-%-GOLDEN'
            ORDER BY scenario_code
            """
        )
    ).mappings()
    failures: list[str] = []
    for row in rows:
        errors = sorted(
            validator.iter_errors(row["calculation_dsl"]), key=lambda e: e.path
        )
        if errors:
            failures.append(f"{row['scenario_code']}: {errors[0].message}")
    if failures:
        raise AssertionError("Stored DSL validation failed: " + "; ".join(failures))


def build_request(
    items: tuple[ItemCostInput, ...],
    *,
    eligible: bool,
) -> ComparisonRequest:
    eligibility = {}
    if eligible:
        eligibility = {
            regime: PreferenceEligibility(
                regime=regime,
                proof_valid=True,
                origin_rule_compliance_confirmed=True,
                nomenclature_correlation_confirmed=True,
                enterprise_reviewed=False,
                simulation_only=True,
            )
            for regime in ("ACFTA", "RCEP")
        }
    return ComparisonRequest(
        country_iso2="MY",
        import_date=date(2026, 7, 28),
        currency_code="MYR",
        items=items,
        requested_regimes=("MFN", "ACFTA", "RCEP"),
        eligibility=eligibility,
        profit=ProfitInput(
            sales_revenue=Decimal(180000),
            non_import_costs=Decimal(20000),
            recoverable_sst_fraction=Decimal(0),
        ),
    )


def main() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        validate_stored_dsl(session)
        repository = TariffRepository(session)
        options = repository.list_effective_options(
            country_iso2="MY",
            ccu_codes=tuple(CCU_MAPPING_SELECTIONS),
            as_of=date(2026, 7, 28),
        )
        selected = repository.require_explicit_selection(
            options, CCU_MAPPING_SELECTIONS
        )
        values = bom_values(session)
        items = tuple(
            ItemCostInput(
                ccu_code=ccu_code,
                customs_value=values[ccu_code],
                selected_rates=selected[ccu_code],
                excise_amount=Decimal(0),
                enterprise_inputs_complete=False,
                gri_2a_review_complete=False,
            )
            for ccu_code in CCU_MAPPING_SELECTIONS
        )
        calculation_engine = CalculationEngine()
        blocked = calculation_engine.compare(build_request(items, eligible=False))
        eligible = calculation_engine.compare(build_request(items, eligible=True))
        blocked_by_regime = {
            result.requested_regime: result for result in blocked.scenarios
        }
        eligible_by_regime = {
            result.requested_regime: result for result in eligible.scenarios
        }
        expected = stored_totals(session)

        comparisons = {
            "MFN": (
                eligible_by_regime["MFN"].gross_import_tax,
                expected["RUN-MY-GP-MFN"],
            ),
            "ACFTA": (
                eligible_by_regime["ACFTA"].gross_import_tax,
                expected["RUN-MY-GP-ACFTA-ELIGIBLE-SIM"],
            ),
            "RCEP": (
                eligible_by_regime["RCEP"].gross_import_tax,
                expected["RUN-MY-GP-RCEP-ELIGIBLE-SIM"],
            ),
        }
        for regime, (python_total, sql_total) in comparisons.items():
            if python_total != sql_total:
                raise AssertionError(
                    f"{regime} mismatch: Python={python_total}, SQL={sql_total}"
                )
        for regime in ("ACFTA", "RCEP"):
            result = blocked_by_regime[regime]
            if not result.fallback_applied or result.applied_regime != "MFN":
                raise AssertionError(f"{regime} missing-evidence fallback failed")

        output = {
            "status": "PASS",
            "engine_version": calculation_engine.engine_version,
            "stored_dsl_contract": "PASS",
            "dynamic_ccu_count": len(items),
            "sql_python_tax_reconciliation": {
                regime: {
                    "python_gross_tax": str(python_total),
                    "sql_gross_tax": str(sql_total),
                    "match": python_total == sql_total,
                }
                for regime, (python_total, sql_total) in comparisons.items()
            },
            "missing_evidence_fallback": {
                regime: {
                    "requested": regime,
                    "applied": blocked_by_regime[regime].applied_regime,
                    "fallback": blocked_by_regime[regime].fallback_applied,
                }
                for regime in ("ACFTA", "RCEP")
            },
            "profit_comparison_demo": {
                regime: {
                    "total_cost": str(eligible_by_regime[regime].total_cost),
                    "gross_profit": str(eligible_by_regime[regime].gross_profit),
                    "gross_profit_margin": str(
                        eligible_by_regime[regime].gross_profit_margin
                    ),
                    "tax_saving_vs_mfn": str(
                        eligible_by_regime[regime].tax_saving_vs_baseline
                    ),
                    "profit_uplift_vs_mfn": str(
                        eligible_by_regime[regime].profit_uplift_vs_baseline
                    ),
                    "completeness": eligible_by_regime[regime].completeness,
                }
                for regime in ("MFN", "ACFTA", "RCEP")
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
