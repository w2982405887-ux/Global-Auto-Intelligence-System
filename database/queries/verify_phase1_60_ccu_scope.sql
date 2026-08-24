\pset null '[NULL]'

SELECT count(*) AS active_ccu_count
FROM customs.customs_classification_unit
WHERE unit_level='CUSTOMS_CLASSIFICATION_UNIT'
  AND record_status='ACTIVE';

SELECT count(*) AS phase1_new_ccu_count,
       count(*) FILTER (WHERE candidate_count BETWEEN 1 AND 3) AS with_1_to_3_hs6,
       count(*) FILTER (WHERE risk_count=3) AS with_three_risk_tags
FROM (
  SELECT c.ccu_id,
         count(DISTINCT h.candidate_id) AS candidate_count,
         count(DISTINCT r.ccu_risk_tag_id) AS risk_count
  FROM customs.customs_classification_unit c
  JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  LEFT JOIN customs.ccu_risk_tag r ON r.ccu_id=c.ccu_id
  WHERE h.candidate_basis =
    'Phase 1 generic candidate route; national-line selection is conditional.'
  GROUP BY c.ccu_id
) quality;

SELECT c.ccu_code,
       string_agg(DISTINCT h.hs6_code, ', ' ORDER BY h.hs6_code) AS hs6_candidates,
       jsonb_array_length(c.required_input_fields) AS required_field_count
FROM customs.customs_classification_unit c
JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
WHERE h.candidate_basis =
  'Phase 1 generic candidate route; national-line selection is conditional.'
GROUP BY c.ccu_code, c.required_input_fields
ORDER BY c.ccu_code;

