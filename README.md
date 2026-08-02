# CacaTools Download Manager

<p align="center">
  <img src="logo.svg" width="88" alt="CacaTools">
</p>

Descargas oficiales y actualizaciones firmadas de **CacaTools Download
Manager** para Windows.

> Este repositorio contiene distribución binaria y documentación pública. El
> código fuente se mantiene en un repositorio privado y no se publica aquí.

## Descargar

[**Descargar la última versión para Windows**](https://github.com/CacaPlay/cacatools-download-manager-releases/releases/latest)

Abre el instalador `.exe`, sigue el asistente y deja activada la comprobación
de actualizaciones. Las actualizaciones se verifican criptográficamente antes
de instalarse.

## Verificar una descarga

Cada Release incluye `SHA256SUMS.txt`. En PowerShell, desde la carpeta de la
descarga:

```powershell
Get-FileHash .\CacaTools.Download.Manager_*_x64-setup.exe -Algorithm SHA256
```

Compara el valor con la línea del instalador en `SHA256SUMS.txt`. No ejecutes
un archivo cuyo hash no coincida.

## Documentación

- [Privacidad](PRIVACY.md)
- [Soporte](SUPPORT.md)
- [Seguridad](SECURITY.md)
- [Distribución y licencia](LICENSE-DISTRIBUTION.md)

La extensión del navegador se publica y actualiza por separado en Chrome Web
Store.
