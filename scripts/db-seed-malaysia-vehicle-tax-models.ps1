$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    python (Join-Path $PSScriptRoot "seed_malaysia_vehicle_tax_models.py")
}
finally {
    Pop-Location
}
