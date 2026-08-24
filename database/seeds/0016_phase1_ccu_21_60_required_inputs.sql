BEGIN;

WITH target_ccus AS (
  SELECT DISTINCT c.ccu_id, c.required_input_fields
  FROM customs.customs_classification_unit c
  JOIN customs.ccu_candidate_hs h ON h.ccu_id=c.ccu_id
  WHERE h.candidate_basis =
    'Phase 1 generic candidate route; national-line selection is conditional.'
),
expanded AS (
  SELECT t.ccu_id, f.field_path, f.ordinality::integer AS display_order
  FROM target_ccus t
  CROSS JOIN LATERAL jsonb_array_elements_text(t.required_input_fields)
    WITH ORDINALITY f(field_path, ordinality)
),
typed AS (
  SELECT *,
    CASE
      WHEN field_path ~ '(_cc|_kw|_w|_v|_mm|_m3h)$'
        THEN 'NUMBER'::ref.input_data_type
      WHEN field_path ~ '(complete_|_confirmed$|included|integrated|electrically_|engine_mounted|with_|pneumatic$|mounted_|radio_receiver|function$)'
        AND field_path NOT LIKE 'part.primary_function'
        THEN 'BOOLEAN'::ref.input_data_type
      ELSE 'TEXT'::ref.input_data_type
    END AS value_type,
    CASE
      WHEN field_path ~ '_cc$' THEN 'cc'
      WHEN field_path ~ '_kw$' THEN 'kW'
      WHEN field_path ~ '_w$' THEN 'W'
      WHEN field_path ~ '_v$' THEN 'V'
      WHEN field_path ~ '_mm$' THEN 'mm'
      WHEN field_path ~ '_m3h$' THEN 'm3/h'
      ELSE NULL
    END AS unit
  FROM expanded
)
INSERT INTO customs.ccu_input_requirement (
  ccu_id, field_path, field_name_cn, field_name_en, required_at_use,
  value_type, unit, suggested_value, allowed_values, data_owner,
  guidance_cn, classification_impact_cn, evidence_required, display_order,
  effective_from, version, record_status, verification_status
)
SELECT ccu_id, field_path, field_path, field_path, true,
       value_type, unit, NULL, '[]'::jsonb,
       CASE WHEN field_path LIKE 'shipment.%' THEN '物流包装'
            WHEN field_path LIKE 'vehicle.%' THEN '车型工程'
            ELSE '企业工程' END,
       '实际企业料号关联本CCU并执行归类或税负计算时填写；数据库当前仅保留空位。',
       '缺失时不得确认最终税号、FTA适用性或正式综合税率。',
       true, display_order, DATE '2025-11-01', 1,
       'ACTIVE', 'VERIFIED'
FROM typed
ON CONFLICT (ccu_id, field_path, version) DO UPDATE
SET required_at_use=true,
    value_type=EXCLUDED.value_type,
    unit=EXCLUDED.unit,
    suggested_value=NULL,
    allowed_values='[]'::jsonb,
    data_owner=EXCLUDED.data_owner,
    guidance_cn=EXCLUDED.guidance_cn,
    classification_impact_cn=EXCLUDED.classification_impact_cn,
    evidence_required=true,
    display_order=EXCLUDED.display_order,
    record_status='ACTIVE',
    verification_status='VERIFIED',
    updated_at=now();

DO $$
DECLARE link_record record;
BEGIN
  FOR link_record IN
    SELECT DISTINCT link.part_ccu_link_id
    FROM enterprise.enterprise_part_ccu_link link
    JOIN customs.ccu_candidate_hs candidate
      ON candidate.ccu_id=link.ccu_id
     AND candidate.candidate_basis =
       'Phase 1 generic candidate route; national-line selection is conditional.'
  LOOP
    PERFORM enterprise.sync_part_ccu_input_slots(link_record.part_ccu_link_id);
  END LOOP;
END
$$;

COMMIT;
