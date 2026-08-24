BEGIN;

DO $$
BEGIN
  CREATE TYPE ref.input_data_type AS ENUM
    ('TEXT', 'NUMBER', 'BOOLEAN', 'ENUM', 'DATE', 'JSON');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
  CREATE TYPE ref.input_value_status AS ENUM
    ('EMPTY', 'PROVIDED', 'VERIFIED', 'REJECTED');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS customs.ccu_input_requirement (
  input_requirement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ccu_id uuid NOT NULL
    REFERENCES customs.customs_classification_unit(ccu_id),
  field_path text NOT NULL,
  field_name_cn text NOT NULL,
  field_name_en text,
  required_at_use boolean NOT NULL DEFAULT true,
  value_type ref.input_data_type NOT NULL,
  unit text,
  suggested_value jsonb,
  allowed_values jsonb NOT NULL DEFAULT '[]'::jsonb,
  data_owner text NOT NULL,
  guidance_cn text,
  classification_impact_cn text,
  evidence_required boolean NOT NULL DEFAULT true,
  display_order integer NOT NULL CHECK (display_order > 0),
  effective_from date NOT NULL,
  effective_to date,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  record_status ref.record_status NOT NULL DEFAULT 'ACTIVE',
  verification_status ref.verification_status NOT NULL DEFAULT 'VERIFIED',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (field_path ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'),
  CHECK (jsonb_typeof(allowed_values) = 'array'),
  CHECK (effective_to IS NULL OR effective_to > effective_from),
  UNIQUE (ccu_id, field_path, version),
  UNIQUE (ccu_id, display_order, version)
);

COMMENT ON TABLE customs.ccu_input_requirement IS
  'CCU-level enterprise input definitions. suggested_value is guidance only and is never copied into an enterprise fact value.';

CREATE TABLE IF NOT EXISTS enterprise.part_ccu_input_value (
  part_ccu_input_value_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  part_ccu_link_id uuid NOT NULL
    REFERENCES enterprise.enterprise_part_ccu_link(part_ccu_link_id)
    ON DELETE CASCADE,
  input_requirement_id uuid NOT NULL
    REFERENCES customs.ccu_input_requirement(input_requirement_id),
  value_payload jsonb,
  value_status ref.input_value_status NOT NULL DEFAULT 'EMPTY',
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  notes text,
  provided_by text,
  provided_at timestamptz,
  verified_by text,
  verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(evidence_refs) = 'array'),
  CHECK (
    (value_status = 'EMPTY' AND value_payload IS NULL)
    OR
    (value_status <> 'EMPTY' AND value_payload IS NOT NULL
      AND jsonb_typeof(value_payload) <> 'null')
  ),
  CHECK ((value_status = 'VERIFIED') = (verified_at IS NOT NULL)),
  UNIQUE (part_ccu_link_id, input_requirement_id)
);

COMMENT ON TABLE enterprise.part_ccu_input_value IS
  'One progressively completed enterprise value slot per part-to-CCU link and CCU requirement. EMPTY rows are valid during research but block input snapshots and calculations when required_at_use is true.';

CREATE INDEX IF NOT EXISTS idx_ccu_input_requirement_active
  ON customs.ccu_input_requirement(ccu_id, record_status, effective_from, effective_to);

CREATE INDEX IF NOT EXISTS idx_part_ccu_input_value_status
  ON enterprise.part_ccu_input_value(part_ccu_link_id, value_status);

CREATE OR REPLACE FUNCTION enterprise.validate_ccu_input_value_type()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  requirement_record customs.ccu_input_requirement%ROWTYPE;
  payload_type text;
  enum_value text;
