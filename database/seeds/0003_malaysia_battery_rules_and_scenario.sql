BEGIN;

-- Phase 1 Malaysia demo: complete the verified MFN import route for
-- CCU-HV-BATTERY-PACK. Preferential ACFTA/RCEP rates are intentionally
-- excluded until the exact preferential tariff line and origin rule are verified.

INSERT INTO evidence.source_document (
  source_document_id, source_code, authority_id, document_title,
  document_number, source_type, official_status, canonical_url,
  publication_date, effective_from, accessed_at, language_code,
  version, record_status
) VALUES
  ('30000000-0000-4000-8000-000000000005',
   'SRC-MY-MITI-BATTERY-AP-SOP-2026',
   '20000000-0000-4000-8000-000000000002',
   'Standard Operating Procedure for Battery Importation',
   NULL, 'OFFICIAL_PORTAL', 'OFFICIAL',
   'https://www.miti.gov.my/index.php/pages/view/10897',
   NULL, DATE '2026-01-01',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'en', 1, 'ACTIVE'),
  ('30000000-0000-4000-8000-000000000006',
   'SRC-MY-SALES-TAX-ACT-2018',
   '20000000-0000-4000-8000-000000000001',
   'Sales Tax Act 2018',
   'Act 806', 'LAW', 'OFFICIAL',
   'https://mysst.customs.gov.my/assets/document/SST%20Act/Sales%20Tax%20Act%202018_b.pdf',
   NULL, DATE '2018-09-01',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'en', 1, 'ACTIVE'),
  ('30000000-0000-4000-8000-000000000007',
   'SRC-MY-SALES-TAX-RATE-ORDER-2025',
   '20000000-0000-4000-8000-000000000001',
   'Sales Tax (Rate of Sales Tax) Order 2025',
   'P.U. (A) 170/2025', 'GAZETTE', 'OFFICIAL',
   'https://mysst.customs.gov.my/assets/document/SST%20Orders/order/1-PUA%20170_2025.pdf',
   DATE '2025-06-09', DATE '2025-07-01',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'ms,en', 1, 'ACTIVE')
ON CONFLICT DO NOTHING;

