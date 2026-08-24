BEGIN;

-- Real-source minimum demo.
-- No duty or SST rate is inserted until the exact PDK 2025 tariff line is verified.

INSERT INTO ref.country (
  country_id, iso2, iso3, country_name_en, country_name_cn,
  currency_code, timezone_name, record_status
) VALUES
  ('10000000-0000-4000-8000-000000000001', 'MY', 'MYS',
   'Malaysia', '马来西亚', 'MYR', 'Asia/Kuala_Lumpur', 'ACTIVE'),
  ('10000000-0000-4000-8000-000000000002', 'CN', 'CHN',
   'China', '中国', 'CNY', 'Asia/Shanghai', 'ACTIVE')
ON CONFLICT DO NOTHING;

INSERT INTO ref.authority (
  authority_id, authority_code, country_id, authority_name,
  official_url, record_status
) VALUES
  ('20000000-0000-4000-8000-000000000001', 'MY-JKDM',
   '10000000-0000-4000-8000-000000000001',
   'Royal Malaysian Customs Department',
   'https://www.customs.gov.my/', 'ACTIVE'),
  ('20000000-0000-4000-8000-000000000002', 'MY-MITI',
   '10000000-0000-4000-8000-000000000001',
   'Ministry of Investment, Trade and Industry',
   'https://www.miti.gov.my/', 'ACTIVE')
ON CONFLICT DO NOTHING;

INSERT INTO evidence.source_document (
  source_document_id, source_code, authority_id, document_title,
  document_number, source_type, official_status, canonical_url,
  publication_date, effective_from, accessed_at, language_code,
  version, record_status
) VALUES
  ('30000000-0000-4000-8000-000000000001', 'SRC-MY-PDK-2025',
   '20000000-0000-4000-8000-000000000001',
   'Customs Duties Order 2025', 'P.U. (A) 384/2025',
   'GAZETTE', 'OFFICIAL',
   'https://www.customs.gov.my/images/06-prosedur/perintah-kastam/perintah/PUA_384.pdf',
   DATE '2025-10-31', DATE '2025-11-01',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'ms,en', 1, 'ACTIVE'),
  ('30000000-0000-4000-8000-000000000002', 'SRC-MY-MITI-AP-FAQ',
   '20000000-0000-4000-8000-000000000002',
   'Approved Permit FAQ', NULL,
   'OFFICIAL_PORTAL', 'OFFICIAL',
   'https://www.miti.gov.my/index.php/pages/view/10621',
   NULL, NULL, TIMESTAMPTZ '2026-07-28 00:00:00+08',
   'en', 1, 'ACTIVE'),
  ('30000000-0000-4000-8000-000000000003', 'SRC-MY-JKDM-HS-EXPLORER',
   '20000000-0000-4000-8000-000000000001',
   'JKDM HS Explorer - PDK 2025', NULL,
   'OFFICIAL_PORTAL', 'OFFICIAL',
   'https://ezhs.customs.gov.my/', NULL, NULL,
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'ms,en', 1, 'ACTIVE')
ON CONFLICT DO NOTHING;

