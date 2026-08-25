param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Project .env not found: $envPath"
}

$postgres = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
    $trimmed = $line.Trim()
    if ($trimmed -eq "" -or $trimmed.StartsWith("#")) {
        continue
    }
    $parts = $trimmed.Split("=", 2)
    if ($parts.Count -eq 2) {
        $postgres[$parts[0].Trim()] = $parts[1].Trim()
    }
}

# Local convenience: during the OpenClaw smoke test the operator may keep the
# Gateway/model/search secrets in ops/openclaw-local-test/.env.  Root .env
# always wins; this fallback avoids copying secrets into a second file during
# development.  Production should inject the GAIS_* variables from a secret
# manager instead of relying on this local file.
$openclawEnv = @{}
$openclawEnvPath = Join-Path $projectRoot "ops\openclaw-local-test\.env"
if (Test-Path -LiteralPath $openclawEnvPath) {
    foreach ($line in Get-Content -LiteralPath $openclawEnvPath -Encoding UTF8) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -eq 2) {
            $openclawEnv[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
}

$dbUser = if ($postgres.ContainsKey("POSTGRES_USER")) {
    $postgres["POSTGRES_USER"]
} else {
    "gais"
}
$dbName = if ($postgres.ContainsKey("POSTGRES_DB")) {
    $postgres["POSTGRES_DB"]
} else {
    "global_auto"
}
$dbPort = if ($postgres.ContainsKey("POSTGRES_PORT")) {
    $postgres["POSTGRES_PORT"]
} else {
    "5432"
}
if (-not $postgres.ContainsKey("GAIS_DATABASE_URL") -and -not $postgres.ContainsKey("POSTGRES_PASSWORD")) {
    throw "POSTGRES_PASSWORD is missing from project .env"
}

$configuredDatabaseUrl = if ($postgres.ContainsKey("GAIS_DATABASE_URL")) {
    $postgres["GAIS_DATABASE_URL"]
} else {
    $null
}
if (-not [string]::IsNullOrWhiteSpace($configuredDatabaseUrl)) {
    # A server may use a managed or remote PostgreSQL instance.  Preserve the
    # full URL instead of rebuilding it as a local loopback connection.
    $env:GAIS_DATABASE_URL = $configuredDatabaseUrl
} else {
    $dbHost = if ($postgres.ContainsKey("POSTGRES_HOST")) {
        $postgres["POSTGRES_HOST"]
    } else {
        "127.0.0.1"
    }
    $encodedUser = [uri]::EscapeDataString($dbUser)
    $encodedPassword = [uri]::EscapeDataString($postgres["POSTGRES_PASSWORD"])
    $env:GAIS_DATABASE_URL = "postgresql+psycopg://${encodedUser}:${encodedPassword}@${dbHost}:${dbPort}/${dbName}"
}
$env:GAIS_CALCULATION_DSL_PATH = Join-Path $projectRoot "spec\calculation_dsl.schema.json"
# Never keep provider credentials in this launcher.  Put them in the local
# .env (or inject them from the server secret store) and forward only the
# values that are present.
$env:AUTOPOLICY_LLM_PROVIDER = if ($postgres.ContainsKey("AUTOPOLICY_LLM_PROVIDER")) { $postgres["AUTOPOLICY_LLM_PROVIDER"] } else { "openai" }
$env:AUTOPOLICY_LLM_MODEL = if ($postgres.ContainsKey("AUTOPOLICY_LLM_MODEL")) { $postgres["AUTOPOLICY_LLM_MODEL"] } else { "deepseek-v4-pro" }
$env:AUTOPOLICY_LLM_API_KEY = if ($postgres.ContainsKey("AUTOPOLICY_LLM_API_KEY")) { $postgres["AUTOPOLICY_LLM_API_KEY"] } else { "" }
$env:AUTOPOLICY_LLM_BASE_URL = if ($postgres.ContainsKey("AUTOPOLICY_LLM_BASE_URL")) { $postgres["AUTOPOLICY_LLM_BASE_URL"] } else { "https://api.deepseek.com" }

$env:GAIS_OPENCLAW_ENABLED = if ($postgres.ContainsKey("GAIS_OPENCLAW_ENABLED")) { $postgres["GAIS_OPENCLAW_ENABLED"] } elseif ($openclawEnv.ContainsKey("GAIS_OPENCLAW_ENABLED")) { $openclawEnv["GAIS_OPENCLAW_ENABLED"] } else { "false" }
$env:GAIS_OPENCLAW_BASE_URL = if ($postgres.ContainsKey("GAIS_OPENCLAW_BASE_URL")) { $postgres["GAIS_OPENCLAW_BASE_URL"] } elseif ($openclawEnv.ContainsKey("GAIS_OPENCLAW_BASE_URL")) { $openclawEnv["GAIS_OPENCLAW_BASE_URL"] } else { "http://127.0.0.1:18789" }
$env:GAIS_OPENCLAW_GATEWAY_TOKEN = if ($postgres.ContainsKey("GAIS_OPENCLAW_GATEWAY_TOKEN")) { $postgres["GAIS_OPENCLAW_GATEWAY_TOKEN"] } elseif ($openclawEnv.ContainsKey("GAIS_OPENCLAW_GATEWAY_TOKEN")) { $openclawEnv["GAIS_OPENCLAW_GATEWAY_TOKEN"] } elseif ($openclawEnv.ContainsKey("OPENCLAW_GATEWAY_TOKEN")) { $openclawEnv["OPENCLAW_GATEWAY_TOKEN"] } else { "" }
$env:GAIS_OPENCLAW_MODEL = if ($postgres.ContainsKey("GAIS_OPENCLAW_MODEL")) { $postgres["GAIS_OPENCLAW_MODEL"] } elseif ($openclawEnv.ContainsKey("GAIS_OPENCLAW_MODEL")) { $openclawEnv["GAIS_OPENCLAW_MODEL"] } else { "openclaw/default" }
$env:GAIS_OPENCLAW_UPSTREAM_MODEL = if ($postgres.ContainsKey("GAIS_OPENCLAW_UPSTREAM_MODEL")) { $postgres["GAIS_OPENCLAW_UPSTREAM_MODEL"] } elseif ($openclawEnv.ContainsKey("GAIS_OPENCLAW_UPSTREAM_MODEL")) { $openclawEnv["GAIS_OPENCLAW_UPSTREAM_MODEL"] } else { "" }
$env:GAIS_WEB_SEARCH_PROVIDER = if ($postgres.ContainsKey("GAIS_WEB_SEARCH_PROVIDER")) { $postgres["GAIS_WEB_SEARCH_PROVIDER"] } elseif ($openclawEnv.ContainsKey("GAIS_WEB_SEARCH_PROVIDER")) { $openclawEnv["GAIS_WEB_SEARCH_PROVIDER"] } else { "brave" }
$env:GAIS_BRAVE_API_KEY = if ($postgres.ContainsKey("GAIS_BRAVE_API_KEY")) { $postgres["GAIS_BRAVE_API_KEY"] } elseif ($openclawEnv.ContainsKey("GAIS_BRAVE_API_KEY")) { $openclawEnv["GAIS_BRAVE_API_KEY"] } elseif ($openclawEnv.ContainsKey("BRAVE_API_KEY")) { $openclawEnv["BRAVE_API_KEY"] } else { "" }
$env:GAIS_TAVILY_API_KEY = if ($postgres.ContainsKey("GAIS_TAVILY_API_KEY")) { $postgres["GAIS_TAVILY_API_KEY"] } elseif ($openclawEnv.ContainsKey("GAIS_TAVILY_API_KEY")) { $openclawEnv["GAIS_TAVILY_API_KEY"] } elseif ($openclawEnv.ContainsKey("TAVILY_API_KEY")) { $openclawEnv["TAVILY_API_KEY"] } else { "" }
$env:GAIS_SEARXNG_BASE_URL = if ($postgres.ContainsKey("GAIS_SEARXNG_BASE_URL")) { $postgres["GAIS_SEARXNG_BASE_URL"] } elseif ($openclawEnv.ContainsKey("GAIS_SEARXNG_BASE_URL")) { $openclawEnv["GAIS_SEARXNG_BASE_URL"] } else { "" }

function Test-OpenClawHttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,
        [Parameter(Mandatory = $true)]
        [string]$GatewayToken,
        [int]$TimeoutMilliseconds = 1500
    )

    if ([string]::IsNullOrWhiteSpace($BaseUrl) -or [string]::IsNullOrWhiteSpace($GatewayToken)) {
        return $false
    }

    $httpClient = $null
    $response = $null
    try {
        $httpClient = [System.Net.Http.HttpClient]::new()
        $httpClient.Timeout = [TimeSpan]::FromMilliseconds($TimeoutMilliseconds)
        $httpClient.DefaultRequestHeaders.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $GatewayToken)
        $modelsUrl = $BaseUrl.TrimEnd("/") + "/v1/models"
        $response = $httpClient.GetAsync($modelsUrl).GetAwaiter().GetResult()
        # A listening Docker-published port is not sufficient: only a successful
        # authenticated Gateway API response means the service is ready.
        return $response.StatusCode -eq [System.Net.HttpStatusCode]::OK
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $response) {
            $response.Dispose()
        }
        if ($null -ne $httpClient) {
            $httpClient.Dispose()
        }
    }
}

