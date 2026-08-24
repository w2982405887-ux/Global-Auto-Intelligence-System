"""Tool: calculate_ckd_tax — wraps ckd_calculator.CkdCalculator."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import text

from app.agent.guard import sanitize_evidence_text, sanitize_tool_result_summary
from app.db.session import SessionLocal


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


def _contract_status_from_row(row: dict[str, Any]) -> str:
    """Map database/legacy candidate states to the tool contract.

    ``CANDIDATE`` and ``UNVERIFIED`` are deliberately conditional: a rate
    that has not been reviewed, or that still depends on origin evidence, is
    not a verified legal result.  A missing rate is a data-ingestion issue,
    not evidence that the destination has no such legal rate.
    """

    if not row.get("candidate_tariff_code") and not row.get("national_tariff_code"):
        return "NOT_INGESTED"
    if row.get("rate") is None and row.get("duty_rate") is None:
        return "NOT_INGESTED"
    verification = str(
        row.get("verification_status")
        or row.get("mapping_verification_status")
        or row.get("candidate_verification_status")
        or ""
    ).upper()
    if verification in {"VERIFIED", "RULING_CONFIRMED"} and not row.get("eligibility_condition"):
        return "VERIFIED"
    return "CONDITIONAL"


def _candidate_source(row: dict[str, Any]) -> dict[str, Any] | None:
    """Return source metadata without fabricating a source when absent."""

    source_code = row.get("source_code") or row.get("source_id")
    url = row.get("canonical_url") or row.get("official_url")
    locator = row.get("source_locator") or row.get("locator_value")
    if not any((source_code, url, locator)):
        return None
    return {
        "source_code": str(source_code) if source_code is not None else None,
        "official_url": str(url) if url else None,
        "locator": str(locator) if locator else None,
        "document_title": row.get("document_title"),
        "authority_name": row.get("authority_name"),
    }


def _candidate_contract(
    *,
    destination_country: str,
    component_code: str | None,
    as_of: date,
    row: dict[str, Any],
    regime: str | None = None,
    status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Normalize one tariff candidate into the shared agent contract."""

    tariff_code = row.get("candidate_tariff_code") or row.get("national_tariff_code")
    row_regime = regime or row.get("regime") or row.get("agreement") or row.get("agreement_code")
    row_regime = str(row_regime or "MFN").upper()
    raw_rate = row.get("rate") if "rate" in row else row.get("duty_rate")
    if raw_rate is None:
        raw_rate = row.get("import_duty_rate")
    rate_value = str(raw_rate) if raw_rate is not None else None
    effective_from = row.get("effective_from")
    effective_to = row.get("effective_to")
    status_value = status or _contract_status_from_row({**row, "candidate_tariff_code": tariff_code, "rate": raw_rate})
    if status_value not in CONTRACT_STATUSES:
        status_value = "CONDITIONAL"
    source = _candidate_source(row)
    evidence = list(row.get("evidence") or [])
    if source and not evidence:
        evidence = [{
            "source_code": source.get("source_code"),
            "official_url": source.get("official_url"),
            "locator": source.get("locator"),
        }]
    item = {
        "destination_country": destination_country,
        "component_code": component_code,
        "as_of": as_of.isoformat(),
        "candidate_tariff_code": str(tariff_code) if tariff_code else None,
        # Keep the legacy name too; older callers use it directly.
        "national_tariff_code": str(tariff_code) if tariff_code else None,
        "regime": row_regime,
        "rate": rate_value,
        "effective_period": {
            "from": str(effective_from) if effective_from else None,
            "to": str(effective_to) if effective_to else None,
        },
        "effective_from": str(effective_from) if effective_from else None,
        "effective_to": str(effective_to) if effective_to else None,
        "source": source,
        "evidence": evidence,
        "status": status_value,
        "description": row.get("tariff_description"),
    }
    if reason:
        item["reason"] = reason
    if row.get("eligibility_condition"):
        item["eligibility_condition"] = row.get("eligibility_condition")
    return item


