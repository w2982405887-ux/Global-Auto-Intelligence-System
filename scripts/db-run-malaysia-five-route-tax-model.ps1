$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    docker compose up -d postgres

    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        docker compose exec -T postgres sh -c `
            'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' *> $null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw "PostgreSQL did not become ready within 30 seconds."
    }

    & (Join-Path $PSScriptRoot `
        "db-migrate-malaysia-five-route-tax-model.ps1")
    & (Join-Path $PSScriptRoot `
        "db-seed-malaysia-five-route-tax-model.ps1")
    & (Join-Path $PSScriptRoot `
        "db-verify-malaysia-five-route-tax-model.ps1")
}
finally {
    Pop-Location
}
