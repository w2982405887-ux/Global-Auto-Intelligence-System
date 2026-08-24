$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "build_malaysia_60_ccu_bom_package.py"

Push-Location $projectRoot
try {
    python $scriptPath
}
finally {
    Pop-Location
}