def _expected_vietnam_regimes(origin_country: str | None) -> list[str]:
    """Return applicable comparison regimes; MFN is always a baseline."""

    origin = (origin_country or "").upper()
    regimes = ["MFN"]
    if origin in {"CN", "BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"}:
        regimes.append("ACFTA")
        if origin != "CN":
            regimes.append("ATIGA")
        regimes.append("RCEP")
    elif origin in {"AU", "JP", "KR", "NZ"}:
        regimes.append("RCEP")
    return regimes


def _empty_candidate_contract(
    *,
    destination_country: str,
    component_code: str | None,
    as_of: date,
    regime: str,
    status: str = "NOT_INGESTED",
    reason: str,
) -> dict[str, Any]:
    return _candidate_contract(
        destination_country=destination_country,
        component_code=component_code,
        as_of=as_of,
        row={},
        regime=regime,
        status=status,
        reason=reason,
    )


def _query_vietnam_component_rows(
    db: Any,
    *,
    component_code: str,
    as_of: date,
) -> list[dict[str, Any]]:
    """Read all effective VN mappings for one component, including MFN.

    The Vietnam quick-estimate service historically exposed only the three
    FTA mapping groups.  This small tool-layer read intentionally includes
    the mapping's own ``origin_regime`` so a later seed of ordinary MFN rows
    becomes visible without changing the calculator.  It is best-effort: if
    an older database has not applied the CCU schema, the existing service
    result remains usable and the contract marks the missing regime as
    ``NOT_INGESTED``.
    """

    rows = db.execute(text("""
        SELECT
          ccu.ccu_code,
          ccu.ccu_name_cn,
          candidate.hs6_code,
          candidate.verification_status::text AS candidate_verification_status,
          mapping.national_tariff_code,
          mapping.tariff_description,
          mapping.origin_regime::text AS origin_regime,
          agreement.agreement_code,
          mapping.duty_rate,
          mapping.effective_from,
          mapping.effective_to,
          mapping.eligibility_condition,
          mapping.verification_status::text AS verification_status,
          source.source_code,
          source.document_title,
          source.canonical_url,
          clause.locator_value AS source_locator,
          clause.clause_code,
          clause.evidence_summary
        FROM customs.tariff_mapping mapping
        JOIN ref.country country ON country.country_id = mapping.country_id
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
        WHERE country.iso2 = 'VN'
          AND ccu.ccu_code = :component_code
          AND ccu.record_status = 'ACTIVE'
          AND mapping.record_status = 'ACTIVE'
          AND mapping.effective_from <= :as_of
          AND (mapping.effective_to IS NULL OR mapping.effective_to > :as_of)
        ORDER BY mapping.origin_regime, agreement.agreement_code,
                 mapping.national_tariff_code
    """), {"component_code": component_code, "as_of": as_of})
    return [dict(row._mapping) for row in rows]


