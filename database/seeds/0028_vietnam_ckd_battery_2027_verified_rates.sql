BEGIN;

-- Vietnam CKD traction-battery tariff verification, 2027.
-- Scope is deliberately limited to the BEV/CKD traction-battery CCU and
-- national tariff lines 85076033, 85076039 and 85076090.  It must not alter
-- tariff mappings for other components or other RCEP origin groups.
--
-- Verified facts used by this seed:
--   MFN    = 5% (Decree 26/2023/ND-CP, as amended where applicable)
--   ACFTA  = 0% (Decree 118/2022/ND-CP, China origin)
--   RCEP   = 0% (Decree 129/2022/ND-CP, China origin)
--
-- effective_to is an exclusive boundary.  2028-01-01 therefore includes
-- every declaration date in calendar year 2027, including 2027-12-31.

-- Promote the four legal source records used by these rows to the official
-- Government of Vietnam legal portal.  The earlier round-1 seed used mirror
-- URLs; this idempotent refresh preserves the existing source codes while
-- making the provenance auditable.
WITH vn_gov AS (
  SELECT authority_id
  FROM ref.authority
  WHERE authority_code = 'VN_GOVERNMENT'
)
INSERT INTO evidence.source_document (
  source_code, authority_id, document_title, document_number, source_type,
  official_status, canonical_url, publication_date, effective_from, effective_to,
  accessed_at, language_code, version, record_status
)
SELECT * FROM (
  SELECT
    'VN-DECREE-26-2023-IMPORT-TARIFF-AUTO-PARTS',
    (SELECT authority_id FROM vn_gov),
    'Nghị định số 26/2023/NĐ-CP: Biểu thuế xuất khẩu, Biểu thuế nhập khẩu ưu đãi và Danh mục hàng hóa',
    '26/2023/NĐ-CP',
    'REGULATION'::ref.source_type,
    'OFFICIAL'::ref.official_status,
    'https://vanban.chinhphu.vn/?docid=208020&pageid=27160',
    DATE '2023-05-31', DATE '2023-07-15', NULL::date,
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'vi', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT
    'VN-DECREE-199-2025-AUTO-PARTS-AMEND',
    (SELECT authority_id FROM vn_gov),
    'Nghị định số 199/2025/NĐ-CP sửa đổi, bổ sung Nghị định số 26/2023/NĐ-CP',
    '199/2025/NĐ-CP',
    'REGULATION'::ref.source_type,
    'OFFICIAL'::ref.official_status,
    'https://vanban.chinhphu.vn/?classid=0&docid=214494&pageid=27160',
    DATE '2025-07-08', DATE '2025-07-08', NULL::date,
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'vi', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT
    'VN-DECREE-118-2022-ACFTA',
    (SELECT authority_id FROM vn_gov),
    'Nghị định số 118/2022/NĐ-CP: Biểu thuế nhập khẩu ưu đãi đặc biệt ACFTA 2022-2027',
    '118/2022/NĐ-CP',
    'TREATY'::ref.source_type,
    'OFFICIAL'::ref.official_status,
    'https://vanban.chinhphu.vn/?classid=1&docid=207167&pageid=27160&typegroupid=',
    DATE '2022-12-30', DATE '2022-12-30', DATE '2028-01-01',
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'vi', 1, 'ACTIVE'::ref.record_status
  UNION ALL SELECT
    'VN-DECREE-129-2022-RCEP',
    (SELECT authority_id FROM vn_gov),
    'Nghị định số 129/2022/NĐ-CP: Biểu thuế nhập khẩu ưu đãi đặc biệt RCEP 2022-2027',
    '129/2022/NĐ-CP',
    'TREATY'::ref.source_type,
    'OFFICIAL'::ref.official_status,
    'https://vanban.chinhphu.vn/?classid=1&docid=207257&pageid=27160',
    DATE '2022-12-30', DATE '2022-12-30', DATE '2028-01-01',
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'vi', 1, 'ACTIVE'::ref.record_status
) AS rows(
  source_code, authority_id, document_title, document_number, source_type,
  official_status, canonical_url, publication_date, effective_from, effective_to,
  accessed_at, language_code, version, record_status
)
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
  version = EXCLUDED.version,
  record_status = EXCLUDED.record_status;

