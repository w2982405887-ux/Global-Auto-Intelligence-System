$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$seedPath = Join-Path $projectRoot "database\seeds\0011_malaysia_golden_path_demo.sql"

if (-not (Test-Path -LiteralPath $seedPath)) {
    throw "Seed script not found: $seedPath"
}

Get-Content -LiteralPath $seedPath -Raw -Encoding UTF8 |
    docker compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
