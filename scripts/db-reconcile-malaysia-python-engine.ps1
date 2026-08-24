$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "reconcile_malaysia_python_engine.py"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Python reconciliation script not found: $scriptPath"
}

Push-Location $projectRoot
try {
    python $scriptPath
}
finally {
    Pop-Location
}
