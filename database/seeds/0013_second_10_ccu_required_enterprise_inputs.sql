BEGIN;

-- Materialise the second-batch CCU required_input_fields as use-time gates.
-- No enterprise value is populated here: linked parts receive EMPTY slots.
WITH expanded AS (
  SELECT
    c.ccu_id,
    c.ccu_code,
    f.field_path,
    f.ordinality::integer AS display_order
  FROM customs.customs_classification_unit c
  CROSS JOIN LATERAL jsonb_array_elements_text(c.required_input_fields)
    WITH ORDINALITY AS f(field_path, ordinality)
  WHERE c.ccu_id::text LIKE '64100000-%'
),
typed AS (
  SELECT *,
    CASE
      WHEN field_path ~ '(_kw|_v|_count|_cc_per_rev)$'
        THEN 'NUMBER'::ref.input_data_type
      WHEN field_path ~ '(includes_|integrated_|complete_|shaped_|assembled_|driving_)'
        THEN 'BOOLEAN'::ref.input_data_type
      ELSE 'TEXT'::ref.input_data_type
    END AS value_type,
    CASE
      WHEN field_path ~ '_kw$' THEN 'kW'
      WHEN field_path ~ '_v$' THEN 'V'
      WHEN field_path ~ '_cc_per_rev$' THEN 'cc/rev'
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
SELECT
  ccu_id, field_path, field_path, field_path, true,
  value_type, unit, NULL, '[]'::jsonb,
  CASE WHEN field_path LIKE 'shipment.%' THEN '物流包装' ELSE '企业工程' END,
  '在实际企业料号关联本CCU并执行归类或税负计算时填写；当前数据库保留空位。',
  '缺失时不得将候选税号提升为最终税号，也不得进入正式综合税率计算。',
  true, display_order, DATE '2025-11-01', 1, 'ACTIVE', 'VERIFIED'
FROM typed
ON CONFLICT (ccu_id, field_path, version) DO UPDATE
SET required_at_use = true,
    value_type = EXCLUDED.value_type,
    unit = EXCLUDED.unit,
    suggested_value = NULL,
    allowed_values = EXCLUDED.allowed_values,
    data_owner = EXCLUDED.data_owner,
    guidance_cn = EXCLUDED.guidance_cn,
    classification_impact_cn = EXCLUDED.classification_impact_cn,
    evidence_required = true,
    display_order = EXCLUDED.display_order,
    record_status = 'ACTIVE',
    verification_status = 'VERIFIED',
    updated_at = now();

DO $$
DECLARE link_record record;
BEGIN
  FOR link_record IN
    SELECT link.part_ccu_link_id
    FROM enterprise.enterprise_part_ccu_link link
    JOIN customs.customs_classification_unit c ON c.ccu_id = link.ccu_id
    WHERE c.ccu_id::text LIKE '64100000-%'
  LOOP
    PERFORM enterprise.sync_part_ccu_input_slots(link_record.part_ccu_link_id);
  END LOOP;
END
$$;

COMMIT;
