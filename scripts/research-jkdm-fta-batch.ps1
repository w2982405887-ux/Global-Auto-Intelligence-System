param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('ACFTA', 'RCEP')]
  [string]$Regime,
  [Parameter(Mandatory = $true)]
  [string[]]$Hs6Codes,
  [string]$EvidenceDirectory = (
    Join-Path $PSScriptRoot '..\storage\evidence\my\2026-07-29'
  )
)

$ErrorActionPreference = 'Stop'
$baseUri = 'https://ezhs.customs.gov.my/'
$searchUri = 'https://ezhs.customs.gov.my/public-find-hs-data'
$resolvedEvidenceDirectory = [IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $resolvedEvidenceDirectory -Force | Out-Null

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri $baseUri -WebSession $session -UseBasicParsing | Out-Null

$results = foreach ($hs6 in ($Hs6Codes | Sort-Object -Unique)) {
  if ($hs6 -notmatch '^\d{6}$') {
    throw "Invalid HS6 code: $hs6"
  }
  $response = Invoke-WebRequest -Uri $searchUri -Method Post `
    -WebSession $session -UseBasicParsing -Body @{
      hsType = $Regime
      hsCriteria = '1'
      hsKeyword = $hs6
      find_item = 'yes'
    }

  $fileName = "JKDM_HS_Explorer_${Regime}_${hs6}_RATE_2026.html"
  $filePath = Join-Path $resolvedEvidenceDirectory $fileName
  [IO.File]::WriteAllText(
    $filePath, $response.Content, [Text.UTF8Encoding]::new($false)
  )
  [pscustomobject]@{
    regime = $Regime
    hs6 = $hs6
    http_status = [int]$response.StatusCode
    sha256 = (
      Get-FileHash -LiteralPath $filePath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    evidence_path = $filePath
  }
}

$results | Format-Table -AutoSize
