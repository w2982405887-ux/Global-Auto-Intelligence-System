$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$migration = Join-Path $projectRoot "database\migrations\0005_malaysia_vehicle_tax_models.sql"

Get-Content -Raw -LiteralPath $migration |
  docker compose -f (Join-Path $projectRoot "compose.yaml") exec -T postgres `
    psql -v ON_ERROR_STOP=1 -U gais -d global_auto
