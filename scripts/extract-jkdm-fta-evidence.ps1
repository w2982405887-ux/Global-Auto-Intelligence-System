param(
  [string]$EvidenceDirectory = (
    Join-Path $PSScriptRoot '..\storage\evidence\my\2026-07-29'
  ),
  [string]$OutputCsv = (
    Join-Path $PSScriptRoot '..\outputs\malaysia_fta_2026_research_extract.csv'
  )
)

$ErrorActionPreference = 'Stop'
$evidencePath = [IO.Path]::GetFullPath($EvidenceDirectory)
$outputPath = [IO.Path]::GetFullPath($OutputCsv)
New-Item -ItemType Directory -Path (Split-Path -Parent $outputPath) -Force |
  Out-Null

function Convert-HtmlText([string]$value) {
  $withoutTags = [regex]::Replace($value, '(?is)<[^>]+>', ' ')
  return (
    [Net.WebUtility]::HtmlDecode($withoutTags) -replace '\s+', ' '
  ).Trim()
}

$rows = foreach ($file in Get-ChildItem -LiteralPath $evidencePath `
  -Filter 'JKDM_HS_Explorer_*_*_RATE_2026.html') {
  $nameMatch = [regex]::Match(
    $file.BaseName,
    '^JKDM_HS_Explorer_(ACFTA|RCEP)_(\d{6})_RATE_2026$'
  )
  if (-not $nameMatch.Success) { continue }
  $regime = $nameMatch.Groups[1].Value
  $hs6 = $nameMatch.Groups[2].Value
  $html = [IO.File]::ReadAllText($file.FullName)

  foreach ($rowMatch in [regex]::Matches($html, '(?is)<tr[^>]*>(.*?)</tr>')) {
    $cells = @(
      [regex]::Matches($rowMatch.Groups[1].Value, '(?is)<td[^>]*>(.*?)</td>') |
        ForEach-Object { Convert-HtmlText $_.Groups[1].Value }
    )
    if ($cells.Count -lt 6 -or $cells[3] -notmatch '^\d{6,10}$') {
      continue
    }
    [pscustomobject]@{
      regime = $regime
      hs6_query = $hs6
      national_tariff_code = $cells[3]
      description = $cells[4]
      current_rate = $cells[5]
      source_file = $file.Name
      source_sha256 = (
        Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
      ).Hash.ToLowerInvariant()
    }
  }
}

$rows |
  Sort-Object regime, hs6_query, national_tariff_code |
  Export-Csv -LiteralPath $outputPath -NoTypeInformation -Encoding utf8

Write-Output "Extracted FTA rows: $($rows.Count)"
Write-Output "Output: $outputPath"
