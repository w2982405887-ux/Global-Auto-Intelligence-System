BEGIN;

-- Phase 1.4 golden path.
-- All enterprise records below are synthetic DEMO records. They must never be
-- interpreted as a real vehicle BOM, customs declaration or FTA qualification.

-- Data-quality promotion: this mapping was already VERIFIED and used by the
-- verified battery scenario, but its publication state remained DRAFT.
UPDATE customs.tariff_mapping
SET record_status = 'ACTIVE',
    updated_at = now()
WHERE mapping_code = 'MAP-MY-PDK2025-8507603300-MFN'
  AND version = 1
  AND verification_status = 'VERIFIED'
  AND record_status = 'DRAFT';

INSERT INTO rules.tax_scenario_model (
  scenario_code, country_id, scenario_name_cn, import_mode, origin_regime,
  powertrain, classification_route, required_input_fields, calculation_dsl,
  fallback_scenario_id, output_scope, effective_from, version, record_status,
  verification_status
)
SELECT
  v.scenario_code,
  '10000000-0000-4000-8000-000000000001'::uuid,
  v.scenario_name_cn,
  'CKD'::ref.import_mode,
  v.origin_regime::ref.origin_regime,
  'BEV'::ref.powertrain,
  'CCU_SEPARATE_CLASSIFICATION_SUBJECT_TO_GRI_2A',
  '["import.customs_value","classification.selected_mapping","tax.excise_assessment","tax.sst_rate","enterprise.ccu_required_inputs","origin.preference_proof","origin.rule_compliance"]'::jsonb,
  jsonb_build_object(
    'dsl_version', '0.1.0',
    'scenario_code', v.scenario_code,
    'inputs', jsonb_build_array(
      jsonb_build_object('path','import.customs_value','type','currency','required',true,'ownership','ENTERPRISE'),
      jsonb_build_object('path','classification.selected_mapping','type','object','required',true,'ownership','MIXED'),
      jsonb_build_object('path','tax.excise_assessment','type','currency','required',true,'ownership','PUBLIC'),
      jsonb_build_object('path','tax.sst_rate','type','decimal','required',true,'ownership','PUBLIC'),
      jsonb_build_object('path','origin.preference_proof','type','boolean','required',v.preference_required,'ownership','ENTERPRISE'),
      jsonb_build_object('path','origin.rule_compliance','type','boolean','required',v.preference_required,'ownership','ENTERPRISE')
    ),
    'steps', jsonb_build_array(
      jsonb_build_object(
        'step_id','IMPORT_DUTY','sequence_no',1,'tax_code','IMPORT_DUTY',
        'base',jsonb_build_object('ref','import.customs_value'),
        'rate_source',jsonb_build_object('type','TARIFF_MAPPING','reference','SELECTED_PER_CCU'),
        'amount',jsonb_build_object('op','MULTIPLY','args',jsonb_build_array(
          jsonb_build_object('ref','import.customs_value'),
          jsonb_build_object('ref','rates.import_duty')
        )),
        'rounding',jsonb_build_object('mode','HALF_UP','scale',2),
        'on_missing','BLOCK',
        'display_formula','customs_value * selected duty rate'
      ),
      jsonb_build_object(
        'step_id','EXCISE_ASSESSMENT','sequence_no',2,'tax_code','EXCISE',
        'base',jsonb_build_object('ref','import.customs_value'),
        'rate_source',jsonb_build_object('type','INPUT','reference','tax.excise_assessment'),
        'amount',jsonb_build_object('ref','tax.excise_assessment'),
        'rounding',jsonb_build_object('mode','HALF_UP','scale',2),
        'on_missing','PARTIAL',
        'display_formula','explicit excise assessment; zero is not an exemption conclusion'
      ),
      jsonb_build_object(
        'step_id','SALES_TAX','sequence_no',3,'tax_code','SST',
        'depends_on',jsonb_build_array('IMPORT_DUTY','EXCISE_ASSESSMENT'),
        'base',jsonb_build_object('op','ADD','args',jsonb_build_array(
          jsonb_build_object('ref','import.customs_value'),
          jsonb_build_object('ref','steps.import_duty.amount'),
          jsonb_build_object('ref','steps.excise_assessment.amount')
        )),
        'rate_source',jsonb_build_object('type','INPUT','reference','tax.sst_rate'),
        'amount',jsonb_build_object('op','MULTIPLY','args',jsonb_build_array(
          jsonb_build_object('ref','steps.sales_tax.base'),
          jsonb_build_object('ref','rates.sst')
        )),
        'rounding',jsonb_build_object('mode','HALF_UP','scale',2),
        'on_missing','BLOCK',
        'display_formula','(customs_value + import_duty + excise) * SST rate'
      )
    ),
    'outputs', jsonb_build_array(
      jsonb_build_object('code','GROSS_TAX','expression',jsonb_build_object(
        'op','ADD','args',jsonb_build_array(
          jsonb_build_object('ref','steps.import_duty.amount'),
          jsonb_build_object('ref','steps.excise_assessment.amount'),
          jsonb_build_object('ref','steps.sales_tax.amount')
        )
      )),
      jsonb_build_object('code','EFFECTIVE_TAX_RATE','expression',jsonb_build_object(
        'op','DIVIDE','args',jsonb_build_array(
          jsonb_build_object('ref','outputs.gross_tax'),
          jsonb_build_object('ref','import.customs_value')
        )
      ))
    ),
    'completeness_policy', jsonb_build_object(
      'missing_required_input','PARTIAL',
      'failed_eligibility','FALLBACK',
      'unknown_rate','BLOCK'
    )
  ),
  NULL,
  jsonb_build_object(
    'currency','MYR',
    'taxes',jsonb_build_array('IMPORT_DUTY','EXCISE_ASSESSMENT','SST'),
    'comparison_regime',v.regime_code,
    'limitations',jsonb_build_array(
      'DEMO_VALUES_ONLY',
      'CCU_CLASSIFICATION_NOT_FINAL_WHERE_CANDIDATE',
      'GRI_2A_REQUIRES_SHIPMENT_LEVEL_REVIEW',
      'EXCISE_ZERO_IS_NOT_A_LEGAL_EXEMPTION_CONCLUSION'
    )
  ),
  DATE '2026-01-01', 1, 'ACTIVE', 'CANDIDATE'
