BEGIN;

-- Vietnam automotive incentive / preferential-policy seed, round 1.
-- Scope: policies that reduce or may reduce normal import duty, excise/SCT,
-- registration fee, or eligibility thresholds outside ordinary tariff lookup.

INSERT INTO ref.country (iso2, iso3, country_name_en, country_name_cn, currency_code, timezone_name, record_status)
VALUES ('VN', 'VNM', 'Vietnam', '越南', 'VND', 'Asia/Ho_Chi_Minh', 'ACTIVE')
ON CONFLICT (iso2) DO UPDATE SET
  iso3 = EXCLUDED.iso3,
  country_name_en = EXCLUDED.country_name_en,
  country_name_cn = EXCLUDED.country_name_cn,
  currency_code = EXCLUDED.currency_code,
  timezone_name = EXCLUDED.timezone_name,
  record_status = 'ACTIVE',
  updated_at = now();

WITH vn AS (SELECT country_id FROM ref.country WHERE iso2 = 'VN')
INSERT INTO ref.authority (authority_code, country_id, authority_name, official_url, record_status)
SELECT * FROM (
  SELECT 'VN_NATIONAL_ASSEMBLY', vn.country_id, 'National Assembly of Vietnam', 'https://quochoi.vn', 'ACTIVE'::ref.record_status FROM vn
  UNION ALL SELECT 'VN_GOVERNMENT', vn.country_id, 'Government of Vietnam', 'https://chinhphu.vn', 'ACTIVE'::ref.record_status FROM vn
  UNION ALL SELECT 'VN_MINISTRY_OF_FINANCE', vn.country_id, 'Ministry of Finance of Vietnam', 'https://mof.gov.vn', 'ACTIVE'::ref.record_status FROM vn
  UNION ALL SELECT 'VN_CUSTOMS', vn.country_id, 'Vietnam Customs', 'https://customs.gov.vn', 'ACTIVE'::ref.record_status FROM vn
  UNION ALL SELECT 'VN_MINISTRY_OF_INDUSTRY_TRADE', vn.country_id, 'Ministry of Industry and Trade of Vietnam', 'https://moit.gov.vn', 'ACTIVE'::ref.record_status FROM vn
) AS rows(authority_code, country_id, authority_name, official_url, record_status)
ON CONFLICT (authority_code) DO UPDATE SET
  country_id = EXCLUDED.country_id,
  authority_name = EXCLUDED.authority_name,
  official_url = EXCLUDED.official_url,
  record_status = 'ACTIVE',
  updated_at = now();

