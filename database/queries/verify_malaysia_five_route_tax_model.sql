\set ON_ERROR_STOP on
\pset null '[NULL]'

DO $$
DECLARE
  actual integer;
BEGIN
  SELECT count(*) INTO actual
  FROM rules.vehicle_tax_route route
  JOIN ref.country country ON country.country_id = route.country_id
  WHERE country.iso2 = 'MY'
    AND route.record_status = 'ACTIVE';
  IF actual <> 5 THEN
    RAISE EXCEPTION 'Expected 5 active Malaysia routes, found %', actual;
  END IF;

  SELECT count(DISTINCT decision_order) INTO actual
  FROM rules.vehicle_tax_route route
  JOIN ref.country country ON country.country_id = route.country_id
  WHERE country.iso2 = 'MY'
    AND route.record_status = 'ACTIVE'
    AND decision_order BETWEEN 1 AND 5;
  IF actual <> 5 THEN
    RAISE EXCEPTION 'Malaysia route decision order is incomplete';
  END IF;

  SELECT count(*) INTO actual
  FROM rules.kd_tax_bucket_definition bucket
  JOIN ref.country country ON country.country_id = bucket.country_id
  WHERE country.iso2 = 'MY'
    AND bucket.record_status = 'ACTIVE';
  IF actual <> 8 THEN
    RAISE EXCEPTION 'Expected 8 KD tax buckets, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.customs_classification_unit
  WHERE unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
    AND record_status = 'ACTIVE';
  IF actual < 60 THEN
    RAISE EXCEPTION 'Expected at least 60 active CCUs, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.tariff_mapping mapping
  JOIN ref.country country ON country.country_id = mapping.country_id
  WHERE country.iso2 = 'MY'
    AND mapping.record_status = 'ACTIVE';
  IF actual < 346 THEN
    RAISE EXCEPTION 'Expected at least 346 active Malaysia CCU mappings, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.tariff_mapping mapping
  JOIN ref.country country ON country.country_id = mapping.country_id
  WHERE country.iso2 = 'MY'
    AND mapping.record_status = 'ACTIVE'
    AND mapping.duty_rate IS NULL;
  IF actual <> 0 THEN
    RAISE EXCEPTION 'Found % active CCU mappings without duty rate', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line line
  JOIN ref.country country ON country.country_id = line.country_id
  WHERE country.iso2 = 'MY'
    AND line.record_status = 'ACTIVE';
  IF actual <> 1589 THEN
    RAISE EXCEPTION 'Expected 1589 current vehicle tariff rows, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line line
  JOIN ref.country country ON country.country_id = line.country_id
  WHERE country.iso2 = 'MY'
    AND line.record_status = 'ACTIVE'
    AND line.tariff_schedule_code = 'PDK-2025';
  IF actual <> 471 THEN
    RAISE EXCEPTION 'Expected 471 PDK 2025 vehicle rows, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line line
  JOIN rules.vehicle_tax_route route
    ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
  WHERE line.tariff_schedule_code = 'PDK-2025'
    AND route.route_code = 'ROUTE-MY-01-CBU';
  IF actual <> 304 THEN
    RAISE EXCEPTION 'Expected 304 PDK CBU rows, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line line
  JOIN rules.vehicle_tax_route route
    ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
  WHERE line.tariff_schedule_code = 'PDK-2025'
    AND route.route_code = 'ROUTE-MY-02-CKD-WHOLE-KIT';
  IF actual <> 167 THEN
    RAISE EXCEPTION 'Expected 167 PDK CKD rows, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line
  WHERE tariff_schedule_code = 'ACFTA-CURRENT-2026';
  IF actual <> 471 THEN
    RAISE EXCEPTION 'Expected 471 ACFTA vehicle rows, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line
  WHERE tariff_schedule_code = 'RCEP-CURRENT-2026';
  IF actual <> 647 THEN
    RAISE EXCEPTION 'Expected 647 RCEP vehicle rows, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line
  WHERE import_duty_rate IS NULL;
  IF actual <> 0 THEN
    RAISE EXCEPTION 'Found % tariff rows without a public import-duty rate', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line line
  JOIN rules.vehicle_tax_route route
    ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
  WHERE route.route_code = 'ROUTE-MY-02-CKD-WHOLE-KIT'
    AND (
      line.sales_tax_rate IS DISTINCT FROM 0
      OR line.sales_tax_treatment <> 'EXEMPT'
      OR line.excise_treatment <> 'NOT_AT_IMPORT'
    );
  IF actual <> 0 THEN
    RAISE EXCEPTION 'Found % CKD vehicle rows with invalid SST/excise treatment', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line
  WHERE origin_regime = 'FTA'
    AND (
      trade_agreement_id IS NULL
      OR eligibility_condition = '{}'::jsonb
      OR eligibility_condition->>'fallback_if_not_eligible' <> 'MFN'
    );
  IF actual <> 0 THEN
    RAISE EXCEPTION 'Found % FTA rows without agreement, eligibility or MFN fallback', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line
  WHERE tariff_schedule_code = 'PDK-2025'
    AND excise_duty_rate IS NULL;
  IF actual <> 218 THEN
    RAISE EXCEPTION
      'Expected 218 intentionally unresolved/not-at-import PDK excise rows, found %',
      actual;
  END IF;

  SELECT count(*) INTO actual
  FROM customs.vehicle_tariff_rate_line line
  JOIN rules.vehicle_tax_route route
    ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
  WHERE line.tariff_schedule_code = 'PDK-2025'
    AND route.route_code = 'ROUTE-MY-01-CBU'
    AND line.excise_duty_rate IS NULL
    AND line.excise_treatment = 'UNKNOWN'
    AND line.verification_status = 'CANDIDATE';
  IF actual <> 51 THEN
    RAISE EXCEPTION
      'Expected 51 CBU lines to remain explicit candidate/unknown excise rows, found %',
      actual;
  END IF;

  SELECT count(*) INTO actual
  FROM rules.tax_scenario_model
  WHERE scenario_code LIKE 'SCN-MY-ROUTE-%'
    AND record_status = 'ACTIVE';
  IF actual <> 5 THEN
    RAISE EXCEPTION 'Expected 5 active five-route scenarios, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM rules.tax_scenario_model
  WHERE scenario_code LIKE 'SCN-MY-CBU-%'
    AND calculation_dsl::text LIKE '%vehicle.excise_value%';
  IF actual <> 0 THEN
    RAISE EXCEPTION 'A CBU scenario still uses enterprise-supplied excise value';
  END IF;

  SELECT count(*) INTO actual
  FROM rules.tax_scenario_model
  WHERE scenario_code LIKE 'SCN-MY-LOCAL-%'
    AND calculation_dsl::text LIKE '%"step_id": "IMPORT_DUTY"%';
  IF actual <> 0 THEN
    RAISE EXCEPTION 'A local finished-vehicle scenario still taxes the vehicle as an import';
  END IF;

  SELECT count(*) INTO actual
  FROM rules.approval_matrix
  WHERE requirement_code IN (
    'REQ-MY-CBU-N180-OR-FRANCHISE-AP',
    'REQ-MY-CBU-ANNUAL-AP-ALLOCATION',
    'REQ-MY-CKD-AP-AND-DEFINITION',
    'REQ-MY-N205-PARTS-SUBASSEMBLIES',
    'REQ-MY-PART-LEVEL-IMPORT-CONTROL-SCREEN',
    'REQ-MY-FTA-SHIPMENT-ORIGIN-PROOF',
    'REQ-MY-LOCAL-BEV-EXEMPTION-CONFIRMATION',
    'REQ-MY-CUSTOMISED-AUTOMOTIVE-INCENTIVE-LETTER',
    'REQ-MY-COMPONENT-DUTY-EXEMPTION-APPROVAL'
  )
    AND record_status = 'ACTIVE';
  IF actual <> 9 THEN
    RAISE EXCEPTION 'Expected 9 core approval/eligibility gates, found %', actual;
  END IF;

  SELECT count(*) INTO actual
  FROM rules.country_rule_card
  WHERE rule_code = 'RULE-MY-CUSTOMISED-INCENTIVE-NO-PUBLIC-DEFAULT'
    AND formula_expression->>'excise_reduction_source' = 'ENTERPRISE_APPROVAL'
    AND formula_expression->>'localization_threshold_source' = 'ENTERPRISE_APPROVAL'
    AND formula_expression->>'missing_approval' = 'STATUTORY_RATE';
  IF actual <> 1 THEN
    RAISE EXCEPTION 'Customized incentive is not protected by enterprise approval';
  END IF;

  SELECT count(*) INTO actual
  FROM rules.country_rule_card
  WHERE rule_code = 'RULE-MY-COMPONENT-EXEMPTION-APPROVAL-ONLY'
    AND formula_expression->>'approved_rate_source' = 'ENTERPRISE_APPROVAL'
    AND formula_expression->>'fallback' = 'STATUTORY';
  IF actual <> 1 THEN
    RAISE EXCEPTION 'Component exemption is not protected by enterprise approval';
  END IF;

  SELECT count(*) INTO actual
  FROM rules.country_rule_card
  WHERE rule_code = 'RULE-MY-NO-SEPARATE-VAT-GST'
    AND (formula_expression->>'vat_rate')::numeric = 0
    AND (formula_expression->>'gst_rate')::numeric = 0;
  IF actual <> 1 THEN
    RAISE EXCEPTION 'Malaysia no-separate-VAT/GST guard is missing';
  END IF;
