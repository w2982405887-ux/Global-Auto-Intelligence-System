\pset null '[NULL]'

\echo '1. Collection API and views exist'
SELECT
  to_regprocedure(
    'enterprise.set_part_ccu_input_value(uuid,text,jsonb,text,jsonb,text,boolean,text,date)'
  ) IS NOT NULL AS setter_exists,
  to_regprocedure(
    'enterprise.clear_part_ccu_input_value(uuid,text)'
  ) IS NOT NULL AS clearer_exists,
  to_regclass(
    'enterprise.v_part_ccu_input_collection'
  ) IS NOT NULL AS collection_view_exists,
  to_regclass(
    'enterprise.v_part_ccu_input_completion'
  ) IS NOT NULL AS completion_view_exists;

\echo '2. Transactional use-flow test; all verification records are rolled back'
BEGIN;

INSERT INTO enterprise.enterprise_part (
  enterprise_part_id,
  enterprise_code,
  part_no,
  part_name_cn,
  attributes,
  effective_from,
  version,
  record_status
) VALUES (
  '9e000000-0000-4000-8000-000000000001',
  'VERIFY_ONLY',
  'VERIFY-INPUT-API-001',
  '企业输入接口验证零件',
  '{}'::jsonb,
  DATE '2026-01-01',
  1,
  'DRAFT'
);

INSERT INTO enterprise.enterprise_part_ccu_link (
  part_ccu_link_id,
  enterprise_part_id,
  ccu_id,
  mapping_basis,
  confidence,
  effective_from,
  verification_status
)
SELECT
  '9e000000-0000-4000-8000-000000000002',
  '9e000000-0000-4000-8000-000000000001',
  ccu.ccu_id,
  'Transactional verification only',
  1.0000,
  DATE '2026-01-01',
  'VERIFIED'
FROM customs.customs_classification_unit ccu
WHERE ccu.ccu_code = 'CCU-TRACTION-MOTOR'
  AND ccu.version = 1;

\echo '2a. New links start at zero completion'
SELECT
  parameter_count,
  required_count,
  accepted_required_count,
  missing_required_count,
  completion_ratio,
  ready_for_use
FROM enterprise.v_part_ccu_input_completion
WHERE part_ccu_link_id =
  '9e000000-0000-4000-8000-000000000002';

\echo '2b. UNKNOWN is stored for traceability but remains unresolved'
SELECT enterprise.set_part_ccu_input_value(
  '9e000000-0000-4000-8000-000000000002',
  'part.output_power_basis',
  '"UNKNOWN"'::jsonb,
  'VERIFY_USER',
  '["VERIFY-DATASHEET-001"]'::jsonb,
  'Unknown marker must not pass the use gate.'
);

SELECT
  missing_reason,
  count(*) AS missing_count
FROM enterprise.list_missing_required_ccu_inputs(
  '9e000000-0000-4000-8000-000000000002',
  DATE '2026-01-01'
)
GROUP BY missing_reason
ORDER BY missing_reason;

\echo '2c. A resolved value increases completion'
SELECT enterprise.set_part_ccu_input_value(
  '9e000000-0000-4000-8000-000000000002',
  'part.output_power_basis',
  '"CONTINUOUS_RATED"'::jsonb,
  'VERIFY_USER',
  '["VERIFY-DATASHEET-001"]'::jsonb,
  'Resolved verification value.'
);

SELECT
  accepted_required_count,
  missing_required_count,
  completion_ratio,
  ready_for_use
FROM enterprise.v_part_ccu_input_completion
WHERE part_ccu_link_id =
  '9e000000-0000-4000-8000-000000000002';

\echo '2d. Wrong JSON type is rejected'
DO $$
DECLARE
  invalid_type_blocked boolean := false;
BEGIN
  BEGIN
    PERFORM enterprise.set_part_ccu_input_value(
      '9e000000-0000-4000-8000-000000000002',
      'part.rated_output_kw',
      '"not-a-number"'::jsonb,
      'VERIFY_USER'
    );
  EXCEPTION
    WHEN invalid_parameter_value THEN
      invalid_type_blocked := true;
  END;

  IF NOT invalid_type_blocked THEN
    RAISE EXCEPTION 'Wrong JSON type was not rejected';
  END IF;
END
$$;

\echo '2e. Fill remaining required fields through the API'
SELECT enterprise.set_part_ccu_input_value(
  '9e000000-0000-4000-8000-000000000002',
  requirement.field_path,
  CASE requirement.value_type
    WHEN 'TEXT' THEN '"TEST_VALUE"'::jsonb
    WHEN 'NUMBER' THEN '1'::jsonb
    WHEN 'BOOLEAN' THEN 'false'::jsonb
    WHEN 'ENUM' THEN requirement.allowed_values -> 0
    WHEN 'DATE' THEN '"2026-01-01"'::jsonb
    WHEN 'JSON' THEN '{}'::jsonb
  END,
  'VERIFY_USER',
  '["VERIFY-EVIDENCE"]'::jsonb,
  'Transactional verification value.'
)
FROM customs.ccu_input_requirement requirement
JOIN enterprise.enterprise_part_ccu_link link
  ON link.ccu_id = requirement.ccu_id
WHERE link.part_ccu_link_id =
    '9e000000-0000-4000-8000-000000000002'
  AND requirement.required_at_use
  AND requirement.field_path <> 'part.output_power_basis';

SELECT
  accepted_required_count,
  missing_required_count,
  completion_ratio,
  ready_for_use
FROM enterprise.v_part_ccu_input_completion
WHERE part_ccu_link_id =
  '9e000000-0000-4000-8000-000000000002';

SELECT enterprise.assert_part_ccu_inputs_ready(
  '9e000000-0000-4000-8000-000000000002',
  DATE '2026-01-01'
) AS completed_link_accepted;

\echo '2f. Clearing one value returns the record to blocked state'
SELECT enterprise.clear_part_ccu_input_value(
  '9e000000-0000-4000-8000-000000000002',
  'part.rated_output_kw'
);

SELECT
  accepted_required_count,
  missing_required_count,
  completion_ratio,
  ready_for_use
FROM enterprise.v_part_ccu_input_completion
WHERE part_ccu_link_id =
  '9e000000-0000-4000-8000-000000000002';

ROLLBACK;

\echo '3. No verification-only enterprise data persisted'
SELECT count(*) AS verification_record_count
FROM enterprise.enterprise_part
WHERE enterprise_code = 'VERIFY_ONLY'
  AND part_no = 'VERIFY-INPUT-API-001';
