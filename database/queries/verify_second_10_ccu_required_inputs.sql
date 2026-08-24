\pset null '[NULL]'

SELECT c.ccu_code,
       count(r.input_requirement_id) AS required_parameter_count,
       count(*) FILTER (WHERE r.suggested_value IS NOT NULL) AS prefilled_guidance_count
FROM customs.customs_classification_unit c
LEFT JOIN customs.ccu_input_requirement r
  ON r.ccu_id = c.ccu_id AND r.record_status = 'ACTIVE'
WHERE c.ccu_id::text LIKE '64100000-%'
GROUP BY c.ccu_code
ORDER BY c.ccu_code;

SELECT count(*) AS nonempty_enterprise_values
FROM enterprise.part_ccu_input_value value_slot
JOIN enterprise.enterprise_part_ccu_link link
  ON link.part_ccu_link_id = value_slot.part_ccu_link_id
WHERE link.ccu_id::text LIKE '64100000-%'
  AND value_slot.value_payload IS NOT NULL;

