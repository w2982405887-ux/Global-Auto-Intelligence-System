\pset null '[NULL]'
\x off

\echo '=== FTA mapping summary ==='
SELECT
  a.agreement_code,
  t.verification_status,
  count(*) AS mapping_count,
  count(DISTINCT u.ccu_id) AS ccu_count,
  min(t.duty_rate) AS minimum_rate,
  max(t.duty_rate) AS maximum_rate
FROM customs.tariff_mapping t
JOIN ref.trade_agreement a
  ON a.trade_agreement_id = t.trade_agreement_id
JOIN customs.ccu_candidate_hs c
  ON c.candidate_id = t.candidate_id
JOIN customs.customs_classification_unit u
  ON u.ccu_id = c.ccu_id
WHERE t.mapping_id::text LIKE 'b5000000-%'
GROUP BY a.agreement_code, t.verification_status
ORDER BY a.agreement_code, t.verification_status;

\echo '=== FTA mappings by CCU ==='
SELECT
  a.agreement_code,
  u.ccu_code,
  c.hs6_code,
  t.additional_measure ->> 'pdk_2025_code' AS pdk_2025_code,
  t.national_tariff_code AS fta_tariff_code,
  t.duty_rate,
  t.additional_measure ->> 'origin_rule' AS origin_rule,
  t.additional_measure #>> '{nomenclature_correlation,status}' AS correlation_status,
  t.verification_status
FROM customs.tariff_mapping t
JOIN ref.trade_agreement a
  ON a.trade_agreement_id = t.trade_agreement_id
JOIN customs.ccu_candidate_hs c
  ON c.candidate_id = t.candidate_id
JOIN customs.customs_classification_unit u
  ON u.ccu_id = c.ccu_id
WHERE t.mapping_id::text LIKE 'b5000000-%'
ORDER BY a.agreement_code, u.ccu_code, t.mapping_code;

\echo '=== Official evidence archive ==='
SELECT
  source_code,
  source_type,
  document_number,
  effective_from,
  content_sha256 IS NOT NULL AS has_sha256,
  archived_object_key
FROM evidence.source_document
WHERE source_document_id::text LIKE 'b1000000-%'
ORDER BY source_code;

\echo '=== Executable FTA rule cards ==='
SELECT
  rule_code,
  tariff_version,
  effective_from,
  verification_status,
  source_clause_id IS NOT NULL AS has_source_clause
FROM rules.country_rule_card
WHERE rule_card_id::text LIKE 'b3000000-%'
ORDER BY rule_code;

\echo '=== Deferred enterprise and correlation gaps ==='
SELECT
  priority,
  field_path,
  blocking_scope,
  status,
  next_action
FROM audit.missing_data
WHERE missing_data_id::text LIKE 'b6000000-%'
ORDER BY priority, field_path;

\echo '=== Acceptance checks ==='
SELECT
  CASE WHEN count(*) = 32 THEN 'PASS' ELSE 'FAIL' END AS mapping_count_check,
  count(*) AS actual_mapping_count,
  count(*) FILTER (WHERE duty_rate IS NULL) AS null_rate_count,
  count(*) FILTER (WHERE source_clause_id IS NULL) AS missing_source_clause_count
FROM customs.tariff_mapping
WHERE mapping_id::text LIKE 'b5000000-%';

SELECT
  CASE WHEN count(*) = 21
        AND bool_and(content_sha256 IS NOT NULL)
        AND bool_and(archived_object_key IS NOT NULL)
       THEN 'PASS' ELSE 'FAIL' END AS evidence_archive_check,
  count(*) AS source_document_count
FROM evidence.source_document
WHERE source_document_id::text LIKE 'b1000000-%';
