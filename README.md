# Clear Download Manager (CDM)

<p align="center">
  <img src="logo-clear-download-manager.png" width="96" height="96" alt="Clear Download Manager">
  <br><strong>Clear Download Manager</strong>
  <br><sub>Releases oficiales para Windows</sub>
</p>

Este repositorio contiene únicamente las versiones públicas de Clear Download
Manager: instaladores, firmas, hashes, notas y metadatos del updater.

## Descargar

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.0/Clear.Download.Manager_0.95.0_x64-setup.exe">
        <img src="logo-clear-download-manager.png" width="36" height="36" alt="Logo de Clear Download Manager"><br>
        <strong>Descargar para Windows</strong>
      </a>
    </td>
    <td align="center">
      <a href="https://apps.microsoft.com/detail/9NSTJ7JXM843">
        <img src="docs/assets/microsoft-store.png" width="36" height="36" alt="Microsoft Store"><br>
        <strong>Microsoft Store</strong>
      </a>
    </td>
    <td align="center">
      <a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp">
        <img src="docs/assets/chrome-web-store.png" width="36" height="36" alt="Chrome Web Store"><br>
        <strong>Chrome Web Store</strong>
      </a>
    </td>
  </tr>
</table>

También puedes abrir el [release completo de CDM 0.95.0](https://github.com/CacaPlay/clear-download-manager-releases/releases/tag/v0.95.0)
para consultar todos sus archivos.

Antes de ejecutar un instalador, verifica su SHA-256:

```powershell
Get-FileHash .\Clear.Download.Manager_0.95.0_x64-setup.exe -Algorithm SHA256
```

SHA-256 esperado:
`6f22a95cc288f1624951614544203f1eaaed80decd183db83ad6874ae290f880`

El manifiesto completo está en [`SHA256SUMS.txt`](https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.0/SHA256SUMS.txt).

## Repositorios

- [Código fuente](https://github.com/CacaPlay/clear-download-manager)
- [Releases de Windows](https://github.com/CacaPlay/clear-download-manager-releases)

Las claves privadas, datos de usuario, bases de datos, logs y perfiles de
prueba no se almacenan aquí.

Consulta [`LICENSE-DISTRIBUTION.md`](LICENSE-DISTRIBUTION.md), [`PRIVACY.md`](PRIVACY.md),
[`SECURITY.md`](SECURITY.md) y [`SUPPORT.md`](SUPPORT.md) para las políticas
de distribución.