INSERT INTO evidence.source_clause (
  source_clause_id, clause_code, source_document_id, locator_type,
  locator_value, original_text, translated_text_cn, evidence_summary,
  extraction_method, extracted_at, verification_status
) VALUES
  ('40000000-0000-4000-8000-000000000007',
   'CLAUSE-MY-MITI-BATTERY-AP-2026',
   '30000000-0000-4000-8000-000000000005',
   'WEB_SECTION', 'Requirement; Documents Needed; Processing Time',
   $ap$All importations of all kinds of new reusable batteries (accumulators) for motor vehicles under headings 87.01, 87.02, 87.03, 87.04, 87.05, 87.09 and 87.11 must obtain an Approved Permit (AP) from MITI, effective 1 January 2026 through ePermit application system.$ap$,
   $apcn$自2026年1月1日起，所列机动车辆用各种新可充电蓄电池进口必须通过ePermit系统取得MITI签发的Approved Permit。$apcn$,
   $apsum$Required documents: Customs Classification Letter, Application Letter, Product Catalogue, Invoice and Technical Evaluation Report. The TER comprises UN 38.3, applicable UN R100 or UN R136, and the relevant IEC test report. Complete applications are processed within five working days.$apsum$,
   'MANUAL_OFFICIAL_WEB_REVIEW',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED'),
  ('40000000-0000-4000-8000-000000000008',
   'CLAUSE-MY-SALES-TAX-ACT-S9-IMPORT-VALUE',
   '30000000-0000-4000-8000-000000000006',
   'SECTION', 'Section 9(2)',
   $sstbase$In the case of taxable goods imported into Malaysia, the sale value of the taxable goods shall be the sum of the value for customs duty, the amount of customs duty, if any, and the amount of excise duty, if any.$sstbase$,
   $sstbasecn$进口应税货物的销售税计税价值为海关完税价格、应付进口关税及应付消费税之和。$sstbasecn$,
   $sstbasesum$Executable imported-goods SST base: customs value + import duty + excise duty.$sstbasesum$,
   'MANUAL_OFFICIAL_LAW_REVIEW',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED'),
  ('40000000-0000-4000-8000-000000000009',
   'CLAUSE-MY-SALES-TAX-RATE-2025-P2',
   '30000000-0000-4000-8000-000000000007',
   'PARAGRAPH', 'Paragraph 2(1)',
   $sstrate$Sales tax shall be charged and levied at the rate of ten per cent on all taxable goods except goods otherwise specified or exempted under the applicable orders.$sstrate$,
   $sstratecn$除适用税率令另有规定或属于免税货物外，应税货物销售税税率为10%。$sstratecn$,
   $sstratesum$HS Explorer displays 10% for tariff line 8507603300; the general 10% rate applies subject to exemptions and special rates.$sstratesum$,
   'MANUAL_OFFICIAL_GAZETTE_REVIEW',
   TIMESTAMPTZ '2026-07-28 00:00:00+08', 'VERIFIED')
ON CONFLICT DO NOTHING;

INSERT INTO rules.country_rule_card (
  rule_card_id, rule_code, country_id, rule_domain, rule_name_cn,
  rule_content, condition_expression, formula_expression, tariff_version,
  authority_id, effective_from, version, source_clause_id,
  record_status, verification_status, verified_at, verified_by
) VALUES
  ('50000000-0000-4000-8000-000000000002',
   'RULE-MY-SST-IMPORT-BASE-2018',
   '10000000-0000-4000-8000-000000000001',
   'SALES_TAX', '进口货物销售税计税基础',
   '进口应税货物的销售税计税基础为海关完税价格、进口关税和消费税之和。',
   '{"all":[{"field":"scenario.country_iso2","operator":"EQ","value":"MY"},{"field":"transaction.is_import","operator":"EQ","value":true}]}'::jsonb,
   '{"op":"ADD","args":[{"ref":"import.customs_value"},{"ref":"tax.import_duty"},{"ref":"tax.excise_duty"}],"result_path":"tax.sst_base"}'::jsonb,
   NULL, '20000000-0000-4000-8000-000000000001',
   DATE '2018-09-01', 1,
   '40000000-0000-4000-8000-000000000008',
   'ACTIVE', 'VERIFIED', now(), 'PHASE1_OFFICIAL_SOURCE_REVIEW'),
  ('50000000-0000-4000-8000-000000000003',
   'RULE-MY-SST-RATE-8507603300-2025',
   '10000000-0000-4000-8000-000000000001',
   'SALES_TAX', '8507603300进口销售税税率',
   'PDK 2025 HS Explorer对8507603300显示SST 10%；适用时仍须检查特定免税资格。',
   '{"all":[{"field":"scenario.country_iso2","operator":"EQ","value":"MY"},{"field":"classification.national_tariff_code","operator":"EQ","value":"8507603300"},{"field":"tax.sst_exemption_approved","operator":"EQ","value":false}]}'::jsonb,
   '{"rate":0.10,"base_rule_code":"RULE-MY-SST-IMPORT-BASE-2018","result_path":"tax.sst"}'::jsonb,
   'PDK-2025', '20000000-0000-4000-8000-000000000001',
   DATE '2025-11-01', 1,
   '40000000-0000-4000-8000-000000000009',
   'ACTIVE', 'VERIFIED', now(), 'PHASE1_OFFICIAL_SOURCE_REVIEW')
ON CONFLICT DO NOTHING;

UPDATE rules.approval_matrix
SET
  requirement_type = 'MANDATORY',
  trigger_condition = '{
    "all": [
      {"field":"scenario.country_iso2","operator":"EQ","value":"MY"},
      {"field":"goods.condition","operator":"EQ","value":"NEW"},
      {"field":"goods.rechargeable","operator":"EQ","value":true},
      {"field":"goods.motor_vehicle_use","operator":"EQ","value":true}
    ]
  }'::jsonb,
  required_document = '[
    "MITI Approved Permit via ePermit",
    "Customs Classification Letter",
    "Application Letter",
    "Product Catalogue",
    "Invoice",
    "Technical Evaluation Report",
    "UN 38.3 report",
    "UN R100 or UN R136 report, as applicable",
    "Relevant IEC test report"
  ]'::jsonb,
  failure_consequence =
    'MITI Approved Permit is required before importation. Missing AP may block import clearance.',
  effective_from = DATE '2026-01-01',
  source_clause_id = '40000000-0000-4000-8000-000000000007',
  record_status = 'ACTIVE',
  verification_status = 'VERIFIED',
  updated_at = now()