-- Create narrowly scoped, verified evidence clauses.  They are intentionally
-- separate from the generic round-1 ACFTA/RCEP clauses so only the three
-- battery mappings below become VERIFIED; unrelated rows remain candidates.
WITH doc AS (
  SELECT source_document_id, source_code
  FROM evidence.source_document
)
INSERT INTO evidence.source_clause (
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
SELECT * FROM (
  SELECT
    'VN-CKD-BATTERY-MFN-850760-2027-5PCT',
    (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-26-2023-IMPORT-TARIFF-AUTO-PARTS'),
    'tariff_line',
    'Appendix II / heading 8507.60 / national lines 85076033, 85076039, 85076090',
    'Preferential import tariff (MFN): 8507.60.33, 8507.60.39 and 8507.60.90 — 5%.',
    '普通优惠进口税率（MFN）：8507.60.33、8507.60.39和8507.60.90均为5%。',
    'Verified 2027 MFN import-duty rate for Vietnam CKD traction-battery candidate lines.',
    'official_portal_manual_review',
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'VERIFIED'::ref.verification_status
  UNION ALL SELECT
    'VN-CKD-BATTERY-ACFTA-850760-2027-0PCT',
    (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-118-2022-ACFTA'),
    'tariff_line',
    'Appendix I / ACFTA tariff schedule / 85076033, 85076039, 85076090 / 2027 column',
    'ACFTA special preferential import tariff: 8507.60.33, 8507.60.39 and 8507.60.90 — 0% for eligible China-origin goods.',
    'ACFTA特别优惠进口税率：中国原产且满足协定条件时，8507.60.33、8507.60.39和8507.60.90均为0%。',
    'Verified 2027 ACFTA rate for China-origin Vietnam CKD traction-battery candidate lines.',
    'official_portal_manual_review',
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'VERIFIED'::ref.verification_status
  UNION ALL SELECT
    'VN-CKD-BATTERY-RCEP-850760-2027-0PCT',
    (SELECT source_document_id FROM doc WHERE source_code='VN-DECREE-129-2022-RCEP'),
    'tariff_line',
    'RCEP tariff appendix / China column / 85076033, 85076039, 85076090 / 2027 column',
    'RCEP special preferential import tariff: 8507.60.33, 8507.60.39 and 8507.60.90 — 0% for eligible China-origin goods.',
    'RCEP特别优惠进口税率：中国原产且满足协定条件时，8507.60.33、8507.60.39和8507.60.90均为0%。',
    'Verified 2027 RCEP rate for China-origin Vietnam CKD traction-battery candidate lines.',
    'official_portal_manual_review',
    TIMESTAMPTZ '2026-08-18 14:00:00+08', 'VERIFIED'::ref.verification_status
) AS rows(
  clause_code, source_document_id, locator_type, locator_value,
  original_text, translated_text_cn, evidence_summary, extraction_method,
  extracted_at, verification_status
)
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

-- Extend only the China-origin battery mappings through the end of 2027 and
-- attach the narrowly scoped verified evidence.  In particular, RCEP Japan,
-- Korea, Australia and New Zealand rows are not changed here.
WITH target AS (
  SELECT mapping.mapping_id, agreement.agreement_code, clause.source_clause_id
  FROM customs.tariff_mapping AS mapping
  JOIN ref.country AS country ON country.country_id = mapping.country_id
  JOIN customs.ccu_candidate_hs AS candidate ON candidate.candidate_id = mapping.candidate_id
  JOIN customs.customs_classification_unit AS component ON component.ccu_id = candidate.ccu_id
  JOIN ref.trade_agreement AS agreement ON agreement.trade_agreement_id = mapping.trade_agreement_id
  JOIN evidence.source_clause AS clause
    ON clause.clause_code = CASE agreement.agreement_code
      WHEN 'ACFTA' THEN 'VN-CKD-BATTERY-ACFTA-850760-2027-0PCT'
      WHEN 'RCEP' THEN 'VN-CKD-BATTERY-RCEP-850760-2027-0PCT'
    END
  WHERE country.iso2 = 'VN'
    AND component.ccu_code = 'VN-CKD-TRACTION-BATTERY'
    AND mapping.origin_regime = 'FTA'::ref.origin_regime
    AND agreement.agreement_code IN ('ACFTA','RCEP')
    AND mapping.eligibility_condition->>'origin_group' = 'CN'
    AND mapping.national_tariff_code IN ('85076033','85076039','85076090')
    AND mapping.record_status = 'ACTIVE'::ref.record_status
)
UPDATE customs.tariff_mapping AS mapping
SET effective_to = DATE '2028-01-01',
    duty_rate = 0,
    rate_type = 'ZERO'::ref.rate_type,
    source_clause_id = target.source_clause_id,
    verification_status = 'VERIFIED'::ref.verification_status,
    eligibility_condition = mapping.eligibility_condition || jsonb_build_object(
      'verified_origin_country','CN',
      'verified_tariff_year','2027',
      'verified_at','2026-08-18T14:00:00+08:00',
      'verified_source_clause', CASE target.agreement_code
        WHEN 'ACFTA' THEN 'VN-CKD-BATTERY-ACFTA-850760-2027-0PCT'
        WHEN 'RCEP' THEN 'VN-CKD-BATTERY-RCEP-850760-2027-0PCT'
      END
    ),
    updated_at = now()
FROM target
WHERE mapping.mapping_id = target.mapping_id;

-- Add the ordinary MFN rows for the same three candidate national lines.  The
-- rows are scoped to China-origin scenario calculations but the MFN regime
-- itself does not require preferential origin proof.
WITH vn AS (
  SELECT country_id FROM ref.country WHERE iso2='VN'
), candidate AS (
  SELECT candidate.candidate_id
  FROM customs.ccu_candidate_hs AS candidate
  JOIN customs.customs_classification_unit AS component ON component.ccu_id = candidate.ccu_id
  WHERE component.ccu_code='VN-CKD-TRACTION-BATTERY'
    AND candidate.hs6_code='850760'
    AND candidate.hs_nomenclature_version='AHTN-2022'
), clause AS (
  SELECT source_clause_id
  FROM evidence.source_clause
  WHERE clause_code='VN-CKD-BATTERY-MFN-850760-2027-5PCT'
), rows(national_tariff_code, tariff_description) AS (
  VALUES
    ('85076033','锂离子蓄电池：用于第87章车辆（Dùng cho xe thuộc Chương 87）'),
    ('85076039','锂离子蓄电池：其他（Loại khác）'),
    ('85076090','锂离子蓄电池：其他（Loại khác）')
)
INSERT INTO customs.tariff_mapping (
  mapping_code, country_id, candidate_id, tariff_version, national_tariff_code,
  tariff_description, origin_regime, trade_agreement_id, duty_rate, rate_type,
  additional_measure, eligibility_condition, effective_from, effective_to,
  version, source_clause_id, record_status, verification_status
)
SELECT
  'VN-CKD-PART-MFN-CN-' || rows.national_tariff_code || '-2027',
  vn.country_id,
  candidate.candidate_id,
  'VN-MFN-2027-CKD-BATTERY',
  rows.national_tariff_code,
  rows.tariff_description,
  'MFN'::ref.origin_regime,
  NULL::uuid,
  0.05000000,
  'AD_VALOREM'::ref.rate_type,
  jsonb_build_object(
    'tax_type','IMPORT_DUTY',
    'rate_percent',5,
    'verified_tariff_year','2027',
    'verified_at','2026-08-18T14:00:00+08:00',
    'source_url','https://vanban.chinhphu.vn/?docid=208020&pageid=27160',
    'amendment_crosscheck_url','https://vanban.chinhphu.vn/?classid=0&docid=214494&pageid=27160'
  ),
  jsonb_build_object(
    'country','VN',
    'scope','NEW_PASSENGER_CAR_CKD_MAJOR_COMPONENT_ESTIMATE',
    'import_mode','CKD',
    'origin_regime','MFN',
    'origin_group','CN',
    'requires_origin_rule',false,
    'requires_proof_of_origin',false,
    'national_code_display',rows.national_tariff_code,
    'verified_tariff_year','2027',
    'verified_source_clause','VN-CKD-BATTERY-MFN-850760-2027-5PCT'
  ),
  DATE '2027-01-01', DATE '2028-01-01', 1,
  clause.source_clause_id,
  'ACTIVE'::ref.record_status,
  'VERIFIED'::ref.verification_status
FROM vn CROSS JOIN candidate CROSS JOIN clause CROSS JOIN rows
ON CONFLICT (mapping_code, version) DO UPDATE SET
  country_id = EXCLUDED.country_id,
  candidate_id = EXCLUDED.candidate_id,
  tariff_version = EXCLUDED.tariff_version,
  national_tariff_code = EXCLUDED.national_tariff_code,
  tariff_description = EXCLUDED.tariff_description,
  origin_regime = EXCLUDED.origin_regime,
  trade_agreement_id = EXCLUDED.trade_agreement_id,
  duty_rate = EXCLUDED.duty_rate,
  rate_type = EXCLUDED.rate_type,
  additional_measure = EXCLUDED.additional_measure,
  eligibility_condition = EXCLUDED.eligibility_condition,
  effective_from = EXCLUDED.effective_from,
  effective_to = EXCLUDED.effective_to,
  source_clause_id = EXCLUDED.source_clause_id,
  record_status = EXCLUDED.record_status,
  verification_status = EXCLUDED.verification_status,
  updated_at = now();

COMMIT;
