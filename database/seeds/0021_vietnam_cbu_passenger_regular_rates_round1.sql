BEGIN;

-- Vietnam CBU new passenger vehicle regular tax-rate seed, round 1.
-- Scope: new CBU passenger vehicles under heading 87.03 only; excludes used cars,
-- two-wheelers, CKD and parts/BOM routes. Vietnam HS is 8-digit; stored as 10-digit
-- by appending 00, with original VN HS8 preserved in eligibility_condition.vn_hs8_code.

WITH vn AS (SELECT country_id FROM ref.country WHERE iso2='VN')
INSERT INTO ref.authority (authority_code, country_id, authority_name, official_url, record_status)
SELECT 'VN_OFFICIAL_GAZETTE', vn.country_id, 'Official Gazette of Vietnam', 'https://congbao.chinhphu.vn', 'ACTIVE'::ref.record_status
FROM vn
ON CONFLICT (authority_code) DO UPDATE SET
  country_id=EXCLUDED.country_id,
  authority_name=EXCLUDED.authority_name,
  official_url=EXCLUDED.official_url,
  record_status='ACTIVE',
  updated_at=now();

WITH auth AS (SELECT authority_id, authority_code FROM ref.authority)
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, document_number, source_type,
  official_status, canonical_url, publication_date, effective_from, effective_to,
  accessed_at, language_code, version, record_status
)
SELECT * FROM (
  SELECT 'VN-DECREE-73-2025-MFN-AUTO-8703',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 73/2025/ND-CP amending preferential import tariff rates under Decree No. 26/2023/ND-CP',
    '73/2025/ND-CP', 'REGULATION'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://xaydungchinhsach.chinhphu.vn/nghi-dinh-73-2025-nd-cp-sua-doi-bo-sung-muc-thue-suat-thue-nhap-khau-uu-dai-119250331221945389.htm',
    DATE '2025-03-31', DATE '2025-03-31', NULL::date, now(), 'vi', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-LAW-66-2025-SCT-VEHICLES',
    (SELECT authority_id FROM auth WHERE authority_code='VN_NATIONAL_ASSEMBLY'),
    'Law No. 66/2025/QH15 on Special Consumption Tax',
    '66/2025/QH15', 'LAW'::ref.source_type, 'OFFICIAL'::ref.official_status,
    'https://congbao.chinhphu.vn/van-ban/luat-so-66-2025-qh15-45587.htm',
    DATE '2025-06-14', DATE '2026-01-01', NULL::date, now(), 'vi', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-360-2025-SCT-GUIDANCE-HYBRID',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 360/2025/ND-CP guiding the Law on Special Consumption Tax',
    '360/2025/ND-CP', 'REGULATION'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/thue/decree-360-2025-nd-cp-guiding-the-law-on-special-consumption-tax-429083-d1.html',
    DATE '2025-12-31', DATE '2026-01-01', NULL::date, now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-LAW-48-2024-VAT',
    (SELECT authority_id FROM auth WHERE authority_code='VN_NATIONAL_ASSEMBLY'),
    'Law No. 48/2024/QH15 on Value Added Tax',
    '48/2024/QH15', 'LAW'::ref.source_type, 'OFFICIAL'::ref.official_status,
    'https://congbao.chinhphu.vn/van-ban/luat-so-48-2024-qh15-43576.htm',
    DATE '2024-11-26', DATE '2025-07-01', NULL::date, now(), 'vi', 1, 'ACTIVE'::ref.record_status
) rows(source_code, authority_id, document_title, document_number, source_type, official_status, canonical_url, publication_date, effective_from, effective_to, accessed_at, language_code, version, record_status)
ON CONFLICT (source_code) DO UPDATE SET
  authority_id=EXCLUDED.authority_id,
  document_title=EXCLUDED.document_title,
  document_number=EXCLUDED.document_number,
  source_type=EXCLUDED.source_type,
  official_status=EXCLUDED.official_status,
  canonical_url=EXCLUDED.canonical_url,
  publication_date=EXCLUDED.publication_date,
  effective_from=EXCLUDED.effective_from,
  effective_to=EXCLUDED.effective_to,
  accessed_at=EXCLUDED.accessed_at,
  language_code=EXCLUDED.language_code,
  record_status='ACTIVE';

