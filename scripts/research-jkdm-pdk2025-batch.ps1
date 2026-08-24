param(
  [string[]]$Hs6Codes = @(
    '854430',
    '870895',
    '940120',
    '700721',
    '851220',
    '841430',
    '870850',
    '870810',
    '870821',
    '870891'
  ),
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

$results = foreach ($hs6 in $Hs6Codes) {
  if ($hs6 -notmatch '^\d{6}$') {
    throw "Invalid HS6 code: $hs6"
  }

  $response = Invoke-WebRequest `
    -Uri $searchUri `
    -Method Post `
    -WebSession $session `
    -Body @{
      hsType = 'PDK'
      hsCriteria = '1'
      hsKeyword = $hs6
      find_item = 'yes'
    } `
    -UseBasicParsing

  $fileName = "JKDM_HS_Explorer_PDK2025_$hs6.html"
  $filePath = Join-Path $resolvedEvidenceDirectory $fileName
  [IO.File]::WriteAllText(
    $filePath,
    $response.Content,
    [Text.UTF8Encoding]::new($false)
  )

  $hash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
  [pscustomobject]@{
    hs6 = $hs6
    http_status = [int]$response.StatusCode
    sha256 = $hash
    evidence_path = $filePath
  }
}

$results | Format-Table -AutoSize
