\pset null '[NULL]'

WITH target_ccus AS (
  SELECT DISTINCT c.ccu_id, c.ccu_code
  FROM customs.customs_classification_unit c
  JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  WHERE h.candidate_basis =
    'Phase 1 generic candidate route; national-line selection is conditional.'
),
mapping_summary AS (
  SELECT c.ccu_id, count(m.mapping_id) AS mapping_count
  FROM target_ccus c
  LEFT JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  LEFT JOIN customs.tariff_mapping m
    ON m.candidate_id=h.candidate_id
   AND m.origin_regime='MFN'
   AND m.tariff_version='PDK 2025'
   AND m.record_status='ACTIVE'
   AND m.eligibility_condition
       ->>'final_classification_requires_use_time_gate'='true'
  GROUP BY c.ccu_id
)
SELECT count(*) AS target_ccu_count,
       count(*) FILTER (WHERE mapping_count>0) AS ccu_with_mapping,
       count(*) FILTER (WHERE mapping_count=0) AS ccu_without_mapping
FROM mapping_summary;

SELECT m.verification_status, count(*) AS mapping_count,
       count(DISTINCT c.ccu_id) AS ccu_count
FROM customs.tariff_mapping m
JOIN customs.ccu_candidate_hs h ON h.candidate_id=m.candidate_id
JOIN customs.customs_classification_unit c ON c.ccu_id=h.ccu_id
WHERE m.eligibility_condition
      ->>'final_classification_requires_use_time_gate'='true'
GROUP BY m.verification_status
ORDER BY m.verification_status;

SELECT
  count(*) AS mapping_count,
  count(*) FILTER (WHERE m.duty_rate IS NULL) AS missing_duty,
  count(*) FILTER (
    WHERE m.additional_measure #>> '{sst,displayed_rate}' IS NULL
  ) AS missing_sst,
  count(*) FILTER (WHERE m.source_clause_id IS NULL) AS missing_clause,
  count(*) FILTER (
    WHERE d.content_sha256 IS NULL OR d.archived_object_key IS NULL
  ) AS missing_source_archive,
  count(*) FILTER (
    WHERE m.additional_measure
      #>> '{portal_import_control,content_sha256}' IS NULL
  ) AS missing_control_hash
FROM customs.tariff_mapping m
JOIN evidence.source_clause clause
  ON clause.source_clause_id=m.source_clause_id
JOIN evidence.source_document d
  ON d.source_document_id=clause.source_document_id
WHERE m.eligibility_condition
      ->>'final_classification_requires_use_time_gate'='true';

SELECT c.ccu_code,
       count(m.mapping_id) AS mapping_count,
       string_agg(
         m.national_tariff_code || ':' || m.verification_status::text,
         ', ' ORDER BY m.national_tariff_code
       ) AS national_lines
FROM customs.customs_classification_unit c
JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
LEFT JOIN customs.tariff_mapping m
  ON m.candidate_id=h.candidate_id
 AND m.eligibility_condition
     ->>'final_classification_requires_use_time_gate'='true'
WHERE h.candidate_basis =
  'Phase 1 generic candidate route; national-line selection is conditional.'
GROUP BY c.ccu_code
ORDER BY c.ccu_code;

SELECT field_path, priority, status, blocking_scope
FROM audit.missing_data
WHERE field_path IN (
  'customs.pdk2025.national_line_selection[CCU-ENGINE-BLOCK-OR-HEAD]',
  'customs.pdk2025.national_line_selection[CCU-ENGINE-FUEL-INJECTOR]'
)
ORDER BY field_path;

WITH all_ccus AS (
  SELECT c.ccu_id
  FROM customs.customs_classification_unit c
  WHERE c.unit_level='CUSTOMS_CLASSIFICATION_UNIT'
    AND c.record_status='ACTIVE'
),
coverage AS (
  SELECT c.ccu_id,
         count(DISTINCT h.candidate_id) AS hs6_count,
         count(DISTINCT m.mapping_id) FILTER (
           WHERE m.origin_regime='MFN'
             AND m.tariff_version='PDK 2025'
             AND m.record_status='ACTIVE'
         ) AS mfn_mapping_count
  FROM all_ccus c
  LEFT JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  LEFT JOIN customs.tariff_mapping m ON m.candidate_id=h.candidate_id
  GROUP BY c.ccu_id
)
SELECT count(*) AS active_ccus,
       count(*) FILTER (WHERE hs6_count BETWEEN 1 AND 3)
         AS ccu_with_1_to_3_hs6,
       count(*) FILTER (WHERE mfn_mapping_count>0) AS ccu_with_mfn_mapping,
       count(*) FILTER (WHERE mfn_mapping_count=0) AS ccu_without_mfn_mapping
FROM coverage;

