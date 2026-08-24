$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $projectRoot "compose.yaml"
$migrationPath = Join-Path $projectRoot "database\migrations\0011_iam_core.sql"
$verificationPath = Join-Path $projectRoot "database\queries\verify_0011_iam_core.sql"

foreach ($requiredPath in @($composePath, $migrationPath, $verificationPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required migration file not found: $requiredPath"
    }
}

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) {
    $dockerCommand.Source
} else {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
}

if (-not (Test-Path -LiteralPath $dockerPath)) {
    throw "Docker executable not found. Start Docker Desktop first."
}

$composeArgs = @(
    "compose",
    "--project-directory", $projectRoot,
    "-f", $composePath
)

# 0011 is intentionally not a bootstrap migration.  These representative
# objects prove that 0001--0010 have already been applied before IAM is added.
$preflightSql = @"
SELECT string_agg(required_object, ', ' ORDER BY required_object)
FROM (VALUES
  ('ref.country'::text),
  ('customs.tariff_mapping'::text),
  ('enterprise.part_ccu_input_value'::text),
  ('customs.vehicle_tariff_line'::text),
  ('rules.vehicle_tax_route'::text),
  ('enterprise.decision_project'::text),
  ('customs.vehicle_tariff_rate_line'::text),
  ('enterprise.project_bom_line'::text),
  ('audit.passenger_vehicle_scope_cleanup_20260812'::text)
) AS expected(required_object)
WHERE to_regclass(required_object) IS NULL;
"@

$missingObjects = $preflightSql |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL preflight failed. Confirm the postgres container is running."
}

$missingObjects = ($missingObjects | Out-String).Trim()
if ($missingObjects) {
    throw "0011 requires migrations 0001-0010 first; missing database objects: $missingObjects"
}

Get-Content -LiteralPath $migrationPath -Raw -Encoding UTF8 |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

if ($LASTEXITCODE -ne 0) {
    throw "Migration 0011_iam_core failed. PostgreSQL rolled back the transaction."
}

Get-Content -LiteralPath $verificationPath -Raw -Encoding UTF8 |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

if ($LASTEXITCODE -ne 0) {
    throw "Migration 0011 applied but its read-only verification failed."
}

Write-Output "Migration 0011_iam_core applied and verified."