BEGIN
  SELECT *
  INTO requirement_record
  FROM customs.ccu_input_requirement
  WHERE input_requirement_id = NEW.input_requirement_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Unknown CCU input requirement: %',
      NEW.input_requirement_id USING ERRCODE = '23503';
  END IF;

  IF NEW.value_status = 'EMPTY' THEN
    NEW.value_payload := NULL;
    NEW.provided_by := NULL;
    NEW.provided_at := NULL;
    NEW.verified_by := NULL;
    NEW.verified_at := NULL;
    NEW.updated_at := now();
    RETURN NEW;
  END IF;

  payload_type := jsonb_typeof(NEW.value_payload);

  IF requirement_record.value_type = 'TEXT'
     AND (payload_type <> 'string' OR btrim(NEW.value_payload #>> '{}') = '') THEN
    RAISE EXCEPTION 'Field % requires a non-empty JSON string',
      requirement_record.field_path USING ERRCODE = '22023';
  ELSIF requirement_record.value_type = 'NUMBER'
        AND payload_type <> 'number' THEN
    RAISE EXCEPTION 'Field % requires a JSON number',
      requirement_record.field_path USING ERRCODE = '22023';
  ELSIF requirement_record.value_type = 'BOOLEAN'
        AND payload_type <> 'boolean' THEN
    RAISE EXCEPTION 'Field % requires a JSON boolean',
      requirement_record.field_path USING ERRCODE = '22023';
  ELSIF requirement_record.value_type = 'ENUM' THEN
    IF payload_type <> 'string' THEN
      RAISE EXCEPTION 'Field % requires a JSON string enum',
        requirement_record.field_path USING ERRCODE = '22023';
    END IF;
    enum_value := NEW.value_payload #>> '{}';
    IF jsonb_array_length(requirement_record.allowed_values) > 0
       AND NOT requirement_record.allowed_values ? enum_value THEN
      RAISE EXCEPTION 'Field % value % is not in allowed_values',
        requirement_record.field_path, enum_value USING ERRCODE = '22023';
    END IF;
  ELSIF requirement_record.value_type = 'DATE'
        AND (
          payload_type <> 'string'
          OR (NEW.value_payload #>> '{}') !~
             '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        ) THEN
    RAISE EXCEPTION 'Field % requires a YYYY-MM-DD JSON string',
      requirement_record.field_path USING ERRCODE = '22023';
  END IF;

  IF NEW.provided_at IS NULL THEN
    NEW.provided_at := now();
  END IF;

  IF NEW.value_status = 'VERIFIED' THEN
    IF NEW.verified_by IS NULL OR btrim(NEW.verified_by) = '' THEN
      RAISE EXCEPTION 'VERIFIED field % requires verified_by',
        requirement_record.field_path USING ERRCODE = '23514';
    END IF;
    IF NEW.verified_at IS NULL THEN
      NEW.verified_at := now();
    END IF;
  ELSE
    NEW.verified_by := NULL;
    NEW.verified_at := NULL;
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_validate_ccu_input_value
  ON enterprise.part_ccu_input_value;
CREATE TRIGGER trg_validate_ccu_input_value
BEFORE INSERT OR UPDATE OF
  input_requirement_id, value_payload, value_status, verified_by, verified_at
ON enterprise.part_ccu_input_value
FOR EACH ROW
EXECUTE FUNCTION enterprise.validate_ccu_input_value_type();

CREATE OR REPLACE FUNCTION enterprise.sync_part_ccu_input_slots(
  p_part_ccu_link_id uuid
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
  inserted_count integer;
BEGIN
  INSERT INTO enterprise.part_ccu_input_value (
    part_ccu_link_id,
    input_requirement_id,
    value_payload,
    value_status
  )
  SELECT
    link.part_ccu_link_id,
    requirement.input_requirement_id,
    NULL,
    'EMPTY'::ref.input_value_status
  FROM enterprise.enterprise_part_ccu_link link
  JOIN customs.ccu_input_requirement requirement
    ON requirement.ccu_id = link.ccu_id
   AND requirement.record_status = 'ACTIVE'
   AND requirement.effective_from <= link.effective_from
   AND (
     requirement.effective_to IS NULL
     OR requirement.effective_to > link.effective_from
   )
  WHERE link.part_ccu_link_id = p_part_ccu_link_id
  ON CONFLICT (part_ccu_link_id, input_requirement_id) DO NOTHING;

  GET DIAGNOSTICS inserted_count = ROW_COUNT;
  RETURN inserted_count;
END
$$;

CREATE OR REPLACE FUNCTION enterprise.sync_part_ccu_input_slots_trigger()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM enterprise.sync_part_ccu_input_slots(NEW.part_ccu_link_id);
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_sync_part_ccu_input_slots
  ON enterprise.enterprise_part_ccu_link;
CREATE TRIGGER trg_sync_part_ccu_input_slots
AFTER INSERT OR UPDATE OF ccu_id, effective_from, effective_to
ON enterprise.enterprise_part_ccu_link
FOR EACH ROW
EXECUTE FUNCTION enterprise.sync_part_ccu_input_slots_trigger();

CREATE OR REPLACE FUNCTION enterprise.backfill_ccu_requirement_slots_trigger()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.record_status = 'ACTIVE' THEN
    INSERT INTO enterprise.part_ccu_input_value (
      part_ccu_link_id,
      input_requirement_id,
      value_payload,
      value_status
    )
    SELECT
      link.part_ccu_link_id,
      NEW.input_requirement_id,
      NULL,
      'EMPTY'::ref.input_value_status
    FROM enterprise.enterprise_part_ccu_link link
    WHERE link.ccu_id = NEW.ccu_id
      AND NEW.effective_from <= link.effective_from
      AND (NEW.effective_to IS NULL OR NEW.effective_to > link.effective_from)
    ON CONFLICT (part_ccu_link_id, input_requirement_id) DO NOTHING;
  END IF;
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_backfill_ccu_requirement_slots
  ON customs.ccu_input_requirement;
CREATE TRIGGER trg_backfill_ccu_requirement_slots
AFTER INSERT OR UPDATE OF record_status, effective_from, effective_to
ON customs.ccu_input_requirement
FOR EACH ROW
EXECUTE FUNCTION enterprise.backfill_ccu_requirement_slots_trigger();

CREATE OR REPLACE FUNCTION enterprise.list_missing_required_ccu_inputs(
  p_part_ccu_link_id uuid,
  p_as_of date DEFAULT current_date
)
RETURNS TABLE (
  field_path text,
  field_name_cn text,
  data_owner text,
  missing_reason text
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    requirement.field_path,
    requirement.field_name_cn,
    requirement.data_owner,
    CASE
      WHEN value_slot.part_ccu_input_value_id IS NULL THEN 'SLOT_NOT_CREATED'
      WHEN value_slot.value_payload IS NULL
        OR jsonb_typeof(value_slot.value_payload) = 'null' THEN 'VALUE_EMPTY'
      WHEN jsonb_typeof(value_slot.value_payload) = 'string'
        AND upper(btrim(value_slot.value_payload #>> '{}')) IN (
          'UNKNOWN',
          'TO_BE_CONFIRMED',
          'PENDING',
          '待确认'
        ) THEN 'VALUE_UNRESOLVED'
      ELSE 'VALUE_NOT_ACCEPTED'
    END
  FROM enterprise.enterprise_part_ccu_link link
  JOIN customs.ccu_input_requirement requirement
    ON requirement.ccu_id = link.ccu_id
   AND requirement.required_at_use
   AND requirement.record_status = 'ACTIVE'
   AND requirement.effective_from <= p_as_of
   AND (
     requirement.effective_to IS NULL
     OR requirement.effective_to > p_as_of
   )
  LEFT JOIN enterprise.part_ccu_input_value value_slot
    ON value_slot.part_ccu_link_id = link.part_ccu_link_id
   AND value_slot.input_requirement_id = requirement.input_requirement_id
  WHERE link.part_ccu_link_id = p_part_ccu_link_id
    AND (
      value_slot.part_ccu_input_value_id IS NULL
      OR value_slot.value_payload IS NULL
      OR jsonb_typeof(value_slot.value_payload) = 'null'
      OR value_slot.value_status NOT IN ('PROVIDED', 'VERIFIED')
      OR (
        jsonb_typeof(value_slot.value_payload) = 'string'
        AND upper(btrim(value_slot.value_payload #>> '{}')) IN (
          'UNKNOWN',
          'TO_BE_CONFIRMED',
          'PENDING',
          '待确认'
        )
      )
    )
  ORDER BY requirement.display_order
$$;

CREATE OR REPLACE FUNCTION enterprise.assert_part_ccu_inputs_ready(
  p_part_ccu_link_id uuid,
  p_as_of date DEFAULT current_date
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  missing_paths text;
BEGIN
  SELECT string_agg(missing.field_path, ', ' ORDER BY missing.field_path)
  INTO missing_paths
  FROM enterprise.list_missing_required_ccu_inputs(
    p_part_ccu_link_id,
    p_as_of
  ) missing;

  IF missing_paths IS NOT NULL THEN
    RAISE EXCEPTION
      'Required enterprise CCU inputs are missing for link %: %',
      p_part_ccu_link_id,
      missing_paths
      USING ERRCODE = '23514',
            HINT = 'Fill enterprise.part_ccu_input_value and set value_status to PROVIDED or VERIFIED before classification or calculation.';
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION enterprise.list_missing_required_bom_inputs(
  p_bom_version_id uuid,
  p_as_of date DEFAULT current_date
)
RETURNS TABLE (
  enterprise_part_id uuid,
  part_no text,
  ccu_code text,
  field_path text,
  field_name_cn text,
  data_owner text,
  missing_reason text
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    part.enterprise_part_id,
    part.part_no,
    ccu.ccu_code,
    missing.field_path,
    missing.field_name_cn,
    missing.data_owner,
    missing.missing_reason
  FROM enterprise.bom_line bom_line
  JOIN enterprise.enterprise_part part
    ON part.enterprise_part_id = bom_line.enterprise_part_id
  JOIN enterprise.enterprise_part_ccu_link link
    ON link.enterprise_part_id = part.enterprise_part_id
   AND link.effective_from <= p_as_of
   AND (link.effective_to IS NULL OR link.effective_to > p_as_of)
  JOIN customs.customs_classification_unit ccu
    ON ccu.ccu_id = link.ccu_id
  CROSS JOIN LATERAL enterprise.list_missing_required_ccu_inputs(
    link.part_ccu_link_id,
    p_as_of
  ) missing
  WHERE bom_line.bom_version_id = p_bom_version_id
    AND bom_line.included_flag
  ORDER BY part.part_no, ccu.ccu_code, missing.field_path
$$;

CREATE OR REPLACE FUNCTION enterprise.assert_bom_inputs_ready(
  p_bom_version_id uuid,
  p_as_of date DEFAULT current_date
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  missing_count integer;
  sample_paths text;
BEGIN
  SELECT
    count(*),
    string_agg(
      missing.part_no || ':' || missing.ccu_code || ':' || missing.field_path,
      ', '
      ORDER BY missing.part_no, missing.ccu_code, missing.field_path
    ) FILTER (WHERE missing.sample_rank <= 10)
  INTO missing_count, sample_paths
  FROM (
    SELECT
      result.*,
      row_number() OVER (
        ORDER BY result.part_no, result.ccu_code, result.field_path
      ) AS sample_rank
    FROM enterprise.list_missing_required_bom_inputs(
      p_bom_version_id,
      p_as_of
    ) result
  ) missing;

  IF missing_count > 0 THEN
    RAISE EXCEPTION
      'BOM % has % missing required enterprise CCU inputs. First fields: %',
      p_bom_version_id,
      missing_count,
      sample_paths
      USING ERRCODE = '23514',
            HINT = 'Complete the empty enterprise input slots before creating an input snapshot or calculation run.';
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION enterprise.block_incomplete_input_snapshot()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  scenario_bom_version_id uuid;
  scenario_import_date date;
BEGIN
  SELECT scenario.bom_version_id, scenario.import_date
  INTO scenario_bom_version_id, scenario_import_date
  FROM enterprise.scenario_input scenario
  WHERE scenario.scenario_input_id = NEW.scenario_input_id;

  IF scenario_bom_version_id IS NOT NULL THEN
    PERFORM enterprise.assert_bom_inputs_ready(
      scenario_bom_version_id,
      scenario_import_date
    );
  END IF;

  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_block_incomplete_input_snapshot
  ON enterprise.input_snapshot;
CREATE TRIGGER trg_block_incomplete_input_snapshot
BEFORE INSERT OR UPDATE OF scenario_input_id, payload
ON enterprise.input_snapshot
FOR EACH ROW
EXECUTE FUNCTION enterprise.block_incomplete_input_snapshot();

COMMIT;
