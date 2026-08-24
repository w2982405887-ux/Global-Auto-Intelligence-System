\pset null '[NULL]'
\x off

WITH RECURSIVE tree AS (
  SELECT ccu_id, ccu_code, ccu_name_cn, unit_level, parent_ccu_id,
         1 AS depth, ccu_code::text AS path
  FROM customs.customs_classification_unit
  WHERE parent_ccu_id IS NULL
    AND ccu_code IN ('SYS-ELECTRIFIED-POWERTRAIN','SYS-BODY','SYS-CHASSIS')
  UNION ALL
  SELECT c.ccu_id, c.ccu_code, c.ccu_name_cn, c.unit_level,
         c.parent_ccu_id, t.depth + 1, t.path || ' > ' || c.ccu_code
  FROM customs.customs_classification_unit c
  JOIN tree t ON t.ccu_id = c.parent_ccu_id
)
SELECT depth, unit_level, ccu_code, ccu_name_cn, path
FROM tree
ORDER BY path;

SELECT
  c.ccu_code,
  c.ccu_name_cn,
  count(DISTINCT h.candidate_id) AS candidate_hs_count,
  string_agg(DISTINCT h.hs6_code, ', ' ORDER BY h.hs6_code) AS candidate_hs6,
  count(DISTINCT r.risk_tag_type) AS risk_tag_count,
  jsonb_array_length(c.required_input_fields) AS required_input_count
FROM customs.customs_classification_unit c
LEFT JOIN customs.ccu_candidate_hs h ON h.ccu_id = c.ccu_id
LEFT JOIN customs.ccu_risk_tag r ON r.ccu_id = c.ccu_id
WHERE c.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'
  AND c.ccu_code IN (
    'CCU-HV-BATTERY-PACK','CCU-TRACTION-MOTOR','CCU-TRACTION-INVERTER',
    'CCU-ONBOARD-CHARGER','CCU-DC-DC-CONVERTER',
    'CCU-PASSENGER-BODY-SHELL','CCU-ROAD-WHEEL','CCU-FOUNDATION-BRAKE',
    'CCU-STEERING-GEAR-COLUMN','CCU-SHOCK-ABSORBER-STRUT'
  )
GROUP BY c.ccu_code, c.ccu_name_cn, c.required_input_fields
ORDER BY c.ccu_code;

SELECT
  count(*) FILTER (WHERE unit_level = 'VEHICLE_SYSTEM') AS vehicle_systems,
  count(*) FILTER (WHERE unit_level = 'ASSEMBLY') AS assemblies,
  count(*) FILTER (WHERE unit_level = 'SUBASSEMBLY') AS subassemblies,
  count(*) FILTER (WHERE unit_level = 'CUSTOMS_CLASSIFICATION_UNIT') AS classification_units
FROM customs.customs_classification_unit
WHERE ccu_code LIKE 'SYS-%'
   OR ccu_code LIKE 'ASM-%'
   OR ccu_code LIKE 'SUBASM-%'
   OR ccu_code IN (
     'CCU-HV-BATTERY-PACK','CCU-TRACTION-MOTOR','CCU-TRACTION-INVERTER',
     'CCU-ONBOARD-CHARGER','CCU-DC-DC-CONVERTER',
     'CCU-PASSENGER-BODY-SHELL','CCU-ROAD-WHEEL','CCU-FOUNDATION-BRAKE',
     'CCU-STEERING-GEAR-COLUMN','CCU-SHOCK-ABSORBER-STRUT'
   );

SELECT priority, status, count(*) AS item_count
FROM audit.missing_data
WHERE field_path LIKE 'customs.tariff_mapping[CCU-%].national_tariff_code'
GROUP BY priority, status
ORDER BY priority, status;
