\set ON_ERROR_STOP on
BEGIN;

CREATE TEMP TABLE gp_case (
  input_code text PRIMARY KEY,
  run_code text NOT NULL,
  requested_regime text NOT NULL,
  applied_regime text NOT NULL,
  scenario_code text NOT NULL,
  fallback_applied boolean NOT NULL,
  preference_eligible boolean NOT NULL
) ON COMMIT DROP;

INSERT INTO gp_case VALUES
  ('DEMO-MY-BEV-001-MFN','RUN-MY-GP-MFN','MFN','MFN','SCN-MY-CKD-BEV-MFN-GOLDEN',false,true),
  ('DEMO-MY-BEV-001-ACFTA-BLOCKED','RUN-MY-GP-ACFTA-BLOCKED-FALLBACK-MFN','ACFTA','MFN','SCN-MY-CKD-BEV-MFN-GOLDEN',true,false),
  ('DEMO-MY-BEV-001-RCEP-BLOCKED','RUN-MY-GP-RCEP-BLOCKED-FALLBACK-MFN','RCEP','MFN','SCN-MY-CKD-BEV-MFN-GOLDEN',true,false),
  ('DEMO-MY-BEV-001-ACFTA-ELIGIBLE-SIM','RUN-MY-GP-ACFTA-ELIGIBLE-SIM','ACFTA','ACFTA','SCN-MY-CKD-BEV-ACFTA-GOLDEN',false,true),
  ('DEMO-MY-BEV-001-RCEP-ELIGIBLE-SIM','RUN-MY-GP-RCEP-ELIGIBLE-SIM','RCEP','RCEP','SCN-MY-CKD-BEV-RCEP-GOLDEN',false,true);

CREATE TEMP TABLE gp_mapping_choice (
  ccu_code text NOT NULL,
  regime text NOT NULL,
  mapping_code text NOT NULL,
  PRIMARY KEY (ccu_code, regime)
) ON COMMIT DROP;