WHERE requirement_code = 'REQ-MY-IMPORT-CONTROL-8507603300'
  AND version = 1;

UPDATE customs.ccu_risk_tag
SET
  trigger_condition = '{
    "all": [
      {"field":"goods.condition","operator":"EQ","value":"NEW"},
      {"field":"goods.rechargeable","operator":"EQ","value":true},
      {"field":"goods.motor_vehicle_use","operator":"EQ","value":true}
    ]
  }'::jsonb,
  risk_level = 'BLOCKING',
  risk_note = 'From 1 January 2026, covered new rechargeable motor-vehicle batteries require a MITI Approved Permit through ePermit.',
  source_clause_id = '40000000-0000-4000-8000-000000000007',
  verification_status = 'VERIFIED'
WHERE ccu_id = '60000000-0000-4000-8000-000000000001'
  AND risk_tag_type = 'AP_REGULATORY';

INSERT INTO rules.tax_scenario_model (
  scenario_model_id, scenario_code, country_id, scenario_name_cn,
  import_mode, origin_regime, powertrain, classification_route,
  required_input_fields, calculation_dsl, fallback_scenario_id,
  output_scope, effective_from, version, record_status, verification_status
) VALUES (
  'c0000000-0000-4000-8000-000000000001',
  'SCN-MY-PARTS-BEV-BATTERY-MFN',
  '10000000-0000-4000-8000-000000000001',
  '马来西亚BEV动力电池包普通进口MFN场景',
  'PARTS', 'MFN', 'BEV',
  'CCU-HV-BATTERY-PACK -> HS6 850760 -> MY 8507603300 -> MFN',
  '[
    "import.customs_value",
    "tax.excise_duty",
    "tax.sst_exemption_approved",
    "classification.national_tariff_code",
    "goods.condition",
    "goods.rechargeable",
    "goods.motor_vehicle_use",
    "approval.miti_ap_obtained"
  ]'::jsonb,
  '{
    "dsl_version":"0.1.0",
    "scenario_code":"SCN-MY-PARTS-BEV-BATTERY-MFN",
    "inputs":[
      {"path":"import.customs_value","type":"currency","required":true,"ownership":"ENTERPRISE"},
      {"path":"tax.excise_duty","type":"currency","required":true,"ownership":"PUBLIC"},
      {"path":"tax.sst_exemption_approved","type":"boolean","required":true,"ownership":"ENTERPRISE"}
    ],
    "steps":[
      {
        "step_id":"IMPORT_DUTY",
        "sequence_no":1,
        "tax_code":"IMPORT_DUTY",
        "base":{"ref":"import.customs_value"},
        "rate_source":{"type":"TARIFF_MAPPING","reference":"MAP-MY-PDK2025-8507603300-MFN"},
        "amount":{"op":"MULTIPLY","args":[{"ref":"import.customs_value"},{"ref":"rates.import_duty"}]},
        "rounding":{"scale":2,"mode":"HALF_UP"},
        "on_missing":"BLOCK",
        "display_formula":"customs_value × MFN duty rate"
      },
      {
        "step_id":"SALES_TAX",
        "sequence_no":2,
        "tax_code":"SST",
        "depends_on":["IMPORT_DUTY"],
        "base":{"op":"ADD","args":[{"ref":"import.customs_value"},{"ref":"steps.import_duty.amount"},{"ref":"tax.excise_duty"}]},
        "rate_source":{"type":"COUNTRY_RULE","reference":"RULE-MY-SST-RATE-8507603300-2025"},
        "amount":{"op":"MULTIPLY","args":[{"ref":"steps.sales_tax.base"},{"ref":"rates.sst"}]},
        "rounding":{"scale":2,"mode":"HALF_UP"},
        "on_missing":"BLOCK",
        "display_formula":"(customs_value + import_duty + excise_duty) × SST rate"
      }
    ],
    "outputs":[
      {"code":"GROSS_TAX","expression":{"op":"ADD","args":[{"ref":"steps.import_duty.amount"},{"ref":"steps.sales_tax.amount"}]}},
      {"code":"EFFECTIVE_TAX_RATE","expression":{"op":"DIVIDE","args":[{"ref":"outputs.gross_tax"},{"ref":"import.customs_value"}]}}
    ],
    "completeness_policy":{
      "unknown_rate":"BLOCK",
      "missing_required_input":"BLOCK",
      "failed_eligibility":"FALLBACK"
    }
  }'::jsonb,
  NULL,
  '{"taxes":["IMPORT_DUTY","SST"],"currency":"MYR","excludes":["EXCISE_IF_APPLICABLE","FTA_PREFERENCE","ENTERPRISE_EXEMPTION"]}'::jsonb,
  DATE '2026-01-01', 1, 'ACTIVE', 'VERIFIED'
) ON CONFLICT DO NOTHING;

