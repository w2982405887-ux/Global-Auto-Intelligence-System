\pset null '[NULL]'

SELECT c.ccu_code, h.hs6_code, m.national_tariff_code,
       m.tariff_description, m.duty_rate,
       m.additional_measure #>> '{sst,displayed_rate}' AS sst_display_rate,
       m.additional_measure #>> '{portal_import_control,result}' AS control_observation,
       m.verification_status
FROM customs.customs_classification_unit c
JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
LEFT JOIN customs.tariff_mapping m
  ON m.candidate_id=h.candidate_id
 AND m.origin_regime='MFN'
 AND m.tariff_version='PDK 2025'
 AND m.record_status='ACTIVE'
WHERE c.ccu_id::text LIKE '64100000-%'
ORDER BY c.ccu_code, m.national_tariff_code;

SELECT verification_status, count(*) AS mapping_count
FROM customs.tariff_mapping
WHERE mapping_code LIKE 'MAP-MY-PDK2025-MFN-%'
  AND candidate_id::text LIKE '65100000-%'
GROUP BY verification_status
ORDER BY verification_status;

SELECT count(*) FILTER (WHERE d.content_sha256 IS NULL) AS source_without_hash,
       count(*) AS source_count
FROM evidence.source_document d
WHERE d.source_code LIKE 'SRC-MY-JKDM-PDK2025-%-20260729';

