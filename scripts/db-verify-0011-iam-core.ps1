$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$composePath = Join-Path $projectRoot "compose.yaml"
$queryPath = Join-Path $projectRoot "database\queries\verify_0011_iam_core.sql"

foreach ($requiredPath in @($composePath, $queryPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required verification file not found: $requiredPath"
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

Get-Content -LiteralPath $queryPath -Raw -Encoding UTF8 |
    & $dockerPath @composeArgs exec -T postgres sh -c `
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

if ($LASTEXITCODE -ne 0) {
    throw "0011 IAM verification failed."
}
