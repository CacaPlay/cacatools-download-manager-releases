# Clear Download Manager Releases

<p align="center">
  <img src="logo-clear-download-manager.png" width="96" height="96" alt="Clear Download Manager">
  <br><strong>Clear Download Manager</strong>
  <br><sub>Official Windows releases and signed updater metadata</sub>
</p>

This is the official distribution repository for [Clear Download Manager](https://github.com/CacaPlay/clear-download-manager).
It contains public Windows release assets and the small metadata files consumed
by the signed updater.

## Download

Use the [latest stable release](https://github.com/CacaPlay/clear-download-manager-releases/releases/latest).
Each release includes the Windows installer, its updater signature,
`latest.json`, and `SHA256SUMS.txt` when applicable.

Verify the SHA-256 value before running an installer:

```powershell
Get-FileHash .\Clear-Download-Manager-*.exe -Algorithm SHA256
```

The updater also verifies the signed catalog. Do not run a file whose hash or
signature does not match the release notes.

## Migration bridge

Users still running CacaTools 0.45.4 receive the first Clear Download Manager
0.95.0 update through the historical
[`cacatools-download-manager-releases`](https://github.com/CacaPlay/cacatools-download-manager-releases)
repository. That repository is retained as a compatibility bridge and is not
replaced or deleted during the migration.

After the bridge is tested on a separate machine, new CDM releases use this
repository as the canonical updater endpoint.

## Repository scope

Source code, build workflows, and issue tracking live in the
[source repository](https://github.com/CacaPlay/clear-download-manager).
Private signing keys, user data, databases, logs, and temporary test profiles
never belong here.

See [`LICENSE-DISTRIBUTION.md`](LICENSE-DISTRIBUTION.md), [`PRIVACY.md`](PRIVACY.md),
[`SECURITY.md`](SECURITY.md), and [`SUPPORT.md`](SUPPORT.md) for public release
policies.
