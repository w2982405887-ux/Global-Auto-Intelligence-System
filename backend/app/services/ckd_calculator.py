"""CKD whole-kit tax scenario — two-stage model.

Stage 1 — IMPORT:  duty (MFN/ACFTA/RCEP) + conditional import SST
Stage 2 — LOCAL:   excise + finished-vehicle SST (not at import)
Stage 3 — FULL:    optional simulation (only when valuation ratios supplied,
                    and only for taxes with applied_rate > 0)

Uses classification + incentive + domestic_tax + valuation resolvers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.classification_resolver import (
    HsClassification,
    _fetch_tariff_lines,
    build_rule_reference,
    build_source_reference,
    classification_condition_warning,
    pick_best_national_code,
    malaysia_870360_excise_rate,
    malaysia_870360_excise_rate_by_conditions,
    resolve_hs6_prefix,
)
from app.services.incentive_resolver import (
    IncentiveResolver,
    IncentiveValidationResult,
    ResolvedTreatment,
)
from app.services.domestic_tax_resolver import DomesticTaxResolver
from app.services.valuation_engine import (
    FullCycleSimulation,
    FullCycleSimulationResults,
    ImportStageResult,
    NORMALIZED_BASE,
    ValuationEngine,
)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class ImportDutyOption:
    regime: str
    agreement_code: str | None
    national_tariff_code: str
    tariff_description: str
    rate: Decimal | None
    per_100: Decimal | None
    verification_status: str
    eligibility_note: str | None
    rule_reference: dict[str, Any] = field(default_factory=dict)
    source_reference: dict[str, Any] = field(default_factory=dict)


@dataclass
class CkdCalculationResult:
    country_iso2: str
    effective_date: date
    powertrain: str
    displacement_cc: int | None
    origin_country_iso2: str
    normalized_base: Decimal
    declaration_mode: str
    miti_ckd_ap_confirmed: bool

    # ① Classification
    hs_classification: HsClassification | None
    classification_note: str

    # ② Import stage
    import_duty_options: list[ImportDutyOption]
    import_sales_tax: ResolvedTreatment
    import_stage_results: list[ImportStageResult]

    # ③ Local assembly stage
    excise_duty: ResolvedTreatment
    finished_vehicle_sales_tax: ResolvedTreatment

    # ④ Full-cycle simulation
    full_cycle: FullCycleSimulationResults | None

    # Policy validation
    incentive_validation: IncentiveValidationResult | None
    notes: list[str]
    disclaimer: str
    calculation_explanation: list[dict[str, Any]] = field(default_factory=list)


# ── Scenario ────────────────────────────────────────────────────────

class CkdCalculator:
    ROUTE_CODE = "ROUTE-MY-02-CKD-WHOLE-KIT"

    def __init__(self, session: Session) -> None:
        self._session = session
        self._domestic = DomesticTaxResolver(session)
        self._incentive = IncentiveResolver(session)

    def calculate(
        self,
        *,
        effective_date: date,
        origin_country_iso2: str,
        powertrain: str,
        displacement_cc: int | None = None,
        body_type: str = "SEDAN",
        drive_type: str = "4WD_AWD",
        ckd_tariff_code: str | None = None,
        customs_value: Decimal | None = None,
        declaration_mode: str = "CKD_WHOLE_KIT_PENDING_RULING",
        miti_ckd_ap_confirmed: bool = False,
        selected_policy_codes: list[str] | None = None,
        excise_value_ratio: Decimal | None = None,
        sales_value_ratio: Decimal | None = None,
    ) -> CkdCalculationResult:
        origin = origin_country_iso2.upper()
        normalized = NORMALIZED_BASE
        policies = selected_policy_codes or []

        # ── 0. Validate incentive policies ──
        incentive_validation = self._incentive.validate_selected_policies(
            policies,
            effective_date=effective_date,
            powertrain=powertrain,
            import_mode="CKD",
        )

        # ── 1. Validate request consistency ──
        notes: list[str] = list(incentive_validation.notes)

        if declaration_mode == "CKD_WHOLE_KIT_WITH_RULING" and not ckd_tariff_code:
            raise ValueError(
                "已取得整套归类裁定时，CKD税号为必填。"
                "如尚未确定税号，请选择'拟按整套申报'或'尚未确定归类方式'。"
            )
        if declaration_mode == "CLASSIFICATION_PENDING" and ckd_tariff_code:
            notes.append(
                "申报方式为'尚未确定归类'但填入了税号；"
                "系统将基于提供的税号进行测算，但归类仍需海关确认。"
            )

        # ── 2. Resolve HS ──
        hs6_prefix = resolve_hs6_prefix(powertrain, displacement_cc)
        if hs6_prefix is None:
            raise ValueError(f"无法确定 {powertrain} {displacement_cc} 的HS6前缀")

        all_rows: list[dict[str, Any]] = []
        classification_note = ""

        if ckd_tariff_code:
            # User supplied a code — validate it
            all_rows = _fetch_tariff_lines(
                self._session,
                route_code=self.ROUTE_CODE,
                effective_date=effective_date,
                powertrain=powertrain,
                origin_country_iso2=origin,
                national_tariff_code=ckd_tariff_code,
            )
            if not all_rows:
                # Code not found — show available candidates
                all_candidates = _fetch_tariff_lines(
                    self._session,
                    route_code=self.ROUTE_CODE,
                    hs6_prefix=hs6_prefix,
                    effective_date=effective_date,
                    powertrain=powertrain,
                    origin_country_iso2=origin,
                )
                available = sorted({r["national_tariff_code"] for r in all_candidates})
                raise ValueError(
                    f"税号 {ckd_tariff_code} 在当前条件下未找到。"
                    f"可用CKD候选: {', '.join(available[:12])}"
                    f"{'...' if len(available) > 12 else ''}"
                )
            classification_note = "用户已确认税号"
        else:
            # Query candidates with LIKE filter
            all_rows = _fetch_tariff_lines(
                self._session,
                route_code=self.ROUTE_CODE,
                hs6_prefix=hs6_prefix,
                effective_date=effective_date,
                powertrain=powertrain,
                origin_country_iso2=origin,
            )
            if not all_rows:
                raise ValueError(
                    f"数据库中未找到匹配的CKD税号: powertrain={powertrain}"
                )
            if declaration_mode == "CLASSIFICATION_PENDING":
                classification_note = (
                    "归类待定 — 以下为候选税号，需海关确认后方可使用。"
                )
            else:
                classification_note = (
                    "未提供已确认税号 — 系统自动选择最佳匹配。"
                    "请取得海关归类裁定后确认。"
                )

        mfn_rows = [r for r in all_rows if r["origin_regime"] == "MFN"]
        fta_rows = [r for r in all_rows if r["origin_regime"] == "FTA"]
        mfn_best = pick_best_national_code(mfn_rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc) if mfn_rows else (
            pick_best_national_code(all_rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc) if all_rows else None
        )

        hs_classification = None
        if mfn_best:
            hs_classification = HsClassification(
                national_tariff_code=str(mfn_best["national_tariff_code"]),
                hs6_code=str(mfn_best["hs6_code"]),
                tariff_description=str(mfn_best["tariff_description"]),
                verification_status=str(mfn_best.get("verification_status", "UNVERIFIED")),
                source_code=str(mfn_best.get("source_code", "")),
                source_locator=str(mfn_best.get("source_locator", "")),
            )

        # ── 3. Import duty options ──
        import_duty_options = self._build_duty_options(mfn_best, fta_rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc)

        # ── 4. Import sales tax (CONDITIONAL EXEMPTION — NOT automatic 0%) ──
        ist_rule = self._domestic.get_import_sales_tax()
        ist_treatment = self._incentive.resolve_applied_treatment(
            tax_code="IMPORT_SALES_TAX",
            stage="AT_IMPORT",
            statutory_rate=ist_rule.statutory_rate if ist_rule else Decimal("0.10"),
            treatment=ist_rule.treatment if ist_rule else "CONDITIONAL_EXEMPTION",
            import_mode="CKD",
            powertrain=powertrain,
            effective_date=effective_date,
            resolved_policies=incentive_validation.resolved,
            is_ckd=True,
        )

        # Effective import SST rate for computation:
        # EXEMPT → None (not applicable)
        # CONDITIONAL_EXEMPTION with confirmed policy → applied_rate
        # CONDITIONAL_EXEMPTION without confirmation → statutory_rate (warning)
        ist_effective: Decimal | None = None
        if ist_treatment.applied_rate is not None:
            ist_effective = ist_treatment.applied_rate
        elif ist_treatment.treatment in ("EXEMPT", "NOT_AT_IMPORT"):
            ist_effective = None

        if ist_treatment.treatment == "CONDITIONAL_EXEMPTION" and not ist_treatment.approval_confirmed:
            notes.append(
                "CKD进口销售税豁免需经海关总监(DG)批准。"
                f"当前按法定税率 ({ist_treatment.statutory_rate}) 计算。"
                "请在取得批准后勾选 MY_CKD_IMPORT_SST_EXEMPTION。"
            )

        # ── 5. Import stage results (normalized) ──
        import_stage_results = ValuationEngine.calculate_import_stage(
            import_duty_options=[
                {
                    "agreement_code": o.agreement_code,
                    "rate": str(o.rate) if o.rate is not None else None,
                }
                for o in import_duty_options
            ],
            import_sales_tax_rate=ist_effective,
        )
        # Fix up: rebuild with full metadata
        import_stage_results = []
        for o in import_duty_options:
            duty_per_100 = _money(normalized * o.rate) if o.rate is not None else None
            ist_per_100 = (
                _money(normalized * ist_effective)
                if ist_effective is not None
                else Decimal("0")
            )
            import_total = None
            import_eff = None
            if duty_per_100 is not None:
                import_total = _money(duty_per_100 + ist_per_100)
                import_eff = _rate(import_total / normalized)

            import_stage_results.append(ImportStageResult(
                regime_label=o.agreement_code or "MFN",
                agreement_code=o.agreement_code,
                import_duty_rate=o.rate,
                import_duty_per_100=duty_per_100,
                import_sales_tax_rate=ist_effective,
                import_sales_tax_per_100=ist_per_100,
                import_total_per_100=import_total,
                import_effective_rate=import_eff,
            ))

        # ── 6. Local assembly: excise ──
        excise_rule = self._domestic.get_excise(import_mode="CKD", powertrain=powertrain)
        if mfn_best and excise_rule:
            code_excise = malaysia_870360_excise_rate(str(mfn_best.get("national_tariff_code", "")))
            condition_excise = malaysia_870360_excise_rate_by_conditions(body_type, drive_type, displacement_cc) if powertrain == "PHEV" else None
            if code_excise is not None:
                excise_rule.statutory_rate = Decimal(code_excise)
            elif condition_excise is not None:
                excise_rule.statutory_rate = Decimal(condition_excise)
            elif excise_rule.statutory_rate is None:
                mfn_excise = mfn_best.get("excise_duty_rate")
                if mfn_excise is not None:
                    excise_rule.statutory_rate = Decimal(str(mfn_excise))
            if excise_rule.statutory_rate is not None and excise_rule.treatment == "NOT_AT_IMPORT":
                excise_rule.treatment = "STATUTORY_RATE"
        excise_treatment = self._incentive.resolve_applied_treatment(
            tax_code="EXCISE",
            stage="LOCAL_ASSEMBLY",
            statutory_rate=excise_rule.statutory_rate if excise_rule else None,
            treatment=excise_rule.treatment if excise_rule else "NOT_AT_IMPORT",
            import_mode="CKD",
            powertrain=powertrain,
            effective_date=effective_date,
            resolved_policies=incentive_validation.resolved,
            is_ckd=True,
        )

        # ── 7. Local assembly: finished vehicle SST ──
        sst_rule = self._domestic.get_finished_vehicle_sst(powertrain=powertrain)
        finished_sst_treatment = self._incentive.resolve_applied_treatment(
            tax_code="FINISHED_VEHICLE_SST",
            stage="LOCAL_ASSEMBLY",
            statutory_rate=sst_rule.statutory_rate if sst_rule else Decimal("0.10"),
            treatment=sst_rule.treatment if sst_rule else "STATUTORY_RATE",
            import_mode="CKD",
            powertrain=powertrain,
            effective_date=effective_date,
            resolved_policies=incentive_validation.resolved,
            is_ckd=True,
        )

        # ── 8. Full-cycle simulation (dynamic missing inputs) ──
        full_cycle = ValuationEngine.simulate_full_cycle(
            import_duty_options=[
                {
                    "agreement_code": o.agreement_code,
                    "rate": str(o.rate) if o.rate is not None else None,
                }
                for o in import_duty_options
            ],
            excise_applied_rate=excise_treatment.applied_rate,
            finished_sst_applied_rate=finished_sst_treatment.applied_rate,
            excise_value_ratio=excise_value_ratio,
            sales_value_ratio=sales_value_ratio,
        )

        # ── 9. Warnings ──
        if not miti_ckd_ap_confirmed:
            notes.append(
                "未确认MITI CKD AP。CKD进口需取得MITI批准的CKD AP（进口许可证），"
                "与税务减免是两个独立条件。"
            )
        if declaration_mode == "CLASSIFICATION_PENDING":
            notes.append(
                "当前申报方式为'尚未确定'，返回结果仅供评估参考。"
                "实际税负需以海关正式归类和裁定为准。"
            )

        explanation = _build_ckd_explanation(
            hs_classification, import_duty_options, ist_treatment,
            excise_treatment, finished_sst_treatment, full_cycle,
        )

        return CkdCalculationResult(
            country_iso2="MY",
            effective_date=effective_date,
            powertrain=powertrain,
            displacement_cc=displacement_cc,
            origin_country_iso2=origin,
            normalized_base=normalized,
            declaration_mode=declaration_mode,
            miti_ckd_ap_confirmed=miti_ckd_ap_confirmed,
            hs_classification=hs_classification,
            classification_note=classification_note,
            import_duty_options=import_duty_options,
            import_sales_tax=ist_treatment,
            import_stage_results=import_stage_results,
            excise_duty=excise_treatment,
            finished_vehicle_sales_tax=finished_sst_treatment,
            full_cycle=full_cycle,
            incentive_validation=incentive_validation,
            calculation_explanation=explanation,
            notes=notes,
            disclaimer=(
                "本系统为信息咨询工具，不构成正式归类、报关或税务意见。"
                "CKD进口关税取决于原产国及适用协定（MFN/ACFTA/RCEP）。"
                "进口销售税豁免需经海关总监(DG)批准，非自动适用。"
                "消费税和成车销售税在本地组装阶段按各自核定价值征收，"
                "与进口价值的比例因车型和MITI批准而异。"
                "所有数值均为标准化税基(100)下的计算，非实际MYR金额。"
                "全流程模拟税负率分母为进口价值，"
                "实际消费税和销售税核定价值可能与进口价值不同。"
            ),
        )

    @staticmethod
    def _build_duty_options(
        mfn_best: dict[str, Any] | None,
        fta_rows: list[dict[str, Any]],
        *,
        body_type: str = "SEDAN",
        drive_type: str = "4WD_AWD",
        displacement_cc: int | None = None,
    ) -> list[ImportDutyOption]:
        options: list[ImportDutyOption] = []
        normalized = NORMALIZED_BASE

        if mfn_best:
            rate = (
                Decimal(str(mfn_best["import_duty_rate"]))
                if mfn_best.get("import_duty_rate") is not None else None
            )
            options.append(ImportDutyOption(
                regime="MFN", agreement_code=None,
                national_tariff_code=str(mfn_best["national_tariff_code"]),
                tariff_description=str(mfn_best["tariff_description"]),
                rate=rate,
                per_100=_money(normalized * rate) if rate is not None else None,
                verification_status=str(mfn_best.get("verification_status", "UNVERIFIED")),
                eligibility_note=None,
                rule_reference=build_rule_reference(mfn_best),
                source_reference=build_source_reference(mfn_best),
            ))

        fta_by_agreement: dict[str, list[dict[str, Any]]] = {}
        for row in fta_rows:
            ag = row.get("agreement_code") or "FTA"
            fta_by_agreement.setdefault(ag, []).append(row)

        for ag, rows in sorted(fta_by_agreement.items()):
            best = pick_best_national_code(rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc)
            if best is None:
                continue
            rate = (
                Decimal(str(best["import_duty_rate"]))
                if best.get("import_duty_rate") is not None else None
            )
            eligibility = best.get("eligibility_condition") or {}
            proof = eligibility.get("proof_of_origin", "原产地证明")

            options.append(ImportDutyOption(
                regime="FTA", agreement_code=ag,
                national_tariff_code=str(best["national_tariff_code"]),
                tariff_description=str(best["tariff_description"]),
                rate=rate,
                per_100=_money(normalized * rate) if rate is not None else None,
                verification_status=str(best.get("verification_status", "UNVERIFIED")),
                eligibility_note=f"需提供 {proof} 并满足原产地规则",
                rule_reference=build_rule_reference(best),
                source_reference=build_source_reference(best),
            ))

        return options


# ── Explanation builder ─────────────────────────────────────────────

def _build_ckd_explanation(
    hs: HsClassification | None,
    duty_opts: list[ImportDutyOption],
    ist: ResolvedTreatment,
    excise: ResolvedTreatment,
    sst: ResolvedTreatment,
    full_cycle: Any | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []

    if hs:
        steps.append({
            "sequence": 1, "step_type": "CLASSIFICATION",
            "decision": f"CKD HS {hs.national_tariff_code} — {hs.tariff_description}",
            "basis": "数据库匹配 CKD 整套税号",
            "input_reference": [],
            "confidence": 1.0,
            "source_id": hs.source_code or "",
        })

    best = duty_opts[0] if duty_opts else None
    if best:
        steps.append({
            "sequence": 2, "step_type": "FTA_SELECTION",
            "decision": f"进口关税 — {best.agreement_code or 'MFN'} 适用",
            "reason": " / ".join(
                [f"{o.agreement_code or 'MFN'}={(o.rate * 100) if o.rate else '?'}%"
                 for o in duty_opts if o.rate]
            ),
            "input_reference": [],
            "confidence": 0.95 if len(duty_opts) > 1 else 1.0,
            "source_id": best.source_reference.get("source_id", "") if best.source_reference else "",
        })

    steps.append({
        "sequence": 3, "step_type": "DOMESTIC_TAX",
        "decision": (
            f"进口销售税 {ist.treatment}，"
            f"消费税 {excise.treatment}，"
            f"成车销售税 {sst.treatment}"
        ),
        "basis": "CKD: excise_treatment=NOT_AT_IMPORT, import_sst=CONDITIONAL_EXEMPTION",
        "input_reference": [
            {"field": "import_mode", "value": "CKD", "source": "system"},
        ],
        "confidence": 1.0,
        "source_id": "",
    })

    if full_cycle and full_cycle.available:
        steps.append({
            "sequence": 4, "step_type": "SIMULATION",
            "decision": "全流程模拟已计算",
            "basis": f"使用估值系数: excise={full_cycle.results[0].excise_value_ratio_used if full_cycle.results else 'N/A'}, sales={full_cycle.results[0].sales_value_ratio_used if full_cycle.results else 'N/A'}",
            "input_reference": [
                {"field": "excise_value_ratio", "source": "user_input"},
                {"field": "sales_value_ratio", "source": "user_input"},
            ],
            "confidence": 0.6,
            "source_id": "",
        })

    return steps