WITH doc AS (SELECT source_document_id, source_code FROM evidence.source_document)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
SELECT * FROM (
  SELECT 'VN-MFN-8703-CBU-TARIFF-2025', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-73-2025-MFN-AUTO-8703'),
    'appendix', 'Appendix amending preferential import tariff / heading 87.03 CBU lines',
    'Decree 73/2025/ND-CP amends MFN preferential import duty for heading 87.03 passenger motor vehicles; common CBU lines remain 70%, with selected high-displacement sedan/SUV lines reduced to 50%, 52%, 47% or 32%.',
    '第73/2025号法令修订87.03乘用车MFN优惠进口税率；多数CBU整车为70%，部分大排量轿车/SUV税号降至50%、52%、47%或32%。',
    'MFN import-duty source for Vietnam CBU passenger vehicle tariff lines.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-SCT-2026-PASSENGER-CARS-ICE', (SELECT source_document_id FROM doc WHERE source_code='VN-LAW-66-2025-SCT-VEHICLES'),
    'article', 'Article 8 tax schedule, motor vehicles under 24 seats / items 4a-4c',
    'From 2026, passenger cars with 9 seats or fewer: cylinder capacity <=1,500cc 35%; >1,500-2,000cc 40%; >2,000-2,500cc 50%; >2,500-3,000cc 60%; >3,000-4,000cc 90%; >4,000-5,000cc 110%; >5,000-6,000cc 130%; >6,000cc 150%. Passenger cars 10 to under 16 seats 15%; 16 to under 24 seats 10%.',
    '自2026年起，9座及以下乘用车SCT按排量为35%、40%、50%、60%、90%、110%、130%、150%；10至16座以下为15%；16至24座以下为10%。',
    'SCT rates for ordinary ICE passenger vehicles under Law 66/2025/QH15.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-SCT-2026-HYBRID-70PCT-CONDITION', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-360-2025-SCT-GUIDANCE-HYBRID'),
    'article', 'Hybrid/gasoline-electric energy proportion guidance',
    'Gasoline-electric vehicles qualifying under Government rules may apply SCT equal to 70% of the rate for the same type of ordinary vehicle; qualification depends on prescribed gasoline/energy proportion and conformity evidence.',
    '符合政府规定的汽油-电动混合车辆可按同类普通车辆SCT税率的70%计算；资格取决于汽油/能量占比及合规证明。',
    'Condition for HEV/PHEV preferential SCT calculation at 70% of comparable ordinary vehicle rate.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-SCT-2026-BEV-RATES', (SELECT source_document_id FROM doc WHERE source_code='VN-LAW-66-2025-SCT-VEHICLES'),
    'article', 'Article 8 tax schedule, battery-powered electric cars / item 4g',
    'Battery-powered electric cars: through 2027-02-28 reduced SCT rates remain 3%, 2%, 1%, 2% by category; from 2027-03-01 rates are 11%, 7%, 4%, 7% by category.',
    '电池纯电动车：至2027-02-28按类别适用3%、2%、1%、2%；自2027-03-01按类别适用11%、7%、4%、7%。',
    'SCT rates for battery-powered electric cars.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-VAT-2025-STANDARD-10', (SELECT source_document_id FROM doc WHERE source_code='VN-LAW-48-2024-VAT'),
    'article', 'Article 9 VAT rates',
    'The standard VAT rate is 10%, except goods and services subject to 0% or 5% or non-taxable treatment. Goods subject to special consumption tax are excluded from temporary 2% VAT reduction measures except gasoline.',
    '标准VAT税率为10%，除适用0%、5%或不征税项目外。受特别消费税约束的商品通常不适用临时2% VAT减免（汽油除外）。',
    'Standard VAT source for imported passenger vehicles; passenger vehicles subject to SCT remain treated as 10% for this model.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
) rows(clause_code, source_document_id, locator_type, locator_value, original_text, translated_text_cn, evidence_summary, extraction_method, extracted_at, verification_status)
ON CONFLICT (clause_code) DO UPDATE SET
  source_document_id=EXCLUDED.source_document_id,
  locator_type=EXCLUDED.locator_type,
  locator_value=EXCLUDED.locator_value,
  original_text=EXCLUDED.original_text,
  translated_text_cn=EXCLUDED.translated_text_cn,
  evidence_summary=EXCLUDED.evidence_summary,
  extraction_method=EXCLUDED.extraction_method,
  extracted_at=EXCLUDED.extracted_at,
  verification_status=EXCLUDED.verification_status;

