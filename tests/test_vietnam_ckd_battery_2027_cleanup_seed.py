from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "database" / "seeds" / "0029_vietnam_ckd_battery_non_automotive_line_cleanup.sql"


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


def test_cleanup_seed_is_scoped_and_auditable() -> None:
    sql = SEED.read_text(encoding="utf-8")
    assert "VN-CKD-TRACTION-BATTERY" in sql
    assert "85076031" in sql and "85076032" in sql
    assert "record_status = 'SUSPENDED'::ref.record_status" in sql
    assert "SUSPENDED_NON_AUTOMOTIVE_LINE" in sql
    assert "previous_source_clause_id" in sql
    assert "VN-CKD-BATTERY-AUTO-SCOPE-EXCLUDE-85076031-32" in sql
    assert "'ACTIVE'::ref.record_status" in sql


def test_vietnam_ckd_battery_cleanup_preserves_2027_automotive_candidates() -> None:
    url = _database_url()
    if not url:
        pytest.skip("GAIS_DATABASE_URL or .env database settings are unavailable")

    engine = create_engine(url)
    try:
        connection = engine.connect()
    except Exception as exc:  # pragma: no cover - only exercised without local DB
        engine.dispose()
        pytest.skip(f"Vietnam tariff integration database unavailable: {exc}")

    try:
        with connection.begin():
            active_non_auto = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM customs.tariff_mapping AS mapping
                    JOIN customs.ccu_candidate_hs AS candidate
                      ON candidate.candidate_id = mapping.candidate_id
                    JOIN customs.customs_classification_unit AS component
                      ON component.ccu_id = candidate.ccu_id
                    WHERE component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
                      AND mapping.national_tariff_code IN ('85076031','85076032')
                      AND mapping.record_status = 'ACTIVE'
                    """
                )
            ).scalar_one()
            assert active_non_auto == 0

            suspended = connection.execute(
                text(
                    """
                    SELECT mapping.national_tariff_code,
                           mapping.record_status::text AS record_status,
                           mapping.additional_measure->>'data_quality_status' AS quality,
                           source_clause.clause_code
                    FROM customs.tariff_mapping AS mapping
                    JOIN customs.ccu_candidate_hs AS candidate
                      ON candidate.candidate_id = mapping.candidate_id
                    JOIN customs.customs_classification_unit AS component
                      ON component.ccu_id = candidate.ccu_id
                    JOIN evidence.source_clause AS source_clause
                      ON source_clause.source_clause_id = mapping.source_clause_id
                    WHERE component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
                      AND mapping.national_tariff_code IN ('85076031','85076032')
                    """
                )
            ).mappings().all()
            assert suspended
            assert all(row["record_status"] == "SUSPENDED" for row in suspended)
            assert all(row["quality"] == "SUSPENDED_NON_AUTOMOTIVE_LINE" for row in suspended)
            assert all(
                row["clause_code"] == "VN-CKD-BATTERY-AUTO-SCOPE-EXCLUDE-85076031-32"
                for row in suspended
            )

            scope_violations = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM customs.tariff_mapping AS mapping
                    JOIN evidence.source_clause AS source_clause
                      ON source_clause.source_clause_id = mapping.source_clause_id
                    JOIN customs.ccu_candidate_hs AS candidate
                      ON candidate.candidate_id = mapping.candidate_id
                    JOIN customs.customs_classification_unit AS component
                      ON component.ccu_id = candidate.ccu_id
                    WHERE source_clause.clause_code =
                      'VN-CKD-BATTERY-AUTO-SCOPE-EXCLUDE-85076031-32'
                      AND (
                        component.ccu_code <> 'VN-CKD-TRACTION-BATTERY'
                        OR mapping.national_tariff_code NOT IN ('85076031','85076032')
                      )
                    """
                )
            ).scalar_one()
            assert scope_violations == 0

            automotive = connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM customs.tariff_mapping AS mapping
                    JOIN ref.country AS country ON country.country_id = mapping.country_id
                      AND country.iso2 = 'VN'
                    JOIN customs.ccu_candidate_hs AS candidate
                      ON candidate.candidate_id = mapping.candidate_id
                      AND candidate.hs6_code = '850760'
                    JOIN customs.customs_classification_unit AS component
                      ON component.ccu_id = candidate.ccu_id
                      AND component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
                    WHERE mapping.national_tariff_code IN ('85076033','85076039','85076090')
                      AND mapping.record_status = 'ACTIVE'
                      AND mapping.effective_from <= DATE '2027-12-31'
                      AND (mapping.effective_to IS NULL OR mapping.effective_to > DATE '2027-12-31')
                    """
                )
            ).scalar_one()
            assert automotive == 9
    finally:
        connection.close()
        engine.dispose()
