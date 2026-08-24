BEGIN;

INSERT INTO ref.trade_agreement (
  trade_agreement_id, agreement_code, agreement_name, version,
  effective_from, record_status
) VALUES
  ('f1000000-0000-4000-8000-000000000001',
   'ACFTA', 'ASEAN-China Free Trade Area', 1, DATE '2005-07-20', 'ACTIVE'),
  ('f1000000-0000-4000-8000-000000000002',
   'RCEP', 'Regional Comprehensive Economic Partnership', 1,
   DATE '2022-03-18', 'ACTIVE')
ON CONFLICT DO NOTHING;

INSERT INTO evidence.source_document (
  source_document_id, source_code, authority_id, document_title,
  document_number, source_type, official_status, canonical_url,
  publication_date, effective_from, accessed_at, language_code,
  content_sha256, archived_object_key, version, record_status
) VALUES
  ('f2000000-0000-4000-8000-000000000001',
   'SRC-MY-JKDM-HS-EXPLORER-ACFTA-850760-2026',
   '20000000-0000-4000-8000-000000000001',
   'JKDM HS Explorer - ACFTA 850760 Current Rate 2026',
   NULL, 'OFFICIAL_PORTAL', 'OFFICIAL', 'https://ezhs.customs.gov.my/',
   NULL, DATE '2026-01-01', TIMESTAMPTZ '2026-07-28 00:00:00+08',
   'en', '74249716c87e3b9645d77e132acbe1408718b7a3e0894843e4dce9a5131b8463',
   'evidence/my/2026-07-28/JKDM_HS_Explorer_ACFTA_850760_RATE_2026.png',
   1, 'ACTIVE'),
  ('f2000000-0000-4000-8000-000000000002',
   'SRC-MY-JKDM-HS-EXPLORER-RCEP-850760-2026',
   '20000000-0000-4000-8000-000000000001',
   'JKDM HS Explorer - RCEP 850760 Current Rate 2026',
   NULL, 'OFFICIAL_PORTAL', 'OFFICIAL', 'https://ezhs.customs.gov.my/',
   NULL, DATE '2026-01-01', TIMESTAMPTZ '2026-07-28 00:00:00+08',
   'en', '284f7c58355bdd5e8d0a5d0df157d6db1a123f04739564c4726a93dd6b4fb36d',
   'evidence/my/2026-07-28/JKDM_HS_Explorer_RCEP_850760_RATE_2026.png',
   1, 'ACTIVE'),
  ('f2000000-0000-4000-8000-000000000003',
   'SRC-MY-JKDM-ROO-FAQ-2026',
   '20000000-0000-4000-8000-000000000001',
   'FAQ Rules of Origin',
   NULL, 'OFFICIAL_PORTAL', 'OFFICIAL',
   'https://www.customs.gov.my/en/business/facilitation/rules-of-origin-roo/faq-rules-of-origin',
   NULL, NULL, TIMESTAMPTZ '2026-07-28 00:00:00+08',
   'en', NULL, NULL, 1, 'ACTIVE')
ON CONFLICT DO NOTHING;

