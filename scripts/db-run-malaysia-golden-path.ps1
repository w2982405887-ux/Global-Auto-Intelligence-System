$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$calculationPath = Join-Path $projectRoot "database\calculations\run_malaysia_golden_path.sql"

if (-not (Test-Path -LiteralPath $calculationPath)) {
    throw "Calculation script not found: $calculationPath"
}

Get-Content -LiteralPath $calculationPath -Raw -Encoding UTF8 |
    docker compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