INSERT INTO gp_mapping_choice VALUES
  ('CCU-HV-BATTERY-PACK','MFN','MAP-MY-PDK2025-8507603300-MFN'),
  ('CCU-TRACTION-MOTOR','MFN','MAP-MY-MFN-CCU-TRACTION-MOTOR-8501531000-R1'),
  ('CCU-TRACTION-INVERTER','MFN','MAP-MY-MFN-CCU-TRACTION-INVERTER-8504404000-R1'),
  ('CCU-ONBOARD-CHARGER','MFN','MAP-MY-MFN-CCU-ONBOARD-CHARGER-8504409000-R1'),
  ('CCU-DC-DC-CONVERTER','MFN','MAP-MY-MFN-CCU-DC-DC-CONVERTER-8504409000-R1'),
  ('CCU-PASSENGER-BODY-SHELL','MFN','MAP-MY-MFN-CCU-PASSENGER-BODY-SHELL-8707109000-R1'),
  ('CCU-ROAD-WHEEL','MFN','MAP-MY-MFN-CCU-ROAD-WHEEL-8708703200-R1'),
  ('CCU-FOUNDATION-BRAKE','MFN','MAP-MY-MFN-CCU-FOUNDATION-BRAKE-8708302900-R1'),
  ('CCU-STEERING-GEAR-COLUMN','MFN','MAP-MY-MFN-CCU-STEERING-GEAR-COLUMN-8708949500-R1'),
  ('CCU-SHOCK-ABSORBER-STRUT','MFN','MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708809200-R1'),
  ('CCU-HV-BATTERY-PACK','ACFTA','MAP-MY-ACFTA-2026-8507603300-CN'),
  ('CCU-TRACTION-MOTOR','ACFTA','MAP-MY-ACFTA-2026-CCU-TRACTION-MOTOR-8501531000'),
  ('CCU-TRACTION-INVERTER','ACFTA','MAP-MY-ACFTA-2026-CCU-TRACTION-INVERTER-8504404000'),
  ('CCU-ONBOARD-CHARGER','ACFTA','MAP-MY-ACFTA-2026-CCU-ONBOARD-CHARGER-8504409000'),
  ('CCU-DC-DC-CONVERTER','ACFTA','MAP-MY-ACFTA-2026-CCU-DC-DC-CONVERTER-8504409000'),
  ('CCU-PASSENGER-BODY-SHELL','ACFTA','MAP-MY-ACFTA-2026-CCU-PASSENGER-BODY-SHELL-8707109000'),
  ('CCU-ROAD-WHEEL','ACFTA','MAP-MY-ACFTA-2026-CCU-ROAD-WHEEL-8708703200'),
  ('CCU-FOUNDATION-BRAKE','ACFTA','MAP-MY-ACFTA-2026-CCU-FOUNDATION-BRAKE-8708302900'),
  ('CCU-STEERING-GEAR-COLUMN','ACFTA','MAP-MY-ACFTA-2026-CCU-STEERING-GEAR-COLUMN-8708949500'),
  ('CCU-SHOCK-ABSORBER-STRUT','ACFTA','MAP-MY-ACFTA-2026-CCU-SHOCK-ABSORBER-STRUT-8708809200'),
  ('CCU-HV-BATTERY-PACK','RCEP','MAP-MY-RCEP-2026-8507609000-CN'),
  ('CCU-TRACTION-MOTOR','RCEP','MAP-MY-RCEP-2026-CCU-TRACTION-MOTOR-8501530000'),
  ('CCU-TRACTION-INVERTER','RCEP','MAP-MY-RCEP-2026-CCU-TRACTION-INVERTER-8504404000'),
  ('CCU-ONBOARD-CHARGER','RCEP','MAP-MY-RCEP-2026-CCU-ONBOARD-CHARGER-8504409000'),
  ('CCU-DC-DC-CONVERTER','RCEP','MAP-MY-RCEP-2026-CCU-DC-DC-CONVERTER-8504409000'),
  ('CCU-PASSENGER-BODY-SHELL','RCEP','MAP-MY-RCEP-2026-CCU-PASSENGER-BODY-SHELL-8707109000'),
  ('CCU-ROAD-WHEEL','RCEP','MAP-MY-RCEP-2026-CCU-ROAD-WHEEL-8708703200'),
  ('CCU-FOUNDATION-BRAKE','RCEP','MAP-MY-RCEP-2026-CCU-FOUNDATION-BRAKE-8708302900'),
  ('CCU-STEERING-GEAR-COLUMN','RCEP','MAP-MY-RCEP-2026-CCU-STEERING-GEAR-COLUMN-8708949500'),
  ('CCU-SHOCK-ABSORBER-STRUT','RCEP','MAP-MY-RCEP-2026-CCU-SHOCK-ABSORBER-STRUT-8708809200');

CREATE TEMP TABLE gp_item AS
SELECT
  cases.run_code,
  cases.requested_regime,
  cases.applied_regime,
  cases.fallback_applied,
  cases.preference_eligible,
  part.part_no,
  ccu.ccu_id,
  ccu.ccu_code,
  ccu.ccu_name_cn,
  (line.quantity_per_vehicle * line.unit_value)::numeric(20,6) AS customs_value,
  mapping.mapping_id,
  mapping.mapping_code,
  mapping.national_tariff_code,
  mapping.duty_rate,
  mapping.verification_status,
  mapping.source_clause_id,
  0.10::numeric(12,8) AS sst_rate
FROM gp_case cases
JOIN enterprise.scenario_input input
  ON input.scenario_code = cases.input_code
JOIN enterprise.bom_line line
  ON line.bom_version_id = input.bom_version_id AND line.included_flag
JOIN enterprise.enterprise_part part
  ON part.enterprise_part_id = line.enterprise_part_id
JOIN enterprise.enterprise_part_ccu_link part_ccu
  ON part_ccu.enterprise_part_id = part.enterprise_part_id
 AND part_ccu.effective_from <= input.import_date
 AND (part_ccu.effective_to IS NULL OR part_ccu.effective_to > input.import_date)
JOIN customs.customs_classification_unit ccu
  ON ccu.ccu_id = part_ccu.ccu_id