def _build_vietnam_ckd_contract(
    *,
    db: Any,
    origin_country: str | None,
    component_code: str | None,
    as_of: date,
    component_candidates: list[dict[str, Any]],
    missing_information: list[str],
) -> dict[str, Any]:
    """Build a deterministic, auditable contract for Vietnam CKD candidates."""

    destination = "VN"
    requested_component = component_code.strip().upper() if component_code else None
    groups = component_candidates
    if requested_component:
        groups = [
            group for group in groups
            if str(group.get("ccu_code") or "").upper() == requested_component
        ]

    # If the service did not return a group (most often because MFN rows were
    # seeded after the service was written), hydrate only the requested CCU.
    # A targeted lookup never reads or reports unrelated component gaps.
    db_rows: list[dict[str, Any]] = []
    if requested_component and (
        not groups or not any(group.get("candidates") for group in groups)
    ):
        try:
            db_rows = _query_vietnam_component_rows(
                db, component_code=requested_component, as_of=as_of,
            )
        except Exception:
            db_rows = []
        if db_rows:
            groups = [{
                "ccu_code": requested_component,
                "ccu_name_cn": db_rows[0].get("ccu_name_cn") or requested_component,
                "required_facts": [],
                "candidates": db_rows,
            }]

    raw_candidates: list[dict[str, Any]] = []
    for group in groups:
        code = str(group.get("ccu_code") or "").upper() or requested_component
        if requested_component and code != requested_component:
            continue
        for candidate in group.get("candidates") or []:
            candidate_row = dict(candidate)
            candidate_row.setdefault("component_code", code)
            candidate_row.setdefault("component_name_cn", group.get("ccu_name_cn"))
            raw_candidates.append(candidate_row)

    # Hydrate rows even when the service has FTA candidates: this adds MFN and
    # source/effective-period fields while retaining the service's candidates.
    if requested_component and raw_candidates:
        try:
            db_rows = _query_vietnam_component_rows(
                db, component_code=requested_component, as_of=as_of,
            )
        except Exception:
            db_rows = []
        if db_rows:
            raw_candidates.extend(db_rows)

    expected_regimes = _expected_vietnam_regimes(origin_country)
    # Keep one candidate per regime/code pair, never choose the lowest rate.
    normalized: list[dict[str, Any]] = []
    seen: dict[tuple[str, str | None], int] = {}
    for row in raw_candidates:
        component = str(row.get("component_code") or requested_component or "").upper() or None
        regime = row.get("regime") or row.get("agreement") or row.get("agreement_code")
        if not regime and str(row.get("origin_regime") or "").upper() == "MFN":
            regime = "MFN"
        regime = str(regime or "MFN").upper()
        if regime == "FTA" and row.get("agreement_code"):
            regime = str(row["agreement_code"]).upper()
        if regime not in expected_regimes:
            continue
        tariff_code = row.get("candidate_tariff_code") or row.get("national_tariff_code")
        key = (regime, str(tariff_code) if tariff_code else None)
        if key in seen:
            # Prefer the database row when it enriches a legacy service
            # candidate with source/effective-period/verification metadata.
            existing = normalized[seen[key]]
            if (
                (existing.get("source") is None and _candidate_source(row) is not None)
                or (existing.get("effective_from") is None and row.get("effective_from"))
            ):
                normalized[seen[key]] = _candidate_contract(
                    destination_country=destination,
                    component_code=component,
                    as_of=as_of,
                    row=row,
                    regime=regime,
                )
            continue
        seen[key] = len(normalized)
        row["component_code"] = component
        normalized.append(_candidate_contract(
            destination_country=destination,
            component_code=component,
            as_of=as_of,
            row=row,
            regime=regime,
        ))

    # Add explicit placeholders for regimes that are applicable but not
    # ingested. This is intentionally not phrased as "no legal rate".
    target_component = requested_component or (
        str(groups[0].get("ccu_code") or "").upper() if len(groups) == 1 else None
    )
    for regime in expected_regimes:
        if not any(item["regime"] == regime for item in normalized):
            normalized.append(_empty_candidate_contract(
                destination_country=destination,
                component_code=target_component,
                as_of=as_of,
                regime=regime,
                reason=(
                    f"{destination} {target_component or '该部件'} 的 {regime} 税率行尚未进入当前数据库；"
                    "这是数据接入状态，不能据此判断越南法规中的实际税率。"
                ),
            ))

    if requested_component and not groups and not db_rows:
        normalized = [
            _empty_candidate_contract(
                destination_country=destination,
                component_code=requested_component,
                as_of=as_of,
                regime=regime,
                status="NO_MATCH",
                reason=f"未找到部件编码 {requested_component} 的分类单元；请确认 component_code。",
            )
            for regime in expected_regimes
        ]
    elif requested_component and not normalized:
        normalized = [
            _empty_candidate_contract(
                destination_country=destination,
                component_code=requested_component,
                as_of=as_of,
                regime=regime,
                status="CLASSIFICATION_REQUIRED",
                reason="该部件存在候选范围，但尚未形成可确认的唯一税号。",
            )
            for regime in expected_regimes
        ]

    statuses = {item["status"] for item in normalized}
    if "NO_MATCH" in statuses:
        overall = "NO_MATCH"
    elif statuses and statuses <= {"VERIFIED"}:
        overall = "VERIFIED"
    elif "CLASSIFICATION_REQUIRED" in statuses:
        overall = "CLASSIFICATION_REQUIRED"
    elif statuses and statuses <= {"NOT_INGESTED", "NOT_APPLICABLE"}:
        overall = "NOT_INGESTED"
    elif not normalized:
        overall = "NOT_INGESTED"
    else:
        overall = "CONDITIONAL"

    contract_missing = list(dict.fromkeys(
        str(item) for item in missing_information
        if not requested_component or not (
            str(item).upper().startswith("VN-CKD-")
            and not str(item).upper().startswith(requested_component)
        )
    ))
    return {
        "contract_version": CONTRACT_VERSION,
        "status": overall,
        "destination_country": destination,
        "route": "CKD",
        "component_code": requested_component,
        "as_of": as_of.isoformat(),
        "origin_country": origin_country.upper() if origin_country else None,
        "candidates": normalized,
        "missing_information": contract_missing,
        "selection_policy": "NO_AUTO_LOWEST_CANDIDATE",
    }


