$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

python (Join-Path $PSScriptRoot "seed_phase1_60_ccu_fta_mapping.py")
