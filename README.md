# Clear Download Manager

<p align="center">
  <img src="app-ui/assets/brand/clear-download-manager-celeste.png" width="72" height="72" alt="Clear Download Manager">
  <br><strong>Clear Download Manager</strong>
  <br><sub>Gestor de descargas y multimedia para Windows</sub>
</p>

Clear Download Manager es una aplicación local para Windows que gestiona
descargas HTTP/HTTPS, vídeo, audio, playlists, torrents y enlaces directos.
Está construida con Tauri y Rust e incluye una extensión opcional para Chrome.

## Descargar

Las versiones listas para usar están en el
[repositorio oficial de releases](https://github.com/CacaPlay/clear-download-manager-releases).

La extensión para Chrome está disponible en la
[Chrome Web Store](https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp).

## Funciones

- Descargas HTTP/HTTPS con reanudación, cola persistente y progreso real.
- Descarga de vídeo, audio y playlists mediante yt-dlp.
- Torrents y enlaces magnet mediante aria2c.
- Procesamiento multimedia con FFmpeg y FFprobe.
- Historial SQLite, categorías, prioridades, concurrencia y límites de ancho de banda.
- Reproductor local con pantalla completa segura para cualquier relación de aspecto.
- Temas claro/oscuro/sistema y colores de acento sincronizados.
- Integración opcional con Chrome mediante Native Messaging.

## Desarrollo en Windows

Requisitos: Windows x64, Node.js, Rust/MSVC, WebView2 y PowerShell 5.1 o
posterior.

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

No incluyas instaladores, bases de datos, logs, credenciales, cookies ni
claves privadas en el repositorio.