FROM (
  VALUES
    ('SCN-MY-CKD-BEV-MFN-GOLDEN','马来西亚BEV CKD零部件MFN黄金路径','MFN','MFN',false),
    ('SCN-MY-CKD-BEV-ACFTA-GOLDEN','马来西亚BEV CKD零部件ACFTA黄金路径','FTA','ACFTA',true),
    ('SCN-MY-CKD-BEV-RCEP-GOLDEN','马来西亚BEV CKD零部件RCEP黄金路径','FTA','RCEP',true)
) AS v(scenario_code, scenario_name_cn, origin_regime, regime_code, preference_required)
ON CONFLICT (scenario_code, version) DO UPDATE SET
  scenario_name_cn = EXCLUDED.scenario_name_cn,
  required_input_fields = EXCLUDED.required_input_fields,
  calculation_dsl = EXCLUDED.calculation_dsl,
  output_scope = EXCLUDED.output_scope,
  updated_at = now();

UPDATE rules.tax_scenario_model preferred
SET fallback_scenario_id = fallback.scenario_model_id,
    updated_at = now()
FROM rules.tax_scenario_model fallback
WHERE fallback.scenario_code = 'SCN-MY-CKD-BEV-MFN-GOLDEN'
  AND fallback.version = 1
  AND preferred.scenario_code IN (
    'SCN-MY-CKD-BEV-ACFTA-GOLDEN',
    'SCN-MY-CKD-BEV-RCEP-GOLDEN'
  )
  AND preferred.version = 1;

INSERT INTO rules.scenario_rule_link (
  scenario_model_id, rule_card_id, sequence_no, mandatory
)
SELECT scenario.scenario_model_id, rule.rule_card_id, v.sequence_no, true
FROM (
  VALUES
    ('SCN-MY-CKD-BEV-MFN-GOLDEN','RULE-MY-SST-IMPORT-BASE-2018',1),
    ('SCN-MY-CKD-BEV-ACFTA-GOLDEN','RULE-MY-SST-IMPORT-BASE-2018',1),
    ('SCN-MY-CKD-BEV-ACFTA-GOLDEN','RULE-MY-ACFTA-ORIGIN-FIRST9',2),
    ('SCN-MY-CKD-BEV-RCEP-GOLDEN','RULE-MY-SST-IMPORT-BASE-2018',1),
    ('SCN-MY-CKD-BEV-RCEP-GOLDEN','RULE-MY-RCEP-ORIGIN-FIRST9',2)
) AS v(scenario_code, rule_code, sequence_no)
JOIN rules.tax_scenario_model scenario
  ON scenario.scenario_code = v.scenario_code AND scenario.version = 1
JOIN rules.country_rule_card rule
  ON rule.rule_code = v.rule_code AND rule.version = 1
ON CONFLICT (scenario_model_id, rule_card_id) DO UPDATE SET
  sequence_no = EXCLUDED.sequence_no,
  mandatory = EXCLUDED.mandatory;

