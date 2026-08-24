"""Tool: search_policy_rules — wraps intelligence_repository.rules()."""

from __future__ import annotations

from datetime import date

from langchain_core.tools import tool

from app.agent.guard import sanitize_tool_result_summary
from app.db.session import SessionLocal
from app.services.intelligence_repository import IntelligenceRepository


SUPPORTED_COUNTRIES = {"MY", "VN"}
CONTRACT_VERSION = "1.0"
CONTRACT_STATUSES = {
    "VERIFIED",
    "CONDITIONAL",
    "NOT_INGESTED",
    "NO_MATCH",
    "NOT_APPLICABLE",
    "CLASSIFICATION_REQUIRED",
}
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


def _parse_as_of(value: str | date | None) -> date | None:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


def _rule_regime(rule: dict) -> str | None:
    code = str(rule.get("rule_code") or "").upper()
    for regime in ("ACFTA", "ATIGA", "RCEP", "MFN"):
        if regime in code:
            return regime
    return None


def _policy_item_contract(rule: dict, *, destination: str, as_of: date) -> dict:
    verification = str(rule.get("verification_status") or "VERIFIED").upper()
    status = "VERIFIED" if verification in {"VERIFIED", "RULING_CONFIRMED"} else "CONDITIONAL"
    if status not in CONTRACT_STATUSES:
        status = "CONDITIONAL"
    effective_from = rule.get("effective_from")
    effective_to = rule.get("effective_to")
    evidence = list(rule.get("evidence") or [])
    source = evidence[0] if evidence else None
    return {
        "destination_country": destination,
        "component_code": None,
        "as_of": as_of.isoformat(),
        "candidate_tariff_code": rule.get("candidate_tariff_code"),
        "regime": _rule_regime(rule),
        "rate": rule.get("rate"),
        "effective_period": {
            "from": str(effective_from) if effective_from else None,
            "to": str(effective_to) if effective_to else None,
        },
        "source": source,
        "evidence": evidence,
        "status": status,
        "rule_code": rule.get("rule_code"),
        "rule_name_cn": rule.get("rule_name_cn"),
    }


@tool
def search_policy_rules(
    country: str = "MY",
    keyword: str | None = None,
    domain: str | None = None,
    powertrain: str | None = None,
    as_of: str | None = None,
) -> dict:
    """Search configured-country automotive policy rules, FTA conditions, tax treatments, and approvals.

    Returns rules with: condition summaries, impact scope, formula descriptions, and evidence links.
    Use keyword for full-text search across rule names, codes, descriptions, and source documents.

    Current configured markets are MY (Malaysia) and VN (Vietnam).  Pass the
    destination explicitly as ISO2 when it is known (common names are
    normalized); this tool never substitutes MY
    for another requested country.
    """
    country_code = normalize_country(country)
    as_of_date = _parse_as_of(as_of)
    if as_of_date is None:
        return sanitize_tool_result_summary({
            "status": "NOT_INGESTED",
            "contract_status": "NOT_INGESTED",
            "country": country_code,
            "country_iso2": country_code,
            "destination_country": country_code,
            "as_of": str(as_of),
            "items": [],
            "missing_information": ["as_of必须是ISO日期（YYYY-MM-DD）"],
            "result_contract": {
                "contract_version": CONTRACT_VERSION,
                "status": "NOT_INGESTED",
                "destination_country": country_code,
                "component_code": None,
                "as_of": str(as_of),
                "candidates": [],
                "missing_information": ["as_of必须是ISO日期（YYYY-MM-DD）"],
            },
        })
    if country_code not in SUPPORTED_COUNTRIES:
        contract = {
            "contract_version": CONTRACT_VERSION,
            "status": "NOT_APPLICABLE",
            "destination_country": country_code,
            "component_code": None,
            "as_of": as_of_date.isoformat(),
            "candidates": [],
            "missing_information": ["country_route_configuration"],
        }
        return sanitize_tool_result_summary({
            "status": "UNSUPPORTED_COUNTRY",
            "contract_status": "NOT_APPLICABLE",
            "applicability_status": "UNSUPPORTED_COUNTRY",
            "country": country_code,
            "country_iso2": country_code,
            "destination_country": country_code,
            "as_of": as_of_date.isoformat(),
            "result_contract": contract,
            "supported_countries": sorted(SUPPORTED_COUNTRIES),
            "missing_information": ["country_route_configuration"],
            "error": f"当前政策工具尚未配置目的国 {country_code} 的规则，未回退到马来西亚。",
            "total": 0,
            "items": [],
        })
    db = SessionLocal()
    try:
        repo = IntelligenceRepository(db)
        result = repo.rules(
            iso2=country_code,
            as_of=as_of_date,
            domain=domain,
            status="VERIFIED",
            keyword=keyword,
            page=1,
            page_size=10,
        )

        items = []
        for rule in result.get("items", []):
            items.append({
                "rule_code": rule.get("rule_code", ""),
                "rule_name_cn": rule.get("rule_name_cn", ""),
                "rule_domain": rule.get("rule_domain", ""),
                "rule_content": rule.get("rule_content", ""),
                "condition_summary": rule.get("condition_summary", []),
                "formula_summary": rule.get("formula_summary", []),
                "impact_scope": rule.get("impact_scope", {}),
                "effective_from": str(rule.get("effective_from", "")),
                "effective_to": str(rule.get("effective_to", "")) if rule.get("effective_to") else None,
                "evidence": [
                    {
                        "document_title": ev.get("document_title", ""),
                        "authority_name": ev.get("authority_name", ""),
                        "evidence_role": ev.get("evidence_role", ""),
                        "locator_value": ev.get("locator_value", ""),
                        "clause_id": ev.get("clause_id", ""),
                    }
                    for ev in rule.get("evidence", [])
                ],
                "verification_status": rule.get("verification_status", "VERIFIED"),
            })

        # A zero result can mean either no rules are ingested or simply that
        # a keyword did not match. Probe the country only in this case so the
        # tool can distinguish NO_MATCH from NOT_INGESTED without claiming a
        # legal absence.
        no_match_probe_total = None
        if not items:
            probe = repo.rules(
                iso2=country_code,
                as_of=as_of_date,
                domain=domain,
                status=None,
                keyword=None,
                page=1,
                page_size=1,
            )
            no_match_probe_total = int(probe.get("total", 0))
        overall_status = (
            "NO_MATCH" if keyword and no_match_probe_total
            else "NOT_INGESTED" if not items
            else "VERIFIED"
        )
        contract_items = [
            _policy_item_contract(item, destination=country_code, as_of=as_of_date)
            for item in items
        ]
        return sanitize_tool_result_summary({
            "status": overall_status,
            "contract_status": overall_status,
            "total": result.get("total", 0),
            "page": result.get("page", 1),
            "country": country_code,
            "country_iso2": country_code,
            "destination_country": country_code,
            "as_of": as_of_date.isoformat(),
            "items": items,
            "result_contract": {
                "contract_version": CONTRACT_VERSION,
                "status": overall_status,
                "destination_country": country_code,
                "component_code": None,
                "as_of": as_of_date.isoformat(),
                "candidates": contract_items,
                "missing_information": (
                    [] if items else [
                        "当前目的国政策规则尚未入库或关键词无匹配；"
                        "当前结果不能用于判断目的国法规的实际内容。"
                    ]
                ),
            },
        })

    finally:
        db.close()
