\pset null '[NULL]'

WITH target AS (
  SELECT DISTINCT c.ccu_id
  FROM customs.customs_classification_unit c
  JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  WHERE h.candidate_basis =
    'Phase 1 generic candidate route; national-line selection is conditional.'
)
SELECT count(DISTINCT r.ccu_id) AS ccu_with_input_gate,
       count(*) AS requirement_count,
       count(*) FILTER (WHERE r.required_at_use) AS required_at_use_count,
       count(*) FILTER (WHERE r.suggested_value IS NOT NULL) AS prefilled_count
FROM customs.ccu_input_requirement r
JOIN target t ON t.ccu_id=r.ccu_id
WHERE r.record_status='ACTIVE';

WITH target AS (
  SELECT DISTINCT c.ccu_id
  FROM customs.customs_classification_unit c
  JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  WHERE h.candidate_basis =
    'Phase 1 generic candidate route; national-line selection is conditional.'
)
SELECT count(*) AS nonempty_enterprise_value_count
FROM enterprise.part_ccu_input_value value_slot
JOIN enterprise.enterprise_part_ccu_link link
  ON link.part_ccu_link_id=value_slot.part_ccu_link_id
JOIN target t ON t.ccu_id=link.ccu_id
WHERE value_slot.value_payload IS NOT NULL;

