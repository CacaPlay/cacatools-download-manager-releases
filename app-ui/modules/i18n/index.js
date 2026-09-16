const LOCALE_KEY = 'clear-download-manager/locale-v1';
export const SUPPORTED_LOCALES = Object.freeze(['system', 'es', 'en']);

const MESSAGES = Object.freeze({
  es: {
    news: 'Novedades', newsDescription: 'Actualizaciones, información y soporte de Clear Download Manager.',
    all: 'Todas', updates: 'Actualizaciones', extension: 'Extensión', history: 'Historial',
    noNews: 'No hay novedades nuevas', noNewsDescription: 'Las actualizaciones y avisos aparecerán aquí.',
    details: 'Más detalles', update: 'Actualizar', later: 'Más tarde', installed: 'Instalada',
    support: 'Apoya el proyecto', supportDescription: 'Tu apoyo ayuda a mantener Clear Download Manager en desarrollo.', supportAction: 'Apoyar',
    directLinks: 'Enlaces directos', close: 'Cerrar', language: 'Idioma', system: 'Sistema', spanish: 'Español', english: 'English',
    extensionSummary: 'Envía enlaces, vídeos y playlists del navegador directamente a CDM.',
    updateAvailable: (version) => `Clear Download Manager ${version} disponible`,
    updateCategory: 'ACTUALIZACIÓN', extensionCategory: 'EXTENSIÓN', historyTitle: 'Actualizaciones anteriores'
  },
  en: {
    news: "What's new", newsDescription: 'Updates, information and support for Clear Download Manager.',
    all: 'All', updates: 'Updates', extension: 'Extension', history: 'History',
    noNews: 'No new updates', noNewsDescription: 'Updates and notices will appear here.',
    details: 'More details', update: 'Update', later: 'Later', installed: 'Installed',
    support: 'Support the project', supportDescription: 'Your support helps keep Clear Download Manager in development.', supportAction: 'Support',
    directLinks: 'Direct links', close: 'Close', language: 'Language', system: 'System', spanish: 'Español', english: 'English',
    extensionSummary: 'Send links, videos and playlists from your browser directly to CDM.',
    updateAvailable: (version) => `Clear Download Manager ${version} available`,
    updateCategory: 'UPDATE', extensionCategory: 'EXTENSION', historyTitle: 'Previous updates'
  }
});

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
  const timestamp = Date.parse(String(value || ''));
  if (!Number.isFinite(timestamp)) return '';
  try { return new Intl.DateTimeFormat(resolveLocale(locale), { dateStyle: 'medium' }).format(new Date(timestamp)); } catch { return new Date(timestamp).toLocaleDateString(); }
}

export const LOCALE_STORAGE_KEY = LOCALE_KEY;
