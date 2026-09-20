<p align="center">
  <img src="app-ui/assets/brand/clear-download-manager-celeste.png" width="128" height="128" alt="Clear Download Manager">
</p>

<h1 align="center">Clear Download Manager</h1>
<p align="center">Download and multimedia manager for Windows</p>
<p align="center">Clear Download Manager (CDM) is a local Windows application for organizing HTTP/HTTPS downloads, video, audio, playlists, torrents and direct links. It is built with Tauri and Rust and includes optional Chromium browser integration.</p>

<p align="center">
  <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/feature-pills/downloads-dark.svg"><img src="docs/assets/feature-pills/downloads-light.svg" height="36" alt="Downloads"></picture>&nbsp;
  <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/feature-pills/video-audio-dark.svg"><img src="docs/assets/feature-pills/video-audio-light.svg" height="36" alt="Video and audio"></picture>&nbsp;
  <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/feature-pills/torrents-dark.svg"><img src="docs/assets/feature-pills/torrents-light.svg" height="36" alt="Torrents"></picture>&nbsp;
  <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/feature-pills/direct-links-dark.svg"><img src="docs/assets/feature-pills/direct-links-light.svg" height="36" alt="Direct links"></picture>&nbsp;
  <picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/feature-pills/chromium-dark.svg"><img src="docs/assets/feature-pills/chromium-light.svg" height="36" alt="Chromium integration"></picture>
</p>
<p align="center"><img src="docs/assets/section-divider.svg?v=visual-harmony-20260915" width="100%" height="2" alt=""></p>

## Download

Choose the option that works best for you.

<p align="center">
  <a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.1-build4/Clear.Download.Manager_0.95.1_x64-setup.exe"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/download-buttons/windows-dark.png"><img src="docs/assets/download-buttons/windows-light.png" width="342" alt="Get the app: Windows Installer"></picture></a>&nbsp;&nbsp;
  <a href="https://apps.microsoft.com/detail/9NSTJ7JXM843"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/download-buttons/microsoft-store-dark.png"><img src="docs/assets/download-buttons/microsoft-store-light.png" width="312" alt="Official store: Microsoft Store"></picture></a>
</p>
<p align="center">
  <a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/download-buttons/chrome-web-store-dark.png"><img src="docs/assets/download-buttons/chrome-web-store-light.png" width="346" alt="Browser extension: Chrome Web Store"></picture></a>
</p>

You can also open the [complete Windows release](https://github.com/CacaPlay/clear-download-manager-releases/releases/latest) for hashes, signature and updater metadata.

### What do I need?
- **Install the app:** use the Windows installer or Microsoft Store.
- **Browser integration:** install the extension from Chrome Web Store.
- **Already have CDM:** install only the extension if you want to send content from your browser.

## What it does
- HTTP/HTTPS downloads with resume, persistent queue and real progress.
- Video, audio and playlist downloads through yt-dlp.
- Torrents and magnet links through aria2c.
- Media processing with FFmpeg and FFprobe.
- SQLite history, categories, priorities, concurrency and bandwidth limits.
- Local player with safe full-screen playback for any aspect ratio.
- Light/dark/system themes with synchronized accent colors.
- Optional Chromium integration through Native Messaging.

## Basic usage
1. Open CDM and paste a link, file, torrent or playlist.
2. Select **Analyze** or the appropriate action.
3. Review quality, folder and priority before starting.

The app keeps the queue, history and insertion order locally on this device.

## Verify the installer
The CDM 0.95.1 installer is `Clear.Download.Manager_0.95.1_x64-setup.exe`.
```powershell
Get-FileHash .\Clear.Download.Manager_0.95.1_x64-setup.exe -Algorithm SHA256
```
Expected SHA-256: `de1dc46dd89ec3404e6a091d214ea538e8a72a83fd6da95559b57f19e8645b6c`
The [releases repository](https://github.com/CacaPlay/clear-download-manager-releases/releases/latest) contains the complete `SHA256SUMS.txt` manifest.

## Requirements
Published builds require a compatible Windows x64 installation. WebView2, Node.js and Rust/MSVC are required only for development.

## Privacy and support
CDM is designed to work locally. Do not commit installers, databases, logs, credentials, cookies or private keys. See the [extension privacy policy](docs/extension/PRIVACY.md), [`SECURITY.md`](SECURITY.md) and [`SUPPORT.md`](SUPPORT.md).

## Development
```powershell
npm.cmd ci --no-audit --no-fund
npm.cmd run check:release
npm.cmd run build:windows:final
```
```text
app-ui/       interface, local player and download manager
src-tauri/    Tauri/Rust engine, SQLite and IPC
extension/    Chromium extension and native host
scripts/      build, validation and maintenance tools
docs/         technical contracts and development documentation
```

## Contributing and licensing
Read [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md) and [`LICENSE.md`](LICENSE.md) before sending changes. The license remains proprietary; review it before redistributing or modifying any component.
