const LOCALE_KEY = 'clear-download-manager/locale-v1';
export const SUPPORTED_LOCALES = Object.freeze(['system', 'es', 'en']);

const MESSAGES = Object.freeze({
  es: {
    settings: 'Ajustes', themeToggle: 'Cambiar tema', unreadNews: 'Hay novedades sin leer',
    news: 'Novedades', newsDescription: 'Actualizaciones, información y soporte de Clear Download Manager.', back: 'Volver al gestor',
    all: 'Todas', updates: 'Actualizaciones', extension: 'Extensión', history: 'Historial',
    noNews: 'No hay novedades nuevas', noNewsDescription: 'Las actualizaciones y avisos aparecerán aquí.',
    details: 'Más detalles', update: 'Actualizar', later: 'Más tarde', installed: 'Instalada',
    support: 'Apoya el proyecto', supportDescription: 'Tu apoyo ayuda a mantener Clear Download Manager en desarrollo.', supportAction: 'Apoyar',
    directLinks: 'Enlaces directos', close: 'Cerrar', open: 'Abrir', feedback: 'Comentarios y sugerencias', checkUpdates: 'Buscar actualizaciones', language: 'Idioma', system: 'Sistema', spanish: 'Español', english: 'English',
    extensionSummary: 'Envía enlaces, vídeos y playlists del navegador directamente a CDM.', updateSummary: 'CDM incluye mejoras importantes de estabilidad, rendimiento y experiencia de uso.', extensionTitle: 'Extensión de Clear Download Manager',
    general: 'General', windowStartup: 'Ventana e inicio', windowBehavior: 'Comportamiento de ventana', closeAction: 'Al pulsar cerrar', closeToTray: 'Cerrar a la bandeja', exitCompletely: 'Salir completamente', startWithWindows: 'Iniciar con Windows', automation: 'Automatismos', detectClipboard: 'Detectar enlaces copiados', clipboardDescription: 'Sugerir enlaces al volver a enfocar Clear Download Manager.', receiveNews: 'Recibir novedades', receiveNewsDescription: 'Muestra avisos y mensajes oficiales en Novedades.', automaticUpdates: 'Buscar actualizaciones automáticamente', automaticUpdatesDescription: 'Comprueba actualizaciones en segundo plano cuando hay conexión.', extensionRecommendation: 'Mostrar recomendación de la extensión', extensionRecommendationDescription: 'Permite que la extensión aparezca como sugerencia en Novedades.', status: 'Estado', minimize: 'Minimizar', taskbar: 'Barra de tareas', exit: 'Salida completa', tray: 'Bandeja',
    updateAvailable: (version) => `Clear Download Manager ${version} disponible`,
    updateCategory: 'ACTUALIZACIÓN', extensionCategory: 'EXTENSIÓN', historyTitle: 'Actualizaciones anteriores'
  },
  en: {
    settings: 'Settings', themeToggle: 'Change theme', unreadNews: 'Unread updates',
    news: "What's new", newsDescription: 'Updates, information and support for Clear Download Manager.', back: 'Back to manager',
    all: 'All', updates: 'Updates', extension: 'Extension', history: 'History',
    noNews: 'No new updates', noNewsDescription: 'Updates and notices will appear here.',
    details: 'More details', update: 'Update', later: 'Later', installed: 'Installed',
    support: 'Support the project', supportDescription: 'Your support helps keep Clear Download Manager in development.', supportAction: 'Support',
    directLinks: 'Direct links', close: 'Close', open: 'Open', feedback: 'Comments and suggestions', checkUpdates: 'Check for updates', language: 'Language', system: 'System', spanish: 'Español', english: 'English',
    extensionSummary: 'Send links, videos and playlists from your browser directly to CDM.', updateSummary: 'CDM includes important stability, performance and experience improvements.', extensionTitle: 'Clear Download Manager extension',
    general: 'General', windowStartup: 'Window and startup', windowBehavior: 'Window behavior', closeAction: 'When closing', closeToTray: 'Close to tray', exitCompletely: 'Exit completely', startWithWindows: 'Start with Windows', automation: 'Automation', detectClipboard: 'Detect copied links', clipboardDescription: 'Suggest links when Clear Download Manager regains focus.', receiveNews: 'Receive news', receiveNewsDescription: 'Show official notices and messages in What’s new.', automaticUpdates: 'Check for updates automatically', automaticUpdatesDescription: 'Check for updates in the background when connected.', extensionRecommendation: 'Show extension recommendation', extensionRecommendationDescription: 'Allow the extension to appear as a suggestion in What’s new.', status: 'Status', minimize: 'Minimize', taskbar: 'Taskbar', exit: 'Complete exit', tray: 'Tray',
    updateAvailable: (version) => `Clear Download Manager ${version} available`,
    updateCategory: 'UPDATE', extensionCategory: 'EXTENSION', historyTitle: 'Previous updates'
  }
});

// Exposed read-only for the repository i18n gate; application code should use
// translate()/messagesFor() so locale resolution remains centralized.
export const LOCALE_CATALOGS = MESSAGES;

export function normalizeLocale(value) {
  const locale = String(value || '').toLowerCase();
  return SUPPORTED_LOCALES.includes(locale) ? locale : 'system';
}

export function detectSystemLocale() {
  try { return /^es(?:[-_]|$)/i.test(navigator.language || '') ? 'es' : 'en'; } catch { return 'es'; }
}

export function resolveLocale(value = 'system') {
  const normalized = normalizeLocale(value);
  return normalized === 'system' ? detectSystemLocale() : normalized;
}

export function loadLocale() {
  try { return normalizeLocale(localStorage.getItem(LOCALE_KEY)); } catch { return 'system'; }
}

export function saveLocale(value) {
  const normalized = normalizeLocale(value);
  try { localStorage.setItem(LOCALE_KEY, normalized); } catch {}
  return normalized;
}

export function messagesFor(value = 'system') { return MESSAGES[resolveLocale(value)] || MESSAGES.es; }

export function translate(value, key, ...args) {
  const message = messagesFor(value)[key];
  return typeof message === 'function' ? message(...args) : message || MESSAGES.es[key] || key;
}

export function formatLocaleDate(value, locale = 'system') {
  if (value === null || value === undefined || value === '') return '';
  const raw = String(value).trim();
  const numeric = typeof value === 'number' ? value : Number(raw);
  if (Number.isFinite(numeric) && /^-?\d+(?:\.\d+)?$/.test(raw || String(value)) && numeric < 1000000000) return '';
  const timestamp = Number.isFinite(numeric) && numeric > 1000000000
    ? (numeric < 10000000000 ? numeric * 1000 : numeric)
    : Date.parse(String(value));
  if (!Number.isFinite(timestamp) || timestamp <= 0) return '';
  try { return new Intl.DateTimeFormat(resolveLocale(locale), { dateStyle: 'medium' }).format(new Date(timestamp)); } catch { return new Date(timestamp).toLocaleDateString(); }
}

export const LOCALE_STORAGE_KEY = LOCALE_KEY;
