param(
  [string]$SpotdlPath = (Join-Path $PSScriptRoot '..\..\src-tauri\resources\bin\spotdl-4.5.2-win32.exe'),
  [string]$FfmpegPath = (Join-Path $PSScriptRoot '..\..\src-tauri\resources\bin\ffmpeg.exe'),
  [string]$OutputRoot = (Join-Path $env:TEMP ('cacatools-0221-benchmark-' + [guid]::NewGuid().ToString('N')))
)

throw 'Spotify está desactivado temporalmente. Esta versión de CacaTools no ejecuta spotDL.'
