$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "compile_malaysia_bom_input.py"

Push-Location $projectRoot
try {
    python $scriptPath
}
finally {
    Pop-Location
}
