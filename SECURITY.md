# Seguridad

## Reportar una vulnerabilidad

No publiques credenciales, claves privadas ni detalles explotables en un issue.
Envía el reporte al propietario del repositorio mediante un aviso privado de
GitHub o solicita contacto al propietario `@CacaPlay`.

Incluye la versión afectada, pasos reproducibles, impacto y una propuesta de
mitigación si la tienes. Las descargas y actualizaciones deben conservar la
verificación de firma; nunca se debe desactivar para probar una compilación.

## Reglas del proyecto

- Las claves privadas Tauri permanecen fuera del repositorio y solo se guardan
  en `TAURI_SIGNING_PRIVATE_KEY` de GitHub Actions.
- Los instaladores se publican únicamente como artefactos de GitHub Releases.
- Las modificaciones a `main` deben entrar mediante pull request revisada.
- No se aceptan binarios, carpetas de compilación, logs ni datos personales en
  el código fuente.
