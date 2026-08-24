"""Contract-level tests for country-routed agent tools.

These tests deliberately use fakes. They verify that an absent database row is
reported as an ingestion gap, not as a claim about the destination country's
law, and that a one-component request stays scoped to that component.
"""

from __future__ import annotations

from typing import Any

from app.agent.tools import ckd_tool


class _FakeDb:
    def close(self) -> None:
        pass

    def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("the contract test intentionally has no database")


def test_vietnam_battery_contract_keeps_regimes_and_marks_missing_data(monkeypatch) -> None:
    class FakeQuickEstimate:
        def __init__(self, _db):
            pass

        def estimate(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "country_iso2": "VN",
                "paths": [{
                    "path": "CKD",
                    "missing_items": [
                        "VN-CKD-TRACTION-BATTERY尚未选择最终越南税号",
                        "VN-CKD-BODY尚未选择最终越南税号",
                    ],
                    "component_candidates": [{
                        "ccu_code": "VN-CKD-TRACTION-BATTERY",
                        "ccu_name_cn": "动力电池",
                        "candidates": [{
                            "agreement": "ACFTA",
                            "national_tariff_code": "85076033",
                            "import_duty_rate": "0",
                            "verification_status": "CANDIDATE",
                        }],
                    }, {
                        "ccu_code": "VN-CKD-BODY",
                        "ccu_name_cn": "车身",
                        "candidates": [],
                    }],
                }],
                "missing_information": ["BOM价值占比"],
            }

    monkeypatch.setattr(ckd_tool, "SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.services.quick_estimate.QuickEstimateService", FakeQuickEstimate
    )

    result = ckd_tool.calculate_ckd_tax.invoke({
        "country": "VN",
        "origin_country": "CN",
        "powertrain": "BEV",
        "component_code": "VN-CKD-TRACTION-BATTERY",
        "effective_date": "2027-01-01",
    })

    contract = result["result_contract"]
    assert contract["destination_country"] == "VN"
    assert contract["component_code"] == "VN-CKD-TRACTION-BATTERY"
    assert contract["as_of"] == "2027-01-01"
    assert {item["regime"] for item in contract["candidates"]} == {
        "MFN", "ACFTA", "RCEP"
    }
    acfta = next(item for item in contract["candidates"] if item["regime"] == "ACFTA")
    assert acfta["candidate_tariff_code"] == "85076033"
    assert acfta["rate"] == "0"
    assert acfta["status"] == "CONDITIONAL"
    mfn = next(item for item in contract["candidates"] if item["regime"] == "MFN")
    assert mfn["status"] == "NOT_INGESTED"
    assert "法律不存在" not in mfn["reason"]
    assert "VN-CKD-BODY尚未选择最终越南税号" not in contract["missing_information"]
    assert result["contract_status"] == contract["status"]

