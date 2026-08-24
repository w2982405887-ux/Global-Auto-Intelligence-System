$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$migrationPath = Join-Path $projectRoot "database\migrations\0001_phase1_core.sql"

if (-not (Test-Path -LiteralPath $migrationPath)) {
    throw "Migration file not found: $migrationPath"
}

Get-Content -LiteralPath $migrationPath -Raw -Encoding UTF8 |
    docker compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
