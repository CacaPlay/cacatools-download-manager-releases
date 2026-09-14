# Clear Download Manager

<p align="center">
  <img src="app-ui/favicon.svg" width="72" height="72" alt="Clear Download Manager">
  <br><strong>Clear Download Manager</strong>
  <br><sub>Windows download manager and media downloader built with Tauri and Rust</sub><br><br>
  <a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/latest"><img src="https://img.shields.io/badge/Windows%20release-Download-0ea5c9?style=for-the-badge&logo=windows&logoColor=white" alt="Download Clear Download Manager for Windows"></a>
  <a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp"><img src="https://img.shields.io/badge/Chrome%20extension-Web%20Store-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Clear Download Manager Chrome extension"></a>
</p>

Clear Download Manager (CDM) is a local-first Windows application for HTTP
downloads, video and audio downloads, playlists, torrents, and direct links.
It is a native Tauri/Rust application with a modular web interface and an
optional Chrome extension connected through Chrome Native Messaging.

This repository contains the reproducible source code. Public installers,
signatures, `latest.json`, hashes, and release notes live in the dedicated
[release repository](https://github.com/CacaPlay/clear-download-manager-releases).
The historical
[CacaTools releases repository](https://github.com/CacaPlay/cacatools-download-manager-releases)
remains the migration bridge for users upgrading from 0.45.4.

## Features

- HTTP/HTTPS downloads with resume, persistent queue, ordering, and real progress.
- Video, audio, and playlist analysis through yt-dlp.
- Torrents and magnet links through aria2c.
- FFmpeg/FFprobe media processing and validation.
- SQLite history, categories, scheduling, priorities, concurrency, and bandwidth limits.
- Local offline player with aspect-ratio-safe fullscreen playback.
- Responsive sidebar, dark/light/system themes, and synchronized accent colors.
- Optional Chrome extension with native messaging and context-menu integration.

## Repository layout

```text
app-ui/       UI, local player, download manager, and shared assets
src-tauri/    Tauri/Rust engine, SQLite, IPC, and native processes
extension/    Chromium extension and native-host source
scripts/      Windows build, validation, and release tooling
docs/         Maintained contracts and release documentation
```

The package and native identifiers that still contain the historical
`CacaTools` name are compatibility contracts for existing installations and
are intentionally not changed by the repository split.

## Build on Windows

Requirements: Windows x64, Node.js, Rust/MSVC, WebView2, and PowerShell 5.1+.

```powershell
npm.cmd ci --no-audit --no-fund
npm.cmd run version:check
npm.cmd run check:release
npm.cmd run build:windows:final
```

`check:release` is the current 0.95.x source gate. The build keeps both lock
files, verifies Rust and web assets, checks bundled tools, and records SHA-256
values for generated artifacts. Private signing keys are never stored in the
repository.

## Release flow

1. Merge a reviewed change into `main`.
2. Create a version tag such as `v0.95.1`.
3. GitHub Actions runs the source gate, Windows build, signature generation,
   `latest.json`, and `SHA256SUMS.txt`.
4. The workflow publishes the assets to
   `clear-download-manager-releases`.
5. The application updater consumes the signed catalog after the legacy
   0.45.4 bridge has been validated.

See [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md) and
[`docs/UPDATER-MIGRATION.md`](docs/UPDATER-MIGRATION.md) for the release
contracts. A production signing key is required in GitHub Actions; this
checkout does not contain one.

## Chrome extension

The extension source is in `extension/` and can be packaged locally with:

```powershell
npm.cmd run extension:build
```

The Chrome Web Store listing and the Windows release are versioned and
published independently.

## Contributing and security

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request and
[`SECURITY.md`](SECURITY.md) before reporting a vulnerability. Do not commit
installers, logs, user databases, credentials, cookies, or signing keys.