JOIN gp_mapping_choice choice
  ON choice.ccu_code = ccu.ccu_code
 AND choice.regime = cases.applied_regime
JOIN customs.tariff_mapping mapping
  ON mapping.mapping_code = choice.mapping_code AND mapping.version = 1;

DO $$
BEGIN
  IF (SELECT count(*) FROM gp_item) <> 50 THEN
    RAISE EXCEPTION 'Golden path expected 50 selected item mappings (5 runs x 10 CCUs), got %',
      (SELECT count(*) FROM gp_item);
  END IF;
  IF EXISTS (SELECT 1 FROM gp_item WHERE duty_rate IS NULL) THEN
    RAISE EXCEPTION 'Golden path contains a null duty rate';
  END IF;
  IF EXISTS (
    SELECT 1 FROM gp_item
    GROUP BY run_code
    HAVING sum(customs_value) <> 100000.00
  ) THEN
    RAISE EXCEPTION 'Golden path customs value must total MYR 100,000 per run';
  END IF;
END $$;

INSERT INTO calc.calculation_run (
  run_code, scenario_model_id, input_snapshot_id, rule_snapshot_at,
  engine_version, run_status, completeness, currency_code, base_value,
  gross_tax, recoverable_tax, net_tax, effective_tax_rate,
  started_at, completed_at, error_summary
)
SELECT
  cases.run_code,
  scenario.scenario_model_id,
  snapshot.input_snapshot_id,
  now(),
  'sql-golden-path-0.1.0',
  'COMPLETE',
  'PARTIAL',
  'MYR',
  100000.00,
  NULL, 0, NULL, NULL,
  now(), now(),
  CASE
    WHEN cases.fallback_applied
      THEN 'Requested preference blocked by missing enterprise origin evidence; MFN fallback calculated.'
    ELSE 'Calculation complete; overall completeness remains PARTIAL because enterprise CCU parameters and shipment-level GRI 2(a) review are deferred.'
  END
FROM gp_case cases
JOIN enterprise.scenario_input input
  ON input.scenario_code = cases.input_code
JOIN enterprise.input_snapshot snapshot
  ON snapshot.scenario_input_id = input.scenario_input_id
 AND snapshot.payload_sha256 = encode(digest(input.input_payload::text, 'sha256'), 'hex')
JOIN rules.tax_scenario_model scenario
  ON scenario.scenario_code = cases.scenario_code AND scenario.version = 1
ON CONFLICT (run_code) DO UPDATE SET
  scenario_model_id = EXCLUDED.scenario_model_id,
  input_snapshot_id = EXCLUDED.input_snapshot_id,
  rule_snapshot_at = EXCLUDED.rule_snapshot_at,
  engine_version = EXCLUDED.engine_version,
  run_status = EXCLUDED.run_status,
  completeness = EXCLUDED.completeness,
  currency_code = EXCLUDED.currency_code,
  base_value = EXCLUDED.base_value,
  started_at = EXCLUDED.started_at,
  completed_at = EXCLUDED.completed_at,
  error_summary = EXCLUDED.error_summary;

CREATE TEMP TABLE gp_calc_line AS
WITH expanded AS (
  SELECT item.*, tax.tax_order, tax.tax_code
  FROM gp_item item
  CROSS JOIN (VALUES
    (1,'IMPORT_DUTY'),
    (2,'EXCISE_ASSESSMENT'),
    (3,'SST')
  ) AS tax(tax_order, tax_code)
),
numbered AS (
  SELECT
    expanded.*,
    row_number() OVER (PARTITION BY run_code ORDER BY ccu_code, tax_order) AS sequence_no,
    round(customs_value * duty_rate, 2) AS import_duty_amount
  FROM expanded
)
SELECT
  numbered.*,
  CASE tax_code
    WHEN 'IMPORT_DUTY' THEN customs_value
    WHEN 'EXCISE_ASSESSMENT' THEN customs_value
    WHEN 'SST' THEN customs_value + import_duty_amount
  END AS tax_base,
  CASE tax_code
    WHEN 'IMPORT_DUTY' THEN duty_rate
    WHEN 'EXCISE_ASSESSMENT' THEN NULL
    WHEN 'SST' THEN sst_rate
  END AS tax_rate,
  CASE tax_code
    WHEN 'IMPORT_DUTY' THEN import_duty_amount
    WHEN 'EXCISE_ASSESSMENT' THEN 0.00
    WHEN 'SST' THEN round((customs_value + import_duty_amount) * sst_rate, 2)
  END AS tax_amount
