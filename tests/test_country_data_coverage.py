import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.tools import coverage_tool
from app.services.data_coverage_service import DataCoverageService


class FakeResult:
    def __init__(self, row: dict):
        self._row = row

    def mappings(self):
        return self

    def one(self):
        return self._row


class FakeSession:
    def __init__(self, row: dict):
        self.row = row
        self.calls: list[tuple[str, dict]] = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return FakeResult(self.row)

    def close(self):
        pass


class CountryDataCoverageTests(unittest.TestCase):
    def test_vietnam_cbu_uses_vietnam_route_and_requested_2027_date(self):
        session = FakeSession({"total": 1, "has_excise": 1, "has_sedan": 1})

        report = DataCoverageService(session).inspect(
            country_iso2="vn",
            powertrain="BEV",
            import_mode="CBU",
            effective_date="2027-10-11",
        )

        self.assertEqual(report.coverage_status, "FULL")
        self.assertEqual(len(session.calls), 1)
        sql, params = session.calls[0]
        self.assertIn("ROUTE-VN-01-CBU-NEW-PASSENGER", params["route_code"])
        self.assertEqual(params["country_iso2"], "VN")
        self.assertEqual(params["effective_date"], date(2027, 10, 11))
        self.assertNotIn("CURRENT_DATE", sql)
        self.assertIn("line.effective_from", sql)
        self.assertIn("route.effective_from", sql)

        dimension = report.available_dimensions[0]
        self.assertEqual(dimension["country_iso2"], "VN")
        self.assertEqual(dimension["route_code"], "ROUTE-VN-01-CBU-NEW-PASSENGER")
        self.assertEqual(dimension["effective_date"], "2027-10-11")
        self.assertNotIn("马来西亚", report.note)

    def test_vietnam_ckd_uses_major_parts_tables_and_date(self):
        session = FakeSession(
            {
                "total": 3,
                "has_duty": 3,
                "component_count": 2,
                "has_duty_components": 2,
                "has_mfn": 2,
                "has_fta": 2,
            }
        )

        report = DataCoverageService(session).inspect(
            country_iso2="VN",
            powertrain="BEV",
            import_mode="CKD",
            effective_date="2027-01-01",
        )

        self.assertEqual(report.coverage_status, "FULL")
        sql, params = session.calls[0]
        self.assertIn("customs.tariff_mapping", sql)
        self.assertIn("customs.customs_classification_unit", sql)
        self.assertIn("mapping.effective_from", sql)
        self.assertNotIn("ROUTE-MY", sql)
        self.assertEqual(params["effective_date"], date(2027, 1, 1))
        dimension = report.available_dimensions[0]
        self.assertEqual(dimension["country_iso2"], "VN")
        self.assertEqual(
            dimension["route_code"], "ROUTE-VN-CKD-PARTS-MAJOR-ESTIMATE"
        )
        self.assertEqual(dimension["effective_date"], "2027-01-01")
        self.assertNotIn("马来西亚", " ".join(report.known_issues) + report.note)

    def test_unsupported_country_never_queries_malaysia(self):
        session = FakeSession({"total": 1, "has_excise": 1, "has_sedan": 1})

        report = DataCoverageService(session).inspect(
            country_iso2="ID",
            powertrain="BEV",
            import_mode="CBU",
            effective_date="2027-01-01",
        )

        self.assertEqual(report.coverage_status, "UNSUPPORTED")
        self.assertEqual(session.calls, [])
        missing = report.missing_dimensions[0]
        self.assertEqual(missing["country_iso2"], "ID")
        self.assertEqual(missing["effective_date"], "2027-01-01")
        self.assertEqual(missing["status"], "UNSUPPORTED")
        self.assertNotIn("ROUTE-MY", report.note)

    def test_malaysia_route_cannot_be_used_for_vietnam(self):
        session = FakeSession({"total": 1, "has_excise": 1, "has_sedan": 1})

        report = DataCoverageService(session).inspect(
            country_iso2="VN",
            powertrain="BEV",
            import_mode="CBU",
            route_code="ROUTE-MY-01-CBU",
            effective_date="2027-01-01",
        )

        self.assertEqual(report.coverage_status, "UNSUPPORTED")
        self.assertEqual(session.calls, [])
        self.assertEqual(
            report.missing_dimensions[0]["reason"],
            "ROUTE_NOT_CONFIGURED_FOR_COUNTRY",
        )
        self.assertEqual(report.missing_dimensions[0]["country_iso2"], "VN")

    def test_invalid_date_is_explicit_missing_without_query(self):
        session = FakeSession({"total": 1, "has_excise": 1, "has_sedan": 1})

        report = DataCoverageService(session).inspect(
            country_iso2="VN",
            powertrain="BEV",
            import_mode="CBU",
            effective_date="2027/01/01",
        )

        self.assertEqual(report.coverage_status, "MISSING")
        self.assertEqual(session.calls, [])
        self.assertEqual(
            report.missing_dimensions[0]["reason"], "INVALID_EFFECTIVE_DATE"
        )

    def test_tool_preserves_vietnam_and_effective_date_in_envelope(self):
        session = FakeSession({"total": 1, "has_excise": 1, "has_sedan": 1})

        with patch.object(coverage_tool, "SessionLocal", return_value=session):
            result = coverage_tool.inspect_data_coverage.invoke(
                {
                    "country": "VN",
                    "powertrain": "BEV",
                    "import_mode": "CBU",
                    "effective_date": "2027-10-11",
                }
            )

        self.assertEqual(result["country_iso2"], "VN")
        self.assertEqual(result["effective_date"], "2027-10-11")
        self.assertEqual(result["available"][0]["country_iso2"], "VN")
        self.assertEqual(
            result["available"][0]["route_code"], "ROUTE-VN-01-CBU-NEW-PASSENGER"
        )


if __name__ == "__main__":
    unittest.main()
