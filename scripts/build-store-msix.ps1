param(
  [Parameter(Mandatory = $true)][string]$IdentityName,
  [Parameter(Mandatory = $true)][string]$Publisher,
  [Parameter(Mandatory = $true)][string]$CurrentStoreVersion,
  [Parameter(Mandatory = $true)][ValidatePattern('^\d+\.\d+\.\d+\.\d+$')][string]$PackageVersion,
  [string]$Output = '',
  [string]$TauriTargetDirectory = '',
  [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Package = Get-Content (Join-Path $Root 'package.json') -Raw | ConvertFrom-Json
$AppVersion = [string]$Package.version
$ExtensionManifest = Get-Content (Join-Path $Root 'extension\manifest.json') -Raw | ConvertFrom-Json
$ExtensionVersion = [string]$ExtensionManifest.version
$OutputRoot = if ([string]::IsNullOrWhiteSpace($Output)) { Join-Path $Root 'output\store-msix' } else { [IO.Path]::GetFullPath($Output) }
$TauriTargetRoot = if ([string]::IsNullOrWhiteSpace($TauriTargetDirectory)) {
  if ([string]::IsNullOrWhiteSpace($env:CARGO_TARGET_DIR)) { Join-Path $Root 'src-tauri\target' } else { [IO.Path]::GetFullPath($env:CARGO_TARGET_DIR) }
} else { [IO.Path]::GetFullPath($TauriTargetDirectory) }
$TauriRelease = Join-Path $TauriTargetRoot 'release'
$Stage = Join-Path $OutputRoot 'stage'
$PackagePath = Join-Path $OutputRoot ("CacaTools-Download-Manager-$PackageVersion.msix")
$ManifestPath = Join-Path $Stage 'AppxManifest.xml'

function Invoke-Native {
  param([Parameter(Mandatory = $true)][string]$Command, [string[]]$Arguments = @())
  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE." }
}

function Get-Version4 {
  param([Parameter(Mandatory = $true)][string]$Value, [Parameter(Mandatory = $true)][string]$Label)
  if ($Value -notmatch '^\d+\.\d+\.\d+\.\d+$') { throw "$Label must be a four-part Windows package version: $Value" }
  try { return [version]$Value } catch { throw "$Label is not a valid Windows package version: $Value" }
}

$CurrentVersion = Get-Version4 $CurrentStoreVersion 'CurrentStoreVersion'
$TargetVersion = Get-Version4 $PackageVersion 'PackageVersion'
if ($TargetVersion -le $CurrentVersion) {
  throw "Store update rejected: package version $PackageVersion must be greater than the published version $CurrentStoreVersion."
}
if ($AppVersion -ne (($PackageVersion -split '\.')[0..2] -join '.')) {
  throw "PackageVersion $PackageVersion does not belong to app version $AppVersion."
}
if ([string]::IsNullOrWhiteSpace($IdentityName) -or [string]::IsNullOrWhiteSpace($Publisher)) {
  throw 'IdentityName and Publisher must be the exact values from the existing Store listing.'
}

$TauriExe = Join-Path $TauriRelease 'cacatools-desktop.exe'
$TauriResources = Join-Path $TauriRelease 'resources'
$SourceResources = Join-Path $Root 'src-tauri\resources'
$NativeHostProject = Join-Path $Root 'extension\native-host'
$NativeHostTargetRoot = Join-Path ([IO.Path]::GetDirectoryName($TauriTargetRoot)) (([IO.Path]::GetFileName($TauriTargetRoot)) + '-native-host')
$NativeHostSource = Join-Path $SourceResources 'extension\cacatools-native-host.exe'
$ExtensionZip = Join-Path $Root ("CacaTools-Chrome-Extension-{0}.zip" -f $ExtensionVersion)
if (-not $SkipBuild) {
  $PreviousCargoTargetDirectory = $env:CARGO_TARGET_DIR
  try {
    $env:CARGO_TARGET_DIR = $TauriTargetRoot
    Invoke-Native 'npx.cmd' @('--no-install', 'tauri', 'build', '--no-bundle')
  }
  finally {
    $env:CARGO_TARGET_DIR = $PreviousCargoTargetDirectory
  }
}
if (-not (Test-Path -LiteralPath $TauriExe) -or -not (Test-Path -LiteralPath $TauriResources)) {
  throw "No standalone Tauri runtime found at $TauriRelease."
}
# Always rebuild the host. A stale bundled executable can still answer ping
# while silently exposing an older protocol to the published extension.
$PreviousCargoTargetDirectory = $env:CARGO_TARGET_DIR
try {
  $env:CARGO_TARGET_DIR = $NativeHostTargetRoot
  Invoke-Native 'cargo.exe' @('build', '--release', '--locked', '--manifest-path', (Join-Path $NativeHostProject 'Cargo.toml'))
}
finally {
  $env:CARGO_TARGET_DIR = $PreviousCargoTargetDirectory
}
$BuiltNativeHost = Join-Path $NativeHostTargetRoot 'release\cacatools-native-host.exe'
if (-not (Test-Path -LiteralPath $BuiltNativeHost)) {
  throw "The native host build completed without creating $BuiltNativeHost"
}
New-Item -ItemType Directory -Path (Split-Path -Parent $NativeHostSource) -Force | Out-Null
Copy-Item -LiteralPath $BuiltNativeHost -Destination $NativeHostSource -Force
$TargetExtensionResources = Join-Path $TauriResources 'extension'
New-Item -ItemType Directory -Path $TargetExtensionResources -Force | Out-Null
# Tauri can retain an incremental resource directory when only a generated
# native host changes. Copy the generated build artifact explicitly so the
# Store package cannot silently omit the extension bridge.
Copy-Item -LiteralPath $NativeHostSource -Destination (Join-Path $TargetExtensionResources 'cacatools-native-host.exe') -Force
if (-not (Test-Path -LiteralPath $ExtensionZip)) {
  throw "The extension package is missing: $ExtensionZip. Run npm.cmd run extension:build first."
}
$RuntimeHost = Join-Path $TauriResources 'extension\cacatools-native-host.exe'
$RuntimeConfig = Join-Path $TauriResources 'extension\extension-config.json'
if (-not (Test-Path -LiteralPath $RuntimeHost) -or -not (Test-Path -LiteralPath $RuntimeConfig)) {
  throw 'The MSIX runtime is missing the bundled native host or extension configuration.'
}
$ExtensionConfig = Get-Content -LiteralPath $RuntimeConfig -Raw | ConvertFrom-Json
$PublishedExtensionId = [string]$ExtensionConfig.chromiumExtensionIds[0]
if ($PublishedExtensionId -ne 'aonppfnabjnicjjeoofkfjofolfibggp') {
  throw "Unexpected Chromium extension ID in bundled runtime: $PublishedExtensionId"
}

if (Test-Path -LiteralPath $OutputRoot) { Remove-Item -LiteralPath $OutputRoot -Recurse -Force }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage 'Assets') -Force | Out-Null
Copy-Item -LiteralPath $TauriExe -Destination (Join-Path $Stage 'cacatools-desktop.exe') -Force
Copy-Item -LiteralPath $TauriResources -Destination $Stage -Recurse -Force
foreach ($Asset in @('StoreLogo.png', 'Square44x44Logo.png', 'Square150x150Logo.png')) {
  $AssetPath = Join-Path $Root "src-tauri\icons\$Asset"
  if (-not (Test-Path -LiteralPath $AssetPath)) { throw "Missing Store asset: $AssetPath" }
  Copy-Item -LiteralPath $AssetPath -Destination (Join-Path $Stage "Assets\$Asset") -Force
}

$ManifestXml = @"
<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10" xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10" xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities" IgnorableNamespaces="uap rescap">
  <Identity Name="$IdentityName" Publisher="$Publisher" Version="$PackageVersion" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>CacaTools Download Manager</DisplayName>
    <PublisherDisplayName>CacaPlay</PublisherDisplayName>
    <Description>Gestor local de descargas, torrents, vídeo, audio y playlists.</Description>
    <Logo>Assets\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="es-MX" />
    <Resource Language="en-US" />
  </Resources>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
  <Applications>
    <Application Id="CacaTools" Executable="cacatools-desktop.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements AppListEntry="default" DisplayName="CacaTools Download Manager" Description="CacaTools Download Manager" BackgroundColor="#0B1522" Square44x44Logo="Assets\Square44x44Logo.png" Square150x150Logo="Assets\Square150x150Logo.png" />
    </Application>
  </Applications>
</Package>
"@
[IO.File]::WriteAllText($ManifestPath, $ManifestXml, [Text.UTF8Encoding]::new($false))

$MakeAppxCommand = Get-Command makeappx.exe -ErrorAction SilentlyContinue
$MakeAppx = if ($null -ne $MakeAppxCommand) { $MakeAppxCommand.Path } else { $null }
if ([string]::IsNullOrWhiteSpace($MakeAppx)) {
  $MakeAppx = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe'
}
if (-not (Test-Path -LiteralPath $MakeAppx)) { throw 'makeappx.exe is not available. Install the Windows 10/11 SDK before building the Store package.' }
Invoke-Native $MakeAppx @('pack', '/d', $Stage, '/p', $PackagePath, '/o')
Invoke-Native $MakeAppx @('unpack', '/p', $PackagePath, '/d', (Join-Path $OutputRoot 'validate'), '/o')

$PackageHash = (Get-FileHash $PackagePath -Algorithm SHA256).Hash.ToLowerInvariant()
$ExtensionHash = (Get-FileHash $ExtensionZip -Algorithm SHA256).Hash.ToLowerInvariant()
$Report = [ordered]@{
  generatedAt = (Get-Date).ToUniversalTime().ToString('o')
  appVersion = $AppVersion
  packageVersion = $PackageVersion
  currentStoreVersion = $CurrentStoreVersion
  identityName = $IdentityName
  publisher = $Publisher
  package = [ordered]@{ name = (Split-Path $PackagePath -Leaf); bytes = (Get-Item $PackagePath).Length; sha256 = $PackageHash }
  extension = [ordered]@{ version = $ExtensionVersion; zip = (Split-Path $ExtensionZip -Leaf); sha256 = $ExtensionHash; chromiumExtensionId = $PublishedExtensionId; nativeHostSha256 = (Get-FileHash $RuntimeHost -Algorithm SHA256).Hash.ToLowerInvariant() }
  signing = 'Unsigned build artifact; Microsoft Store signing is required at submission.'
  buildCommand = if ($SkipBuild) { 'reused existing src-tauri/target/release runtime' } else { 'npx.cmd --no-install tauri build --no-bundle' }
}
$Report | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $OutputRoot 'store-package-report.json') -Encoding UTF8
"$PackageHash  $((Split-Path $PackagePath -Leaf))" | Set-Content (Join-Path $OutputRoot "$((Split-Path $PackagePath -Leaf)).sha256") -Encoding ASCII
Write-Host "MSIX prepared (unsigned): $PackagePath" -ForegroundColor Green
Write-Host "SHA-256: $PackageHash" -ForegroundColor Green
