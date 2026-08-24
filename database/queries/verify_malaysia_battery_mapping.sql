\pset null '[NULL]'
\x off

SELECT
  ccu.ccu_code,
  hs.hs6_code,
  tm.national_tariff_code,
  tm.tariff_description,
  tm.origin_regime,
  tm.duty_rate,
  tm.additional_measure ->> 'sst_display_rate' AS sst_display_rate,
  tm.verification_status
FROM customs.tariff_mapping tm
JOIN customs.ccu_candidate_hs hs ON hs.candidate_id = tm.candidate_id
JOIN customs.customs_classification_unit ccu ON ccu.ccu_id = hs.ccu_id
WHERE tm.mapping_code = 'MAP-MY-PDK2025-8507603300-MFN';

SELECT
  requirement_code,
  requirement_type,
  applicable_object,
  a.authority_code,
  am.verification_status,
  required_document,
  failure_consequence
FROM rules.approval_matrix am
LEFT JOIN ref.authority a ON a.authority_id = am.authority_id
WHERE am.requirement_code = 'REQ-MY-IMPORT-CONTROL-8507603300';

SELECT
  priority,
  field_path,
  blocking_scope,
  status,
  next_action
FROM audit.missing_data
ORDER BY status, priority, field_path;

SELECT
  source_code,
  content_sha256,
  archived_object_key
FROM evidence.source_document
WHERE source_code = 'SRC-MY-JKDM-HS-EXPLORER';