INSERT INTO enterprise.vehicle_model (
  model_code, vehicle_type, powertrain, technical_attributes,
  effective_from, version, record_status
) VALUES (
  'DEMO-MY-BEV-001', 'PASSENGER_BEV', 'BEV',
  '{"demo_only":true,"disclaimer":"Synthetic Phase 1.4 validation vehicle; not a real enterprise model."}'::jsonb,
  DATE '2026-01-01', 1, 'ACTIVE'
)
ON CONFLICT (model_code, version) DO UPDATE SET
  technical_attributes = EXCLUDED.technical_attributes;

WITH demo_parts(part_no, part_name_cn, ccu_code) AS (
  VALUES
    ('DEMO-P001','锂离子动力电池包','CCU-HV-BATTERY-PACK'),
    ('DEMO-P002','驱动电机（演示额定功率超过75kW）','CCU-TRACTION-MOTOR'),
    ('DEMO-P003','牵引逆变器','CCU-TRACTION-INVERTER'),
    ('DEMO-P004','车载充电机（候选税号演示）','CCU-ONBOARD-CHARGER'),
    ('DEMO-P005','DC-DC转换器（候选税号演示）','CCU-DC-DC-CONVERTER'),
    ('DEMO-P006','乘用车白车身','CCU-PASSENGER-BODY-SHELL'),
    ('DEMO-P007','未装轮胎的车轮','CCU-ROAD-WHEEL'),
    ('DEMO-P008','制动器及其零件','CCU-FOUNDATION-BRAKE'),
    ('DEMO-P009','转向器/转向柱','CCU-STEERING-GEAR-COLUMN'),
    ('DEMO-P010','减振器/支柱','CCU-SHOCK-ABSORBER-STRUT')
)
INSERT INTO enterprise.enterprise_part (
  enterprise_code, part_no, part_name_cn, part_name_en, attributes,
  effective_from, version, record_status
)
SELECT
  'DEMO-GOLDEN-PATH', part_no, part_name_cn, ccu_code,
  jsonb_build_object(
    'demo_only', true,
    'ccu_code', ccu_code,
    'enterprise_technical_parameters_complete', false,
    'use_time_fields_remain_empty', true
  ),
  DATE '2026-01-01', 1, 'ACTIVE'
FROM demo_parts
ON CONFLICT (enterprise_code, part_no, version) DO UPDATE SET
  part_name_cn = EXCLUDED.part_name_cn,
  attributes = EXCLUDED.attributes;

INSERT INTO enterprise.enterprise_part_ccu_link (
  enterprise_part_id, ccu_id, mapping_basis, confidence,
  effective_from, verification_status
)
SELECT
  part.enterprise_part_id,
  ccu.ccu_id,
  'DEMO_GOLDEN_PATH_CCU_LINK; enterprise technical fields intentionally deferred until use',
  CASE WHEN ccu.ccu_code IN (
    'CCU-HV-BATTERY-PACK','CCU-TRACTION-MOTOR','CCU-TRACTION-INVERTER',
    'CCU-ROAD-WHEEL','CCU-STEERING-GEAR-COLUMN','CCU-SHOCK-ABSORBER-STRUT'
  ) THEN 0.9000 ELSE 0.6000 END,
  DATE '2026-01-01',
  CASE WHEN ccu.ccu_code IN (
    'CCU-HV-BATTERY-PACK','CCU-TRACTION-MOTOR','CCU-TRACTION-INVERTER',
    'CCU-ROAD-WHEEL','CCU-STEERING-GEAR-COLUMN','CCU-SHOCK-ABSORBER-STRUT'
  ) THEN 'VERIFIED'::ref.verification_status ELSE 'CANDIDATE'::ref.verification_status END
FROM enterprise.enterprise_part part
JOIN customs.customs_classification_unit ccu
  ON ccu.ccu_code = part.attributes->>'ccu_code' AND ccu.version = 1
WHERE part.enterprise_code = 'DEMO-GOLDEN-PATH'
ON CONFLICT (enterprise_part_id, ccu_id, effective_from) DO UPDATE SET
  mapping_basis = EXCLUDED.mapping_basis,
  confidence = EXCLUDED.confidence,
  verification_status = EXCLUDED.verification_status;

INSERT INTO enterprise.bom_version (
  vehicle_id, bom_code, version, effective_from, record_status
)
SELECT vehicle_id, 'DEMO-MY-BEV-001-BOM', 1, DATE '2026-01-01', 'ACTIVE'
FROM enterprise.vehicle_model
WHERE model_code = 'DEMO-MY-BEV-001' AND version = 1
ON CONFLICT (bom_code, version) DO UPDATE SET
  record_status = EXCLUDED.record_status;

