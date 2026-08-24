$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

& (Join-Path $PSScriptRoot "db-seed-phase1-60-ccu-fta.ps1")
& (Join-Path $PSScriptRoot "db-verify-phase1-60-ccu-fta.ps1")
& (Join-Path $PSScriptRoot "db-reconcile-malaysia-python-engine.ps1")