END
$$;

SELECT
  decision_order,
  route_code,
  route_name_cn,
  route_kind,
  classification_granularity,
  verification_status
FROM ai.v_malaysia_five_route_decision_current
ORDER BY decision_order;

SELECT
  route_code,
  tariff_line_count,
  mfn_line_count,
  acfta_line_count,
  rcep_line_count,
  missing_public_duty_rate_count,
  verified_tariff_line_count,
  kd_tax_bucket_count,
  active_ccu_count,
  mapped_ccu_count,
  ccu_tariff_mapping_count,
  ccu_mapping_missing_duty_count
FROM ai.v_malaysia_five_route_readiness
ORDER BY decision_order;

SELECT
  tariff_schedule_code,
  count(*) AS line_count,
  count(*) FILTER (WHERE import_duty_rate IS NULL) AS missing_import_rate,
  count(*) FILTER (WHERE excise_duty_rate IS NULL) AS excise_not_public_or_not_at_import,
  min(import_duty_rate) AS minimum_import_rate,
  max(import_duty_rate) AS maximum_import_rate
FROM customs.vehicle_tariff_rate_line
GROUP BY tariff_schedule_code
ORDER BY tariff_schedule_code;

SELECT
  route.route_code,
  count(*) AS linked_source_clauses
FROM rules.vehicle_tax_route route
JOIN rules.vehicle_tax_route_source_link link
  ON link.vehicle_tax_route_id = route.vehicle_tax_route_id
GROUP BY route.route_code, route.decision_order
ORDER BY route.decision_order;

SELECT
  scenario_code,
  import_mode,
  verification_status,
  jsonb_array_length(required_input_fields) AS required_input_count
FROM rules.tax_scenario_model
WHERE scenario_code LIKE 'SCN-MY-ROUTE-%'
ORDER BY scenario_code;

\echo 'Malaysia five-route tax model verification passed.'
