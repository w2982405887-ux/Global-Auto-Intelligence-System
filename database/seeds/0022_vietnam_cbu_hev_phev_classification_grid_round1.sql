BEGIN;

-- Vietnam CBU new passenger HEV/PHEV classification grid, round 1.
-- Scope: ordinary new CBU passenger vehicles under 8703.40 and 8703.60.
-- Excludes CKD rows, ATV, ambulance, hearse, prison van and other special-purpose
-- lines unless the user later asks to support those business cases.
-- SCT rates below are for the "qualified hybrid/PHEV energy-saving condition" scenario:
-- 70% of comparable ordinary ICE passenger-car SCT rate under Law 66/2025/QH15.

WITH doc AS (
  SELECT source_document_id, source_code FROM evidence.source_document
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
SELECT * FROM (
  SELECT
    'VN-HS-870340-870360-CBU-PASSENGER-GRID-AHTN2022',
    (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-73-2025-MFN-AUTO-8703'),
    'tariff_heading',
    'Vietnam AHTN 2022 heading 8703.40 and 8703.60 ordinary CBU passenger vehicle subheadings',
    'Vietnam AHTN 2022 classifies hybrid vehicles not externally chargeable under 8703.40 and externally chargeable spark-ignition hybrid vehicles under 8703.60; ordinary CBU passenger lines are subdivided by body/subcategory, displacement band and 4WD/non-4WD status.',
    '越南AHTN 2022中，非外接充电的火花点火混动车归入8703.40，可外接充电的火花点火混动车归入8703.60；普通CBU乘用车继续按车身细分类别、排量区间和四驱/非四驱拆分。',
    'Classification-grid source for Vietnam HEV/PHEV ordinary CBU passenger vehicles.',
    'manual_web_research',
    now(),
    'CANDIDATE'::ref.verification_status
) rows(clause_code, source_document_id, locator_type, locator_value, original_text, translated_text_cn, evidence_summary, extraction_method, extracted_at, verification_status)
ON CONFLICT (source_document_id, locator_type, locator_value) DO UPDATE SET
  clause_code=EXCLUDED.clause_code,
  original_text=EXCLUDED.original_text,
  translated_text_cn=EXCLUDED.translated_text_cn,
  evidence_summary=EXCLUDED.evidence_summary,
  extraction_method=EXCLUDED.extraction_method,
  extracted_at=now(),
  verification_status='CANDIDATE';

WITH
vn AS (SELECT country_id FROM ref.country WHERE iso2='VN'),
route AS (SELECT vehicle_tax_route_id FROM rules.vehicle_tax_route WHERE route_code='ROUTE-VN-01-CBU-NEW-PASSENGER'),
tariff_clause AS (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-MFN-8703-CBU-TARIFF-2025'),
tax_clause AS (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-SCT-2026-HYBRID-70PCT-CONDITION'),
grid_clause AS (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-HS-870340-870360-CBU-PASSENGER-GRID-AHTN2022'),
rows AS (
  SELECT * FROM (VALUES
    -- 8703.40: spark-ignition HEV, not externally chargeable, ordinary CBU passenger lines
    ('VN-CBU-MFN-87034056-HEV-MOTORHOME-LE1500-QUAL-2026','870340','8703405600','8703.40.56','HEV','MOTORHOME','NONE',0,1500,0.24500000,'Motor-home, <=1,500 cc'),
    ('VN-CBU-MFN-87034057-HEV-MOTORHOME-1500-2000-QUAL-2026','870340','8703405700','8703.40.57','HEV','MOTORHOME','NONE',1500,2000,0.28000000,'Motor-home, >1,500-2,000 cc'),
    ('VN-CBU-MFN-87034058-HEV-MOTORHOME-GT2000-QUAL-2026','870340','8703405800','8703.40.58','HEV','MOTORHOME','NONE',2000,NULL,0.35000000,'Motor-home, >2,000 cc; SCT uses >2,000-2,500 baseline unless larger displacement is confirmed'),
    ('VN-CBU-MFN-87034061-HEV-SEDAN-LE1000-QUAL-2026','870340','8703406100','8703.40.61','HEV','SEDAN','NONE',0,1000,0.24500000,'Sedan, <=1,000 cc'),
    ('VN-CBU-MFN-87034062-HEV-SEDAN-1000-1500-QUAL-2026','870340','8703406200','8703.40.62','HEV','SEDAN','NONE',1000,1500,0.24500000,'Sedan, >1,000-1,500 cc'),
    ('VN-CBU-MFN-87034063-HEV-SEDAN-1500-1800-QUAL-2026','870340','8703406300','8703.40.63','HEV','SEDAN','NONE',1500,1800,0.28000000,'Sedan, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87034064-HEV-SEDAN-1800-2000-QUAL-2026','870340','8703406400','8703.40.64','HEV','SEDAN','NONE',1800,2000,0.28000000,'Sedan, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87034065-HEV-SEDAN-2000-2500-QUAL-2026','870340','8703406500','8703.40.65','HEV','SEDAN','NONE',2000,2500,0.35000000,'Sedan, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87034066-HEV-SEDAN-2500-3000-QUAL-2026','870340','8703406600','8703.40.66','HEV','SEDAN','NONE',2500,3000,0.42000000,'Sedan, >2,500-3,000 cc'),
    ('VN-CBU-MFN-87034071-HEV-OTHERPV-4WD-LE1000-QUAL-2026','870340','8703407100','8703.40.71','HEV','OTHER_PASSENGER','4WD',0,1000,0.24500000,'Other passenger car, 4WD, <=1,000 cc'),
    ('VN-CBU-MFN-87034072-HEV-OTHERPV-4WD-1000-1500-QUAL-2026','870340','8703407200','8703.40.72','HEV','OTHER_PASSENGER','4WD',1000,1500,0.24500000,'Other passenger car, 4WD, >1,000-1,500 cc'),
    ('VN-CBU-MFN-87034073-HEV-OTHERPV-4WD-1500-1800-QUAL-2026','870340','8703407300','8703.40.73','HEV','OTHER_PASSENGER','4WD',1500,1800,0.28000000,'Other passenger car, 4WD, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87034074-HEV-OTHERPV-4WD-1800-2000-QUAL-2026','870340','8703407400','8703.40.74','HEV','OTHER_PASSENGER','4WD',1800,2000,0.28000000,'Other passenger car, 4WD, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87034075-HEV-OTHERPV-4WD-2000-2500-QUAL-2026','870340','8703407500','8703.40.75','HEV','OTHER_PASSENGER','4WD',2000,2500,0.35000000,'Other passenger car, 4WD, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87034076-HEV-OTHERPV-4WD-2500-3000-QUAL-2026','870340','8703407600','8703.40.76','HEV','OTHER_PASSENGER','4WD',2500,3000,0.42000000,'Other passenger car, 4WD, >2,500-3,000 cc'),
    ('VN-CBU-MFN-87034081-HEV-OTHERPV-2WD-LE1000-QUAL-2026','870340','8703408100','8703.40.81','HEV','OTHER_PASSENGER','NON_4WD',0,1000,0.24500000,'Other passenger car, non-4WD, <=1,000 cc'),
    ('VN-CBU-MFN-87034082-HEV-OTHERPV-2WD-1000-1500-QUAL-2026','870340','8703408200','8703.40.82','HEV','OTHER_PASSENGER','NON_4WD',1000,1500,0.24500000,'Other passenger car, non-4WD, >1,000-1,500 cc'),
    ('VN-CBU-MFN-87034083-HEV-OTHERPV-2WD-1500-1800-QUAL-2026','870340','8703408300','8703.40.83','HEV','OTHER_PASSENGER','NON_4WD',1500,1800,0.28000000,'Other passenger car, non-4WD, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87034084-HEV-OTHERPV-2WD-1800-2000-QUAL-2026','870340','8703408400','8703.40.84','HEV','OTHER_PASSENGER','NON_4WD',1800,2000,0.28000000,'Other passenger car, non-4WD, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87034085-HEV-OTHERPV-2WD-2000-2500-QUAL-2026','870340','8703408500','8703.40.85','HEV','OTHER_PASSENGER','NON_4WD',2000,2500,0.35000000,'Other passenger car, non-4WD, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87034086-HEV-OTHERPV-2WD-2500-3000-QUAL-2026','870340','8703408600','8703.40.86','HEV','OTHER_PASSENGER','NON_4WD',2500,3000,0.42000000,'Other passenger car, non-4WD, >2,500-3,000 cc'),
    ('VN-CBU-MFN-87034091-HEV-OTHER-LE1000-QUAL-2026','870340','8703409100','8703.40.91','HEV','OTHER','NONE',0,1000,0.24500000,'Other, <=1,000 cc'),
    ('VN-CBU-MFN-87034093-HEV-OTHER-1500-1800-QUAL-2026','870340','8703409300','8703.40.93','HEV','OTHER','NONE',1500,1800,0.28000000,'Other, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87034094-HEV-OTHER-1800-2000-QUAL-2026','870340','8703409400','8703.40.94','HEV','OTHER','NONE',1800,2000,0.28000000,'Other, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87034095-HEV-OTHER-2000-2500-QUAL-2026','870340','8703409500','8703.40.95','HEV','OTHER','NONE',2000,2500,0.35000000,'Other, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87034096-HEV-OTHER-2500-3000-QUAL-2026','870340','8703409600','8703.40.96','HEV','OTHER','NONE',2500,3000,0.42000000,'Other, >2,500-3,000 cc'),

    -- 8703.60: externally chargeable spark-ignition PHEV/EREV, ordinary CBU passenger lines
    ('VN-CBU-MFN-87036056-PHEV-MOTORHOME-LE1500-QUAL-2026','870360','8703605600','8703.60.56','PHEV','MOTORHOME','NONE',0,1500,0.24500000,'Motor-home, <=1,500 cc'),
    ('VN-CBU-MFN-87036057-PHEV-MOTORHOME-1500-2000-QUAL-2026','870360','8703605700','8703.60.57','PHEV','MOTORHOME','NONE',1500,2000,0.28000000,'Motor-home, >1,500-2,000 cc'),
    ('VN-CBU-MFN-87036058-PHEV-MOTORHOME-GT2000-QUAL-2026','870360','8703605800','8703.60.58','PHEV','MOTORHOME','NONE',2000,NULL,0.35000000,'Motor-home, >2,000 cc; SCT uses >2,000-2,500 baseline unless larger displacement is confirmed'),
    ('VN-CBU-MFN-87036061-PHEV-SEDAN-LE1000-QUAL-2026','870360','8703606100','8703.60.61','PHEV','SEDAN','NONE',0,1000,0.24500000,'Sedan, <=1,000 cc'),
    ('VN-CBU-MFN-87036062-PHEV-SEDAN-1000-1500-QUAL-2026','870360','8703606200','8703.60.62','PHEV','SEDAN','NONE',1000,1500,0.24500000,'Sedan, >1,000-1,500 cc'),
    ('VN-CBU-MFN-87036063-PHEV-SEDAN-1500-1800-QUAL-2026','870360','8703606300','8703.60.63','PHEV','SEDAN','NONE',1500,1800,0.28000000,'Sedan, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87036064-PHEV-SEDAN-1800-2000-QUAL-2026','870360','8703606400','8703.60.64','PHEV','SEDAN','NONE',1800,2000,0.28000000,'Sedan, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87036065-PHEV-SEDAN-2000-2500-QUAL-2026','870360','8703606500','8703.60.65','PHEV','SEDAN','NONE',2000,2500,0.35000000,'Sedan, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87036066-PHEV-SEDAN-2500-3000-QUAL-2026','870360','8703606600','8703.60.66','PHEV','SEDAN','NONE',2500,3000,0.42000000,'Sedan, >2,500-3,000 cc'),
    ('VN-CBU-MFN-87036071-PHEV-OTHERPV-4WD-LE1000-QUAL-2026','870360','8703607100','8703.60.71','PHEV','OTHER_PASSENGER','4WD',0,1000,0.24500000,'Other passenger car, 4WD, <=1,000 cc'),
    ('VN-CBU-MFN-87036072-PHEV-OTHERPV-4WD-1000-1500-QUAL-2026','870360','8703607200','8703.60.72','PHEV','OTHER_PASSENGER','4WD',1000,1500,0.24500000,'Other passenger car, 4WD, >1,000-1,500 cc'),
    ('VN-CBU-MFN-87036073-PHEV-OTHERPV-4WD-1500-1800-QUAL-2026','870360','8703607300','8703.60.73','PHEV','OTHER_PASSENGER','4WD',1500,1800,0.28000000,'Other passenger car, 4WD, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87036074-PHEV-OTHERPV-4WD-1800-2000-QUAL-2026','870360','8703607400','8703.60.74','PHEV','OTHER_PASSENGER','4WD',1800,2000,0.28000000,'Other passenger car, 4WD, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87036075-PHEV-OTHERPV-4WD-2000-2500-QUAL-2026','870360','8703607500','8703.60.75','PHEV','OTHER_PASSENGER','4WD',2000,2500,0.35000000,'Other passenger car, 4WD, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87036076-PHEV-OTHERPV-4WD-2500-3000-QUAL-2026','870360','8703607600','8703.60.76','PHEV','OTHER_PASSENGER','4WD',2500,3000,0.42000000,'Other passenger car, 4WD, >2,500-3,000 cc'),
    ('VN-CBU-MFN-87036081-PHEV-OTHERPV-2WD-LE1000-QUAL-2026','870360','8703608100','8703.60.81','PHEV','OTHER_PASSENGER','NON_4WD',0,1000,0.24500000,'Other passenger car, non-4WD, <=1,000 cc'),
    ('VN-CBU-MFN-87036082-PHEV-OTHERPV-2WD-1000-1500-QUAL-2026','870360','8703608200','8703.60.82','PHEV','OTHER_PASSENGER','NON_4WD',1000,1500,0.24500000,'Other passenger car, non-4WD, >1,000-1,500 cc'),
    ('VN-CBU-MFN-87036083-PHEV-OTHERPV-2WD-1500-1800-QUAL-2026','870360','8703608300','8703.60.83','PHEV','OTHER_PASSENGER','NON_4WD',1500,1800,0.28000000,'Other passenger car, non-4WD, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87036084-PHEV-OTHERPV-2WD-1800-2000-QUAL-2026','870360','8703608400','8703.60.84','PHEV','OTHER_PASSENGER','NON_4WD',1800,2000,0.28000000,'Other passenger car, non-4WD, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87036085-PHEV-OTHERPV-2WD-2000-2500-QUAL-2026','870360','8703608500','8703.60.85','PHEV','OTHER_PASSENGER','NON_4WD',2000,2500,0.35000000,'Other passenger car, non-4WD, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87036086-PHEV-OTHERPV-2WD-2500-3000-QUAL-2026','870360','8703608600','8703.60.86','PHEV','OTHER_PASSENGER','NON_4WD',2500,3000,0.42000000,'Other passenger car, non-4WD, >2,500-3,000 cc'),
    ('VN-CBU-MFN-87036091-PHEV-OTHER-LE1000-QUAL-2026','870360','8703609100','8703.60.91','PHEV','OTHER','NONE',0,1000,0.24500000,'Other, <=1,000 cc'),
    ('VN-CBU-MFN-87036093-PHEV-OTHER-1500-1800-QUAL-2026','870360','8703609300','8703.60.93','PHEV','OTHER','NONE',1500,1800,0.28000000,'Other, >1,500-1,800 cc'),
    ('VN-CBU-MFN-87036094-PHEV-OTHER-1800-2000-QUAL-2026','870360','8703609400','8703.60.94','PHEV','OTHER','NONE',1800,2000,0.28000000,'Other, >1,800-2,000 cc'),
    ('VN-CBU-MFN-87036095-PHEV-OTHER-2000-2500-QUAL-2026','870360','8703609500','8703.60.95','PHEV','OTHER','NONE',2000,2500,0.35000000,'Other, >2,000-2,500 cc'),
    ('VN-CBU-MFN-87036096-PHEV-OTHER-2500-3000-QUAL-2026','870360','8703609600','8703.60.96','PHEV','OTHER','NONE',2500,3000,0.42000000,'Other, >2,500-3,000 cc')
  ) AS t(rate_line_code, hs6_code, national_tariff_code, vn_hs8_code, powertrain, vehicle_subcategory, drive_form, displacement_min_cc, displacement_max_cc, excise_duty_rate, tariff_description)
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
  'VN-MFN-2026-CBU-PASSENGER-AHTN2022',
  2026,
  'MFN'::ref.origin_regime,
  NULL::uuid,
  rows.hs6_code::char(6),
  rows.national_tariff_code,
  rows.tariff_description,
  rows.powertrain::ref.powertrain,
  'PASSENGER_VEHICLE_8703',
  0.70000000,
  0.10000000,
  rows.excise_duty_rate,
  'TAXABLE',
  'STATUTORY_RATE',
  jsonb_build_object(
    'import_mode', 'CBU',
    'new_or_used', 'NEW',
    'business_scope', 'NEW_PASSENGER_VEHICLE_ONLY',
    'vn_hs8_code', rows.vn_hs8_code,
    'vehicle_subcategory', rows.vehicle_subcategory,
    'drive_form', rows.drive_form,
    'displacement_min_cc_exclusive', rows.displacement_min_cc,
    'displacement_max_cc_inclusive', rows.displacement_max_cc,
    'hybrid_sct_70pct_qualification_required', true,
    'sct_rate_basis', '70_PERCENT_OF_COMPARABLE_ICE_RATE',
    'fta_origin_regime', 'MFN_BASELINE_ONLY',
    'excluded_from_round1', jsonb_build_array('CKD','USED_VEHICLE','ATV','AMBULANCE','HEARSE','PRISON_VAN')
  ),
  tariff_clause.source_clause_id,
  tax_clause.source_clause_id,
  DATE '2026-01-01',
  NULL::date,
  1,
  'ACTIVE'::ref.record_status,
  'CANDIDATE'::ref.verification_status,
  'CANDIDATE'::ref.verification_status
FROM rows
CROSS JOIN vn
CROSS JOIN route
CROSS JOIN tariff_clause
CROSS JOIN tax_clause
CROSS JOIN grid_clause
ON CONFLICT (rate_line_code, version) DO UPDATE SET
  tariff_description=EXCLUDED.tariff_description,
  import_duty_rate=EXCLUDED.import_duty_rate,
  sales_tax_rate=EXCLUDED.sales_tax_rate,
  excise_duty_rate=EXCLUDED.excise_duty_rate,
  eligibility_condition=EXCLUDED.eligibility_condition,
  tariff_source_clause_id=EXCLUDED.tariff_source_clause_id,
  tax_treatment_source_clause_id=EXCLUDED.tax_treatment_source_clause_id,
  verification_status='CANDIDATE',
  route_verification_status='CANDIDATE',
  updated_at=now();

COMMIT;
