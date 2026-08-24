$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$seedPath = Join-Path $projectRoot "database\seeds\0003_malaysia_battery_rules_and_scenario.sql"

if (-not (Test-Path -LiteralPath $seedPath)) {
    throw "Seed file not found: $seedPath"
}

Get-Content -LiteralPath $seedPath -Raw -Encoding UTF8 |
    docker compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