def _build_generic_ckd_contract(
    *,
    destination_country: str,
    as_of: date,
    import_duty_options: list[dict[str, Any]],
    missing_information: list[str],
) -> dict[str, Any]:
    """Normalize the legacy whole-kit calculator without changing its math."""

    candidates = [
        _candidate_contract(
            destination_country=destination_country,
            component_code=None,
            as_of=as_of,
            row={
                "candidate_tariff_code": option.get("national_tariff_code"),
                "tariff_description": option.get("tariff_description"),
                "rate": option.get("rate"),
                "verification_status": option.get("verification_status"),
                "eligibility_condition": option.get("eligibility_note"),
            },
            regime=option.get("regime") or "MFN",
        )
        for option in import_duty_options
    ]
    if not candidates:
        status = "CLASSIFICATION_REQUIRED"
    elif all(item["status"] == "VERIFIED" for item in candidates):
        status = "VERIFIED"
    else:
        status = "CONDITIONAL"
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "destination_country": destination_country,
        "route": "CKD",
        "component_code": None,
        "as_of": as_of.isoformat(),
        "candidates": candidates,
        "missing_information": list(dict.fromkeys(str(item) for item in missing_information)),
        "selection_policy": "NO_AUTO_LOWEST_CANDIDATE",
    }


def _unsupported_country_response(country: str, *, powertrain: str, effective_date: date) -> dict:
    """Return a safe routing result instead of silently using Malaysia."""

    code = normalize_country(country)
    contract = {
        "contract_version": CONTRACT_VERSION,
        "status": "NOT_APPLICABLE",
        "destination_country": code,
        "route": "CKD",
        "component_code": None,
        "as_of": effective_date.isoformat(),
        "candidates": [],
        "missing_information": ["country_route_configuration"],
        "selection_policy": "NO_AUTO_LOWEST_CANDIDATE",
    }
    return {
        "status": "UNSUPPORTED_COUNTRY",
        "contract_status": "NOT_APPLICABLE",
        "result_contract": contract,
        "applicability_status": "UNSUPPORTED_COUNTRY",
        "country": code,
        "country_iso2": code,
        "route": "CKD",
        "powertrain": powertrain,
        "effective_date": str(effective_date),
        "supported_countries": sorted(SUPPORTED_COUNTRIES),
        "missing_information": ["country_route_configuration"],
        "error": f"当前工具尚未配置目的国 {code} 的 CKD 规则，未回退到马来西亚。",
    }


