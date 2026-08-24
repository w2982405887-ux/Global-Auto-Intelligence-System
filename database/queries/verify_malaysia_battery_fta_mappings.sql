\pset null '[NULL]'
\x off

SELECT
  ta.agreement_code,
  tm.tariff_version,
  tm.national_tariff_code,
  tm.tariff_description,
  tm.duty_rate,
  tm.rate_type,
  tm.verification_status,
  tm.additional_measure
FROM customs.tariff_mapping tm
JOIN ref.trade_agreement ta
  ON ta.trade_agreement_id = tm.trade_agreement_id
WHERE tm.mapping_code IN (
  'MAP-MY-ACFTA-2026-8507603300-CN',
  'MAP-MY-RCEP-2026-8507609000-CN'
)
ORDER BY ta.agreement_code;

SELECT
  rule_code,
  rule_name_cn,
  rule_name_cn LIKE '%?%' AS contains_literal_question_mark,
  encode(convert_to(rule_name_cn, 'UTF8'), 'hex') AS rule_name_cn_utf8_hex,
  verification_status,
  condition_expression
FROM rules.country_rule_card
WHERE rule_code IN (
  'RULE-MY-ACFTA-ORIGIN-DOCUMENT',
  'RULE-MY-RCEP-ORIGIN-DOCUMENT'
)
ORDER BY rule_code;

SELECT
  'MFN' AS regime, 20.00::numeric(12,2) AS import_duty,
  12.00::numeric(12,2) AS sst, 32.00::numeric(12,2) AS total_tax
UNION ALL
SELECT 'ACFTA', 0.00, 10.00, 10.00
UNION ALL
SELECT 'RCEP', 20.00, 12.00, 32.00;

SELECT
  priority, field_path, blocking_scope, status, next_action
FROM audit.missing_data
WHERE missing_data_id IN (
  'a0000000-0000-4000-8000-000000000007',
  'a0000000-0000-4000-8000-000000000008',
  'f6000000-0000-4000-8000-000000000001',
  'f6000000-0000-4000-8000-000000000002'
)
ORDER BY status, field_path;

SELECT source_code, content_sha256, archived_object_key
FROM evidence.source_document
WHERE source_code IN (
  'SRC-MY-JKDM-HS-EXPLORER-ACFTA-850760-2026',
  'SRC-MY-JKDM-HS-EXPLORER-RCEP-850760-2026'
)
ORDER BY source_code;
