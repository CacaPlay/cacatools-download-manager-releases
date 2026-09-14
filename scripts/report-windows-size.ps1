[CmdletBinding()]
param(
  [string]$OutputDirectory = 'output\size-report'
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "powershell-hash-compat.ps1")
$Output = Join-Path $Root $OutputDirectory
New-Item -ItemType Directory -Force -Path $Output | Out-Null

function File-Entry {
  param([string]$Path, [string]$Category)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  $Item = Get-Item -LiteralPath $Path
  return [pscustomobject][ordered]@{
    category = $Category
    name = $Item.Name
    path = $Item.FullName
    bytes = [int64]$Item.Length
    mebibytes = [math]::Round($Item.Length / 1MB, 2)
    sha256 = (Get-FileHash -LiteralPath $Item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  }
}

$Entries = New-Object System.Collections.Generic.List[object]
$Candidates = @(
  @{ Path = 'src-tauri\target\release\cacatools-desktop.exe'; Category = 'app' },
  @{ Path = 'src-tauri\resources\bin\aria2c.exe'; Category = 'runtime' },
  @{ Path = 'src-tauri\resources\bin\yt-dlp.exe'; Category = 'runtime' },
  @{ Path = 'src-tauri\resources\bin\ffmpeg.exe'; Category = 'runtime' },
  @{ Path = 'src-tauri\resources\bin\ffprobe.exe'; Category = 'runtime' }
)
foreach ($Candidate in $Candidates) {
  $Entry = File-Entry -Path (Join-Path $Root $Candidate.Path) -Category $Candidate.Category
  if ($null -ne $Entry) { [void]$Entries.Add($Entry) }
}

$BundleRoot = Join-Path $Root 'src-tauri\target\release\bundle'
if (Test-Path $BundleRoot) {
  Get-ChildItem $BundleRoot -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in '.exe', '.msi', '.zip' -or $_.Name -like '*.sig' } |
    Sort-Object FullName |
    ForEach-Object {
      $Category = if ($_.Name -like '*.sig') { 'signature' } elseif ($_.Extension -eq '.zip') { 'updater' } else { 'installer' }
      $Entry = File-Entry -Path $_.FullName -Category $Category
      if ($null -ne $Entry) { [void]$Entries.Add($Entry) }
    }
}

$EntryArray = $Entries.ToArray()

function Get-CategoryByteSum {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Items,
    [Parameter(Mandatory = $true)][string]$Category
  )

  $Measurement = $Items |
    Where-Object { $_.category -eq $Category } |
    Measure-Object -Property bytes -Sum

  if ($null -eq $Measurement.Sum) { return [int64]0 }
  return [int64]$Measurement.Sum
}

$RuntimeBytes = Get-CategoryByteSum -Items $EntryArray -Category 'runtime'
$AppBytes = Get-CategoryByteSum -Items $EntryArray -Category 'app'
$Report = [ordered]@{
  generatedAt = (Get-Date).ToUniversalTime().ToString('o')
  version = ((Get-Content (Join-Path $Root 'package.json') -Raw | ConvertFrom-Json).version)
  optimization = [ordered]@{
    rustRelease = 'LTO + opt-level=s + panic=abort + strip + codegen-units=1 (Cargo stable)'
    unusedCommands = 'Tauri removeUnusedCommands=true'
    nsis = 'LZMA'
    webview2 = 'downloadBootstrapper (not embedded)'
    note = 'The four offline engines dominate the installed payload. They remain bundled to preserve offline reliability.'
  }
  totals = [ordered]@{
    appBytes = $AppBytes
    runtimeBytes = $RuntimeBytes
    appMiB = [math]::Round($AppBytes / 1MB, 2)
    runtimeMiB = [math]::Round($RuntimeBytes / 1MB, 2)
  }
  files = @($EntryArray)
}
$ReportPath = Join-Path $Output 'windows-size-report.json'
[IO.File]::WriteAllText($ReportPath, (($Report | ConvertTo-Json -Depth 8) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))

Write-Host "OK: size report written to $ReportPath" -ForegroundColor Green
$EntryArray | Sort-Object -Property bytes -Descending | Format-Table -Property category, name, mebibytes
Write-Host "App: $($Report.totals.appMiB) MiB | Offline runtimes: $($Report.totals.runtimeMiB) MiB"
