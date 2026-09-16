import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { LOCALE_CATALOGS } from '../../app-ui/modules/i18n/index.js';

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
if (errors.length) {
  console.error(`i18n check failed (${errors.length})`);
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}
console.log(`i18n check passed: ${esKeys.length} shared ES/EN keys; required UI surfaces present`);
