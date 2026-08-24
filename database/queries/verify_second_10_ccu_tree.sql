\pset null '[NULL]'

SELECT unit_level, count(*) AS second_batch_count
FROM customs.customs_classification_unit
WHERE ccu_id::text LIKE '61100000-%'
   OR ccu_id::text LIKE '62100000-%'
   OR ccu_id::text LIKE '63100000-%'
   OR ccu_id::text LIKE '64100000-%'
GROUP BY unit_level
ORDER BY unit_level;

SELECT c.ccu_code, c.ccu_name_cn, h.hs6_code,
       h.candidate_rank, h.verification_status,
       jsonb_array_length(c.required_input_fields) AS required_field_count
FROM customs.customs_classification_unit c
JOIN customs.ccu_candidate_hs h ON h.ccu_id = c.ccu_id
WHERE c.ccu_id::text LIKE '64100000-%'
ORDER BY c.ccu_code, h.candidate_rank;

SELECT risk_tag_type, count(*) AS tag_count
FROM customs.ccu_risk_tag
WHERE ccu_id::text LIKE '64100000-%'
GROUP BY risk_tag_type
ORDER BY risk_tag_type;

