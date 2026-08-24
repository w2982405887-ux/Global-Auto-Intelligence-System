from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "outputs" / "malaysia_60_ccu_bom_input_template.json"
VALIDATION_PATH = ROOT / "outputs" / "malaysia_60_ccu_bom_validation.json"
PAYLOAD_PATH = ROOT / "outputs" / "malaysia_60_ccu_calculation_request.json"


def decimal_value(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def add_blocker(
    blockers: list[dict[str, str]],
    *,
    field_path: str,
    description: str,
    owner: str,
) -> None:
    blockers.append(
        {
            "priority": "P0",
            "field_path": field_path,
            "description": description,
            "owner": owner,
        }
    )


def compile_input(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    blockers: list[dict[str, str]] = []
    scenario = source.get("scenario") or {}
    regimes = scenario.get("requested_regimes") or []
    if not scenario.get("scenario_name"):
        add_blocker(
            blockers,
            field_path="scenario.scenario_name",
            description="Scenario name is required for audit identification.",
            owner="ENTERPRISE_PROJECT_OWNER",
        )
    if not scenario.get("vehicle_model"):
        add_blocker(
            blockers,
            field_path="scenario.vehicle_model",
            description="Vehicle model is required.",
            owner="ENTERPRISE_PROJECT_OWNER",
        )
    if not scenario.get("import_date"):
        add_blocker(
            blockers,
            field_path="scenario.import_date",
            description="Import date is required for version-effective tariff selection.",
            owner="ENTERPRISE_CUSTOMS_OWNER",
        )

    included = [item for item in source.get("items", []) if item.get("included") is True]
    if not included:
        add_blocker(
            blockers,
            field_path="items",
            description="At least one CCU must be explicitly included in the shipment.",
            owner="ENTERPRISE_BOM_OWNER",
        )

    compiled_items: list[dict[str, Any]] = []
    for item in included:
        code = item["ccu_code"]
        prefix = f"items[{code}]"
        quantity = decimal_value(item.get("quantity"))
        unit_value = decimal_value(item.get("unit_customs_value"))
        customs_value = decimal_value(item.get("customs_value"))
        if customs_value is None and quantity is not None and unit_value is not None:
            customs_value = quantity * unit_value
        if customs_value is None:
            add_blocker(
                blockers,
                field_path=f"{prefix}.customs_value",
                description="Provide customs_value or both quantity and unit_customs_value.",
                owner="ENTERPRISE_FINANCE_AND_CUSTOMS",
            )
        elif customs_value < 0:
            add_blocker(
                blockers,
                field_path=f"{prefix}.customs_value",
                description="Customs value cannot be negative.",
                owner="ENTERPRISE_FINANCE_AND_CUSTOMS",
            )

        additional_landed = decimal_value(item.get("additional_landed_cost"))
        if additional_landed is None:
            add_blocker(
                blockers,
                field_path=f"{prefix}.additional_landed_cost",
                description="Enter the additional landed cost; use zero only when confirmed.",
                owner="ENTERPRISE_LOGISTICS_AND_FINANCE",
            )
        if not item.get("enterprise_inputs_complete"):
            add_blocker(
                blockers,
                field_path=f"{prefix}.enterprise_inputs_complete",
                description="Required enterprise technical inputs have not been confirmed.",
                owner="ENTERPRISE_ENGINEERING_AND_CUSTOMS",
            )
        if not item.get("gri_2a_review_complete"):
            add_blocker(
                blockers,
                field_path=f"{prefix}.gri_2a_review_complete",
                description="Shipment-level GRI 2(a) review has not been completed.",
                owner="ENTERPRISE_CUSTOMS_OWNER",
            )

        selections: dict[str, str] = {}
        for regime in regimes:
            selected = (item.get("selected_mapping_codes") or {}).get(regime)
            candidates = {
                option.get("mapping_code")
                for option in (item.get("mapping_options") or {}).get(regime, [])
            }
            if not selected:
                add_blocker(
                    blockers,
                    field_path=f"{prefix}.selected_mapping_codes.{regime}",
                    description=f"Explicit {regime} tariff mapping selection is required.",
                    owner="ENTERPRISE_CUSTOMS_OWNER",
                )
            elif selected not in candidates:
                add_blocker(
                    blockers,
                    field_path=f"{prefix}.selected_mapping_codes.{regime}",
                    description=f"Selected {regime} mapping is not an available effective option.",
                    owner="ENTERPRISE_CUSTOMS_OWNER",
                )
            else:
                selections[regime] = selected

        compiled_items.append(
            {
                "ccu_code": code,
                "customs_value": str(customs_value) if customs_value is not None else None,
                "selected_mapping_codes": selections,
                "excise_amount": (
                    str(decimal_value(item.get("excise_amount")))
                    if decimal_value(item.get("excise_amount")) is not None
                    else None
                ),
                "additional_landed_cost": (
                    str(additional_landed) if additional_landed is not None else None
                ),
                "enterprise_inputs_complete": bool(item.get("enterprise_inputs_complete")),
                "gri_2a_review_complete": bool(item.get("gri_2a_review_complete")),
            }
        )

    eligibility: dict[str, dict[str, Any]] = {}
    origin = source.get("origin_eligibility") or {}
    for regime in regimes:
        if regime == scenario.get("baseline_regime", "MFN"):
            continue
        values = origin.get(regime) or {}
        for field_name in (
            "proof_valid",
            "origin_rule_compliance_confirmed",
            "nomenclature_correlation_confirmed",
            "enterprise_reviewed",
        ):
            if values.get(field_name) is not True:
                add_blocker(
                    blockers,
                    field_path=f"origin_eligibility.{regime}.{field_name}",
                    description=f"{regime} {field_name} must be explicitly confirmed.",
                    owner="ENTERPRISE_FTA_OWNER",
                )
        if not values.get("evidence_reference"):
            add_blocker(
                blockers,
                field_path=f"origin_eligibility.{regime}.evidence_reference",
                description=f"{regime} eligibility evidence reference is required.",
                owner="ENTERPRISE_FTA_OWNER",
            )
        eligibility[regime] = {
            "proof_valid": bool(values.get("proof_valid")),
            "origin_rule_compliance_confirmed": bool(
                values.get("origin_rule_compliance_confirmed")
            ),
            "nomenclature_correlation_confirmed": bool(
                values.get("nomenclature_correlation_confirmed")
            ),
            "enterprise_reviewed": bool(values.get("enterprise_reviewed")),
            "simulation_only": False,
        }

    profit = source.get("profit") or {}
    for field_name in ("sales_revenue", "non_import_costs", "recoverable_sst_fraction"):
        if decimal_value(profit.get(field_name)) is None:
            add_blocker(
                blockers,
                field_path=f"profit.{field_name}",
                description=f"{field_name} is required for profit comparison.",
                owner="ENTERPRISE_FINANCE_OWNER",
            )

    validation = {
        "template_code": source.get("template_code"),
        "included_ccu_count": len(included),
        "blocker_count": len(blockers),
        "calculation_ready": not blockers,
        "blockers": blockers,
    }
    if blockers:
        return validation, None

    payload = {
        "import_date": scenario["import_date"],
        "currency_code": scenario.get("currency_code", "MYR"),
        "requested_regimes": regimes,
        "baseline_regime": scenario.get("baseline_regime", "MFN"),
        "allow_mfn_fallback": bool(scenario.get("allow_mfn_fallback", True)),
        "items": compiled_items,
        "eligibility": eligibility,
        "profit": {
            "sales_revenue": str(decimal_value(profit["sales_revenue"])),
            "non_import_costs": str(decimal_value(profit["non_import_costs"])),
            "recoverable_sst_fraction": str(
                decimal_value(profit["recoverable_sst_fraction"])
            ),
        },
    }
    return validation, payload


def main() -> None:
    source = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    validation, payload = compile_input(source)
    VALIDATION_PATH.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if payload is None:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        print("Calculation request was not generated because required inputs are incomplete.")
        return
    PAYLOAD_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    print(f"Calculation request: {PAYLOAD_PATH}")


if __name__ == "__main__":
    main()
