param([string]$Version = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Manifest = Get-Content (Join-Path $Root 'extension\manifest.json') -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($Version)) { $Version = [string]$Manifest.version }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Versión de extensión inválida: $Version" }

$Source = Join-Path $Root 'extension'
$Destination = Join-Path $Root 'extension-dist'
$Zip = Join-Path $Root ("Clear-Download-Manager-Chrome-Extension-{0}.zip" -f $Version)
$RuntimeFiles = @(
  'manifest.json',
  'app-compat.json',
  'service-worker.js',
  'sidepanel.html',
  'sidepanel.css',
  'sidepanel.js',
  'thumbnail-service.js',
  'content\detector.js',
  'sdk\cacatools-native-client.js',
  'sdk\compatibility.js',
  'sdk\operation-journal.js',
  'sdk\selection.js',
  'sdk\panel-features.js',
  'sdk\appearance.js',
  'icons\icon16.png',
  'icons\icon32.png',
  'icons\icon48.png',
  'icons\icon128.png'
)
$RuntimeFiles += @(Get-ChildItem (Join-Path $Source 'assets') -Recurse -File | Sort-Object FullName | ForEach-Object { $_.FullName.Substring($Source.Length + 1) })
$RuntimeFiles += @(Get-ChildItem (Join-Path $Source 'icons\brand') -Recurse -File | Sort-Object FullName | ForEach-Object { $_.FullName.Substring($Source.Length + 1) })

if (Test-Path -LiteralPath $Destination) { Remove-Item -LiteralPath $Destination -Recurse -Force }
if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
foreach ($RelativePath in $RuntimeFiles) {
  $InputPath = Join-Path $Source $RelativePath
  if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) { throw "Falta archivo de runtime de extensión: $RelativePath" }
  $OutputPath = Join-Path $Destination $RelativePath
  New-Item -ItemType Directory -Path (Split-Path -Parent $OutputPath) -Force | Out-Null
  Copy-Item -LiteralPath $InputPath -Destination $OutputPath -Force
}
# Chrome derives an unpacked extension ID from manifest.key.  The historical
# QA build injected the verified public identity key only into the generated
# package, keeping the source manifest clean.  Preserve that exact mechanism
# so the unpacked build resolves to the production ID and the existing native
# host allow-list remains valid.
$IdentityPath = Join-Path $Root 'evidence\official-public-key.json'
if (-not (Test-Path -LiteralPath $IdentityPath -PathType Leaf)) {
  throw "Falta la clave pública de identidad recuperada: $IdentityPath"
}
$Identity = Get-Content -LiteralPath $IdentityPath -Raw | ConvertFrom-Json
$PublicId = 'aonppfnabjnicjjeoofkfjofolfibggp'
if ([string]$Identity.id -ne $PublicId -or [string]::IsNullOrWhiteSpace([string]$Identity.key)) {
  throw 'La clave pública recuperada no corresponde al ID publicado.'
}
$KeyBytes = [Convert]::FromBase64String([string]$Identity.key)
$KeyDigest = [System.Security.Cryptography.SHA256]::Create().ComputeHash($KeyBytes)
$DerivedIdChars = foreach ($Byte in $KeyDigest[0..15]) {
  [char](97 + (($Byte -shr 4) -band 15))
  [char](97 + ($Byte -band 15))
}
$DerivedId = -join $DerivedIdChars
if ($DerivedId -ne $PublicId) {
  throw "La clave pública no deriva el ID publicado: $DerivedId"
}
$Manifest | Add-Member -NotePropertyName key -NotePropertyValue ([string]$Identity.key) -Force
$ManifestPath = Join-Path $Destination 'manifest.json'
$Utf8NoBom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
[System.IO.File]::WriteAllText($ManifestPath, (($Manifest | ConvertTo-Json -Depth 20) + [Environment]::NewLine), $Utf8NoBom)
Compress-Archive -Path (Join-Path $Destination '*') -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "OK: $Zip" -ForegroundColor Green
