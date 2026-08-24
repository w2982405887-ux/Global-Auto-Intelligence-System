BEGIN;

-- Account-bound assistant history.  Conversation IDs remain text so existing
-- client-generated IDs continue to work, while ownership is enforced by the
-- user_id foreign key and every application query.
CREATE SCHEMA IF NOT EXISTS assistant;

CREATE TABLE IF NOT EXISTS assistant.conversation (
  conversation_id text PRIMARY KEY,
  user_id uuid NOT NULL
    REFERENCES iam.user_account(user_id) ON DELETE CASCADE,
  current_organization_id uuid
    REFERENCES iam.organization(organization_id) ON DELETE SET NULL,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'IDLE'
    CHECK (status IN ('IDLE', 'RUNNING', 'ARCHIVED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (btrim(conversation_id) <> '' AND length(conversation_id) <= 80),
  CHECK (btrim(title) <> '')
);

-- PostgreSQL's ``now()`` is transaction-scoped.  The update trigger can
-- therefore be a few milliseconds earlier than an application-supplied
-- created_at during the same transaction; do not reject an otherwise valid
-- row on timestamp ordering.
ALTER TABLE assistant.conversation
  DROP CONSTRAINT IF EXISTS conversation_check;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'assistant_conversation_status_check'
      AND conrelid = 'assistant.conversation'::regclass
  ) THEN
    ALTER TABLE assistant.conversation
      ADD CONSTRAINT assistant_conversation_status_check
      CHECK (status IN ('IDLE', 'RUNNING', 'ARCHIVED'));
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'assistant_conversation_id_check'
      AND conrelid = 'assistant.conversation'::regclass
  ) THEN
    ALTER TABLE assistant.conversation
      ADD CONSTRAINT assistant_conversation_id_check
      CHECK (btrim(conversation_id) <> '' AND length(conversation_id) <= 80);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'assistant_conversation_title_check'
      AND conrelid = 'assistant.conversation'::regclass
  ) THEN
    ALTER TABLE assistant.conversation
      ADD CONSTRAINT assistant_conversation_title_check
      CHECK (btrim(title) <> '');
  END IF;
END
$$;

COMMENT ON TABLE assistant.conversation IS
  'Assistant conversation owned by one account. Organization context is informational for this phase; sharing is not enabled.';
COMMENT ON COLUMN assistant.conversation.user_id IS
  'Durable account owner. Every assistant history read and write must filter by this value.';
COMMENT ON COLUMN assistant.conversation.current_organization_id IS
  'Organization active when the conversation was created; not a sharing boundary in this phase.';

CREATE TABLE IF NOT EXISTS assistant.message (
  message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id text NOT NULL
    REFERENCES assistant.conversation(conversation_id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content text NOT NULL,
  tool_calls jsonb NOT NULL DEFAULT '[]'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (btrim(content) <> '')
);

COMMENT ON TABLE assistant.message IS
  'Durable assistant transcript. It is reachable only through its owner conversation.';

CREATE INDEX IF NOT EXISTS idx_assistant_conversation_user_updated
  ON assistant.conversation(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_assistant_conversation_user_status
  ON assistant.conversation(user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_assistant_message_conversation_created
  ON assistant.message(conversation_id, created_at ASC, message_id ASC);

CREATE OR REPLACE FUNCTION assistant.touch_conversation_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_touch_assistant_conversation_updated_at
  ON assistant.conversation;
CREATE TRIGGER trg_touch_assistant_conversation_updated_at
BEFORE UPDATE ON assistant.conversation
FOR EACH ROW EXECUTE FUNCTION assistant.touch_conversation_updated_at();

DO $$
DECLARE
  expected_checksum char(64) := encode(digest('0012_assistant_history:v1', 'sha256'), 'hex');
  existing_checksum char(64);
  existing_key text;
BEGIN
  SELECT checksum
  INTO existing_checksum
  FROM platform.schema_migration
  WHERE migration_key = '0012_assistant_history';

  IF existing_checksum IS NOT NULL THEN
    IF lower(existing_checksum) <> lower(expected_checksum) THEN
      RAISE EXCEPTION
        'Migration 0012_assistant_history checksum mismatch: database %, expected %',
        existing_checksum, expected_checksum;
    END IF;
    RETURN;
  END IF;

  SELECT migration_key
  INTO existing_key
  FROM platform.schema_migration
  WHERE version = 12;

  IF existing_key IS NOT NULL AND existing_key <> '0012_assistant_history' THEN
    RAISE EXCEPTION
      'Migration version 12 is already registered as %', existing_key;
  END IF;

  INSERT INTO platform.schema_migration (
    migration_key, version, checksum, notes
  )
  VALUES (
    '0012_assistant_history', 12, expected_checksum,
    'Account-bound assistant conversations and messages; organization sharing is disabled.'
  );
END
$$;

COMMIT;
