from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_csrf, require_permission
from app.db.session import get_db_session
from app.schemas.calculation import MalaysiaComparisonRequest
from app.schemas.decision import (
    CbuCalculateRequest,
    CkdCalculateRequest,
    DecisionProjectCreate,
    ProjectApprovalUpdate,
    ProjectBomComparisonRequest,
    ProjectBomLineUpdate,
    ProjectBomMappingSelectionUpdate,
    ProjectInputUpdate,
    ProjectRouteFactsUpdate,
    ProjectTariffSelectionUpdate,
    QuickEstimateRequest,
    RouteResolveRequest,
)
from app.services.calculation_engine import (
    CalculationEngine,
    CalculationError,
    ComparisonRequest,
    ItemCostInput,
    PreferenceEligibility,
    ProfitInput,
)
from app.services.cbu_calculator import CbuCalculator
from app.services.ckd_calculator import CkdCalculator
from app.services.comparison_persistence import ComparisonPersistence
from app.services.decision_repository import DecisionRepository
from app.services.intelligence_repository import IntelligenceRepository
from app.services.project_calculation import ProjectCalculationService
from app.services.project_bom import ProjectBomService
from app.services.quick_estimate import QuickEstimateService
from app.services.tariff_repository import TariffRepository

router = APIRouter()


@router.get("/meta/phase", tags=["system"])
def phase_metadata() -> dict[str, object]:
    return {
        "phase": "Phase 4",
        "version": "0.4.0",
        "capabilities": [
            "schema_contract",
            "source_traceability",
            "rule_versioning",
            "calculation_dsl_validation",
            "deterministic_tax_comparison",
            "profit_impact_comparison",
            "mfn_fallback",
            "explicit_tariff_mapping_selection",
            "malaysia_five_route_read_api",
            "country_policy_and_evidence_api",
            "vehicle_tariff_catalog_api",
            "ccu_catalog_api",
            "five_route_write_workflow",
            "project_calculation_preview",
            "project_calculation_run",
            "calculation_line_and_decision_trace",
            "missing_data_and_llm_safe_view",
            "project_bom_ccu_allocation",
            "project_bom_tariff_selection",
            "project_bom_regime_comparison",
            "four_condition_quick_estimate",
        ],
        "disabled": [
            "final_hs_classification",
            "crawler",
            "rag",
            "cross_route_profit_optimization",
        ],
    }


