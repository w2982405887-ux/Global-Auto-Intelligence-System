BEGIN;

-- Standalone personal accounts (2026-08-20).
--
-- The existing IAM tables remain available for a future organization mode, but
-- the current product does not require a tenant or membership to log in.  A
-- password hash is optional so OIDC and legacy local-development identities
-- remain compatible.  The application stores only a PBKDF2-SHA256 encoded
-- value; clear-text passwords never enter PostgreSQL.

ALTER TABLE iam.user_account
  ADD COLUMN IF NOT EXISTS password_hash text,
  ADD COLUMN IF NOT EXISTS password_updated_at timestamptz;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'user_account_password_hash_check'
      AND conrelid = 'iam.user_account'::regclass
  ) THEN
    ALTER TABLE iam.user_account
      ADD CONSTRAINT user_account_password_hash_check
      CHECK (password_hash IS NULL OR btrim(password_hash) <> '');
  END IF;
END
$$;

COMMENT ON COLUMN iam.user_account.password_hash IS
  'Optional self-describing PBKDF2-SHA256 hash for a standalone personal account; never clear text.';
COMMENT ON COLUMN iam.user_account.password_updated_at IS
  'UTC time at which the personal-account password was last changed.';

CREATE INDEX IF NOT EXISTS idx_user_account_personal_email
  ON iam.user_account(lower(email))
  WHERE identity_provider = 'personal' AND status <> 'DELETED'::iam.user_status;

DO $$
DECLARE
  expected_checksum char(64) := encode(digest('0013_personal_accounts:v1', 'sha256'), 'hex');
  existing_checksum char(64);
  existing_key text;
BEGIN
  SELECT checksum
  INTO existing_checksum
  FROM platform.schema_migration
  WHERE migration_key = '0013_personal_accounts';

  IF existing_checksum IS NOT NULL THEN
    IF lower(existing_checksum) <> lower(expected_checksum) THEN
      RAISE EXCEPTION
        'Migration 0013_personal_accounts checksum mismatch: database %, expected %',
        existing_checksum, expected_checksum;
    END IF;
    RETURN;
  END IF;

  SELECT migration_key
  INTO existing_key
  FROM platform.schema_migration
  WHERE version = 13;

  IF existing_key IS NOT NULL AND existing_key <> '0013_personal_accounts' THEN
    RAISE EXCEPTION
      'Migration version 13 is already registered as %', existing_key;
  END IF;

  INSERT INTO platform.schema_migration (
    migration_key, version, checksum, notes
  )
  VALUES (
    '0013_personal_accounts', 13, expected_checksum,
    'Standalone personal accounts with optional PBKDF2 password hashes; no organization required.'
  );
END
$$;

COMMIT;
