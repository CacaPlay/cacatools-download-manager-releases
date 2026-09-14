# Privacidad de la extensión

CacaTools procesa localmente la URL, el título, miniatura pública y metadatos
visibles de las páginas permitidas para detectar reproductores multimedia. En
YouTube, Spotify, Pinterest y TikTok el detector puede ejecutarse
automáticamente; en otros sitios solo se inyecta cuando el usuario abre el
panel o solicita el análisis. Solo envía una selección al escritorio cuando el usuario la confirma desde el panel;
las descargas normales se envían únicamente para intentar la captura automática
configurada por el usuario. La extensión no recopila ni envía cookies,
contraseñas, encabezados de autorización, tokens, historial, playlists
personales ni nombres de archivos. No se añade telemetría.

La comunicación con la aplicación usa Chrome Native Messaging por un proceso
local. Solo se aceptan URLs `http` y `https`; `file:`, `javascript:`, `data:`,
`chrome:`, `about:` y `blob:` como destino final se rechazan.
