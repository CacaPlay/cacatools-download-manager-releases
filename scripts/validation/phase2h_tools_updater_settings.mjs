import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

globalThis.window = { __cacatoolsVisualDiagnostics: {} };
const { configureSettings, settingsMarkup } = await import('../../app-ui/modules/settings/index.js');

const state = {
  settingsCategory: 'updates',
  runtimeStatus: { version: '0.45.4' },
  mediaRuntimeStatus: { yt_dlp: true, ffmpeg: true },
  toolUpdateStatus: { component: 'yt-dlp', state: 'UNAVAILABLE', canUpdate: false, availableVersion: null, lastChecked: null },
  appearance: { theme: 'system', preset: 'blue', accent: '#00b8ff', scale: 100, density: 'balanced' }
};
configureSettings({
  getAppState: () => state,
  icon: () => '',
  escapeHtml: (value) => String(value ?? ''),
  visualDiagnosticsSnapshot: () => ({ resolvedScale: 100, font: { size: '16px' } }),
  displayedScalePercent: (value) => value,
  automaticScalePercent: () => 100,
  downloadDirectoryLabel: () => 'Descargas\\CacaTools',
  APP_VERSION: '0.45.4'
});

const labels = new Map([
  ['UNAVAILABLE', 'Actualizaciones no configuradas'],
  ['CURRENT', 'Actualizado'],
  ['AVAILABLE', 'Disponible'],
  ['CHECKING', 'Comprobando…'],
  ['INSTALLING', 'Instalando…'],
  ['UPDATED', 'Actualizado'],
  ['OFFLINE', 'Sin conexión'],
  ['FAILED', 'No se pudo completar']
]);
for (const [status, label] of labels) {
  state.toolUpdateStatus = { component: 'yt-dlp', state: status, canUpdate: status === 'AVAILABLE', availableVersion: status === 'AVAILABLE' ? '2026.09.01' : null, lastChecked: null };
  const markup = settingsMarkup();
  assert.match(markup, /Herramientas internas/);
  assert.match(markup, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
}

const root = path.dirname(path.dirname(path.dirname(fileURLToPath(import.meta.url))));
const commands = fs.readFileSync(path.join(root, 'src-tauri/src/commands/tools.rs'), 'utf8');
assert.match(commands, /get_tool_update_status\s*\(app: AppHandle\)/);
assert.match(commands, /check_tool_updates_now\s*\(app: AppHandle\)/);
assert.match(commands, /apply_available_tool_update\s*\(\s*app: AppHandle,\s*state: State/);
assert.doesNotMatch(commands, /PathBuf|Url|sha256|artifact|component:\s*String|path:\s*|url:\s*|hash:\s*/i);
assert.doesNotMatch(settingsMarkup(), /cacaplay\.lat|ozelot\.github\.io|https?:\/\//i);
console.log('OK: Settings tool updater states and closed IPC contract validated.');
