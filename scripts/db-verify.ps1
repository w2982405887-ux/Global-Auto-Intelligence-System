$ErrorActionPreference = "Stop"

$query = @'
SELECT table_schema, count(*) AS table_count
FROM information_schema.tables
WHERE table_schema IN
  ('ref', 'evidence', 'rules', 'customs', 'enterprise', 'calc', 'audit', 'ai')
  AND table_type = 'BASE TABLE'
GROUP BY table_schema
ORDER BY table_schema;
'@

$query |
    docker compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
