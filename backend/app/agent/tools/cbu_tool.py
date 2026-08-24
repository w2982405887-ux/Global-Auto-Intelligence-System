"""Tool: calculate_cbu_tax — wraps cbu_calculator.CbuCalculator."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal

from langchain_core.tools import tool

from app.agent.guard import sanitize_evidence_text, sanitize_tool_result_summary
from app.db.session import SessionLocal


SUPPORTED_COUNTRIES = {"MY", "VN"}
COUNTRY_ALIASES = {
    "MY": "MY",
    "MALAYSIA": "MY",
    "马来西亚": "MY",
    "VN": "VN",
    "VIETNAM": "VN",
    "越南": "VN",
}


def normalize_country(value: str | None) -> str:
    raw = (value or "MY").strip().upper()
    return COUNTRY_ALIASES.get(raw, raw)


def _unsupported_country_response(country: str, *, route: str, powertrain: str, effective_date: date) -> dict:
    """Return a safe routing result instead of silently using Malaysia."""

    code = normalize_country(country)
    return {
        "status": "UNSUPPORTED_COUNTRY",
        "applicability_status": "UNSUPPORTED_COUNTRY",
        "country": code,
        "country_iso2": code,
        "route": route,
        "powertrain": powertrain,
        "effective_date": str(effective_date),
        "supported_countries": sorted(SUPPORTED_COUNTRIES),
        "missing_information": ["country_route_configuration"],
        "error": f"当前工具尚未配置目的国 {code} 的 {route} 规则，未回退到马来西亚。",
    }


def _vietnam_classification_required(
    *,
    origin_country: str | None,
    powertrain: str,
    body_type: str,
    drive_type: str,
    effective_date: date,
) -> dict:
    """Expose the explicit Vietnam classification gate without guessing an HS code."""

    missing = ["cbu_tariff_code"]
    if not origin_country:
        missing.append("origin_country")
    if powertrain in {"ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV"}:
        missing.append("engine_displacement_cc")
    return {
        "status": "CLASSIFICATION_SELECTION_REQUIRED",
        "applicability_status": "CLASSIFICATION_SELECTION_REQUIRED",
        "country": "VN",
        "country_iso2": "VN",
        "route": "CBU",
        "powertrain": powertrain,
        "body_type": body_type,
        "drive_type": drive_type,
        "effective_date": str(effective_date),
        "origin_country": origin_country,
        "missing_information": list(dict.fromkeys(missing)),
        "classification_scope": {
            "status": "USER_SELECTED_TARIFF_CODE_REQUIRED",
            "required_facts": [
                "越南整车10位税号",
                "车辆用途与车身类别",
                "座位数",
                "动力类型",
                "发动机排量（混合动力/燃油车）",
            ],
            "note": "工具不会根据最低税率或模糊车型描述自动确认越南整车税号。",
        },
        "notes": ["请先选择或确认越南CBU整车10位税号，再计算进口关税、SCT和进口VAT。"],
    }


def _calculate_vietnam_cbu(
    *,
    origin_country: str | None,
    powertrain: str,
    displacement_cc: int | None,
    body_type: str,
    drive_type: str,
    effective_date: date,
    cbu_tariff_code: str,
) -> dict:
    """Run the existing Vietnam quick-estimate service through the agent tool."""

    from app.services.quick_estimate import QuickEstimateService

    db = SessionLocal()
    try:
        requested_origin = origin_country.upper() if origin_country else None
        result = QuickEstimateService(db).estimate(
            country_iso2="VN",
            origin_country_iso2=requested_origin or "UNKNOWN",
            effective_date=effective_date,
            path="CBU",
            powertrain=powertrain,
            cbu_tariff_code=cbu_tariff_code,
            ckd_declaration_mode="PARTS_BOM",
            ckd_tariff_code=None,
            customs_value_cbu=None,
            customs_value_ckd=None,
            ckd_component_tariff_codes={},
        )
        result = dict(result)
        # Keep request identity explicit.  The service's internal fallback
        # origin (UNKNOWN) must not look like a user-supplied origin.
        result["country"] = "VN"
        result["country_iso2"] = "VN"
        result["origin_country"] = requested_origin
        result["origin_country_iso2"] = requested_origin
        missing = list(result.get("missing_information") or [])
        if requested_origin is None:
            missing.append("origin_country")
        result["missing_information"] = list(dict.fromkeys(missing))
        fingerprint_src = json.dumps(
            {
                "country": "VN",
                "origin_country": requested_origin,
                "powertrain": powertrain,
                "displacement_cc": displacement_cc,
                "body_type": body_type,
                "drive_type": drive_type,
                "effective_date": str(effective_date),
                "cbu_tariff_code": cbu_tariff_code,
            },
            sort_keys=True,
        )
        result["_meta"] = {
            "run_id": str(uuid.uuid4())[:8],
            "task_id": "",
            "parameter_fingerprint": hashlib.sha256(fingerprint_src.encode()).hexdigest()[:16],
            "depends_on_fields": [
                "country", "origin_country", "powertrain", "body_type", "drive_type",
                "effective_date", "cbu_tariff_code",
            ],
        }
        return result
    finally:
        db.close()


def _classification_missing_information(powertrain: str, displacement_cc: int | None) -> list[str]:
    missing: list[str] = []
    if powertrain in {"ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV"} and displacement_cc is None:
        missing.append("engine_displacement_cc")
    if powertrain == "EREV":
        missing.extend([
            "ice_to_wheel_mechanical_connection",
            "ice_can_drive_wheels_in_any_mode",
            "ice_only_drives_generator",
            "electric_motor_only_wheel_torque_source",
            "customs_ruling_reference_if_claiming_870380",
        ])
    return missing


@tool
def calculate_cbu_tax(
    country: str = "MY",
    origin_country: str | None = None,
    powertrain: str = "BEV",
    displacement_cc: int | None = None,
    body_type: str = "SEDAN",
    drive_type: str = "4WD_AWD",
    effective_date: str | None = None,
    cbu_tariff_code: str | None = None,
) -> dict:
    """Calculate a configured-country CBU (Completely Built-Up) import tax scenario.

    When origin_country is None/unknown, returns CANDIDATE_REGIMES with MFN + available FTA rates.
    The user must confirm origin_country to get precise applicable rates.

    The current configured destinations are MY (Malaysia) and VN (Vietnam).
    Pass the destination country explicitly as ISO2 (MY or VN; common country
    names are also normalized); a named destination is never silently routed
    to Malaysia.  Vietnam requires an explicit 10-digit CBU
    tariff code because the tool must not guess a national classification.
    effective_date defaults to today.
    displacement_cc is required for ICE_GASOLINE, ICE_DIESEL, HEV, PHEV, EREV.
    """
    from app.services.cbu_calculator import CbuCalculator

    eff_date = date.today() if effective_date is None else date.fromisoformat(effective_date)
    country_code = normalize_country(country)

    if country_code not in SUPPORTED_COUNTRIES:
        return sanitize_tool_result_summary(
            _unsupported_country_response(country_code, route="CBU", powertrain=powertrain, effective_date=eff_date)
        )

    if country_code == "VN":
        if not cbu_tariff_code:
            return sanitize_tool_result_summary(
                _vietnam_classification_required(
                    origin_country=origin_country,
                    powertrain=powertrain,
                    body_type=body_type,
                    drive_type=drive_type,
                    effective_date=eff_date,
                )
            )
        return sanitize_tool_result_summary(
            _calculate_vietnam_cbu(
                origin_country=origin_country,
                powertrain=powertrain,
                displacement_cc=displacement_cc,
                body_type=body_type,
                drive_type=drive_type,
                effective_date=eff_date,
                cbu_tariff_code=cbu_tariff_code,
            )
        )

    db = SessionLocal()
    try:
        calc = CbuCalculator(db)
        result = calc.calculate(
            effective_date=eff_date,
            origin_country_iso2=origin_country or "CN",  # fallback for resolver
            powertrain=powertrain,
            displacement_cc=displacement_cc,
            body_type=body_type,
            drive_type=drive_type,
            customs_value=None,
        )

        run_id = str(uuid.uuid4())[:8]
        task_id = ""  # injected by caller

        # Build evidence refs
        evidence_refs = []
        for opt in result.import_duty_options:
            src = opt.source_reference
            if src and src.get("source_id"):
                evidence_refs.append({
                    "evidence_id": src.get("source_id", ""),
                    "source_type": "OFFICIAL_POLICY",
                    "document_title": src.get("document_title", ""),
                    "authority_name": src.get("authority_name", ""),
                    "locator": src.get("locator", {}).get("locator_value", ""),
                    "official_url": src.get("official_url"),
                })

        # Import duty options as structured output
        import_duty_options = []
        for opt in result.import_duty_options:
            import_duty_options.append({
                "regime": opt.regime,
                "agreement_code": opt.agreement_code,
                "national_tariff_code": opt.national_tariff_code,
                "tariff_description": opt.tariff_description,
                "rate": str(opt.rate) if opt.rate is not None else None,
                "per_100": str(opt.per_100) if opt.per_100 is not None else None,
                "eligibility_note": opt.eligibility_note,
            })

        # Combined results
        combined = []
        for cr in result.combined_results:
            combined.append({
                "regime_label": cr.regime_label,
                "agreement_code": cr.agreement_code,
                "import_duty_rate": str(cr.import_duty_rate) if cr.import_duty_rate else None,
                "import_duty_per_100": str(cr.import_duty_per_100) if cr.import_duty_per_100 else None,
                "excise_duty_rate": str(cr.excise_duty_rate) if cr.excise_duty_rate else None,
                "excise_duty_per_100": str(cr.excise_duty_per_100) if cr.excise_duty_per_100 else None,
                "sales_tax_rate": str(cr.sales_tax_rate) if cr.sales_tax_rate else None,
                "sales_tax_per_100": str(cr.sales_tax_per_100) if cr.sales_tax_per_100 else None,
                "total_per_100": str(cr.total_per_100) if cr.total_per_100 else None,
                "effective_tax_rate": str(cr.effective_tax_rate) if cr.effective_tax_rate else None,
                "is_complete": cr.is_complete,
                "unknown_items": cr.unknown_items,
            })

        output = {
            "applicability_status": "FULL_RESULT" if origin_country else "CANDIDATE_REGIMES",
            "country": country_code,
            "country_iso2": country_code,
            "powertrain": powertrain,
            "displacement_cc": displacement_cc,
            "body_type": body_type,
            "drive_type": drive_type,
            "effective_date": str(eff_date),
            "origin_country": origin_country,
            "hs_classification": (
                {
                    "national_tariff_code": result.hs_classification.national_tariff_code,
                    "tariff_description": result.hs_classification.tariff_description,
                }
                if result.hs_classification
                else None
            ),
            "import_duty_options": import_duty_options,
            "excise_duty": {
                "rate": str(result.excise_duty.applied_rate) if result.excise_duty.applied_rate else None,
                "statutory_rate": str(result.excise_duty.statutory_rate) if result.excise_duty.statutory_rate else None,
                "treatment": result.excise_duty.treatment,
                "note": sanitize_evidence_text(result.excise_duty.note),
            },
            "sales_tax": {
                "rate": str(result.sales_tax.applied_rate) if result.sales_tax.applied_rate else None,
                "statutory_rate": str(result.sales_tax.statutory_rate) if result.sales_tax.statutory_rate else None,
                "treatment": result.sales_tax.treatment,
                "note": sanitize_evidence_text(result.sales_tax.note),
            },
            "combined_results": combined,
            "notes": result.notes,
            "missing_information": ([] if origin_country else ["origin_country"]) + _classification_missing_information(powertrain, displacement_cc),
            "evidence_refs": evidence_refs,
        }

        # Compute parameter fingerprint for dedup / comparison
        fingerprint_src = json.dumps({
            "country": country_code, "powertrain": powertrain,
            "displacement_cc": displacement_cc, "body_type": body_type, "drive_type": drive_type, "origin": origin_country,
            "effective_date": str(eff_date), "import_mode": "CBU", "cbu_tariff_code": cbu_tariff_code,
        }, sort_keys=True)
        output["_meta"] = {
            "run_id": run_id,
            "task_id": task_id,
            "parameter_fingerprint": hashlib.sha256(fingerprint_src.encode()).hexdigest()[:16],
            "depends_on_fields": ["country", "origin_country", "powertrain", "displacement_cc", "body_type", "drive_type", "effective_date", "cbu_tariff_code"],
        }

        return sanitize_tool_result_summary(output)

    finally:
        db.close()
