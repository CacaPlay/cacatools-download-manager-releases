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
transición completa en una máquina separada (configuración, historial, SQLite,
extensión y Native Messaging) sigue siendo una comprobación operativa
pendiente; publicar el puente no equivale a haber observado esa migración en
tiempo de ejecución.
