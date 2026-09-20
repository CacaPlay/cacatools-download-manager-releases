# Publicar Clear Download Manager

## Repositorios

- Código fuente: `CacaPlay/clear-download-manager`.
- Distribución: `CacaPlay/clear-download-manager-releases`.
- Puente de migración 0.45.4: `CacaPlay/cacatools-download-manager-releases`.

El repositorio de distribución contiene únicamente instaladores, firmas,
`latest.json`, `news.json`, hashes y notas de release. Las claves privadas
permanecen fuera del árbol de trabajo y se guardan solo como secretos de
GitHub Actions.

## Publicar una versión nueva

1. Confirmar una versión coherente en `package.json`, Tauri, Cargo y la
   extensión independiente.
2. Ejecutar en Windows:

   ```powershell
   npm.cmd ci --no-audit --no-fund
   npm.cmd run version:check
   npm.cmd run check:release
   ```

3. Crear un tag firmado o protegido, por ejemplo `v0.95.1`, y abrir el
   workflow de release.
4. El workflow compila en Windows, genera artefactos Tauri firmados,
   `latest.json` y `SHA256SUMS.txt`, y publica todo en el repositorio de
   distribución.
5. Verificar el endpoint, los hashes, la firma y una instalación limpia antes
   de marcar el release como estable.

La primera publicación de Clear Download Manager 0.95.0 salió como puente por
el repositorio legacy para que los usuarios 0.45.4 puedan actualizar. El
cliente 0.95.0 conserva el endpoint legacy para mantener la continuidad del
puente, mientras el `latest.json` publicado identifica el artefacto canónico.
La validación manual de instalación, arranque y funcionamiento básico en un
entorno Windows 11 limpio fue completada por el mantenedor. El cambio definitivo
al endpoint canónico queda reservado para una versión posterior y una prueba
separada de configuración, historial, SQLite, extensión y Native Messaging.

## No publicar

No publiques desde un checkout con `node_modules`, `target`, `output`, bases de
datos, logs, instaladores sin firma, claves privadas ni perfiles de navegador.
No se considera una release válida un artefacto cuya procedencia o firma no
pueda verificarse.
