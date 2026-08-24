BEGIN;

-- Official MITI AP MRA EV guidance reviewed on 2026-08-11.
-- This record deliberately keeps the CKD tax exemption window in the rule content:
-- the AP MRA operating framework runs through 2030, while the CKD EV excise and
-- sales-tax exemption is stated as running through 2027-12-31.
INSERT INTO evidence.source_document (
  source_document_id, source_code, authority_id, document_title,
  document_number, source_type, official_status, canonical_url,
  publication_date, effective_from, effective_to, accessed_at,
  language_code, version, record_status
) VALUES (
  '70000000-0000-4000-8000-000000000001',
  'SRC-MY-MITI-AP-MRA-EV-2026',
  '20000000-0000-4000-8000-000000000002',
  'Guidelines on Approved Permit for Market Research and Assembly (MRA) of Electric Vehicles',
  'GP_AP_MRA_EV_1_JAN_2026',
  'OFFICIAL_GUIDE',
  'OFFICIAL',
  'https://www.miti.gov.my/miti/resources/Approve%20Permit/Guidelines/GP_AP_MRA_EV_1_JAN_2026.pdf',
  NULL,
  DATE '2026-01-01',
  DATE '2031-01-01',
  TIMESTAMPTZ '2026-08-11 12:00:00+08',
  'en',
  1,
  'ACTIVE'
)
ON CONFLICT (source_code) DO UPDATE SET
  canonical_url = EXCLUDED.canonical_url,
  accessed_at = EXCLUDED.accessed_at,
  record_status = EXCLUDED.record_status;

INSERT INTO evidence.source_clause (
  source_clause_id, clause_code, source_document_id, locator_type,
  locator_value, original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
) VALUES (
  '70000000-0000-4000-8000-000000000002',
  'CLAUSE-MY-MITI-AP-MRA-EV-2026-SCOPE',
  (SELECT source_document_id
   FROM evidence.source_document
   WHERE source_code = 'SRC-MY-MITI-AP-MRA-EV-2026'),
  'GUIDELINE_SECTION',
  'Scope, eligibility and implementation period',
  NULL,
  'AP MRA EV政策自2026年1月1日至2030年12月31日实施；符合条件的本地组装电动车可按规定申请相关AP安排，CKD EV消费税和销售税豁免窗口延续至2027年12月31日。',
  'MITI官方指南明确了EV市场研究/本地组装AP框架、企业资格和CKD EV税费优惠期限。',
  'MANUAL_OFFICIAL_WEB_REVIEW',
  TIMESTAMPTZ '2026-08-11 12:00:00+08',
  'VERIFIED'
)
ON CONFLICT (clause_code) DO UPDATE SET
  source_document_id = EXCLUDED.source_document_id,
  translated_text_cn = EXCLUDED.translated_text_cn,
  evidence_summary = EXCLUDED.evidence_summary,
  extracted_at = EXCLUDED.extracted_at,
  verification_status = EXCLUDED.verification_status;

INSERT INTO rules.country_rule_card (
  rule_card_id, rule_code, country_id, rule_domain, rule_name_cn,
  rule_content, condition_expression, formula_expression, tariff_version,
  authority_id, effective_from, effective_to, version, source_clause_id,
  record_status, verification_status, verified_at, verified_by
) VALUES (
  '70000000-0000-4000-8000-000000000003',
  'RULE-MY-AP-MRA-EV-2026-2030',
  '10000000-0000-4000-8000-000000000001',
  'APPROVAL',
  'MITI AP MRA EV框架（2026—2030）及CKD EV税费窗口',
  '符合MITI/BPI车型批准、本地组装企业或合同组装资质等条件的BEV、FCEV、PHEV和HEV，可在AP MRA EV框架下申请相应安排。CKD EV消费税和销售税豁免应单独按其有效期核验，当前官方指南显示窗口至2027年12月31日。该记录不自动视为企业已经获批。',
  '{
    "all": [
      {"field": "scenario.import_mode", "operator": "IN", "value": ["CBU", "CKD"]},
      {"field": "vehicle.powertrain", "operator": "IN", "value": ["BEV", "FCEV", "PHEV", "HEV"]},
      {"field": "approval.miti_model_or_assembly_approval", "operator": "EQUALS", "value": "CONFIRMED"}
    ]
  }'::jsonb,
  '{
    "ap_mra_implementation_to": "2030-12-31",
    "ckd_ev_excise_sales_tax_exemption_to": "2027-12-31",
    "requires_enterprise_confirmation": true
  }'::jsonb,
  'MITI_AP_MRA_EV_2026',
  '20000000-0000-4000-8000-000000000002',
  DATE '2026-01-01',
  DATE '2031-01-01',
  1,
  '70000000-0000-4000-8000-000000000002',
  'ACTIVE',
  'VERIFIED',
  TIMESTAMPTZ '2026-08-11 12:00:00+08',
  'manual official web review'
)
ON CONFLICT (rule_code, version) DO UPDATE SET
  rule_name_cn = EXCLUDED.rule_name_cn,
  rule_content = EXCLUDED.rule_content,
  condition_expression = EXCLUDED.condition_expression,
  formula_expression = EXCLUDED.formula_expression,
  effective_from = EXCLUDED.effective_from,
  effective_to = EXCLUDED.effective_to,
  source_clause_id = EXCLUDED.source_clause_id,
  verification_status = EXCLUDED.verification_status,
  verified_at = EXCLUDED.verified_at,
  verified_by = EXCLUDED.verified_by,
  updated_at = now();

INSERT INTO rules.country_rule_card (
  rule_card_id, rule_code, country_id, rule_domain, rule_name_cn,
  rule_content, condition_expression, formula_expression, tariff_version,
  authority_id, effective_from, effective_to, version, source_clause_id,
  record_status, verification_status
) VALUES (
  '70000000-0000-4000-8000-000000000004',
  'RULE-VN-CBU-BEV-REG-FEE-2027-2030',
  'c105e945-0956-49d7-9a6d-2be867ce2d21',
  'INCENTIVE',
  '越南BEV首次登记费政策（2027—2030）待核验',
  '现有来源记录指向越南 Decree No. 202/2026/ND-CP，预计自2027年3月1日至2030年12月31日生效。该动态属于车辆首次登记环节，不等同于进口关税；在官方公报和车型适用范围完成复核前，不得计入确定的综合税率。',
  '{
    "all": [
      {"field": "vehicle.powertrain", "operator": "EQUALS", "value": "BEV"},
      {"field": "vehicle.condition", "operator": "EQUALS", "value": "NEW"}
    ]
  }'::jsonb,
  '{
    "tax_stage": "FIRST_REGISTRATION",
    "requires_official_gazette_confirmation": true
  }'::jsonb,
  'VN_REGISTRATION_FEE_2027',
  'e037102b-ae51-4c99-8e61-df1fcac94e8f',
  DATE '2027-03-01',
  DATE '2030-12-31',
  1,
  'ace621dd-1387-4f68-a2fa-5e459e45625a',
  'ACTIVE',
  'CANDIDATE'
)
ON CONFLICT (rule_code, version) DO UPDATE SET
  rule_name_cn = EXCLUDED.rule_name_cn,
  rule_content = EXCLUDED.rule_content,
  condition_expression = EXCLUDED.condition_expression,
  formula_expression = EXCLUDED.formula_expression,
  effective_from = EXCLUDED.effective_from,
  effective_to = EXCLUDED.effective_to,
  source_clause_id = EXCLUDED.source_clause_id,
  verification_status = EXCLUDED.verification_status,
  updated_at = now();

COMMIT;
