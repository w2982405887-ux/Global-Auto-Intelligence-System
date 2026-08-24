--
-- PostgreSQL database dump
--

\restrict CJmHFGJKa7jn5Bouvi7QyCT37AdfWucCVe3XxhLRui1CbCh4db18KYyitaN60Le

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: ai; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA ai;


--
-- Name: assistant; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA assistant;


--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA audit;


--
-- Name: calc; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA calc;


--
-- Name: customs; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA customs;


--
-- Name: enterprise; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA enterprise;


--
-- Name: evidence; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA evidence;


--
-- Name: iam; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA iam;


--
-- Name: platform; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA platform;


--
-- Name: ref; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA ref;


--
-- Name: rules; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA rules;


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: invitation_status; Type: TYPE; Schema: iam; Owner: -
--

CREATE TYPE iam.invitation_status AS ENUM (
    'PENDING',
    'ACCEPTED',
    'REVOKED',
    'EXPIRED'
);


--
-- Name: membership_status; Type: TYPE; Schema: iam; Owner: -
--

CREATE TYPE iam.membership_status AS ENUM (
    'INVITED',
    'ACTIVE',
    'SUSPENDED',
    'REMOVED'
);


--
-- Name: role_scope; Type: TYPE; Schema: iam; Owner: -
--

CREATE TYPE iam.role_scope AS ENUM (
    'SYSTEM',
    'ORGANIZATION'
);


--
-- Name: user_status; Type: TYPE; Schema: iam; Owner: -
--

CREATE TYPE iam.user_status AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'DELETED'
);


--
-- Name: assembly_state; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.assembly_state AS ENUM (
    'COMPLETE',
    'INCOMPLETE',
    'UNASSEMBLED',
    'DISASSEMBLED',
    'MIXED',
    'UNKNOWN'
);


--
-- Name: calculation_status; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.calculation_status AS ENUM (
    'QUEUED',
    'RUNNING',
    'COMPLETE',
    'PARTIAL',
    'BLOCKED',
    'FAILED',
    'SUPERSEDED'
);


--
-- Name: ccu_unit_level; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.ccu_unit_level AS ENUM (
    'VEHICLE_SYSTEM',
    'ASSEMBLY',
    'SUBASSEMBLY',
    'CUSTOMS_CLASSIFICATION_UNIT'
);


--
-- Name: completeness; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.completeness AS ENUM (
    'COMPLETE',
    'PARTIAL',
    'BLOCKED'
);


--
-- Name: data_ownership; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.data_ownership AS ENUM (
    'PUBLIC',
    'ENTERPRISE',
    'MIXED'
);


--
-- Name: decision_step_type; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.decision_step_type AS ENUM (
    'INPUT_VALIDATION',
    'SCENARIO_SELECTION',
    'CLASSIFICATION',
    'RULE_SELECTION',
    'ELIGIBILITY',
    'CALCULATION',
    'RISK_ASSESSMENT',
    'OUTPUT'
);


--
-- Name: import_mode; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.import_mode AS ENUM (
    'CBU',
    'DKD',
    'SKD',
    'CKD',
    'PARTS',
    'LOCAL_PRODUCTION'
);


--
-- Name: input_data_type; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.input_data_type AS ENUM (
    'TEXT',
    'NUMBER',
    'BOOLEAN',
    'ENUM',
    'DATE',
    'JSON'
);


--
-- Name: input_value_status; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.input_value_status AS ENUM (
    'EMPTY',
    'PROVIDED',
    'VERIFIED',
    'REJECTED'
);


--
-- Name: missing_data_kind; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.missing_data_kind AS ENUM (
    'PUBLIC_RESEARCH',
    'ENTERPRISE_INPUT',
    'AUTHORITY_CONFIRMATION',
    'ADVANCE_RULING',
    'OFFICIAL_NOT_FOUND'
);


--
-- Name: missing_data_status; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.missing_data_status AS ENUM (
    'OPEN',
    'IN_RESEARCH',
    'WAITING_ENTERPRISE',
    'WAITING_AUTHORITY',
    'RESOLVED',
    'WAIVED'
);


--
-- Name: official_status; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.official_status AS ENUM (
    'OFFICIAL',
    'OFFICIAL_ARCHIVE',
    'SECONDARY',
    'ENTERPRISE_INTERNAL',
    'UNKNOWN'
);


--
-- Name: origin_regime; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.origin_regime AS ENUM (
    'MFN',
    'FTA',
    'PREFERENTIAL_PROGRAM',
    'ENTERPRISE_EXEMPTION',
    'UNKNOWN'
);


--
-- Name: powertrain; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.powertrain AS ENUM (
    'ICE_GASOLINE',
    'ICE_DIESEL',
    'HEV',
    'PHEV',
    'EREV',
    'BEV',
    'FCEV',
    'OTHER'
);


--
-- Name: priority; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.priority AS ENUM (
    'P0',
    'P1',
    'P2',
    'P3'
);


--
-- Name: rate_type; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.rate_type AS ENUM (
    'AD_VALOREM',
    'SPECIFIC',
    'COMPOUND',
    'FORMULA',
    'ZERO',
    'NOT_APPLICABLE',
    'UNKNOWN'
);


--
-- Name: record_status; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.record_status AS ENUM (
    'DRAFT',
    'ACTIVE',
    'SUSPENDED',
    'SUPERSEDED',
    'EXPIRED',
    'REJECTED'
);


--
-- Name: requirement_type; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.requirement_type AS ENUM (
    'MANDATORY',
    'INCENTIVE_ONLY',
    'RULING_RECOMMENDED'
);


--
-- Name: review_decision; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.review_decision AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'NEEDS_MORE_EVIDENCE'
);


--
-- Name: risk_level; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.risk_level AS ENUM (
    'NONE',
    'LOW',
    'MEDIUM',
    'HIGH',
    'BLOCKING'
);


--
-- Name: risk_tag_type; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.risk_tag_type AS ENUM (
    'GRI_2A',
    'HEADING_8708_EXCLUSION',
    'AP_REGULATORY'
);


--
-- Name: rule_domain; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.rule_domain AS ENUM (
    'CUSTOMS_CLASSIFICATION',
    'IMPORT_DUTY',
    'SALES_TAX',
    'EXCISE',
    'VAT_GST',
    'FTA',
    'APPROVAL',
    'QUOTA',
    'LOCALIZATION',
    'INCENTIVE',
    'VALUATION',
    'OTHER'
);


--
-- Name: source_type; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.source_type AS ENUM (
    'LAW',
    'REGULATION',
    'GAZETTE',
    'TARIFF_SCHEDULE',
    'OFFICIAL_GUIDE',
    'OFFICIAL_PORTAL',
    'BUDGET_DOCUMENT',
    'ADVANCE_RULING',
    'ENTERPRISE_APPROVAL',
    'TREATY',
    'OTHER'
);


--
-- Name: verification_status; Type: TYPE; Schema: ref; Owner: -
--

CREATE TYPE ref.verification_status AS ENUM (
    'UNVERIFIED',
    'CANDIDATE',
    'VERIFIED',
    'RULING_CONFIRMED'
);


--
-- Name: touch_conversation_updated_at(); Type: FUNCTION; Schema: assistant; Owner: -
--

CREATE FUNCTION assistant.touch_conversation_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;


--
-- Name: assert_bom_inputs_ready(uuid, date); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.assert_bom_inputs_ready(p_bom_version_id uuid, p_as_of date DEFAULT CURRENT_DATE) RETURNS void
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


--
-- Name: assert_part_ccu_inputs_ready(uuid, date); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.assert_part_ccu_inputs_ready(p_part_ccu_link_id uuid, p_as_of date DEFAULT CURRENT_DATE) RETURNS void
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


--
-- Name: backfill_ccu_requirement_slots_trigger(); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.backfill_ccu_requirement_slots_trigger() RETURNS trigger
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


--
-- Name: block_incomplete_input_snapshot(); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.block_incomplete_input_snapshot() RETURNS trigger
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


--
-- Name: FUNCTION block_incomplete_input_snapshot(); Type: COMMENT; Schema: enterprise; Owner: -
--

COMMENT ON FUNCTION enterprise.block_incomplete_input_snapshot() IS 'Blocks incomplete production snapshots. Allows only explicitly non-operational DEMO-* snapshots with enterprise_ccu_fields_complete=false and operational_use_permitted=false.';


--
-- Name: clear_part_ccu_input_value(uuid, text); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.clear_part_ccu_input_value(p_part_ccu_link_id uuid, p_field_path text) RETURNS uuid
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


--
-- Name: list_missing_required_bom_inputs(uuid, date); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.list_missing_required_bom_inputs(p_bom_version_id uuid, p_as_of date DEFAULT CURRENT_DATE) RETURNS TABLE(enterprise_part_id uuid, part_no text, ccu_code text, field_path text, field_name_cn text, data_owner text, missing_reason text)
    LANGUAGE sql STABLE
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


--
-- Name: list_missing_required_ccu_inputs(uuid, date); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.list_missing_required_ccu_inputs(p_part_ccu_link_id uuid, p_as_of date DEFAULT CURRENT_DATE) RETURNS TABLE(field_path text, field_name_cn text, data_owner text, missing_reason text)
    LANGUAGE sql STABLE
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


--
-- Name: set_part_ccu_input_value(uuid, text, jsonb, text, jsonb, text, boolean, text, date); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.set_part_ccu_input_value(p_part_ccu_link_id uuid, p_field_path text, p_value_payload jsonb, p_provided_by text, p_evidence_refs jsonb DEFAULT '[]'::jsonb, p_notes text DEFAULT NULL::text, p_mark_verified boolean DEFAULT false, p_verified_by text DEFAULT NULL::text, p_as_of date DEFAULT CURRENT_DATE) RETURNS uuid
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


--
-- Name: sync_part_ccu_input_slots(uuid); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.sync_part_ccu_input_slots(p_part_ccu_link_id uuid) RETURNS integer
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


--
-- Name: sync_part_ccu_input_slots_trigger(); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.sync_part_ccu_input_slots_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  PERFORM enterprise.sync_part_ccu_input_slots(NEW.part_ccu_link_id);
  RETURN NEW;
END
$$;


--
-- Name: validate_ccu_input_value_type(); Type: FUNCTION; Schema: enterprise; Owner: -
--

CREATE FUNCTION enterprise.validate_ccu_input_value_type() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
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
$_$;


--
-- Name: touch_updated_at(); Type: FUNCTION; Schema: platform; Owner: -
--

CREATE FUNCTION platform.touch_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: llm_view_item; Type: TABLE; Schema: ai; Owner: -
--

CREATE TABLE ai.llm_view_item (
    llm_view_item_id uuid DEFAULT gen_random_uuid() NOT NULL,
    calculation_run_id uuid NOT NULL,
    sequence_no integer NOT NULL,
    record_type text NOT NULL,
    record_id uuid NOT NULL,
    field_subset jsonb NOT NULL,
    why_read text NOT NULL,
    source_clause_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    data_quality ref.verification_status NOT NULL,
    prompt_safe boolean DEFAULT false NOT NULL,
    CONSTRAINT llm_view_item_field_subset_check CHECK ((jsonb_typeof(field_subset) = 'object'::text)),
    CONSTRAINT llm_view_item_sequence_no_check CHECK ((sequence_no > 0)),
    CONSTRAINT llm_view_item_source_clause_refs_check CHECK ((jsonb_typeof(source_clause_refs) = 'array'::text))
);


--
-- Name: source_clause; Type: TABLE; Schema: evidence; Owner: -
--