@router.post("/api/v1/quick-estimates", tags=["quick-estimate"])
def create_quick_estimate(
    payload: QuickEstimateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = QuickEstimateService(session).estimate(
            country_iso2=payload.country_iso2,
            origin_country_iso2=payload.origin_country_iso2,
            effective_date=payload.effective_date,
            path=payload.path,
            powertrain=payload.powertrain,
            cbu_tariff_code=payload.cbu_tariff_code,
            ckd_declaration_mode=payload.ckd_declaration_mode,
            ckd_tariff_code=payload.ckd_tariff_code,
            customs_value_cbu=payload.customs_value_cbu,
            customs_value_ckd=payload.customs_value_ckd,
            ckd_component_tariff_codes=payload.ckd_component_tariff_codes,
        )
        return _json_safe(result)  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ── CBU 整车进口计算 ──────────────────────────────────────────────


@router.post("/api/v1/cbu/calculate", tags=["cbu-calculator"])
def calculate_cbu(
    payload: CbuCalculateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = CbuCalculator(session).calculate(
            effective_date=payload.effective_date,
            origin_country_iso2=payload.origin_country_iso2,
            powertrain=payload.powertrain,
            displacement_cc=payload.displacement_cc,
            body_type=payload.body_type,
            drive_type=payload.drive_type,
            customs_value=payload.customs_value,
            selected_policy_codes=payload.selected_policy_codes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _json_safe(
        {
            "country_iso2": result.country_iso2,
            "effective_date": str(result.effective_date),
            "powertrain": result.powertrain,
            "displacement_cc": result.displacement_cc,
            "origin_country_iso2": result.origin_country_iso2,
            "normalized_base": str(result.normalized_base),
            "hs_classification": (
                {
                    "national_tariff_code": result.hs_classification.national_tariff_code,
                    "hs6_code": result.hs_classification.hs6_code,
                    "tariff_description": result.hs_classification.tariff_description,
                    "verification_status": result.hs_classification.verification_status,
                    "source_code": result.hs_classification.source_code,
                    "source_locator": result.hs_classification.source_locator,
                }
                if result.hs_classification
                else None
            ),
            "import_duty_options": [
                {
                    "regime": opt.regime,
                    "agreement_code": opt.agreement_code,
                    "national_tariff_code": opt.national_tariff_code,
                    "tariff_description": opt.tariff_description,
                    "rate": str(opt.rate) if opt.rate is not None else None,
                    "per_100": str(opt.per_100) if opt.per_100 is not None else None,
                    "verification_status": opt.verification_status,
                    "eligibility_note": opt.eligibility_note,
                    "rule_reference": opt.rule_reference,
                    "source_reference": opt.source_reference,
                }
                for opt in result.import_duty_options
            ],
            "excise_duty": _resolved_treatment_dict(result.excise_duty),
            "sales_tax": _resolved_treatment_dict(result.sales_tax),
            "incentive_validation": {
                "resolved": [
                    {
                        "program_code": rp.program_code,
                        "program_name_cn": rp.program_name_cn,
                        "status": rp.status,
                        "status_chain": rp.status_chain,
                        "matched_conditions": rp.matched_conditions,
                        "required_documents": rp.required_documents,
                        "approval_authority": rp.approval_authority,
                        "incentive_scope": rp.incentive_scope,
                        "condition_expression": rp.condition_expression,
                        "benefit_expression": rp.benefit_expression,
                        "effective_from": rp.effective_from,
                        "effective_to": rp.effective_to,
                        "benefit": ({
                            "benefit_type": rp.benefit.benefit_type,
                            "target_taxes": rp.benefit.target_taxes,
                            "overrides": rp.benefit.overrides,
                            "requires_project_approval": rp.benefit.requires_project_approval,
                            "note": rp.benefit.note,
                        } if rp.benefit else None),
                        "source_reference": rp.source_reference,
                    }
                    for rp in (result.incentive_validation.resolved if result.incentive_validation else [])
                ],
                "invalid_codes": result.incentive_validation.invalid_codes if result.incentive_validation else [],
                "notes": result.incentive_validation.notes if result.incentive_validation else [],
            },
            "combined_results": [
                {
                    "regime_label": cr.regime_label,
                    "agreement_code": cr.agreement_code,
                    "import_duty_rate": str(cr.import_duty_rate) if cr.import_duty_rate is not None else None,
                    "import_duty_per_100": str(cr.import_duty_per_100) if cr.import_duty_per_100 is not None else None,
                    "excise_duty_rate": str(cr.excise_duty_rate) if cr.excise_duty_rate is not None else None,
                    "excise_duty_per_100": str(cr.excise_duty_per_100) if cr.excise_duty_per_100 is not None else None,
                    "sales_tax_rate": str(cr.sales_tax_rate) if cr.sales_tax_rate is not None else None,
                    "sales_tax_per_100": str(cr.sales_tax_per_100) if cr.sales_tax_per_100 is not None else None,
                    "total_per_100": str(cr.total_per_100) if cr.total_per_100 is not None else None,
                    "effective_tax_rate": str(cr.effective_tax_rate) if cr.effective_tax_rate is not None else None,
                    "is_complete": cr.is_complete,
                    "unknown_items": cr.unknown_items,
                }
                for cr in result.combined_results
            ],
            "calculation_explanation": result.calculation_explanation,
            "notes": result.notes,
            "disclaimer": result.disclaimer,
        }
    )


# ── CKD 整套进口计算 ──────────────────────────────────────────────


@router.post("/api/v1/ckd/calculate", tags=["ckd-calculator"])
def calculate_ckd(
    payload: CkdCalculateRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = CkdCalculator(session).calculate(
            effective_date=payload.effective_date,
            origin_country_iso2=payload.origin_country_iso2,
            powertrain=payload.powertrain,
            displacement_cc=payload.displacement_cc,
            body_type=payload.body_type,
            drive_type=payload.drive_type,
            ckd_tariff_code=payload.ckd_tariff_code,
            customs_value=payload.customs_value,
            declaration_mode=payload.declaration_mode,
            miti_ckd_ap_confirmed=payload.miti_ckd_ap_confirmed,
            selected_policy_codes=payload.selected_policy_codes,
            excise_value_ratio=payload.excise_value_ratio,
            sales_value_ratio=payload.sales_value_ratio,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    incentive = result.incentive_validation

    return _json_safe(
        {
            "country_iso2": result.country_iso2,
            "effective_date": str(result.effective_date),
            "powertrain": result.powertrain,
            "displacement_cc": result.displacement_cc,
            "origin_country_iso2": result.origin_country_iso2,
            "normalized_base": str(result.normalized_base),
            "declaration_mode": result.declaration_mode,
            "miti_ckd_ap_confirmed": result.miti_ckd_ap_confirmed,
            "classification_note": result.classification_note,

            # ① HS classification
            "hs_classification": (
                {
                    "national_tariff_code": result.hs_classification.national_tariff_code,
                    "hs6_code": result.hs_classification.hs6_code,
                    "tariff_description": result.hs_classification.tariff_description,
                    "verification_status": result.hs_classification.verification_status,
                    "source_code": result.hs_classification.source_code,
                    "source_locator": result.hs_classification.source_locator,
                }
                if result.hs_classification
                else None
            ),

            # ② Import stage
            "import_stage": {
                "import_duty_options": [
                    {
                        "regime": opt.regime,
                        "agreement_code": opt.agreement_code,
                        "national_tariff_code": opt.national_tariff_code,
                        "tariff_description": opt.tariff_description,
                        "rate": str(opt.rate) if opt.rate is not None else None,
                        "per_100": str(opt.per_100) if opt.per_100 is not None else None,
                        "verification_status": opt.verification_status,
                        "eligibility_note": opt.eligibility_note,
                        "rule_reference": opt.rule_reference,
                        "source_reference": opt.source_reference,
                    }
                    for opt in result.import_duty_options
                ],
                "import_sales_tax": _resolved_treatment_dict(result.import_sales_tax),
                "import_effective_rates": [
                    {
                        "regime_label": r.regime_label,
                        "agreement_code": r.agreement_code,
                        "effective_rate": (
                            str(r.import_effective_rate)
                            if r.import_effective_rate is not None
                            else None
                        ),
                    }
                    for r in result.import_stage_results
                ],
            },

            # ③ Local assembly stage
            "local_assembly_stage": {
                "excise_duty": _resolved_treatment_dict(result.excise_duty),
                "finished_vehicle_sales_tax": _resolved_treatment_dict(result.finished_vehicle_sales_tax),
                "missing_for_complete_calculation": [
                    inp["description"]
                    for inp in (result.full_cycle.missing_inputs if result.full_cycle else [])
                ],
            },

            # ④ Full-cycle simulation
            "full_cycle_simulation": {
                "available": result.full_cycle.available if result.full_cycle else False,
                "message": (
                    ""
                    if (result.full_cycle and result.full_cycle.available)
                    else "缺少估值系数或适用税率为0，无法计算全流程税负率。"
                ),
                "required_inputs": (
                    result.full_cycle.missing_inputs
                    if result.full_cycle
                    else [
                        {"field": "excise_value_ratio", "description": "消费税核定价值 ÷ CKD进口价值"},
                        {"field": "sales_value_ratio", "description": "销售税计税价值 ÷ CKD进口价值"},
                    ]
                ),
                "results": (
                    [
                        {
                            "regime_label": r.regime_label,
                            "agreement_code": r.agreement_code,
                            "import_duty_per_100": str(r.import_duty_per_100) if r.import_duty_per_100 is not None else None,
                            "import_sales_tax_per_100": str(r.import_sales_tax_per_100),
                            "excise_per_100": str(r.excise_per_100) if r.excise_per_100 is not None else None,
                            "finished_sst_per_100": str(r.finished_sst_per_100) if r.finished_sst_per_100 is not None else None,
                            "import_total_per_100": str(r.import_total_per_100) if r.import_total_per_100 is not None else None,
                            "full_cycle_total_per_100": str(r.full_cycle_total_per_100) if r.full_cycle_total_per_100 is not None else None,
                            "import_effective_rate": str(r.import_effective_rate) if r.import_effective_rate is not None else None,
                            "simulated_full_cycle_rate": str(r.simulated_full_cycle_rate) if r.simulated_full_cycle_rate is not None else None,
                            "metric_name": r.metric_name,
                            "is_statutory_rate": r.is_statutory_rate,
                        }
                        for r in result.full_cycle.results
                    ]
                    if (result.full_cycle and result.full_cycle.available)
                    else None
                ),
            },

            # ⑤ Policy validation
            "incentive_validation": (
                {
                    "resolved": [
                        {
                            "program_code": rp.program_code,
                            "program_name_cn": rp.program_name_cn,
                            "status": rp.status,
                            "status_chain": rp.status_chain,
                            "matched_conditions": rp.matched_conditions,
                            "required_documents": rp.required_documents,
                            "approval_authority": rp.approval_authority,
                            "incentive_scope": rp.incentive_scope,
                            "condition_expression": rp.condition_expression,
                            "benefit_expression": rp.benefit_expression,
                            "effective_from": rp.effective_from,
                            "effective_to": rp.effective_to,
                            "benefit": (
                                {
                                    "benefit_type": rp.benefit.benefit_type,
                                    "target_taxes": rp.benefit.target_taxes,
                                    "overrides": rp.benefit.overrides,
                                    "requires_project_approval": rp.benefit.requires_project_approval,
                                    "note": rp.benefit.note,
                                }
                                if rp.benefit else None
                            ),
                            "source_reference": rp.source_reference,
                        }
                        for rp in incentive.resolved
                    ] if incentive else [],
                    "invalid_codes": incentive.invalid_codes if incentive else [],
                    "notes": incentive.notes if incentive else [],
                }
                if incentive
                else None
            ),

            "calculation_explanation": result.calculation_explanation,
            "notes": result.notes,
            "disclaimer": result.disclaimer,
        }
    )


# ── Source evidence detail ─────────────────────────────────────────


@router.get("/api/v1/sources/{source_id}", tags=["evidence"])
def get_source_evidence(
    source_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    """Return detailed evidence for a source document, including original text."""
    row = session.execute(
        text("""
            SELECT
              doc.source_code AS source_id,
              doc.document_title,
              doc.document_number,
              doc.source_type,
              doc.canonical_url AS official_url,
              doc.effective_from,
              doc.effective_to,
              auth.authority_name,
              clause.locator_type,
              clause.locator_value,
              clause.original_text,
              clause.translated_text_cn
            FROM evidence.source_document doc
            JOIN evidence.source_clause clause
              ON clause.source_document_id = doc.source_document_id
            LEFT JOIN ref.authority auth
              ON auth.authority_id = doc.authority_id
            WHERE doc.source_code = :source_id
            LIMIT 1
        """),
        {"source_id": source_id},
    ).first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    _m = row._mapping
    return {
        "source_id": str(_m["source_id"]),
        "document_title": str(_m["document_title"]),
        "document_number": _m.get("document_number"),
        "source_type": str(_m.get("source_type", "")),
        "official_url": _m.get("official_url"),
        "authority_name": _m.get("authority_name"),
        "locator": {
            "locator_type": str(_m.get("locator_type", "")),
            "locator_value": str(_m.get("locator_value", "")),
        },
        "original_excerpt": _m.get("original_text"),
        "translated_excerpt_cn": _m.get("translated_text_cn"),
        "effective_from": str(_m["effective_from"]) if _m.get("effective_from") else None,
        "effective_to": str(_m["effective_to"]) if _m.get("effective_to") else None,
    }


# ── helpers ─────────────────────────────────────────────────────────


def _resolved_treatment_dict(t: object) -> dict[str, object]:
    """Serialize ResolvedTreatment to a flat dict."""
    return {
        "tax_code": str(getattr(t, "tax_code", "")),
        "stage": str(getattr(t, "stage", "")),
        "statutory_rate": (
            str(getattr(t, "statutory_rate", None))
            if getattr(t, "statutory_rate", None) is not None
            else None
        ),
        "applied_rate": (
            str(getattr(t, "applied_rate", None))
            if getattr(t, "applied_rate", None) is not None
            else None
        ),
        "treatment": str(getattr(t, "treatment", "")),
        "is_conditional": bool(getattr(t, "is_conditional", False)),
        "approval_required": bool(getattr(t, "approval_required", False)),
        "approval_confirmed": bool(getattr(t, "approval_confirmed", False)),
        "source_policy_code": getattr(t, "source_policy_code", None),
        "note": str(getattr(t, "note", "")),
    }


# ── shared serializers ──────────────────────────────────────────────


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _as_of(value: date | None) -> date:
    return value or date.today()


def _country_or_404(
    repository: IntelligenceRepository, country_iso2: str
) -> dict[str, object]:
    country = repository.country(iso2=country_iso2)
    if country is None:
        raise HTTPException(status_code=404, detail=f"Country {country_iso2.upper()} not found")
    return country


@router.get("/api/v1/dashboard/overview", tags=["intelligence"])
def dashboard_overview(
    session: Annotated[Session, Depends(get_db_session)],
    as_of: date | None = None,
) -> dict[str, object]:
    result = IntelligenceRepository(session).dashboard_overview(as_of=_as_of(as_of))
    return _json_safe(result)  # type: ignore[return-value]


@router.get("/api/v1/countries/{country_iso2}/overview", tags=["intelligence"])
def country_overview(
    country_iso2: str,
    session: Annotated[Session, Depends(get_db_session)],
    as_of: date | None = None,
) -> dict[str, object]:
    current_date = _as_of(as_of)
    repository = IntelligenceRepository(session)
    country = _country_or_404(repository, country_iso2)
    route_readiness = repository.route_readiness(
        iso2=country_iso2, as_of=current_date
    )
    completeness = (
        round(
            sum(int(route["completeness_percent"]) for route in route_readiness)
            / len(route_readiness)
        )
        if route_readiness
        else 0
    )
    return _json_safe(
        {
            "country": country,
            "as_of": current_date,
            "route_readiness": route_readiness,
            "policy_nodes": repository.policy_nodes(
                iso2=country_iso2, as_of=current_date
            ),
            "open_missing_data": repository.open_missing_data_count(),
            "completeness_percent": completeness,
            "last_verified_at": repository.last_verified_at(iso2=country_iso2),
        }
    )  # type: ignore[return-value]


@router.get("/api/v1/countries/{country_iso2}/tax-routes", tags=["intelligence"])
def country_tax_routes(
    country_iso2: str,
    session: Annotated[Session, Depends(get_db_session)],
    as_of: date | None = None,
) -> dict[str, object]:
    current_date = _as_of(as_of)
    repository = IntelligenceRepository(session)
    _country_or_404(repository, country_iso2)
    return _json_safe(
        {
            "country_iso2": country_iso2.upper(),
            "as_of": current_date,
            "items": repository.tax_routes(iso2=country_iso2, as_of=current_date),
        }
    )  # type: ignore[return-value]


@router.post(
    "/api/v1/countries/{country_iso2}/tax-routes/resolve",
    tags=["decision"],
)
def resolve_country_tax_route(
    country_iso2: str,
    payload: RouteResolveRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    intelligence = IntelligenceRepository(session)
    _country_or_404(intelligence, country_iso2)
    routes = intelligence.tax_routes(iso2=country_iso2, as_of=payload.as_of)
    result = DecisionRepository.resolve_route(routes, payload.facts)
    return _json_safe(
        {
            "country_iso2": country_iso2.upper(),
            "as_of": payload.as_of,
            **result,
        }
    )  # type: ignore[return-value]


@router.post("/api/v1/projects", tags=["decision"], status_code=201)
def create_decision_project(
    payload: DecisionProjectCreate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("project.create"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = DecisionRepository(session).create_project(payload)
        session.commit()
        return _json_safe(result)  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get("/api/v1/projects/{project_id}", tags=["decision"])
def get_decision_project(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        return _json_safe(
            DecisionRepository(session).get_project(project_id)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/api/v1/projects/{project_id}/route-facts", tags=["decision"])
def update_project_route_facts(
    project_id: str,
    payload: ProjectRouteFactsUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("project.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    repository = DecisionRepository(session)
    try:
        project = repository.get_project(project_id)
        routes = IntelligenceRepository(session).tax_routes(
            iso2=str(project["country_iso2"]),
            as_of=project["calculation_date"],
        )
        resolution = repository.resolve_route(routes, payload.facts)
        updated = repository.save_route_resolution(
            project_id=project_id,
            facts=payload.facts,
            selected_route_code=resolution["selected_route_code"],
        )
        session.commit()
        return _json_safe(
            {"project": updated, "resolution": resolution}
        )  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get("/api/v1/projects/{project_id}/inputs", tags=["decision"])
def get_project_inputs(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    repository = DecisionRepository(session)
    try:
        repository.get_project(project_id)
        return _json_safe(
            {"project_id": project_id, "items": repository.project_inputs(project_id)}
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/api/v1/projects/{project_id}/inputs/{field_path:path}",
    tags=["decision"],
)
def set_project_input(
    project_id: str,
    field_path: str,
    payload: ProjectInputUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("project.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    repository = DecisionRepository(session)
    try:
        allowed_fields = {
            item["field_path"] for item in repository.project_inputs(project_id)
        }
        if field_path not in allowed_fields:
            raise ValueError(f"Field {field_path} is not required by the selected route")
        input_id = repository.set_project_input(
            project_id=project_id,
            field_path=field_path,
            value_payload=payload.value_payload,
            provided_by=payload.provided_by,
            evidence_refs=payload.evidence_refs,
            notes=payload.notes,
        )
        session.commit()
        return _json_safe(
            {
                "project_input_value_id": input_id,
                "completion": repository.completion(project_id),
            }
        )  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.delete(
    "/api/v1/projects/{project_id}/inputs/{field_path:path}",
    tags=["decision"],
)
def clear_project_input(
    project_id: str,
    field_path: str,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("project.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    repository = DecisionRepository(session)
    repository.clear_project_input(project_id=project_id, field_path=field_path)
    session.commit()
    return _json_safe(
        {"project_id": project_id, "completion": repository.completion(project_id)}
    )  # type: ignore[return-value]


@router.get("/api/v1/projects/{project_id}/completion", tags=["decision"])
def get_project_completion(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        return _json_safe(
            DecisionRepository(session).completion(project_id)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/v1/projects/{project_id}/approval-readiness", tags=["decision"])
def get_project_approval_readiness(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        return _json_safe(
            DecisionRepository(session).approval_readiness(project_id)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/api/v1/projects/{project_id}/approvals/{requirement_code}",
    tags=["decision"],
)
def upsert_project_approval(
    project_id: str,
    requirement_code: str,
    payload: ProjectApprovalUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("project.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    repository = DecisionRepository(session)
    try:
        approval_id = repository.upsert_approval(
            project_id=project_id,
            requirement_code=requirement_code,
            payload=payload,
        )
        session.commit()
        return _json_safe(
            {
                "project_approval_id": approval_id,
                "readiness": repository.approval_readiness(project_id),
            }
        )  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.put(
    "/api/v1/projects/{project_id}/tariff-selections/{selection_scope}",
    tags=["decision"],
)
def select_project_tariff(
    project_id: str,
    selection_scope: str,
    payload: ProjectTariffSelectionUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("project.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    repository = DecisionRepository(session)
    try:
        repository.get_project(project_id)
        selection_id = repository.select_tariff(
            project_id=project_id,
            selection_scope=selection_scope,
            tariff_mapping_id=payload.tariff_mapping_id,
            vehicle_tariff_rate_line_id=payload.vehicle_tariff_rate_line_id,
            selected_by=payload.selected_by,
            selection_note=payload.selection_note,
        )
        session.commit()
        return {"project_tariff_selection_id": selection_id}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get(
    "/api/v1/projects/{project_id}/bom-lines",
    tags=["decision"],
)
def list_project_bom_lines(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        return _json_safe(
            ProjectBomService(session).list_lines(project_id)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/api/v1/projects/{project_id}/bom-lines/{line_no}",
    tags=["decision"],
)
def upsert_project_bom_line(
    project_id: str,
    line_no: int,
    payload: ProjectBomLineUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("bom.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    service = ProjectBomService(session)
    try:
        line_id = service.upsert_line(project_id, line_no, payload)
        session.commit()
        return _json_safe(
            {
                "project_bom_line_id": line_id,
                "bom": service.list_lines(project_id),
            }
        )  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.delete(
    "/api/v1/projects/{project_id}/bom-lines/{line_no}",
    tags=["decision"],
)
def delete_project_bom_line(
    project_id: str,
    line_no: int,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("bom.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    service = ProjectBomService(session)
    try:
        service.delete_line(project_id, line_no)
        session.commit()
        return _json_safe(service.list_lines(project_id))  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/api/v1/projects/{project_id}/bom-lines/{line_no}/tariff-selections/{regime}",
    tags=["decision"],
)
def select_project_bom_mapping(
    project_id: str,
    line_no: int,
    regime: str,
    payload: ProjectBomMappingSelectionUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("bom.update"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    normalized_regime = regime.upper()
    if normalized_regime not in {"MFN", "ACFTA", "RCEP"}:
        raise HTTPException(status_code=422, detail=f"Unsupported regime {regime}")
    service = ProjectBomService(session)
    try:
        selection_id = service.select_mapping(
            project_id,
            line_no,
            normalized_regime,
            payload.mapping_code,
            payload.selected_by,
            payload.selection_note,
        )
        session.commit()
        return _json_safe(
            {
                "project_bom_tariff_selection_id": selection_id,
                "bom": service.list_lines(project_id),
            }
        )  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/v1/projects/{project_id}/bom-comparison/preview",
    tags=["calculation"],
)
def preview_project_bom_comparison(
    project_id: str,
    payload: ProjectBomComparisonRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = ProjectBomService(session).preview(
            project_id,
            requested_regimes=tuple(payload.requested_regimes),
            eligibility=payload.eligibility,
            sales_revenue=payload.sales_revenue,
            non_import_costs=payload.non_import_costs,
            recoverable_sst_fraction=payload.recoverable_sst_fraction,
        )
        return _json_safe(asdict(result))  # type: ignore[return-value]
    except (CalculationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/v1/projects/{project_id}/bom-comparison/run",
    tags=["calculation"],
    status_code=201,
)
def run_project_bom_comparison(
    project_id: str,
    payload: ProjectBomComparisonRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    service = ProjectBomService(session)
    try:
        project = DecisionRepository(session).get_project(project_id)
        result, request_payload = service.build_comparison(
            project_id,
            requested_regimes=tuple(payload.requested_regimes),
            eligibility=payload.eligibility,
            sales_revenue=payload.sales_revenue,
            non_import_costs=payload.non_import_costs,
            recoverable_sst_fraction=payload.recoverable_sst_fraction,
        )
        origin_iso2 = next(
            (
                str(item["origin_country_iso2"])
                for item in request_payload["items"]
                if item.get("origin_country_iso2")
            ),
            "CN",
        )
        audit = ComparisonPersistence(session).persist(
            request_payload=request_payload,
            result=result,
            engine_version=CalculationEngine.engine_version,
            decision_project_id=project["project_id"],
            vehicle_id=project["vehicle_id"],
            import_mode="PARTS",
            origin_country_iso2=origin_iso2,
            scenario_code="SCN-MY-ROUTE-04-PART-LEVEL",
        )
        session.commit()
        return {
            "result": _json_safe(asdict(result)),
            "audit": _json_safe(audit),
        }
    except (CalculationError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get("/api/v1/countries/{country_iso2}/rules", tags=["intelligence"])
def country_rules(
    country_iso2: str,
    session: Annotated[Session, Depends(get_db_session)],
    as_of: date | None = None,
    domain: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    current_date = _as_of(as_of)
    repository = IntelligenceRepository(session)
    _country_or_404(repository, country_iso2)
    result = repository.rules(
        iso2=country_iso2, as_of=current_date,
        domain=domain, status=status, keyword=q,
        page=page, page_size=page_size,
    )
    return _json_safe(
        {
            "country_iso2": country_iso2.upper(),
            "as_of": current_date,
            **result,
        }
    )  # type: ignore[return-value]


@router.get("/api/v1/countries/{country_iso2}/vehicle-tariffs", tags=["intelligence"])
def country_vehicle_tariffs(
    country_iso2: str,
    session: Annotated[Session, Depends(get_db_session)],
    as_of: date | None = None,
    route_code: str | None = None,
    origin_regime: str | None = None,
    agreement_code: str | None = None,
    hs6_code: str | None = None,
    powertrain: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    current_date = _as_of(as_of)
    repository = IntelligenceRepository(session)
    _country_or_404(repository, country_iso2)
    total, items = repository.vehicle_tariffs(
        iso2=country_iso2,
        as_of=current_date,
        route_code=route_code,
        origin_regime=origin_regime,
        agreement_code=agreement_code,
        hs6_code=hs6_code,
        powertrain=powertrain,
        limit=limit,
        offset=offset,
    )
    return _json_safe(
        {
            "country_iso2": country_iso2.upper(),
            "as_of": current_date,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    )  # type: ignore[return-value]


@router.get("/api/v1/ccus", tags=["classification"])
def list_ccus(
    session: Annotated[Session, Depends(get_db_session)],
    country: str = "MY",
    query: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    repository = IntelligenceRepository(session)
    _country_or_404(repository, country)
    total, items = repository.ccus(
        country_iso2=country, query=query, limit=limit, offset=offset
    )
    return _json_safe(
        {
            "country_iso2": country.upper(),
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    )  # type: ignore[return-value]


@router.get("/api/v1/ccus/{ccu_code}", tags=["classification"])
def get_ccu(
    ccu_code: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    item = IntelligenceRepository(session).ccu(ccu_code=ccu_code)
    if item is None:
        raise HTTPException(status_code=404, detail=f"CCU {ccu_code} not found")
    return _json_safe(item)  # type: ignore[return-value]


@router.get("/api/v1/ccus/{ccu_code}/tariff-options", tags=["classification"])
def get_ccu_tariff_options(
    ccu_code: str,
    session: Annotated[Session, Depends(get_db_session)],
    country: str = "MY",
    as_of: date | None = None,
) -> dict[str, object]:
    current_date = _as_of(as_of)
    repository = IntelligenceRepository(session)
    if repository.ccu(ccu_code=ccu_code) is None:
        raise HTTPException(status_code=404, detail=f"CCU {ccu_code} not found")
    _country_or_404(repository, country)
    items = repository.ccu_tariff_options(
        ccu_code=ccu_code, country_iso2=country, as_of=current_date
    )
    return _json_safe(
        {
            "country_iso2": country.upper(),
            "ccu_code": ccu_code,
            "as_of": current_date,
            "total": len(items),
            "items": items,
        }
    )  # type: ignore[return-value]


def _calculate_malaysia(
    payload: MalaysiaComparisonRequest,
    session: Session,
):
    repository = TariffRepository(session)
    ccu_codes = tuple(item.ccu_code for item in payload.items)
    try:
        options = repository.list_effective_options(
            country_iso2="MY",
            ccu_codes=ccu_codes,
            as_of=payload.import_date,
        )
        selections = {item.ccu_code: item.selected_mapping_codes for item in payload.items}
        selected = repository.require_explicit_selection(options, selections)
        request = ComparisonRequest(
            country_iso2="MY",
            import_date=payload.import_date,
            currency_code=payload.currency_code,
            items=tuple(
                ItemCostInput(
                    ccu_code=item.ccu_code,
                    customs_value=item.customs_value,
                    selected_rates=selected[item.ccu_code],
                    excise_amount=item.excise_amount,
                    additional_landed_cost=item.additional_landed_cost,
                    enterprise_inputs_complete=item.enterprise_inputs_complete,
                    gri_2a_review_complete=item.gri_2a_review_complete,
                )
                for item in payload.items
            ),
            requested_regimes=payload.requested_regimes,
            baseline_regime=payload.baseline_regime,
            allow_mfn_fallback=payload.allow_mfn_fallback,
            eligibility={
                regime: PreferenceEligibility(regime=regime, **value.model_dump())
                for regime, value in payload.eligibility.items()
            },
            profit=ProfitInput(**payload.profit.model_dump()),
        )
        result = CalculationEngine().compare(request)
    except (CalculationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.post("/calculations/malaysia/preview", tags=["calculation"])
def preview_malaysia_comparison(
    payload: MalaysiaComparisonRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    """Calculate without creating an operational or audit record."""

    result = _calculate_malaysia(payload, session)
    return _json_safe(asdict(result))  # type: ignore[return-value]


@router.post("/calculations/malaysia/run", tags=["calculation"])
def run_malaysia_comparison(
    payload: MalaysiaComparisonRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    """Calculate and persist the input snapshot, lines and audit trace."""

    result = _calculate_malaysia(payload, session)
    try:
        audit = ComparisonPersistence(session).persist(
            request_payload=payload.model_dump(mode="python"),
            result=result,
            engine_version=CalculationEngine.engine_version,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "result": _json_safe(asdict(result)),
        "audit": _json_safe(audit),
    }


@router.post(
    "/api/v1/projects/{project_id}/calculations/preview",
    tags=["project-calculation"],
)
def preview_project_calculation(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = ProjectCalculationService(session).preview(project_id)
        return _json_safe(result)  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/v1/projects/{project_id}/calculations/run",
    tags=["project-calculation"],
    status_code=201,
)
def run_project_calculation(
    project_id: str,
    session: Annotated[Session, Depends(get_db_session)],
    _permission: Annotated[object, Depends(require_permission("calculation.run"))],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> dict[str, object]:
    try:
        result = ProjectCalculationService(session).run(project_id)
        session.commit()
        return _json_safe(result)  # type: ignore[return-value]
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get(
    "/api/v1/calculations/{run_id}",
    tags=["project-calculation"],
)
def get_project_calculation(
    run_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        return _json_safe(
            ProjectCalculationService(session).get_run(run_id)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/api/v1/calculations/{run_id}/trace",
    tags=["project-calculation"],
)
def get_project_calculation_trace(
    run_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    items = ProjectCalculationService(session).get_trace(run_id)
    return _json_safe({"run_id": run_id, "items": items})  # type: ignore[return-value]


@router.get(
    "/api/v1/calculations/{run_id}/missing-data",
    tags=["project-calculation"],
)
def get_project_calculation_missing_data(
    run_id: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    items = ProjectCalculationService(session).get_missing(run_id)
    return _json_safe({"run_id": run_id, "items": items})  # type: ignore[return-value]
