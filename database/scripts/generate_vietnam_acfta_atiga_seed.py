from __future__ import annotations

import csv
from pathlib import Path


IN = Path("database/reference_exports/vietnam_acfta_atiga_8703_cbu_rates_ready_round1.csv")
OUT = Path("database/seeds/0023_vietnam_cbu_acfta_atiga_8703_rates_round1.sql")


POWERTRAIN_BY_HS6 = {
    "870321": "ICE_GASOLINE",
    "870322": "ICE_GASOLINE",
    "870323": "ICE_GASOLINE",
    "870324": "ICE_GASOLINE",
    "870340": "HEV",
    "870350": "HEV",
    "870360": "PHEV",
    "870370": "PHEV",
    "870380": "BEV",
    "870390": "OTHER",
}


def sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def parse_rate(value: str) -> str | None:
    value = value.strip()
    if not value or value == "*":
        return None
    return f"{int(value) / 100:.8f}"


def main() -> int:
    rows = list(csv.DictReader(IN.open(encoding="utf-8-sig")))
    inserts: list[str] = []
    for row in rows:
        rate = parse_rate(row["rate_2026"])
        if rate is None:
            continue
        hs6 = row["hs6_code"]
        powertrain = POWERTRAIN_BY_HS6.get(hs6, "OTHER")
        agreement = row["agreement"]
        code = row["national_tariff_code_as_stored"]
        rate_line_code = f"VN-CBU-{agreement}-{code}-2026"
        clause_code = (
            "VN-ACFTA-ORIGIN-PREFERENTIAL-DUTY"
            if agreement == "ACFTA"
            else "VN-ATIGA-ORIGIN-PREFERENTIAL-DUTY"
        )
        inserts.append(
            "("
            + ",".join(
                [
                    sql_literal(rate_line_code),
                    sql_literal(agreement),
                    sql_literal(clause_code),
                    sql_literal(hs6),
                    sql_literal(code),
                    sql_literal(row["vn_code"]),
                    sql_literal(row["description_vi"]),
                    sql_literal(powertrain),
                    rate,
                    sql_literal(row["rates_extracted"]),
                    sql_literal(row["source_file"]),
                ]
            )
            + ")"
        )

    sql = f"""BEGIN;

-- Vietnam CBU 8703 ACFTA/ATIGA preferential import-duty rate lines, round 1.
-- Generated from Vietnamese official gazette .doc attachments downloaded by user.
-- Scope: new CBU ordinary/passenger vehicle blocks under 87.03. CKD and special
-- vehicle blocks marked with '*' are excluded from importable rate rows.

INSERT INTO ref.trade_agreement (
  agreement_code, agreement_name, version, effective_from, effective_to, record_status
) VALUES
  ('ATIGA', 'ASEAN Trade in Goods Agreement', 1, DATE '2010-05-17', NULL::date, 'ACTIVE'::ref.record_status)
ON CONFLICT (agreement_code, version) DO UPDATE SET
  agreement_name=EXCLUDED.agreement_name,
  effective_from=EXCLUDED.effective_from,
  effective_to=EXCLUDED.effective_to,
  record_status='ACTIVE';

WITH
vn AS (SELECT country_id FROM ref.country WHERE iso2='VN'),
route AS (SELECT vehicle_tax_route_id FROM rules.vehicle_tax_route WHERE route_code='ROUTE-VN-01-CBU-NEW-PASSENGER'),
agreement AS (SELECT trade_agreement_id, agreement_code FROM ref.trade_agreement),
clause AS (SELECT source_clause_id, clause_code FROM evidence.source_clause),
rows(rate_line_code, agreement_code, clause_code, hs6_code, national_tariff_code, vn_hs8_code, description_vi, powertrain, import_duty_rate, rates_extracted, source_file) AS (
  VALUES
  {",\n  ".join(inserts)}
)
INSERT INTO customs.vehicle_tariff_rate_line (
  rate_line_code, country_id, vehicle_tax_route_id, tariff_schedule_code,
  tariff_year, origin_regime, trade_agreement_id, hs6_code, national_tariff_code,
  tariff_description, powertrain, vehicle_category, import_duty_rate,
  sales_tax_rate, excise_duty_rate, sales_tax_treatment, excise_treatment,
  eligibility_condition, tariff_source_clause_id, tax_treatment_source_clause_id,
  effective_from, effective_to, version, record_status, verification_status,
  route_verification_status
)
SELECT
  rows.rate_line_code,
  vn.country_id,
  route.vehicle_tax_route_id,
  'VN-' || rows.agreement_code || '-2026-CBU-8703',
  2026,
  'FTA'::ref.origin_regime,
  agreement.trade_agreement_id,
  rows.hs6_code::char(6),
  rows.national_tariff_code,
  rows.description_vi,
  rows.powertrain::ref.powertrain,
  'PASSENGER_VEHICLE_8703',
  rows.import_duty_rate::numeric,
  0.10000000,
  NULL::numeric,
  'TAXABLE',
  'UNKNOWN',
  jsonb_build_object(
    'import_mode','CBU',
    'new_or_used','NEW',
    'business_scope','NEW_PASSENGER_VEHICLE_ONLY',
    'vn_hs8_code', rows.vn_hs8_code,
    'agreement', rows.agreement_code,
    'requires_origin_rule', true,
    'requires_direct_shipment', true,
    'requires_proof_of_origin', true,
    'rates_extracted', rows.rates_extracted,
    'source_file', rows.source_file,
    'rate_year_selected', 2026,
    'note', 'Preferential import duty only; SCT and VAT are resolved from statutory vehicle tax rows or scenario logic.'
  ),
  clause.source_clause_id,
  NULL::uuid,
  DATE '2026-01-01',
  DATE '2028-01-01',
  1,
  'ACTIVE'::ref.record_status,
  'CANDIDATE'::ref.verification_status,
  'CANDIDATE'::ref.verification_status
FROM rows
CROSS JOIN vn
CROSS JOIN route
JOIN agreement ON agreement.agreement_code = rows.agreement_code
JOIN clause ON clause.clause_code = rows.clause_code
ON CONFLICT (rate_line_code, version) DO UPDATE SET
  tariff_schedule_code=EXCLUDED.tariff_schedule_code,
  import_duty_rate=EXCLUDED.import_duty_rate,
  sales_tax_rate=EXCLUDED.sales_tax_rate,
  excise_duty_rate=EXCLUDED.excise_duty_rate,
  excise_treatment=EXCLUDED.excise_treatment,
  eligibility_condition=EXCLUDED.eligibility_condition,
  tariff_source_clause_id=EXCLUDED.tariff_source_clause_id,
  tax_treatment_source_clause_id=EXCLUDED.tax_treatment_source_clause_id,
  verification_status='CANDIDATE',
  route_verification_status='CANDIDATE',
  updated_at=now();

COMMIT;
"""
    OUT.write_text(sql, encoding="utf-8")
    print(f"wrote {OUT} rows={len(inserts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