WITH demo_values(part_no, customs_value_myr) AS (
  VALUES
    ('DEMO-P001',40000.00::numeric),
    ('DEMO-P002',15000.00::numeric),
    ('DEMO-P003', 8000.00::numeric),
    ('DEMO-P004', 5000.00::numeric),
    ('DEMO-P005', 3000.00::numeric),
    ('DEMO-P006',12000.00::numeric),
    ('DEMO-P007', 5000.00::numeric),
    ('DEMO-P008', 4000.00::numeric),
    ('DEMO-P009', 4000.00::numeric),
    ('DEMO-P010', 4000.00::numeric)
)
INSERT INTO enterprise.bom_line (
  bom_version_id, enterprise_part_id, quantity_per_vehicle, unit_value,
  currency_code, origin_country_id, shipment_group, included_flag
)
SELECT
  bom.bom_version_id, part.enterprise_part_id, 1, value.customs_value_myr,
  'MYR', china.country_id, 'DEMO-CKD-SHIPMENT-001', true
FROM demo_values value
JOIN enterprise.enterprise_part part
  ON part.part_no = value.part_no
 AND part.enterprise_code = 'DEMO-GOLDEN-PATH'
 AND part.version = 1
JOIN enterprise.bom_version bom
  ON bom.bom_code = 'DEMO-MY-BEV-001-BOM' AND bom.version = 1
JOIN ref.country china ON china.iso2 = 'CN'
ON CONFLICT (bom_version_id, enterprise_part_id, shipment_group) DO UPDATE SET
  quantity_per_vehicle = EXCLUDED.quantity_per_vehicle,
  unit_value = EXCLUDED.unit_value,
  currency_code = EXCLUDED.currency_code,
  origin_country_id = EXCLUDED.origin_country_id,
  included_flag = EXCLUDED.included_flag;

WITH demo_cases(
  input_code, requested_regime, proof_valid, rule_confirmed,
  nomenclature_confirmed, simulation_eligibility
) AS (
  VALUES
    ('DEMO-MY-BEV-001-MFN','MFN',false,false,false,false),
    ('DEMO-MY-BEV-001-ACFTA-BLOCKED','ACFTA',false,false,false,false),
    ('DEMO-MY-BEV-001-RCEP-BLOCKED','RCEP',false,false,false,false),
    ('DEMO-MY-BEV-001-ACFTA-ELIGIBLE-SIM','ACFTA',true,true,true,true),
    ('DEMO-MY-BEV-001-RCEP-ELIGIBLE-SIM','RCEP',true,true,true,true)
)
INSERT INTO enterprise.scenario_input (
  scenario_code, country_id, vehicle_id, bom_version_id, import_date,
  import_mode, origin_country_id, input_payload, record_status
)
SELECT
  demo.input_code,
  malaysia.country_id,
  vehicle.vehicle_id,
  bom.bom_version_id,
  DATE '2026-07-28',
  'CKD',
  china.country_id,
  jsonb_build_object(
    'demo_only', true,
    'requested_origin_regime', demo.requested_regime,
    'origin_country_iso2', 'CN',
    'preference_proof_valid', demo.proof_valid,
    'origin_rule_compliance_confirmed', demo.rule_confirmed,
    'nomenclature_correlation_confirmed', demo.nomenclature_confirmed,
    'simulation_eligibility', demo.simulation_eligibility,
    'customs_value_total_myr', 100000.00,
    'valuation_assumption', 'Freight and insurance included in customs value',
    'excise_assessment_myr', 0.00,
    'excise_disclaimer', 'Zero is a demo calculation input, not a legal exemption conclusion.',
    'enterprise_ccu_fields_complete', false,
    'gri_2a_review_complete', false,
    'operational_use_permitted', false
  ),
  'ACTIVE'
FROM demo_cases demo
JOIN ref.country malaysia ON malaysia.iso2 = 'MY'
JOIN ref.country china ON china.iso2 = 'CN'
JOIN enterprise.vehicle_model vehicle
  ON vehicle.model_code = 'DEMO-MY-BEV-001' AND vehicle.version = 1
JOIN enterprise.bom_version bom
  ON bom.bom_code = 'DEMO-MY-BEV-001-BOM' AND bom.version = 1
ON CONFLICT (scenario_code) DO UPDATE SET
  input_payload = EXCLUDED.input_payload,
  updated_at = now();

INSERT INTO enterprise.input_snapshot (
  scenario_input_id, payload, payload_sha256
)
SELECT
  input.scenario_input_id,
  input.input_payload,
  encode(digest(input.input_payload::text, 'sha256'), 'hex')
FROM enterprise.scenario_input input
WHERE input.scenario_code LIKE 'DEMO-MY-BEV-001-%'
ON CONFLICT (payload_sha256) DO NOTHING;

COMMIT;
