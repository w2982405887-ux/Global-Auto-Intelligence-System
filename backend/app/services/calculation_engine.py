from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.00000001")


class CalculationError(ValueError):
    """Raised when a deterministic calculation cannot safely continue."""


class Completeness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    RULING_CONFIRMED = "RULING_CONFIRMED"


@dataclass(frozen=True)
class EvidenceReference:
    source_clause_id: str
    source_code: str | None = None
    locator: str | None = None


@dataclass(frozen=True)
class TariffRateOption:
    regime: str
    mapping_code: str
    national_tariff_code: str
    duty_rate: Decimal | None
    sst_rate: Decimal | None
    verification_status: VerificationStatus
    effective_from: date
    effective_to: date | None
    tariff_version: str
    evidence: tuple[EvidenceReference, ...]
    classification_notes: str | None = None

    def is_effective(self, as_of: date) -> bool:
        return self.effective_from <= as_of and (
            self.effective_to is None or self.effective_to > as_of
        )


@dataclass(frozen=True)
class ItemCostInput:
    ccu_code: str
    customs_value: Decimal
    selected_rates: dict[str, TariffRateOption]
    excise_amount: Decimal | None = None
    additional_landed_cost: Decimal = Decimal("0")
    enterprise_inputs_complete: bool = False
    gri_2a_review_complete: bool = False


@dataclass(frozen=True)
class PreferenceEligibility:
    regime: str
    proof_valid: bool
    origin_rule_compliance_confirmed: bool
    nomenclature_correlation_confirmed: bool = True
    enterprise_reviewed: bool = False
    simulation_only: bool = False

    @property
    def eligible(self) -> bool:
        return (
            self.proof_valid
            and self.origin_rule_compliance_confirmed
            and self.nomenclature_correlation_confirmed
        )


@dataclass(frozen=True)
class ProfitInput:
    sales_revenue: Decimal | None = None
    non_import_costs: Decimal | None = None
    recoverable_sst_fraction: Decimal = Decimal("0")


@dataclass(frozen=True)
class ComparisonRequest:
    country_iso2: str
    import_date: date
    currency_code: str
    items: tuple[ItemCostInput, ...]
    requested_regimes: tuple[str, ...]
    eligibility: dict[str, PreferenceEligibility] = field(default_factory=dict)
    profit: ProfitInput = field(default_factory=ProfitInput)
    baseline_regime: str = "MFN"
    allow_mfn_fallback: bool = True


@dataclass(frozen=True)
class TaxLineResult:
    ccu_code: str
    requested_regime: str
    applied_regime: str
    mapping_code: str
    national_tariff_code: str
    customs_value: Decimal
    duty_rate: Decimal
    import_duty: Decimal
    excise_amount: Decimal
    sst_base: Decimal
    sst_rate: Decimal
    sst_amount: Decimal
    gross_import_tax: Decimal
    recoverable_tax: Decimal
    net_import_tax: Decimal
    verification_status: VerificationStatus
    evidence: tuple[EvidenceReference, ...]


@dataclass(frozen=True)
class MissingData:
    field_path: str
    description: str
    blocking_scope: str
    priority: str
    owner: str


@dataclass(frozen=True)
class ScenarioResult:
    requested_regime: str
    applied_regime: str
    fallback_applied: bool
    completeness: Completeness
    currency_code: str
    customs_value: Decimal
    gross_import_tax: Decimal | None
    recoverable_tax: Decimal | None
    net_import_tax: Decimal | None
    effective_gross_tax_rate: Decimal | None
    effective_net_tax_rate: Decimal | None
    landed_cost: Decimal | None
    total_cost: Decimal | None
    sales_revenue: Decimal | None
    gross_profit: Decimal | None
    gross_profit_margin: Decimal | None
    tax_saving_vs_baseline: Decimal | None
    profit_uplift_vs_baseline: Decimal | None
    lines: tuple[TaxLineResult, ...]
    missing_data: tuple[MissingData, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonResult:
    baseline_regime: str
    currency_code: str
    scenarios: tuple[ScenarioResult, ...]
    decision_summary: dict[str, Any]


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)


