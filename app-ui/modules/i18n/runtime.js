/*
 * Last-mile localization for legacy renderers.  The download manager has a
 * number of small templates that predate the central catalog and are rebuilt
 * from several modules.  This pass translates only exact, known UI phrases
 * after rendering; user content, paths, code and diagnostic payloads remain
 * untouched.
 */
const ES_TO_EN = Object.freeze({
  'Ajustes': 'Settings', 'Cambiar tema': 'Change theme', 'Novedades': "What's new", 'Navegación principal': 'Main navigation', 'Abrir navegación': 'Open navigation', 'Accesos de entrada': 'Input shortcuts', 'Cola': 'Queue',
  'Descargas': 'Downloads', 'Descargas activas': 'Active downloads', 'Todos los trabajos locales y sus estados.': 'All local jobs and their status.',
  'Gestor local de archivos y multimedia.': 'Local file and media manager.', 'Documentos': 'Documents', 'Biblioteca': 'Library', 'Imágenes': 'Images', 'Utilidades': 'Utilities', 'Inicio': 'Home',
  'Pega un enlace, torrent, archivo, playlist o busca un vídeo…': 'Paste a link, torrent, file, playlist, or search for a video…',
  'Pega un enlace multimedia, playlist o archivo directo': 'Paste a media link, playlist, or direct file', 'Entrada universal de descarga': 'Universal download input',
  'Pegar': 'Paste', 'Torrent': 'Torrent', 'Archivo o enlace': 'File or link', 'Playlist': 'Playlist', 'Seleccionar': 'Select', 'Seleccionar descargas': 'Select downloads', 'Todas las categorías': 'All categories', 'Filtrar categorías': 'Filter categories', 'Mostrar detalles': 'Show details', 'Pausar': 'Pause',
  'Analizar': 'Analyze', 'Analizando…': 'Analyzing…', 'Limpiar': 'Clear', 'Activas': 'Active', 'Completadas': 'Completed', 'Velocidad': 'Speed',
  'Pendientes': 'Pending', 'En ejecución': 'Running', 'Con errores': 'With errors', 'Archivos': 'Files', 'Vídeo': 'Video', 'Audio': 'Audio', 'Multimedia': 'Media',
  'No hay descargas aquí todavía': 'No downloads here yet', 'Pega un enlace, añade un torrent o busca un vídeo para comenzar.': 'Paste a link, add a torrent, or search for a video to get started.',
  'Nueva descarga': 'New download', 'ÁREA DE DESCARGAS': 'DOWNLOAD AREA', 'Resumen de descargas': 'Download summary', 'Sugerencias de búsqueda': 'Search suggestions',
  'RESULTADOS DE VÍDEO': 'VIDEO RESULTS', 'Cargando más resultados': 'Loading more results', 'Listos': 'Ready', 'Cargando resultados': 'Loading results',
  'Sigue escribiendo para buscar coincidencias.': 'Keep typing to search for matches.', 'Busca un vídeo por su título': 'Search for a video by title', 'También puedes escribir artista, canal o palabras clave.': 'You can also enter an artist, channel, or keywords.',
  'Vídeo encontrado': 'Video found', 'Sugerencia de YouTube': 'YouTube suggestion', 'Reproducir': 'Play', '↑↓ para navegar · Enter para analizar': '↑↓ to navigate · Enter to analyze', 'Ctrl + K enfoca el buscador': 'Ctrl + K focuses search',
  'Resumen': 'Overview', 'Detalles avanzados': 'Advanced details', 'Registro': 'Log', 'Motor': 'Engine', 'Protocolo': 'Protocol', 'Modo': 'Mode', 'Transferencia': 'Transfer', 'Conexiones': 'Connections', 'Recuperación': 'Recovery', 'Enlace original': 'Original link',
  'Cerrar': 'Close', 'Volver': 'Back', 'Volver al gestor': 'Back to manager', 'Abrir': 'Open', 'Mostrar archivo': 'Show in folder', 'Abrir archivo': 'Open file', 'Copiar ruta': 'Copy path', 'Copiar enlace original': 'Copy original link',
  'Eliminar': 'Delete', 'Eliminar selección': 'Delete selection', 'Cancelar': 'Cancel', 'Guardar': 'Save', 'Restablecer': 'Reset', 'Restablecer colores': 'Reset colors', 'Restablecer apariencia': 'Reset appearance',
  'Más detalles': 'More details', 'Actualizar': 'Update', 'Más tarde': 'Later', 'Instalar ahora': 'Install now', 'Preparando…': 'Preparing…', 'Buscar ahora': 'Check now', 'Buscar actualizaciones': 'Check for updates', 'Comentarios y sugerencias': 'Feedback', 'Ver release': 'View release', 'Ver extensión': 'View extension', 'Apoyar': 'Support',
  'Apoya el proyecto': 'Support the project', 'Tu apoyo ayuda a mantener Clear Download Manager en desarrollo.': 'Your support helps keep Clear Download Manager in development.',
  'Actualizaciones': 'Updates', 'Extensión': 'Extension', 'Historial': 'History', 'Todas': 'All', 'ACTUALIZACIÓN': 'UPDATE', 'EXTENSIÓN': 'EXTENSION', 'Actualizaciones anteriores': 'Previous updates',
  'General': 'General', 'Descargas simultáneas': 'Concurrent downloads', 'Carpeta de descargas': 'Download folder', 'Cambiar carpeta': 'Change folder', 'Abrir carpeta': 'Open folder', 'Comportamiento': 'Behavior', 'Reanudación': 'Resume', 'Parciales': 'Partials', 'Conservados': 'Kept', 'En tiempo real': 'Real-time', 'Disponible': 'Available', 'No detectado': 'Not detected',
  'Destino y organización': 'Destination and organization', 'UBICACIÓN ACTUAL': 'CURRENT LOCATION', 'Descargas HTTP simultáneas': 'Concurrent HTTP downloads', 'Descargas multimedia simultáneas': 'Concurrent media downloads', 'Las tareas activas continúan; el límite se aplica al próximo espacio disponible.': 'Active tasks continue; the limit applies to the next available slot.', 'Límite máximo por descarga': 'Maximum limit per download', 'Progreso': 'Progress',
  'Velocidad': 'Speed', 'Limitar velocidad de descarga': 'Limit download speed', 'Máximo por descarga': 'Maximum per download', 'Velocidad personalizada': 'Custom speed', 'Unidad': 'Unit', 'Sin límite': 'Unlimited', 'Personalizado': 'Custom', 'Se aplicará a descargas nuevas y reanudadas. MB/s significa megabytes por segundo.': 'Applies to new and resumed downloads. MB/s means megabytes per second.',
  'Multimedia': 'Media', 'Motores y preferencias': 'Engines and preferences', 'Disponibilidad': 'Availability', 'Sesión': 'Session', 'Cookies de Brave activadas': 'Brave cookies enabled', 'Sin cookies del navegador': 'No browser cookies', 'Mejor disponible': 'Best available', 'Calidad preferida': 'Preferred quality', 'Compatibilidad': 'Compatibility', 'Las políticas multimedia y el reproductor se conservan sin cambios.': 'Media policies and the player remain unchanged.',
  'Apariencia': 'Appearance', 'Personaliza la interfaz': 'Customize the interface', 'Tema y color': 'Theme and color', 'Tema': 'Theme', 'Sistema': 'System', 'Oscuro': 'Dark', 'Claro': 'Light', 'Color de acento': 'Accent color', 'Colores de acento': 'Accent colors', 'Colores de acento para iconos': 'Accent colors for icons', 'Color de iconos': 'Icon color', 'Controla la parte de color de los iconos; la base gris permanece limpia y legible.': 'Controls the colored part of icons; the gray base stays clean and legible.', 'Colores preajustados': 'Preset colors', 'Colores preajustados para iconos': 'Preset icon colors', 'Color personalizado': 'Custom color', 'Color personalizado de iconos': 'Custom icon color', 'Colores de progreso': 'Progress colors', 'Activo': 'Active', 'Completado': 'Completed', 'En pausa': 'Paused', 'Error': 'Error', 'Activo, completado, pausa y error conservan sus colores independientes.': 'Active, completed, paused, and error keep independent colors.', 'Escala y densidad': 'Scale and density', 'Escala automática': 'Automatic scale', 'Activada': 'Enabled', 'Desactivada': 'Disabled', 'Escala de interfaz': 'Interface scale', 'Reducir escala': 'Decrease scale', 'Aumentar escala': 'Increase scale', 'Porcentaje de escala': 'Scale percentage', 'Densidad': 'Density', 'Compacta': 'Compact', 'Equilibrada': 'Balanced', 'Amplia': 'Spacious', 'Avanzado': 'Advanced', 'Tamaño del texto': 'Text size', 'Miniaturas': 'Thumbnails', 'Medianas': 'Medium', 'Grandes': 'Large', 'Muy grandes': 'Extra large', 'Efectos': 'Effects', 'Superficie': 'Surface', 'Sólida': 'Solid', 'Mica': 'Mica', 'Movimiento': 'Motion', 'Reducido': 'Reduced', 'Desactivado': 'Off', 'Esquinas': 'Corners', 'Rectas': 'Sharp', 'Estándar': 'Standard', 'Suaves': 'Soft', 'Tamaño de texto, miniaturas y preferencias visuales': 'Text size, thumbnails, and visual preferences', 'Caca verde': 'Green', 'Caca azul': 'Blue', 'Violeta': 'Violet', 'Cian': 'Cyan', 'Rosa': 'Rose', 'Ámbar': 'Amber', 'Esmeralda': 'Emerald', 'Índigo': 'Indigo', 'Magenta': 'Magenta', 'Carmesí': 'Crimson', 'Turquesa': 'Teal', 'Gris predeterminado': 'Default gray', 'Automático': 'Automatic',
  'Integraciones': 'Integrations', 'Conexiones disponibles': 'Available connections', 'Extensión del navegador': 'Browser extension', 'Puente': 'Bridge', 'Preparado': 'Ready', 'Spotify': 'Spotify', 'Spotify está desactivado temporalmente.': 'Spotify is temporarily disabled.', 'Spotify desactivado': 'Spotify disabled',
  'Actualizaciones y diagnóstico': 'Updates and diagnostics', 'Estado local': 'Local status', 'Versiones': 'Versions', 'Aplicación': 'Application', 'Herramientas internas': 'Internal tools', 'Comprueba de forma segura el motor interno de multimedia.': 'Safely check the internal media engine.', 'Última comprobación': 'Last check', 'Diagnóstico visual': 'Visual diagnostics', 'Escala efectiva': 'Effective scale', 'Tipografía': 'Typography', 'Copiar diagnóstico': 'Copy diagnostics', 'Actualizado': 'Up to date', 'Comprobando…': 'Checking…', 'Descargando…': 'Downloading…', 'Verificando…': 'Verifying…', 'Instalando…': 'Installing…', 'No se pudo completar': 'Could not complete', 'Sin conexión': 'Offline', 'Actualizaciones no configuradas': 'Updates not configured', 'Estado no disponible': 'Status unavailable', 'Aún no comprobado': 'Not checked yet',
  'Preparar una descarga': 'Prepare a download', 'Pega un enlace multimedia, playlist o archivo directo y pulsa Analizar.': 'Paste a media link, playlist, or direct file and press Analyze.', 'Espera a que termine el análisis para confirmar la descarga.': 'Wait for analysis to finish to confirm the download.', 'Cerrar ahora saldrá completamente': 'Close now to exit completely', 'Cerrar ahora enviará CacaTools a la bandeja': 'Close now to send Clear Download Manager to the tray',
  'CENTRO DE DESCARGAS': 'DOWNLOAD CENTER', 'Enlace de descarga': 'Download link', 'Calidad': 'Quality', 'Formato': 'Format', 'Destino': 'Destination', 'Tamaño': 'Size', 'Selección': 'Selection', 'Descargar': 'Download', 'Descargando…': 'Downloading…', 'Cancelar': 'Cancel', 'Cargando…': 'Loading…', 'Resolviendo metadatos multimedia…': 'Resolving media metadata…', 'Analizando elementos de la playlist…': 'Analyzing playlist items…', 'Descarga lista': 'Download ready', 'Confirmar descarga': 'Confirm download', 'Espera': 'Wait', 'No se pudo analizar el enlace.': 'The link could not be analyzed.', 'Debes seleccionar al menos un elemento.': 'Select at least one item.', 'Elementos seleccionados': 'Selected items',
  'Buscar vídeos': 'Search videos', 'Título, artista, canal o descripción': 'Title, artist, channel, or description', 'Buscar': 'Search', 'La búsqueda se realiza mediante el resolvedor local. Nada se envía a CacaTools.': 'Search uses the local resolver. Nothing is sent anywhere.', 'Buscando coincidencias…': 'Searching for matches…',
  'Añadir torrent de forma local': 'Add a torrent locally', 'Pega un enlace magnet o selecciona un archivo .torrent. aria2c gestionará la descarga, la pausa y la recuperación.': 'Paste a magnet link or select a .torrent file. aria2c handles downloading, pausing, and recovery.', 'Magnet o archivo .torrent': 'Magnet or .torrent file', 'Elegir archivo': 'Choose file', 'Abre el selector nativo de Windows.': 'Opens the native Windows picker.', 'Pegar magnet': 'Paste magnet', 'Lee el portapapeles solo al pulsarlo.': 'Reads the clipboard only when pressed.', 'Motor privado y local': 'Private local engine', 'La fuente se entrega directamente a aria2c. CacaTools no utiliza un servidor intermediario.': 'The source is sent directly to aria2c. No intermediary server is used.', 'Añadir a la cola': 'Add to queue', 'Nueva descarga torrent': 'New torrent download',
  'Cancelar descarga': 'Cancel download', 'Cancelar y conservar': 'Cancel and keep', 'Cancelar y limpiar': 'Cancel and clean', 'Volver': 'Back', 'Eliminar descarga': 'Delete download', 'Eliminar selección': 'Delete selection', 'Solo de CacaTools': 'From Clear Download Manager only', 'CacaTools y almacenamiento': 'Clear Download Manager and storage', 'Confirmo la eliminación del almacenamiento': 'I confirm storage deletion', 'Eliminar archivo y registro': 'Delete file and record', 'Eliminar archivos y registros': 'Delete files and records',
  'Actualización disponible': 'Update available', 'ACTUALIZACIÓN DISPONIBLE': 'UPDATE AVAILABLE', 'La instalación no comienza automáticamente y se mantiene bloqueada mientras haya descargas activas.': 'Installation does not start automatically and remains blocked while downloads are active.',
  'Vista previa': 'Preview', 'No hay un enlace original disponible para esta tarea.': 'No original link is available for this task.', 'No hay novedades nuevas': 'No new updates', 'Las actualizaciones y avisos aparecerán aquí.': 'Updates and notices will appear here.',
  'Contenido administrado localmente por CacaTools.': 'Content managed locally by Clear Download Manager.', 'CacaTools encontró un error de interfaz': 'Clear Download Manager encountered an interface error', 'Recargar la interfaz': 'Reload interface'
});