FROM numbered;

INSERT INTO calc.calculation_line (
  calculation_run_id, sequence_no, tax_code, base_expression, base_amount,
  rate_type, rate, tax_expression, gross_tax_amount, recoverable_fraction,
  net_tax_amount, rule_card_id, tariff_mapping_id, line_status, notes
)
SELECT
  run.calculation_run_id,
  line.sequence_no,
  line.tax_code || ':' || line.ccu_code,
  CASE line.tax_code
    WHEN 'IMPORT_DUTY' THEN jsonb_build_object('ref','item.customs_value','ccu_code',line.ccu_code)
    WHEN 'EXCISE_ASSESSMENT' THEN jsonb_build_object('ref','item.customs_value','ccu_code',line.ccu_code)
    WHEN 'SST' THEN jsonb_build_object(
      'op','ADD','args',jsonb_build_array('item.customs_value','item.import_duty','item.excise_assessment'),
      'ccu_code',line.ccu_code
    )
  END,
  line.tax_base,
  CASE
    WHEN line.tax_code = 'EXCISE_ASSESSMENT' THEN 'NOT_APPLICABLE'::ref.rate_type
    WHEN line.tax_rate = 0 THEN 'ZERO'::ref.rate_type
    ELSE 'AD_VALOREM'::ref.rate_type
  END,
  line.tax_rate,
  CASE line.tax_code
    WHEN 'IMPORT_DUTY' THEN jsonb_build_object('op','MULTIPLY','base','item.customs_value','rate_source',line.mapping_code)
    WHEN 'EXCISE_ASSESSMENT' THEN jsonb_build_object('op','EXPLICIT_ZERO_DEMO_INPUT','legal_exemption_conclusion',false)
    WHEN 'SST' THEN jsonb_build_object('op','MULTIPLY','base','customs_value_plus_duty_plus_excise','rate',line.sst_rate)
  END,
  line.tax_amount,
  0,
  line.tax_amount,
  CASE WHEN line.tax_code = 'SST'
    THEN (SELECT rule_card_id FROM rules.country_rule_card
          WHERE rule_code = 'RULE-MY-SST-IMPORT-BASE-2018' AND version = 1)
    ELSE NULL
  END,
  CASE WHEN line.tax_code IN ('IMPORT_DUTY','SST') THEN line.mapping_id ELSE NULL END,
  'COMPLETE',
  concat(
    'DEMO; ccu=', line.ccu_code,
    '; tariff=', line.national_tariff_code,
    '; requested=', line.requested_regime,
    '; applied=', line.applied_regime,
    '; mapping_status=', line.verification_status,
    CASE WHEN line.tax_code = 'EXCISE_ASSESSMENT'
      THEN '; zero is an explicit demo input, not a legal exemption conclusion'
      ELSE ''
    END
  )
FROM gp_calc_line line
JOIN calc.calculation_run run ON run.run_code = line.run_code
ON CONFLICT (calculation_run_id, sequence_no) DO UPDATE SET
  tax_code = EXCLUDED.tax_code,
  base_expression = EXCLUDED.base_expression,
  base_amount = EXCLUDED.base_amount,
  rate_type = EXCLUDED.rate_type,
  rate = EXCLUDED.rate,
  tax_expression = EXCLUDED.tax_expression,
  gross_tax_amount = EXCLUDED.gross_tax_amount,
  recoverable_fraction = EXCLUDED.recoverable_fraction,
  net_tax_amount = EXCLUDED.net_tax_amount,
  rule_card_id = EXCLUDED.rule_card_id,
  tariff_mapping_id = EXCLUDED.tariff_mapping_id,
  line_status = EXCLUDED.line_status,
  notes = EXCLUDED.notes;

