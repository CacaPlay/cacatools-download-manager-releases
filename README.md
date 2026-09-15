# Clear Download Manager

<p align="center">
  <img src="app-ui/assets/brand/clear-download-manager-celeste.png" width="72" height="72" alt="Clear Download Manager">
  <br><strong>Clear Download Manager</strong>
  <br><sub>Gestor de descargas y multimedia para Windows</sub>
</p>

Clear Download Manager (CDM) es una aplicación local para Windows que organiza
descargas HTTP/HTTPS, vídeo, audio, playlists, torrents y enlaces directos.
Está construida con Tauri y Rust e incluye integración opcional con navegadores
Chromium.

## Descargar

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/CacaPlay/clear-download-manager-releases/releases/download/v0.95.0/Clear.Download.Manager_0.95.0_x64-setup.exe">
        <img src="app-ui/assets/brand/clear-download-manager-celeste.png" width="36" height="36" alt="Logo de Clear Download Manager"><br>
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

También puedes consultar el [release completo de Windows](https://github.com/CacaPlay/clear-download-manager-releases/releases/latest),
incluidos sus hashes, firma y metadatos del updater.

### ¿Qué necesito?

- **Instalar la aplicación:** usa el instalador de Windows o Microsoft Store.
- **Integrar el navegador:** instala la extensión desde Chrome Web Store.
- **Ya tienes CDM:** instala solo la extensión si necesitas enviar contenido
  desde el navegador.

## Qué hace

- Descargas HTTP/HTTPS con reanudación, cola persistente y progreso real.
- Descarga de vídeo, audio y playlists mediante yt-dlp.
- Torrents y enlaces magnet mediante aria2c.
- Procesamiento multimedia con FFmpeg y FFprobe.
- Historial SQLite, categorías, prioridades, concurrencia y límites de ancho de banda.
- Reproductor local con pantalla completa segura para cualquier relación de aspecto.
- Temas claro/oscuro/sistema y colores de acento sincronizados.
- Integración opcional con Chrome mediante Native Messaging.

## Uso básico

1. Abre CDM y pega un enlace, archivo, torrent o playlist.
2. Pulsa **Analizar** o elige la acción correspondiente.
3. Revisa la calidad, carpeta y prioridad antes de iniciar.

La aplicación conserva la cola, el historial y el orden en que se añadieron
las descargas en el equipo local.

## Verificar el instalador

El instalador publicado para CDM 0.95.0 es
`Clear.Download.Manager_0.95.0_x64-setup.exe`.

```powershell
Get-FileHash .\Clear.Download.Manager_0.95.0_x64-setup.exe -Algorithm SHA256
```

SHA-256 esperado:
`6f22a95cc288f1624951614544203f1eaaed80decd183db83ad6874ae290f880`

El archivo `SHA256SUMS.txt` del [repositorio de releases](https://github.com/CacaPlay/clear-download-manager-releases/releases/latest)
contiene el manifiesto completo.

## Requisitos

Windows x64, WebView2, Node.js y Rust/MSVC son necesarios para desarrollar.
Para instalar una versión publicada solo se necesita Windows compatible con el
instalador.

## Privacidad y soporte

CDM está diseñado para trabajar localmente. No incluyas instaladores, bases de
datos, logs, credenciales, cookies ni claves privadas en este repositorio.
Consulta la [política de privacidad de la extensión](docs/extension/PRIVACY.md),
[`SECURITY.md`](SECURITY.md) y
[`SUPPORT.md`](SUPPORT.md) para la información pública disponible.

## Desarrollo en Windows

Para preparar el entorno y ejecutar las comprobaciones actuales:

```powershell
npm.cmd ci --no-audit --no-fund
npm.cmd run check:release
npm.cmd run build:windows:final
```

La estructura principal es:

```text
app-ui/       interfaz, reproductor local y gestor de descargas
src-tauri/    motor Tauri/Rust, SQLite e IPC
extension/    extensión Chromium y host nativo
scripts/      compilación, validación y herramientas de mantenimiento
docs/         contratos técnicos y documentación de desarrollo
```

## Contribuir

Consulta [`CONTRIBUTING.md`](CONTRIBUTING.md) antes de enviar cambios. Las
reglas de seguridad están en [`SECURITY.md`](SECURITY.md) y la licencia en
[`LICENSE.md`](LICENSE.md).

El código se publica para facilitar la revisión y la colaboración técnica. La
licencia sigue siendo propietaria; revisa [`LICENSE.md`](LICENSE.md) antes de
redistribuir o modificar cualquier componente.

## Compatibilidad de versiones anteriores

Las instalaciones antiguas pueden utilizar temporalmente un repositorio de
actualización legacy como puente. No se debe eliminar ese puente mientras siga
habiendo usuarios que dependan de él. Las versiones nuevas se distribuyen
desde el repositorio canónico de releases.
