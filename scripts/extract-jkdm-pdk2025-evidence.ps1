param(
  [string]$EvidenceDirectory = (
    Join-Path $PSScriptRoot '..\storage\evidence\my\2026-07-29'
  ),
  [string]$OutputCsv = (
    Join-Path $PSScriptRoot '..\outputs\malaysia_pdk2025_research_extract.csv'
  )
)

$ErrorActionPreference = 'Stop'
$evidencePath = [IO.Path]::GetFullPath($EvidenceDirectory)
$outputPath = [IO.Path]::GetFullPath($OutputCsv)
$outputDirectory = Split-Path -Parent $outputPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

function Convert-HtmlText([string]$value) {
  $withoutTags = [regex]::Replace($value, '(?is)<[^>]+>', ' ')
  $decoded = [Net.WebUtility]::HtmlDecode($withoutTags)
  return ($decoded -replace '\s+', ' ').Trim()
}

$rows = foreach ($file in Get-ChildItem -LiteralPath $evidencePath -Filter 'JKDM_HS_Explorer_PDK2025_*.html') {
  $hs6 = [regex]::Match($file.BaseName, '(\d{6})$').Groups[1].Value
  if (-not $hs6) { continue }

  $html = [IO.File]::ReadAllText($file.FullName)
  $rowIndex = 0
  foreach ($rowMatch in [regex]::Matches($html, '(?is)<tr[^>]*>(.*?)</tr>')) {
    $rowIndex++
    $rowHtml = $rowMatch.Groups[1].Value
    $prefix = [regex]::Match(
      $rowHtml,
      '(?is)^\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*)$'
    )
    if (-not $prefix.Success) { continue }

    $header = Convert-HtmlText $prefix.Groups[1].Value
    $sub = Convert-HtmlText $prefix.Groups[2].Value
    $item = Convert-HtmlText $prefix.Groups[3].Value
    $unit = Convert-HtmlText $prefix.Groups[4].Value
    if ($header -notmatch '^\d{4}$' -or $sub -notmatch '^\d{2}$' -or $item -notmatch '^\d{4}$') {
      continue
    }

    $tail = $prefix.Groups[5].Value
    $descriptionMatch = [regex]::Match($tail, '(?is)<a[^>]*>(.*?)</a>')
    if (-not $descriptionMatch.Success) { continue }
    $description = Convert-HtmlText $descriptionMatch.Groups[1].Value

    $afterDescription = $tail.Substring(
      $descriptionMatch.Index + $descriptionMatch.Length
    )
    $rateCells = @(
      [regex]::Matches($afterDescription, '(?is)<td>(.*?)</td>') |
        ForEach-Object { Convert-HtmlText $_.Groups[1].Value }
    )
    while ($rateCells.Count -lt 10) { $rateCells += '' }

    [pscustomobject]@{
      hs6_query = $hs6
      national_tariff_code = "$header$sub$item"
      unit = $unit
      description = $description
      import_rate = $rateCells[0]
      export_rate = $rateCells[1]
      trq = $rateCells[2]
      sst = $rateCells[3]
      excise = $rateCells[4]
      cess_1 = $rateCells[5]
      cess_2 = $rateCells[6]
      cess_3 = $rateCells[7]
      source_file = $file.Name
      source_sha256 = (
        Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256
      ).Hash.ToLowerInvariant()
    }
  }
}

$rows |
  Sort-Object hs6_query, national_tariff_code |
  Export-Csv -LiteralPath $outputPath -NoTypeInformation -Encoding utf8

Write-Output "Extracted rows: $($rows.Count)"
Write-Output "Output: $outputPath"
