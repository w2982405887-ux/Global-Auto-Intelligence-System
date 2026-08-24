\pset null '[NULL]'
\pset expanded off

\echo '1. Golden-path run summary'
SELECT
  run.run_code,
  input.input_payload->>'requested_origin_regime' AS requested_regime,
  CASE
    WHEN run.run_code LIKE '%FALLBACK-MFN' OR run.run_code = 'RUN-MY-GP-MFN' THEN 'MFN'
    WHEN run.run_code LIKE '%ACFTA%' THEN 'ACFTA'
    WHEN run.run_code LIKE '%RCEP%' THEN 'RCEP'
  END AS applied_regime,
  run.run_status,
  run.completeness,
  run.currency_code,
  run.base_value,
  run.gross_tax,
  run.effective_tax_rate
FROM calc.calculation_run run
JOIN enterprise.input_snapshot snapshot
  ON snapshot.input_snapshot_id = run.input_snapshot_id
JOIN enterprise.scenario_input input
  ON input.scenario_input_id = snapshot.scenario_input_id
WHERE run.run_code LIKE 'RUN-MY-GP-%'
ORDER BY run.run_code;

\echo '2. Tax totals by run'
SELECT
  run.run_code,
  split_part(line.tax_code, ':', 1) AS tax_type,
  count(*) AS ccu_line_count,
  sum(line.base_amount) AS summed_base,
  sum(line.gross_tax_amount) AS tax_amount
FROM calc.calculation_run run
JOIN calc.calculation_line line
  ON line.calculation_run_id = run.calculation_run_id
WHERE run.run_code LIKE 'RUN-MY-GP-%'
GROUP BY run.run_code, split_part(line.tax_code, ':', 1)
ORDER BY run.run_code, tax_type;

\echo '3. Per-CCU applied tariff mapping and tax result'
SELECT
  run.run_code,
  split_part(line.tax_code, ':', 2) AS ccu_code,
  mapping.national_tariff_code,
  mapping.duty_rate,
  mapping.verification_status AS mapping_status,
  line.base_amount AS customs_value,
  line.gross_tax_amount AS import_duty
FROM calc.calculation_run run
JOIN calc.calculation_line line
  ON line.calculation_run_id = run.calculation_run_id
JOIN customs.tariff_mapping mapping
  ON mapping.mapping_id = line.tariff_mapping_id
WHERE run.run_code LIKE 'RUN-MY-GP-%'
  AND split_part(line.tax_code, ':', 1) = 'IMPORT_DUTY'
ORDER BY run.run_code, ccu_code;

\echo '4. Fallback decisions'
SELECT
  run.run_code,
  trace.result->>'requested_regime' AS requested_regime,
  trace.result->>'applied_regime' AS applied_regime,
  trace.result->>'fallback_applied' AS fallback_applied,
  trace.explicit_rationale
FROM calc.calculation_run run
JOIN audit.decision_trace trace
  ON trace.calculation_run_id = run.calculation_run_id
WHERE run.run_code LIKE 'RUN-MY-GP-%'
  AND trace.step_type = 'SCENARIO_SELECTION'
ORDER BY run.run_code;

\echo '5. Audit coverage and open use-time gaps'
SELECT
  run.run_code,
  count(DISTINCT trace.decision_trace_id) AS decision_steps,
  count(DISTINCT view_item.llm_view_item_id) AS llm_view_items,
  count(DISTINCT missing.missing_data_id) AS run_missing_items,
  count(DISTINCT missing.missing_data_id) FILTER (
    WHERE missing.status = 'WAITING_ENTERPRISE'
  ) AS waiting_enterprise_items
FROM calc.calculation_run run
LEFT JOIN audit.decision_trace trace
  ON trace.calculation_run_id = run.calculation_run_id
LEFT JOIN ai.llm_view_item view_item
  ON view_item.calculation_run_id = run.calculation_run_id
LEFT JOIN audit.missing_data missing
  ON missing.calculation_run_id = run.calculation_run_id
WHERE run.run_code LIKE 'RUN-MY-GP-%'
GROUP BY run.run_code
ORDER BY run.run_code;

