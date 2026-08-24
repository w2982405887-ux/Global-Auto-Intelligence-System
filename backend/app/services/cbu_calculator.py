"""CBU vehicle tax scenario — uses classification + incentive + valuation resolvers.

Import duty is regime-dependent (MFN/ACFTA/RCEP).
Excise and Sales Tax are Malaysian DOMESTIC taxes — same regardless of FTA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.classification_resolver import (
    ClassificationResolver,
    HsClassification,
    _fetch_tariff_lines,
    build_rule_reference,
    build_source_reference,
    classification_condition_warning,
    pick_best_national_code,
    malaysia_870360_excise_rate,
    resolve_hs6_prefix,
)
from app.services.incentive_resolver import (
    IncentiveResolver,
    IncentiveValidationResult,
    ResolvedTreatment,
)
from app.services.domestic_tax_resolver import DomesticTaxResolver, DomesticTaxRule
from app.services.valuation_engine import NORMALIZED_BASE, ValuationEngine


# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class ImportDutyOption:
    regime: str
    agreement_code: str | None
    national_tariff_code: str
    tariff_description: str
    rate: Decimal | None       # import duty rate
    per_100: Decimal | None    # normalized per 100
    verification_status: str
    eligibility_note: str | None
    rule_reference: dict[str, Any] = field(default_factory=dict)
    source_reference: dict[str, Any] = field(default_factory=dict)


@dataclass
class CombinedResult:
    regime_label: str
    agreement_code: str | None
    import_duty_rate: Decimal | None
    import_duty_per_100: Decimal | None
    excise_duty_rate: Decimal | None
    excise_duty_per_100: Decimal | None
    sales_tax_rate: Decimal | None
    sales_tax_per_100: Decimal | None
    total_per_100: Decimal | None
    effective_tax_rate: Decimal | None
    is_complete: bool
    unknown_items: list[str] = field(default_factory=list)


@dataclass
class CbuCalculationResult:
    country_iso2: str
    effective_date: date
    powertrain: str
    displacement_cc: int | None
    origin_country_iso2: str
    normalized_base: Decimal
    hs_classification: HsClassification | None
    import_duty_options: list[ImportDutyOption]
    excise_duty: ResolvedTreatment
    sales_tax: ResolvedTreatment
    combined_results: list[CombinedResult]
    incentive_validation: IncentiveValidationResult | None
    notes: list[str]
    disclaimer: str
    calculation_explanation: list[dict[str, Any]] = field(default_factory=list)


# ── Scenario ────────────────────────────────────────────────────────

class CbuCalculator:
    ROUTE_CODE = "ROUTE-MY-01-CBU"

    def __init__(self, session: Session) -> None:
        self._session = session
        self._classification = ClassificationResolver(session)
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
        customs_value: Decimal | None = None,
        selected_policy_codes: list[str] | None = None,
    ) -> CbuCalculationResult:
        origin = origin_country_iso2.upper()
        normalized = NORMALIZED_BASE
        policies = selected_policy_codes or []

        # 1. Validate incentive policies
        incentive_validation = self._incentive.validate_selected_policies(
            policies,
            effective_date=effective_date,
            powertrain=powertrain,
            import_mode="CBU",
        )

        # 2. Resolve HS classification
        hs6_prefix = resolve_hs6_prefix(powertrain, displacement_cc)
        if hs6_prefix is None:
            raise ValueError(f"无法确定 {powertrain} {displacement_cc} 的HS6前缀")

        all_rows = _fetch_tariff_lines(
            self._session,
            route_code=self.ROUTE_CODE,
            hs6_prefix=hs6_prefix,
            effective_date=effective_date,
            powertrain=powertrain,
            origin_country_iso2=origin,
        )
        if not all_rows:
            raise ValueError(f"数据库中未找到匹配的CBU税号: powertrain={powertrain}")

        mfn_rows = [r for r in all_rows if r["origin_regime"] == "MFN"]
        fta_rows = [r for r in all_rows if r["origin_regime"] == "FTA"]
        mfn_best = pick_best_national_code(mfn_rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc)

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

        # 3. Domestic tax rules
        excise_rule = self._domestic.get_excise(import_mode="CBU", powertrain=powertrain)
        sst_rule = self._domestic.get_sales_tax(import_mode="CBU", powertrain=powertrain)

        # If final 10-digit tariff code carries a known Malaysia 8703.60 excise subgroup,
        # prefer the subgroup rate. This avoids treating PHEV / engine-drive EREV as a
        # single flat powertrain bucket; pure electric range is not a 8703.60 divider.
        if mfn_best and excise_rule:
            code_excise = malaysia_870360_excise_rate(str(mfn_best.get("national_tariff_code", "")))
            if code_excise is not None:
                excise_rule.statutory_rate = Decimal(code_excise)
            elif excise_rule.statutory_rate is None:
                mfn_excise = mfn_best.get("excise_duty_rate")
                if mfn_excise is not None:
                    excise_rule.statutory_rate = Decimal(str(mfn_excise))

        # 4. Resolve applied treatments (with incentive overlay)
        excise_treatment = self._incentive.resolve_applied_treatment(
            tax_code="EXCISE", stage="AT_IMPORT",
            statutory_rate=excise_rule.statutory_rate if excise_rule else None,
            treatment=excise_rule.treatment if excise_rule else "UNKNOWN",
            import_mode="CBU", powertrain=powertrain,
            effective_date=effective_date,
            resolved_policies=incentive_validation.resolved,
        )
        sst_treatment = self._incentive.resolve_applied_treatment(
            tax_code="SALES_TAX", stage="AT_IMPORT",
            statutory_rate=sst_rule.statutory_rate if sst_rule else None,
            treatment=sst_rule.treatment if sst_rule else "UNKNOWN",
            import_mode="CBU", powertrain=powertrain,
            effective_date=effective_date,
            resolved_policies=incentive_validation.resolved,
        )

        # 5. Import duty options (MFN + FTAs)
        import_duty_options = self._build_duty_options(mfn_best, fta_rows, body_type=body_type, drive_type=drive_type, displacement_cc=displacement_cc)

        # 6. Combined results (normalized per 100)
        combined = self._build_combined(
            import_duty_options, excise_treatment.applied_rate,
            sst_treatment.applied_rate,
        )

        # 7. Notes
        notes: list[str] = list(incentive_validation.notes)
        warning = classification_condition_warning(mfn_best, body_type, drive_type)
        if warning:
            notes.append(warning)
        if displacement_cc is None and powertrain in (
            "ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV",
        ):
            notes.append("未提供排量，ICE/HEV/PHEV/EREV 消费税与排量直接相关。")
        # Build explanation
        explanation = _build_cbu_explanation(
            hs_classification, import_duty_options, excise_treatment, sst_treatment,
        )

        return CbuCalculationResult(
            country_iso2="MY",
            effective_date=effective_date,
            powertrain=powertrain,
            displacement_cc=displacement_cc,
            origin_country_iso2=origin,
            normalized_base=normalized,
            hs_classification=hs_classification,
            import_duty_options=import_duty_options,
            excise_duty=excise_treatment,
            sales_tax=sst_treatment,
            combined_results=combined,
            incentive_validation=incentive_validation,
            calculation_explanation=explanation,
            notes=notes,
            disclaimer=(
                "本系统为信息咨询工具，不构成正式归类、报关或税务意见。"
                "进口关税取决于原产国及适用协定（MFN/ACFTA/RCEP）。"
                "消费税和销售税为马来西亚国内税，不受FTA影响。"
                "所有数值均为标准化税基(100)下的计算，非实际MYR金额。"
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
                per_100=None if rate is None else (
                    NORMALIZED_BASE * rate
                ),
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
                per_100=None if rate is None else (
                    NORMALIZED_BASE * rate
                ),
                verification_status=str(best.get("verification_status", "UNVERIFIED")),
                eligibility_note=f"需提供 {proof} 并满足原产地规则",
                rule_reference=build_rule_reference(best),
                source_reference=build_source_reference(best),
            ))

        return options

    @staticmethod
    def _build_combined(
        options: list[ImportDutyOption],
        excise_rate: Decimal | None,
        sst_rate: Decimal | None,
    ) -> list[CombinedResult]:
        from decimal import ROUND_HALF_UP
        _m = lambda v: v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        _r = lambda v: v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        base = NORMALIZED_BASE

        results: list[CombinedResult] = []
        for opt in options:
            duty = opt.per_100
            duty_rate = opt.rate

            excise = None
            if duty is not None and excise_rate is not None:
                excise_base = _m(base + duty)
                excise = _m(excise_base * excise_rate)

            sst = None
            if duty is not None and excise is not None and sst_rate is not None:
                sst_base = _m(base + duty + excise)
                sst = _m(sst_base * sst_rate)

            unknown: list[str] = []
            if duty_rate is None:
                unknown.append("进口关税")
            if excise_rate is None:
                unknown.append("消费税")

            complete = len(unknown) == 0
            total = None
            effective = None
            if complete and duty is not None and excise is not None and sst is not None:
                total = _m(duty + excise + sst)
                effective = _r(total / base)

            results.append(CombinedResult(
                regime_label=opt.agreement_code or "MFN",
                agreement_code=opt.agreement_code,
                import_duty_rate=duty_rate,
                import_duty_per_100=duty,
                excise_duty_rate=excise_rate,
                excise_duty_per_100=excise,
                sales_tax_rate=sst_rate,
                sales_tax_per_100=sst,
                total_per_100=total,
                effective_tax_rate=effective,
                is_complete=complete,
                unknown_items=unknown,
            ))

        return results


# ── Explanation builder ─────────────────────────────────────────────

def _build_cbu_explanation(
    hs: HsClassification | None,
    duty_opts: list[ImportDutyOption],
    excise: ResolvedTreatment,
    sst: ResolvedTreatment,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []

    if hs:
        steps.append({
            "sequence": 1, "step_type": "CLASSIFICATION",
            "decision": f"HS {hs.national_tariff_code} — {hs.tariff_description}",
            "basis": "数据库匹配，自动选择最佳乘用车税号",
            "input_reference": [],
            "confidence": 1.0,
            "source_id": hs.source_code or "",
        })

    best = duty_opts[0] if duty_opts else None
    if best:
        steps.append({
            "sequence": 2, "step_type": "FTA_SELECTION",
            "decision": f"{best.agreement_code or 'MFN'} 适用",
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
        "decision": f"消费税 {float(excise.applied_rate or 0)*100:.0f}%，销售税 {float(sst.applied_rate or 0)*100:.0f}%",
        "basis": f"消费税: {excise.treatment} / 销售税: {sst.treatment}",
        "input_reference": [
            {"field": "import_mode", "value": "CBU", "source": "system"},
        ],
        "confidence": 1.0 if excise.applied_rate is not None else 0.5,
        "source_id": "",
    })

    return steps
