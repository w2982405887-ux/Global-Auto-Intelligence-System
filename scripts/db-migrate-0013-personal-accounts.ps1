$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $projectRoot "compose.yaml"
$migrationPath = Join-Path $projectRoot "database\migrations\0013_personal_accounts.sql"
$verificationPath = Join-Path $projectRoot "database\queries\verify_0013_personal_accounts.sql"

foreach ($requiredPath in @($composePath, $migrationPath, $verificationPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required migration file not found: $requiredPath"
    }
}

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { "C:\Program Files\Docker\Docker\resources\bin\docker.exe" }
if (-not (Test-Path -LiteralPath $dockerPath)) {
    throw "Docker executable not found. Start Docker Desktop first."
}

$composeArgs = @("compose", "--project-directory", $projectRoot, "-f", $composePath)
$preflightSql = @"
SELECT string_agg(required_object, ', ' ORDER BY required_object)
FROM (VALUES
  ('platform.schema_migration'::text),
  ('iam.user_account'::text),
  ('iam.session'::text)
) AS expected(required_object)
WHERE to_regclass(required_object) IS NULL;
"@

$missingObjects = $preflightSql |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL preflight failed." }
$missingObjects = ($missingObjects | Out-String).Trim()
if ($missingObjects) { throw "0013 requires IAM migration 0011 first; missing: $missingObjects" }

Get-Content -LiteralPath $migrationPath -Raw -Encoding UTF8 |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) { throw "Migration 0013_personal_accounts failed." }

Get-Content -LiteralPath $verificationPath -Raw -Encoding UTF8 |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) { throw "Migration 0013 applied but verification failed." }

Write-Output "Migration 0013_personal_accounts applied and verified."