CREATE TABLE evidence.source_clause (
    source_clause_id uuid DEFAULT gen_random_uuid() NOT NULL,
    clause_code text NOT NULL,
    source_document_id uuid NOT NULL,
    locator_type text NOT NULL,
    locator_value text NOT NULL,
    original_text text,
    translated_text_cn text,
    evidence_summary text,
    extraction_method text,
    extracted_at timestamp with time zone,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_document; Type: TABLE; Schema: evidence; Owner: -
--

CREATE TABLE evidence.source_document (
    source_document_id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_code text NOT NULL,
    authority_id uuid,
    document_title text NOT NULL,
    document_number text,
    source_type ref.source_type NOT NULL,
    official_status ref.official_status DEFAULT 'UNKNOWN'::ref.official_status NOT NULL,
    canonical_url text,
    publication_date date,
    effective_from date,
    effective_to date,
    accessed_at timestamp with time zone NOT NULL,
    language_code character varying(12),
    content_sha256 character(64),
    archived_object_key text,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_document_check CHECK (((effective_from IS NULL) OR (effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT source_document_content_sha256_check CHECK (((content_sha256 IS NULL) OR (content_sha256 ~ '^[0-9a-fA-F]{64}$'::text))),
    CONSTRAINT source_document_version_check CHECK ((version > 0))
);


--
-- Name: authority; Type: TABLE; Schema: ref; Owner: -
--

CREATE TABLE ref.authority (
    authority_id uuid DEFAULT gen_random_uuid() NOT NULL,
    authority_code text NOT NULL,
    country_id uuid,
    authority_name text NOT NULL,
    official_url text,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: country; Type: TABLE; Schema: ref; Owner: -
--

CREATE TABLE ref.country (
    country_id uuid DEFAULT gen_random_uuid() NOT NULL,
    iso2 character(2) NOT NULL,
    iso3 character(3) NOT NULL,
    country_name_en text NOT NULL,
    country_name_cn text,
    currency_code character(3),
    timezone_name text,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: automotive_incentive_program; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.automotive_incentive_program (
    incentive_program_id uuid DEFAULT gen_random_uuid() NOT NULL,
    program_code text NOT NULL,
    country_id uuid NOT NULL,
    program_name_cn text NOT NULL,
    import_mode ref.import_mode,
    powertrain ref.powertrain,
    incentive_scope text NOT NULL,
    condition_expression jsonb NOT NULL,
    benefit_expression jsonb NOT NULL,
    approval_required boolean DEFAULT true NOT NULL,
    approval_authority_id uuid,
    source_clause_id uuid NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT automotive_incentive_program_benefit_expression_check CHECK ((jsonb_typeof(benefit_expression) = 'object'::text)),
    CONSTRAINT automotive_incentive_program_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT automotive_incentive_program_condition_expression_check CHECK ((jsonb_typeof(condition_expression) = 'object'::text)),
    CONSTRAINT automotive_incentive_program_version_check CHECK ((version > 0))
);


--
-- Name: v_malaysia_automotive_incentives_current; Type: VIEW; Schema: ai; Owner: -
--

CREATE VIEW ai.v_malaysia_automotive_incentives_current AS
 SELECT program.program_code,
    program.program_name_cn,
    program.import_mode,
    program.powertrain,
    program.incentive_scope,
    program.condition_expression,
    program.benefit_expression,
    program.approval_required,
    authority.authority_code,
    authority.authority_name,
    program.effective_from,
    program.effective_to,
    program.verification_status,
    source.source_code,
    clause.locator_value AS source_locator
   FROM ((((rules.automotive_incentive_program program
     JOIN ref.country country ON ((country.country_id = program.country_id)))
     LEFT JOIN ref.authority authority ON ((authority.authority_id = program.approval_authority_id)))
     JOIN evidence.source_clause clause ON ((clause.source_clause_id = program.source_clause_id)))
     JOIN evidence.source_document source ON ((source.source_document_id = clause.source_document_id)))
  WHERE ((country.iso2 = 'MY'::bpchar) AND (program.record_status = 'ACTIVE'::ref.record_status) AND (program.effective_from <= CURRENT_DATE) AND ((program.effective_to IS NULL) OR (program.effective_to > CURRENT_DATE)));


--
-- Name: vehicle_tax_route; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.vehicle_tax_route (
    vehicle_tax_route_id uuid DEFAULT gen_random_uuid() NOT NULL,
    route_code text NOT NULL,
    country_id uuid NOT NULL,
    decision_order smallint NOT NULL,
    route_name_cn text NOT NULL,
    route_name_en text NOT NULL,
    route_kind text NOT NULL,
    import_mode ref.import_mode NOT NULL,
    classification_granularity text NOT NULL,
    decision_condition jsonb NOT NULL,
    required_input_fields jsonb NOT NULL,
    calculation_dsl jsonb NOT NULL,
    fallback_route_code text,
    decision_note text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vehicle_tax_route_calculation_dsl_check CHECK ((jsonb_typeof(calculation_dsl) = 'object'::text)),
    CONSTRAINT vehicle_tax_route_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT vehicle_tax_route_classification_granularity_check CHECK ((classification_granularity = ANY (ARRAY['FINISHED_VEHICLE'::text, 'CKD_VEHICLE_TARIFF_LINE'::text, 'SUBASSEMBLY_TAX_BUCKET'::text, 'CUSTOMS_CLASSIFICATION_UNIT'::text, 'MIXED_ROUTE_ALLOCATION'::text]))),
    CONSTRAINT vehicle_tax_route_decision_condition_check CHECK ((jsonb_typeof(decision_condition) = 'object'::text)),
    CONSTRAINT vehicle_tax_route_decision_order_check CHECK (((decision_order >= 1) AND (decision_order <= 5))),
    CONSTRAINT vehicle_tax_route_required_input_fields_check CHECK ((jsonb_typeof(required_input_fields) = 'array'::text)),
    CONSTRAINT vehicle_tax_route_route_kind_check CHECK ((route_kind = ANY (ARRAY['CBU'::text, 'CKD_WHOLE_KIT'::text, 'PARTS_SUBASSEMBLIES'::text, 'PART_LEVEL'::text, 'MIXED_KD'::text]))),
    CONSTRAINT vehicle_tax_route_version_check CHECK ((version > 0))
);


--
-- Name: v_malaysia_five_route_decision_current; Type: VIEW; Schema: ai; Owner: -
--

CREATE VIEW ai.v_malaysia_five_route_decision_current AS
 SELECT route.decision_order,
    route.route_code,
    route.route_name_cn,
    route.route_name_en,
    route.route_kind,
    route.import_mode,
    route.classification_granularity,
    route.decision_condition,
    route.required_input_fields,
    route.fallback_route_code,
    route.decision_note,
    route.effective_from,
    route.effective_to,
    route.verification_status
   FROM (rules.vehicle_tax_route route
     JOIN ref.country country ON ((country.country_id = route.country_id)))
  WHERE ((country.iso2 = 'MY'::bpchar) AND (route.record_status = 'ACTIVE'::ref.record_status) AND (route.effective_from <= CURRENT_DATE) AND ((route.effective_to IS NULL) OR (route.effective_to > CURRENT_DATE)));


--
-- Name: ccu_candidate_hs; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.ccu_candidate_hs (
    candidate_id uuid DEFAULT gen_random_uuid() NOT NULL,
    ccu_id uuid NOT NULL,
    candidate_rank smallint NOT NULL,
    hs_nomenclature_version text NOT NULL,
    hs6_code character(6) NOT NULL,
    candidate_basis text NOT NULL,
    exclusion_notes text,
    source_clause_id uuid,
    verification_status ref.verification_status DEFAULT 'CANDIDATE'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ccu_candidate_hs_candidate_rank_check CHECK (((candidate_rank >= 1) AND (candidate_rank <= 3))),
    CONSTRAINT ccu_candidate_hs_hs6_code_check CHECK ((hs6_code ~ '^[0-9]{6}$'::text))
);


--
-- Name: customs_classification_unit; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.customs_classification_unit (
    ccu_id uuid DEFAULT gen_random_uuid() NOT NULL,
    ccu_code text NOT NULL,
    ccu_name_cn text NOT NULL,
    ccu_name_en text NOT NULL,
    parent_ccu_id uuid,
    vehicle_system text NOT NULL,
    unit_level ref.ccu_unit_level NOT NULL,
    function_description text NOT NULL,
    material_spec text,
    technical_qualifiers jsonb DEFAULT '{}'::jsonb NOT NULL,
    assembly_state ref.assembly_state DEFAULT 'UNKNOWN'::ref.assembly_state NOT NULL,
    included_items jsonb DEFAULT '[]'::jsonb NOT NULL,
    excluded_items jsonb DEFAULT '[]'::jsonb NOT NULL,
    required_input_fields jsonb DEFAULT '[]'::jsonb NOT NULL,
    gri_2a_risk ref.risk_level DEFAULT 'NONE'::ref.risk_level NOT NULL,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT customs_classification_unit_excluded_items_check CHECK ((jsonb_typeof(excluded_items) = 'array'::text)),
    CONSTRAINT customs_classification_unit_included_items_check CHECK ((jsonb_typeof(included_items) = 'array'::text)),
    CONSTRAINT customs_classification_unit_required_input_fields_check CHECK ((jsonb_typeof(required_input_fields) = 'array'::text)),
    CONSTRAINT customs_classification_unit_technical_qualifiers_check CHECK ((jsonb_typeof(technical_qualifiers) = 'object'::text)),
    CONSTRAINT customs_classification_unit_version_check CHECK ((version > 0))
);


--
-- Name: tariff_mapping; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.tariff_mapping (
    mapping_id uuid DEFAULT gen_random_uuid() NOT NULL,
    mapping_code text NOT NULL,
    country_id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    tariff_version text NOT NULL,
    national_tariff_code text NOT NULL,
    tariff_description text NOT NULL,
    origin_regime ref.origin_regime NOT NULL,
    trade_agreement_id uuid,
    duty_rate numeric(12,8),
    rate_type ref.rate_type NOT NULL,
    additional_measure jsonb DEFAULT '{}'::jsonb NOT NULL,
    eligibility_condition jsonb DEFAULT '{}'::jsonb NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    source_clause_id uuid NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tariff_mapping_additional_measure_check CHECK ((jsonb_typeof(additional_measure) = 'object'::text)),
    CONSTRAINT tariff_mapping_check CHECK (((rate_type <> 'UNKNOWN'::ref.rate_type) OR (duty_rate IS NULL))),
    CONSTRAINT tariff_mapping_check1 CHECK (((rate_type <> 'ZERO'::ref.rate_type) OR (duty_rate = (0)::numeric))),
    CONSTRAINT tariff_mapping_check2 CHECK (((origin_regime <> 'FTA'::ref.origin_regime) OR (trade_agreement_id IS NOT NULL))),
    CONSTRAINT tariff_mapping_check3 CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT tariff_mapping_duty_rate_check CHECK (((duty_rate IS NULL) OR (duty_rate >= (0)::numeric))),
    CONSTRAINT tariff_mapping_eligibility_condition_check CHECK ((jsonb_typeof(eligibility_condition) = 'object'::text)),
    CONSTRAINT tariff_mapping_national_tariff_code_check CHECK ((national_tariff_code ~ '^[0-9]{6,12}$'::text)),
    CONSTRAINT tariff_mapping_version_check CHECK ((version > 0))
);


--
-- Name: vehicle_tariff_rate_line; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.vehicle_tariff_rate_line (
    vehicle_tariff_rate_line_id uuid DEFAULT gen_random_uuid() NOT NULL,
    rate_line_code text NOT NULL,
    country_id uuid NOT NULL,
    vehicle_tax_route_id uuid NOT NULL,
    tariff_schedule_code text NOT NULL,
    tariff_year integer NOT NULL,
    origin_regime ref.origin_regime NOT NULL,
    trade_agreement_id uuid,
    hs6_code character(6) NOT NULL,
    national_tariff_code text NOT NULL,
    linked_pdk_tariff_code text,
    tariff_description text NOT NULL,
    powertrain ref.powertrain NOT NULL,
    vehicle_category text DEFAULT 'PASSENGER_VEHICLE_8703'::text NOT NULL,
    import_duty_rate numeric(12,8),
    sales_tax_rate numeric(12,8),
    excise_duty_rate numeric(12,8),
    sales_tax_treatment text NOT NULL,
    excise_treatment text NOT NULL,
    eligibility_condition jsonb DEFAULT '{}'::jsonb NOT NULL,
    tariff_source_clause_id uuid NOT NULL,
    tax_treatment_source_clause_id uuid,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    route_verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vehicle_tariff_rate_line_check CHECK (((origin_regime <> 'FTA'::ref.origin_regime) OR (trade_agreement_id IS NOT NULL))),
    CONSTRAINT vehicle_tariff_rate_line_check1 CHECK (((origin_regime = 'FTA'::ref.origin_regime) OR (trade_agreement_id IS NULL))),
    CONSTRAINT vehicle_tariff_rate_line_check2 CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT vehicle_tariff_rate_line_eligibility_condition_check CHECK ((jsonb_typeof(eligibility_condition) = 'object'::text)),
    CONSTRAINT vehicle_tariff_rate_line_excise_duty_rate_check CHECK (((excise_duty_rate IS NULL) OR (excise_duty_rate >= (0)::numeric))),
    CONSTRAINT vehicle_tariff_rate_line_excise_treatment_check CHECK ((excise_treatment = ANY (ARRAY['STATUTORY_RATE'::text, 'NOT_AT_IMPORT'::text, 'REQUIRES_PDK_CORRELATION'::text, 'UNKNOWN'::text]))),
    CONSTRAINT vehicle_tariff_rate_line_hs6_code_check CHECK ((hs6_code ~ '^[0-9]{6}$'::text)),
    CONSTRAINT vehicle_tariff_rate_line_import_duty_rate_check CHECK (((import_duty_rate IS NULL) OR (import_duty_rate >= (0)::numeric))),
    CONSTRAINT vehicle_tariff_rate_line_linked_pdk_tariff_code_check CHECK (((linked_pdk_tariff_code IS NULL) OR (linked_pdk_tariff_code ~ '^[0-9]{10}$'::text))),
    CONSTRAINT vehicle_tariff_rate_line_national_tariff_code_check CHECK ((national_tariff_code ~ '^[0-9]{10}$'::text)),
    CONSTRAINT vehicle_tariff_rate_line_sales_tax_rate_check CHECK (((sales_tax_rate IS NULL) OR (sales_tax_rate >= (0)::numeric))),
    CONSTRAINT vehicle_tariff_rate_line_sales_tax_treatment_check CHECK ((sales_tax_treatment = ANY (ARRAY['TAXABLE'::text, 'EXEMPT'::text, 'UNKNOWN'::text]))),
    CONSTRAINT vehicle_tariff_rate_line_tariff_year_check CHECK (((tariff_year >= 2000) AND (tariff_year <= 2200))),
    CONSTRAINT vehicle_tariff_rate_line_version_check CHECK ((version > 0))
);


--
-- Name: trade_agreement; Type: TABLE; Schema: ref; Owner: -
--

CREATE TABLE ref.trade_agreement (
    trade_agreement_id uuid DEFAULT gen_random_uuid() NOT NULL,
    agreement_code text NOT NULL,
    agreement_name text NOT NULL,
    version integer NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT trade_agreement_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT trade_agreement_version_check CHECK ((version > 0))
);


--
-- Name: kd_tax_bucket_definition; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.kd_tax_bucket_definition (
    kd_tax_bucket_id uuid DEFAULT gen_random_uuid() NOT NULL,
    bucket_code text NOT NULL,
    country_id uuid NOT NULL,
    bucket_name_cn text NOT NULL,
    bucket_name_en text NOT NULL,
    applicable_route_codes jsonb NOT NULL,
    included_scope jsonb NOT NULL,
    excluded_scope jsonb NOT NULL,
    classification_granularity text NOT NULL,
    import_tax_treatment jsonb NOT NULL,
    local_finished_vehicle_treatment jsonb NOT NULL,
    required_input_fields jsonb NOT NULL,
    double_count_key text NOT NULL,
    source_clause_id uuid,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT kd_tax_bucket_definition_applicable_route_codes_check CHECK ((jsonb_typeof(applicable_route_codes) = 'array'::text)),
    CONSTRAINT kd_tax_bucket_definition_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT kd_tax_bucket_definition_excluded_scope_check CHECK ((jsonb_typeof(excluded_scope) = 'array'::text)),
    CONSTRAINT kd_tax_bucket_definition_import_tax_treatment_check CHECK ((jsonb_typeof(import_tax_treatment) = 'object'::text)),
    CONSTRAINT kd_tax_bucket_definition_included_scope_check CHECK ((jsonb_typeof(included_scope) = 'array'::text)),
    CONSTRAINT kd_tax_bucket_definition_local_finished_vehicle_treatment_check CHECK ((jsonb_typeof(local_finished_vehicle_treatment) = 'object'::text)),
    CONSTRAINT kd_tax_bucket_definition_required_input_fields_check CHECK ((jsonb_typeof(required_input_fields) = 'array'::text)),
    CONSTRAINT kd_tax_bucket_definition_version_check CHECK ((version > 0))
);


--
-- Name: v_malaysia_five_route_readiness; Type: VIEW; Schema: ai; Owner: -
--

CREATE VIEW ai.v_malaysia_five_route_readiness AS
 SELECT route.decision_order,
    route.route_code,
    route.route_name_cn,
    route.verification_status AS route_verification_status,
    count(line.vehicle_tariff_rate_line_id) AS tariff_line_count,
    count(*) FILTER (WHERE (line.origin_regime = 'MFN'::ref.origin_regime)) AS mfn_line_count,
    count(*) FILTER (WHERE (agreement.agreement_code = 'ACFTA'::text)) AS acfta_line_count,
    count(*) FILTER (WHERE (agreement.agreement_code = 'RCEP'::text)) AS rcep_line_count,
    count(*) FILTER (WHERE ((line.vehicle_tariff_rate_line_id IS NOT NULL) AND (line.import_duty_rate IS NULL))) AS missing_public_duty_rate_count,
    count(*) FILTER (WHERE (line.verification_status = 'VERIFIED'::ref.verification_status)) AS verified_tariff_line_count,
        CASE
            WHEN (route.route_kind = ANY (ARRAY['PARTS_SUBASSEMBLIES'::text, 'PART_LEVEL'::text, 'MIXED_KD'::text])) THEN ( SELECT count(*) AS count
               FROM rules.kd_tax_bucket_definition bucket
              WHERE ((bucket.country_id = route.country_id) AND (bucket.record_status = 'ACTIVE'::ref.record_status)))
            ELSE (0)::bigint
        END AS kd_tax_bucket_count,
        CASE
            WHEN (route.route_kind = ANY (ARRAY['PARTS_SUBASSEMBLIES'::text, 'PART_LEVEL'::text, 'MIXED_KD'::text])) THEN ( SELECT count(*) AS count
               FROM customs.customs_classification_unit ccu
              WHERE ((ccu.unit_level = 'CUSTOMS_CLASSIFICATION_UNIT'::ref.ccu_unit_level) AND (ccu.record_status = 'ACTIVE'::ref.record_status)))
            ELSE (0)::bigint
        END AS active_ccu_count,
        CASE
            WHEN (route.route_kind = ANY (ARRAY['PARTS_SUBASSEMBLIES'::text, 'PART_LEVEL'::text, 'MIXED_KD'::text])) THEN ( SELECT count(DISTINCT candidate.ccu_id) AS count
               FROM (customs.tariff_mapping mapping
                 JOIN customs.ccu_candidate_hs candidate ON ((candidate.candidate_id = mapping.candidate_id)))
              WHERE ((mapping.country_id = route.country_id) AND (mapping.record_status = 'ACTIVE'::ref.record_status)))
            ELSE (0)::bigint
        END AS mapped_ccu_count,
        CASE
            WHEN (route.route_kind = ANY (ARRAY['PARTS_SUBASSEMBLIES'::text, 'PART_LEVEL'::text, 'MIXED_KD'::text])) THEN ( SELECT count(*) AS count
               FROM customs.tariff_mapping mapping
              WHERE ((mapping.country_id = route.country_id) AND (mapping.record_status = 'ACTIVE'::ref.record_status)))
            ELSE (0)::bigint
        END AS ccu_tariff_mapping_count,
        CASE
            WHEN (route.route_kind = ANY (ARRAY['PARTS_SUBASSEMBLIES'::text, 'PART_LEVEL'::text, 'MIXED_KD'::text])) THEN ( SELECT count(*) AS count
               FROM customs.tariff_mapping mapping
              WHERE ((mapping.country_id = route.country_id) AND (mapping.record_status = 'ACTIVE'::ref.record_status) AND (mapping.duty_rate IS NULL)))
            ELSE (0)::bigint
        END AS ccu_mapping_missing_duty_count
   FROM (((rules.vehicle_tax_route route
     JOIN ref.country country ON ((country.country_id = route.country_id)))
     LEFT JOIN customs.vehicle_tariff_rate_line line ON (((line.vehicle_tax_route_id = route.vehicle_tax_route_id) AND (line.record_status = 'ACTIVE'::ref.record_status))))
     LEFT JOIN ref.trade_agreement agreement ON ((agreement.trade_agreement_id = line.trade_agreement_id)))
  WHERE ((country.iso2 = 'MY'::bpchar) AND (route.record_status = 'ACTIVE'::ref.record_status))
  GROUP BY route.decision_order, route.route_code, route.route_name_cn, route.route_kind, route.country_id, route.verification_status;


--
-- Name: tax_scenario_model; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.tax_scenario_model (
    scenario_model_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_code text NOT NULL,
    country_id uuid NOT NULL,
    scenario_name_cn text NOT NULL,
    import_mode ref.import_mode NOT NULL,
    origin_regime ref.origin_regime NOT NULL,
    powertrain ref.powertrain,
    classification_route text NOT NULL,
    required_input_fields jsonb NOT NULL,
    calculation_dsl jsonb NOT NULL,
    fallback_scenario_id uuid,
    output_scope jsonb NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tax_scenario_model_calculation_dsl_check CHECK ((jsonb_typeof(calculation_dsl) = 'object'::text)),
    CONSTRAINT tax_scenario_model_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT tax_scenario_model_check1 CHECK (((fallback_scenario_id IS NULL) OR (fallback_scenario_id <> scenario_model_id))),
    CONSTRAINT tax_scenario_model_output_scope_check CHECK ((jsonb_typeof(output_scope) = 'object'::text)),
    CONSTRAINT tax_scenario_model_required_input_fields_check CHECK ((jsonb_typeof(required_input_fields) = 'array'::text)),
    CONSTRAINT tax_scenario_model_version_check CHECK ((version > 0))
);


--
-- Name: v_malaysia_vehicle_scenarios_current; Type: VIEW; Schema: ai; Owner: -
--

CREATE VIEW ai.v_malaysia_vehicle_scenarios_current AS
 SELECT scenario.scenario_code,
    scenario.scenario_name_cn,
    scenario.import_mode,
    scenario.powertrain,
    scenario.classification_route,
    scenario.required_input_fields,
    scenario.output_scope,
    scenario.effective_from,
    scenario.effective_to,
    scenario.verification_status
   FROM (rules.tax_scenario_model scenario
     JOIN ref.country country ON ((country.country_id = scenario.country_id)))
  WHERE ((country.iso2 = 'MY'::bpchar) AND (scenario.record_status = 'ACTIVE'::ref.record_status) AND (scenario.effective_from <= CURRENT_DATE) AND ((scenario.effective_to IS NULL) OR (scenario.effective_to > CURRENT_DATE)) AND ((scenario.scenario_code ~~ 'SCN-MY-CBU-%-2025'::text) OR (scenario.scenario_code ~~ 'SCN-MY-LOCAL-%'::text)));


--
-- Name: v_malaysia_vehicle_tariff_rates_current; Type: VIEW; Schema: ai; Owner: -
--

CREATE VIEW ai.v_malaysia_vehicle_tariff_rates_current AS
 SELECT route.decision_order,
    route.route_code,
    route.route_kind,
    line.tariff_schedule_code,
    line.tariff_year,
    line.origin_regime,
    agreement.agreement_code,
    line.hs6_code,
    line.national_tariff_code,
    line.linked_pdk_tariff_code,
    line.tariff_description,
    line.powertrain,
    line.import_duty_rate,
    line.sales_tax_rate,
    line.excise_duty_rate,
    line.sales_tax_treatment,
    line.excise_treatment,
    line.eligibility_condition,
    line.verification_status,
    line.route_verification_status,
    source.source_code,
    clause.locator_value AS source_locator,
    line.effective_from,
    line.effective_to
   FROM (((((customs.vehicle_tariff_rate_line line
     JOIN rules.vehicle_tax_route route ON ((route.vehicle_tax_route_id = line.vehicle_tax_route_id)))
     JOIN ref.country country ON ((country.country_id = line.country_id)))
     LEFT JOIN ref.trade_agreement agreement ON ((agreement.trade_agreement_id = line.trade_agreement_id)))
     JOIN evidence.source_clause clause ON ((clause.source_clause_id = line.tariff_source_clause_id)))
     JOIN evidence.source_document source ON ((source.source_document_id = clause.source_document_id)))
  WHERE ((country.iso2 = 'MY'::bpchar) AND (line.record_status = 'ACTIVE'::ref.record_status) AND (line.effective_from <= CURRENT_DATE) AND ((line.effective_to IS NULL) OR (line.effective_to > CURRENT_DATE)));


--
-- Name: vehicle_tariff_line; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.vehicle_tariff_line (
    vehicle_tariff_line_id uuid DEFAULT gen_random_uuid() NOT NULL,
    line_code text NOT NULL,
    country_id uuid NOT NULL,
    tariff_version text NOT NULL,
    hs6_code character(6) NOT NULL,
    national_tariff_code text NOT NULL,
    tariff_description text NOT NULL,
    import_mode ref.import_mode DEFAULT 'CBU'::ref.import_mode NOT NULL,
    origin_regime ref.origin_regime DEFAULT 'MFN'::ref.origin_regime NOT NULL,
    powertrain ref.powertrain NOT NULL,
    vehicle_category text DEFAULT 'PASSENGER_VEHICLE_8703'::text NOT NULL,
    classification_inputs jsonb DEFAULT '{}'::jsonb NOT NULL,
    import_duty_rate numeric(12,8) NOT NULL,
    excise_duty_rate numeric(12,8) NOT NULL,
    sales_tax_rate numeric(12,8) NOT NULL,
    tax_sequence jsonb NOT NULL,
    tariff_source_clause_id uuid NOT NULL,
    excise_source_clause_id uuid NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    classification_verification_status ref.verification_status DEFAULT 'CANDIDATE'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vehicle_tariff_line_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT vehicle_tariff_line_classification_inputs_check CHECK ((jsonb_typeof(classification_inputs) = 'object'::text)),
    CONSTRAINT vehicle_tariff_line_excise_duty_rate_check CHECK ((excise_duty_rate >= (0)::numeric)),
    CONSTRAINT vehicle_tariff_line_hs6_code_check CHECK ((hs6_code ~ '^[0-9]{6}$'::text)),
    CONSTRAINT vehicle_tariff_line_import_duty_rate_check CHECK ((import_duty_rate >= (0)::numeric)),
    CONSTRAINT vehicle_tariff_line_national_tariff_code_check CHECK ((national_tariff_code ~ '^[0-9]{10}$'::text)),
    CONSTRAINT vehicle_tariff_line_sales_tax_rate_check CHECK ((sales_tax_rate >= (0)::numeric)),
    CONSTRAINT vehicle_tariff_line_tax_sequence_check CHECK ((jsonb_typeof(tax_sequence) = 'array'::text)),
    CONSTRAINT vehicle_tariff_line_version_check CHECK ((version > 0))
);


--
-- Name: v_malaysia_vehicle_tax_lines_current; Type: VIEW; Schema: ai; Owner: -
--

CREATE VIEW ai.v_malaysia_vehicle_tax_lines_current AS
 SELECT line.line_code,
    line.hs6_code,
    line.national_tariff_code,
    line.tariff_description,
    line.import_mode,
    line.powertrain,
    line.vehicle_category,
    line.classification_inputs,
    line.import_duty_rate,
    line.excise_duty_rate,
    line.sales_tax_rate,
    line.tax_sequence,
    line.effective_from,
    line.effective_to,
    line.verification_status,
    line.classification_verification_status,
    tariff_source.source_code AS tariff_source_code,
    tariff_clause.locator_value AS tariff_source_locator,
    excise_source.source_code AS excise_source_code,
    excise_clause.locator_value AS excise_source_locator
   FROM (((((customs.vehicle_tariff_line line
     JOIN ref.country country ON ((country.country_id = line.country_id)))
     JOIN evidence.source_clause tariff_clause ON ((tariff_clause.source_clause_id = line.tariff_source_clause_id)))
     JOIN evidence.source_document tariff_source ON ((tariff_source.source_document_id = tariff_clause.source_document_id)))
     JOIN evidence.source_clause excise_clause ON ((excise_clause.source_clause_id = line.excise_source_clause_id)))
     JOIN evidence.source_document excise_source ON ((excise_source.source_document_id = excise_clause.source_document_id)))
  WHERE ((country.iso2 = 'MY'::bpchar) AND (line.record_status = 'ACTIVE'::ref.record_status) AND (line.effective_from <= CURRENT_DATE) AND ((line.effective_to IS NULL) OR (line.effective_to > CURRENT_DATE)));


--
-- Name: conversation; Type: TABLE; Schema: assistant; Owner: -
--

CREATE TABLE assistant.conversation (
    conversation_id text NOT NULL,
    user_id uuid NOT NULL,
    current_organization_id uuid,
    title text NOT NULL,
    status text DEFAULT 'IDLE'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT assistant_conversation_id_check CHECK (((btrim(conversation_id) <> ''::text) AND (length(conversation_id) <= 80))),
    CONSTRAINT assistant_conversation_status_check CHECK ((status = ANY (ARRAY['IDLE'::text, 'RUNNING'::text, 'ARCHIVED'::text]))),
    CONSTRAINT assistant_conversation_title_check CHECK ((btrim(title) <> ''::text)),
    CONSTRAINT conversation_conversation_id_check CHECK (((btrim(conversation_id) <> ''::text) AND (length(conversation_id) <= 80))),
    CONSTRAINT conversation_status_check CHECK ((status = ANY (ARRAY['IDLE'::text, 'RUNNING'::text, 'ARCHIVED'::text]))),
    CONSTRAINT conversation_title_check CHECK ((btrim(title) <> ''::text))
);


--
-- Name: TABLE conversation; Type: COMMENT; Schema: assistant; Owner: -
--

COMMENT ON TABLE assistant.conversation IS 'Assistant conversation owned by one account. Organization context is informational for this phase; sharing is not enabled.';


--
-- Name: COLUMN conversation.user_id; Type: COMMENT; Schema: assistant; Owner: -
--

COMMENT ON COLUMN assistant.conversation.user_id IS 'Durable account owner. Every assistant history read and write must filter by this value.';


--
-- Name: COLUMN conversation.current_organization_id; Type: COMMENT; Schema: assistant; Owner: -
--

COMMENT ON COLUMN assistant.conversation.current_organization_id IS 'Organization active when the conversation was created; not a sharing boundary in this phase.';


--
-- Name: message; Type: TABLE; Schema: assistant; Owner: -
--

CREATE TABLE assistant.message (
    message_id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id text NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    tool_calls jsonb DEFAULT '[]'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT message_content_check CHECK ((btrim(content) <> ''::text)),
    CONSTRAINT message_role_check CHECK ((role = ANY (ARRAY['user'::text, 'assistant'::text, 'system'::text, 'tool'::text])))
);


--
-- Name: TABLE message; Type: COMMENT; Schema: assistant; Owner: -
--

COMMENT ON TABLE assistant.message IS 'Durable assistant transcript. It is reachable only through its owner conversation.';


--
-- Name: decision_trace; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.decision_trace (
    decision_trace_id uuid DEFAULT gen_random_uuid() NOT NULL,
    calculation_run_id uuid NOT NULL,
    sequence_no integer NOT NULL,
    step_type ref.decision_step_type NOT NULL,
    decision_question text NOT NULL,
    input_record_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    rule_record_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    source_clause_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    explicit_rationale text NOT NULL,
    result jsonb NOT NULL,
    confidence numeric(5,4),
    human_review_required boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT decision_trace_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT decision_trace_input_record_refs_check CHECK ((jsonb_typeof(input_record_refs) = 'array'::text)),
    CONSTRAINT decision_trace_result_check CHECK ((jsonb_typeof(result) = ANY (ARRAY['object'::text, 'array'::text]))),
    CONSTRAINT decision_trace_rule_record_refs_check CHECK ((jsonb_typeof(rule_record_refs) = 'array'::text)),
    CONSTRAINT decision_trace_sequence_no_check CHECK ((sequence_no > 0)),
    CONSTRAINT decision_trace_source_clause_refs_check CHECK ((jsonb_typeof(source_clause_refs) = 'array'::text))
);


--
-- Name: TABLE decision_trace; Type: COMMENT; Schema: audit; Owner: -
--

COMMENT ON TABLE audit.decision_trace IS 'Stores auditable business decisions and explicit reasons; never hidden model chain-of-thought.';


--
-- Name: missing_data; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.missing_data (
    missing_data_id uuid DEFAULT gen_random_uuid() NOT NULL,
    calculation_run_id uuid,
    field_path text NOT NULL,
    description text NOT NULL,
    data_owner text,
    data_kind ref.missing_data_kind NOT NULL,
    data_ownership ref.data_ownership NOT NULL,
    blocking_scope text NOT NULL,
    priority ref.priority NOT NULL,
    next_action text NOT NULL,
    official_entry_url text,
    status ref.missing_data_status DEFAULT 'OPEN'::ref.missing_data_status NOT NULL,
    resolved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT missing_data_check CHECK (((status = 'RESOLVED'::ref.missing_data_status) = (resolved_at IS NOT NULL)))
);


--
-- Name: passenger_vehicle_scope_cleanup_20260812; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.passenger_vehicle_scope_cleanup_20260812 (
    mapping_id uuid NOT NULL,
    country_iso2 character(2) NOT NULL,
    ccu_code text NOT NULL,
    national_tariff_code text NOT NULL,
    tariff_description text,
    previous_record_status ref.record_status NOT NULL,
    cleanup_reason text NOT NULL,
    cleaned_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: review_record; Type: TABLE; Schema: audit; Owner: -
--

CREATE TABLE audit.review_record (
    review_record_id uuid DEFAULT gen_random_uuid() NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid NOT NULL,
    decision ref.review_decision DEFAULT 'PENDING'::ref.review_decision NOT NULL,
    reviewer text NOT NULL,
    review_notes text,
    reviewed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: calculation_line; Type: TABLE; Schema: calc; Owner: -
--

CREATE TABLE calc.calculation_line (
    calculation_line_id uuid DEFAULT gen_random_uuid() NOT NULL,
    calculation_run_id uuid NOT NULL,
    sequence_no integer NOT NULL,
    tax_code text NOT NULL,
    base_expression jsonb NOT NULL,
    base_amount numeric(20,6),
    rate_type ref.rate_type NOT NULL,
    rate numeric(12,8),
    tax_expression jsonb NOT NULL,
    gross_tax_amount numeric(20,6),
    recoverable_fraction numeric(12,8),
    net_tax_amount numeric(20,6),
    rule_card_id uuid,
    tariff_mapping_id uuid,
    line_status ref.calculation_status NOT NULL,
    notes text,
    vehicle_tariff_rate_line_id uuid,
    CONSTRAINT calculation_line_base_expression_check CHECK ((jsonb_typeof(base_expression) = 'object'::text)),
    CONSTRAINT calculation_line_rate_check CHECK (((rate IS NULL) OR (rate >= (0)::numeric))),
    CONSTRAINT calculation_line_recoverable_fraction_check CHECK (((recoverable_fraction IS NULL) OR ((recoverable_fraction >= (0)::numeric) AND (recoverable_fraction <= (1)::numeric)))),
    CONSTRAINT calculation_line_sequence_no_check CHECK ((sequence_no > 0)),
    CONSTRAINT calculation_line_tax_expression_check CHECK ((jsonb_typeof(tax_expression) = 'object'::text))
);


--
-- Name: calculation_run; Type: TABLE; Schema: calc; Owner: -
--

CREATE TABLE calc.calculation_run (
    calculation_run_id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_code text NOT NULL,
    scenario_model_id uuid NOT NULL,
    input_snapshot_id uuid NOT NULL,
    rule_snapshot_at timestamp with time zone NOT NULL,
    engine_version text NOT NULL,
    run_status ref.calculation_status DEFAULT 'QUEUED'::ref.calculation_status NOT NULL,
    completeness ref.completeness DEFAULT 'BLOCKED'::ref.completeness NOT NULL,
    currency_code character(3) NOT NULL,
    base_value numeric(20,6),
    gross_tax numeric(20,6),
    recoverable_tax numeric(20,6),
    net_tax numeric(20,6),
    effective_tax_rate numeric(12,8),
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    error_summary text,
    CONSTRAINT calculation_run_base_value_check CHECK (((base_value IS NULL) OR (base_value >= (0)::numeric))),
    CONSTRAINT calculation_run_check CHECK (((completed_at IS NULL) OR (completed_at >= started_at))),
    CONSTRAINT calculation_run_gross_tax_check CHECK (((gross_tax IS NULL) OR (gross_tax >= (0)::numeric))),
    CONSTRAINT calculation_run_net_tax_check CHECK (((net_tax IS NULL) OR (net_tax >= (0)::numeric))),
    CONSTRAINT calculation_run_recoverable_tax_check CHECK (((recoverable_tax IS NULL) OR (recoverable_tax >= (0)::numeric)))
);


--
-- Name: ccu_input_requirement; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.ccu_input_requirement (
    input_requirement_id uuid DEFAULT gen_random_uuid() NOT NULL,
    ccu_id uuid NOT NULL,
    field_path text NOT NULL,
    field_name_cn text NOT NULL,
    field_name_en text,
    required_at_use boolean DEFAULT true NOT NULL,
    value_type ref.input_data_type NOT NULL,
    unit text,
    suggested_value jsonb,
    allowed_values jsonb DEFAULT '[]'::jsonb NOT NULL,
    data_owner text NOT NULL,
    guidance_cn text,
    classification_impact_cn text,
    evidence_required boolean DEFAULT true NOT NULL,
    display_order integer NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer DEFAULT 1 NOT NULL,
    record_status ref.record_status DEFAULT 'ACTIVE'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'VERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ccu_input_requirement_allowed_values_check CHECK ((jsonb_typeof(allowed_values) = 'array'::text)),
    CONSTRAINT ccu_input_requirement_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT ccu_input_requirement_display_order_check CHECK ((display_order > 0)),
    CONSTRAINT ccu_input_requirement_field_path_check CHECK ((field_path ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$'::text)),
    CONSTRAINT ccu_input_requirement_version_check CHECK ((version > 0))
);


--
-- Name: TABLE ccu_input_requirement; Type: COMMENT; Schema: customs; Owner: -
--

COMMENT ON TABLE customs.ccu_input_requirement IS 'CCU-level enterprise input definitions. suggested_value is guidance only and is never copied into an enterprise fact value.';


--
-- Name: ccu_risk_tag; Type: TABLE; Schema: customs; Owner: -
--

CREATE TABLE customs.ccu_risk_tag (
    ccu_risk_tag_id uuid DEFAULT gen_random_uuid() NOT NULL,
    ccu_id uuid NOT NULL,
    risk_tag_type ref.risk_tag_type NOT NULL,
    risk_level ref.risk_level NOT NULL,
    trigger_condition jsonb NOT NULL,
    risk_note text NOT NULL,
    source_clause_id uuid,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ccu_risk_tag_trigger_condition_check CHECK ((jsonb_typeof(trigger_condition) = 'object'::text))
);


--
-- Name: bom_line; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.bom_line (
    bom_line_id uuid DEFAULT gen_random_uuid() NOT NULL,
    bom_version_id uuid NOT NULL,
    enterprise_part_id uuid NOT NULL,
    quantity_per_vehicle numeric(20,6) NOT NULL,
    unit_value numeric(20,6),
    currency_code character(3),
    origin_country_id uuid,
    shipment_group text,
    included_flag boolean DEFAULT true NOT NULL,
    CONSTRAINT bom_line_quantity_per_vehicle_check CHECK ((quantity_per_vehicle > (0)::numeric)),
    CONSTRAINT bom_line_unit_value_check CHECK (((unit_value IS NULL) OR (unit_value >= (0)::numeric)))
);


--
-- Name: bom_version; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.bom_version (
    bom_version_id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_id uuid NOT NULL,
    bom_code text NOT NULL,
    version integer NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT bom_version_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT bom_version_version_check CHECK ((version > 0))
);


--
-- Name: decision_project; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.decision_project (
    project_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_code text NOT NULL,
    enterprise_code text NOT NULL,
    project_name text NOT NULL,
    country_id uuid NOT NULL,
    vehicle_id uuid,
    calculation_date date DEFAULT CURRENT_DATE NOT NULL,
    selected_route_code text,
    route_facts jsonb DEFAULT '{}'::jsonb NOT NULL,
    project_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT decision_project_project_payload_check CHECK ((jsonb_typeof(project_payload) = 'object'::text)),
    CONSTRAINT decision_project_route_facts_check CHECK ((jsonb_typeof(route_facts) = 'object'::text))
);


--
-- Name: enterprise_part; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.enterprise_part (
    enterprise_part_id uuid DEFAULT gen_random_uuid() NOT NULL,
    enterprise_code text NOT NULL,
    part_no text NOT NULL,
    part_name_cn text,
    part_name_en text,
    attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT enterprise_part_attributes_check CHECK ((jsonb_typeof(attributes) = 'object'::text)),
    CONSTRAINT enterprise_part_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT enterprise_part_version_check CHECK ((version > 0))
);


--
-- Name: enterprise_part_ccu_link; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.enterprise_part_ccu_link (
    part_ccu_link_id uuid DEFAULT gen_random_uuid() NOT NULL,
    enterprise_part_id uuid NOT NULL,
    ccu_id uuid NOT NULL,
    mapping_basis text NOT NULL,
    confidence numeric(5,4),
    effective_from date NOT NULL,
    effective_to date,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT enterprise_part_ccu_link_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT enterprise_part_ccu_link_confidence_check CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))
);


--
-- Name: input_snapshot; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.input_snapshot (
    input_snapshot_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_input_id uuid NOT NULL,
    payload jsonb NOT NULL,
    payload_sha256 character(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT input_snapshot_payload_check CHECK ((jsonb_typeof(payload) = 'object'::text)),
    CONSTRAINT input_snapshot_payload_sha256_check CHECK ((payload_sha256 ~ '^[0-9a-fA-F]{64}$'::text))
);


--
-- Name: part_ccu_input_value; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.part_ccu_input_value (
    part_ccu_input_value_id uuid DEFAULT gen_random_uuid() NOT NULL,
    part_ccu_link_id uuid NOT NULL,
    input_requirement_id uuid NOT NULL,
    value_payload jsonb,
    value_status ref.input_value_status DEFAULT 'EMPTY'::ref.input_value_status NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    notes text,
    provided_by text,
    provided_at timestamp with time zone,
    verified_by text,
    verified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT part_ccu_input_value_check CHECK ((((value_status = 'EMPTY'::ref.input_value_status) AND (value_payload IS NULL)) OR ((value_status <> 'EMPTY'::ref.input_value_status) AND (value_payload IS NOT NULL) AND (jsonb_typeof(value_payload) <> 'null'::text)))),
    CONSTRAINT part_ccu_input_value_check1 CHECK (((value_status = 'VERIFIED'::ref.input_value_status) = (verified_at IS NOT NULL))),
    CONSTRAINT part_ccu_input_value_evidence_refs_check CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))
);


--
-- Name: TABLE part_ccu_input_value; Type: COMMENT; Schema: enterprise; Owner: -
--

COMMENT ON TABLE enterprise.part_ccu_input_value IS 'One progressively completed enterprise value slot per part-to-CCU link and CCU requirement. EMPTY rows are valid during research but block input snapshots and calculations when required_at_use is true.';


--
-- Name: project_approval; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.project_approval (
    project_approval_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    requirement_id uuid NOT NULL,
    approval_reference text,
    approval_status text DEFAULT 'NOT_PROVIDED'::text NOT NULL,
    authority_name text,
    issue_date date,
    effective_from date,
    effective_to date,
    covered_model text,
    covered_tariff_codes jsonb DEFAULT '[]'::jsonb NOT NULL,
    approved_rate numeric(18,8),
    exemption_scope jsonb DEFAULT '{}'::jsonb NOT NULL,
    evidence_ref text,
    notes text,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT project_approval_approval_status_check CHECK ((approval_status = ANY (ARRAY['NOT_PROVIDED'::text, 'PROVIDED'::text, 'VERIFIED'::text, 'REJECTED'::text, 'EXPIRED'::text]))),
    CONSTRAINT project_approval_check CHECK (((effective_to IS NULL) OR (effective_from IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT project_approval_covered_tariff_codes_check CHECK ((jsonb_typeof(covered_tariff_codes) = 'array'::text)),
    CONSTRAINT project_approval_exemption_scope_check CHECK ((jsonb_typeof(exemption_scope) = 'object'::text))
);


--
-- Name: project_bom_line; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.project_bom_line (
    project_bom_line_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    line_no integer NOT NULL,
    enterprise_part_no text NOT NULL,
    part_name text,
    ccu_id uuid NOT NULL,
    kd_tax_bucket_id uuid,
    customs_value numeric(20,6) NOT NULL,
    quantity numeric(20,6) DEFAULT 1 NOT NULL,
    currency_code character(3) DEFAULT 'MYR'::bpchar NOT NULL,
    origin_country_id uuid,
    local_or_imported text DEFAULT 'IMPORTED'::text NOT NULL,
    enterprise_inputs_complete boolean DEFAULT false NOT NULL,
    gri_2a_review_complete boolean DEFAULT false NOT NULL,
    notes text,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT project_bom_line_customs_value_check CHECK ((customs_value >= (0)::numeric)),
    CONSTRAINT project_bom_line_line_no_check CHECK ((line_no > 0)),
    CONSTRAINT project_bom_line_local_or_imported_check CHECK ((local_or_imported = ANY (ARRAY['IMPORTED'::text, 'LOCAL'::text]))),
    CONSTRAINT project_bom_line_quantity_check CHECK ((quantity > (0)::numeric))
);


--
-- Name: project_bom_tariff_selection; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.project_bom_tariff_selection (
    project_bom_tariff_selection_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_bom_line_id uuid NOT NULL,
    regime text NOT NULL,
    tariff_mapping_id uuid NOT NULL,
    selected_by text NOT NULL,
    selection_note text,
    verification_status ref.verification_status DEFAULT 'CANDIDATE'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT project_bom_tariff_selection_regime_check CHECK ((regime = ANY (ARRAY['MFN'::text, 'ACFTA'::text, 'RCEP'::text])))
);


--
-- Name: project_input_value; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.project_input_value (
    project_input_value_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    field_path text NOT NULL,
    value_payload jsonb,
    value_status ref.input_value_status DEFAULT 'EMPTY'::ref.input_value_status NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    notes text,
    provided_by text,
    provided_at timestamp with time zone,
    verified_by text,
    verified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT project_input_value_check CHECK ((((value_status = 'EMPTY'::ref.input_value_status) AND (value_payload IS NULL)) OR ((value_status <> 'EMPTY'::ref.input_value_status) AND (value_payload IS NOT NULL)))),
    CONSTRAINT project_input_value_evidence_refs_check CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))
);


--
-- Name: project_tariff_selection; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.project_tariff_selection (
    project_tariff_selection_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    selection_scope text NOT NULL,
    tariff_mapping_id uuid,
    vehicle_tariff_rate_line_id uuid,
    selected_by text NOT NULL,
    selection_note text,
    verification_status ref.verification_status DEFAULT 'CANDIDATE'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT project_tariff_selection_check CHECK ((num_nonnulls(tariff_mapping_id, vehicle_tariff_rate_line_id) = 1))
);


--
-- Name: scenario_input; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.scenario_input (
    scenario_input_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_code text NOT NULL,
    country_id uuid NOT NULL,
    vehicle_id uuid,
    bom_version_id uuid,
    import_date date NOT NULL,
    import_mode ref.import_mode NOT NULL,
    origin_country_id uuid,
    input_payload jsonb NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    decision_project_id uuid,
    CONSTRAINT scenario_input_input_payload_check CHECK ((jsonb_typeof(input_payload) = 'object'::text))
);


--
-- Name: v_part_ccu_input_collection; Type: VIEW; Schema: enterprise; Owner: -
--

CREATE VIEW enterprise.v_part_ccu_input_collection AS
 SELECT link.part_ccu_link_id,
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
    COALESCE(value_slot.value_status, 'EMPTY'::ref.input_value_status) AS value_status,
    COALESCE(value_slot.evidence_refs, '[]'::jsonb) AS evidence_refs,
    value_slot.notes,
    value_slot.provided_by,
    value_slot.provided_at,
    value_slot.verified_by,
    value_slot.verified_at,
        CASE
            WHEN (NOT requirement.required_at_use) THEN true
            WHEN (value_slot.value_status <> ALL (ARRAY['PROVIDED'::ref.input_value_status, 'VERIFIED'::ref.input_value_status])) THEN false
            WHEN ((value_slot.value_payload IS NULL) OR (jsonb_typeof(value_slot.value_payload) = 'null'::text)) THEN false
            WHEN ((jsonb_typeof(value_slot.value_payload) = 'string'::text) AND (upper(btrim((value_slot.value_payload #>> '{}'::text[]))) = ANY (ARRAY['UNKNOWN'::text, 'TO_BE_CONFIRMED'::text, 'PENDING'::text, '待确认'::text]))) THEN false
            ELSE true
        END AS accepted_for_use
   FROM ((((enterprise.enterprise_part_ccu_link link
     JOIN enterprise.enterprise_part part ON ((part.enterprise_part_id = link.enterprise_part_id)))
     JOIN customs.customs_classification_unit ccu ON ((ccu.ccu_id = link.ccu_id)))
     JOIN customs.ccu_input_requirement requirement ON (((requirement.ccu_id = link.ccu_id) AND (requirement.record_status = 'ACTIVE'::ref.record_status))))
     LEFT JOIN enterprise.part_ccu_input_value value_slot ON (((value_slot.part_ccu_link_id = link.part_ccu_link_id) AND (value_slot.input_requirement_id = requirement.input_requirement_id))));


--
-- Name: VIEW v_part_ccu_input_collection; Type: COMMENT; Schema: enterprise; Owner: -
--

COMMENT ON VIEW enterprise.v_part_ccu_input_collection IS 'User-facing collection rows for enterprise facts. suggested_value is displayed as guidance and never treated as a supplied value.';


--
-- Name: v_part_ccu_input_completion; Type: VIEW; Schema: enterprise; Owner: -
--

CREATE VIEW enterprise.v_part_ccu_input_completion AS
 SELECT part_ccu_link_id,
    enterprise_part_id,
    enterprise_code,
    part_no,
    part_name_cn,
    ccu_code,
    ccu_name_cn,
    count(*) AS parameter_count,
    count(*) FILTER (WHERE required_at_use) AS required_count,
    count(*) FILTER (WHERE (required_at_use AND accepted_for_use)) AS accepted_required_count,
    count(*) FILTER (WHERE (required_at_use AND (NOT accepted_for_use))) AS missing_required_count,
    round(
        CASE
            WHEN (count(*) FILTER (WHERE required_at_use) = 0) THEN (1)::numeric
            ELSE ((count(*) FILTER (WHERE (required_at_use AND accepted_for_use)))::numeric / (count(*) FILTER (WHERE required_at_use))::numeric)
        END, 4) AS completion_ratio,
    bool_and(((NOT required_at_use) OR accepted_for_use)) AS ready_for_use
   FROM enterprise.v_part_ccu_input_collection collection
  GROUP BY part_ccu_link_id, enterprise_part_id, enterprise_code, part_no, part_name_cn, ccu_code, ccu_name_cn;


--
-- Name: VIEW v_part_ccu_input_completion; Type: COMMENT; Schema: enterprise; Owner: -
--

COMMENT ON VIEW enterprise.v_part_ccu_input_completion IS 'Per part-to-CCU input completion summary used before classification and calculation.';


--
-- Name: v_project_input_completion; Type: VIEW; Schema: enterprise; Owner: -
--

CREATE VIEW enterprise.v_project_input_completion AS
SELECT
    NULL::uuid AS project_id,
    NULL::text AS project_code,
    NULL::text AS selected_route_code,
    NULL::bigint AS required_count,
    NULL::bigint AS accepted_required_count,
    NULL::bigint AS missing_required_count,
    NULL::numeric AS completion_ratio,
    NULL::boolean AS ready_for_preview;


--
-- Name: vehicle_model; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.vehicle_model (
    vehicle_id uuid DEFAULT gen_random_uuid() NOT NULL,
    model_code text NOT NULL,
    vehicle_type text NOT NULL,
    powertrain ref.powertrain NOT NULL,
    technical_attributes jsonb DEFAULT '{}'::jsonb NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vehicle_model_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT vehicle_model_technical_attributes_check CHECK ((jsonb_typeof(technical_attributes) = 'object'::text)),
    CONSTRAINT vehicle_model_version_check CHECK ((version > 0))
);


--
-- Name: vehicle_project_approval; Type: TABLE; Schema: enterprise; Owner: -
--

CREATE TABLE enterprise.vehicle_project_approval (
    vehicle_project_approval_id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_id uuid,
    incentive_program_id uuid NOT NULL,
    enterprise_code text NOT NULL,
    approval_reference text,
    approval_status ref.review_decision DEFAULT 'PENDING'::ref.review_decision NOT NULL,
    approved_condition_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    approved_benefit_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    evidence_source_document_id uuid,
    effective_from date,
    effective_to date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vehicle_project_approval_approved_benefit_payload_check CHECK ((jsonb_typeof(approved_benefit_payload) = 'object'::text)),
    CONSTRAINT vehicle_project_approval_approved_condition_payload_check CHECK ((jsonb_typeof(approved_condition_payload) = 'object'::text)),
    CONSTRAINT vehicle_project_approval_check CHECK (((effective_from IS NULL) OR (effective_to IS NULL) OR (effective_to > effective_from)))
);


--
-- Name: invitation; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.invitation (
    invitation_id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    email text NOT NULL,
    invitation_token_hash character(64) NOT NULL,
    invited_by uuid,
    role_id uuid,
    invitation_status iam.invitation_status DEFAULT 'PENDING'::iam.invitation_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    accepted_by uuid,
    revoked_at timestamp with time zone,
    CONSTRAINT invitation_check CHECK ((expires_at > created_at)),
    CONSTRAINT invitation_check1 CHECK (((accepted_at IS NULL) OR (accepted_at >= created_at))),
    CONSTRAINT invitation_check2 CHECK (((revoked_at IS NULL) OR (revoked_at >= created_at))),
    CONSTRAINT invitation_check3 CHECK ((NOT ((accepted_at IS NOT NULL) AND (revoked_at IS NOT NULL)))),
    CONSTRAINT invitation_email_check CHECK (((btrim(email) = email) AND (POSITION(('@'::text) IN (email)) > 1))),
    CONSTRAINT invitation_invitation_token_hash_check CHECK ((invitation_token_hash ~ '^[0-9a-fA-F]{64}$'::text))
);


--
-- Name: TABLE invitation; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON TABLE iam.invitation IS 'One-time organization invitation. Only a token hash is stored; invitation acceptance is auditable through timestamps and user references.';


--
-- Name: membership_role; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.membership_role (
    membership_id uuid NOT NULL,
    role_id uuid NOT NULL,
    assigned_at timestamp with time zone DEFAULT now() NOT NULL,
    assigned_by uuid
);


--
-- Name: organization; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.organization (
    organization_id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_key text NOT NULL,
    organization_name text NOT NULL,
    legal_name text,
    status iam.user_status DEFAULT 'ACTIVE'::iam.user_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT organization_legal_name_check CHECK (((legal_name IS NULL) OR (btrim(legal_name) <> ''::text))),
    CONSTRAINT organization_organization_key_check CHECK ((organization_key ~ '^[a-zA-Z0-9][a-zA-Z0-9_-]{1,99}$'::text)),
    CONSTRAINT organization_organization_name_check CHECK ((btrim(organization_name) <> ''::text))
);


--
-- Name: TABLE organization; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON TABLE iam.organization IS 'Tenant boundary for enterprise projects, BOMs, calculations, conversations and uploads.';


--
-- Name: organization_membership; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.organization_membership (
    membership_id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    user_id uuid NOT NULL,
    membership_status iam.membership_status DEFAULT 'ACTIVE'::iam.membership_status NOT NULL,
    joined_at timestamp with time zone,
    invited_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT organization_membership_check CHECK (((joined_at IS NULL) OR (joined_at >= created_at)))
);


--
-- Name: TABLE organization_membership; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON TABLE iam.organization_membership IS 'A user-to-organization membership. All tenant-scoped authorization resolves through this row.';


--
-- Name: permission; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.permission (
    permission_id uuid DEFAULT gen_random_uuid() NOT NULL,
    permission_key text NOT NULL,
    resource_key text NOT NULL,
    action_key text NOT NULL,
    permission_name_cn text NOT NULL,
    permission_name_en text NOT NULL,
    description text,
    is_system_permission boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT permission_action_key_check CHECK ((action_key ~ '^[a-z][a-z0-9_.-]{0,49}$'::text)),
    CONSTRAINT permission_permission_key_check CHECK ((permission_key ~ '^[a-z][a-z0-9_.-]{1,99}$'::text)),
    CONSTRAINT permission_permission_name_cn_check CHECK ((btrim(permission_name_cn) <> ''::text)),
    CONSTRAINT permission_permission_name_en_check CHECK ((btrim(permission_name_en) <> ''::text)),
    CONSTRAINT permission_resource_key_check CHECK ((resource_key ~ '^[a-z][a-z0-9_.-]{0,49}$'::text))
);


--
-- Name: role; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.role (
    role_id uuid DEFAULT gen_random_uuid() NOT NULL,
    role_key text NOT NULL,
    role_name_cn text NOT NULL,
    role_name_en text NOT NULL,
    role_scope iam.role_scope DEFAULT 'ORGANIZATION'::iam.role_scope NOT NULL,
    description text,
    is_system_role boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT role_role_key_check CHECK ((role_key ~ '^[a-z][a-z0-9_.-]{1,99}$'::text)),
    CONSTRAINT role_role_name_cn_check CHECK ((btrim(role_name_cn) <> ''::text)),
    CONSTRAINT role_role_name_en_check CHECK ((btrim(role_name_en) <> ''::text))
);


--
-- Name: role_permission; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.role_permission (
    role_id uuid NOT NULL,
    permission_id uuid NOT NULL,
    granted_at timestamp with time zone DEFAULT now() NOT NULL,
    granted_by uuid
);


--
-- Name: session; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.session (
    session_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    session_token_hash character(64) NOT NULL,
    auth_provider text DEFAULT 'local'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    ip_address inet,
    user_agent text,
    current_organization_id uuid,
    CONSTRAINT session_auth_provider_check CHECK ((btrim(auth_provider) <> ''::text)),
    CONSTRAINT session_check CHECK ((expires_at > created_at)),
    CONSTRAINT session_check1 CHECK ((last_seen_at >= created_at)),
    CONSTRAINT session_check2 CHECK (((revoked_at IS NULL) OR (revoked_at >= created_at))),
    CONSTRAINT session_session_token_hash_check CHECK ((session_token_hash ~ '^[0-9a-fA-F]{64}$'::text))
);


--
-- Name: TABLE session; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON TABLE iam.session IS 'Server-side session registry. Store only a SHA-256 token hash; the raw cookie token never enters PostgreSQL.';


--
-- Name: COLUMN session.expires_at; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON COLUMN iam.session.expires_at IS 'Absolute UTC expiration instant.';


--
-- Name: COLUMN session.current_organization_id; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON COLUMN iam.session.current_organization_id IS 'Current organization context selected for this session; application must verify an active membership before use.';


--
-- Name: user_account; Type: TABLE; Schema: iam; Owner: -
--

CREATE TABLE iam.user_account (
    user_id uuid DEFAULT gen_random_uuid() NOT NULL,
    identity_provider text DEFAULT 'local'::text NOT NULL,
    external_subject text,
    email text,
    display_name text,
    status iam.user_status DEFAULT 'ACTIVE'::iam.user_status NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    password_hash text,
    password_updated_at timestamp with time zone,
    CONSTRAINT user_account_display_name_check CHECK (((display_name IS NULL) OR (btrim(display_name) <> ''::text))),
    CONSTRAINT user_account_email_check CHECK (((email IS NULL) OR ((btrim(email) = email) AND (POSITION(('@'::text) IN (email)) > 1)))),
    CONSTRAINT user_account_external_subject_check CHECK (((external_subject IS NULL) OR (btrim(external_subject) <> ''::text))),
    CONSTRAINT user_account_identity_provider_check CHECK ((btrim(identity_provider) <> ''::text)),
    CONSTRAINT user_account_password_hash_check CHECK (((password_hash IS NULL) OR (btrim(password_hash) <> ''::text)))
);


--
-- Name: TABLE user_account; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON TABLE iam.user_account IS 'Application identity. OIDC/provider subject is the durable external identity key; no provider access token is stored here.';


--
-- Name: COLUMN user_account.external_subject; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON COLUMN iam.user_account.external_subject IS 'Stable subject identifier from the configured identity provider, not an access token.';


--
-- Name: COLUMN user_account.updated_at; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON COLUMN iam.user_account.updated_at IS 'Absolute UTC instant.';


--
-- Name: COLUMN user_account.password_hash; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON COLUMN iam.user_account.password_hash IS 'Optional self-describing PBKDF2-SHA256 hash for a standalone personal account; never clear text.';


--
-- Name: COLUMN user_account.password_updated_at; Type: COMMENT; Schema: iam; Owner: -
--

COMMENT ON COLUMN iam.user_account.password_updated_at IS 'UTC time at which the personal-account password was last changed.';


--
-- Name: schema_migration; Type: TABLE; Schema: platform; Owner: -
--

CREATE TABLE platform.schema_migration (
    migration_id bigint NOT NULL,
    migration_key text NOT NULL,
    version integer NOT NULL,
    checksum character(64) NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_by text DEFAULT CURRENT_USER NOT NULL,
    notes text,
    CONSTRAINT schema_migration_checksum_check CHECK ((checksum ~ '^[0-9a-fA-F]{64}$'::text)),
    CONSTRAINT schema_migration_version_check CHECK ((version > 0))
);


--
-- Name: TABLE schema_migration; Type: COMMENT; Schema: platform; Owner: -
--

COMMENT ON TABLE platform.schema_migration IS 'Applied database migrations. checksum is a stable migration-contract hash; rerunning a migration with a different checksum fails.';


--
-- Name: COLUMN schema_migration.applied_at; Type: COMMENT; Schema: platform; Owner: -
--

COMMENT ON COLUMN platform.schema_migration.applied_at IS 'Absolute UTC instant. PostgreSQL TIMESTAMPTZ is used intentionally.';


--
-- Name: schema_migration_migration_id_seq; Type: SEQUENCE; Schema: platform; Owner: -
--

ALTER TABLE platform.schema_migration ALTER COLUMN migration_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME platform.schema_migration_migration_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: approval_matrix; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.approval_matrix (
    requirement_id uuid DEFAULT gen_random_uuid() NOT NULL,
    requirement_code text NOT NULL,
    country_id uuid NOT NULL,
    requirement_type ref.requirement_type NOT NULL,
    applicable_object text NOT NULL,
    import_mode ref.import_mode,
    powertrain ref.powertrain,
    trigger_condition jsonb NOT NULL,
    required_document jsonb,
    authority_id uuid,
    benefit_rule_id uuid,
    failure_consequence text,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    source_clause_id uuid NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT approval_matrix_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT approval_matrix_required_document_check CHECK (((required_document IS NULL) OR (jsonb_typeof(required_document) = ANY (ARRAY['array'::text, 'object'::text])))),
    CONSTRAINT approval_matrix_trigger_condition_check CHECK ((jsonb_typeof(trigger_condition) = 'object'::text)),
    CONSTRAINT approval_matrix_version_check CHECK ((version > 0))
);


--
-- Name: country_rule_card; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.country_rule_card (
    rule_card_id uuid DEFAULT gen_random_uuid() NOT NULL,
    rule_code text NOT NULL,
    country_id uuid NOT NULL,
    rule_domain ref.rule_domain NOT NULL,
    rule_name_cn text NOT NULL,
    rule_content text NOT NULL,
    condition_expression jsonb NOT NULL,
    formula_expression jsonb,
    tariff_version text,
    authority_id uuid,
    effective_from date NOT NULL,
    effective_to date,
    version integer NOT NULL,
    source_clause_id uuid NOT NULL,
    record_status ref.record_status DEFAULT 'DRAFT'::ref.record_status NOT NULL,
    verification_status ref.verification_status DEFAULT 'UNVERIFIED'::ref.verification_status NOT NULL,
    verified_at timestamp with time zone,
    verified_by text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT country_rule_card_check CHECK (((effective_to IS NULL) OR (effective_to > effective_from))),
    CONSTRAINT country_rule_card_check1 CHECK (((verification_status = ANY (ARRAY['VERIFIED'::ref.verification_status, 'RULING_CONFIRMED'::ref.verification_status])) = (verified_at IS NOT NULL))),
    CONSTRAINT country_rule_card_condition_expression_check CHECK ((jsonb_typeof(condition_expression) = 'object'::text)),
    CONSTRAINT country_rule_card_formula_expression_check CHECK (((formula_expression IS NULL) OR (jsonb_typeof(formula_expression) = 'object'::text))),
    CONSTRAINT country_rule_card_version_check CHECK ((version > 0))
);


--
-- Name: scenario_requirement_link; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.scenario_requirement_link (
    scenario_requirement_link_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_model_id uuid NOT NULL,
    requirement_id uuid NOT NULL,
    sequence_no integer NOT NULL,
    blocking boolean DEFAULT true NOT NULL,
    CONSTRAINT scenario_requirement_link_sequence_no_check CHECK ((sequence_no > 0))
);


--
-- Name: scenario_rule_link; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.scenario_rule_link (
    scenario_rule_link_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_model_id uuid NOT NULL,
    rule_card_id uuid NOT NULL,
    sequence_no integer NOT NULL,
    mandatory boolean DEFAULT true NOT NULL,
    CONSTRAINT scenario_rule_link_sequence_no_check CHECK ((sequence_no > 0))
);


--
-- Name: vehicle_tax_route_source_link; Type: TABLE; Schema: rules; Owner: -
--

CREATE TABLE rules.vehicle_tax_route_source_link (
    vehicle_tax_route_source_link_id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_tax_route_id uuid NOT NULL,
    source_clause_id uuid NOT NULL,
    source_purpose text NOT NULL,
    sequence_no integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vehicle_tax_route_source_link_sequence_no_check CHECK ((sequence_no > 0))
);


--
-- Name: llm_view_item llm_view_item_calculation_run_id_sequence_no_key; Type: CONSTRAINT; Schema: ai; Owner: -
--

ALTER TABLE ONLY ai.llm_view_item
    ADD CONSTRAINT llm_view_item_calculation_run_id_sequence_no_key UNIQUE (calculation_run_id, sequence_no);


--
-- Name: llm_view_item llm_view_item_pkey; Type: CONSTRAINT; Schema: ai; Owner: -
--

ALTER TABLE ONLY ai.llm_view_item
    ADD CONSTRAINT llm_view_item_pkey PRIMARY KEY (llm_view_item_id);


--
-- Name: conversation conversation_pkey; Type: CONSTRAINT; Schema: assistant; Owner: -
--

ALTER TABLE ONLY assistant.conversation
    ADD CONSTRAINT conversation_pkey PRIMARY KEY (conversation_id);


--
-- Name: message message_pkey; Type: CONSTRAINT; Schema: assistant; Owner: -
--

ALTER TABLE ONLY assistant.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (message_id);


--
-- Name: decision_trace decision_trace_calculation_run_id_sequence_no_key; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.decision_trace
    ADD CONSTRAINT decision_trace_calculation_run_id_sequence_no_key UNIQUE (calculation_run_id, sequence_no);


--
-- Name: decision_trace decision_trace_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.decision_trace
    ADD CONSTRAINT decision_trace_pkey PRIMARY KEY (decision_trace_id);


--
-- Name: missing_data missing_data_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.missing_data
    ADD CONSTRAINT missing_data_pkey PRIMARY KEY (missing_data_id);


--
-- Name: passenger_vehicle_scope_cleanup_20260812 passenger_vehicle_scope_cleanup_20260812_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.passenger_vehicle_scope_cleanup_20260812
    ADD CONSTRAINT passenger_vehicle_scope_cleanup_20260812_pkey PRIMARY KEY (mapping_id);


--
-- Name: review_record review_record_pkey; Type: CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.review_record
    ADD CONSTRAINT review_record_pkey PRIMARY KEY (review_record_id);


--
-- Name: calculation_line calculation_line_calculation_run_id_sequence_no_key; Type: CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_line
    ADD CONSTRAINT calculation_line_calculation_run_id_sequence_no_key UNIQUE (calculation_run_id, sequence_no);


--
-- Name: calculation_line calculation_line_pkey; Type: CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_line
    ADD CONSTRAINT calculation_line_pkey PRIMARY KEY (calculation_line_id);


--
-- Name: calculation_run calculation_run_pkey; Type: CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_run
    ADD CONSTRAINT calculation_run_pkey PRIMARY KEY (calculation_run_id);


--
-- Name: calculation_run calculation_run_run_code_key; Type: CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_run
    ADD CONSTRAINT calculation_run_run_code_key UNIQUE (run_code);


--
-- Name: ccu_candidate_hs ccu_candidate_hs_ccu_id_candidate_rank_hs_nomenclature_vers_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_candidate_hs
    ADD CONSTRAINT ccu_candidate_hs_ccu_id_candidate_rank_hs_nomenclature_vers_key UNIQUE (ccu_id, candidate_rank, hs_nomenclature_version);


--
-- Name: ccu_candidate_hs ccu_candidate_hs_ccu_id_hs6_code_hs_nomenclature_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_candidate_hs
    ADD CONSTRAINT ccu_candidate_hs_ccu_id_hs6_code_hs_nomenclature_version_key UNIQUE (ccu_id, hs6_code, hs_nomenclature_version);


--
-- Name: ccu_candidate_hs ccu_candidate_hs_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_candidate_hs
    ADD CONSTRAINT ccu_candidate_hs_pkey PRIMARY KEY (candidate_id);


--
-- Name: ccu_input_requirement ccu_input_requirement_ccu_id_display_order_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_input_requirement
    ADD CONSTRAINT ccu_input_requirement_ccu_id_display_order_version_key UNIQUE (ccu_id, display_order, version);


--
-- Name: ccu_input_requirement ccu_input_requirement_ccu_id_field_path_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_input_requirement
    ADD CONSTRAINT ccu_input_requirement_ccu_id_field_path_version_key UNIQUE (ccu_id, field_path, version);


--
-- Name: ccu_input_requirement ccu_input_requirement_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_input_requirement
    ADD CONSTRAINT ccu_input_requirement_pkey PRIMARY KEY (input_requirement_id);


--
-- Name: ccu_risk_tag ccu_risk_tag_ccu_id_risk_tag_type_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_risk_tag
    ADD CONSTRAINT ccu_risk_tag_ccu_id_risk_tag_type_key UNIQUE (ccu_id, risk_tag_type);


--
-- Name: ccu_risk_tag ccu_risk_tag_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_risk_tag
    ADD CONSTRAINT ccu_risk_tag_pkey PRIMARY KEY (ccu_risk_tag_id);


--
-- Name: customs_classification_unit customs_classification_unit_ccu_code_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.customs_classification_unit
    ADD CONSTRAINT customs_classification_unit_ccu_code_version_key UNIQUE (ccu_code, version);


--
-- Name: customs_classification_unit customs_classification_unit_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.customs_classification_unit
    ADD CONSTRAINT customs_classification_unit_pkey PRIMARY KEY (ccu_id);


--
-- Name: tariff_mapping tariff_mapping_mapping_code_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.tariff_mapping
    ADD CONSTRAINT tariff_mapping_mapping_code_version_key UNIQUE (mapping_code, version);


--
-- Name: tariff_mapping tariff_mapping_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.tariff_mapping
    ADD CONSTRAINT tariff_mapping_pkey PRIMARY KEY (mapping_id);


--
-- Name: vehicle_tariff_line vehicle_tariff_line_country_id_tariff_version_national_tari_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_line
    ADD CONSTRAINT vehicle_tariff_line_country_id_tariff_version_national_tari_key UNIQUE (country_id, tariff_version, national_tariff_code, origin_regime, effective_from, version);


--
-- Name: vehicle_tariff_line vehicle_tariff_line_line_code_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_line
    ADD CONSTRAINT vehicle_tariff_line_line_code_version_key UNIQUE (line_code, version);


--
-- Name: vehicle_tariff_line vehicle_tariff_line_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_line
    ADD CONSTRAINT vehicle_tariff_line_pkey PRIMARY KEY (vehicle_tariff_line_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_pkey; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_pkey PRIMARY KEY (vehicle_tariff_rate_line_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_rate_line_code_version_key; Type: CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_rate_line_code_version_key UNIQUE (rate_line_code, version);


--
-- Name: bom_line bom_line_bom_version_id_enterprise_part_id_shipment_group_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_line
    ADD CONSTRAINT bom_line_bom_version_id_enterprise_part_id_shipment_group_key UNIQUE (bom_version_id, enterprise_part_id, shipment_group);


--
-- Name: bom_line bom_line_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_line
    ADD CONSTRAINT bom_line_pkey PRIMARY KEY (bom_line_id);


--
-- Name: bom_version bom_version_bom_code_version_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_version
    ADD CONSTRAINT bom_version_bom_code_version_key UNIQUE (bom_code, version);


--
-- Name: bom_version bom_version_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_version
    ADD CONSTRAINT bom_version_pkey PRIMARY KEY (bom_version_id);


--
-- Name: decision_project decision_project_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.decision_project
    ADD CONSTRAINT decision_project_pkey PRIMARY KEY (project_id);


--
-- Name: decision_project decision_project_project_code_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.decision_project
    ADD CONSTRAINT decision_project_project_code_key UNIQUE (project_code);


--
-- Name: enterprise_part_ccu_link enterprise_part_ccu_link_enterprise_part_id_ccu_id_effectiv_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.enterprise_part_ccu_link
    ADD CONSTRAINT enterprise_part_ccu_link_enterprise_part_id_ccu_id_effectiv_key UNIQUE (enterprise_part_id, ccu_id, effective_from);


--
-- Name: enterprise_part_ccu_link enterprise_part_ccu_link_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.enterprise_part_ccu_link
    ADD CONSTRAINT enterprise_part_ccu_link_pkey PRIMARY KEY (part_ccu_link_id);


--
-- Name: enterprise_part enterprise_part_enterprise_code_part_no_version_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.enterprise_part
    ADD CONSTRAINT enterprise_part_enterprise_code_part_no_version_key UNIQUE (enterprise_code, part_no, version);


--
-- Name: enterprise_part enterprise_part_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.enterprise_part
    ADD CONSTRAINT enterprise_part_pkey PRIMARY KEY (enterprise_part_id);


--
-- Name: input_snapshot input_snapshot_payload_sha256_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.input_snapshot
    ADD CONSTRAINT input_snapshot_payload_sha256_key UNIQUE (payload_sha256);


--
-- Name: input_snapshot input_snapshot_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.input_snapshot
    ADD CONSTRAINT input_snapshot_pkey PRIMARY KEY (input_snapshot_id);


--
-- Name: part_ccu_input_value part_ccu_input_value_part_ccu_link_id_input_requirement_id_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.part_ccu_input_value
    ADD CONSTRAINT part_ccu_input_value_part_ccu_link_id_input_requirement_id_key UNIQUE (part_ccu_link_id, input_requirement_id);


--
-- Name: part_ccu_input_value part_ccu_input_value_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.part_ccu_input_value
    ADD CONSTRAINT part_ccu_input_value_pkey PRIMARY KEY (part_ccu_input_value_id);


--
-- Name: project_approval project_approval_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_approval
    ADD CONSTRAINT project_approval_pkey PRIMARY KEY (project_approval_id);


--
-- Name: project_approval project_approval_project_id_requirement_id_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_approval
    ADD CONSTRAINT project_approval_project_id_requirement_id_key UNIQUE (project_id, requirement_id);


--
-- Name: project_bom_line project_bom_line_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_pkey PRIMARY KEY (project_bom_line_id);


--
-- Name: project_bom_line project_bom_line_project_id_ccu_id_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_project_id_ccu_id_key UNIQUE (project_id, ccu_id);


--
-- Name: project_bom_line project_bom_line_project_id_line_no_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_project_id_line_no_key UNIQUE (project_id, line_no);


--
-- Name: project_bom_tariff_selection project_bom_tariff_selection_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_tariff_selection
    ADD CONSTRAINT project_bom_tariff_selection_pkey PRIMARY KEY (project_bom_tariff_selection_id);


--
-- Name: project_bom_tariff_selection project_bom_tariff_selection_project_bom_line_id_regime_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_tariff_selection
    ADD CONSTRAINT project_bom_tariff_selection_project_bom_line_id_regime_key UNIQUE (project_bom_line_id, regime);


--
-- Name: project_input_value project_input_value_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_input_value
    ADD CONSTRAINT project_input_value_pkey PRIMARY KEY (project_input_value_id);


--
-- Name: project_input_value project_input_value_project_id_field_path_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_input_value
    ADD CONSTRAINT project_input_value_project_id_field_path_key UNIQUE (project_id, field_path);


--
-- Name: project_tariff_selection project_tariff_selection_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_tariff_selection
    ADD CONSTRAINT project_tariff_selection_pkey PRIMARY KEY (project_tariff_selection_id);


--
-- Name: project_tariff_selection project_tariff_selection_project_id_selection_scope_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_tariff_selection
    ADD CONSTRAINT project_tariff_selection_project_id_selection_scope_key UNIQUE (project_id, selection_scope);


--
-- Name: scenario_input scenario_input_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_pkey PRIMARY KEY (scenario_input_id);


--
-- Name: scenario_input scenario_input_scenario_code_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_scenario_code_key UNIQUE (scenario_code);


--
-- Name: vehicle_model vehicle_model_model_code_version_key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_model
    ADD CONSTRAINT vehicle_model_model_code_version_key UNIQUE (model_code, version);


--
-- Name: vehicle_model vehicle_model_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_model
    ADD CONSTRAINT vehicle_model_pkey PRIMARY KEY (vehicle_id);


--
-- Name: vehicle_project_approval vehicle_project_approval_enterprise_code_incentive_program__key; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_project_approval
    ADD CONSTRAINT vehicle_project_approval_enterprise_code_incentive_program__key UNIQUE (enterprise_code, incentive_program_id, approval_reference);


--
-- Name: vehicle_project_approval vehicle_project_approval_pkey; Type: CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_project_approval
    ADD CONSTRAINT vehicle_project_approval_pkey PRIMARY KEY (vehicle_project_approval_id);


--
-- Name: source_clause source_clause_clause_code_key; Type: CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_clause
    ADD CONSTRAINT source_clause_clause_code_key UNIQUE (clause_code);


--
-- Name: source_clause source_clause_pkey; Type: CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_clause
    ADD CONSTRAINT source_clause_pkey PRIMARY KEY (source_clause_id);


--
-- Name: source_clause source_clause_source_document_id_locator_type_locator_value_key; Type: CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_clause
    ADD CONSTRAINT source_clause_source_document_id_locator_type_locator_value_key UNIQUE (source_document_id, locator_type, locator_value);


--
-- Name: source_document source_document_pkey; Type: CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_document
    ADD CONSTRAINT source_document_pkey PRIMARY KEY (source_document_id);


--
-- Name: source_document source_document_source_code_key; Type: CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_document
    ADD CONSTRAINT source_document_source_code_key UNIQUE (source_code);


--
-- Name: invitation invitation_invitation_token_hash_key; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.invitation
    ADD CONSTRAINT invitation_invitation_token_hash_key UNIQUE (invitation_token_hash);


--
-- Name: invitation invitation_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.invitation
    ADD CONSTRAINT invitation_pkey PRIMARY KEY (invitation_id);


--
-- Name: membership_role membership_role_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.membership_role
    ADD CONSTRAINT membership_role_pkey PRIMARY KEY (membership_id, role_id);


--
-- Name: organization_membership organization_membership_organization_id_user_id_key; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization_membership
    ADD CONSTRAINT organization_membership_organization_id_user_id_key UNIQUE (organization_id, user_id);


--
-- Name: organization_membership organization_membership_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization_membership
    ADD CONSTRAINT organization_membership_pkey PRIMARY KEY (membership_id);


--
-- Name: organization organization_organization_key_key; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization
    ADD CONSTRAINT organization_organization_key_key UNIQUE (organization_key);


--
-- Name: organization organization_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization
    ADD CONSTRAINT organization_pkey PRIMARY KEY (organization_id);


--
-- Name: permission permission_permission_key_key; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.permission
    ADD CONSTRAINT permission_permission_key_key UNIQUE (permission_key);


--
-- Name: permission permission_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.permission
    ADD CONSTRAINT permission_pkey PRIMARY KEY (permission_id);


--
-- Name: role_permission role_permission_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.role_permission
    ADD CONSTRAINT role_permission_pkey PRIMARY KEY (role_id, permission_id);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (role_id);


--
-- Name: role role_role_key_key; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.role
    ADD CONSTRAINT role_role_key_key UNIQUE (role_key);


--
-- Name: session session_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.session
    ADD CONSTRAINT session_pkey PRIMARY KEY (session_id);


--
-- Name: session session_session_token_hash_key; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.session
    ADD CONSTRAINT session_session_token_hash_key UNIQUE (session_token_hash);


--
-- Name: user_account user_account_pkey; Type: CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.user_account
    ADD CONSTRAINT user_account_pkey PRIMARY KEY (user_id);


--
-- Name: schema_migration schema_migration_migration_key_key; Type: CONSTRAINT; Schema: platform; Owner: -
--

ALTER TABLE ONLY platform.schema_migration
    ADD CONSTRAINT schema_migration_migration_key_key UNIQUE (migration_key);


--
-- Name: schema_migration schema_migration_pkey; Type: CONSTRAINT; Schema: platform; Owner: -
--

ALTER TABLE ONLY platform.schema_migration
    ADD CONSTRAINT schema_migration_pkey PRIMARY KEY (migration_id);


--
-- Name: schema_migration schema_migration_version_key; Type: CONSTRAINT; Schema: platform; Owner: -
--

ALTER TABLE ONLY platform.schema_migration
    ADD CONSTRAINT schema_migration_version_key UNIQUE (version);


--
-- Name: authority authority_authority_code_key; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.authority
    ADD CONSTRAINT authority_authority_code_key UNIQUE (authority_code);


--
-- Name: authority authority_pkey; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.authority
    ADD CONSTRAINT authority_pkey PRIMARY KEY (authority_id);


--
-- Name: country country_iso2_key; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.country
    ADD CONSTRAINT country_iso2_key UNIQUE (iso2);


--
-- Name: country country_iso3_key; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.country
    ADD CONSTRAINT country_iso3_key UNIQUE (iso3);


--
-- Name: country country_pkey; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.country
    ADD CONSTRAINT country_pkey PRIMARY KEY (country_id);


--
-- Name: trade_agreement trade_agreement_agreement_code_version_key; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.trade_agreement
    ADD CONSTRAINT trade_agreement_agreement_code_version_key UNIQUE (agreement_code, version);


--
-- Name: trade_agreement trade_agreement_pkey; Type: CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.trade_agreement
    ADD CONSTRAINT trade_agreement_pkey PRIMARY KEY (trade_agreement_id);


--
-- Name: approval_matrix approval_matrix_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.approval_matrix
    ADD CONSTRAINT approval_matrix_pkey PRIMARY KEY (requirement_id);


--
-- Name: approval_matrix approval_matrix_requirement_code_version_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.approval_matrix
    ADD CONSTRAINT approval_matrix_requirement_code_version_key UNIQUE (requirement_code, version);


--
-- Name: automotive_incentive_program automotive_incentive_program_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.automotive_incentive_program
    ADD CONSTRAINT automotive_incentive_program_pkey PRIMARY KEY (incentive_program_id);


--
-- Name: automotive_incentive_program automotive_incentive_program_program_code_version_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.automotive_incentive_program
    ADD CONSTRAINT automotive_incentive_program_program_code_version_key UNIQUE (program_code, version);


--
-- Name: country_rule_card country_rule_card_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.country_rule_card
    ADD CONSTRAINT country_rule_card_pkey PRIMARY KEY (rule_card_id);


--
-- Name: country_rule_card country_rule_card_rule_code_version_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.country_rule_card
    ADD CONSTRAINT country_rule_card_rule_code_version_key UNIQUE (rule_code, version);


--
-- Name: kd_tax_bucket_definition kd_tax_bucket_definition_bucket_code_version_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.kd_tax_bucket_definition
    ADD CONSTRAINT kd_tax_bucket_definition_bucket_code_version_key UNIQUE (bucket_code, version);


--
-- Name: kd_tax_bucket_definition kd_tax_bucket_definition_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.kd_tax_bucket_definition
    ADD CONSTRAINT kd_tax_bucket_definition_pkey PRIMARY KEY (kd_tax_bucket_id);


--
-- Name: scenario_requirement_link scenario_requirement_link_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_requirement_link
    ADD CONSTRAINT scenario_requirement_link_pkey PRIMARY KEY (scenario_requirement_link_id);


--
-- Name: scenario_requirement_link scenario_requirement_link_scenario_model_id_requirement_id_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_requirement_link
    ADD CONSTRAINT scenario_requirement_link_scenario_model_id_requirement_id_key UNIQUE (scenario_model_id, requirement_id);


--
-- Name: scenario_requirement_link scenario_requirement_link_scenario_model_id_sequence_no_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_requirement_link
    ADD CONSTRAINT scenario_requirement_link_scenario_model_id_sequence_no_key UNIQUE (scenario_model_id, sequence_no);


--
-- Name: scenario_rule_link scenario_rule_link_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_rule_link
    ADD CONSTRAINT scenario_rule_link_pkey PRIMARY KEY (scenario_rule_link_id);


--
-- Name: scenario_rule_link scenario_rule_link_scenario_model_id_rule_card_id_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_rule_link
    ADD CONSTRAINT scenario_rule_link_scenario_model_id_rule_card_id_key UNIQUE (scenario_model_id, rule_card_id);


--
-- Name: scenario_rule_link scenario_rule_link_scenario_model_id_sequence_no_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_rule_link
    ADD CONSTRAINT scenario_rule_link_scenario_model_id_sequence_no_key UNIQUE (scenario_model_id, sequence_no);


--
-- Name: tax_scenario_model tax_scenario_model_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.tax_scenario_model
    ADD CONSTRAINT tax_scenario_model_pkey PRIMARY KEY (scenario_model_id);


--
-- Name: tax_scenario_model tax_scenario_model_scenario_code_version_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.tax_scenario_model
    ADD CONSTRAINT tax_scenario_model_scenario_code_version_key UNIQUE (scenario_code, version);


--
-- Name: vehicle_tax_route vehicle_tax_route_country_id_decision_order_effective_from__key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route
    ADD CONSTRAINT vehicle_tax_route_country_id_decision_order_effective_from__key UNIQUE (country_id, decision_order, effective_from, version);


--
-- Name: vehicle_tax_route vehicle_tax_route_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route
    ADD CONSTRAINT vehicle_tax_route_pkey PRIMARY KEY (vehicle_tax_route_id);


--
-- Name: vehicle_tax_route vehicle_tax_route_route_code_version_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route
    ADD CONSTRAINT vehicle_tax_route_route_code_version_key UNIQUE (route_code, version);


--
-- Name: vehicle_tax_route_source_link vehicle_tax_route_source_link_pkey; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route_source_link
    ADD CONSTRAINT vehicle_tax_route_source_link_pkey PRIMARY KEY (vehicle_tax_route_source_link_id);


--
-- Name: vehicle_tax_route_source_link vehicle_tax_route_source_link_vehicle_tax_route_id_sequence_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route_source_link
    ADD CONSTRAINT vehicle_tax_route_source_link_vehicle_tax_route_id_sequence_key UNIQUE (vehicle_tax_route_id, sequence_no);


--
-- Name: vehicle_tax_route_source_link vehicle_tax_route_source_link_vehicle_tax_route_id_source_c_key; Type: CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route_source_link
    ADD CONSTRAINT vehicle_tax_route_source_link_vehicle_tax_route_id_source_c_key UNIQUE (vehicle_tax_route_id, source_clause_id);


--
-- Name: idx_assistant_conversation_user_status; Type: INDEX; Schema: assistant; Owner: -
--

CREATE INDEX idx_assistant_conversation_user_status ON assistant.conversation USING btree (user_id, status, updated_at DESC);


--
-- Name: idx_assistant_conversation_user_updated; Type: INDEX; Schema: assistant; Owner: -
--

CREATE INDEX idx_assistant_conversation_user_updated ON assistant.conversation USING btree (user_id, updated_at DESC);


--
-- Name: idx_assistant_message_conversation_created; Type: INDEX; Schema: assistant; Owner: -
--

CREATE INDEX idx_assistant_message_conversation_created ON assistant.message USING btree (conversation_id, created_at, message_id);


--
-- Name: idx_missing_data_open; Type: INDEX; Schema: audit; Owner: -
--

CREATE INDEX idx_missing_data_open ON audit.missing_data USING btree (priority, status) WHERE (status <> ALL (ARRAY['RESOLVED'::ref.missing_data_status, 'WAIVED'::ref.missing_data_status]));


--
-- Name: idx_calc_run_scenario; Type: INDEX; Schema: calc; Owner: -
--

CREATE INDEX idx_calc_run_scenario ON calc.calculation_run USING btree (scenario_model_id, started_at);


--
-- Name: idx_calculation_line_vehicle_tariff; Type: INDEX; Schema: calc; Owner: -
--

CREATE INDEX idx_calculation_line_vehicle_tariff ON calc.calculation_line USING btree (vehicle_tariff_rate_line_id);


--
-- Name: idx_candidate_hs6; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_candidate_hs6 ON customs.ccu_candidate_hs USING btree (hs6_code, hs_nomenclature_version);


--
-- Name: idx_ccu_input_requirement_active; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_ccu_input_requirement_active ON customs.ccu_input_requirement USING btree (ccu_id, record_status, effective_from, effective_to);


--
-- Name: idx_ccu_parent; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_ccu_parent ON customs.customs_classification_unit USING btree (parent_ccu_id);


--
-- Name: idx_ccu_risk_tag; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_ccu_risk_tag ON customs.ccu_risk_tag USING btree (risk_tag_type, risk_level);


--
-- Name: idx_tariff_mapping_lookup; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_tariff_mapping_lookup ON customs.tariff_mapping USING btree (country_id, national_tariff_code, origin_regime, effective_from, effective_to);


--
-- Name: idx_vehicle_tariff_lookup; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_vehicle_tariff_lookup ON customs.vehicle_tariff_line USING btree (country_id, import_mode, powertrain, origin_regime, effective_from, effective_to);


--
-- Name: idx_vehicle_tariff_rate_code; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_vehicle_tariff_rate_code ON customs.vehicle_tariff_rate_line USING btree (national_tariff_code, tariff_schedule_code, tariff_year);


--
-- Name: idx_vehicle_tariff_rate_lookup; Type: INDEX; Schema: customs; Owner: -
--

CREATE INDEX idx_vehicle_tariff_rate_lookup ON customs.vehicle_tariff_rate_line USING btree (country_id, vehicle_tax_route_id, powertrain, origin_regime, tariff_year, effective_from, effective_to);


--
-- Name: idx_decision_project_country; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_decision_project_country ON enterprise.decision_project USING btree (country_id, calculation_date, record_status);


--
-- Name: idx_part_ccu_input_value_status; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_part_ccu_input_value_status ON enterprise.part_ccu_input_value USING btree (part_ccu_link_id, value_status);


--
-- Name: idx_part_ccu_link_part; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_part_ccu_link_part ON enterprise.enterprise_part_ccu_link USING btree (enterprise_part_id, effective_from, effective_to);


--
-- Name: idx_project_approval_project; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_project_approval_project ON enterprise.project_approval USING btree (project_id, approval_status);


--
-- Name: idx_project_bom_ccu; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_project_bom_ccu ON enterprise.project_bom_line USING btree (ccu_id);


--
-- Name: idx_project_bom_project; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_project_bom_project ON enterprise.project_bom_line USING btree (project_id, line_no);


--
-- Name: idx_project_bom_selection_line; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_project_bom_selection_line ON enterprise.project_bom_tariff_selection USING btree (project_bom_line_id, regime);


--
-- Name: idx_project_input_project; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_project_input_project ON enterprise.project_input_value USING btree (project_id, field_path);


--
-- Name: idx_scenario_input_decision_project; Type: INDEX; Schema: enterprise; Owner: -
--

CREATE INDEX idx_scenario_input_decision_project ON enterprise.scenario_input USING btree (decision_project_id, created_at DESC);


--
-- Name: idx_source_clause_document; Type: INDEX; Schema: evidence; Owner: -
--

CREATE INDEX idx_source_clause_document ON evidence.source_clause USING btree (source_document_id);


--
-- Name: idx_source_document_authority; Type: INDEX; Schema: evidence; Owner: -
--

CREATE INDEX idx_source_document_authority ON evidence.source_document USING btree (authority_id);


--
-- Name: idx_invitation_expiry; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_invitation_expiry ON iam.invitation USING btree (expires_at, invitation_status);


--
-- Name: idx_membership_org_status; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_membership_org_status ON iam.organization_membership USING btree (organization_id, membership_status);


--
-- Name: idx_membership_role_role; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_membership_role_role ON iam.membership_role USING btree (role_id, membership_id);


--
-- Name: idx_membership_user_status; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_membership_user_status ON iam.organization_membership USING btree (user_id, membership_status);


--
-- Name: idx_permission_resource; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_permission_resource ON iam.permission USING btree (resource_key, action_key);


--
-- Name: idx_role_permission_permission; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_role_permission_permission ON iam.role_permission USING btree (permission_id, role_id);


--
-- Name: idx_role_scope; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_role_scope ON iam.role USING btree (role_scope, role_key);


--
-- Name: idx_session_current_organization; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_session_current_organization ON iam.session USING btree (current_organization_id, user_id) WHERE (revoked_at IS NULL);


--
-- Name: idx_session_expiry; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_session_expiry ON iam.session USING btree (expires_at) WHERE (revoked_at IS NULL);


--
-- Name: idx_session_user_active; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_session_user_active ON iam.session USING btree (user_id, expires_at) WHERE (revoked_at IS NULL);


--
-- Name: idx_user_account_personal_email; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_user_account_personal_email ON iam.user_account USING btree (lower(email)) WHERE ((identity_provider = 'personal'::text) AND (status <> 'DELETED'::iam.user_status));


--
-- Name: idx_user_account_status; Type: INDEX; Schema: iam; Owner: -
--

CREATE INDEX idx_user_account_status ON iam.user_account USING btree (status, created_at DESC);


--
-- Name: uq_invitation_org_email_pending; Type: INDEX; Schema: iam; Owner: -
--

CREATE UNIQUE INDEX uq_invitation_org_email_pending ON iam.invitation USING btree (organization_id, lower(email)) WHERE ((invitation_status = 'PENDING'::iam.invitation_status) AND (revoked_at IS NULL));


--
-- Name: uq_user_account_email_ci; Type: INDEX; Schema: iam; Owner: -
--

CREATE UNIQUE INDEX uq_user_account_email_ci ON iam.user_account USING btree (lower(email)) WHERE ((email IS NOT NULL) AND (status <> 'DELETED'::iam.user_status));


--
-- Name: uq_user_account_provider_subject; Type: INDEX; Schema: iam; Owner: -
--

CREATE UNIQUE INDEX uq_user_account_provider_subject ON iam.user_account USING btree (identity_provider, external_subject) WHERE (external_subject IS NOT NULL);


--
-- Name: idx_approval_lookup; Type: INDEX; Schema: rules; Owner: -
--

CREATE INDEX idx_approval_lookup ON rules.approval_matrix USING btree (country_id, import_mode, powertrain, effective_from, effective_to);


--
-- Name: idx_automotive_incentive_lookup; Type: INDEX; Schema: rules; Owner: -
--

CREATE INDEX idx_automotive_incentive_lookup ON rules.automotive_incentive_program USING btree (country_id, import_mode, powertrain, effective_from, effective_to);


--
-- Name: idx_country_rule_effective; Type: INDEX; Schema: rules; Owner: -
--

CREATE INDEX idx_country_rule_effective ON rules.country_rule_card USING btree (country_id, rule_domain, effective_from, effective_to);


--
-- Name: idx_kd_tax_bucket_lookup; Type: INDEX; Schema: rules; Owner: -
--

CREATE INDEX idx_kd_tax_bucket_lookup ON rules.kd_tax_bucket_definition USING btree (country_id, effective_from, effective_to);


--
-- Name: idx_vehicle_tax_route_lookup; Type: INDEX; Schema: rules; Owner: -
--

CREATE INDEX idx_vehicle_tax_route_lookup ON rules.vehicle_tax_route USING btree (country_id, decision_order, effective_from, effective_to);


--
-- Name: v_project_input_completion _RETURN; Type: RULE; Schema: enterprise; Owner: -
--

CREATE OR REPLACE VIEW enterprise.v_project_input_completion AS
 WITH required_fields AS (
         SELECT project_1.project_id,
            route.route_code,
            required_1.field_path
           FROM ((enterprise.decision_project project_1
             JOIN rules.vehicle_tax_route route ON (((route.route_code = project_1.selected_route_code) AND (route.country_id = project_1.country_id) AND (route.record_status = 'ACTIVE'::ref.record_status) AND (route.effective_from <= project_1.calculation_date) AND ((route.effective_to IS NULL) OR (route.effective_to > project_1.calculation_date)))))
             CROSS JOIN LATERAL jsonb_array_elements_text(route.required_input_fields) required_1(field_path))
          WHERE (project_1.record_status = ANY (ARRAY['DRAFT'::ref.record_status, 'ACTIVE'::ref.record_status]))
        )
 SELECT project.project_id,
    project.project_code,
    project.selected_route_code,
    count(required.field_path) AS required_count,
    count(required.field_path) FILTER (WHERE ((value.value_status = ANY (ARRAY['PROVIDED'::ref.input_value_status, 'VERIFIED'::ref.input_value_status])) AND (value.value_payload IS NOT NULL) AND (lower(TRIM(BOTH FROM (value.value_payload #>> '{}'::text[]))) <> ALL (ARRAY[''::text, 'unknown'::text, 'pending'::text, '待确认'::text])))) AS accepted_required_count,
    count(required.field_path) FILTER (WHERE ((value.project_input_value_id IS NULL) OR (value.value_status <> ALL (ARRAY['PROVIDED'::ref.input_value_status, 'VERIFIED'::ref.input_value_status])) OR (value.value_payload IS NULL) OR (lower(TRIM(BOTH FROM (value.value_payload #>> '{}'::text[]))) = ANY (ARRAY[''::text, 'unknown'::text, 'pending'::text, '待确认'::text])))) AS missing_required_count,
        CASE
            WHEN (count(required.field_path) = 0) THEN (0)::numeric
            ELSE round(((count(required.field_path) FILTER (WHERE ((value.value_status = ANY (ARRAY['PROVIDED'::ref.input_value_status, 'VERIFIED'::ref.input_value_status])) AND (value.value_payload IS NOT NULL) AND (lower(TRIM(BOTH FROM (value.value_payload #>> '{}'::text[]))) <> ALL (ARRAY[''::text, 'unknown'::text, 'pending'::text, '待确认'::text])))))::numeric / (count(required.field_path))::numeric), 4)
        END AS completion_ratio,
    ((count(required.field_path) > 0) AND (count(required.field_path) FILTER (WHERE ((value.project_input_value_id IS NULL) OR (value.value_status <> ALL (ARRAY['PROVIDED'::ref.input_value_status, 'VERIFIED'::ref.input_value_status])) OR (value.value_payload IS NULL) OR (lower(TRIM(BOTH FROM (value.value_payload #>> '{}'::text[]))) = ANY (ARRAY[''::text, 'unknown'::text, 'pending'::text, '待确认'::text])))) = 0)) AS ready_for_preview
   FROM ((enterprise.decision_project project
     LEFT JOIN required_fields required ON ((required.project_id = project.project_id)))
     LEFT JOIN enterprise.project_input_value value ON (((value.project_id = project.project_id) AND (value.field_path = required.field_path))))
  GROUP BY project.project_id;


--
-- Name: conversation trg_touch_assistant_conversation_updated_at; Type: TRIGGER; Schema: assistant; Owner: -
--

CREATE TRIGGER trg_touch_assistant_conversation_updated_at BEFORE UPDATE ON assistant.conversation FOR EACH ROW EXECUTE FUNCTION assistant.touch_conversation_updated_at();


--
-- Name: ccu_input_requirement trg_backfill_ccu_requirement_slots; Type: TRIGGER; Schema: customs; Owner: -
--

CREATE TRIGGER trg_backfill_ccu_requirement_slots AFTER INSERT OR UPDATE OF record_status, effective_from, effective_to ON customs.ccu_input_requirement FOR EACH ROW EXECUTE FUNCTION enterprise.backfill_ccu_requirement_slots_trigger();


--
-- Name: input_snapshot trg_block_incomplete_input_snapshot; Type: TRIGGER; Schema: enterprise; Owner: -
--

CREATE TRIGGER trg_block_incomplete_input_snapshot BEFORE INSERT OR UPDATE OF scenario_input_id, payload ON enterprise.input_snapshot FOR EACH ROW EXECUTE FUNCTION enterprise.block_incomplete_input_snapshot();


--
-- Name: enterprise_part_ccu_link trg_sync_part_ccu_input_slots; Type: TRIGGER; Schema: enterprise; Owner: -
--

CREATE TRIGGER trg_sync_part_ccu_input_slots AFTER INSERT OR UPDATE OF ccu_id, effective_from, effective_to ON enterprise.enterprise_part_ccu_link FOR EACH ROW EXECUTE FUNCTION enterprise.sync_part_ccu_input_slots_trigger();


--
-- Name: part_ccu_input_value trg_validate_ccu_input_value; Type: TRIGGER; Schema: enterprise; Owner: -
--

CREATE TRIGGER trg_validate_ccu_input_value BEFORE INSERT OR UPDATE OF input_requirement_id, value_payload, value_status, verified_by, verified_at ON enterprise.part_ccu_input_value FOR EACH ROW EXECUTE FUNCTION enterprise.validate_ccu_input_value_type();


--
-- Name: organization_membership trg_touch_membership_updated_at; Type: TRIGGER; Schema: iam; Owner: -
--

CREATE TRIGGER trg_touch_membership_updated_at BEFORE UPDATE ON iam.organization_membership FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();


--
-- Name: organization trg_touch_organization_updated_at; Type: TRIGGER; Schema: iam; Owner: -
--

CREATE TRIGGER trg_touch_organization_updated_at BEFORE UPDATE ON iam.organization FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();


--
-- Name: permission trg_touch_permission_updated_at; Type: TRIGGER; Schema: iam; Owner: -
--

CREATE TRIGGER trg_touch_permission_updated_at BEFORE UPDATE ON iam.permission FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();


--
-- Name: role trg_touch_role_updated_at; Type: TRIGGER; Schema: iam; Owner: -
--

CREATE TRIGGER trg_touch_role_updated_at BEFORE UPDATE ON iam.role FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();


--
-- Name: user_account trg_touch_user_account_updated_at; Type: TRIGGER; Schema: iam; Owner: -
--

CREATE TRIGGER trg_touch_user_account_updated_at BEFORE UPDATE ON iam.user_account FOR EACH ROW EXECUTE FUNCTION platform.touch_updated_at();


--
-- Name: llm_view_item llm_view_item_calculation_run_id_fkey; Type: FK CONSTRAINT; Schema: ai; Owner: -
--

ALTER TABLE ONLY ai.llm_view_item
    ADD CONSTRAINT llm_view_item_calculation_run_id_fkey FOREIGN KEY (calculation_run_id) REFERENCES calc.calculation_run(calculation_run_id);


--
-- Name: conversation conversation_current_organization_id_fkey; Type: FK CONSTRAINT; Schema: assistant; Owner: -
--

ALTER TABLE ONLY assistant.conversation
    ADD CONSTRAINT conversation_current_organization_id_fkey FOREIGN KEY (current_organization_id) REFERENCES iam.organization(organization_id) ON DELETE SET NULL;


--
-- Name: conversation conversation_user_id_fkey; Type: FK CONSTRAINT; Schema: assistant; Owner: -
--

ALTER TABLE ONLY assistant.conversation
    ADD CONSTRAINT conversation_user_id_fkey FOREIGN KEY (user_id) REFERENCES iam.user_account(user_id) ON DELETE CASCADE;


--
-- Name: message message_conversation_id_fkey; Type: FK CONSTRAINT; Schema: assistant; Owner: -
--

ALTER TABLE ONLY assistant.message
    ADD CONSTRAINT message_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES assistant.conversation(conversation_id) ON DELETE CASCADE;


--
-- Name: decision_trace decision_trace_calculation_run_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.decision_trace
    ADD CONSTRAINT decision_trace_calculation_run_id_fkey FOREIGN KEY (calculation_run_id) REFERENCES calc.calculation_run(calculation_run_id);


--
-- Name: missing_data missing_data_calculation_run_id_fkey; Type: FK CONSTRAINT; Schema: audit; Owner: -
--

ALTER TABLE ONLY audit.missing_data
    ADD CONSTRAINT missing_data_calculation_run_id_fkey FOREIGN KEY (calculation_run_id) REFERENCES calc.calculation_run(calculation_run_id);


--
-- Name: calculation_line calculation_line_calculation_run_id_fkey; Type: FK CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_line
    ADD CONSTRAINT calculation_line_calculation_run_id_fkey FOREIGN KEY (calculation_run_id) REFERENCES calc.calculation_run(calculation_run_id);


--
-- Name: calculation_line calculation_line_rule_card_id_fkey; Type: FK CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_line
    ADD CONSTRAINT calculation_line_rule_card_id_fkey FOREIGN KEY (rule_card_id) REFERENCES rules.country_rule_card(rule_card_id);


--
-- Name: calculation_line calculation_line_tariff_mapping_id_fkey; Type: FK CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_line
    ADD CONSTRAINT calculation_line_tariff_mapping_id_fkey FOREIGN KEY (tariff_mapping_id) REFERENCES customs.tariff_mapping(mapping_id);


--
-- Name: calculation_line calculation_line_vehicle_tariff_rate_line_id_fkey; Type: FK CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_line
    ADD CONSTRAINT calculation_line_vehicle_tariff_rate_line_id_fkey FOREIGN KEY (vehicle_tariff_rate_line_id) REFERENCES customs.vehicle_tariff_rate_line(vehicle_tariff_rate_line_id);


--
-- Name: calculation_run calculation_run_input_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_run
    ADD CONSTRAINT calculation_run_input_snapshot_id_fkey FOREIGN KEY (input_snapshot_id) REFERENCES enterprise.input_snapshot(input_snapshot_id);


--
-- Name: calculation_run calculation_run_scenario_model_id_fkey; Type: FK CONSTRAINT; Schema: calc; Owner: -
--

ALTER TABLE ONLY calc.calculation_run
    ADD CONSTRAINT calculation_run_scenario_model_id_fkey FOREIGN KEY (scenario_model_id) REFERENCES rules.tax_scenario_model(scenario_model_id);


--
-- Name: ccu_candidate_hs ccu_candidate_hs_ccu_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_candidate_hs
    ADD CONSTRAINT ccu_candidate_hs_ccu_id_fkey FOREIGN KEY (ccu_id) REFERENCES customs.customs_classification_unit(ccu_id);


--
-- Name: ccu_candidate_hs ccu_candidate_hs_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_candidate_hs
    ADD CONSTRAINT ccu_candidate_hs_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: ccu_input_requirement ccu_input_requirement_ccu_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_input_requirement
    ADD CONSTRAINT ccu_input_requirement_ccu_id_fkey FOREIGN KEY (ccu_id) REFERENCES customs.customs_classification_unit(ccu_id);


--
-- Name: ccu_risk_tag ccu_risk_tag_ccu_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_risk_tag
    ADD CONSTRAINT ccu_risk_tag_ccu_id_fkey FOREIGN KEY (ccu_id) REFERENCES customs.customs_classification_unit(ccu_id);


--
-- Name: ccu_risk_tag ccu_risk_tag_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.ccu_risk_tag
    ADD CONSTRAINT ccu_risk_tag_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: customs_classification_unit customs_classification_unit_parent_ccu_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.customs_classification_unit
    ADD CONSTRAINT customs_classification_unit_parent_ccu_id_fkey FOREIGN KEY (parent_ccu_id) REFERENCES customs.customs_classification_unit(ccu_id);


--
-- Name: tariff_mapping tariff_mapping_candidate_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.tariff_mapping
    ADD CONSTRAINT tariff_mapping_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES customs.ccu_candidate_hs(candidate_id);


--
-- Name: tariff_mapping tariff_mapping_country_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.tariff_mapping
    ADD CONSTRAINT tariff_mapping_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: tariff_mapping tariff_mapping_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.tariff_mapping
    ADD CONSTRAINT tariff_mapping_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: tariff_mapping tariff_mapping_trade_agreement_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.tariff_mapping
    ADD CONSTRAINT tariff_mapping_trade_agreement_id_fkey FOREIGN KEY (trade_agreement_id) REFERENCES ref.trade_agreement(trade_agreement_id);


--
-- Name: vehicle_tariff_line vehicle_tariff_line_country_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_line
    ADD CONSTRAINT vehicle_tariff_line_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: vehicle_tariff_line vehicle_tariff_line_excise_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_line
    ADD CONSTRAINT vehicle_tariff_line_excise_source_clause_id_fkey FOREIGN KEY (excise_source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: vehicle_tariff_line vehicle_tariff_line_tariff_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_line
    ADD CONSTRAINT vehicle_tariff_line_tariff_source_clause_id_fkey FOREIGN KEY (tariff_source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_country_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_tariff_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_tariff_source_clause_id_fkey FOREIGN KEY (tariff_source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_tax_treatment_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_tax_treatment_source_clause_id_fkey FOREIGN KEY (tax_treatment_source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_trade_agreement_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_trade_agreement_id_fkey FOREIGN KEY (trade_agreement_id) REFERENCES ref.trade_agreement(trade_agreement_id);


--
-- Name: vehicle_tariff_rate_line vehicle_tariff_rate_line_vehicle_tax_route_id_fkey; Type: FK CONSTRAINT; Schema: customs; Owner: -
--

ALTER TABLE ONLY customs.vehicle_tariff_rate_line
    ADD CONSTRAINT vehicle_tariff_rate_line_vehicle_tax_route_id_fkey FOREIGN KEY (vehicle_tax_route_id) REFERENCES rules.vehicle_tax_route(vehicle_tax_route_id);


--
-- Name: bom_line bom_line_bom_version_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_line
    ADD CONSTRAINT bom_line_bom_version_id_fkey FOREIGN KEY (bom_version_id) REFERENCES enterprise.bom_version(bom_version_id);


--
-- Name: bom_line bom_line_enterprise_part_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_line
    ADD CONSTRAINT bom_line_enterprise_part_id_fkey FOREIGN KEY (enterprise_part_id) REFERENCES enterprise.enterprise_part(enterprise_part_id);


--
-- Name: bom_line bom_line_origin_country_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_line
    ADD CONSTRAINT bom_line_origin_country_id_fkey FOREIGN KEY (origin_country_id) REFERENCES ref.country(country_id);


--
-- Name: bom_version bom_version_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.bom_version
    ADD CONSTRAINT bom_version_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES enterprise.vehicle_model(vehicle_id);


--
-- Name: decision_project decision_project_country_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.decision_project
    ADD CONSTRAINT decision_project_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: decision_project decision_project_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.decision_project
    ADD CONSTRAINT decision_project_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES enterprise.vehicle_model(vehicle_id);


--
-- Name: enterprise_part_ccu_link enterprise_part_ccu_link_ccu_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.enterprise_part_ccu_link
    ADD CONSTRAINT enterprise_part_ccu_link_ccu_id_fkey FOREIGN KEY (ccu_id) REFERENCES customs.customs_classification_unit(ccu_id);


--
-- Name: enterprise_part_ccu_link enterprise_part_ccu_link_enterprise_part_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.enterprise_part_ccu_link
    ADD CONSTRAINT enterprise_part_ccu_link_enterprise_part_id_fkey FOREIGN KEY (enterprise_part_id) REFERENCES enterprise.enterprise_part(enterprise_part_id);


--
-- Name: input_snapshot input_snapshot_scenario_input_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.input_snapshot
    ADD CONSTRAINT input_snapshot_scenario_input_id_fkey FOREIGN KEY (scenario_input_id) REFERENCES enterprise.scenario_input(scenario_input_id);


--
-- Name: part_ccu_input_value part_ccu_input_value_input_requirement_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.part_ccu_input_value
    ADD CONSTRAINT part_ccu_input_value_input_requirement_id_fkey FOREIGN KEY (input_requirement_id) REFERENCES customs.ccu_input_requirement(input_requirement_id);


--
-- Name: part_ccu_input_value part_ccu_input_value_part_ccu_link_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.part_ccu_input_value
    ADD CONSTRAINT part_ccu_input_value_part_ccu_link_id_fkey FOREIGN KEY (part_ccu_link_id) REFERENCES enterprise.enterprise_part_ccu_link(part_ccu_link_id) ON DELETE CASCADE;


--
-- Name: project_approval project_approval_project_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_approval
    ADD CONSTRAINT project_approval_project_id_fkey FOREIGN KEY (project_id) REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE;


--
-- Name: project_approval project_approval_requirement_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_approval
    ADD CONSTRAINT project_approval_requirement_id_fkey FOREIGN KEY (requirement_id) REFERENCES rules.approval_matrix(requirement_id);


--
-- Name: project_bom_line project_bom_line_ccu_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_ccu_id_fkey FOREIGN KEY (ccu_id) REFERENCES customs.customs_classification_unit(ccu_id);


--
-- Name: project_bom_line project_bom_line_kd_tax_bucket_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_kd_tax_bucket_id_fkey FOREIGN KEY (kd_tax_bucket_id) REFERENCES rules.kd_tax_bucket_definition(kd_tax_bucket_id);


--
-- Name: project_bom_line project_bom_line_origin_country_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_origin_country_id_fkey FOREIGN KEY (origin_country_id) REFERENCES ref.country(country_id);


--
-- Name: project_bom_line project_bom_line_project_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_line
    ADD CONSTRAINT project_bom_line_project_id_fkey FOREIGN KEY (project_id) REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE;


--
-- Name: project_bom_tariff_selection project_bom_tariff_selection_project_bom_line_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_tariff_selection
    ADD CONSTRAINT project_bom_tariff_selection_project_bom_line_id_fkey FOREIGN KEY (project_bom_line_id) REFERENCES enterprise.project_bom_line(project_bom_line_id) ON DELETE CASCADE;


--
-- Name: project_bom_tariff_selection project_bom_tariff_selection_tariff_mapping_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_bom_tariff_selection
    ADD CONSTRAINT project_bom_tariff_selection_tariff_mapping_id_fkey FOREIGN KEY (tariff_mapping_id) REFERENCES customs.tariff_mapping(mapping_id);


--
-- Name: project_input_value project_input_value_project_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_input_value
    ADD CONSTRAINT project_input_value_project_id_fkey FOREIGN KEY (project_id) REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE;


--
-- Name: project_tariff_selection project_tariff_selection_project_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_tariff_selection
    ADD CONSTRAINT project_tariff_selection_project_id_fkey FOREIGN KEY (project_id) REFERENCES enterprise.decision_project(project_id) ON DELETE CASCADE;


--
-- Name: project_tariff_selection project_tariff_selection_tariff_mapping_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_tariff_selection
    ADD CONSTRAINT project_tariff_selection_tariff_mapping_id_fkey FOREIGN KEY (tariff_mapping_id) REFERENCES customs.tariff_mapping(mapping_id);


--
-- Name: project_tariff_selection project_tariff_selection_vehicle_tariff_rate_line_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.project_tariff_selection
    ADD CONSTRAINT project_tariff_selection_vehicle_tariff_rate_line_id_fkey FOREIGN KEY (vehicle_tariff_rate_line_id) REFERENCES customs.vehicle_tariff_rate_line(vehicle_tariff_rate_line_id);


--
-- Name: scenario_input scenario_input_bom_version_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_bom_version_id_fkey FOREIGN KEY (bom_version_id) REFERENCES enterprise.bom_version(bom_version_id);


--
-- Name: scenario_input scenario_input_country_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: scenario_input scenario_input_decision_project_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_decision_project_id_fkey FOREIGN KEY (decision_project_id) REFERENCES enterprise.decision_project(project_id);


--
-- Name: scenario_input scenario_input_origin_country_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_origin_country_id_fkey FOREIGN KEY (origin_country_id) REFERENCES ref.country(country_id);


--
-- Name: scenario_input scenario_input_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.scenario_input
    ADD CONSTRAINT scenario_input_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES enterprise.vehicle_model(vehicle_id);


--
-- Name: vehicle_project_approval vehicle_project_approval_evidence_source_document_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_project_approval
    ADD CONSTRAINT vehicle_project_approval_evidence_source_document_id_fkey FOREIGN KEY (evidence_source_document_id) REFERENCES evidence.source_document(source_document_id);


--
-- Name: vehicle_project_approval vehicle_project_approval_incentive_program_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_project_approval
    ADD CONSTRAINT vehicle_project_approval_incentive_program_id_fkey FOREIGN KEY (incentive_program_id) REFERENCES rules.automotive_incentive_program(incentive_program_id);


--
-- Name: vehicle_project_approval vehicle_project_approval_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: enterprise; Owner: -
--

ALTER TABLE ONLY enterprise.vehicle_project_approval
    ADD CONSTRAINT vehicle_project_approval_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES enterprise.vehicle_model(vehicle_id);


--
-- Name: source_clause source_clause_source_document_id_fkey; Type: FK CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_clause
    ADD CONSTRAINT source_clause_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES evidence.source_document(source_document_id);


--
-- Name: source_document source_document_authority_id_fkey; Type: FK CONSTRAINT; Schema: evidence; Owner: -
--

ALTER TABLE ONLY evidence.source_document
    ADD CONSTRAINT source_document_authority_id_fkey FOREIGN KEY (authority_id) REFERENCES ref.authority(authority_id);


--
-- Name: invitation invitation_accepted_by_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.invitation
    ADD CONSTRAINT invitation_accepted_by_fkey FOREIGN KEY (accepted_by) REFERENCES iam.user_account(user_id) ON DELETE SET NULL;


--
-- Name: invitation invitation_invited_by_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.invitation
    ADD CONSTRAINT invitation_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES iam.user_account(user_id) ON DELETE SET NULL;


--
-- Name: invitation invitation_organization_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.invitation
    ADD CONSTRAINT invitation_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES iam.organization(organization_id) ON DELETE CASCADE;


--
-- Name: invitation invitation_role_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.invitation
    ADD CONSTRAINT invitation_role_id_fkey FOREIGN KEY (role_id) REFERENCES iam.role(role_id) ON DELETE RESTRICT;


--
-- Name: membership_role membership_role_assigned_by_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.membership_role
    ADD CONSTRAINT membership_role_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES iam.user_account(user_id) ON DELETE SET NULL;


--
-- Name: membership_role membership_role_membership_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.membership_role
    ADD CONSTRAINT membership_role_membership_id_fkey FOREIGN KEY (membership_id) REFERENCES iam.organization_membership(membership_id) ON DELETE CASCADE;


--
-- Name: membership_role membership_role_role_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.membership_role
    ADD CONSTRAINT membership_role_role_id_fkey FOREIGN KEY (role_id) REFERENCES iam.role(role_id) ON DELETE RESTRICT;


--
-- Name: organization_membership organization_membership_invited_by_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization_membership
    ADD CONSTRAINT organization_membership_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES iam.user_account(user_id) ON DELETE SET NULL;


--
-- Name: organization_membership organization_membership_organization_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization_membership
    ADD CONSTRAINT organization_membership_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES iam.organization(organization_id) ON DELETE CASCADE;


--
-- Name: organization_membership organization_membership_user_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.organization_membership
    ADD CONSTRAINT organization_membership_user_id_fkey FOREIGN KEY (user_id) REFERENCES iam.user_account(user_id) ON DELETE CASCADE;


--
-- Name: role_permission role_permission_granted_by_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.role_permission
    ADD CONSTRAINT role_permission_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES iam.user_account(user_id) ON DELETE SET NULL;


--
-- Name: role_permission role_permission_permission_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.role_permission
    ADD CONSTRAINT role_permission_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES iam.permission(permission_id) ON DELETE CASCADE;


--
-- Name: role_permission role_permission_role_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.role_permission
    ADD CONSTRAINT role_permission_role_id_fkey FOREIGN KEY (role_id) REFERENCES iam.role(role_id) ON DELETE CASCADE;


--
-- Name: session session_current_organization_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.session
    ADD CONSTRAINT session_current_organization_id_fkey FOREIGN KEY (current_organization_id) REFERENCES iam.organization(organization_id) ON DELETE SET NULL;


--
-- Name: session session_user_id_fkey; Type: FK CONSTRAINT; Schema: iam; Owner: -
--

ALTER TABLE ONLY iam.session
    ADD CONSTRAINT session_user_id_fkey FOREIGN KEY (user_id) REFERENCES iam.user_account(user_id) ON DELETE CASCADE;


--
-- Name: authority authority_country_id_fkey; Type: FK CONSTRAINT; Schema: ref; Owner: -
--

ALTER TABLE ONLY ref.authority
    ADD CONSTRAINT authority_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: approval_matrix approval_matrix_authority_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.approval_matrix
    ADD CONSTRAINT approval_matrix_authority_id_fkey FOREIGN KEY (authority_id) REFERENCES ref.authority(authority_id);


--
-- Name: approval_matrix approval_matrix_benefit_rule_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.approval_matrix
    ADD CONSTRAINT approval_matrix_benefit_rule_id_fkey FOREIGN KEY (benefit_rule_id) REFERENCES rules.country_rule_card(rule_card_id);


--
-- Name: approval_matrix approval_matrix_country_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.approval_matrix
    ADD CONSTRAINT approval_matrix_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: approval_matrix approval_matrix_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.approval_matrix
    ADD CONSTRAINT approval_matrix_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: automotive_incentive_program automotive_incentive_program_approval_authority_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.automotive_incentive_program
    ADD CONSTRAINT automotive_incentive_program_approval_authority_id_fkey FOREIGN KEY (approval_authority_id) REFERENCES ref.authority(authority_id);


--
-- Name: automotive_incentive_program automotive_incentive_program_country_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.automotive_incentive_program
    ADD CONSTRAINT automotive_incentive_program_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: automotive_incentive_program automotive_incentive_program_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.automotive_incentive_program
    ADD CONSTRAINT automotive_incentive_program_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: country_rule_card country_rule_card_authority_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.country_rule_card
    ADD CONSTRAINT country_rule_card_authority_id_fkey FOREIGN KEY (authority_id) REFERENCES ref.authority(authority_id);


--
-- Name: country_rule_card country_rule_card_country_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.country_rule_card
    ADD CONSTRAINT country_rule_card_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: country_rule_card country_rule_card_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.country_rule_card
    ADD CONSTRAINT country_rule_card_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: kd_tax_bucket_definition kd_tax_bucket_definition_country_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.kd_tax_bucket_definition
    ADD CONSTRAINT kd_tax_bucket_definition_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: kd_tax_bucket_definition kd_tax_bucket_definition_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.kd_tax_bucket_definition
    ADD CONSTRAINT kd_tax_bucket_definition_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: scenario_requirement_link scenario_requirement_link_requirement_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_requirement_link
    ADD CONSTRAINT scenario_requirement_link_requirement_id_fkey FOREIGN KEY (requirement_id) REFERENCES rules.approval_matrix(requirement_id);


--
-- Name: scenario_requirement_link scenario_requirement_link_scenario_model_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_requirement_link
    ADD CONSTRAINT scenario_requirement_link_scenario_model_id_fkey FOREIGN KEY (scenario_model_id) REFERENCES rules.tax_scenario_model(scenario_model_id);


--
-- Name: scenario_rule_link scenario_rule_link_rule_card_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_rule_link
    ADD CONSTRAINT scenario_rule_link_rule_card_id_fkey FOREIGN KEY (rule_card_id) REFERENCES rules.country_rule_card(rule_card_id);


--
-- Name: scenario_rule_link scenario_rule_link_scenario_model_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.scenario_rule_link
    ADD CONSTRAINT scenario_rule_link_scenario_model_id_fkey FOREIGN KEY (scenario_model_id) REFERENCES rules.tax_scenario_model(scenario_model_id);


--
-- Name: tax_scenario_model tax_scenario_model_country_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.tax_scenario_model
    ADD CONSTRAINT tax_scenario_model_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: tax_scenario_model tax_scenario_model_fallback_scenario_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.tax_scenario_model
    ADD CONSTRAINT tax_scenario_model_fallback_scenario_id_fkey FOREIGN KEY (fallback_scenario_id) REFERENCES rules.tax_scenario_model(scenario_model_id);


--
-- Name: vehicle_tax_route vehicle_tax_route_country_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route
    ADD CONSTRAINT vehicle_tax_route_country_id_fkey FOREIGN KEY (country_id) REFERENCES ref.country(country_id);


--
-- Name: vehicle_tax_route_source_link vehicle_tax_route_source_link_source_clause_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route_source_link
    ADD CONSTRAINT vehicle_tax_route_source_link_source_clause_id_fkey FOREIGN KEY (source_clause_id) REFERENCES evidence.source_clause(source_clause_id);


--
-- Name: vehicle_tax_route_source_link vehicle_tax_route_source_link_vehicle_tax_route_id_fkey; Type: FK CONSTRAINT; Schema: rules; Owner: -
--

ALTER TABLE ONLY rules.vehicle_tax_route_source_link
    ADD CONSTRAINT vehicle_tax_route_source_link_vehicle_tax_route_id_fkey FOREIGN KEY (vehicle_tax_route_id) REFERENCES rules.vehicle_tax_route(vehicle_tax_route_id);


--
-- PostgreSQL database dump complete
--

\unrestrict CJmHFGJKa7jn5Bouvi7QyCT37AdfWucCVe3XxhLRui1CbCh4db18KYyitaN60Le