const ES_PHRASES = Object.freeze([
  ['CacaTools', 'Clear Download Manager'],
  ['Esta versión de Clear Download Manager', 'This version of Clear Download Manager'],
  ['Clear Download Manager no puede', 'Clear Download Manager cannot'],
  ['Clear Download Manager todavía', 'Clear Download Manager still'],
  ['Se abrirá el navegador oficial de Spotify.', 'The official Spotify browser will open.'],
  ['No se pudieron inspeccionar las rutas.', 'The paths could not be inspected.'],
  ['La descarga ya no está disponible', 'The download is no longer available'],
  ['La fuente se entrega directamente', 'The source is sent directly']
]);

const EN_TO_ES = Object.freeze(Object.fromEntries(Object.entries(ES_TO_EN).map(([es, en]) => [en, es])));

function replaceKnown(value, locale) {
  let text = String(value ?? '');
  if (locale === 'en') {
    const exact = ES_TO_EN[text.trim()];
    if (exact) return text.replace(text.trim(), exact);
    for (const [from, to] of ES_PHRASES) text = text.split(from).join(to);
    for (const [from, to] of Object.entries(ES_TO_EN)) {
      if (from.length < 4 || !text.includes(from)) continue;
      text = text.split(from).join(to);
    }
    text = text.replace(/^(?:Abrir|Open) (.+) en el reproductor$/, 'Open $1 in the player');
    text = text.replace(/^Más acciones para (.+)$/, 'More actions for $1');
  } else {
    const exact = EN_TO_ES[text.trim()];
    if (exact) return text.replace(text.trim(), exact);
  }
  return text;
}

export const RUNTIME_TRANSLATION_TERMS = Object.freeze(Object.keys(ES_TO_EN));

export function localizeDom(root, locale = 'es') {
  if (!root || locale !== 'en') return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const parent = node.parentElement;
    if (!parent || /^(SCRIPT|STYLE|CODE|PRE|TEXTAREA|INPUT)$/i.test(parent.tagName)) continue;
    const next = replaceKnown(node.nodeValue, locale);
    if (next !== node.nodeValue) node.nodeValue = next;
  }
  root.querySelectorAll('title, [title], [aria-label], [placeholder], [data-tooltip]').forEach((element) => {
    for (const attribute of ['title', 'aria-label', 'placeholder', 'data-tooltip']) {
      if (!element.hasAttribute(attribute)) continue;
      const value = element.getAttribute(attribute);
      const next = replaceKnown(value, locale);
      if (next !== value) element.setAttribute(attribute, next);
    }
  });
}
