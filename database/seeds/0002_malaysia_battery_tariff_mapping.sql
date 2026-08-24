BEGIN;

-- Evidence captured from the official JKDM HS Explorer PDK 2025 result.
-- The tariff line is verified; final classification of a specific enterprise
-- product remains subject to technical facts and customs review.

UPDATE evidence.source_document
SET
  content_sha256 = '300799394e0c87118d525acb0f750ad6c923e5449c91e9f3a39494405fa3cb6b',
  archived_object_key = 'evidence/my/2026-07-28/JKDM_HS_Explorer_PDK2025_8507603300.png'
WHERE source_document_id = '30000000-0000-4000-8000-000000000003';

INSERT INTO evidence.source_document (
  source_document_id, source_code, authority_id, document_title,
  document_number, source_type, official_status, canonical_url,
  publication_date, effective_from, accessed_at, language_code,
  content_sha256, archived_object_key, version, record_status
) VALUES (
  '30000000-0000-4000-8000-000000000004',
  'SRC-MY-JKDM-8507603300-IMPORT-CONTROL',
  '20000000-0000-4000-8000-000000000001',
  'JKDM HS Explorer - 8507603300 Import Prohibition Schedule Detail',
  NULL, 'OFFICIAL_PORTAL', 'OFFICIAL',
  'https://ezhs.customs.gov.my/',
  NULL, NULL, TIMESTAMPTZ '2026-07-28 00:00:00+08', 'en',
  '515c468a79de6ee3666193c88edab2cec9643abcf142477186d2e86b95385dd6',
  'evidence/my/2026-07-28/JKDM_HS_Explorer_8507603300_Import_Control.png',
  1, 'ACTIVE'
)
ON CONFLICT DO NOTHING;

INSERT INTO evidence.source_clause (
  source_clause_id, clause_code, source_document_id, locator_type,
  locator_value, original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
) VALUES
  ('40000000-0000-4000-8000-000000000005',
   'CLAUSE-MY-PDK2025-8507603300-RATE',
   '30000000-0000-4000-8000-000000000003',
   'HS_EXPLORER_RESULT',
   'PDK 2025; 8507.60.3300; tariff result row',
   $rate$Of a kind used for vehicles in Chapter 87$rate$,
   $ratecn$用于第87章车辆的锂离子蓄电池。$ratecn$,
   $ratesum$Unit u; import duty 20%; export duty 0%; SST display rate 10%.$ratesum$,
   'MANUAL_OFFICIAL_PORTAL_SCREENSHOT',
   TIMESTAMPTZ '2026-07-28 00:00:00+08',
   'VERIFIED'),
  ('40000000-0000-4000-8000-000000000006',
   'CLAUSE-MY-IMPORT-PROHIBITION-8507603300',
   '30000000-0000-4000-8000-000000000004',
   'HS_EXPLORER_DETAIL',
   'Import Prohibition Schedule 2; Part 2; PDK key 8507603300',
   $control$All kinds of new reusable batteries (accumulators) for motor vehicles of headings 87.01, 87.02, 87.03, 87.04, 87.05, 87.09 and 87.26$control$,
   $controlcn$用于所列第87章机动车辆的各种新可充电蓄电池。$controlcn$,
   $controlsum$Applies to all countries; issuing authority is MITI; the OGA code and subsequent visible fields were blank.$controlsum$,
   'MANUAL_OFFICIAL_PORTAL_SCREENSHOT',
   TIMESTAMPTZ '2026-07-28 00:00:00+08',
   'VERIFIED')
ON CONFLICT DO NOTHING;

UPDATE evidence.source_clause
SET source_document_id = '30000000-0000-4000-8000-000000000004'
WHERE clause_code = 'CLAUSE-MY-IMPORT-PROHIBITION-8507603300';

INSERT INTO customs.tariff_mapping (
  mapping_id, mapping_code, country_id, candidate_id, tariff_version,
  national_tariff_code, tariff_description, origin_regime,
  trade_agreement_id, duty_rate, rate_type, additional_measure,
  eligibility_condition, effective_from, effective_to, version,
  source_clause_id, record_status, verification_status
) VALUES (
  'b0000000-0000-4000-8000-000000000001',
  'MAP-MY-PDK2025-8507603300-MFN',
  '10000000-0000-4000-8000-000000000001',
  '70000000-0000-4000-8000-000000000001',
  'PDK-2025',
  '8507603300',
  'Of a kind used for vehicles in Chapter 87',
  'MFN',
  NULL,
  0.20000000,
  'AD_VALOREM',
  '{
    "unit": "u",
    "export_duty_rate": 0.00000000,
    "sst_display_rate": 0.10000000,
    "import_control": {
      "schedule": "2",
      "part": "2",
      "country_scope": "ALL_COUNTRIES",
      "issuing_authority_code": "MY-MITI",
      "oga_code": null,
      "portal_mandatory_flag": null,
      "exact_licence_type": null
    }
  }'::jsonb,
  '{}'::jsonb,
  DATE '2025-11-01',
  NULL,
  1,
  '40000000-0000-4000-8000-000000000005',
  'DRAFT',
  'VERIFIED'
)
ON CONFLICT DO NOTHING;

