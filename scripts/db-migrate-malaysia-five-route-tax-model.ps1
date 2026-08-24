$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$migrationPath = Join-Path $projectRoot `
    "database\migrations\0006_malaysia_five_route_tax_model.sql"

if (-not (Test-Path -LiteralPath $migrationPath)) {
    throw "Migration file not found: $migrationPath"
}

Push-Location $projectRoot
try {
    Get-Content -LiteralPath $migrationPath -Raw -Encoding UTF8 |
        docker compose exec -T postgres sh -c `
            'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}
finally {
    Pop-Location
}
