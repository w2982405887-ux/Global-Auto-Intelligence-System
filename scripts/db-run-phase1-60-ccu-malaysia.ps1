$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

& (Join-Path $PSScriptRoot "db-seed-phase1-ccu-21-60.ps1")
& (Join-Path $PSScriptRoot "db-seed-phase1-ccu-21-60-required-inputs.ps1")
& (Join-Path $PSScriptRoot "db-seed-phase1-ccu-21-60-pdk-mapping.ps1")
& (Join-Path $PSScriptRoot "db-normalize-pdk2025-version-key.ps1")

& (Join-Path $PSScriptRoot "db-verify-phase1-60-ccu-scope.ps1")
& (Join-Path $PSScriptRoot "db-verify-phase1-ccu-21-60-required-inputs.ps1")
& (Join-Path $PSScriptRoot "db-verify-phase1-ccu-21-60-pdk-mapping.ps1")
