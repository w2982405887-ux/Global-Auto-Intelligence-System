\pset null '[NULL]'
\x off

SELECT
  c.iso2,
  c.country_name_en,
  a.authority_code,
  a.authority_name
FROM ref.country c
JOIN ref.authority a ON a.country_id = c.country_id
WHERE c.iso2 = 'MY'
ORDER BY a.authority_code;

SELECT
  d.source_code,
  d.document_number,
  d.official_status,
  d.effective_from,
  count(cl.source_clause_id) AS clause_count
FROM evidence.source_document d
LEFT JOIN evidence.source_clause cl
  ON cl.source_document_id = d.source_document_id
WHERE d.source_code LIKE 'SRC-MY-%'
GROUP BY d.source_document_id
ORDER BY d.source_code;

SELECT
  ccu.ccu_code,
  ccu.ccu_name_en,
  hs.candidate_rank,
  hs.hs6_code,
  hs.verification_status,
  tm.national_tariff_code,
  tm.duty_rate
FROM customs.customs_classification_unit ccu
JOIN customs.ccu_candidate_hs hs ON hs.ccu_id = ccu.ccu_id
LEFT JOIN customs.tariff_mapping tm ON tm.candidate_id = hs.candidate_id
WHERE ccu.ccu_code = 'CCU-HV-BATTERY-PACK';

SELECT
  rt.risk_tag_type,
  rt.risk_level,
  rt.verification_status,
  rt.risk_note
FROM customs.ccu_risk_tag rt
JOIN customs.customs_classification_unit ccu ON ccu.ccu_id = rt.ccu_id
WHERE ccu.ccu_code = 'CCU-HV-BATTERY-PACK'
ORDER BY rt.risk_tag_type;

SELECT
  requirement_code,
  requirement_type,
  import_mode,
  verification_status,
  failure_consequence
FROM rules.approval_matrix
WHERE requirement_code = 'REQ-MY-AP-MOTOR-VEHICLE-CKD';

SELECT
  priority,
  field_path,
  blocking_scope,
  status,
  next_action
FROM audit.missing_data
WHERE status = 'OPEN'
ORDER BY priority, field_path;
