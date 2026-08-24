$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$seedPath = Join-Path $projectRoot `
    "database\seeds\0009_first_9_ccu_required_enterprise_inputs.sql"

if (-not (Test-Path -LiteralPath $seedPath)) {
    throw "Seed file not found: $seedPath"
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

Get-Content -LiteralPath $seedPath -Raw -Encoding UTF8 |
    & $dockerPath compose exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
