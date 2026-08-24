from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
TEMPLATE_PATH = OUTPUT_DIR / "malaysia_60_ccu_bom_input_template.json"
OPTIONS_PATH = OUTPUT_DIR / "malaysia_60_ccu_mapping_options.csv"
READINESS_PATH = OUTPUT_DIR / "malaysia_60_ccu_bom_readiness.json"


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


def fetch_ccus(session: Session) -> list[dict[str, object]]:
    rows = session.execute(
        text(
            """
            SELECT
              ccu.ccu_code,
              ccu.ccu_name_cn,
              ccu.ccu_name_en,
              ccu.vehicle_system,
              ccu.unit_level,
              ccu.required_input_fields,
              ccu.gri_2a_risk::text AS gri_2a_risk
            FROM customs.customs_classification_unit ccu
            WHERE ccu.record_status = 'ACTIVE'
              AND ccu.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
            ORDER BY ccu.ccu_code
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def fetch_mapping_options(session: Session) -> list[dict[str, object]]:
    rows = session.execute(
        text(
            """
            SELECT
              ccu.ccu_code,
              COALESCE(agreement.agreement_code, 'MFN') AS regime,
              mapping.mapping_code,
              candidate.candidate_rank,
              candidate.hs6_code,
              mapping.national_tariff_code,
              mapping.tariff_description,
              mapping.duty_rate,
              mapping.rate_type::text AS rate_type,
              mapping.additional_measure,
              mapping.eligibility_condition,
              mapping.verification_status::text AS verification_status,
              mapping.effective_from,
              mapping.effective_to,
              source.source_code,
              clause.locator_type,
              clause.locator_value
            FROM customs.tariff_mapping mapping
            JOIN ref.country country
              ON country.country_id = mapping.country_id
            JOIN customs.ccu_candidate_hs candidate
              ON candidate.candidate_id = mapping.candidate_id
            JOIN customs.customs_classification_unit ccu
              ON ccu.ccu_id = candidate.ccu_id
            JOIN evidence.source_clause clause
              ON clause.source_clause_id = mapping.source_clause_id
            JOIN evidence.source_document source
              ON source.source_document_id = clause.source_document_id
            LEFT JOIN ref.trade_agreement agreement
              ON agreement.trade_agreement_id = mapping.trade_agreement_id
            WHERE country.iso2 = 'MY'
              AND ccu.record_status = 'ACTIVE'
              AND ccu.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
              AND mapping.record_status = 'ACTIVE'
              AND mapping.effective_from <= DATE '2026-07-29'
              AND (
                mapping.effective_to IS NULL
                OR mapping.effective_to > DATE '2026-07-29'
              )
            ORDER BY
              ccu.ccu_code,
              COALESCE(agreement.agreement_code, 'MFN'),
              candidate.candidate_rank,
              mapping.mapping_code
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "as_tuple"):
        return str(value)
    return value


def sst_rate(measure: object) -> object:
    if not isinstance(measure, dict):
        return None
    value = measure.get("sst_display_rate")
    if value is None and isinstance(measure.get("sst"), dict):
        value = measure["sst"].get("displayed_rate")
    return json_value(value)


def build_package(
    ccus: list[dict[str, object]],
    options: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    by_ccu: dict[str, dict[str, list[dict[str, object]]]] = {}
    for option in options:
        ccu_code = str(option["ccu_code"])
        regime = str(option["regime"])
        by_ccu.setdefault(ccu_code, {}).setdefault(regime, []).append(option)

    items: list[dict[str, object]] = []
    blockers: list[dict[str, object]] = []
    regime_coverage = {"MFN": 0, "ACFTA": 0, "RCEP": 0}
    for ccu in ccus:
        code = str(ccu["ccu_code"])
        regimes = by_ccu.get(code, {})
        available: dict[str, list[dict[str, object]]] = {}
        for regime in ("MFN", "ACFTA", "RCEP"):
            regime_options = regimes.get(regime, [])
            if regime_options:
                regime_coverage[regime] += 1
            available[regime] = [
                {
                    "mapping_code": row["mapping_code"],
                    "candidate_rank": row["candidate_rank"],
                    "hs6_code": row["hs6_code"],
                    "national_tariff_code": row["national_tariff_code"],
                    "description": row["tariff_description"],
                    "duty_rate": json_value(row["duty_rate"]),
                    "sst_rate": sst_rate(row["additional_measure"]),
                    "verification_status": row["verification_status"],
                    "effective_from": json_value(row["effective_from"]),
                    "effective_to": json_value(row["effective_to"]),
                    "source_code": row["source_code"],
                    "source_locator": {
                        "type": row["locator_type"],
                        "value": row["locator_value"],
                    },
                    "eligibility_condition": row["eligibility_condition"],
                }
                for row in regime_options
            ]
        missing_regimes = [regime for regime, values in available.items() if not values]
        if missing_regimes:
            blockers.append(
                {
                    "ccu_code": code,
                    "field_path": "selected_mapping_codes",
                    "missing_regimes": missing_regimes,
                    "priority": "P0",
                    "action": "Complete official tariff mapping; do not guess a rate.",
                }
            )
        items.append(
            {
                "included": False,
                "ccu_code": code,
                "ccu_name_cn": ccu["ccu_name_cn"],
                "ccu_name_en": ccu["ccu_name_en"],
                "vehicle_system": ccu["vehicle_system"],
                "unit_level": ccu["unit_level"],
                "quantity": None,
                "unit_customs_value": None,
                "customs_value": None,
                "additional_landed_cost": None,
                "excise_amount": None,
                "enterprise_inputs_complete": False,
                "gri_2a_review_complete": False,
                "gri_2a_risk": ccu["gri_2a_risk"],
                "required_input_fields": ccu["required_input_fields"] or [],
                "selected_mapping_codes": {
                    "MFN": None,
                    "ACFTA": None,
                    "RCEP": None,
                },
                "mapping_options": available,
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    template = {
        "template_code": "TPL-MY-60-CCU-BOM-COMPARISON-V1",
        "template_version": 1,
        "generated_at": generated_at,
        "status": "INPUT_REQUIRED",
        "instructions": [
            "Set included=true only for CCUs present in the vehicle shipment.",
            "Enter quantity and unit_customs_value, or customs_value, in MYR.",
            "Explicitly select one mapping_code per requested regime; never infer from candidate rank.",
            "Set enterprise_inputs_complete only after all required_input_fields are evidenced.",
            "Set gri_2a_review_complete only after shipment-level whole-vehicle review.",
            "FTA proof and product-specific origin compliance must be confirmed separately.",
            "Leave unknown values null. Null values block calculation instead of becoming zero.",
        ],
        "scenario": {
            "scenario_name": None,
            "vehicle_model": None,
            "import_date": None,
            "currency_code": "MYR",
            "requested_regimes": ["MFN", "ACFTA", "RCEP"],
            "baseline_regime": "MFN",
            "allow_mfn_fallback": True,
        },
        "origin_eligibility": {
            "ACFTA": {
                "proof_valid": False,
                "origin_rule_compliance_confirmed": False,
                "nomenclature_correlation_confirmed": False,
                "enterprise_reviewed": False,
                "evidence_reference": None,
            },
            "RCEP": {
                "proof_valid": False,
                "origin_rule_compliance_confirmed": False,
                "nomenclature_correlation_confirmed": False,
                "enterprise_reviewed": False,
                "evidence_reference": None,
            },
        },
        "profit": {
            "sales_revenue": None,
            "non_import_costs": None,
            "recoverable_sst_fraction": None,
        },
        "items": items,
    }
    readiness = {
        "generated_at": generated_at,
        "active_ccu_count": len(ccus),
        "mapping_option_count": len(options),
        "regime_coverage": regime_coverage,
        "ccus_with_all_three_regimes": sum(
            1
            for item in items
            if all(item["mapping_options"][regime] for regime in ("MFN", "ACFTA", "RCEP"))
        ),
        "public_data_blockers": blockers,
        "enterprise_values_prefilled": 0,
        "calculation_ready": False,
        "calculation_block_reason": (
            "This is a use-time input template. No enterprise value, mapping selection, "
            "origin qualification or GRI 2(a) conclusion is prefilled."
        ),
    }
    return template, readiness


def write_options_csv(options: list[dict[str, object]]) -> None:
    fields = [
        "ccu_code",
        "regime",
        "mapping_code",
        "candidate_rank",
        "hs6_code",
        "national_tariff_code",
        "tariff_description",
        "duty_rate",
        "sst_rate",
        "verification_status",
        "effective_from",
        "effective_to",
        "source_code",
        "locator_type",
        "locator_value",
    ]
    with OPTIONS_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for option in options:
            row = {key: json_value(value) for key, value in option.items()}
            row["sst_rate"] = sst_rate(option["additional_measure"])
            writer.writerow(row)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        ccus = fetch_ccus(session)
        options = fetch_mapping_options(session)
    template, readiness = build_package(ccus, options)
    TEMPLATE_PATH.write_text(
        json.dumps(template, ensure_ascii=False, indent=2, default=json_value) + "\n",
        encoding="utf-8",
    )
    READINESS_PATH.write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2, default=json_value) + "\n",
        encoding="utf-8",
    )
    write_options_csv(options)
    print(json.dumps(readiness, ensure_ascii=False, indent=2))
    print(f"Template: {TEMPLATE_PATH}")
    print(f"Options: {OPTIONS_PATH}")
    print(f"Readiness: {READINESS_PATH}")


if __name__ == "__main__":
    main()