INSERT INTO rules.scenario_rule_link (
  scenario_rule_link_id, scenario_model_id, rule_card_id, sequence_no, mandatory
) VALUES
  ('d0000000-0000-4000-8000-000000000001',
   'c0000000-0000-4000-8000-000000000001',
   '50000000-0000-4000-8000-000000000002', 1, true),
  ('d0000000-0000-4000-8000-000000000002',
   'c0000000-0000-4000-8000-000000000001',
   '50000000-0000-4000-8000-000000000003', 2, true)
ON CONFLICT DO NOTHING;

INSERT INTO rules.scenario_requirement_link (
  scenario_requirement_link_id, scenario_model_id, requirement_id,
  sequence_no, blocking
) VALUES (
  'e0000000-0000-4000-8000-000000000001',
  'c0000000-0000-4000-8000-000000000001',
  '90000000-0000-4000-8000-000000000002',
  1, true
) ON CONFLICT DO NOTHING;

UPDATE audit.missing_data
SET status = 'RESOLVED', resolved_at = now()
WHERE missing_data_id IN (
  'a0000000-0000-4000-8000-000000000004',
  'a0000000-0000-4000-8000-000000000005',
  'a0000000-0000-4000-8000-000000000006'
)
AND status <> 'RESOLVED';

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description,
  data_owner, data_kind, data_ownership, blocking_scope, priority,
  next_action, official_entry_url, status
) VALUES
  ('a0000000-0000-4000-8000-000000000007', NULL,
   'customs.tariff_mapping[ACFTA].duty_rate',
   'The exact ACFTA preferential rate for Malaysia tariff code 8507603300 and China origin has not yet been line-verified.',
   'FTA_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'ACFTA_PREFERENCE_ONLY', 'P1',
   'Verify the tariff line in the ACFTA Customs Duties Order and capture Form E and product-specific origin-rule conditions.',
   'https://www.customs.gov.my/ms/pg/Akta%20Kastam/PUA454_2024.pdf', 'OPEN'),
  ('a0000000-0000-4000-8000-000000000008', NULL,
   'customs.tariff_mapping[RCEP].duty_rate',
   'The exact RCEP preferential rate for Malaysia tariff code 8507603300 and China origin has not yet been line-verified.',
   'FTA_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'RCEP_PREFERENCE_ONLY', 'P1',
   'Verify the 2026 RCEP tariff line, staging year, proof of origin and product-specific origin rule.',
   'https://www.customs.gov.my/en/procedure/customs/customs', 'OPEN'),
  ('a0000000-0000-4000-8000-000000000009', NULL,
   'evidence.source_document.archived_object_key',
   'MITI AP SOP, Sales Tax Act and Sales Tax Rate Order are referenced by official URLs but still require immutable local archive files and SHA-256 hashes.',
   'EVIDENCE_OWNER', 'PUBLIC_RESEARCH', 'PUBLIC',
   'SOURCE_IMMUTABILITY_NONBLOCKING', 'P1',
   'Download the three official sources, calculate SHA-256 and store immutable object keys.',
   'https://www.miti.gov.my/index.php/pages/view/10897', 'OPEN')
ON CONFLICT DO NOTHING;

COMMIT;
