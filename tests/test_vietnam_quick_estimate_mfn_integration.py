"""Focused tests for Vietnam CKD ordinary and preferential tariff visibility."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.services.vietnam_quick_estimate import VietnamQuickEstimateService


class _Row:
    def __init__(self, values: dict[str, Any]) -> None:
        self._mapping = values


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = [_Row(row) for row in rows]

    def __iter__(self):
        return iter(self._rows)


def _battery_row(*, regime: str, rate: str, agreement: str | None = None) -> dict[str, Any]:
    return {
        "ccu_code": "VN-CKD-TRACTION-BATTERY",
        "ccu_name_cn": "动力电池",
        "required_input_fields": ["part.battery_chemistry", "part.pack_or_cell_module"],
        "technical_qualifiers": {},
        "national_tariff_code": "85076033",
        "tariff_description": "Lithium-ion accumulator for a vehicle of Chapter 87 (87.03)",
        "duty_rate": Decimal(rate),
        "origin_regime": regime,
        "agreement_code": agreement,
        "eligibility_condition": {} if regime == "MFN" else {"origin_group": "CN", "requires_proof_of_origin": True},
        "effective_from": date(2027, 1, 1),
        "effective_to": date(2028, 1, 1),
        "verification_status": "VERIFIED",
        "source_code": f"VN-{regime}-BATTERY-2027",
        "document_title": "Official tariff schedule",
        "official_url": "https://official.example/vn/tariff",
        "source_locator": "8507.60.33",
        "clause_code": f"VN-{regime}-BATTERY-2027",
        "evidence_summary": "Official 2027 tariff row",
    }


class _FakeSession:
    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = str(statement)
        params = params or {}
        if "m.origin_regime::text='MFN'" in sql:
            return _Result([_battery_row(regime="MFN", rate="0.05")])
        if "a.agreement_code=:agreement" in sql and params.get("agreement") in {"ACFTA", "RCEP"}:
            return _Result([_battery_row(regime="FTA", agreement=params["agreement"], rate="0.00")])
        return _Result([])


def test_vietnam_component_candidates_include_mfn_and_applicable_ftas() -> None:
    service = VietnamQuickEstimateService(_FakeSession())

    groups = service.ckd_component_candidates("CN", date(2027, 1, 1), "BEV")
    battery = next(group for group in groups if group["ccu_code"] == "VN-CKD-TRACTION-BATTERY")

    regimes = {(row["regime"], row["national_tariff_code"], row["import_duty_rate"]) for row in battery["candidates"]}
    assert ("MFN", "85076033", Decimal("0.05")) in regimes
    assert ("ACFTA", "85076033", Decimal("0.00")) in regimes
    assert ("RCEP", "85076033", Decimal("0.00")) in regimes
    assert all(row["source_code"] for row in battery["candidates"])
    assert all(row["effective_from"] == date(2027, 1, 1) for row in battery["candidates"])


def test_vietnam_ckd_does_not_claim_mfn_not_ingested_when_mfn_row_exists() -> None:
    service = VietnamQuickEstimateService(_FakeSession())

    result = service.estimate(
        origin_country_iso2="CN",
        effective_date=date(2027, 1, 1),
        path="CKD",
        powertrain="BEV",
        cbu_tariff_code=None,
        ckd_declaration_mode="PARTS_BOM",
        customs_value_cbu=None,
        customs_value_ckd=Decimal("100"),
        ckd_component_tariff_codes={"VN-CKD-TRACTION-BATTERY": "85076033"},
    )
    ckd = result["paths"][0]

    assert ckd["statutory"]["regime"] == "MFN"
    assert ckd["statutory"]["tax_lines"]
    assert not any("MFN普通税率尚未完整入库" in item for item in ckd["statutory"]["unknown_tax_items"])
    battery_line = next(line for line in ckd["statutory"]["tax_lines"] if "动力电池" in line["tax"])
    assert battery_line["rate"] == Decimal("0.05")
    assert battery_line["source_code"] == "VN-MFN-BATTERY-2027"
    # The selected battery is usable evidence, but the full BOM remains
    # incomplete because the other major components were not selected.
    assert "主要零件MFN税率" in ckd["missing_items"]

