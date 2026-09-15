<p align="center">
  <img src="logo-clear-download-manager.png" width="128" height="128" alt="Clear Download Manager">
</p>

<h1 align="center">Clear Download Manager</h1>
<p align="center"><strong>Releases oficiales para Windows</strong></p>
<p align="center">
  Este repositorio contiene únicamente las versiones públicas de Clear Download Manager:<br>
  instaladores, firmas, hashes, notas y metadatos del updater.
</p>

<table align="center" width="100%">
  <tr>
    <td align="center"><img src="docs/assets/feature-icons/download.svg" width="28" alt=""><br><strong>Descargas</strong></td>
    <td align="center"><img src="docs/assets/feature-icons/video.svg" width="28" alt=""><br><strong>Vídeo y audio</strong></td>
    <td align="center"><img src="docs/assets/feature-icons/package.svg" width="28" alt=""><br><strong>Torrents</strong></td>
    <td align="center"><img src="docs/assets/feature-icons/link.svg" width="28" alt=""><br><strong>Enlaces directos</strong></td>
    <td align="center"><img src="docs/assets/chrome-web-store.png" width="28" height="28" alt=""><br><strong>Integración Chromium</strong></td>
  </tr>
</table>

## Descargar

<table align="center" width="100%">
  <tr>
    <td align="center" width="33%">
      <a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.0/Clear.Download.Manager_0.95.0_x64-setup.exe">
        <img src="docs/assets/download-cards/windows.png" width="100%" alt="Descargar para Windows — Instalador para Windows">
      </a>
    </td>
    <td align="center" width="33%">
      <a href="https://apps.microsoft.com/detail/9NSTJ7JXM843">
        <img src="docs/assets/download-cards/microsoft-store.png" width="100%" alt="Microsoft Store — Obtener en Microsoft Store">
      </a>
    </td>
    <td align="center" width="33%">
      <a href="https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp">
        <img src="docs/assets/download-cards/chrome-web-store.png" width="100%" alt="Chrome Web Store — Disponible en Chrome Web Store">
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
