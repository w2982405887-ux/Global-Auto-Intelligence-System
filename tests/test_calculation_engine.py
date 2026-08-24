import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.calculation_engine import (
    CalculationEngine,
    ComparisonRequest,
    Completeness,
    EvidenceReference,
    ItemCostInput,
    PreferenceEligibility,
    ProfitInput,
    TariffRateOption,
    VerificationStatus,
)


def option(
    regime: str,
    duty_rate: str,
    *,
    status: VerificationStatus = VerificationStatus.VERIFIED,
) -> TariffRateOption:
    return TariffRateOption(
        regime=regime,
        mapping_code=f"MAP-{regime}",
        national_tariff_code="8507603300",
        duty_rate=Decimal(duty_rate),
        sst_rate=Decimal("0.10"),
        verification_status=status,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        tariff_version=f"{regime}-2026",
        evidence=(EvidenceReference(source_clause_id="source-clause-1"),),
    )


class CalculationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CalculationEngine()
        self.item = ItemCostInput(
            ccu_code="CCU-HV-BATTERY-PACK",
            customs_value=Decimal(100000),
            selected_rates={
                "MFN": option("MFN", "0.20"),
                "ACFTA": option("ACFTA", "0.00"),
                "RCEP": option("RCEP", "0.20"),
            },
            excise_amount=Decimal(0),
            enterprise_inputs_complete=True,
            gri_2a_review_complete=True,
        )

    def request(
        self, eligibility: dict[str, PreferenceEligibility]
    ) -> ComparisonRequest:
        return ComparisonRequest(
            country_iso2="MY",
            import_date=date(2026, 7, 28),
            currency_code="MYR",
            items=(self.item,),
            requested_regimes=("MFN", "ACFTA", "RCEP"),
            eligibility=eligibility,
            profit=ProfitInput(
                sales_revenue=Decimal(160000),
                non_import_costs=Decimal(10000),
            ),
        )

    def test_mfn_tax_formula_and_profit(self) -> None:
        result = self.engine.compare(self.request({}))
        mfn = result.scenarios[0]
        self.assertEqual(mfn.gross_import_tax, Decimal("32000.00"))
        self.assertEqual(mfn.effective_gross_tax_rate, Decimal("0.32000000"))
        self.assertEqual(mfn.total_cost, Decimal("142000.00"))
        self.assertEqual(mfn.gross_profit, Decimal("18000.00"))

    def test_missing_fta_evidence_falls_back_to_mfn(self) -> None:
        result = self.engine.compare(self.request({}))
        acfta = next(x for x in result.scenarios if x.requested_regime == "ACFTA")
        self.assertTrue(acfta.fallback_applied)
        self.assertEqual(acfta.applied_regime, "MFN")
        self.assertEqual(acfta.gross_import_tax, Decimal("32000.00"))
        self.assertEqual(acfta.completeness, Completeness.PARTIAL)

    def test_eligible_acfta_changes_tax_and_profit(self) -> None:
        result = self.engine.compare(
            self.request(
                {
                    "ACFTA": PreferenceEligibility(
                        regime="ACFTA",
                        proof_valid=True,
                        origin_rule_compliance_confirmed=True,
                        enterprise_reviewed=True,
                    )
                }
            )
        )
        acfta = next(x for x in result.scenarios if x.requested_regime == "ACFTA")
        self.assertEqual(acfta.applied_regime, "ACFTA")
        self.assertEqual(acfta.gross_import_tax, Decimal("10000.00"))
        self.assertEqual(acfta.tax_saving_vs_baseline, Decimal("22000.00"))
        self.assertEqual(acfta.gross_profit, Decimal("40000.00"))
        self.assertEqual(acfta.profit_uplift_vs_baseline, Decimal("22000.00"))

    def test_candidate_mapping_forces_partial(self) -> None:
        candidate_item = ItemCostInput(
            **{
                **self.item.__dict__,
                "selected_rates": {
                    **self.item.selected_rates,
                    "ACFTA": option("ACFTA", "0", status=VerificationStatus.CANDIDATE),
                },
            }
        )
        request = ComparisonRequest(
            **{
                **self.request(
                    {
                        "ACFTA": PreferenceEligibility(
                            regime="ACFTA",
                            proof_valid=True,
                            origin_rule_compliance_confirmed=True,
                            enterprise_reviewed=True,
                        )
                    }
                ).__dict__,
                "items": (candidate_item,),
            }
        )
        acfta = next(
            x
            for x in self.engine.compare(request).scenarios
            if x.requested_regime == "ACFTA"
        )
        self.assertEqual(acfta.completeness, Completeness.PARTIAL)
        self.assertTrue(any("CANDIDATE" in warning for warning in acfta.warnings))

    def test_missing_rate_blocks_instead_of_guessing(self) -> None:
        broken = TariffRateOption(
            **{**option("MFN", "0.2").__dict__, "duty_rate": None}
        )
        item = ItemCostInput(
            **{
                **self.item.__dict__,
                "selected_rates": {**self.item.selected_rates, "MFN": broken},
            }
        )
        request = ComparisonRequest(**{**self.request({}).__dict__, "items": (item,)})
        mfn = self.engine.compare(request).scenarios[0]
        self.assertEqual(mfn.completeness, Completeness.BLOCKED)
        self.assertIsNone(mfn.gross_import_tax)


if __name__ == "__main__":
    unittest.main()
