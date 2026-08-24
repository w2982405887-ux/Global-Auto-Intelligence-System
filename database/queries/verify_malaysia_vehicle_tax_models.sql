\pset null '[NULL]'

SELECT
  powertrain,
  count(*) AS full_tariff_lines,
  min(import_duty_rate) AS min_import_rate,
  max(import_duty_rate) AS max_import_rate,
  min(excise_duty_rate) AS min_excise_rate,
  max(excise_duty_rate) AS max_excise_rate,
  min(sales_tax_rate) AS min_sst_rate,
  max(sales_tax_rate) AS max_sst_rate
FROM customs.vehicle_tariff_line
WHERE country_id = (SELECT country_id FROM ref.country WHERE iso2 = 'MY')
  AND tariff_version = 'PDK 2025'
  AND record_status = 'ACTIVE'
GROUP BY powertrain
ORDER BY powertrain;

SELECT
  count(*) AS total_vehicle_lines,
  count(*) FILTER (
    WHERE import_duty_rate IS NULL
       OR excise_duty_rate IS NULL
       OR sales_tax_rate IS NULL
  ) AS missing_rate_lines,
  count(*) FILTER (
    WHERE tariff_source_clause_id IS NULL
       OR excise_source_clause_id IS NULL
  ) AS missing_evidence_lines,
  count(DISTINCT national_tariff_code) AS distinct_national_codes
FROM customs.vehicle_tariff_line
WHERE record_status = 'ACTIVE';

SELECT
  program_code,
  import_mode,
  powertrain,
  approval_required,
  effective_from,
  effective_to,
  verification_status,
  benefit_expression
FROM rules.automotive_incentive_program
WHERE record_status = 'ACTIVE'
ORDER BY program_code;

SELECT
  requirement_code,
  requirement_type,
  import_mode,
  powertrain,
  verification_status,
  failure_consequence
FROM rules.approval_matrix
WHERE requirement_code IN (
  'REQ-MY-CBU-VEHICLE-AP-2026',
  'REQ-MY-LOCAL-ASSEMBLY-MODEL-APPROVAL',
  'REQ-MY-AUTOMOTIVE-CUSTOMISED-INCENTIVE-LETTER',
  'REQ-MY-CKD-BEV-TAX-EXEMPTION-CONFIRMATION'
)
ORDER BY requirement_code;

SELECT
  scenario_code,
  import_mode,
  powertrain,
  classification_route,
  verification_status,
  effective_from,
  effective_to
FROM rules.tax_scenario_model
WHERE scenario_code IN (
  'SCN-MY-CBU-ICE-MFN-2025',
  'SCN-MY-CBU-PHEV-MFN-2025',
  'SCN-MY-CBU-BEV-MFN-2025',
  'SCN-MY-LOCAL-ICE-PROJECT',
  'SCN-MY-LOCAL-PHEV-PROJECT',
  'SCN-MY-LOCAL-BEV-EXEMPT-2027'
)
ORDER BY scenario_code;

SELECT
  (SELECT count(*) FROM ai.v_malaysia_vehicle_tax_lines_current)
    AS ai_current_vehicle_lines,
  (SELECT count(*) FROM ai.v_malaysia_automotive_incentives_current)
    AS ai_current_incentives,
  (SELECT count(*) FROM ai.v_malaysia_vehicle_scenarios_current)
    AS ai_current_scenarios;

WITH normalized AS (
  SELECT
    national_tariff_code,
    powertrain,
    import_duty_rate,
    excise_duty_rate,
    sales_tax_rate,
    100.00::numeric AS customs_value,
    100.00::numeric AS excise_value
  FROM customs.vehicle_tariff_line
  WHERE national_tariff_code IN (
    SELECT min(national_tariff_code)
    FROM customs.vehicle_tariff_line
    WHERE record_status = 'ACTIVE'
    GROUP BY powertrain, excise_duty_rate
  )
),
taxes AS (
  SELECT
    *,
    customs_value * import_duty_rate AS import_duty,
    excise_value * excise_duty_rate AS excise_duty
  FROM normalized
)
SELECT
  national_tariff_code,
  powertrain,
  import_duty_rate,
  excise_duty_rate,
  sales_tax_rate,
  round(import_duty, 2) AS import_duty_on_100,
  round(excise_duty, 2) AS excise_on_100,
  round(
    (customs_value + import_duty + excise_duty) * sales_tax_rate,
    2
  ) AS sst_on_100,
  round(
    import_duty + excise_duty
    + (customs_value + import_duty + excise_duty) * sales_tax_rate,
    2
  ) AS gross_tax_on_100
FROM taxes
ORDER BY powertrain, excise_duty_rate;

DO $$
DECLARE
  line_count integer;
  missing_count integer;
  scenario_count integer;
  program_count integer;
  unsafe_default_count integer;
  ai_line_count integer;
BEGIN
  SELECT count(*) INTO line_count
  FROM customs.vehicle_tariff_line
  WHERE record_status = 'ACTIVE';
  IF line_count <> 247 THEN
    RAISE EXCEPTION 'Expected 247 active CBU lines, found %', line_count;
  END IF;

  SELECT count(*) INTO missing_count
  FROM customs.vehicle_tariff_line
  WHERE record_status = 'ACTIVE'
    AND (
      import_duty_rate IS NULL
      OR excise_duty_rate IS NULL
      OR sales_tax_rate IS NULL
      OR tariff_source_clause_id IS NULL
      OR excise_source_clause_id IS NULL
    );
  IF missing_count <> 0 THEN
    RAISE EXCEPTION 'Vehicle lines with missing rate/evidence: %', missing_count;
  END IF;

  SELECT count(*) INTO scenario_count
  FROM rules.tax_scenario_model
  WHERE scenario_code LIKE 'SCN-MY-CBU-%-2025'
     OR scenario_code LIKE 'SCN-MY-LOCAL-%';
  IF scenario_count < 6 THEN
    RAISE EXCEPTION 'Expected at least 6 vehicle scenarios, found %', scenario_count;
  END IF;

  SELECT count(*) INTO program_count
  FROM rules.automotive_incentive_program
  WHERE record_status = 'ACTIVE';
  IF program_count <> 3 THEN
    RAISE EXCEPTION 'Expected 3 incentive programs, found %', program_count;
  END IF;

  SELECT count(*) INTO unsafe_default_count
  FROM rules.automotive_incentive_program
  WHERE powertrain IN ('ICE_GASOLINE', 'PHEV')
    AND (
      benefit_expression ? 'default_excise_reduction'
      AND benefit_expression->'default_excise_reduction' <> 'null'::jsonb
    );
  IF unsafe_default_count <> 0 THEN
    RAISE EXCEPTION 'ICE/PHEV programs contain unsafe public default reductions';
  END IF;

  SELECT count(*) INTO ai_line_count
  FROM ai.v_malaysia_vehicle_tax_lines_current;
  IF ai_line_count <> 247 THEN
    RAISE EXCEPTION 'AI current vehicle-line view expected 247 rows, found %', ai_line_count;
  END IF;

  RAISE NOTICE 'Malaysia vehicle tax model verification PASS';
END
$$;
