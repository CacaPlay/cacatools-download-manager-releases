<div align="center">
  <img src="./logo.svg" width="112" alt="CacaTools Download Manager">
  <h1>CacaTools Download Manager</h1>
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest"><strong>Descargar para Windows</strong></a>
    &nbsp; · &nbsp;
    <a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp?utm_source=item-share-cb"><strong>Descargar extensión Chrome</strong></a>
    &nbsp; · &nbsp;
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases">Ver versiones</a>
    &nbsp; · &nbsp;
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/blob/main/SUPPORT.md">Soporte</a>
  </p>
  <p>
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest"><img alt="Versión estable" src="https://img.shields.io/github/v/release/CacaPlay/cacatools-download-manager-releases?label=versi%C3%B3n%20estable&color=6366f1"></a>
    <a href="https://github.com/CacaPlay/cacatools-download-manager-releases/releases/download/v0.23.4/CacaTools-Chrome-Extension-0.23.4-manual.zip"><img alt="Extensión Chrome manual" src="[https://img.shields.io/badge/Chrome%20Extension-manual%20v0.23.4-4285F4?style=flat&logo=googlechrome&logoColor=white](https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp?utm_source=item-share-cb)"></a>
  </p>
</div>

> Este repositorio contiene únicamente los instaladores y la documentación pública. El código fuente se mantiene en un repositorio privado.

## Instalar CacaTools

1. Pulsa **Descargar para Windows**.
2. Abre el instalador <code>.exe</code> y sigue el asistente.
3. Mantén activada la comprobación de actualizaciones.

La aplicación valida criptográficamente cada actualización antes de instalarla.

## Actualizar en el futuro

No tienes que reemplazar archivos manualmente:

1. En el repositorio privado se prepara la nueva versión.
2. GitHub Actions compila y firma el instalador.
3. El instalador, su firma y <code>latest.json</code> se publican automáticamente aquí.
4. CacaTools detecta la nueva versión y muestra la actualización.
5. El usuario pulsa **Instalar** y la aplicación se reinicia ya actualizada.

El flujo técnico queda preparado para publicar nuevas versiones sin volver a configurar el repositorio público.

## Comprobar una descarga

Cada versión incluye <code>SHA256SUMS.txt</code>. En PowerShell, dentro de la carpeta de descarga:

    Get-FileHash .\CacaTools.Download.Manager_*_x64-setup.exe -Algorithm SHA256

Compara el resultado con la línea correspondiente del archivo <code>SHA256SUMS.txt</code>. Si no coincide, no ejecutes el instalador.

## SmartScreen de Windows

En las primeras descargas Windows puede mostrar una alerta de SmartScreen porque la aplicación todavía está construyendo reputación. Esto no equivale a una detección de malware: SmartScreen evalúa la reputación del editor y del hash del archivo, y una versión nueva puede empezar con reputación desconocida incluso si está firmada.

Descarga únicamente desde este repositorio, comprueba el hash de SHA-256 y revisa la firma y el editor cuando Windows los muestre. La firma del actualizador Tauri protege las actualizaciones, pero no sustituye una firma Authenticode del instalador; por eso una instalación nueva puede mostrar “Editor desconocido”. Si los datos no coinciden, cancela la instalación. No desactives Microsoft Defender para ejecutar un archivo.

Consulta la explicación oficial de [Microsoft sobre SmartScreen](https://learn.microsoft.com/es-es/windows/apps/package-and-deploy/smartscreen-reputation).

## Documentación

- [Privacidad](PRIVACY.md)
- [Soporte](SUPPORT.md)
- [Seguridad](SECURITY.md)
- [Distribución y licencia](LICENSE-DISTRIBUTION.md)

La extensión oficial se publicará y actualizará por separado en Chrome Web Store.

## Enlaces oficiales

- [Última versión](https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest)
- [Historial de versiones](https://github.com/CacaPlay/cacatools-download-manager-releases/releases)
- [Repositorio de código fuente](https://github.com/CacaPlay/cacatools-download-manager) (privado)