def _calculate_vietnam_ckd(
    *,
    origin_country: str | None,
    powertrain: str,
    displacement_cc: int | None,
    body_type: str,
    drive_type: str,
    effective_date: date,
    ckd_declaration_mode: str,
    ckd_component_tariff_codes: dict[str, str],
    component_code: str | None,
) -> dict:
    """Run the Vietnam major-component CKD estimator through the agent tool."""

    from app.services.quick_estimate import QuickEstimateService

    db = SessionLocal()
    try:
        requested_origin = origin_country.upper() if origin_country else None
        result = QuickEstimateService(db).estimate(
            country_iso2="VN",
            origin_country_iso2=requested_origin or "UNKNOWN",
            effective_date=effective_date,
            path="CKD",
            powertrain=powertrain,
            cbu_tariff_code=None,
            ckd_declaration_mode="PARTS_BOM",
            ckd_tariff_code=None,
            customs_value_cbu=None,
            customs_value_ckd=None,
            ckd_component_tariff_codes=ckd_component_tariff_codes,
        )
        result = dict(result)
        result["country"] = "VN"
        result["country_iso2"] = "VN"
        result["origin_country"] = requested_origin
        result["origin_country_iso2"] = requested_origin
        result["powertrain"] = powertrain
        result["displacement_cc"] = displacement_cc
        result["body_type"] = body_type
        result["drive_type"] = drive_type
        result["ckd_declaration_mode"] = "PARTS_BOM"
        result["component_code"] = component_code

        # The service returns candidates grouped by CCU.  A targeted question
        # (for example, the traction battery only) should not force the model
        # to read all 19 component groups.  Filtering is display-only and
        # never selects a tariff code or lowest rate.
        ckd_path = next(
            (path for path in (result.get("paths") or []) if path.get("path") == "CKD"),
            {},
        )
        component_candidates = list(ckd_path.get("component_candidates") or [])
        if component_code:
            requested_component = component_code.strip().upper()
            component_candidates = [
                group
                for group in component_candidates
                if str(group.get("ccu_code") or "").upper() == requested_component
            ]
            if ckd_path:
                ckd_path["component_candidates"] = component_candidates
            result["component_filter_applied"] = requested_component
        # Flatten the CKD path's grouped candidate list into the tool result;
        # this keeps the common single-tool response useful to the model while
        # retaining the full auditable ``paths`` structure.
        result["component_candidates"] = component_candidates

        missing = list(result.get("missing_information") or [])
        missing.extend(ckd_path.get("missing_items") or [])
        if not requested_origin:
            missing.append("origin_country")
        if component_code:
            requested_component = component_code.strip().upper()
            # A focused component lookup should not report the other 18
            # component selections as blockers for this one answer.
            missing = [
                item
                for item in missing
                if not (
                    str(item).upper().startswith("VN-CKD-")
                    and not str(item).upper().startswith(requested_component)
                )
            ]
            if not result.get("component_candidates"):
                missing.append("component_code")
        result["missing_information"] = list(dict.fromkeys(missing))
        result_contract = _build_vietnam_ckd_contract(
            db=db,
            origin_country=requested_origin,
            component_code=component_code,
            as_of=effective_date,
            component_candidates=component_candidates,
            missing_information=result["missing_information"],
        )
        result["result_contract"] = result_contract
        result["contract_status"] = result_contract["status"]
        result["destination_country"] = "VN"
        result["as_of"] = effective_date.isoformat()
        # ``status`` was not present on this VN legacy envelope.  Use the
        # strict contract state for new callers while retaining the old path
        # status at ``paths[].status`` for the existing UI.
        result["status"] = result_contract["status"]
        result["candidate_tariffs"] = result_contract["candidates"]
        fingerprint_src = json.dumps(
            {
                "country": "VN",
                "origin_country": requested_origin,
                "powertrain": powertrain,
                "displacement_cc": displacement_cc,
                "body_type": body_type,
                "drive_type": drive_type,
                "effective_date": str(effective_date),
                "ckd_declaration_mode": "PARTS_BOM",
                "ckd_component_tariff_codes": ckd_component_tariff_codes,
                "component_code": component_code,
            },
            sort_keys=True,
        )
        result["_meta"] = {
            "run_id": str(uuid.uuid4())[:8],
            "task_id": "",
            "parameter_fingerprint": hashlib.sha256(fingerprint_src.encode()).hexdigest()[:16],
            "depends_on_fields": [
                "country", "origin_country", "powertrain", "displacement_cc", "body_type",
                "drive_type", "effective_date", "ckd_declaration_mode",
                "ckd_component_tariff_codes", "component_code",
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
def calculate_ckd_tax(
    country: str = "MY",
    origin_country: str | None = None,
    powertrain: str = "BEV",
    displacement_cc: int | None = None,
    body_type: str = "SEDAN",
    drive_type: str = "4WD_AWD",
    effective_date: str | None = None,
    ckd_declaration_mode: str = "WHOLE_KIT",
    ckd_tariff_code: str | None = None,
    ckd_component_tariff_codes: dict[str, str] | None = None,
    component_code: str | None = None,
) -> dict:
    """Calculate a configured-country CKD import and local-assembly scenario.

    ``country`` should be an ISO2 destination code (MY or VN; common country
    names are normalized).  An unsupported destination returns a structured
    result and is never routed through the Malaysia calculator.

    CKD tax is a TWO-STAGE model:
    - Import stage: import duty + conditional import sales tax exemption
    - Local assembly stage: excise duty + finished-vehicle sales tax (NOT collected at import)

    When origin_country is None, returns CANDIDATE_REGIMES with available rates.
    ckd_tariff_code is optional for the legacy MY whole-kit route.  For VN,
    pass ckd_component_tariff_codes only for explicitly confirmed component
    codes; omitted codes produce candidates and are never auto-selected.
    component_code can restrict a VN response to one CCU (major component).
    Full-cycle simulation requires valuation ratios (not included here).
    """
    from app.services.ckd_calculator import CkdCalculator

    eff_date = date.today() if effective_date is None else date.fromisoformat(effective_date)
    country_code = normalize_country(country)

    if country_code not in SUPPORTED_COUNTRIES:
        return sanitize_tool_result_summary(
            _unsupported_country_response(country_code, powertrain=powertrain, effective_date=eff_date)
        )

    if country_code == "VN":
        selected_component_codes = {
            str(key): str(value)
            for key, value in (ckd_component_tariff_codes or {}).items()
            if str(key).strip() and str(value).strip()
        }
        return sanitize_tool_result_summary(
            _calculate_vietnam_ckd(
                origin_country=origin_country,
                powertrain=powertrain,
                displacement_cc=displacement_cc,
                body_type=body_type,
                drive_type=drive_type,
                effective_date=eff_date,
                ckd_declaration_mode=ckd_declaration_mode,
                ckd_component_tariff_codes=selected_component_codes,
                component_code=component_code,
            )
        )

    db = SessionLocal()
    try:
        calc = CkdCalculator(db)
        result = calc.calculate(
            effective_date=eff_date,
            origin_country_iso2=origin_country or "CN",
            powertrain=powertrain,
            displacement_cc=displacement_cc,
            body_type=body_type,
            drive_type=drive_type,
            ckd_tariff_code=ckd_tariff_code,
            customs_value=None,
            declaration_mode=(
                "CKD_WHOLE_KIT_WITH_RULING" if ckd_tariff_code else "CKD_WHOLE_KIT_PENDING_RULING"
            ),
        )

        run_id = str(uuid.uuid4())[:8]
        task_id = ""

        # Import duty options
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

        # Import effective rates
        import_effective_rates = []
        for r in result.import_stage_results:
            import_effective_rates.append({
                "regime_label": r.regime_label,
                "agreement_code": r.agreement_code,
                "import_duty_rate": str(r.import_duty_rate) if r.import_duty_rate else None,
                "import_sales_tax_rate": str(r.import_sales_tax_rate) if r.import_sales_tax_rate else None,
                "import_effective_rate": str(r.import_effective_rate) if r.import_effective_rate else None,
            })

        evidence_refs: list[dict] = []

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
            "classification_note": result.classification_note,
            "import_stage": {
                "import_duty_options": import_duty_options,
                "import_sales_tax": {
                    "treatment": result.import_sales_tax.treatment,
                    "statutory_rate": str(result.import_sales_tax.statutory_rate) if result.import_sales_tax.statutory_rate else None,
                    "applied_rate": str(result.import_sales_tax.applied_rate) if result.import_sales_tax.applied_rate else None,
                    "note": sanitize_evidence_text(result.import_sales_tax.note),
                    "is_conditional": result.import_sales_tax.is_conditional,
                    "approval_required": result.import_sales_tax.approval_required,
                },
                "import_effective_rates": import_effective_rates,
            },
            "local_assembly_stage": {
                "excise_duty": {
                    "treatment": result.excise_duty.treatment,
                    "statutory_rate": str(result.excise_duty.statutory_rate) if result.excise_duty.statutory_rate else None,
                    "applied_rate": str(result.excise_duty.applied_rate) if result.excise_duty.applied_rate else None,
                    "note": sanitize_evidence_text(result.excise_duty.note),
                    "is_conditional": result.excise_duty.is_conditional,
                },
                "finished_vehicle_sales_tax": {
                    "treatment": result.finished_vehicle_sales_tax.treatment,
                    "statutory_rate": str(result.finished_vehicle_sales_tax.statutory_rate) if result.finished_vehicle_sales_tax.statutory_rate else None,
                    "applied_rate": str(result.finished_vehicle_sales_tax.applied_rate) if result.finished_vehicle_sales_tax.applied_rate else None,
                    "note": sanitize_evidence_text(result.finished_vehicle_sales_tax.note),
                    "is_conditional": result.finished_vehicle_sales_tax.is_conditional,
                },
            },
            "full_cycle_available": result.full_cycle.available if result.full_cycle else False,
            "notes": result.notes,
            "missing_information": ([] if origin_country else ["origin_country"]) + _classification_missing_information(powertrain, displacement_cc),
            "evidence_refs": evidence_refs,
        }
        result_contract = _build_generic_ckd_contract(
            destination_country=country_code,
            as_of=eff_date,
            import_duty_options=import_duty_options,
            missing_information=output["missing_information"],
        )
        output["result_contract"] = result_contract
        output["contract_status"] = result_contract["status"]
        output["destination_country"] = country_code
        output["as_of"] = eff_date.isoformat()
        output["status"] = result_contract["status"]

        fingerprint_src = json.dumps({
            "country": country_code, "powertrain": powertrain,
            "displacement_cc": displacement_cc, "body_type": body_type, "drive_type": drive_type, "origin": origin_country,
            "effective_date": str(eff_date), "import_mode": "CKD",
            "ckd_tariff_code": ckd_tariff_code,
            "ckd_component_tariff_codes": ckd_component_tariff_codes,
            "ckd_declaration_mode": ckd_declaration_mode,
            "component_code": component_code,
        }, sort_keys=True)
        output["_meta"] = {
            "run_id": run_id,
            "task_id": task_id,
            "parameter_fingerprint": hashlib.sha256(fingerprint_src.encode()).hexdigest()[:16],
            "depends_on_fields": [
                "country", "origin_country", "powertrain", "displacement_cc", "body_type",
                "drive_type", "effective_date", "ckd_declaration_mode", "ckd_tariff_code",
                "ckd_component_tariff_codes", "component_code",
            ],
        }

        return sanitize_tool_result_summary(output)

    finally:
        db.close()
