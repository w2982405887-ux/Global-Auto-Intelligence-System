from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "database" / "seeds" / "0028_vietnam_ckd_battery_2027_verified_rates.sql"


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _database_url() -> str:
    configured = os.environ.get("GAIS_DATABASE_URL")
    if configured:
        return configured
    env = _load_dotenv(ROOT / ".env")
    if not env.get("POSTGRES_USER"):
        return ""
    password = quote_plus(env.get("POSTGRES_PASSWORD", ""))
    return (
        f"postgresql+psycopg://{env['POSTGRES_USER']}:{password}"
        f"@127.0.0.1:{env.get('POSTGRES_PORT', '5432')}/{env['POSTGRES_DB']}"
    )


def test_seed_declares_verified_official_sources_and_exclusive_2027_boundary() -> None:
    sql = SEED.read_text(encoding="utf-8")
    assert "https://vanban.chinhphu.vn/?docid=208020&pageid=27160" in sql
    assert "https://vanban.chinhphu.vn/?classid=1&docid=207167&pageid=27160&typegroupid=" in sql
    assert "https://vanban.chinhphu.vn/?classid=1&docid=207257&pageid=27160" in sql
    assert "'VERIFIED'::ref.verification_status" in sql
    assert "TIMESTAMPTZ '2026-08-18 14:00:00+08'" in sql
    assert "effective_to = DATE '2028-01-01'" in sql
    for code in ("85076033", "85076039", "85076090"):
        assert code in sql


def test_vietnam_ckd_battery_2027_returns_all_regimes_at_year_edges() -> None:
    url = _database_url()
    if not url:
        pytest.skip("GAIS_DATABASE_URL or .env database settings are unavailable")

    engine = create_engine(url)
    lookup = text(
        """
        SELECT
          COALESCE(agreement.agreement_code, 'MFN') AS regime,
          mapping.national_tariff_code,
          mapping.duty_rate,
          mapping.effective_to,
          mapping.verification_status::text AS verification_status,
          source_document.official_status::text AS official_status,
          source_document.canonical_url
        FROM customs.tariff_mapping AS mapping
        JOIN ref.country AS country ON country.country_id = mapping.country_id
          AND country.iso2 = 'VN'
        JOIN customs.ccu_candidate_hs AS candidate
          ON candidate.candidate_id = mapping.candidate_id
          AND candidate.hs6_code = '850760'
        JOIN customs.customs_classification_unit AS component
          ON component.ccu_id = candidate.ccu_id
          AND component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
        LEFT JOIN ref.trade_agreement AS agreement
          ON agreement.trade_agreement_id = mapping.trade_agreement_id
        JOIN evidence.source_clause AS source_clause
          ON source_clause.source_clause_id = mapping.source_clause_id
        JOIN evidence.source_document AS source_document
          ON source_document.source_document_id = source_clause.source_document_id
        WHERE mapping.national_tariff_code IN ('85076033', '85076039', '85076090')
          AND mapping.record_status = 'ACTIVE'
          AND mapping.effective_from <= :as_of
          AND (mapping.effective_to IS NULL OR mapping.effective_to > :as_of)
        ORDER BY mapping.national_tariff_code, regime
        """
    )
    expected_rates = {
        ("85076033", "MFN"): 0.05,
        ("85076033", "ACFTA"): 0.00,
        ("85076033", "RCEP"): 0.00,
        ("85076039", "MFN"): 0.05,
        ("85076039", "ACFTA"): 0.00,
        ("85076039", "RCEP"): 0.00,
        ("85076090", "MFN"): 0.05,
        ("85076090", "ACFTA"): 0.00,
        ("85076090", "RCEP"): 0.00,
    }

    try:
        connection = engine.connect()
    except Exception as exc:  # pragma: no cover - only exercised without local DB
        engine.dispose()
        pytest.skip(f"Vietnam tariff integration database unavailable: {exc}")
    try:
        with connection.begin():
            for as_of in ("2027-01-01", "2027-12-31"):
                rows = connection.execute(lookup, {"as_of": as_of}).mappings().all()
                assert len(rows) == len(expected_rates)
                actual = {
                    (row["national_tariff_code"], row["regime"]): float(row["duty_rate"])
                    for row in rows
                }
                assert actual == expected_rates
                assert all(row["verification_status"] == "VERIFIED" for row in rows)
                assert all(row["official_status"] == "OFFICIAL" for row in rows)
                assert all(row["effective_to"].isoformat() == "2028-01-01" for row in rows)
                assert all("vanban.chinhphu.vn" in row["canonical_url"] for row in rows)

            unrelated = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM customs.tariff_mapping AS mapping
                    JOIN evidence.source_clause AS clause
                      ON clause.source_clause_id = mapping.source_clause_id
                    JOIN customs.ccu_candidate_hs AS candidate
                      ON candidate.candidate_id = mapping.candidate_id
                    JOIN customs.customs_classification_unit AS component
                      ON component.ccu_id = candidate.ccu_id
                    WHERE clause.clause_code IN (
                      'VN-CKD-BATTERY-MFN-850760-2027-5PCT',
                      'VN-CKD-BATTERY-ACFTA-850760-2027-0PCT',
                      'VN-CKD-BATTERY-RCEP-850760-2027-0PCT'
                    )
                    AND component.ccu_code <> 'VN-CKD-TRACTION-BATTERY'
                    """
                )
            ).scalar_one()
            assert unrelated == 0
    finally:
        connection.close()
        engine.dispose()
