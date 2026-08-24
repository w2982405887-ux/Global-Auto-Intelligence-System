param(
  [Parameter(Mandatory = $true)]
  [string[]]$TariffCodes,
  [string]$EvidenceDirectory = (
    Join-Path $PSScriptRoot '..\storage\evidence\my\2026-07-29'
  )
)

$ErrorActionPreference = 'Stop'
$baseUri = 'https://ezhs.customs.gov.my/'
$controlUri = 'https://ezhs.customs.gov.my/public-larangan'
$resolvedEvidenceDirectory = [IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $resolvedEvidenceDirectory -Force | Out-Null

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri $baseUri -WebSession $session -UseBasicParsing | Out-Null

$results = foreach ($tariffCode in ($TariffCodes | Sort-Object -Unique)) {
  if ($tariffCode -notmatch '^\d{10}$') {
    throw "Invalid Malaysia tariff code: $tariffCode"
  }

  $response = Invoke-WebRequest `
    -Uri $controlUri `
    -Method Post `
    -WebSession $session `
    -Body @{ PDK_KEY = $tariffCode; aa = '1' } `
    -UseBasicParsing

  $fileName = "JKDM_HS_Explorer_Import_Control_$tariffCode.html"
  $filePath = Join-Path $resolvedEvidenceDirectory $fileName
  [IO.File]::WriteAllText(
    $filePath,
    $response.Content,
    [Text.UTF8Encoding]::new($false)
  )

  $plainText = [Net.WebUtility]::HtmlDecode(
    [regex]::Replace($response.Content, '<[^>]+>', ' ')
  )
  $normalizedText = ($plainText -replace '\s+', ' ').Trim()
  [pscustomobject]@{
    tariff_code = $tariffCode
    portal_observation = if (
      $normalizedText -match '(?i)no data|tiada data' -or
      $normalizedText.Length -lt 120
    ) { 'NO_DATA_DISPLAYED' } else { 'CONTROL_DETAIL_DISPLAYED' }
    content_sha256 = (
      Get-FileHash -LiteralPath $filePath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    evidence_path = $filePath
  }
}

$results | Format-Table -AutoSize
