\pset null '[NULL]'
\pset border 2

\echo '1. Official PDF evidence'
SELECT
  d.source_code,
  d.document_number,
  d.content_sha256,
  d.archived_object_key,
  count(c.source_clause_id) FILTER (
    WHERE c.clause_code LIKE 'CLAUSE-MY-PDK2025-%-PARENT-INDENTATION'
  ) AS parent_clause_count
FROM evidence.source_document d
LEFT JOIN evidence.source_clause c
  ON c.source_document_id = d.source_document_id
WHERE d.source_code = 'SRC-MY-PDK-2025'
GROUP BY d.source_code, d.document_number,
         d.content_sha256, d.archived_object_key;

\echo '2. Resolved conditional mappings'
SELECT
  c.ccu_code,
  tm.national_tariff_code,
  tm.tariff_description,
  tm.record_status,
  tm.verification_status,
  tm.additional_measure ->> 'pdk_parent_group' AS pdk_parent_group,
  tm.additional_measure ->> 'classification_disposition'
    AS classification_disposition
FROM customs.tariff_mapping tm
JOIN customs.ccu_candidate_hs h ON h.candidate_id = tm.candidate_id
JOIN customs.customs_classification_unit c ON c.ccu_id = h.ccu_id
WHERE tm.mapping_code IN (
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501521200-R1',
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501522200-R1',
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501523200-R1',
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501531000-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708701600-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708702200-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708703200-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708709700-R1',
  'MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708801600-R1',
  'MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708809200-R1',
  'MAP-MY-MFN-CCU-STEERING-GEAR-COLUMN-8708949500-R1'
)
ORDER BY c.ccu_code, tm.national_tariff_code;

\echo '3. Four research gaps should be RESOLVED'
SELECT field_path, status, resolved_at
FROM audit.missing_data
WHERE field_path LIKE 'customs.pdk2025.omitted_parent_indentation[%'
ORDER BY field_path;

\echo '4. Integrity checks: every result should be zero'
SELECT 'unresolved_parent_indentation_gap' AS check_name, count(*) AS error_count
FROM audit.missing_data
WHERE field_path LIKE 'customs.pdk2025.omitted_parent_indentation[%'
  AND status <> 'RESOLVED'
UNION ALL
SELECT 'active_parent_mapping_not_verified', count(*)
FROM customs.tariff_mapping
WHERE mapping_code IN (
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501521200-R1',
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501522200-R1',
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501523200-R1',
  'MAP-MY-MFN-CCU-TRACTION-MOTOR-8501531000-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708702200-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708703200-R1',
  'MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708809200-R1',
  'MAP-MY-MFN-CCU-STEERING-GEAR-COLUMN-8708949500-R1'
)
  AND (record_status <> 'ACTIVE' OR verification_status <> 'VERIFIED')
UNION ALL
SELECT 'excluded_mapping_not_rejected', count(*)
FROM customs.tariff_mapping
WHERE mapping_code IN (
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708701600-R1',
  'MAP-MY-MFN-CCU-ROAD-WHEEL-8708709700-R1',
  'MAP-MY-MFN-CCU-SHOCK-ABSORBER-STRUT-8708801600-R1'
)
  AND record_status <> 'REJECTED'
UNION ALL
SELECT 'parent_clause_not_verified', count(*)
FROM evidence.source_clause
WHERE clause_code LIKE 'CLAUSE-MY-PDK2025-%-PARENT-INDENTATION'
  AND verification_status <> 'VERIFIED';

