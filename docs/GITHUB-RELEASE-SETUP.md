# GitHub release setup

The source workflow publishes only after a version tag and a successful
Windows build. Configure these repository secrets in
`CacaPlay/clear-download-manager`:

- `TAURI_SIGNING_PRIVATE_KEY`: the production Tauri updater private key.
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: its password, when configured.
- `RELEASES_REPO_TOKEN`: a fine-grained token limited to releases in
  `CacaPlay/clear-download-manager-releases`.

Keep the token and signing key out of commits, logs, artifacts, and pull
requests. The workflow checks that the updater is enabled, publishes
`latest.json`, and verifies the downloaded catalog and Windows asset before
finishing. The publication target is resolved from the bundled updater
configuration, so `latest.json` and the GitHub release cannot silently point
to different repositories during the legacy bridge.

The first 0.95.0 migration release is exceptional: it was signed and
published through the legacy releases repository so that 0.45.x installations
can discover it. The current 0.95.0 client keeps that legacy endpoint for
continuity. Change the release target and updater endpoint only in a later
version, after the bridge transition described in `UPDATER-MIGRATION.md` has
been validated separately.