WITH vn AS (SELECT country_id FROM ref.country WHERE iso2='VN')
INSERT INTO rules.vehicle_tax_route (
  route_code, country_id, decision_order, route_name_cn, route_name_en,
  route_kind, import_mode, classification_granularity, decision_condition,
  required_input_fields, calculation_dsl, fallback_route_code, decision_note,
  effective_from, effective_to, version, record_status, verification_status
)
SELECT 'ROUTE-VN-01-CBU-NEW-PASSENGER', vn.country_id, 1,
  '越南CBU新乘用车进口', 'Vietnam CBU new passenger vehicle import',
  'CBU', 'CBU'::ref.import_mode, 'FINISHED_VEHICLE',
  jsonb_build_object('country','VN','import_mode','CBU','new_or_used','NEW','vehicle_use','PASSENGER','heading','8703'),
  jsonb_build_array('effective_date','new_or_used','vn_hs8_code','origin_country_iso2','origin_regime','origin_rule_qualified','customs_value','seat_count_including_driver','vehicle_body_type','powertrain','engine_displacement_cc_if_applicable','hybrid_energy_standard_qualified_if_applicable','battery_powered_bev_if_applicable'),
  jsonb_build_object(
    'formula','import_duty=CIF*duty_rate; sct=(CIF+import_duty)*sct_rate; vat=(CIF+import_duty+sct)*vat_rate; effective_rate=(import_duty+sct+vat)/CIF',
    'tax_sequence', jsonb_build_array('IMPORT_DUTY','SPECIAL_CONSUMPTION_TAX','VAT')
  ),
  NULL,
  'Vietnam CBU new passenger vehicle formula. Used cars may use absolute/mixed duties and are outside this route. Vietnam HS8 is stored as national_tariff_code plus 00 for schema compatibility.',
  DATE '2026-01-01', NULL, 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
FROM vn
ON CONFLICT (route_code, version) DO UPDATE SET
  decision_condition=EXCLUDED.decision_condition,
  required_input_fields=EXCLUDED.required_input_fields,
  calculation_dsl=EXCLUDED.calculation_dsl,
  decision_note=EXCLUDED.decision_note,
  record_status='ACTIVE',
  verification_status=EXCLUDED.verification_status,
  updated_at=now();

