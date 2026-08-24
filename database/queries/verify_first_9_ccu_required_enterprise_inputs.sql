\pset null '[NULL]'

\echo '1. Requirement definitions by CCU'
SELECT
  ccu.ccu_code,
  count(*) AS parameter_count,
  count(*) FILTER (WHERE requirement.required_at_use) AS required_at_use_count,
  count(*) FILTER (WHERE NOT requirement.required_at_use) AS optional_count
FROM customs.ccu_input_requirement requirement
JOIN customs.customs_classification_unit ccu
  ON ccu.ccu_id = requirement.ccu_id
WHERE requirement.record_status = 'ACTIVE'
  AND ccu.ccu_code IN (
    'CCU-TRACTION-MOTOR',
    'CCU-TRACTION-INVERTER',
    'CCU-ONBOARD-CHARGER',
    'CCU-DC-DC-CONVERTER',
    'CCU-PASSENGER-BODY-SHELL',
    'CCU-ROAD-WHEEL',
    'CCU-FOUNDATION-BRAKE',
    'CCU-STEERING-GEAR-COLUMN',
    'CCU-SHOCK-ABSORBER-STRUT'
  )
GROUP BY ccu.ccu_code
ORDER BY ccu.ccu_code;

\echo '2. Overall requirement totals'
SELECT
  count(DISTINCT requirement.ccu_id) AS ccu_count,
  count(*) AS parameter_count,
  count(*) FILTER (WHERE requirement.required_at_use) AS required_at_use_count,
  count(*) FILTER (
    WHERE requirement.suggested_value IS NOT NULL
  ) AS suggested_value_count,
  count(*) FILTER (
    WHERE requirement.verification_status <> 'VERIFIED'
  ) AS unverified_definition_count
FROM customs.ccu_input_requirement requirement
WHERE requirement.record_status = 'ACTIVE';

\echo '3. Existing enterprise slots remain empty unless users supplied facts'
SELECT
  value_status,
  count(*) AS slot_count
FROM enterprise.part_ccu_input_value
GROUP BY value_status
ORDER BY value_status;

\echo '4. Existing enterprise gaps remain waiting, not falsely resolved'
SELECT
  status,
  count(*) AS gap_count
FROM audit.missing_data
WHERE field_path LIKE 'enterprise.classification_input[CCU-%]%'
GROUP BY status
ORDER BY status;

\echo '5. Transactional smoke test: link creation generates empty slots and the usage gate blocks'
BEGIN;

INSERT INTO enterprise.enterprise_part (
  enterprise_part_id,
  enterprise_code,
  part_no,
  part_name_cn,
  part_name_en,
  attributes,
  effective_from,
  effective_to,
  version,
  record_status
) VALUES (
  '9f000000-0000-4000-8000-000000000001',
  'VERIFY_ONLY',
  'VERIFY-MOTOR-001',
  '验证用驱动电机',
  'Verification-only traction motor',
  '{}'::jsonb,
  DATE '2026-01-01',
  NULL,
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
  effective_to,
  verification_status
)
SELECT
  '9f000000-0000-4000-8000-000000000002',
  '9f000000-0000-4000-8000-000000000001',
  ccu.ccu_id,
  'Transactional verification only',
  1.0000,
  DATE '2026-01-01',
  NULL,
  'VERIFIED'
FROM customs.customs_classification_unit ccu
WHERE ccu.ccu_code = 'CCU-TRACTION-MOTOR'
  AND ccu.version = 1;

SELECT
  count(*) AS generated_slot_count,
  count(*) FILTER (
    WHERE value_status = 'EMPTY' AND value_payload IS NULL
  ) AS correctly_empty_slot_count
FROM enterprise.part_ccu_input_value
WHERE part_ccu_link_id =
  '9f000000-0000-4000-8000-000000000002';

SELECT
  count(*) AS missing_required_count
FROM enterprise.list_missing_required_ccu_inputs(
  '9f000000-0000-4000-8000-000000000002',
  DATE '2026-01-01'
);

DO $$
DECLARE
  gate_blocked boolean := false;
BEGIN
  BEGIN
    PERFORM enterprise.assert_part_ccu_inputs_ready(
      '9f000000-0000-4000-8000-000000000002',
      DATE '2026-01-01'
    );
  EXCEPTION
    WHEN check_violation THEN
      gate_blocked := true;
  END;

  IF NOT gate_blocked THEN
    RAISE EXCEPTION
      'Usage gate test failed: incomplete enterprise inputs were accepted';
  END IF;

  RAISE NOTICE
    'Usage gate test passed: incomplete enterprise inputs were blocked';
END
$$;

ROLLBACK;

\echo '6. Integrity error counts: all must be zero'
SELECT
  'unexpected_requirement_total' AS check_name,
  CASE WHEN count(*) = 83 THEN 0 ELSE 1 END AS error_count
FROM customs.ccu_input_requirement requirement
WHERE requirement.record_status = 'ACTIVE'
UNION ALL
SELECT
  'unexpected_required_at_use_total',
  CASE
    WHEN count(*) FILTER (WHERE requirement.required_at_use) = 82
    THEN 0 ELSE 1
  END
FROM customs.ccu_input_requirement requirement
WHERE requirement.record_status = 'ACTIVE'
UNION ALL
SELECT
  'suggested_value_copied_into_empty_slot',
  count(*)
FROM enterprise.part_ccu_input_value value_slot
WHERE value_slot.value_status = 'EMPTY'
  AND value_slot.value_payload IS NOT NULL
UNION ALL
SELECT
  'required_definition_not_verified',
  count(*)
FROM customs.ccu_input_requirement requirement
WHERE requirement.record_status = 'ACTIVE'
  AND requirement.required_at_use
  AND requirement.verification_status <> 'VERIFIED'
UNION ALL
SELECT
  'enterprise_gap_incorrectly_resolved',
  count(*)
FROM audit.missing_data
WHERE field_path LIKE 'enterprise.classification_input[CCU-%]%'
  AND status = 'RESOLVED';
