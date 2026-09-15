# Clear Download Manager Extension 0.45.12

Extensión Chromium para enviar vídeos, audio, playlists, imágenes y enlaces a
Clear Download Manager 0.95.x. La distribución pública se realiza mediante la
[Chrome Web Store](https://chromewebstore.google.com/detail/aonppfnabjnicjjeoofkfjofolfibggp).

## Instalación

1. Instala Clear Download Manager para Windows desde el
   [repositorio oficial de releases](https://github.com/CacaPlay/clear-download-manager-releases/releases/latest)
   o Microsoft Store.
2. Instala la extensión desde Chrome Web Store.
3. Abre CDM una vez para que la integración del navegador pueda descubrir la
   aplicación.

El paquete generado para pruebas conserva la identidad pública oficial de la
extensión. [`../evidence/official-public-key.json`](../evidence/official-public-key.json)
contiene únicamente material público de identidad; ninguna clave privada se
distribuye en este repositorio.

## Funciones

- Detecta contenido multimedia compatible en la pestaña activa.
- Envía vídeos, audio, playlists, páginas, imágenes HTTP(S) y enlaces al gestor.
- Mantiene la calidad automática cuando la fuente no ofrece una selección fija.
- Permite añadir vídeos o audio a playlists manuales sin duplicados.
- Conserva miniaturas, etiquetas de formato y estados de la solicitud.
- Ofrece menú contextual y panel lateral con la marca de CDM.
- Mantiene preferencias de color y tema cuando la aplicación las publica.
- Rechaza explícitamente imágenes `blob:`/`data:` que no pueden transferirse de
  forma segura.

## Comportamiento de captura

Las instalaciones nuevas comienzan en modo **Automático**. La captura ignora
ventanas de incógnito, consulta las capacidades disponibles y solo cancela una
acción del navegador después de recibir una aceptación. Si el resultado es
incierto, la extensión pide revisión en lugar de reanudar a ciegas una posible
transferencia duplicada.

## Desarrollo y validación

El código de la extensión vive en este directorio y el host nativo se registra
desde los scripts del repositorio principal. Los gates actuales cubren el
módulo de extensión, el panel, la detección, la captura, la sincronización y la
marca. Los resultados de una ejecución deben distinguir siempre entre fixture,
conexión real y acciones observadas en CDM.

No se incluyen perfiles del navegador, credenciales, descargas de prueba ni
configuración QA en el paquete de producción.