UPDATE calc.calculation_run run
SET gross_tax = totals.gross_tax,
    net_tax = totals.gross_tax,
    recoverable_tax = 0,
    effective_tax_rate = totals.gross_tax / run.base_value
FROM (
  SELECT calculation_run_id, sum(gross_tax_amount) AS gross_tax
  FROM calc.calculation_line
  WHERE calculation_run_id IN (
    SELECT calculation_run_id FROM calc.calculation_run
    WHERE run_code LIKE 'RUN-MY-GP-%'
  )
  GROUP BY calculation_run_id
) totals
WHERE run.calculation_run_id = totals.calculation_run_id;

INSERT INTO audit.decision_trace (
  calculation_run_id, sequence_no, step_type, decision_question,
  input_record_refs, rule_record_refs, source_clause_refs,
  explicit_rationale, result, confidence, human_review_required
)
SELECT
  run.calculation_run_id,
  trace.sequence_no,
  trace.step_type::ref.decision_step_type,
  trace.decision_question,
  jsonb_build_array(jsonb_build_object(
    'scenario_input_id', input.scenario_input_id,
    'input_snapshot_id', run.input_snapshot_id,
    'demo_only', true
  )),
  CASE
    WHEN trace.sequence_no = 5 THEN COALESCE((
      SELECT jsonb_agg(DISTINCT jsonb_build_object('rule_card_id', line.rule_card_id))
      FROM calc.calculation_line line
      WHERE line.calculation_run_id = run.calculation_run_id
        AND line.rule_card_id IS NOT NULL
    ), '[]'::jsonb)
    ELSE '[]'::jsonb
  END,
  CASE
    WHEN trace.sequence_no IN (3,5) THEN COALESCE((
      SELECT jsonb_agg(DISTINCT jsonb_build_object('source_clause_id', mapping.source_clause_id))
      FROM calc.calculation_line line
      JOIN customs.tariff_mapping mapping
        ON mapping.mapping_id = line.tariff_mapping_id
      WHERE line.calculation_run_id = run.calculation_run_id
    ), '[]'::jsonb)
    ELSE '[]'::jsonb
  END,
  CASE trace.sequence_no
    WHEN 1 THEN 'The snapshot is a labelled synthetic input. Customs value totals MYR 100,000; enterprise CCU technical fields remain intentionally incomplete.'
    WHEN 2 THEN CASE WHEN cases.fallback_applied
      THEN 'The requested preference failed its enterprise evidence gate, so the configured MFN fallback scenario was selected.'
      ELSE 'The requested regime passed the demo gate and its corresponding scenario was selected.'
    END
    WHEN 3 THEN 'One selected tariff mapping is retained per CCU. Candidate mappings remain candidate and force PARTIAL completeness.'
    WHEN 4 THEN CASE WHEN cases.preference_eligible
      THEN 'The demo preference gate is satisfied. This validates engine behaviour only and is not proof of real shipment eligibility.'
      ELSE 'Origin proof and rule-compliance confirmations are missing, so preferential duty is prohibited for this run.'
    END
    WHEN 5 THEN 'Duty comes from the selected tariff mapping. SST base follows customs value plus import duty plus explicit excise assessment.'
    WHEN 6 THEN 'The deterministic SQL executor calculated duty, explicit excise assessment and SST for each of ten CCUs.'
    WHEN 7 THEN 'GRI 2(a), candidate classifications, import controls and deferred enterprise inputs require human review before operational use.'
  END,
  CASE trace.sequence_no
    WHEN 1 THEN jsonb_build_object('input_valid',true,'demo_only',true,'base_value_myr',100000)
    WHEN 2 THEN jsonb_build_object(
      'requested_regime',cases.requested_regime,
      'applied_regime',cases.applied_regime,
      'fallback_applied',cases.fallback_applied
    )
    WHEN 3 THEN jsonb_build_object(
      'ccu_count',10,
      'candidate_mapping_count',(
        SELECT count(*) FROM gp_item item
        WHERE item.run_code = cases.run_code
          AND item.verification_status <> 'VERIFIED'
      )
    )
    WHEN 4 THEN jsonb_build_object(
      'preference_eligible',cases.preference_eligible,
      'real_enterprise_eligibility_established',false
    )
    WHEN 5 THEN jsonb_build_object(
      'duty_mapping_source','customs.tariff_mapping',
      'sst_base_rule','RULE-MY-SST-IMPORT-BASE-2018',
      'sst_rate',0.10,
      'excise_legal_conclusion',false
    )
    WHEN 6 THEN jsonb_build_object(
      'gross_tax_myr',run.gross_tax,
      'effective_tax_rate',run.effective_tax_rate,
      'line_count',30
    )
    WHEN 7 THEN jsonb_build_object(
      'completeness',run.completeness,
      'human_review_required',true,
      'operational_use_permitted',false
    )
  END,
  CASE WHEN trace.sequence_no IN (6) THEN 0.9500 ELSE 0.8000 END,
  trace.sequence_no IN (3,4,7)