INSERT INTO rules.approval_matrix (
  requirement_id, requirement_code, country_id, requirement_type,
  applicable_object, import_mode, powertrain, trigger_condition,
  required_document, authority_id, benefit_rule_id, failure_consequence,
  effective_from, effective_to, version, source_clause_id,
  record_status, verification_status
) VALUES (
  '90000000-0000-4000-8000-000000000002',
  'REQ-MY-IMPORT-CONTROL-8507603300',
  '10000000-0000-4000-8000-000000000001',
  'RULING_RECOMMENDED',
  'NEW_RECHARGEABLE_MOTOR_VEHICLE_BATTERY',
  NULL,
  NULL,
  '{
    "all": [
      {"field":"scenario.country_iso2","operator":"EQ","value":"MY"},
      {"field":"classification.national_tariff_code","operator":"EQ","value":"8507603300"}
    ]
  }'::jsonb,
  '["MITI approval or import licence: exact document type pending legal schedule review"]'::jsonb,
  '20000000-0000-4000-8000-000000000002',
  NULL,
  'The tariff line is listed in Import Prohibition Schedule 2 Part 2, but the portal Mandatory and OGA Code fields are blank. Obtain the controlling legal conditions or MITI confirmation before clearance.',
  DATE '2026-07-28',
  NULL,
  1,
  '40000000-0000-4000-8000-000000000006',
  'DRAFT',
  'CANDIDATE'
)
ON CONFLICT DO NOTHING;

-- Correct an earlier local run of this seed, if any, without deleting history.
UPDATE customs.tariff_mapping
SET additional_measure = jsonb_set(
  additional_measure,
  '{import_control,portal_mandatory_flag}',
  'null'::jsonb,
  true
)
WHERE mapping_code = 'MAP-MY-PDK2025-8507603300-MFN';

UPDATE rules.approval_matrix
SET
  requirement_type = 'RULING_RECOMMENDED',
  failure_consequence =
    'The tariff line is listed in Import Prohibition Schedule 2 Part 2, but the portal Mandatory and OGA Code fields are blank. Obtain the controlling legal conditions or MITI confirmation before clearance.',
  verification_status = 'CANDIDATE'
WHERE requirement_code = 'REQ-MY-IMPORT-CONTROL-8507603300';

UPDATE audit.missing_data
SET status = 'RESOLVED', resolved_at = now()
WHERE missing_data_id IN (
  'a0000000-0000-4000-8000-000000000001',
  'a0000000-0000-4000-8000-000000000002'
)
AND status <> 'RESOLVED';

UPDATE audit.missing_data
SET status = 'RESOLVED', resolved_at = now()
WHERE missing_data_id = 'a0000000-0000-4000-8000-000000000003'
AND status <> 'RESOLVED';

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description,
  data_owner, data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
) VALUES
  ('a0000000-0000-4000-8000-000000000005', NULL,
   'rules.approval_matrix.required_document',
   'HS Explorer identifies MITI and Import Prohibition Schedule 2 Part 2, but OGA Code, Mandatory and the exact approval or licence document are blank.',
   'REGULATORY_OWNER', 'AUTHORITY_CONFIRMATION', 'PUBLIC',
   'IMPORT_CLEARANCE', 'P0',
   'Locate the controlling prohibition order schedule or obtain written confirmation from MITI for tariff code 8507603300.',
   'https://ezhs.customs.gov.my/', 'OPEN'),
  ('a0000000-0000-4000-8000-000000000006', NULL,
   'rules.country_rule_card.sst_calculation_formula',
   'HS Explorer displays SST 10%, but the applicable Sales Tax order, tax point, exemptions and calculation base have not yet been clause-verified.',
   'TAX_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'SST_CALCULATION', 'P0',
   'Verify the Sales Tax (Rate of Tax) Order 2025 line and imported-goods calculation sequence before creating an executable SST rule.',
   'https://mysst.customs.gov.my/', 'OPEN')
ON CONFLICT DO NOTHING;

COMMIT;
