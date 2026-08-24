-- Read-only verification for database/migrations/0012_assistant_history.sql.
BEGIN;

DO $$
DECLARE
  expected_checksum text := encode(digest('0012_assistant_history:v1', 'sha256'), 'hex');
  actual_checksum text;
  required_table text;
BEGIN
  IF to_regclass('platform.schema_migration') IS NULL THEN
    RAISE EXCEPTION 'platform.schema_migration is missing';
  END IF;

  SELECT checksum
  INTO actual_checksum
  FROM platform.schema_migration
  WHERE migration_key = '0012_assistant_history';

  IF actual_checksum IS NULL OR lower(actual_checksum) <> lower(expected_checksum) THEN
    RAISE EXCEPTION
      '0012 registration is missing or has checksum %, expected %',
      actual_checksum, expected_checksum;
  END IF;

  FOREACH required_table IN ARRAY ARRAY[
    'assistant.conversation',
    'assistant.message'
  ] LOOP
    IF to_regclass(required_table) IS NULL THEN
      RAISE EXCEPTION 'Required assistant history table is missing: %', required_table;
    END IF;
  END LOOP;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'assistant'
      AND table_name = 'conversation'
      AND column_name = 'user_id'
  ) THEN
    RAISE EXCEPTION 'assistant.conversation.user_id is missing';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'assistant'
      AND table_name = 'message'
      AND column_name = 'conversation_id'
  ) THEN
    RAISE EXCEPTION 'assistant.message.conversation_id is missing';
  END IF;

  RAISE NOTICE '0012 assistant history verification passed';
END
$$;

SELECT migration_key, version, checksum, applied_at, applied_by
FROM platform.schema_migration
WHERE migration_key = '0012_assistant_history';

SELECT table_schema, table_name
FROM information_schema.tables
WHERE (table_schema, table_name) IN (
  ('assistant', 'conversation'),
  ('assistant', 'message')
)
ORDER BY table_name;

ROLLBACK;
