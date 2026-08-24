"""Regression tests for country-routed agent tools.

These tests use in-memory service fakes and never require PostgreSQL, a model
gateway, or an external web-search provider.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.agent.tools import cbu_tool, ckd_tool, policy_tool
from app.services import openclaw_client


class _FakeDb:
    def close(self) -> None:
        pass


def test_vietnam_cbu_requires_explicit_tariff_code_without_malaysia_fallback() -> None:
    result = cbu_tool.calculate_cbu_tax.invoke(
        {
            "country": "VN",
            "origin_country": "CN",
            "powertrain": "BEV",
            "effective_date": "2027-01-01",
        }
    )

    assert result["status"] == "CLASSIFICATION_SELECTION_REQUIRED"
    assert result["country"] == "VN"
    assert result["country_iso2"] == "VN"
    assert "cbu_tariff_code" in result["missing_information"]
    assert "MY" not in result.get("error", "")


def test_unknown_cbu_country_is_structured_and_not_routed_to_my() -> None:
    result = cbu_tool.calculate_cbu_tax.invoke(
        {"country": "ID", "powertrain": "BEV", "effective_date": "2027-01-01"}
    )

    assert result["status"] == "UNSUPPORTED_COUNTRY"
    assert result["country"] == "ID"
    assert result["country_iso2"] == "ID"
    assert result["supported_countries"] == ["MY", "VN"]


def test_vietnam_cbu_selected_code_uses_vietnam_service(monkeypatch) -> None:
    class FakeQuickEstimate:
        def __init__(self, _db):
            pass

        def estimate(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["country_iso2"] == "VN"
            assert kwargs["path"] == "CBU"
            assert kwargs["cbu_tariff_code"] == "8703809700"
            return {"country_iso2": "VN", "paths": [{"path": "CBU"}]}

    monkeypatch.setattr(cbu_tool, "SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr("app.services.quick_estimate.QuickEstimateService", FakeQuickEstimate)

    result = cbu_tool.calculate_cbu_tax.invoke(
        {
            "country": "Vietnam",
            "origin_country": "CN",
            "powertrain": "BEV",
            "cbu_tariff_code": "8703809700",
            "effective_date": "2027-01-01",
        }
    )

    assert result["country"] == "VN"
    assert result["country_iso2"] == "VN"
    assert result["origin_country"] == "CN"
    assert result["_meta"]["parameter_fingerprint"]


def test_vietnam_ckd_exposes_and_filters_nested_component_candidates(monkeypatch) -> None:
    class FakeQuickEstimate:
        def __init__(self, _db):
            pass

        def estimate(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["country_iso2"] == "VN"
            assert kwargs["path"] == "CKD"
            assert kwargs["ckd_declaration_mode"] == "PARTS_BOM"
            return {
                "country_iso2": "VN",
                "paths": [
                    {
                        "path": "CKD",
                        "missing_items": [
                            "BOM价值占比",
                            "VN-CKD-TRACTION-BATTERY尚未选择最终越南税号",
                            "VN-CKD-BODY尚未选择最终越南税号",
                        ],
                        "component_candidates": [
                            {
                                "ccu_code": "VN-CKD-TRACTION-BATTERY",
                                "ccu_name_cn": "动力电池",
                                "candidates": [
                                    {
                                        "agreement": "ACFTA",
                                        "national_tariff_code": "8507609000",
                                        "import_duty_rate": "0.00",
                                    }
                                ],
                            },
                            {
                                "ccu_code": "VN-CKD-BODY",
                                "ccu_name_cn": "车身",
                                "candidates": [],
                            },
                        ],
                    }
                ],
            }

    monkeypatch.setattr(ckd_tool, "SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr("app.services.quick_estimate.QuickEstimateService", FakeQuickEstimate)

    result = ckd_tool.calculate_ckd_tax.invoke(
        {
            "country": "VN",
            "origin_country": "CN",
            "powertrain": "BEV",
            "component_code": "VN-CKD-TRACTION-BATTERY",
            "effective_date": "2027-01-01",
        }
    )

    assert result["country"] == "VN"
    assert result["country_iso2"] == "VN"
    assert result["component_filter_applied"] == "VN-CKD-TRACTION-BATTERY"
    assert [x["ccu_code"] for x in result["component_candidates"]] == [
        "VN-CKD-TRACTION-BATTERY"
    ]
    assert result["paths"][0]["component_candidates"] == result["component_candidates"]
    # Candidate output is not an automatic final selection.
    assert "selected" not in result["component_candidates"][0]
    assert "VN-CKD-BODY尚未选择最终越南税号" not in result["missing_information"]
    assert "BOM价值占比" in result["missing_information"]
    assert result["_meta"]["depends_on_fields"][-1] == "component_code"


def test_unknown_ckd_country_and_policy_country_are_structured() -> None:
    ckd_result = ckd_tool.calculate_ckd_tax.invoke(
        {"country": "ID", "powertrain": "BEV", "effective_date": "2027-01-01"}
    )
    policy_result = policy_tool.search_policy_rules.invoke(
        {"country": "ID", "keyword": "EV"}
    )

    assert ckd_result["status"] == "UNSUPPORTED_COUNTRY"
    assert ckd_result["country_iso2"] == "ID"
    assert policy_result["status"] == "UNSUPPORTED_COUNTRY"
    assert policy_result["country_iso2"] == "ID"


def test_tavily_search_includes_requested_country_context(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"results": [{"title": "Official", "url": "https://example.test", "content": "text"}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, _url, *, json, headers):
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(openclaw_client.httpx, "Client", FakeClient)
    settings = SimpleNamespace(
        web_search_provider="tavily",
        tavily_api_key="test-key",
        web_search_max_results=5,
    )

    result = openclaw_client._web_search(
        settings,
        {"query": "2027 EV battery tariff", "country": "VN", "count": 1},
    )

    assert captured["json"]["query"].startswith("VN ")
    assert result["query"] == "2027 EV battery tariff"
    assert result["search_query"] == captured["json"]["query"]
    assert result["country"] == "VN"


def test_openclaw_specs_are_multi_country() -> None:
    specs = openclaw_client._tool_specs()
    assert "Malaysia CBU" not in specs["calculate_cbu_tax"].description
    assert "Malaysia CKD" not in specs["calculate_ckd_tax"].description
    assert "MY" in specs["calculate_cbu_tax"].description
    assert "VN" in specs["calculate_cbu_tax"].description
    ckd_schema = specs["calculate_ckd_tax"].parameters
    assert "component_code" in ckd_schema["properties"]
    assert "ckd_component_tariff_codes" in ckd_schema["properties"]
