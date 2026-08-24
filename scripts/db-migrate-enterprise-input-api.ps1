$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$migrationPath = Join-Path $projectRoot `
    "database\migrations\0003_enterprise_input_collection_api.sql"

if (-not (Test-Path -LiteralPath $migrationPath)) {
    throw "Migration file not found: $migrationPath"
}

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) {
    $dockerCommand.Source
} else {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
}

if (-not (Test-Path -LiteralPath $dockerPath)) {
    throw "Docker executable not found."
}

Get-Content -LiteralPath $migrationPath -Raw -Encoding UTF8 |
    & $dockerPath compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