FROM gp_case cases
JOIN enterprise.scenario_input input ON input.scenario_code = cases.input_code
JOIN calc.calculation_run run ON run.run_code = cases.run_code
CROSS JOIN (
  VALUES
    (1,'INPUT_VALIDATION','Is the calculation input internally complete enough to run?'),
    (2,'SCENARIO_SELECTION','Which tariff regime may the engine apply?'),
    (3,'CLASSIFICATION','Which national tariff mapping is selected for each CCU?'),
    (4,'ELIGIBILITY','May the requested preferential rate be granted?'),
    (5,'RULE_SELECTION','Which executable tax rules and sources are used?'),
    (6,'CALCULATION','What tax amounts result from the selected mappings?'),
    (7,'RISK_ASSESSMENT','What prevents this demo result from operational use?')
) AS trace(sequence_no, step_type, decision_question)
ON CONFLICT (calculation_run_id, sequence_no) DO UPDATE SET
  step_type = EXCLUDED.step_type,
  decision_question = EXCLUDED.decision_question,
  input_record_refs = EXCLUDED.input_record_refs,
  rule_record_refs = EXCLUDED.rule_record_refs,
  source_clause_refs = EXCLUDED.source_clause_refs,
  explicit_rationale = EXCLUDED.explicit_rationale,
  result = EXCLUDED.result,
  confidence = EXCLUDED.confidence,
  human_review_required = EXCLUDED.human_review_required;

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority, next_action,
  official_entry_url, status
)
SELECT
  md5(cases.run_code || ':ENTERPRISE_CCU_INPUTS')::uuid,
  run.calculation_run_id,
  'enterprise.ccu_required_inputs[first_10_ccu]',
  'The 83 use-time enterprise technical parameter slots remain unfilled. The demo mapping is not a final enterprise-part classification.',
  'ENTERPRISE_ENGINEERING_AND_CUSTOMS',
  'ENTERPRISE_INPUT',
  'ENTERPRISE',
  'OPERATIONAL_CLASSIFICATION_AND_CUSTOMS_DECLARATION',
  'P0',
  'At operational use, complete the required fields exposed by enterprise.v_part_ccu_input_collection and attach technical evidence.',
  NULL,
  'WAITING_ENTERPRISE'
FROM gp_case cases
JOIN calc.calculation_run run ON run.run_code = cases.run_code
ON CONFLICT (missing_data_id) DO UPDATE SET
  calculation_run_id = EXCLUDED.calculation_run_id,
  description = EXCLUDED.description,
  status = EXCLUDED.status;

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority, next_action,
  official_entry_url, status
)
SELECT
  md5(cases.run_code || ':GRI_2A')::uuid,
  run.calculation_run_id,
  'shipment.gri_2a_assessment',
  'The completeness, presentation and shipment grouping needed for GRI 2(a) have not been assessed.',
  'ENTERPRISE_CUSTOMS_OWNER',
  'ENTERPRISE_INPUT',
  'MIXED',
  'WHOLE_SHIPMENT_CLASSIFICATION',
  'P0',
  'Before declaration, provide the complete shipment list, assembly state, shipment timing and assembly plan for GRI 2(a) review.',
  NULL,
  'WAITING_ENTERPRISE'
