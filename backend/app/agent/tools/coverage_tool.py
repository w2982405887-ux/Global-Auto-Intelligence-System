"""Tool: inspect_data_coverage — answers "why can't this compute?" questions.

Calls DataCoverageService (not raw SQL) to check database row counts
and known issues for a given powertrain/import_mode combination.
"""

from __future__ import annotations

from datetime import date

from langchain_core.tools import tool

from app.db.session import SessionLocal
from app.services.data_coverage_service import DataCoverageService


CONTRACT_VERSION = "1.0"
CONTRACT_STATUSES = {
    "VERIFIED",
    "CONDITIONAL",
    "NOT_INGESTED",
    "NO_MATCH",
    "NOT_APPLICABLE",
    "CLASSIFICATION_REQUIRED",
}


def _coverage_contract_status(report_status: str, item_status: str | None = None) -> str:
    status = (item_status or report_status or "").upper()
    if status == "FULL":
        return "VERIFIED"
    if status == "PARTIAL":
        return "CONDITIONAL"
    if status in {"MISSING", "INVALID_EFFECTIVE_DATE"}:
        return "NOT_INGESTED"
    if status in {"UNSUPPORTED", "NOT_APPLICABLE"}:
        return "NOT_APPLICABLE"
    if status == "NO_MATCH":
        return "NO_MATCH"
    return "CONDITIONAL"


def _coverage_item_contract(item: dict, *, destination: str, as_of: str) -> dict:
    item_status = _coverage_contract_status(
        str(item.get("status") or ""), str(item.get("status") or "")
    )
    component_code = item.get("component_code") or item.get("route_code")
    return {
        "destination_country": destination,
        "component_code": component_code,
        "as_of": as_of,
        "candidate_tariff_code": item.get("candidate_tariff_code"),
        "regime": item.get("regime"),
        "rate": item.get("rate"),
        "effective_period": {
            "from": item.get("effective_from") or as_of,
            "to": item.get("effective_to"),
        },
        "source": item.get("source"),
        "evidence": item.get("evidence") or [],
        "status": item_status,
        "reason": item.get("reason") or item.get("status"),
    }


@tool
def inspect_data_coverage(
    country: str = "MY",
    powertrain: str | None = None,
    import_mode: str | None = None,
    route_code: str | None = None,
    effective_date: str | date | None = None,
) -> dict:
    """Check which data combinations are available in the system.

    Use when a calculation returned no result or incomplete result, to understand WHY.
    The country is the destination country ISO-2 code (for example MY or VN).
    The service routes the request only to that country's configured data tables;
    it never silently falls back to Malaysia.
    Returns coverage status, missing dimensions, and known issues (including code bugs
    and data gaps that have been verified).

    powertrain can be None to check ALL powertrains.
    import_mode can be "CBU" or "CKD". None checks both.
    effective_date is an optional ISO date (YYYY-MM-DD); when omitted, today
    is used. It is passed to every country-specific coverage query.
    """
    db = SessionLocal()
    try:
        svc = DataCoverageService(db)
        report = svc.inspect(
            country_iso2=(country or "").strip().upper(),
            powertrain=powertrain,
            import_mode=import_mode,
            route_code=route_code,
            effective_date=effective_date,
        )

        # Keep the tool envelope stable for the agent, and make the requested
        # destination explicit even when a dimension is unsupported.
        destination = (country or "").strip().upper()
        effective_date_output = (
            effective_date.isoformat()
            if isinstance(effective_date, date)
            else date.today().isoformat()
            if effective_date is None
            else str(effective_date)
        )
        available = [
            {"country_iso2": destination, **item}
            if "country_iso2" not in item
            else item
            for item in report.available_dimensions
        ]
        missing = [
            {"country_iso2": destination, **item}
            if "country_iso2" not in item
            else item
            for item in report.missing_dimensions
        ]
        contract_items = [
            _coverage_item_contract(item, destination=destination, as_of=effective_date_output)
            for item in [*available, *missing]
        ]
        contract_status = _coverage_contract_status(report.coverage_status)
        return {
            # ``legacy_status`` keeps the old API meaning available to older
            # clients. ``status`` is now the shared strict result state.
            "status": contract_status,
            "legacy_status": "SUCCESS",
            "contract_status": contract_status,
            "result_contract": {
                "contract_version": CONTRACT_VERSION,
                "status": contract_status,
                "destination_country": destination,
                "route": route_code,
                "component_code": None,
                "as_of": effective_date_output,
                "candidates": contract_items,
                "missing_information": [
                    item.get("reason") or item.get("status")
                    for item in missing
                ],
                "selection_policy": "NO_AUTO_LOWEST_CANDIDATE",
            },
            "country_iso2": destination,
            "destination_country": destination,
            "effective_date": effective_date_output,
            "as_of": effective_date_output,
            "coverage_status": report.coverage_status,
            "available": available,
            "missing": missing,
            "known_issues": report.known_issues,
            "note": report.note,
        }

    finally:
        db.close()