function Ensure-OpenClawGateway {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComposeFile,
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,
        [Parameter(Mandatory = $true)]
        [string]$GatewayToken,
        [int]$TimeoutSeconds = 90
    )

    $openClawUri = $null
    try {
        $openClawUri = [Uri]$BaseUrl
    }
    catch {
        Write-Warning "OpenClaw Gateway is enabled, but GAIS_OPENCLAW_BASE_URL is invalid; continuing with the business backend."
        return
    }

    $localHosts = @("localhost", "127.0.0.1", "::1")
    $configuredHost = $openClawUri.Host.TrimStart("[").TrimEnd("]").ToLowerInvariant()
    $isLocalGateway = ($localHosts -contains $configuredHost) -and ($openClawUri.Port -eq 18789) -and ($openClawUri.Scheme -in @("http", "https"))

    if (-not $isLocalGateway) {
        if (Test-OpenClawHttpReady -BaseUrl $BaseUrl -GatewayToken $GatewayToken) {
            Write-Host "OpenClaw Gateway is ready at the configured endpoint; local Docker Compose startup is not needed."
        }
        else {
            Write-Warning "OpenClaw Gateway is enabled but the configured remote/private endpoint is not ready; local Docker Compose startup was skipped. Continuing with the business backend."
        }
        return
    }

    if (Test-OpenClawHttpReady -BaseUrl $BaseUrl -GatewayToken $GatewayToken) {
        Write-Host "OpenClaw Gateway is ready at the configured loopback endpoint; skipping Docker Compose startup."
        return
    }

    if (-not (Test-Path -LiteralPath $ComposeFile)) {
        Write-Warning "OpenClaw Gateway is enabled, but its local Compose file was not found; continuing with the business backend."
        return
    }

    if ($null -eq (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Warning "OpenClaw Gateway is enabled, but Docker is unavailable; continuing with the business backend."
        return
    }

    $composeExitCode = 1
    $composeDirectory = Split-Path -Parent $ComposeFile
    try {
        Push-Location $composeDirectory
        # Start only the named gateway service.  We reach this branch only when
        # the loopback Gateway is not ready, so a healthy existing service is never
        # rebuilt on every backend restart.
        & docker compose -f $ComposeFile up -d gateway *> $null
        $composeExitCode = $LASTEXITCODE
    }
    catch {
        $composeExitCode = 1
    }
    finally {
        Pop-Location
    }

    if ($composeExitCode -ne 0) {
        Write-Warning "OpenClaw Gateway could not be started by Docker Compose; continuing with the business backend."
        return
    }

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-OpenClawHttpReady -BaseUrl $BaseUrl -GatewayToken $GatewayToken) {
            Write-Host "OpenClaw Gateway is ready at the configured loopback endpoint."
            return
        }
        Start-Sleep -Seconds 1
    }

    Write-Warning "OpenClaw Gateway did not become ready within ${TimeoutSeconds}s; continuing with the business backend."
}

