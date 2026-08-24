param(
  [string]$EvidenceDirectory = (
    Join-Path $PSScriptRoot '..\storage\evidence\my\2026-07-29'
  )
)

$ErrorActionPreference = 'Stop'
$baseUri = 'https://ezhs.customs.gov.my/'
$controlUri = 'https://ezhs.customs.gov.my/public-larangan'
$resolvedEvidenceDirectory = [IO.Path]::GetFullPath($EvidenceDirectory)

$targets = @(
  @{ code = '8544301200'; row = '2' },
  @{ code = '8544301400'; row = '4' },
  @{ code = '8708951000'; row = '2' },
  @{ code = '8708959000'; row = '3' },
  @{ code = '9401201000'; row = '2' },
  @{ code = '7007211000'; row = '2' },
  @{ code = '8512202000'; row = '2' },
  @{ code = '8512209900'; row = '4' },
  @{ code = '8414304000'; row = '2' },
  @{ code = '8414309000'; row = '3' },
  @{ code = '8708501100'; row = '2' },
  @{ code = '8708502600'; row = '7' },
  @{ code = '8708109000'; row = '3' },
  @{ code = '8708210000'; row = '1' },
  @{ code = '8708911600'; row = '3' },
  @{ code = '8708919500'; row = '10' }
)

New-Item -ItemType Directory -Path $resolvedEvidenceDirectory -Force | Out-Null

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -Uri $baseUri -WebSession $session -UseBasicParsing | Out-Null

$results = foreach ($target in $targets) {
  $response = Invoke-WebRequest `
    -Uri $controlUri `
    -Method Post `
    -WebSession $session `
    -Body @{
      PDK_KEY = $target.code
      aa = $target.row
    } `
    -UseBasicParsing

  $fileName = "JKDM_HS_Explorer_Import_Control_$($target.code).html"
  $filePath = Join-Path $resolvedEvidenceDirectory $fileName
  [IO.File]::WriteAllText(
    $filePath,
    $response.Content,
    [Text.UTF8Encoding]::new($false)
  )

  $hash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
  $plainText = [Net.WebUtility]::HtmlDecode(
    [regex]::Replace($response.Content, '<[^>]+>', ' ')
  )
  $normalizedText = ($plainText -replace '\s+', ' ').Trim()
  $observation = if (
    $normalizedText -match '(?i)no data|tiada data' -or
    $normalizedText.Length -lt 120
  ) {
    'NO_DATA_DISPLAYED'
  } else {
    'CONTROL_DETAIL_DISPLAYED'
  }

  [pscustomobject]@{
    tariff_code = $target.code
    portal_observation = $observation
    sha256 = $hash
    evidence_path = $filePath
  }
}

$results | Format-Table -AutoSize