INSERT INTO evidence.source_clause (
  source_clause_id, clause_code, source_document_id, locator_type,
  locator_value, original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
) VALUES
  ('f3000000-0000-4000-8000-000000000001',
   'CLAUSE-MY-ACFTA-8507603300-RATE-2026',
   'f2000000-0000-4000-8000-000000000001',
   'HS_EXPLORER_RESULT',
   'ACFTA; HS 850760; full HS 8507603300; RATE_2026',
   '8507603300 — Of a kind used for vehicles in Chapter 87 — Current Rate 0',
   'ACFTA税表中，车辆用锂离子蓄电池完整税号8507603300的2026当前税率为0。',
   'The ACFTA table retains national line 8507603300 and displays current rate zero.',
   'MANUAL_OFFICIAL_PORTAL_SCREENSHOT',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED'),
  ('f3000000-0000-4000-8000-000000000002',
   'CLAUSE-MY-RCEP-8507609000-RATE-2026',
   'f2000000-0000-4000-8000-000000000002',
   'HS_EXPLORER_RESULT',
   'RCEP; HS 850760; full HS 8507609000; RATE_2026',
   '8507609000 — Other — Current Rate 20.0%',
   'RCEP税表未显示8507603300；HS6 850760下的其他锂离子蓄电池税号8507609000的2026当前税率为20%。',
   'The RCEP table uses a different national-line structure: laptop 8507601000, aircraft 8507602000 and other 8507609000. Vehicle traction batteries require nomenclature correlation to 8507609000.',
   'MANUAL_OFFICIAL_PORTAL_SCREENSHOT',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED'),
  ('f3000000-0000-4000-8000-000000000003',
   'CLAUSE-MY-FTA-PROOF-OF-ORIGIN',
   'f2000000-0000-4000-8000-000000000003',
   'FAQ_ITEM', 'Questions 11, 12 and 17',
   'ACFTA: Form E. RCEP: Form RCEP or Declaration of Origin by Approved Exporter. Import declaration and supporting documents are required; tariff nomenclature versions must be correlated when different.',
   'ACFTA使用Form E；RCEP使用Form RCEP或经核准出口商的原产地声明。申报时还应提交进口申报及支持文件；不同协定税号版本之间需要进行关联。',
   'Preferential rate claims require proof of origin and supporting documents. A tariff-version correlation is required where the proof and FTA schedule use different HS versions.',
   'MANUAL_OFFICIAL_WEB_REVIEW',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED')
ON CONFLICT DO NOTHING;

INSERT INTO rules.country_rule_card (
  rule_card_id, rule_code, country_id, rule_domain, rule_name_cn,
  rule_content, condition_expression, formula_expression, tariff_version,
  authority_id, effective_from, version, source_clause_id,
  record_status, verification_status, verified_at, verified_by
) VALUES
  ('f4000000-0000-4000-8000-000000000001',
   'RULE-MY-ACFTA-ORIGIN-DOCUMENT',
   '10000000-0000-4000-8000-000000000001',
   'FTA', 'ACFTA优惠申报文件',
   '中国原产货物主张ACFTA优惠时，应提交Form E、进口申报及海关要求的支持文件，并满足适用原产地规则。',
   '{"all":[{"field":"scenario.origin_country_iso2","operator":"EQ","value":"CN"},{"field":"scenario.origin_regime","operator":"EQ","value":"ACFTA"},{"field":"origin.form_e_valid","operator":"EQ","value":true},{"field":"origin.rule_compliance_confirmed","operator":"EQ","value":true}]}'::jsonb,
   NULL, 'ACFTA-2024',
   '20000000-0000-4000-8000-000000000001',
   DATE '2025-01-01', 1,
   'f3000000-0000-4000-8000-000000000003',
   'ACTIVE', 'VERIFIED', now(), 'PHASE1_OFFICIAL_SOURCE_REVIEW'),
  ('f4000000-0000-4000-8000-000000000002',
   'RULE-MY-RCEP-ORIGIN-DOCUMENT',
   '10000000-0000-4000-8000-000000000001',
   'FTA', 'RCEP优惠申报文件',
   '中国原产货物主张RCEP优惠时，应提交Form RCEP或经核准出口商的原产地声明、进口申报及支持文件，并满足适用原产地规则。',
   '{"all":[{"field":"scenario.origin_country_iso2","operator":"EQ","value":"CN"},{"field":"scenario.origin_regime","operator":"EQ","value":"RCEP"},{"field":"origin.proof_valid","operator":"EQ","value":true},{"field":"origin.rule_compliance_confirmed","operator":"EQ","value":true}]}'::jsonb,
   NULL, 'RCEP-2026',
   '20000000-0000-4000-8000-000000000001',
   DATE '2026-01-01', 1,
   'f3000000-0000-4000-8000-000000000003',
   'ACTIVE', 'VERIFIED', now(), 'PHASE1_OFFICIAL_SOURCE_REVIEW')
ON CONFLICT DO NOTHING;

INSERT INTO customs.tariff_mapping (
  mapping_id, mapping_code, country_id, candidate_id, tariff_version,
  national_tariff_code, tariff_description, origin_regime,
  trade_agreement_id, duty_rate, rate_type, additional_measure,
  eligibility_condition, effective_from, version, source_clause_id,
  record_status, verification_status
) VALUES
  ('f5000000-0000-4000-8000-000000000001',
   'MAP-MY-ACFTA-2026-8507603300-CN',
   '10000000-0000-4000-8000-000000000001',
   '70000000-0000-4000-8000-000000000001',
   'ACFTA-RATE-2026', '8507603300',
   'Of a kind used for vehicles in Chapter 87',
   'FTA', 'f1000000-0000-4000-8000-000000000001',
   0.00000000, 'ZERO',
   '{"displayed_current_rate":"0","source_capture":"RATE_2026"}'::jsonb,
   '{"all":[{"field":"origin.country_iso2","operator":"EQ","value":"CN"},{"field":"origin.form_e_valid","operator":"EQ","value":true},{"field":"origin.rule_compliance_confirmed","operator":"EQ","value":true}]}'::jsonb,
   DATE '2026-01-01', 1,
   'f3000000-0000-4000-8000-000000000001',
   'ACTIVE', 'VERIFIED'),
  ('f5000000-0000-4000-8000-000000000002',
   'MAP-MY-RCEP-2026-8507609000-CN',
   '10000000-0000-4000-8000-000000000001',
   '70000000-0000-4000-8000-000000000001',
   'RCEP-RATE-2026', '8507609000',
   'Other lithium-ion accumulators',
   'FTA', 'f1000000-0000-4000-8000-000000000002',
   0.20000000, 'AD_VALOREM',
   '{"displayed_current_rate":"20.0%","source_capture":"RATE_2026","nomenclature_correlation":{"pdk_2025_line":"8507603300","rcep_2026_line":"8507609000","status":"REQUIRED"}}'::jsonb,
   '{"all":[{"field":"origin.country_iso2","operator":"EQ","value":"CN"},{"field":"origin.proof_valid","operator":"EQ","value":true},{"field":"origin.rule_compliance_confirmed","operator":"EQ","value":true},{"field":"classification.nomenclature_correlation_confirmed","operator":"EQ","value":true}]}'::jsonb,
   DATE '2026-01-01', 1,
   'f3000000-0000-4000-8000-000000000002',
   'ACTIVE', 'VERIFIED')
ON CONFLICT DO NOTHING;

UPDATE audit.missing_data
SET status = 'RESOLVED', resolved_at = now()
WHERE missing_data_id IN (
  'a0000000-0000-4000-8000-000000000007',
  'a0000000-0000-4000-8000-000000000008'
)
AND status <> 'RESOLVED';

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description,
  data_owner, data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
) VALUES
  ('f6000000-0000-4000-8000-000000000001', NULL,
   'customs.tariff_mapping[ACFTA].eligibility_condition.origin_rule',
   'The ACFTA rate and Form E requirement are verified, but enterprise-specific compliance with the product origin rule has not been established.',
   'ENTERPRISE_FTA_OWNER', 'ENTERPRISE_INPUT', 'ENTERPRISE',
   'ACFTA_ELIGIBILITY_FOR_SPECIFIC_SHIPMENT', 'P0',
   'Provide the battery production process, raw-material HS6/origin/value list and valid Form E; obtain an origin ruling if uncertain.',
   'https://www.customs.gov.my/en/business/facilitation/rules-of-origin-roo/faq-customs-ruling-on-origin',
   'WAITING_ENTERPRISE'),
  ('f6000000-0000-4000-8000-000000000002', NULL,
   'customs.tariff_mapping[RCEP].eligibility_condition.origin_rule',
   'The RCEP rate and proof types are verified, but enterprise-specific origin compliance and the tariff-version correlation have not been confirmed.',
   'ENTERPRISE_FTA_OWNER', 'ENTERPRISE_INPUT', 'MIXED',
   'RCEP_ELIGIBILITY_FOR_SPECIFIC_SHIPMENT', 'P0',
   'Provide Form RCEP or approved-exporter declaration, origin working papers and confirmation that the PDK line correlates to RCEP 8507609000.',
   'https://www.customs.gov.my/en/business/facilitation/rules-of-origin-roo/faq-customs-ruling-on-origin',
   'WAITING_ENTERPRISE')
ON CONFLICT DO NOTHING;

COMMIT;