\echo '6. Acceptance checks (all rows should be PASS)'
WITH run_checks AS (
  SELECT
    run.calculation_run_id,
    run.run_code,
    run.base_value,
    run.gross_tax,
    run.effective_tax_rate,
    count(DISTINCT line.calculation_line_id) AS line_count,
    count(DISTINCT split_part(line.tax_code, ':', 2)) AS ccu_count,
    count(DISTINCT trace.decision_trace_id) AS trace_count,
    count(DISTINCT view_item.llm_view_item_id) AS view_count
  FROM calc.calculation_run run
  LEFT JOIN calc.calculation_line line
    ON line.calculation_run_id = run.calculation_run_id
  LEFT JOIN audit.decision_trace trace
    ON trace.calculation_run_id = run.calculation_run_id
  LEFT JOIN ai.llm_view_item view_item
    ON view_item.calculation_run_id = run.calculation_run_id
  WHERE run.run_code LIKE 'RUN-MY-GP-%'
  GROUP BY run.calculation_run_id
)
SELECT 'five_runs_created' AS check_name,
       CASE WHEN count(*) = 5 THEN 'PASS' ELSE 'FAIL' END AS result,
       count(*)::text AS observed
FROM run_checks
UNION ALL
SELECT 'each_run_has_30_tax_lines',
       CASE WHEN bool_and(line_count = 30) THEN 'PASS' ELSE 'FAIL' END,
       min(line_count)::text || '..' || max(line_count)::text
FROM run_checks
UNION ALL
SELECT 'each_run_has_10_ccus',
       CASE WHEN bool_and(ccu_count = 10) THEN 'PASS' ELSE 'FAIL' END,
       min(ccu_count)::text || '..' || max(ccu_count)::text
FROM run_checks
UNION ALL
SELECT 'each_run_has_7_decision_steps',
       CASE WHEN bool_and(trace_count = 7) THEN 'PASS' ELSE 'FAIL' END,
       min(trace_count)::text || '..' || max(trace_count)::text
FROM run_checks
UNION ALL
SELECT 'each_run_has_3_llm_view_items',
       CASE WHEN bool_and(view_count = 3) THEN 'PASS' ELSE 'FAIL' END,
       min(view_count)::text || '..' || max(view_count)::text
FROM run_checks
UNION ALL
SELECT 'base_value_is_100000',
       CASE WHEN bool_and(base_value = 100000) THEN 'PASS' ELSE 'FAIL' END,
       min(base_value)::text || '..' || max(base_value)::text
FROM run_checks
UNION ALL
SELECT 'run_total_matches_line_total',
       CASE WHEN bool_and(gross_tax = line_total) THEN 'PASS' ELSE 'FAIL' END,
       count(*) FILTER (WHERE gross_tax = line_total)::text || '/5'
FROM (
  SELECT checks.*, (
    SELECT sum(line.gross_tax_amount)
    FROM calc.calculation_line line
    WHERE line.calculation_run_id = checks.calculation_run_id
  ) AS line_total
  FROM run_checks checks
) totals
UNION ALL
SELECT 'blocked_fta_runs_fallback_to_mfn',
       CASE WHEN count(*) = 2 THEN 'PASS' ELSE 'FAIL' END,
       count(*)::text
FROM calc.calculation_run run
JOIN audit.decision_trace trace
  ON trace.calculation_run_id = run.calculation_run_id
WHERE run.run_code IN (
  'RUN-MY-GP-ACFTA-BLOCKED-FALLBACK-MFN',
  'RUN-MY-GP-RCEP-BLOCKED-FALLBACK-MFN'
)
  AND trace.step_type = 'SCENARIO_SELECTION'
  AND trace.result->>'applied_regime' = 'MFN'
  AND (trace.result->>'fallback_applied')::boolean;

\echo '7. Enterprise use-time slots remain empty by design'
SELECT
  count(*) AS demo_parameter_slots,
  count(*) FILTER (WHERE value_status = 'EMPTY') AS empty_slots,
  count(*) FILTER (WHERE required_at_use) AS required_at_use_slots,
  count(*) FILTER (WHERE accepted_for_use) AS accepted_slots
FROM enterprise.v_part_ccu_input_collection
WHERE enterprise_code = 'DEMO-GOLDEN-PATH';