-- Source documents.
WITH auth AS (
  SELECT authority_id, authority_code FROM ref.authority WHERE authority_code IN (
    'VN_NATIONAL_ASSEMBLY','VN_GOVERNMENT','VN_MINISTRY_OF_FINANCE'
  )
)
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, document_number, source_type,
  official_status, canonical_url, publication_date, effective_from, effective_to,
  accessed_at, language_code, version, record_status
)
SELECT * FROM (
  SELECT 'VN-LAW-03-2022-QH15-SCT-EV',
    (SELECT authority_id FROM auth WHERE authority_code='VN_NATIONAL_ASSEMBLY'),
    'Law No. 03/2022/QH15 amending the Law on Excise Tax and other laws',
    '03/2022/QH15', 'LAW'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/law-no-03-2022-qh15-dated-january-11-2022-of-the-national-assembly-amending-and-supplementing-a-number-of-articles-of-the-law-on-public-investment-216275-doc1.html',
    DATE '2022-01-11', DATE '2022-03-01', NULL::date, now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-10-2022-REG-FEE',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 10/2022/ND-CP on registration fee',
    '10/2022/ND-CP', 'REGULATION'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/decree-no-10-2022-nd-cp-dated-january-15-2022-of-the-government-on-registration-fee-215819-doc1.html',
    DATE '2022-01-15', DATE '2022-03-01', NULL::date, now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-202-2026-REG-FEE-EV',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 202/2026/ND-CP amending Decree No. 10/2022/ND-CP on registration fee',
    '202/2026/ND-CP', 'REGULATION'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/decree-no-202-2026-nd-cp-of-the-government-amending-and-supplementing-a-number-of-articles-of-the-governments-decree-no-10-2022-nd-cp-dated-january-436912-doc1.html',
    DATE '2026-06-08', DATE '2027-03-01', DATE '2030-12-31', now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-26-2023-IMPORT-TARIFF-AUTO-PARTS',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 26/2023/ND-CP on Export Tariff, Preferential Import Tariff and Chapter 98',
    '26/2023/ND-CP', 'REGULATION'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/thue/decree-26-2023-nd-cp-export-tariff-preferential-import-tariff-and-list-of-commodity-items-254300-d1.html',
    DATE '2023-05-31', DATE '2023-07-15', NULL::date, now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-199-2025-AUTO-PARTS-AMEND',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 199/2025/ND-CP amending Decree No. 26/2023/ND-CP',
    '199/2025/ND-CP', 'REGULATION'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/thue/decree-199-2025-nd-cp-export-tariff-schedule-preferential-import-tariff-schedule-405228-d1.html',
    DATE '2025-07-08', DATE '2025-07-08', NULL::date, now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-118-2022-ACFTA',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 118/2022/ND-CP on Vietnam special preferential import tariff implementing ACFTA 2022-2027',
    '118/2022/ND-CP', 'TREATY'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/decree-no-118-2022-nd-cp-on-vietnams-special-preferential-import-tariff-to-implement-the-asean-china-agree-240222-doc1.html',
    DATE '2022-12-30', DATE '2022-12-30', DATE '2027-12-31', now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-129-2022-RCEP',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 129/2022/ND-CP on Vietnam special preferential import tariff implementing RCEP 2022-2027',
    '129/2022/ND-CP', 'TREATY'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/decree-no-129-2022-nd-cp-dated-december-30-2022-of-the-government-on-vietnams-special-preferential-import-tariff-to-implement-the-regional-comprehe-240513-doc1.html',
    DATE '2022-12-30', DATE '2022-12-30', DATE '2027-12-31', now(), 'en', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT 'VN-DECREE-126-2022-ATIGA',
    (SELECT authority_id FROM auth WHERE authority_code='VN_GOVERNMENT'),
    'Decree No. 126/2022/ND-CP on Vietnam special preferential import tariff implementing ATIGA 2022-2027',
    '126/2022/ND-CP', 'TREATY'::ref.source_type, 'SECONDARY'::ref.official_status,
    'https://english.luatvietnam.vn/decree-no-126-2022-nd-cp-dated-december-30-2022-of-the-government-on-vietnams-special-preferential-import-tariff-to-implement-the-asean-trade-in-go-240213-doc1.html',
    DATE '2022-12-30', DATE '2022-12-30', DATE '2027-12-31', now(), 'en', 1, 'ACTIVE'::ref.record_status
) AS rows(source_code, authority_id, document_title, document_number, source_type, official_status, canonical_url, publication_date, effective_from, effective_to, accessed_at, language_code, version, record_status)
ON CONFLICT (source_code) DO UPDATE SET
  authority_id = EXCLUDED.authority_id,
  document_title = EXCLUDED.document_title,
  document_number = EXCLUDED.document_number,
  source_type = EXCLUDED.source_type,
  official_status = EXCLUDED.official_status,
  canonical_url = EXCLUDED.canonical_url,
  publication_date = EXCLUDED.publication_date,
  effective_from = EXCLUDED.effective_from,
  effective_to = EXCLUDED.effective_to,
  accessed_at = EXCLUDED.accessed_at,
  language_code = EXCLUDED.language_code,
  record_status = 'ACTIVE';

