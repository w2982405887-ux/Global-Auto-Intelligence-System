$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$seedPath = Join-Path $PSScriptRoot "seed_malaysia_five_route_tax_model.py"

if (-not (Test-Path -LiteralPath $seedPath)) {
    throw "Seed script not found: $seedPath"
}

Push-Location $projectRoot
try {
    python $seedPath
}
finally {
    Pop-Location
}