if ($env:GAIS_OPENCLAW_ENABLED -ieq "true") {
    # A cold OpenClaw start on Docker Desktop can take close to a minute while
    # provider plugins and runtime configuration are initialized.
    $openClawTimeoutSeconds = 90
    $configuredTimeout = if ($postgres.ContainsKey("GAIS_OPENCLAW_STARTUP_TIMEOUT_SECONDS")) {
        $postgres["GAIS_OPENCLAW_STARTUP_TIMEOUT_SECONDS"]
    }
    elseif ($openclawEnv.ContainsKey("GAIS_OPENCLAW_STARTUP_TIMEOUT_SECONDS")) {
        $openclawEnv["GAIS_OPENCLAW_STARTUP_TIMEOUT_SECONDS"]
    }
    else {
        $null
    }
    $parsedTimeout = 0
    if ([int]::TryParse([string]$configuredTimeout, [ref]$parsedTimeout)) {
        $openClawTimeoutSeconds = [Math]::Min([Math]::Max($parsedTimeout, 5), 120)
    }

    Ensure-OpenClawGateway `
        -ComposeFile (Join-Path $projectRoot "ops\openclaw-local-test\compose.yaml") `
        -BaseUrl $env:GAIS_OPENCLAW_BASE_URL `
        -GatewayToken $env:GAIS_OPENCLAW_GATEWAY_TOKEN `
        -TimeoutSeconds $openClawTimeoutSeconds
}

Push-Location $projectRoot
try {
    python -m uvicorn app.main:app --app-dir backend --host $BindHost --port $Port
}
finally {
    Pop-Location
}