INSERT INTO evidence.source_clause (
  source_clause_id, clause_code, source_document_id, locator_type,
  locator_value, original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
) VALUES
  ('40000000-0000-4000-8000-000000000001', 'CLAUSE-MY-PDK2025-P4',
   '30000000-0000-4000-8000-000000000001',
   'PARAGRAPH', 'Paragraph 4(1)',
   $p4$The classification of goods in the First Schedule shall be governed by the General Rules for the Interpretation of the Harmonized System.$p4$,
   $p4cn$第一附表货物的归类受协调制度归类总规则约束。$p4cn$,
   $p4sum$PDK 2025 paragraph 4 makes the HS General Rules binding for classification.$p4sum$,
   'MANUAL_OFFICIAL_WEB_REVIEW',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED'),
  ('40000000-0000-4000-8000-000000000002', 'CLAUSE-MY-PDK2025-GRI2A',
   '30000000-0000-4000-8000-000000000001',
   'SCHEDULE_RULE', 'Second Schedule, General Rule 2(a)',
   NULL, NULL,
   $gri2a$Rule 2(a) may treat incomplete, unfinished, unassembled or disassembled goods as the complete article when the rule requirements are met.$gri2a$,
   'LOCATOR_IDENTIFIED_TEXT_PENDING_ARCHIVE',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'CANDIDATE'),
  ('40000000-0000-4000-8000-000000000003', 'CLAUSE-MY-MITI-AP-CKD',
   '30000000-0000-4000-8000-000000000002',
   'WEB_SECTION', 'FAQ - products subject to AP - Vehicle',
   $aptext$All Motorvehicles and Motorcycles (including commercial vehicles) imported as Completely Built-Up (CBU) and Completely Knocked-Down (CKD).$aptext$,
   $apcn$以CBU或CKD方式进口的各类机动车和摩托车（包括商用车）属于AP监管对象。$apcn$,
   $apsum$MITI lists CBU and CKD motor vehicles as products subject to Approved Permit control.$apsum$,
   'MANUAL_OFFICIAL_WEB_REVIEW',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED'),
  ('40000000-0000-4000-8000-000000000004', 'CLAUSE-MY-HS850760-PENDING',
   '30000000-0000-4000-8000-000000000003',
   'SEARCH_TARGET', 'PDK 2025; HS6 850760',
   NULL, NULL,
   $hs850760$The international HS6 candidate for lithium-ion accumulators is 850760; the exact Malaysian national line and rate remain pending official HS Explorer confirmation.$hs850760$,
   'OFFICIAL_PORTAL_TARGET_IDENTIFIED',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'CANDIDATE')
ON CONFLICT DO NOTHING;

INSERT INTO rules.country_rule_card (
  rule_card_id, rule_code, country_id, rule_domain, rule_name_cn,
  rule_content, condition_expression, formula_expression, tariff_version,
  authority_id, effective_from, version, source_clause_id,
  record_status, verification_status
) VALUES (
  '50000000-0000-4000-8000-000000000001',
  'RULE-MY-GRI-2A-2025',
  '10000000-0000-4000-8000-000000000001',
  'CUSTOMS_CLASSIFICATION',
  '不完整、未制成、未组装或拆散货物的GRI 2(a)风险',
  '当同一票或相关货物集合可能具备完整品的基本特征时，必须评估是否按完整品归类；本记录不自动得出整车结论。',
  '{
    "all": [
      {
        "field": "scenario.import_mode",
        "operator": "IN",
        "value": ["CKD", "SKD", "PARTS"]
      },
      {
        "field": "shipment.assembly_state",
        "operator": "IN",
        "value": ["INCOMPLETE", "UNASSEMBLED", "DISASSEMBLED", "MIXED"]
      }
    ]
  }'::jsonb,
  NULL, 'PDK-2025',
  '20000000-0000-4000-8000-000000000001',
  DATE '2025-11-01', 1,
  '40000000-0000-4000-8000-000000000002',
  'DRAFT', 'CANDIDATE'
)
ON CONFLICT DO NOTHING;

INSERT INTO customs.customs_classification_unit (
  ccu_id, ccu_code, ccu_name_cn, ccu_name_en, parent_ccu_id,
  vehicle_system, unit_level, function_description, material_spec,
  technical_qualifiers, assembly_state, included_items, excluded_items,
  required_input_fields, gri_2a_risk, version, record_status,
  verification_status
) VALUES (
  '60000000-0000-4000-8000-000000000001',
  'CCU-HV-BATTERY-PACK',
  '锂离子动力电池包',
  'Lithium-ion traction battery pack',
  NULL, 'HIGH_VOLTAGE_BATTERY',
  'CUSTOMS_CLASSIFICATION_UNIT',
  'Stores electrical energy and supplies high-voltage traction power to an electric vehicle.',
  'Lithium-ion cells/modules with enclosure, busbars and battery management components; exact configuration is enterprise input.',
  '{
    "chemistry": "LITHIUM_ION",
    "vehicle_use": "TRACTION",
    "voltage_v": null,
    "capacity_kwh": null,
    "includes_bms": null,
    "includes_thermal_system": null
  }'::jsonb,
  'COMPLETE',
  '["cells_or_modules", "enclosure", "busbars", "battery_management_components_when_present"]'::jsonb,
  '["vehicle_body", "traction_motor", "inverter", "external_charger"]'::jsonb,
  '[
    "part.chemistry",
    "part.voltage_v",
    "part.capacity_kwh",
    "part.includes_bms",
    "part.includes_thermal_system",
    "shipment.assembly_state"
  ]'::jsonb,
  'MEDIUM', 1, 'DRAFT', 'CANDIDATE'
)
ON CONFLICT DO NOTHING;

INSERT INTO customs.ccu_candidate_hs (
  candidate_id, ccu_id, candidate_rank, hs_nomenclature_version,
  hs6_code, candidate_basis, exclusion_notes, source_clause_id,
  verification_status
) VALUES (
  '70000000-0000-4000-8000-000000000001',
  '60000000-0000-4000-8000-000000000001',
  1, 'HS-2022', '850760',
  'Candidate HS6 for lithium-ion accumulators; final national classification depends on product configuration and official Malaysian tariff confirmation.',
  'Do not default to heading 8708 merely because the battery pack is used in a motor vehicle.',
  '40000000-0000-4000-8000-000000000004',
  'CANDIDATE'
)
ON CONFLICT DO NOTHING;

