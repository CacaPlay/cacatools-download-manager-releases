param(
  [Parameter(Mandatory = $true)][string]$Executable
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$resolvedExecutable = (Resolve-Path -LiteralPath $Executable).Path
$smokeRoot = Join-Path $env:TEMP ('cacatools-background-smoke-' + [Guid]::NewGuid().ToString('N'))
$dataDir = Join-Path $smokeRoot 'data'
$downloadsDir = Join-Path $smokeRoot 'downloads'
New-Item -ItemType Directory -Path $smokeRoot -Force | Out-Null

$oldData = [Environment]::GetEnvironmentVariable('CACATOOLS_DATA_DIR', 'Process')
$oldDownloads = [Environment]::GetEnvironmentVariable('CACATOOLS_DOWNLOADS_DIR', 'Process')
$process = $null
try {
  Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class CacaToolsWindowProbe {
  [DllImport("user32.dll")]
  public static extern bool IsWindowVisible(IntPtr handle);
  [DllImport("user32.dll")]
  public static extern bool GetWindowRect(IntPtr handle, out RECT rect);
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
'@
  $env:CACATOOLS_DATA_DIR = $dataDir
  $env:CACATOOLS_DOWNLOADS_DIR = $downloadsDir
  $process = Start-Process -FilePath $resolvedExecutable -ArgumentList '--background' -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 8
  $process.Refresh()
  $rect = New-Object CacaToolsWindowProbe+RECT
  [void][CacaToolsWindowProbe]::GetWindowRect($process.MainWindowHandle, [ref]$rect)
  $isVisible = [CacaToolsWindowProbe]::IsWindowVisible($process.MainWindowHandle)
  if ($process.HasExited) { throw "El proceso en segundo plano terminó con código $($process.ExitCode)." }
  $windowWidth = $rect.Right - $rect.Left
  $windowHeight = $rect.Bottom - $rect.Top
  # WebView2 can expose a tiny 16x16 helper window as MainWindowHandle even
  # while the real app window is hidden. Only a normal-sized visible surface
  # counts as an unexpected startup window.
  $visible = $process.MainWindowHandle -ne 0 -and $isVisible -and $windowWidth -ge 320 -and $windowHeight -ge 200
  if ($visible) { throw 'El arranque en segundo plano mostró una ventana.' }
  if (-not (Test-Path (Join-Path $dataDir 'cacatools.sqlite3'))) { throw 'El arranque no inicializó la base local.' }
  Write-Host "OK: arranque en segundo plano sin ventana; PID $($process.Id)."
}
finally {
  if ($process -and -not $process.HasExited) { & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null }
  if ($null -eq $oldData) { Remove-Item Env:CACATOOLS_DATA_DIR -ErrorAction SilentlyContinue } else { $env:CACATOOLS_DATA_DIR = $oldData }
  if ($null -eq $oldDownloads) { Remove-Item Env:CACATOOLS_DOWNLOADS_DIR -ErrorAction SilentlyContinue } else { $env:CACATOOLS_DOWNLOADS_DIR = $oldDownloads }
  Remove-Item -LiteralPath $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue
}
