# Contributing to Clear Download Manager

Thank you for helping improve CDM. Keep changes small, reviewable, and tied
to a reproducible issue or an agreed feature.

## Before opening a pull request

- Read the contracts in `docs/` and preserve download, IPC, updater, player,
  extension, and visible UI behavior unless the change explicitly covers it.
- Run `npm.cmd ci --no-audit --no-fund` and `npm.cmd run check:release`.
- For Rust changes, run `cargo fmt --manifest-path src-tauri/Cargo.toml --all
  -- --check`, `cargo check --manifest-path src-tauri/Cargo.toml --locked`,
  and the relevant tests.
- Never include user databases, downloaded media, installers, logs, signing
  keys, or native runtime binaries in a source pull request.

Describe the user-visible effect, the tests run, and any known limitation.
