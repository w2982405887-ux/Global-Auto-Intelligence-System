$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

& (Join-Path $PSScriptRoot "db-migrate-malaysia-vehicle-tax-models.ps1")
& (Join-Path $PSScriptRoot "db-seed-malaysia-vehicle-tax-models.ps1")
& (Join-Path $PSScriptRoot "db-verify-malaysia-vehicle-tax-models.ps1")

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    python (Join-Path $PSScriptRoot "validate_malaysia_vehicle_scenario_dsl.py")
    python -m pytest -q
}
finally {
    Pop-Location
}