-- Source clauses / evidence summaries.
WITH doc AS (SELECT source_document_id, source_code FROM evidence.source_document)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
SELECT * FROM (
  SELECT 'VN-SCT-BEV-LOW-RATE-2022-2027', (SELECT source_document_id FROM doc WHERE source_code='VN-LAW-03-2022-QH15-SCT-EV'),
    'article', 'Article 8, Point g, Clause 4, Section I / 2022-2027 rates',
    'Battery-powered electric cars: passenger cars of 9 seats or fewer 3%; 10 to under 16 seats 2%; 16 to under 24 seats 1%; passenger-cargo cars 2%, from March 1, 2022 through February 28, 2027.',
    '电池电动汽车在2022-03-01至2027-02-28期间适用较低特别消费税率：9座及以下3%，10至16座以下2%，16至24座以下1%，客货两用2%。',
    'Battery electric vehicles receive reduced special consumption tax rates for the first 5-year period.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-SCT-BEV-LOW-RATE-FROM-2027', (SELECT source_document_id FROM doc WHERE source_code='VN-LAW-03-2022-QH15-SCT-EV'),
    'article', 'Article 8, Point g, Clause 4, Section I / rates from 2027-03-01',
    'Battery-powered electric cars: from March 1, 2027, passenger cars of 9 seats or fewer 11%; 10 to under 16 seats 7%; 16 to under 24 seats 4%; passenger-cargo cars 7%.',
    '自2027-03-01起，电池电动汽车继续适用低于传统车辆的特别消费税率：9座及以下11%，10至16座以下7%，16至24座以下4%，客货两用7%。',
    'Battery electric vehicles keep preferential SCT rates after the first 5-year period, but at higher rates than 2022-2027.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-REG-FEE-BEV-0-2022-2027', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-10-2022-REG-FEE'),
    'article', 'Article 8, Clause 5(c)',
    'Battery-powered electric automobiles: for 3 years from the effective date of Decree 10/2022/ND-CP, the first-time registration fee is 0%; for subsequent 2 years, 50% of the rate for petrol/diesel cars with the same seats.',
    '电池电动汽车：自2022-03-01起3年首次登记费0%；随后2年为同座位数汽柴油车首次登记费率的50%。',
    'Original registration-fee preferential roadmap for battery electric automobiles.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-REG-FEE-BEV-0-2027-2030', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-202-2026-REG-FEE-EV'),
    'article', 'Article 1 amending Point c Clause 5 Article 8 of Decree 10/2022/ND-CP',
    'Battery-powered electric automobiles: from the effective date of Decree 202/2026/ND-CP through December 31, 2030, the first-time registration fee is 0%.',
    '电池电动汽车：自2027-03-01至2030-12-31，首次登记费率为0%。',
    'Extension of first-time registration fee exemption for battery electric automobiles through 2030.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-9849-AUTO-PARTS-DUTY-0', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-26-2023-IMPORT-TARIFF-AUTO-PARTS'),
    'article', 'Article 8',
    'Imported automobile parts under heading 98.49 may be eligible for a preferential import duty rate of 0% under the Duty Incentive Program for automobile manufacture and assembly, subject to enterprise certificate, domestic non-production condition, direct/authorized import, output and dossier procedures.',
    '98.49项下进口汽车零部件在汽车制造装配税收激励计划下可适用0%优惠进口税率，条件包括企业具备汽车制造/装配资格、零件国内不能生产、直接或授权进口、产量及申报/返还程序等。',
    '0% import-duty program for qualifying imported automobile parts used in Vietnamese vehicle manufacture/assembly.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-9849-NEV-OUTPUT-MODIFIER-2025', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-199-2025-AUTO-PARTS-AMEND'),
    'article', 'Article 1 adding Points c.3.6 and c.3.7 to Article 8 of Decree 26/2023/ND-CP',
    'Enterprises manufacturing/assembling electric, fuel-cell, hybrid, biofuel or natural-gas automobiles may add such output to minimum output thresholds when determining eligibility for the duty incentive program.',
    '制造/装配电动、燃料电池、混合动力、生物燃料或天然气汽车的企业，可将该等产量计入汽车零部件进口税激励计划的最低产量门槛。',
    'New-energy vehicle output can support eligibility for the 98.49 automobile-parts duty incentive program.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-ACFTA-ORIGIN-PREFERENTIAL-DUTY', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-118-2022-ACFTA'),
    'article', 'Articles 3-4',
    'ACFTA duty rates apply in 2022-2027 if goods are listed in the ACFTA tariff schedule, imported from eligible ACFTA parties, satisfy origin/direct shipment rules and proof-of-origin requirements.',
    'ACFTA优惠税率适用于2022-2027期间列入协定税率表、来自合格成员、满足原产地/直运规则并具备原产证明的货物。',
    'Preferential import-duty framework for China/ASEAN origin goods under ACFTA.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-RCEP-ORIGIN-PREFERENTIAL-DUTY', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-129-2022-RCEP'),
    'article', 'Articles 3-4',
    'RCEP duty rates apply in 2022-2027 if goods are listed in the applicable RCEP tariff appendix, imported from RCEP member states, satisfy origin/direct shipment rules and proof-of-origin requirements.',
    'RCEP优惠税率适用于2022-2027期间列入适用RCEP附录、来自成员国、满足原产地/直运规则并具备原产证明的货物。',
    'Preferential import-duty framework under RCEP, including China, ASEAN, Japan, Korea, Australia and New Zealand origin scenarios.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
  UNION ALL SELECT 'VN-ATIGA-ORIGIN-PREFERENTIAL-DUTY', (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-126-2022-ATIGA'),
    'article', 'Articles 3-4',
    'ATIGA duty rates apply in 2022-2027 if goods are included in the ATIGA special preferential tariff, imported from ASEAN member states, satisfy rules of origin/direct shipment and are accompanied by C/O Form D or proof of origin.',
    'ATIGA优惠税率适用于2022-2027期间列入ATIGA特别优惠税率表、来自东盟成员、满足原产地/直运规则并具备Form D或其他原产证明的货物。',
    'Preferential import-duty framework for ASEAN-origin goods under ATIGA.',
    'manual_web_research', now(), 'CANDIDATE'::ref.verification_status
) AS rows(clause_code, source_document_id, locator_type, locator_value, original_text, translated_text_cn, evidence_summary, extraction_method, extracted_at, verification_status)
ON CONFLICT (clause_code) DO UPDATE SET
  source_document_id = EXCLUDED.source_document_id,
  locator_type = EXCLUDED.locator_type,
  locator_value = EXCLUDED.locator_value,
  original_text = EXCLUDED.original_text,
  translated_text_cn = EXCLUDED.translated_text_cn,
  evidence_summary = EXCLUDED.evidence_summary,
  extraction_method = EXCLUDED.extraction_method,
  extracted_at = EXCLUDED.extracted_at,
  verification_status = EXCLUDED.verification_status;

-- Incentive / preferential policy records.
WITH vn AS (SELECT country_id FROM ref.country WHERE iso2='VN'),
     auth AS (SELECT authority_id, authority_code FROM ref.authority),
     clause AS (SELECT source_clause_id, clause_code FROM evidence.source_clause)
INSERT INTO rules.automotive_incentive_program (
  program_code, country_id, program_name_cn, import_mode, powertrain,
  incentive_scope, condition_expression, benefit_expression, approval_required,
  approval_authority_id, source_clause_id, effective_from, effective_to,
  version, record_status, verification_status
)
SELECT * FROM (
  SELECT 'VN_BEV_SCT_LOW_RATE_2022_2027', vn.country_id,
    '越南电池电动车特别消费税低税率（2022-2027）',
    NULL::ref.import_mode, 'BEV'::ref.powertrain, 'SPECIAL_CONSUMPTION_TAX',
    jsonb_build_object(
      'country','VN','vehicle_powertrain','BEV','battery_powered_only',true,
      'vehicle_categories', jsonb_build_array('passenger_<=9_seats','passenger_10_to_under_16','passenger_16_to_under_24','passenger_cargo_combined'),
      'effective_window','2022-03-01..2027-02-28',
      'not_applicable_to', jsonb_build_array('other_electric_cars_non_battery','ICE','HEV','PHEV')
    ),
    jsonb_build_object(
      'target_taxes', jsonb_build_array('EXCISE','SPECIAL_CONSUMPTION_TAX'),
      'rate_table', jsonb_build_array(
        jsonb_build_object('vehicle_category','passenger_<=9_seats','rate','0.03'),
        jsonb_build_object('vehicle_category','passenger_10_to_under_16','rate','0.02'),
        jsonb_build_object('vehicle_category','passenger_16_to_under_24','rate','0.01'),
        jsonb_build_object('vehicle_category','passenger_cargo_combined','rate','0.02')
      ),
      'calculation_stage','AT_IMPORT_OR_DOMESTIC_SALE',
      'ordinary_rate_reduction','BEV statutory preferential SCT rates replace higher ordinary vehicle SCT rates'
    ), false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-SCT-BEV-LOW-RATE-2022-2027'),
    DATE '2022-03-01', DATE '2027-03-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_BEV_SCT_LOW_RATE_FROM_2027', vn.country_id,
    '越南电池电动车特别消费税低税率（2027年起）',
    NULL::ref.import_mode, 'BEV'::ref.powertrain, 'SPECIAL_CONSUMPTION_TAX',
    jsonb_build_object('country','VN','vehicle_powertrain','BEV','battery_powered_only',true,'effective_from','2027-03-01'),
    jsonb_build_object(
      'target_taxes', jsonb_build_array('EXCISE','SPECIAL_CONSUMPTION_TAX'),
      'rate_table', jsonb_build_array(
        jsonb_build_object('vehicle_category','passenger_<=9_seats','rate','0.11'),
        jsonb_build_object('vehicle_category','passenger_10_to_under_16','rate','0.07'),
        jsonb_build_object('vehicle_category','passenger_16_to_under_24','rate','0.04'),
        jsonb_build_object('vehicle_category','passenger_cargo_combined','rate','0.07')
      )
    ), false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-SCT-BEV-LOW-RATE-FROM-2027'),
    DATE '2027-03-01', NULL, 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_BEV_FIRST_REG_FEE_0_2022_2027', vn.country_id,
    '越南电池电动车首次登记费0%（原2022-2027阶段）',
    NULL::ref.import_mode, 'BEV'::ref.powertrain, 'REGISTRATION_FEE',
    jsonb_build_object('country','VN','vehicle_powertrain','BEV','battery_powered_only',true,'registration_type','first_time','effective_window','2022-03-01..2027-02-28'),
    jsonb_build_object('target_taxes', jsonb_build_array('REGISTRATION_FEE'),'overrides',jsonb_build_object('registration_fee_rate','0'),'note','0% for first-time registration during initial three-year period; subsequent period later amended/extended'),
    false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-REG-FEE-BEV-0-2022-2027'),
    DATE '2022-03-01', DATE '2027-03-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_BEV_FIRST_REG_FEE_0_2027_2030', vn.country_id,
    '越南电池电动车首次登记费0%（2027-2030延长期）',
    NULL::ref.import_mode, 'BEV'::ref.powertrain, 'REGISTRATION_FEE',
    jsonb_build_object('country','VN','vehicle_powertrain','BEV','battery_powered_only',true,'registration_type','first_time','effective_window','2027-03-01..2030-12-31','classification_authority','Minister of Construction regulations'),
    jsonb_build_object('target_taxes', jsonb_build_array('REGISTRATION_FEE'),'overrides',jsonb_build_object('registration_fee_rate','0')),
    false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-REG-FEE-BEV-0-2027-2030'),
    DATE '2027-03-01', DATE '2031-01-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_9849_AUTO_PARTS_IMPORT_DUTY_0_MANUFACTURING_ASSEMBLY', vn.country_id,
    '越南98.49汽车零部件制造装配进口税0%激励',
    'PARTS'::ref.import_mode, NULL::ref.powertrain, 'IMPORT_DUTY',
    jsonb_build_object(
      'country','VN','heading','98.49','business_model','vehicle_manufacture_or_assembly',
      'eligible_subject','enterprise_with_MOIT_certificate_for_automobile_manufacture_assembly',
      'component_conditions', jsonb_build_object(
        'cannot_be_domestically_manufactured', true,
        'used_for_vehicle_manufacture_or_assembly', true,
        'direct_or_authorized_import_by_manufacturer', true,
        'not_8707_body', true,
        'body_frame_chassis_discreteness_requirements','required where imported sets comprise body frame and chassis'
      ),
      'output_requirements','minimum output thresholds by vehicle group/model; NEV special table includes 125 per half-year or 250 per year for each group from 2022 to 2027',
      'procedure','declare/pay normal duty first; apply for 0% and refund after duty incentive consideration period'
    ),
    jsonb_build_object('target_taxes', jsonb_build_array('IMPORT_DUTY'),'overrides',jsonb_build_object('import_duty_rate','0'),'refund_mechanism',true,'chapter_98_heading','98.49'),
    true, (SELECT authority_id FROM auth WHERE authority_code='VN_CUSTOMS'),
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-9849-AUTO-PARTS-DUTY-0'),
    DATE '2023-07-15', DATE '2028-01-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_NEV_OUTPUT_COUNTS_FOR_9849_DUTY_INCENTIVE_2025', vn.country_id,
    '越南新能源汽车产量计入98.49零部件进口税激励门槛',
    'LOCAL_PRODUCTION'::ref.import_mode, NULL::ref.powertrain, 'ELIGIBILITY_MODIFIER',
    jsonb_build_object(
      'country','VN','applies_to_program','VN_9849_AUTO_PARTS_IMPORT_DUTY_0_MANUFACTURING_ASSEMBLY',
      'eligible_powertrains', jsonb_build_array('BEV','FCEV','HEV','BIOFUEL','NATURAL_GAS'),
      'effect','NEV output may be added to minimum general/specific output thresholds for eligible manufacturers/assemblers'
    ),
    jsonb_build_object('target_taxes', jsonb_build_array('IMPORT_DUTY'),'benefit_type','eligibility_threshold_modifier','direct_rate_override',false),
    false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-9849-NEV-OUTPUT-MODIFIER-2025'),
    DATE '2025-07-08', DATE '2028-01-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_ACFTA_ORIGIN_PREFERENTIAL_IMPORT_DUTY_2022_2027', vn.country_id,
    '越南ACFTA原产优惠进口关税框架（2022-2027）',
    NULL::ref.import_mode, NULL::ref.powertrain, 'FTA_IMPORT_DUTY',
    jsonb_build_object('country','VN','agreement','ACFTA','origin_countries',jsonb_build_array('CN','ASEAN'),'requires_tariff_line_in_schedule',true,'requires_origin_rule',true,'requires_direct_shipment',true,'requires_proof_of_origin',true,'proof_examples',jsonb_build_array('ACFTA C/O or accepted proof')),
    jsonb_build_object('target_taxes', jsonb_build_array('IMPORT_DUTY'),'benefit_type','special_preferential_import_duty','rate_source','VN ACFTA tariff schedule by HS/VN code; not a flat rate'),
    false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-ACFTA-ORIGIN-PREFERENTIAL-DUTY'),
    DATE '2022-12-30', DATE '2028-01-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_RCEP_ORIGIN_PREFERENTIAL_IMPORT_DUTY_2022_2027', vn.country_id,
    '越南RCEP原产优惠进口关税框架（2022-2027）',
    NULL::ref.import_mode, NULL::ref.powertrain, 'FTA_IMPORT_DUTY',
    jsonb_build_object('country','VN','agreement','RCEP','origin_countries',jsonb_build_array('BN','KH','ID','LA','MY','SG','TH','AU','CN','KR','JP','NZ'),'requires_tariff_line_in_schedule',true,'requires_origin_rule',true,'requires_direct_shipment',true,'requires_proof_of_origin',true,'appendix_by_origin_country',true),
    jsonb_build_object('target_taxes', jsonb_build_array('IMPORT_DUTY'),'benefit_type','special_preferential_import_duty','rate_source','VN RCEP tariff appendix by origin and HS/VN code; not a flat rate'),
    false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-RCEP-ORIGIN-PREFERENTIAL-DUTY'),
    DATE '2022-12-30', DATE '2028-01-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
  UNION ALL SELECT 'VN_ATIGA_ORIGIN_PREFERENTIAL_IMPORT_DUTY_2022_2027', vn.country_id,
    '越南ATIGA原产优惠进口关税框架（2022-2027）',
    NULL::ref.import_mode, NULL::ref.powertrain, 'FTA_IMPORT_DUTY',
    jsonb_build_object('country','VN','agreement','ATIGA','origin_countries',jsonb_build_array('BN','KH','ID','LA','MY','MM','PH','SG','TH'),'requires_tariff_line_in_schedule',true,'requires_origin_rule',true,'requires_direct_shipment',true,'requires_proof_of_origin',true,'proof_examples',jsonb_build_array('C/O Form D','accepted origin proof')),
    jsonb_build_object('target_taxes', jsonb_build_array('IMPORT_DUTY'),'benefit_type','special_preferential_import_duty','rate_source','VN ATIGA tariff schedule by 8-digit code; not a flat rate'),
    false, NULL::uuid,
    (SELECT source_clause_id FROM clause WHERE clause_code='VN-ATIGA-ORIGIN-PREFERENTIAL-DUTY'),
    DATE '2022-12-30', DATE '2028-01-01', 1, 'ACTIVE'::ref.record_status, 'CANDIDATE'::ref.verification_status
  FROM vn
) AS rows(program_code, country_id, program_name_cn, import_mode, powertrain, incentive_scope, condition_expression, benefit_expression, approval_required, approval_authority_id, source_clause_id, effective_from, effective_to, version, record_status, verification_status)
ON CONFLICT (program_code, version) DO UPDATE SET
  country_id = EXCLUDED.country_id,
  program_name_cn = EXCLUDED.program_name_cn,
  import_mode = EXCLUDED.import_mode,
  powertrain = EXCLUDED.powertrain,
  incentive_scope = EXCLUDED.incentive_scope,
  condition_expression = EXCLUDED.condition_expression,
  benefit_expression = EXCLUDED.benefit_expression,
  approval_required = EXCLUDED.approval_required,
  approval_authority_id = EXCLUDED.approval_authority_id,
  source_clause_id = EXCLUDED.source_clause_id,
  effective_from = EXCLUDED.effective_from,
  effective_to = EXCLUDED.effective_to,
  record_status = EXCLUDED.record_status,
  verification_status = EXCLUDED.verification_status,
  updated_at = now();

COMMIT;
