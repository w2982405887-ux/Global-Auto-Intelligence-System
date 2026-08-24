\pset null '[NULL]'
\x off

SELECT
  requirement_code,
  requirement_type,
  effective_from,
  verification_status,
  required_document
FROM rules.approval_matrix
WHERE requirement_code = 'REQ-MY-IMPORT-CONTROL-8507603300';

SELECT
  rule_code,
  rule_domain,
  effective_from,
  verification_status,
  formula_expression
FROM rules.country_rule_card
WHERE rule_code IN (
  'RULE-MY-SST-IMPORT-BASE-2018',
  'RULE-MY-SST-RATE-8507603300-2025'
)
ORDER BY effective_from;

SELECT
  scenario_code,
  import_mode,
  origin_regime,
  powertrain,
  verification_status,
  calculation_dsl ->> 'dsl_version' AS dsl_version
FROM rules.tax_scenario_model
WHERE scenario_code = 'SCN-MY-PARTS-BEV-BATTERY-MFN';

SELECT
  100.00::numeric(12,2) AS customs_value,
  20.00::numeric(12,2) AS import_duty,
  0.00::numeric(12,2) AS excise_duty,
  120.00::numeric(12,2) AS sst_base,
  12.00::numeric(12,2) AS sst,
  32.00::numeric(12,2) AS gross_import_tax,
  0.32000000::numeric(12,8) AS effective_tax_rate;

SELECT
  priority,
  field_path,
  blocking_scope,
  status
FROM audit.missing_data
ORDER BY status, priority, field_path;
