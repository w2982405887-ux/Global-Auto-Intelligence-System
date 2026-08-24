$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$queryPath = Join-Path $projectRoot "database\queries\verify_utf8_chinese_text.sql"

if (-not (Test-Path -LiteralPath $queryPath)) {
    throw "Verification query not found: $queryPath"
}

Get-Content -LiteralPath $queryPath -Raw -Encoding UTF8 |
    docker compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
