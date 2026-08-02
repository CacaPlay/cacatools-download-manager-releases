<div align="center">
  <img src="./logo.svg" width="112" alt="CacaTools Download Manager">
  <h1>CacaTools Download Manager</h1>
  <p>Descargas y actualizaciones firmadas para Windows.</p>
  <p>
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest"><strong>Descargar para Windows</strong></a>
    &nbsp; · &nbsp;
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases">Ver versiones</a>
    &nbsp; · &nbsp;
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/blob/main/SUPPORT.md">Soporte</a>
  </p>
  <p><a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest"><img alt="Versión estable" src="https://img.shields.io/github/v/release/CacaPlay/cacatools-download-manager-releases?label=versi%C3%B3n%20estable&color=6366f1"></a></p>
</div>

> Este repositorio contiene únicamente los instaladores y la documentación pública. El código fuente se mantiene en un repositorio privado.

## Instalar

1. Pulsa <strong>Descargar para Windows</strong>.
2. Abre el instalador <code>.exe</code> y sigue el asistente.
3. Mantén activada la comprobación de actualizaciones.

La aplicación valida criptográficamente cada actualización antes de instalarla.

## Actualizar en el futuro

No tienes que reemplazar archivos manualmente:

1. En el repositorio privado se prepara la nueva versión.
2. GitHub Actions compila y firma el instalador.
3. El instalador, su firma y <code>latest.json</code> se publican automáticamente aquí.
4. CacaTools detecta la nueva versión y muestra la actualización.
5. El usuario pulsa <strong>Instalar</strong> y la aplicación se reinicia ya actualizada.

El flujo técnico queda preparado para publicar nuevas versiones sin volver a configurar el repositorio público.

## Comprobar una descarga

Cada versión incluye <code>SHA256SUMS.txt</code>. En PowerShell, dentro de la carpeta de descarga:

    Get-FileHash .\CacaTools.Download.Manager_*_x64-setup.exe -Algorithm SHA256

Compara el resultado con la línea correspondiente del archivo <code>SHA256SUMS.txt</code>. Si no coincide, no ejecutes el instalador.

## Documentación

- [Privacidad](PRIVACY.md)
- [Soporte](SUPPORT.md)
- [Seguridad](SECURITY.md)
- [Distribución y licencia](LICENSE-DISTRIBUTION.md)

La extensión del navegador se publica y actualiza por separado en Chrome Web Store.

## Enlaces oficiales

- [Última versión](https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest)
- [Historial de versiones](https://github.com/CacaPlay/cacatools-download-manager-releases/releases)
- [Repositorio de código fuente](https://github.com/CacaPlay/cacatools-download-manager) (privado)