WITH route AS (SELECT vehicle_tax_route_id FROM rules.vehicle_tax_route WHERE route_code='ROUTE-VN-01-CBU-NEW-PASSENGER' AND version=1),
     vn AS (SELECT country_id FROM ref.country WHERE iso2='VN'),
     src AS (
       SELECT
        (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-MFN-8703-CBU-TARIFF-2025') AS tariff_clause,
        (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-SCT-2026-PASSENGER-CARS-ICE') AS sct_ice_clause,
        (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-SCT-2026-HYBRID-70PCT-CONDITION') AS sct_hybrid_clause,
        (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-SCT-2026-BEV-RATES') AS sct_bev_clause,
        (SELECT source_clause_id FROM evidence.source_clause WHERE clause_code='VN-VAT-2025-STANDARD-10') AS vat_clause
     ),
     rows AS (
       -- ICE gasoline, common CBU passenger lines, 9 seats or fewer.
       SELECT 'VN-CBU-MFN-87032145-ICEGAS-SEDAN-LE1000-2026' code, '870321' hs6, '8703214500' ntc, '8703.21.45' hs8,
              'Passenger car, spark ignition, <=1,000cc, Sedan, CBU/new' descr, 'ICE_GASOLINE'::ref.powertrain pt,
              0.70 duty, 0.35 sct, src.sct_ice_clause tax_clause,
              jsonb_build_object('vn_hs8_code','8703.21.45','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','displacement_cc_min',0,'displacement_cc_max',1000) cond FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032219-ICEGAS-OTHER-1000-1500-2026','870322','8703221900','8703.22.19','Passenger car, spark ignition, >1,000-1,500cc, other passenger car, CBU/new','ICE_GASOLINE'::ref.powertrain,0.70,0.35,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.22.19','new_or_used','NEW','seat_count_max',9,'body_type','PASSENGER_OTHER','displacement_cc_min',1000,'displacement_cc_max',1500) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032355-ICEGAS-SEDAN-1500-1800-2026','870323','8703235500','8703.23.55','Passenger car, spark ignition, >1,500-1,800cc, Sedan, CBU/new','ICE_GASOLINE'::ref.powertrain,0.70,0.40,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.23.55','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','displacement_cc_min',1500,'displacement_cc_max',1800) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032356-ICEGAS-SEDAN-1800-2000-2026','870323','8703235600','8703.23.56','Passenger car, spark ignition, >1,800-2,000cc, Sedan, CBU/new','ICE_GASOLINE'::ref.powertrain,0.70,0.40,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.23.56','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','displacement_cc_min',1800,'displacement_cc_max',2000) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032357-ICEGAS-SEDAN-2000-2500-2026','870323','8703235700','8703.23.57','Passenger car, spark ignition, >2,000-2,500cc, Sedan, CBU/new','ICE_GASOLINE'::ref.powertrain,0.50,0.50,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.23.57','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','displacement_cc_min',2000,'displacement_cc_max',2500,'decree_73_2025_reduced_mfn_rate',true) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032363-ICEGAS-SUV4WD-2000-2500-2026','870323','8703236300','8703.23.63','Passenger car, spark ignition, >2,000-2,500cc, other motor car 4WD, CBU/new','ICE_GASOLINE'::ref.powertrain,0.50,0.50,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.23.63','new_or_used','NEW','seat_count_max',9,'body_type','OTHER_MOTOR_CAR','drive_type','4WD_AWD','displacement_cc_min',2000,'displacement_cc_max',2500,'decree_73_2025_reduced_mfn_rate',true) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032367-ICEGAS-SUV2WD-2000-2500-2026','870323','8703236700','8703.23.67','Passenger car, spark ignition, >2,000-2,500cc, other motor car non-4WD, CBU/new','ICE_GASOLINE'::ref.powertrain,0.70,0.50,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.23.67','new_or_used','NEW','seat_count_max',9,'body_type','OTHER_MOTOR_CAR','drive_type','2WD','displacement_cc_min',2000,'displacement_cc_max',2500) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032358-ICEGAS-SEDAN-2500-3000-2026','870323','8703235800','8703.23.58','Passenger car, spark ignition, >2,500-3,000cc, Sedan, CBU/new','ICE_GASOLINE'::ref.powertrain,0.52,0.60,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.23.58','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','displacement_cc_min',2500,'displacement_cc_max',3000) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032445-ICEGAS-SEDAN-4WD-GT3000-2026','870324','8703244500','8703.24.45','Passenger car, spark ignition, >3,000cc, Sedan 4WD, CBU/new','ICE_GASOLINE'::ref.powertrain,0.47,0.90,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.24.45','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','drive_type','4WD_AWD','displacement_cc_min',3000,'displacement_cc_max',4000) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032449-ICEGAS-SEDAN-2WD-GT3000-2026','870324','8703244900','8703.24.49','Passenger car, spark ignition, >3,000cc, Sedan non-4WD, CBU/new','ICE_GASOLINE'::ref.powertrain,0.52,0.90,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.24.49','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','drive_type','2WD','displacement_cc_min',3000,'displacement_cc_max',4000) FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87032451-ICEGAS-SUV4WD-GT3000-2026','870324','8703245100','8703.24.51','Passenger car, spark ignition, >3,000cc, other motor car 4WD, CBU/new','ICE_GASOLINE'::ref.powertrain,0.32,0.90,src.sct_ice_clause,jsonb_build_object('vn_hs8_code','8703.24.51','new_or_used','NEW','seat_count_max',9,'body_type','OTHER_MOTOR_CAR','drive_type','4WD_AWD','displacement_cc_min',3000,'displacement_cc_max',4000,'decree_73_2025_reduced_mfn_rate',true) FROM src
       -- HEV/PHEV representative CBU lines: excise stored as qualifying 70% SCT rate; condition marks fuel-saving qualification required.
       UNION ALL SELECT 'VN-CBU-MFN-87034094-HEV-1800-2000-QUAL-2026','870340','8703409400','8703.40.94','HEV passenger car, spark ignition + electric, non-plug-in, >1,800-2,000cc, qualifying 70% SCT','HEV'::ref.powertrain,0.70,0.28,src.sct_hybrid_clause,jsonb_build_object('vn_hs8_code','8703.40.94','new_or_used','NEW','seat_count_max',9,'displacement_cc_min',1800,'displacement_cc_max',2000,'hybrid_sct_70pct_qualification_required',true,'fallback_if_not_qualified','ordinary_ICE_SCT_rate_for_same_type') FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87036084-PHEV-1800-2000-QUAL-2026','870360','8703608400','8703.60.84','PHEV passenger car, spark ignition + electric, externally chargeable, >1,800-2,000cc, qualifying 70% SCT','PHEV'::ref.powertrain,0.70,0.28,src.sct_hybrid_clause,jsonb_build_object('vn_hs8_code','8703.60.84','new_or_used','NEW','seat_count_max',9,'displacement_cc_min',1800,'displacement_cc_max',2000,'externally_chargeable',true,'hybrid_sct_70pct_qualification_required',true,'fallback_if_not_qualified','ordinary_ICE_SCT_rate_for_same_type') FROM src
       -- BEV CBU: split SCT period.
       UNION ALL SELECT 'VN-CBU-MFN-87038097-BEV-SEDAN-2026-2027','870380','8703809700','8703.80.97','BEV passenger car, electric motor only, Sedan, CBU/new; SCT 2026-2027 window','BEV'::ref.powertrain,0.70,0.03,src.sct_bev_clause,jsonb_build_object('vn_hs8_code','8703.80.97','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','battery_powered_bev',true,'sct_vehicle_category','passenger_<=9_seats','sct_window','2026-01-01..2027-02-28') FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87038097-BEV-SEDAN-FROM2027','870380','8703809700','8703.80.97','BEV passenger car, electric motor only, Sedan, CBU/new; SCT from 2027-03-01','BEV'::ref.powertrain,0.70,0.11,src.sct_bev_clause,jsonb_build_object('vn_hs8_code','8703.80.97','new_or_used','NEW','seat_count_max',9,'body_type','SEDAN','battery_powered_bev',true,'sct_vehicle_category','passenger_<=9_seats','sct_window','from_2027-03-01') FROM src
       UNION ALL SELECT 'VN-CBU-MFN-87038098-BEV-OTHER-2026-2027','870380','8703809800','8703.80.98','BEV passenger car, electric motor only, other motor car, CBU/new; SCT 2026-2027 window','BEV'::ref.powertrain,0.70,0.03,src.sct_bev_clause,jsonb_build_object('vn_hs8_code','8703.80.98','new_or_used','NEW','seat_count_max',9,'body_type','OTHER_MOTOR_CAR','battery_powered_bev',true,'sct_vehicle_category','passenger_<=9_seats','sct_window','2026-01-01..2027-02-28') FROM src
     )
