\pset null '[NULL]'
\pset border 2
\pset expanded off

\echo '1. Round-one coverage'
SELECT
  count(DISTINCT c.ccu_code) AS mapped_ccu_count,
  count(*) AS mapping_row_count,
  count(*) FILTER (WHERE tm.verification_status = 'VERIFIED') AS verified_mapping_rows,
  count(*) FILTER (WHERE tm.verification_status = 'CANDIDATE') AS candidate_mapping_rows
FROM customs.tariff_mapping tm
JOIN customs.ccu_candidate_hs h ON h.candidate_id = tm.candidate_id
JOIN customs.customs_classification_unit c ON c.ccu_id = h.ccu_id
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  AND c.ccu_code <> 'CCU-HV-BATTERY-PACK';

\echo '2. CCU -> HS6 -> PDK 2025 national line -> MFN/SST'
SELECT
  c.ccu_code,
  h.candidate_rank,
  h.hs6_code,
  tm.national_tariff_code,
  tm.tariff_description,
  to_char(tm.duty_rate * 100, 'FM990D00') || '%' AS mfn_duty,
  to_char(
    ((tm.additional_measure -> 'sst' ->> 'displayed_rate')::numeric) * 100,
    'FM990D00'
  ) || '%' AS portal_sst,
  tm.additional_measure ->> 'customs_unit' AS unit,
  tm.additional_measure -> 'portal_import_control' ->> 'result'
    AS portal_import_control,
  tm.verification_status
FROM customs.tariff_mapping tm
JOIN customs.ccu_candidate_hs h ON h.candidate_id = tm.candidate_id
JOIN customs.customs_classification_unit c ON c.ccu_id = h.ccu_id
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
ORDER BY c.ccu_code, h.candidate_rank, tm.national_tariff_code;

\echo '3. Non-empty portal import-control observations'
SELECT
  c.ccu_code,
  tm.national_tariff_code,
  tm.additional_measure -> 'portal_import_control' ->> 'result'
    AS portal_result,
  tm.additional_measure -> 'portal_import_control' ->> 'scope_assessment'
    AS scope_assessment,
  sc.original_text AS portal_text,
  sc.evidence_summary
FROM customs.tariff_mapping tm
JOIN customs.ccu_candidate_hs h ON h.candidate_id = tm.candidate_id
JOIN customs.customs_classification_unit c ON c.ccu_id = h.ccu_id
JOIN evidence.source_clause sc
  ON sc.source_clause_id =
     (tm.additional_measure -> 'portal_import_control' ->> 'source_clause_id')::uuid
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  AND tm.additional_measure -> 'portal_import_control' ->> 'result'
      = 'SCHEDULE_ROWS_DISPLAYED'
ORDER BY tm.national_tariff_code, c.ccu_code;

\echo '4. Enterprise inputs intentionally left open'
SELECT
  field_path,
  priority,
  status,
  description,
  next_action
FROM audit.missing_data
WHERE field_path LIKE 'enterprise.classification_input[CCU-%]%'
ORDER BY priority, field_path;

\echo '5. Authority and omitted-indentation gaps'
SELECT
  data_kind,
  field_path,
  priority,
  status,
  next_action
FROM audit.missing_data
WHERE field_path LIKE 'rules.import_control[%'
   OR field_path LIKE 'customs.pdk2025.omitted_parent_indentation[%'
ORDER BY data_kind, priority, field_path;

\echo '6. Evidence archive integrity'
SELECT
  count(*) AS source_document_count,
  count(*) FILTER (
    WHERE content_sha256 IS NOT NULL
      AND archived_object_key IS NOT NULL
  ) AS hashed_and_archived,
  count(*) FILTER (
    WHERE content_sha256 IS NULL
       OR archived_object_key IS NULL
  ) AS missing_archive_metadata
FROM evidence.source_document
WHERE source_code LIKE 'SRC-MY-JKDM-PDK2025-%-20260728'
   OR source_code LIKE 'SRC-MY-JKDM-CONTROL-%-20260728';

\echo '7. Integrity checks: every result should be zero'
SELECT 'duplicate_mapping_code_version' AS check_name, count(*) AS error_count
FROM (
  SELECT mapping_code, version
  FROM customs.tariff_mapping
  WHERE mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  GROUP BY mapping_code, version
  HAVING count(*) > 1
) x
UNION ALL
SELECT 'national_code_not_under_candidate_hs6', count(*)
FROM customs.tariff_mapping tm
JOIN customs.ccu_candidate_hs h ON h.candidate_id = tm.candidate_id
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  AND left(tm.national_tariff_code, 6) <> h.hs6_code
UNION ALL
SELECT 'mapping_without_verified_tariff_clause', count(*)
FROM customs.tariff_mapping tm
JOIN evidence.source_clause sc ON sc.source_clause_id = tm.source_clause_id
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  AND sc.verification_status <> 'VERIFIED'
UNION ALL
SELECT 'mapping_without_sst_display_rate', count(*)
FROM customs.tariff_mapping tm
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  AND tm.additional_measure -> 'sst' ->> 'displayed_rate' IS NULL
UNION ALL
SELECT 'mapping_without_control_evidence', count(*)
FROM customs.tariff_mapping tm
LEFT JOIN evidence.source_clause sc
  ON sc.source_clause_id =
     (tm.additional_measure -> 'portal_import_control' ->> 'source_clause_id')::uuid
WHERE tm.mapping_code LIKE 'MAP-MY-MFN-CCU-%-R1'
  AND sc.source_clause_id IS NULL;

