BEGIN;

CREATE OR REPLACE FUNCTION enterprise.set_part_ccu_input_value(
  p_part_ccu_link_id uuid,
  p_field_path text,
  p_value_payload jsonb,
  p_provided_by text,
  p_evidence_refs jsonb DEFAULT '[]'::jsonb,
  p_notes text DEFAULT NULL,
  p_mark_verified boolean DEFAULT false,
  p_verified_by text DEFAULT NULL,
  p_as_of date DEFAULT current_date
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  requirement_id uuid;
  result_id uuid;
  target_status ref.input_value_status;
BEGIN
  IF p_value_payload IS NULL OR jsonb_typeof(p_value_payload) = 'null' THEN
    RAISE EXCEPTION 'p_value_payload must contain a real enterprise fact'
      USING ERRCODE = '22023';
  END IF;

  IF p_provided_by IS NULL OR btrim(p_provided_by) = '' THEN
    RAISE EXCEPTION 'p_provided_by is required'
      USING ERRCODE = '22023';
  END IF;

  IF jsonb_typeof(p_evidence_refs) <> 'array' THEN
    RAISE EXCEPTION 'p_evidence_refs must be a JSON array'
      USING ERRCODE = '22023';
  END IF;

  IF p_mark_verified
     AND (p_verified_by IS NULL OR btrim(p_verified_by) = '') THEN
    RAISE EXCEPTION 'p_verified_by is required when p_mark_verified is true'
      USING ERRCODE = '22023';
  END IF;

  SELECT requirement.input_requirement_id
  INTO requirement_id
  FROM enterprise.enterprise_part_ccu_link link
  JOIN customs.ccu_input_requirement requirement
    ON requirement.ccu_id = link.ccu_id
   AND requirement.field_path = p_field_path
   AND requirement.record_status = 'ACTIVE'
   AND requirement.effective_from <= p_as_of
   AND (
     requirement.effective_to IS NULL
     OR requirement.effective_to > p_as_of
   )
  WHERE link.part_ccu_link_id = p_part_ccu_link_id
  ORDER BY requirement.version DESC
  LIMIT 1;

  IF requirement_id IS NULL THEN
    RAISE EXCEPTION
      'No active CCU input requirement for link % and field %',
      p_part_ccu_link_id,
      p_field_path
      USING ERRCODE = 'P0002';
  END IF;

  target_status := CASE
    WHEN p_mark_verified THEN 'VERIFIED'::ref.input_value_status
    ELSE 'PROVIDED'::ref.input_value_status
  END;

  INSERT INTO enterprise.part_ccu_input_value (
    part_ccu_link_id,
    input_requirement_id,
    value_payload,
    value_status,
    evidence_refs,
    notes,
    provided_by,
    provided_at,
    verified_by,
    verified_at,
    updated_at
  ) VALUES (
    p_part_ccu_link_id,
    requirement_id,
    p_value_payload,
    target_status,
    p_evidence_refs,
    p_notes,
    p_provided_by,
    now(),
    CASE WHEN p_mark_verified THEN p_verified_by ELSE NULL END,
    CASE WHEN p_mark_verified THEN now() ELSE NULL END,
    now()
  )
  ON CONFLICT (part_ccu_link_id, input_requirement_id) DO UPDATE
  SET
    value_payload = EXCLUDED.value_payload,
    value_status = EXCLUDED.value_status,
    evidence_refs = EXCLUDED.evidence_refs,
    notes = EXCLUDED.notes,
    provided_by = EXCLUDED.provided_by,
    provided_at = EXCLUDED.provided_at,
    verified_by = EXCLUDED.verified_by,
    verified_at = EXCLUDED.verified_at,
    updated_at = now()
  RETURNING part_ccu_input_value_id INTO result_id;

  RETURN result_id;
END
$$;

CREATE OR REPLACE FUNCTION enterprise.clear_part_ccu_input_value(
  p_part_ccu_link_id uuid,
  p_field_path text
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  result_id uuid;
BEGIN
  UPDATE enterprise.part_ccu_input_value value_slot
  SET
    value_payload = NULL,
    value_status = 'EMPTY',
    evidence_refs = '[]'::jsonb,
    notes = NULL,
    provided_by = NULL,
    provided_at = NULL,
    verified_by = NULL,
    verified_at = NULL,
    updated_at = now()
  FROM customs.ccu_input_requirement requirement
  WHERE value_slot.part_ccu_link_id = p_part_ccu_link_id
    AND value_slot.input_requirement_id = requirement.input_requirement_id
    AND requirement.field_path = p_field_path
    AND requirement.record_status = 'ACTIVE'
  RETURNING value_slot.part_ccu_input_value_id INTO result_id;

  IF result_id IS NULL THEN
    RAISE EXCEPTION
      'No input slot for link % and field %',
      p_part_ccu_link_id,
      p_field_path
      USING ERRCODE = 'P0002';
  END IF;

  RETURN result_id;
END
$$;

CREATE OR REPLACE VIEW enterprise.v_part_ccu_input_collection AS
SELECT
  link.part_ccu_link_id,
  part.enterprise_part_id,
  part.enterprise_code,
  part.part_no,
  part.part_name_cn,
  ccu.ccu_id,
  ccu.ccu_code,
  ccu.ccu_name_cn,
  requirement.input_requirement_id,
  requirement.display_order,
  requirement.field_path,
  requirement.field_name_cn,
  requirement.required_at_use,
  requirement.value_type,
  requirement.unit,
  requirement.suggested_value,
  requirement.allowed_values,
  requirement.data_owner,
  requirement.evidence_required,
  value_slot.value_payload,
  COALESCE(
    value_slot.value_status,
    'EMPTY'::ref.input_value_status
  ) AS value_status,
  COALESCE(value_slot.evidence_refs, '[]'::jsonb) AS evidence_refs,
  value_slot.notes,
  value_slot.provided_by,
  value_slot.provided_at,
  value_slot.verified_by,
  value_slot.verified_at,
  CASE
    WHEN NOT requirement.required_at_use THEN true
    WHEN value_slot.value_status NOT IN ('PROVIDED', 'VERIFIED') THEN false
    WHEN value_slot.value_payload IS NULL
      OR jsonb_typeof(value_slot.value_payload) = 'null' THEN false
    WHEN jsonb_typeof(value_slot.value_payload) = 'string'
      AND upper(btrim(value_slot.value_payload #>> '{}')) IN (
        'UNKNOWN',
        'TO_BE_CONFIRMED',
        'PENDING',
        '待确认'
      ) THEN false
    ELSE true
  END AS accepted_for_use
FROM enterprise.enterprise_part_ccu_link link
JOIN enterprise.enterprise_part part
  ON part.enterprise_part_id = link.enterprise_part_id
JOIN customs.customs_classification_unit ccu
  ON ccu.ccu_id = link.ccu_id
JOIN customs.ccu_input_requirement requirement
  ON requirement.ccu_id = link.ccu_id
 AND requirement.record_status = 'ACTIVE'
LEFT JOIN enterprise.part_ccu_input_value value_slot
  ON value_slot.part_ccu_link_id = link.part_ccu_link_id
 AND value_slot.input_requirement_id = requirement.input_requirement_id;

CREATE OR REPLACE VIEW enterprise.v_part_ccu_input_completion AS
SELECT
  collection.part_ccu_link_id,
  collection.enterprise_part_id,
  collection.enterprise_code,
  collection.part_no,
  collection.part_name_cn,
  collection.ccu_code,
  collection.ccu_name_cn,
  count(*) AS parameter_count,
  count(*) FILTER (
    WHERE collection.required_at_use
  ) AS required_count,
  count(*) FILTER (
    WHERE collection.required_at_use
      AND collection.accepted_for_use
  ) AS accepted_required_count,
  count(*) FILTER (
    WHERE collection.required_at_use
      AND NOT collection.accepted_for_use
  ) AS missing_required_count,
  round(
    CASE
      WHEN count(*) FILTER (WHERE collection.required_at_use) = 0
        THEN 1::numeric
      ELSE
        count(*) FILTER (
          WHERE collection.required_at_use
            AND collection.accepted_for_use
        )::numeric
        / count(*) FILTER (WHERE collection.required_at_use)
    END,
    4
  ) AS completion_ratio,
  bool_and(
    NOT collection.required_at_use
    OR collection.accepted_for_use
  ) AS ready_for_use
FROM enterprise.v_part_ccu_input_collection collection
GROUP BY
  collection.part_ccu_link_id,
  collection.enterprise_part_id,
  collection.enterprise_code,
  collection.part_no,
  collection.part_name_cn,
  collection.ccu_code,
  collection.ccu_name_cn;

COMMENT ON VIEW enterprise.v_part_ccu_input_collection IS
  'User-facing collection rows for enterprise facts. suggested_value is displayed as guidance and never treated as a supplied value.';

COMMENT ON VIEW enterprise.v_part_ccu_input_completion IS
  'Per part-to-CCU input completion summary used before classification and calculation.';

COMMIT;