INSERT INTO customs.vehicle_tariff_rate_line (
  rate_line_code, country_id, vehicle_tax_route_id, tariff_schedule_code,
  tariff_year, origin_regime, trade_agreement_id, hs6_code, national_tariff_code,
  linked_pdk_tariff_code, tariff_description, powertrain, vehicle_category,
  import_duty_rate, sales_tax_rate, excise_duty_rate,
  sales_tax_treatment, excise_treatment, eligibility_condition,
  tariff_source_clause_id, tax_treatment_source_clause_id,
  effective_from, effective_to, version, record_status,
  verification_status, route_verification_status
)
SELECT
  rows.code, vn.country_id, route.vehicle_tax_route_id, 'VN-MFN-2025-CBU-8703',
  2026, 'MFN'::ref.origin_regime, NULL::uuid, rows.hs6, rows.ntc,
  NULL::text, rows.descr, rows.pt, 'PASSENGER_VEHICLE_8703_NEW_CBU',
  rows.duty::numeric, 0.10::numeric, rows.sct::numeric,
  'TAXABLE', 'STATUTORY_RATE', rows.cond || jsonb_build_object(
    'vat_rate_source','VN-VAT-2025-STANDARD-10',
    'calculation_formula','D=CIF*d; SCT=(CIF+D)*sct; VAT=(CIF+D+SCT)*0.10',
    'excluded_scope', jsonb_build_array('USED_CAR','CKD','PARTS','TWO_WHEELERS')
  ),
  src.tariff_clause, rows.tax_clause,
  CASE WHEN rows.code LIKE '%FROM2027' THEN DATE '2027-03-01' ELSE DATE '2026-01-01' END,
  CASE WHEN rows.code LIKE '%2026-2027' THEN DATE '2027-03-01' ELSE NULL::date END,
  1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status, 'CANDIDATE'::ref.verification_status
FROM rows, vn, route, src
ON CONFLICT (rate_line_code, version) DO UPDATE SET
  tariff_description=EXCLUDED.tariff_description,
  import_duty_rate=EXCLUDED.import_duty_rate,
  sales_tax_rate=EXCLUDED.sales_tax_rate,
  excise_duty_rate=EXCLUDED.excise_duty_rate,
  eligibility_condition=EXCLUDED.eligibility_condition,
  tariff_source_clause_id=EXCLUDED.tariff_source_clause_id,
  tax_treatment_source_clause_id=EXCLUDED.tax_treatment_source_clause_id,
  effective_from=EXCLUDED.effective_from,
  effective_to=EXCLUDED.effective_to,
  record_status='ACTIVE',
  verification_status=EXCLUDED.verification_status,
  updated_at=now();

COMMIT;
