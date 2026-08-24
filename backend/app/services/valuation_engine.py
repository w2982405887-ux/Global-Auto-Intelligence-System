"""Normalized tax valuation engine.

All calculations use a standard base of 100 (normalized import value).
Actual MYR amounts are only returned when the user supplies customs_value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


NORMALIZED_BASE = Decimal("100")


@dataclass
class ImportStageResult:
    """One regime's import-stage tax burden (normalized per 100)."""
    regime_label: str
    agreement_code: str | None
    import_duty_rate: Decimal | None
    import_duty_per_100: Decimal | None         # normalized
    import_sales_tax_rate: Decimal | None
    import_sales_tax_per_100: Decimal | None    # normalized
    import_total_per_100: Decimal | None        # duty + import SST
    import_effective_rate: Decimal | None


@dataclass
class FullCycleSimulation:
    """Per-regime full-cycle simulation (only when ratios supplied)."""
    regime_label: str
    agreement_code: str | None
    import_duty_per_100: Decimal | None
    import_sales_tax_per_100: Decimal
    excise_per_100: Decimal | None
    finished_sst_per_100: Decimal | None
    import_total_per_100: Decimal | None
    full_cycle_total_per_100: Decimal | None
    import_effective_rate: Decimal | None
    simulated_full_cycle_rate: Decimal | None
    # Metadata
    excise_value_ratio_used: Decimal | None
    sales_value_ratio_used: Decimal | None
    metric_name: str = "SIMULATED_FULL_CYCLE_TAX_BURDEN_OVER_IMPORT_VALUE"
    denominator: str = "CKD_IMPORT_CUSTOMS_VALUE"
    is_statutory_rate: bool = False


@dataclass
class NormalizedResult:
    """Normalized tax calculation container."""
    normalized_base: Decimal = NORMALIZED_BASE
    # Per-regime import stage
    import_stage: list[ImportStageResult] = field(default_factory=list)
    # Full-cycle (only if ratios supplied + rates available)
    full_cycle_available: bool = False
    full_cycle_results: list[FullCycleSimulation] | None = None


class ValuationEngine:
    """Calculate normalized tax burden. Never converts to MYR unless
    the caller provides an actual customs_value."""

    @staticmethod
    def calculate_import_stage(
        import_duty_options: list[dict[str, Any]],
        import_sales_tax_rate: Decimal | None,
    ) -> list[ImportStageResult]:
        """Calculate per-regime import-stage tax burden on base=100."""
        results: list[ImportStageResult] = []
        for opt in import_duty_options:
            duty_rate = opt.get("rate")
            duty_rate_d = Decimal(str(duty_rate)) if duty_rate is not None else None
            duty_per_100 = (
                _money(NORMALIZED_BASE * duty_rate_d)
                if duty_rate_d is not None
                else None
            )

            ist_rate = import_sales_tax_rate  # could be None (EXEMPT)
            ist_per_100 = (
                _money(NORMALIZED_BASE * ist_rate)
                if ist_rate is not None
                else Decimal("0")
            )

            import_total = None
            import_eff = None
            if duty_per_100 is not None:
                import_total = _money(duty_per_100 + ist_per_100)
                import_eff = _rate(import_total / NORMALIZED_BASE)

            results.append(ImportStageResult(
                regime_label=opt.get("agreement_code") or "MFN",
                agreement_code=opt.get("agreement_code"),
                import_duty_rate=duty_rate_d,
                import_duty_per_100=duty_per_100,
                import_sales_tax_rate=import_sales_tax_rate,
                import_sales_tax_per_100=ist_per_100,
                import_total_per_100=import_total,
                import_effective_rate=import_eff,
            ))

        return results

    @staticmethod
    def simulate_full_cycle(
        import_duty_options: list[dict[str, Any]],
        *,
        excise_applied_rate: Decimal | None,
        finished_sst_applied_rate: Decimal | None,
        excise_value_ratio: Decimal | None = None,
        sales_value_ratio: Decimal | None = None,
    ) -> FullCycleSimulationResults:
        """Simulate full-cycle tax burden per regime.

        Requires excise_value_ratio and sales_value_ratio when the
        corresponding applied rate > 0. If rate == 0 (exemption confirmed),
        the ratio is not needed.
        """
        results: list[FullCycleSimulation] = []
        need_excise_ratio = (
            excise_applied_rate is not None
            and excise_applied_rate > 0
            and excise_value_ratio is None
        )
        need_sales_ratio = (
            finished_sst_applied_rate is not None
            and finished_sst_applied_rate > 0
            and sales_value_ratio is None
        )
        missing_inputs: list[dict[str, str]] = []
        if need_excise_ratio:
            missing_inputs.append({
                "field": "excise_value_ratio",
                "description": "消费税核定价值 ÷ CKD进口价值",
                "reason": f"消费税适用税率为 {excise_applied_rate}，需估值系数方可计算全流程",
            })
        if need_sales_ratio:
            missing_inputs.append({
                "field": "sales_value_ratio",
                "description": "销售税计税价值 ÷ CKD进口价值",
                "reason": f"成车销售税适用税率为 {finished_sst_applied_rate}，需估值系数方可计算全流程",
            })

        can_compute = not (need_excise_ratio or need_sales_ratio)

        for opt in import_duty_options:
            duty_rate_d = (
                Decimal(str(opt["rate"]))
                if opt.get("rate") is not None
                else None
            )
            duty_per_100 = (
                _money(NORMALIZED_BASE * duty_rate_d)
                if duty_rate_d is not None
                else None
            )
            ist_per_100 = Decimal("0")  # CKD import SST = EXEMPT

            import_total = (
                _money((duty_per_100 or Decimal("0")) + ist_per_100)
            )
            import_eff = _rate(import_total / NORMALIZED_BASE) if import_total else None

            if can_compute:
                excise_per_100 = (
                    _money(NORMALIZED_BASE * excise_value_ratio * excise_applied_rate)
                    if excise_applied_rate is not None
                    and excise_value_ratio is not None
                    and excise_applied_rate > 0
                    else None
                ) or Decimal("0")
                sst_per_100 = (
                    _money(NORMALIZED_BASE * sales_value_ratio * finished_sst_applied_rate)
                    if finished_sst_applied_rate is not None
                    and sales_value_ratio is not None
                    and finished_sst_applied_rate > 0
                    else None
                ) or Decimal("0")
                full_total = _money(
                    import_total + excise_per_100 + sst_per_100
                )
                full_rate = _rate(full_total / NORMALIZED_BASE)
            else:
                excise_per_100 = None
                sst_per_100 = None
                full_total = None
                full_rate = None

            results.append(FullCycleSimulation(
                regime_label=opt.get("agreement_code") or "MFN",
                agreement_code=opt.get("agreement_code"),
                import_duty_per_100=duty_per_100,
                import_sales_tax_per_100=ist_per_100,
                excise_per_100=excise_per_100,
                finished_sst_per_100=sst_per_100,
                import_total_per_100=import_total,
                full_cycle_total_per_100=full_total,
                import_effective_rate=import_eff,
                simulated_full_cycle_rate=full_rate,
                excise_value_ratio_used=excise_value_ratio if can_compute else None,
                sales_value_ratio_used=sales_value_ratio if can_compute else None,
            ))

        return FullCycleSimulationResults(
            available=can_compute,
            results=results,
            missing_inputs=missing_inputs,
        )


@dataclass
class FullCycleSimulationResults:
    available: bool
    results: list[FullCycleSimulation]
    missing_inputs: list[dict[str, str]] = field(default_factory=list)