class CalculationEngine:
    """Deterministic automotive import-tax and profit comparison engine.

    The engine never chooses a final HS code. Every item must carry one explicit
    mapping selection per regime. Missing, expired or null-rate mappings block
    that scenario instead of being guessed.
    """

    engine_version = "python-comparison-0.2.0"

    def compare(self, request: ComparisonRequest) -> ComparisonResult:
        self._validate_request(request)

        ordered_regimes = tuple(
            dict.fromkeys((request.baseline_regime, *request.requested_regimes))
        )
        preliminary = tuple(self._calculate_scenario(request, regime) for regime in ordered_regimes)
        baseline = next(
            result for result in preliminary if result.requested_regime == request.baseline_regime
        )
        scenarios = tuple(self._add_baseline_comparison(result, baseline) for result in preliminary)
        viable = [
            result
            for result in scenarios
            if result.net_import_tax is not None and result.completeness is not Completeness.BLOCKED
        ]
        lowest_tax = (
            min(viable, key=lambda result: result.net_import_tax or Decimal("Infinity"))
            if viable
            else None
        )
        profitable = [result for result in viable if result.gross_profit is not None]
        highest_profit = (
            max(profitable, key=lambda result: result.gross_profit or Decimal("-Infinity"))
            if profitable
            else None
        )
        return ComparisonResult(
            baseline_regime=request.baseline_regime,
            currency_code=request.currency_code,
            scenarios=scenarios,
            decision_summary={
                "lowest_net_tax_requested_regime": (
                    lowest_tax.requested_regime if lowest_tax else None
                ),
                "lowest_net_tax_applied_regime": (
                    lowest_tax.applied_regime if lowest_tax else None
                ),
                "highest_profit_requested_regime": (
                    highest_profit.requested_regime if highest_profit else None
                ),
                "all_results_operationally_complete": all(
                    result.completeness is Completeness.COMPLETE for result in scenarios
                ),
                "engine_version": self.engine_version,
                "warning": (
                    "Ranking is decision support only. A preferential scenario is usable "
                    "only when its eligibility and classification evidence is complete."
                ),
            },
        )

    def _validate_request(self, request: ComparisonRequest) -> None:
        if request.country_iso2 != "MY":
            raise CalculationError("This engine profile currently supports Malaysia only")
        if not request.items:
            raise CalculationError("At least one CCU item is required")
        if request.baseline_regime not in request.requested_regimes:
            # The engine inserts the baseline automatically, so this is allowed.
            pass
        if len({item.ccu_code for item in request.items}) != len(request.items):
            raise CalculationError("Each CCU may appear only once in a comparison request")
        for item in request.items:
            if item.customs_value < 0 or item.additional_landed_cost < 0:
                raise CalculationError(f"Negative cost is not allowed for {item.ccu_code}")
            if item.excise_amount is not None and item.excise_amount < 0:
                raise CalculationError(f"Negative excise is not allowed for {item.ccu_code}")
        if not Decimal("0") <= request.profit.recoverable_sst_fraction <= Decimal("1"):
            raise CalculationError("recoverable_sst_fraction must be between 0 and 1")
        if request.profit.sales_revenue is not None and request.profit.sales_revenue < 0:
            raise CalculationError("sales_revenue cannot be negative")
        if request.profit.non_import_costs is not None and request.profit.non_import_costs < 0:
            raise CalculationError("non_import_costs cannot be negative")

    def _calculate_scenario(
        self,
        request: ComparisonRequest,
        requested_regime: str,
    ) -> ScenarioResult:
        missing: list[MissingData] = []
        warnings: list[str] = []
        applied_regime = requested_regime
        fallback_applied = False

        if requested_regime != request.baseline_regime:
            eligibility = request.eligibility.get(requested_regime)
            if eligibility is None or not eligibility.eligible:
                missing.append(
                    MissingData(
                        field_path=f"origin.{requested_regime.lower()}.eligibility",
                        description=(
                            f"{requested_regime} proof and product-specific origin-rule "
                            "compliance have not both been confirmed."
                        ),
                        blocking_scope=f"{requested_regime}_PREFERENCE",
                        priority="P0",
                        owner="ENTERPRISE_FTA_OWNER",
                    )
                )
                if request.allow_mfn_fallback:
                    applied_regime = request.baseline_regime
                    fallback_applied = True
                    warnings.append(
                        f"{requested_regime} preference blocked; "
                        f"{request.baseline_regime} fallback applied."
                    )
                else:
                    return self._blocked_result(
                        request, requested_regime, applied_regime, missing, warnings
                    )
            elif eligibility.simulation_only or not eligibility.enterprise_reviewed:
                warnings.append(
                    f"{requested_regime} eligibility is simulated or not enterprise-reviewed."
                )

        lines: list[TaxLineResult] = []
        is_partial = bool(missing)
        for item in request.items:
            option = item.selected_rates.get(applied_regime)
            if option is None:
                missing.append(
                    MissingData(
                        field_path=(f"items[{item.ccu_code}].selected_rates[{applied_regime}]"),
                        description="No explicit tariff mapping was selected.",
                        blocking_scope="TAX_CALCULATION",
                        priority="P0",
                        owner="CUSTOMS_CLASSIFICATION_OWNER",
                    )
                )
                return self._blocked_result(
                    request, requested_regime, applied_regime, missing, warnings
                )
            if option.regime != applied_regime:
                raise CalculationError(
                    f"{item.ccu_code} mapping regime {option.regime} does not match "
                    f"applied regime {applied_regime}"
                )
            if not option.is_effective(request.import_date):
                missing.append(
                    MissingData(
                        field_path=f"mapping.{option.mapping_code}.effective_period",
                        description="Selected tariff mapping is not effective on import date.",
                        blocking_scope="TAX_CALCULATION",
                        priority="P0",
                        owner="PUBLIC_POLICY_OWNER",
                    )
                )
                return self._blocked_result(
                    request, requested_regime, applied_regime, missing, warnings
                )
            if option.duty_rate is None or option.sst_rate is None:
                missing.append(
                    MissingData(
                        field_path=f"mapping.{option.mapping_code}.rate",
                        description="Duty or SST rate is missing; the engine will not guess.",
                        blocking_scope="TAX_CALCULATION",
                        priority="P0",
                        owner="PUBLIC_POLICY_OWNER",
                    )
                )
                return self._blocked_result(
                    request, requested_regime, applied_regime, missing, warnings
                )
            if not option.evidence:
                missing.append(
                    MissingData(
                        field_path=f"mapping.{option.mapping_code}.source_clause",
                        description="The selected rate has no source-clause evidence.",
                        blocking_scope="AUDITABILITY",
                        priority="P0",
                        owner="PUBLIC_POLICY_OWNER",
                    )
                )
                return self._blocked_result(
                    request, requested_regime, applied_regime, missing, warnings
                )
            if option.verification_status not in (
                VerificationStatus.VERIFIED,
                VerificationStatus.RULING_CONFIRMED,
            ):
                is_partial = True
                warnings.append(
                    f"{item.ccu_code} uses {option.verification_status} mapping "
                    f"{option.mapping_code}."
                )
            if not item.enterprise_inputs_complete:
                is_partial = True
                missing.append(
                    MissingData(
                        field_path=f"items[{item.ccu_code}].enterprise_required_inputs",
                        description="Use-time enterprise technical fields are incomplete.",
                        blocking_scope="OPERATIONAL_CLASSIFICATION",
                        priority="P0",
                        owner="ENTERPRISE_ENGINEERING_AND_CUSTOMS",
                    )
                )
            if not item.gri_2a_review_complete:
                is_partial = True
                missing.append(
                    MissingData(
                        field_path=f"items[{item.ccu_code}].gri_2a_review",
                        description="Shipment-level GRI 2(a) review is incomplete.",
                        blocking_scope="WHOLE_SHIPMENT_CLASSIFICATION",
                        priority="P0",
                        owner="ENTERPRISE_CUSTOMS_OWNER",
                    )
                )
            excise = item.excise_amount
            if excise is None:
                excise = Decimal("0")
                is_partial = True
                missing.append(
                    MissingData(
                        field_path=f"items[{item.ccu_code}].excise_assessment",
                        description=(
                            "No executable excise assessment was provided. Zero is used "
                            "only for a partial comparison and is not an exemption conclusion."
                        ),
                        blocking_scope="EXCISE_ACCURACY",
                        priority="P0",
                        owner="PUBLIC_TAX_OWNER",
                    )
                )
            duty = _money(item.customs_value * option.duty_rate)
            sst_base = _money(item.customs_value + duty + excise)
            sst = _money(sst_base * option.sst_rate)
            recoverable = _money(sst * request.profit.recoverable_sst_fraction)
            gross_tax = _money(duty + excise + sst)
            lines.append(
                TaxLineResult(
                    ccu_code=item.ccu_code,
                    requested_regime=requested_regime,
                    applied_regime=applied_regime,
                    mapping_code=option.mapping_code,
                    national_tariff_code=option.national_tariff_code,
                    customs_value=_money(item.customs_value),
                    duty_rate=_rate(option.duty_rate),
                    import_duty=duty,
                    excise_amount=_money(excise),
                    sst_base=sst_base,
                    sst_rate=_rate(option.sst_rate),
                    sst_amount=sst,
                    gross_import_tax=gross_tax,
                    recoverable_tax=recoverable,
                    net_import_tax=_money(gross_tax - recoverable),
                    verification_status=option.verification_status,
                    evidence=option.evidence,
                )
            )

        customs_value = _money(sum((line.customs_value for line in lines), Decimal("0")))
        gross_tax = _money(sum((line.gross_import_tax for line in lines), Decimal("0")))
        recoverable_tax = _money(sum((line.recoverable_tax for line in lines), Decimal("0")))
        net_tax = _money(gross_tax - recoverable_tax)
        additional_landed = _money(
            sum((item.additional_landed_cost for item in request.items), Decimal("0"))
        )
        landed_cost = _money(customs_value + gross_tax + additional_landed)
        non_import_costs = request.profit.non_import_costs
        total_cost = (
            _money(landed_cost + non_import_costs) if non_import_costs is not None else None
        )
        revenue = request.profit.sales_revenue
        gross_profit = (
            _money(revenue - total_cost) if revenue is not None and total_cost is not None else None
        )
        margin = None
        if gross_profit is not None and revenue is not None and revenue != 0:
            margin = _rate(gross_profit / revenue)
        if revenue is None or non_import_costs is None:
            is_partial = True
            missing.append(
                MissingData(
                    field_path="profit.sales_revenue_and_non_import_costs",
                    description=(
                        "Sales revenue or non-import costs are missing; tax comparison is "
                        "available but profit comparison is incomplete."
                    ),
                    blocking_scope="PROFIT_COMPARISON",
                    priority="P0",
                    owner="ENTERPRISE_FINANCE_OWNER",
                )
            )
        eligibility = request.eligibility.get(requested_regime)
        if (
            requested_regime != request.baseline_regime
            and eligibility is not None
            and (eligibility.simulation_only or not eligibility.enterprise_reviewed)
        ):
            is_partial = True
        return ScenarioResult(
            requested_regime=requested_regime,
            applied_regime=applied_regime,
            fallback_applied=fallback_applied,
            completeness=Completeness.PARTIAL if is_partial else Completeness.COMPLETE,
            currency_code=request.currency_code,
            customs_value=customs_value,
            gross_import_tax=gross_tax,
            recoverable_tax=recoverable_tax,
            net_import_tax=net_tax,
            effective_gross_tax_rate=_rate(gross_tax / customs_value),
            effective_net_tax_rate=_rate(net_tax / customs_value),
            landed_cost=landed_cost,
            total_cost=total_cost,
            sales_revenue=revenue,
            gross_profit=gross_profit,
            gross_profit_margin=margin,
            tax_saving_vs_baseline=None,
            profit_uplift_vs_baseline=None,
            lines=tuple(lines),
            missing_data=tuple(missing),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _blocked_result(
        self,
        request: ComparisonRequest,
        requested_regime: str,
        applied_regime: str,
        missing: list[MissingData],
        warnings: list[str],
    ) -> ScenarioResult:
        return ScenarioResult(
            requested_regime=requested_regime,
            applied_regime=applied_regime,
            fallback_applied=applied_regime != requested_regime,
            completeness=Completeness.BLOCKED,
            currency_code=request.currency_code,
            customs_value=_money(sum((item.customs_value for item in request.items), Decimal("0"))),
            gross_import_tax=None,
            recoverable_tax=None,
            net_import_tax=None,
            effective_gross_tax_rate=None,
            effective_net_tax_rate=None,
            landed_cost=None,
            total_cost=None,
            sales_revenue=request.profit.sales_revenue,
            gross_profit=None,
            gross_profit_margin=None,
            tax_saving_vs_baseline=None,
            profit_uplift_vs_baseline=None,
            lines=(),
            missing_data=tuple(missing),
            warnings=tuple(warnings),
        )

    def _add_baseline_comparison(
        self,
        result: ScenarioResult,
        baseline: ScenarioResult,
    ) -> ScenarioResult:
        tax_saving = (
            _money(baseline.net_import_tax - result.net_import_tax)
            if baseline.net_import_tax is not None and result.net_import_tax is not None
            else None
        )
        profit_uplift = (
            _money(result.gross_profit - baseline.gross_profit)
            if baseline.gross_profit is not None and result.gross_profit is not None
            else None
        )
        return ScenarioResult(
            **{
                **result.__dict__,
                "tax_saving_vs_baseline": tax_saving,
                "profit_uplift_vs_baseline": profit_uplift,
            }
        )