INSERT INTO customs.ccu_risk_tag (
  ccu_risk_tag_id, ccu_id, risk_tag_type, risk_level,
  trigger_condition, risk_note, source_clause_id, verification_status
) VALUES
  ('80000000-0000-4000-8000-000000000001',
   '60000000-0000-4000-8000-000000000001',
   'GRI_2A', 'MEDIUM',
   '{"field":"shipment.assembly_state","operator":"NE","value":"COMPLETE"}'::jsonb,
   'Evaluate Rule 2(a) when the pack or related vehicle goods are presented incomplete, unassembled or disassembled.',
   '40000000-0000-4000-8000-000000000002', 'CANDIDATE'),
  ('80000000-0000-4000-8000-000000000002',
   '60000000-0000-4000-8000-000000000001',
   'HEADING_8708_EXCLUSION', 'HIGH',
   '{"field":"classification.candidate_hs6","operator":"EQ","value":"870899"}'::jsonb,
   'A specific electrical accumulator heading may take precedence over a residual motor-vehicle-parts route; confirm legal notes and product configuration.',
   NULL, 'UNVERIFIED'),
  ('80000000-0000-4000-8000-000000000003',
   '60000000-0000-4000-8000-000000000001',
   'AP_REGULATORY', 'HIGH',
   '{"field":"scenario.import_mode","operator":"EQ","value":"CKD"}'::jsonb,
   'When imported within a CKD vehicle programme, MITI AP approval must be evaluated at the vehicle or programme level.',
   '40000000-0000-4000-8000-000000000003', 'CANDIDATE')
ON CONFLICT DO NOTHING;

INSERT INTO rules.approval_matrix (
  requirement_id, requirement_code, country_id, requirement_type,
  applicable_object, import_mode, powertrain, trigger_condition,
  required_document, authority_id, benefit_rule_id, failure_consequence,
  effective_from, version, source_clause_id, record_status,
  verification_status
) VALUES (
  '90000000-0000-4000-8000-000000000001',
  'REQ-MY-AP-MOTOR-VEHICLE-CKD',
  '10000000-0000-4000-8000-000000000001',
  'MANDATORY', 'MOTOR_VEHICLE_CKD_PROGRAMME', 'CKD', NULL,
  '{
    "all": [
      {"field":"scenario.country_iso2","operator":"EQ","value":"MY"},
      {"field":"scenario.import_mode","operator":"EQ","value":"CKD"}
    ]
  }'::jsonb,
  '["MITI Approved Permit or applicable import licence evidence"]'::jsonb,
  '20000000-0000-4000-8000-000000000002',
  NULL,
  'Import clearance or project execution may be blocked; confirm the exact AP category, applicant eligibility and supporting documents with MITI.',
  DATE '2026-07-28', 1,
  '40000000-0000-4000-8000-000000000003',
  'DRAFT', 'CANDIDATE'
)
ON CONFLICT DO NOTHING;

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description,
  data_owner, data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
) VALUES
  ('a0000000-0000-4000-8000-000000000001', NULL,
   'customs.tariff_mapping.national_tariff_code',
   'The exact Malaysian national tariff line under candidate HS6 850760 has not yet been confirmed in PDK 2025.',
   'CUSTOMS_CLASSIFICATION_OWNER', 'AUTHORITY_CONFIRMATION', 'PUBLIC',
   'TARIFF_MAPPING_AND_ALL_TAX_CALCULATIONS', 'P0',
   'Search JKDM HS Explorer under PDK 2025 and retain the exact result or obtain a customs ruling.',
   'https://ezhs.customs.gov.my/', 'OPEN'),
  ('a0000000-0000-4000-8000-000000000002', NULL,
   'customs.tariff_mapping.duty_rate',
   'MFN import duty is intentionally unknown until the exact PDK 2025 national tariff line is verified.',
   'TAX_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'IMPORT_DUTY_AND_EFFECTIVE_TAX_RATE', 'P0',
   'After confirming the national tariff line, capture the PDK 2025 duty rate and clause locator.',
   'https://ezhs.customs.gov.my/', 'OPEN'),
  ('a0000000-0000-4000-8000-000000000003', NULL,
   'evidence.source_document.archived_object_key',
   'The official P.U. (A) 384/2025 PDF has been identified but is not yet archived with a content hash.',
   'EVIDENCE_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'SOURCE_IMMUTABILITY', 'P1',
   'Download the official PDF, calculate SHA-256 and store the immutable object key.',
   'https://www.customs.gov.my/images/06-prosedur/perintah-kastam/perintah/PUA_384.pdf',
   'OPEN'),
  ('a0000000-0000-4000-8000-000000000004', NULL,
   'rules.approval_matrix.effective_from',
   'The AP requirement is confirmed on the current MITI portal, but the legal commencement date and controlling schedule have not yet been clause-verified.',
   'REGULATORY_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'AP_LEGAL_VERSIONING', 'P1',
   'Locate and archive the applicable Customs (Prohibition of Imports) Order schedule and replace the provisional known-current date with the legal effective date.',
   'https://www.miti.gov.my/index.php/pages/view/10621', 'OPEN')
ON CONFLICT DO NOTHING;

COMMIT;
