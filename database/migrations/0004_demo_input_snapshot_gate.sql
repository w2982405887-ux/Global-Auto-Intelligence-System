BEGIN;

-- Keep the production input gate strict while permitting a visibly labelled,
-- non-operational Phase 1 demo snapshot. A DEMO snapshot is allowed only when:
--   1. the scenario code starts with DEMO-;
--   2. both scenario payload and snapshot payload say demo_only=true;
--   3. both payloads explicitly say enterprise_ccu_fields_complete=false;
--   4. both payloads explicitly say operational_use_permitted=false.
-- Any real or ambiguously labelled snapshot continues through the original
-- required-enterprise-input assertion.

CREATE OR REPLACE FUNCTION enterprise.block_incomplete_input_snapshot()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  scenario_bom_version_id uuid;
  scenario_import_date date;
  scenario_code_value text;
  scenario_payload jsonb;
  is_strict_demo boolean;
BEGIN
  SELECT
    scenario.bom_version_id,
    scenario.import_date,
    scenario.scenario_code,
    scenario.input_payload
  INTO
    scenario_bom_version_id,
    scenario_import_date,
    scenario_code_value,
    scenario_payload
  FROM enterprise.scenario_input scenario
  WHERE scenario.scenario_input_id = NEW.scenario_input_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Unknown scenario_input_id: %', NEW.scenario_input_id
      USING ERRCODE = '23503';
  END IF;

  is_strict_demo :=
    scenario_code_value LIKE 'DEMO-%'
    AND COALESCE((scenario_payload->>'demo_only')::boolean, false)
    AND COALESCE((NEW.payload->>'demo_only')::boolean, false)
    AND NOT COALESCE(
      (scenario_payload->>'enterprise_ccu_fields_complete')::boolean,
      true
    )
    AND NOT COALESCE(
      (NEW.payload->>'enterprise_ccu_fields_complete')::boolean,
      true
    )
    AND NOT COALESCE(
      (scenario_payload->>'operational_use_permitted')::boolean,
      true
    )
    AND NOT COALESCE(
      (NEW.payload->>'operational_use_permitted')::boolean,
      true
    );

  IF scenario_bom_version_id IS NOT NULL AND NOT is_strict_demo THEN
    PERFORM enterprise.assert_bom_inputs_ready(
      scenario_bom_version_id,
      scenario_import_date
    );
  END IF;

  RETURN NEW;
END
$$;

COMMENT ON FUNCTION enterprise.block_incomplete_input_snapshot() IS
  'Blocks incomplete production snapshots. Allows only explicitly non-operational DEMO-* snapshots with enterprise_ccu_fields_complete=false and operational_use_permitted=false.';

COMMIT;
