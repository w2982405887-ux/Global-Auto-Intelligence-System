-- Read-only verification for database/migrations/0013_personal_accounts.sql.
BEGIN;

DO $$
DECLARE
  expected_checksum text := encode(digest('0013_personal_accounts:v1', 'sha256'), 'hex');
  actual_checksum text;
  required_column text;
BEGIN
  IF to_regclass('platform.schema_migration') IS NULL
     OR to_regclass('iam.user_account') IS NULL THEN
    RAISE EXCEPTION '0013 prerequisites are missing';
  END IF;

  SELECT checksum
  INTO actual_checksum
  FROM platform.schema_migration
  WHERE migration_key = '0013_personal_accounts';

  IF actual_checksum IS NULL OR lower(actual_checksum) <> lower(expected_checksum) THEN
    RAISE EXCEPTION
      '0013 registration is missing or has checksum %, expected %',
      actual_checksum, expected_checksum;
  END IF;

  FOREACH required_column IN ARRAY ARRAY['password_hash', 'password_updated_at'] LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'iam'
        AND table_name = 'user_account'
        AND column_name = required_column
    ) THEN
      RAISE EXCEPTION 'Required personal-account column is missing: %', required_column;
    END IF;
  END LOOP;

  RAISE NOTICE '0013 personal-account verification passed';
END
$$;

SELECT migration_key, version, checksum, applied_at, applied_by
FROM platform.schema_migration
WHERE migration_key = '0013_personal_accounts';

ROLLBACK;
