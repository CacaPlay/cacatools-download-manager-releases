# Updater repository migration

The legacy public repository
`CacaPlay/cacatools-download-manager-releases` remains the bridge for users
running the 0.45.x application. Clear Download Manager 0.95.0 was published
there as the migration release so those installations can discover it without
changing their existing updater endpoint.

After the bridge passes, new CDM releases use
`CacaPlay/clear-download-manager-releases`. The source repository and the
release repository are intentionally separate: source changes are reviewed
here, while installers, signatures, `latest.json`, `news.json`, and hashes
are published in the release-only repository.

The migration gate verifies settings, history, SQLite data, extension
registration, Native Messaging, rollback behavior, and a signed catalog. No
production signing key is stored in this repository, and no unsigned catalog
is treated as a release.

## Feed de novedades

Los builds nuevos de Clear Download Manager leen `news.json` desde el
repositorio canónico `CacaPlay/clear-download-manager-releases`. Mientras el
puente siga activo, el repositorio legacy mantiene una copia de la noticia
actual para que las instalaciones anteriores no vuelvan a mostrar el aviso
obsoleto de CacaTools 0.45.3. El cliente identifica la fuente de su caché y
descarta cualquier contenido guardado antes de esta migración.

## Estado actual del puente

El puente firmado `v0.95.0` ya está publicado en
`CacaPlay/cacatools-download-manager-releases` y su `latest.json` anuncia la
migración desde 0.45.4. El release legacy `v0.45.4` permanece intacto. La
validación manual de instalación, arranque y funcionamiento básico en un
entorno Windows 11 limpio fue completada por el mantenedor. Esta nota no
afirma firma Authenticode, auditoría independiente ni compatibilidad universal.

El cliente 0.95.0 conserva la referencia legacy para mantener la continuidad
del puente. El cambio definitivo al endpoint canónico se hará en una versión
posterior, después de validar esa transición en una instalación separada.
