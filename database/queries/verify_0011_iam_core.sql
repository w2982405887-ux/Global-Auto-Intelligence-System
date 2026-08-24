-- Read-only verification for database/migrations/0011_iam_core.sql.
-- Run with psql -v ON_ERROR_STOP=1.  The transaction is rolled back.
BEGIN;

DO $$
DECLARE
  expected_checksum text := encode(digest('0011_iam_core:v1', 'sha256'), 'hex');
  actual_checksum text;
  role_count integer;
  permission_count integer;
  mapping_count integer;
  required_table text;
BEGIN
  IF to_regclass('platform.schema_migration') IS NULL THEN
    RAISE EXCEPTION 'platform.schema_migration is missing';
  END IF;

  SELECT checksum
  INTO actual_checksum
  FROM platform.schema_migration
  WHERE migration_key = '0011_iam_core';

  IF actual_checksum IS NULL OR lower(actual_checksum) <> lower(expected_checksum) THEN
    RAISE EXCEPTION
      '0011_iam_core registration is missing or has checksum %, expected %',
      actual_checksum, expected_checksum;
  END IF;

  FOREACH required_table IN ARRAY ARRAY[
    'iam.user_account',
    'iam.organization',
    'iam.organization_membership',
    'iam.role',
    'iam.permission',
    'iam.role_permission',
    'iam.membership_role',
    'iam.session',
    'iam.invitation'
  ] LOOP
    IF to_regclass(required_table) IS NULL THEN
      RAISE EXCEPTION 'Required IAM table is missing: %', required_table;
    END IF;
  END LOOP;

  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'iam'
      AND table_name = 'session'
      AND column_name = 'current_organization_id'
  ) THEN
    RAISE EXCEPTION 'iam.session.current_organization_id is missing';
  END IF;

  SELECT count(*) INTO role_count FROM iam.role;
  SELECT count(*) INTO permission_count FROM iam.permission;
  SELECT count(*) INTO mapping_count FROM iam.role_permission;

  IF role_count < 8 THEN
    RAISE EXCEPTION 'Expected at least 8 seeded roles, found %', role_count;
  END IF;
  IF permission_count < 25 THEN
    RAISE EXCEPTION 'Expected at least 25 seeded permissions, found %', permission_count;
  END IF;
  IF mapping_count = 0 THEN
    RAISE EXCEPTION 'Seeded role_permission mapping is empty';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM iam.role
    WHERE role_key = 'system_admin' AND role_scope = 'SYSTEM'
  ) THEN
    RAISE EXCEPTION 'system_admin role seed is missing';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM iam.role_permission rp
    JOIN iam.role r ON r.role_id = rp.role_id
    JOIN iam.permission p ON p.permission_id = rp.permission_id
    WHERE r.role_key = 'system_admin' AND p.permission_key = 'system.manage'
  ) THEN
    RAISE EXCEPTION 'system_admin/system.manage seed mapping is missing';
  END IF;

  RAISE NOTICE '0011 IAM verification passed: %, roles; %, permissions; %, role mappings',
    role_count, permission_count, mapping_count;
END
$$;

SELECT
  migration_key,
  version,
  checksum,
  applied_at,
  applied_by
FROM platform.schema_migration
WHERE migration_key = '0011_iam_core';

SELECT role_key, role_scope
FROM iam.role
ORDER BY role_key;

SELECT permission_key, resource_key, action_key
FROM iam.permission
ORDER BY permission_key;

ROLLBACK;