FROM gp_case cases
JOIN calc.calculation_run run ON run.run_code = cases.run_code
ON CONFLICT (missing_data_id) DO UPDATE SET
  calculation_run_id = EXCLUDED.calculation_run_id,
  description = EXCLUDED.description,
  status = EXCLUDED.status;

INSERT INTO audit.missing_data (
  missing_data_id, calculation_run_id, field_path, description, data_owner,
  data_kind, data_ownership, blocking_scope, priority, next_action,
  official_entry_url, status
)
SELECT
  md5(cases.run_code || ':FTA_ELIGIBILITY')::uuid,
  run.calculation_run_id,
  'origin.' || lower(cases.requested_regime) || '.eligibility',
  cases.requested_regime || ' preference was requested but proof and origin-rule compliance were not established. MFN was applied.',
  'ENTERPRISE_FTA_OWNER',
  'ENTERPRISE_INPUT',
  'ENTERPRISE',
  cases.requested_regime || '_PREFERENCE_ONLY',
  'P0',
  'Provide valid proof of origin and the product-specific origin-rule working paper; rerun only after review.',
  'https://www.customs.gov.my/en/business/facilitation/rules-of-origin-roo/faq-customs-ruling-on-origin',
  'WAITING_ENTERPRISE'
FROM gp_case cases
JOIN calc.calculation_run run ON run.run_code = cases.run_code
WHERE cases.fallback_applied
ON CONFLICT (missing_data_id) DO UPDATE SET
  calculation_run_id = EXCLUDED.calculation_run_id,
  description = EXCLUDED.description,
  status = EXCLUDED.status;

INSERT INTO ai.llm_view_item (
  calculation_run_id, sequence_no, record_type, record_id, field_subset,
  why_read, source_clause_refs, data_quality, prompt_safe
)
SELECT
  run.calculation_run_id,
  view_item.sequence_no,
  view_item.record_type,
  CASE view_item.record_type
    WHEN 'CALCULATION_RUN' THEN run.calculation_run_id
    WHEN 'SCENARIO_MODEL' THEN run.scenario_model_id
    WHEN 'INPUT_SNAPSHOT' THEN run.input_snapshot_id
  END,
  CASE view_item.record_type
    WHEN 'CALCULATION_RUN' THEN jsonb_build_object(
      'run_code',run.run_code,'status',run.run_status,'completeness',run.completeness,
      'base_value',run.base_value,'gross_tax',run.gross_tax,
      'effective_tax_rate',run.effective_tax_rate,'currency',run.currency_code
    )
    WHEN 'SCENARIO_MODEL' THEN jsonb_build_object(
      'requested_regime',cases.requested_regime,'applied_regime',cases.applied_regime,
      'fallback_applied',cases.fallback_applied,'demo_only',true
    )
    WHEN 'INPUT_SNAPSHOT' THEN jsonb_build_object(
      'demo_only',true,'enterprise_fields_complete',false,
      'gri_2a_review_complete',false,'operational_use_permitted',false
    )
  END,
  view_item.why_read,
  '[]'::jsonb,
  'CANDIDATE',
  true
FROM gp_case cases
JOIN calc.calculation_run run ON run.run_code = cases.run_code
CROSS JOIN (
  VALUES
    (1,'SCENARIO_MODEL','Explain requested regime, applied regime and fallback without independent tax reasoning.'),
    (2,'CALCULATION_RUN','Explain the deterministic calculation result already stored by the engine.'),
    (3,'INPUT_SNAPSHOT','Explain demo limitations and missing enterprise inputs.')
) AS view_item(sequence_no, record_type, why_read)
ON CONFLICT (calculation_run_id, sequence_no) DO UPDATE SET
  record_type = EXCLUDED.record_type,
  record_id = EXCLUDED.record_id,
  field_subset = EXCLUDED.field_subset,
  why_read = EXCLUDED.why_read,
  source_clause_refs = EXCLUDED.source_clause_refs,
  data_quality = EXCLUDED.data_quality,
  prompt_safe = EXCLUDED.prompt_safe;

COMMIT;
