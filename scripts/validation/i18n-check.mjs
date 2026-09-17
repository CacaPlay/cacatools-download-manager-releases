import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { LOCALE_CATALOGS } from '../../app-ui/modules/i18n/index.js';
import { RUNTIME_TRANSLATION_TERMS } from '../../app-ui/modules/i18n/runtime.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const es = LOCALE_CATALOGS.es;
const en = LOCALE_CATALOGS.en;
const errors = [];
const esKeys = Object.keys(es).sort();
const enKeys = Object.keys(en).sort();
if (JSON.stringify(esKeys) !== JSON.stringify(enKeys)) {
  errors.push(`ES/EN key mismatch: ES-only=${esKeys.filter((key) => !Object.hasOwn(en, key)).join(',') || 'none'} EN-only=${enKeys.filter((key) => !Object.hasOwn(es, key)).join(',') || 'none'}`);
}
const placeholders = (value) => [...String(value).matchAll(/\{\{?\s*([\w.-]+)\s*\}?\}/g)].map((match) => match[1]).sort();
for (const key of esKeys) {
  for (const [locale, catalog] of [['es', es], ['en', en]]) {
    const value = catalog[key];
    if (value === undefined || value === null || (typeof value !== 'function' && !String(value).trim())) errors.push(`${locale}.${key} is empty`);
  }
  if (typeof es[key] === 'function' || typeof en[key] === 'function') {
    if (typeof es[key] !== typeof en[key]) errors.push(`${key} function mismatch`);
    else if (placeholders(es[key].toString()).join('|') !== placeholders(en[key].toString()).join('|')) errors.push(`${key} interpolation mismatch`);
  }
}
for (const relative of ['app-ui/main.js', 'app-ui/download-manager/view/sections.js', 'app-ui/download-manager/view/shared.js']) {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) errors.push(`missing required surface: ${relative}`);
}
const runtimeFiles = [
  'app-ui/main.js',
  'app-ui/modules/composition/index.js',
  'app-ui/modules/settings/index.js',
  'app-ui/modules/runtime/index.js',
  'app-ui/modules/playlists/index.js',
  'app-ui/download-manager/actions.js',
  'app-ui/download-manager/events.js',
  'app-ui/download-manager/view/unified.js',
  'app-ui/download-manager/view/dialogs.js',
  'app-ui/download-manager/view/shared.js',
  'app-ui/download-manager/view/sections.js',
  'app-ui/subwindow.js',
  'app-ui/player/player.js',
  'app-ui/player/index.html'
];
const sourceText = runtimeFiles.map((relative) => {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) { errors.push(`missing runtime surface: ${relative}`); return ''; }
  return fs.readFileSync(file, 'utf8');
}).join('\n');
const coreTerms = ['Pegar', 'Torrent', 'Archivo o enlace', 'Playlist', 'Seleccionar', 'Analizar', 'Todas las categorías', 'Activas', 'Completadas', 'Velocidad', 'Ajustes', 'Descargas', 'Novedades', 'Apariencia', 'Integraciones', 'Más detalles', 'Ver release', 'Detalles avanzados', 'Copiar diagnóstico'];
const uncovered = coreTerms.filter((term) => sourceText.includes(term) && !RUNTIME_TRANSLATION_TERMS.includes(term) && !Object.hasOwn(es, term));
if (uncovered.length) errors.push(`hardcoded core UI terms lack localization coverage: ${uncovered.join(', ')}`);
const knownUserFacingTerms = [
  'Comprobando el archivo', 'Esperando el archivo', 'Preparar descarga HTTP', 'Preparar playlist',
  'Reintentar análisis', 'Selecciona un formato y calidad compatibles.', 'Selecciona una calidad disponible.',
  'Detalles avanzados', 'Abrir carpeta de descargas', 'Eliminar del historial', 'Pausar playlist',
  'Reanudar playlist', 'Motor y diagnóstico', 'Archivos relacionados', 'Registro del trabajo',
  'Calidad oficial de YouTube', 'No hay una pista de subtítulos seleccionable para este contenido.',
  'El archivo no pudo reproducirse', 'Actualización instalada. Windows cerrará la aplicación para finalizar.',
  'Comprobando la versión publicada…', 'Descargando y verificando la actualización firmada…',
  'Espera a que terminen las descargas activas antes de instalar.'
];
const uncoveredKnown = knownUserFacingTerms.filter((term) => sourceText.includes(term) && !RUNTIME_TRANSLATION_TERMS.includes(term) && !Object.hasOwn(es, term));
if (uncoveredKnown.length) errors.push(`known user-facing literals lack localization coverage: ${uncoveredKnown.join(', ')}`);
if (!sourceText.includes('localizeDom')) errors.push('runtime localization hook is not connected');
if (errors.length) {
  console.error(`i18n check failed (${errors.length})`);
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}
console.log(`i18n check passed: ${esKeys.length} shared ES/EN keys; ${RUNTIME_TRANSLATION_TERMS.length} runtime UI terms covered; required UI surfaces present`);
