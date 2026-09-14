# Updater repository migration

The legacy public repository
`CacaPlay/cacatools-download-manager-releases` remains the bridge for users
running CacaTools 0.45.4. The first Clear Download Manager 0.95.0 release must
be published there, signed, and tested on a separate machine before the
updater endpoint is changed.

After the bridge passes, new CDM releases use
`CacaPlay/clear-download-manager-releases`. The source repository and the
release repository are intentionally separate: source changes are reviewed
here, while installers, signatures, `latest.json`, `news.json`, and hashes
are published in the release-only repository.

The migration gate must verify settings, history, SQLite data, extension
registration, Native Messaging, rollback behavior, and a signed catalog. No
production signing key is stored in this repository, and no unsigned catalog
is treated as a release.
