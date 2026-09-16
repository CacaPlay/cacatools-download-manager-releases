<p align="center">
  <img src="app-ui/assets/brand/clear-download-manager-celeste.png" width="128" height="128" alt="Clear Download Manager">
</p>

<h1 align="center">Clear Download Manager</h1>
<p align="center"><span style="color:#8b98a9">Download and multimedia manager for Windows</span></p>
<p align="center">Clear Download Manager (CDM) is a local Windows application for organizing HTTP/HTTPS downloads, video, audio, playlists, torrents and direct links. It is built with Tauri and Rust and includes optional Chromium browser integration.</p>

<p align="center"><picture><source media="(max-width: 700px)" srcset="docs/assets/feature-pills-narrow.svg?v=visual-harmony-20260915"><img src="docs/assets/feature-pills.svg?v=visual-harmony-20260915" width="100%" alt="Downloads · Video and audio · Torrents · Direct links · Chromium integration"></picture></p>
<p align="center"><img src="docs/assets/section-divider.svg?v=visual-harmony-20260915" width="100%" height="2" alt=""></p>

<h3><big>Download</big></h3>
<p>Choose the option that works best for you.</p>
<p align="center"><a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.0/Clear.Download.Manager_0.95.0_x64-setup.exe"><img src="docs/assets/download-cards/windows.svg?v=visual-harmony-20260915" width="32%" alt="Download for Windows — Windows installer"></a>&nbsp;<a href="https://apps.microsoft.com/detail/9NSTJ7JXM843"><img src="docs/assets/download-cards/microsoft-store.svg?v=visual-harmony-20260915" width="32%" alt="Microsoft Store — Get it from Microsoft Store"></a>&nbsp;<a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp"><img src="docs/assets/download-cards/chrome-web-store.svg?v=visual-harmony-20260915" width="32%" alt="Chrome Web Store — Browser extension"></a></p>
<p align="center"><a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.0/Clear.Download.Manager_0.95.0_x64-setup.exe">Download for Windows</a> · <a href="https://apps.microsoft.com/detail/9NSTJ7JXM843">Microsoft Store</a> · <a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp">Chrome Web Store</a></p>

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
The CDM 0.95.0 installer is `Clear.Download.Manager_0.95.0_x64-setup.exe`.
```powershell
Get-FileHash .\Clear.Download.Manager_0.95.0_x64-setup.exe -Algorithm SHA256
```
Expected SHA-256: `6f22a95cc288f1624951614544203f1eaaed80decd183db83ad6874ae290f880`
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
