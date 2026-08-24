from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.services.calculation_engine import (
    CalculationEngine,
    ComparisonRequest,
    ItemCostInput,
    PreferenceEligibility,
    ProfitInput,
)
from app.services.comparison_persistence import ComparisonPersistence
from app.services.tariff_repository import TariffRepository
from reconcile_malaysia_python_engine import (
    CCU_MAPPING_SELECTIONS,
    bom_values,
    database_url,
)


def main() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        options = TariffRepository(session).list_effective_options(
            country_iso2="MY",
            ccu_codes=tuple(CCU_MAPPING_SELECTIONS),
            as_of=date(2026, 7, 28),
        )
        selected = TariffRepository.require_explicit_selection(
            options, CCU_MAPPING_SELECTIONS
        )
        values = bom_values(session)
        request = ComparisonRequest(
            country_iso2="MY",
            import_date=date(2026, 7, 28),
            currency_code="MYR",
            items=tuple(
                ItemCostInput(
                    ccu_code=ccu_code,
                    customs_value=values[ccu_code],
                    selected_rates=selected[ccu_code],
                    excise_amount=Decimal(0),
                    enterprise_inputs_complete=False,
                    gri_2a_review_complete=False,
                )
                for ccu_code in CCU_MAPPING_SELECTIONS
            ),
            requested_regimes=("MFN", "ACFTA", "RCEP"),
            eligibility={
                regime: PreferenceEligibility(
                    regime=regime,
                    proof_valid=True,
                    origin_rule_compliance_confirmed=True,
                    nomenclature_correlation_confirmed=True,
                    enterprise_reviewed=False,
                    simulation_only=True,
                )
                for regime in ("ACFTA", "RCEP")
            },
            profit=ProfitInput(
                sales_revenue=Decimal(180000),
                non_import_costs=Decimal(20000),
            ),
        )
        result = CalculationEngine().compare(request)
        audit = ComparisonPersistence(session).persist(
            request_payload={
                "import_date": request.import_date,
                "currency_code": request.currency_code,
                "requested_regimes": request.requested_regimes,
                "smoke_test": True,
            },
            result=result,
            engine_version=CalculationEngine.engine_version,
        )
        session.flush()
        run_ids = [row["calculation_run_id"] for row in audit["runs"]]
        counts = (
            session.execute(
                text(
                    """
                SELECT
                  (SELECT count(*) FROM calc.calculation_run
                   WHERE calculation_run_id = ANY(:run_ids)) AS runs,
                  (SELECT count(*) FROM calc.calculation_line
                   WHERE calculation_run_id = ANY(:run_ids)) AS lines,
                  (SELECT count(*) FROM audit.decision_trace
                   WHERE calculation_run_id = ANY(:run_ids)) AS traces,
                  (SELECT count(*) FROM ai.llm_view_item
                   WHERE calculation_run_id = ANY(:run_ids)) AS llm_views
                """
                ),
                {"run_ids": run_ids},
            )
            .mappings()
            .one()
        )
        expected = {"runs": 3, "lines": 90, "traces": 21, "llm_views": 9}
        observed = {key: counts[key] for key in expected}
        if observed != expected:
            raise AssertionError(f"Persistence smoke test failed: {observed}")
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "observed": observed,
                    "transaction": "ROLLBACK_AFTER_SMOKE_TEST",
                },
                indent=2,
            )
        )
        session.rollback()


if __name__ == "__main__":
    main()
