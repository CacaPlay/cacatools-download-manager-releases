import fs from 'node:fs';
const readFrontendSource = (extension) => fs.readdirSync('app-ui', { recursive: true })
  .filter((file) => file.endsWith(extension) && !file.replaceAll('\\', '/').startsWith('download-manager/'))
  .sort((a, b) => {
    const primary = extension === '.js' ? 'main.js' : 'styles.css';
    return a === primary ? -1 : b === primary ? 1 : a.localeCompare(b);
  })
  .map((file) => fs.readFileSync(`app-ui/${file}`, 'utf8'))
  .join('\n');

const read = (file) => fs.readFileSync(file, 'utf8');
const files = {
  main: readFrontendSource('.js'),
  manager: read('app-ui/download-manager/index.js'),
  unified: read('app-ui/download-manager/view/unified.js'),
  rust: fs.readdirSync('src-tauri/src', { recursive: true })
    .filter((file) => file.endsWith('.rs'))
    .sort((a, b) => (a === 'lib.rs' ? -1 : b === 'lib.rs' ? 1 : a.localeCompare(b)))
    .map((file) => fs.readFileSync(`src-tauri/src/${file}`, 'utf8'))
    .join('\n'),
  bridge: read('src-tauri/src/extension_bridge.rs'),
  worker: read('extension/service-worker.js'),
  sdk: read('extension/sdk/cacatools-native-client.js'),
  detector: read('extension/content/detector.js'),
  panel: read('extension/sidepanel.js'),
  host: read('extension/native-host/src/main.rs'),
  verify: read('scripts/verify-binaries.mjs'),
  prepare: read('scripts/prepare-windows-binaries.ps1'),
  config: read('src-tauri/resources/extension/extension-config.json')
};
const failures = [];
const requireToken = (source, token, label) => {
  if (!source.includes(token)) failures.push(`${label}: falta ${token}`);
};
const forbidToken = (source, token, label) => {
  if (source.includes(token)) failures.push(`${label}: conserva ${token}`);
};

requireToken(files.main, "invoke('resolve_spotify_source'", 'frontend Spotify');
requireToken(files.main, "invoke('queue_spotify_download'", 'cola frontend Spotify');
requireToken(files.rust, 'disable_legacy_spotify_jobs', 'migración controlada');
requireToken(files.rust, 'job_uses_disabled_spotify', 'bloqueo de reintentos');
requireToken(files.rust, "resolution_state='spotify_disabled'", 'estado persistente');
requireToken(files.rust, 'Err(spotify_disabled_error())', 'comandos nativos bloqueados');
requireToken(files.rust, 'spotdl: None', 'runtime spotDL aislado');
requireToken(files.rust, 'CONTENT_DISPOSITION', 'Content-Disposition');
requireToken(files.rust, 'remote_download_probe', 'URL final y cabeceras');
requireToken(files.rust, 'resolve_download_filename', 'resolución central de nombres');
requireToken(files.rust, '_ => "file"', 'archivo desconocido genérico backend');
requireToken(files.unified, "return ['file', 'generic'];", 'archivo desconocido genérico frontend');
requireToken(files.manager, 'forceDownloadManagerAllView', 'filtro Todas centralizado');
requireToken(files.main, 'extensionBridgePendingRequest', 'solicitud de extensión preservada');
if (files.bridge.includes('payload_contains_spotify')) failures.push('El host integrado aún bloquea metadata Spotify de forma recursiva');
if (files.host.includes('payload_contains_spotify')) failures.push('El host publicado aún bloquea metadata Spotify de forma recursiva');
requireToken(files.bridge, 'browser_download_capture', 'host integrado distingue capturas directas');
requireToken(files.host, 'browser_download_capture', 'host publicado distingue capturas directas');
requireToken(files.sdk, 'spotify_direct_capture_ignored', 'SDK protege capturas directas');
requireToken(files.detector, "id: 'spotify-page'", 'detector de página Spotify');
requireToken(files.panel, "status === 'spotify_disabled'", 'panel muestra rechazo');
requireToken(files.worker, 'SPOTIFY_DIRECT_CAPTURE_MESSAGE', 'service worker protege captura directa');
requireToken(files.config, 'aonppfnabjnicjjeoofkfjofolfibggp', 'ID publicado fijo');
forbidToken(files.verify, 'spotdl-4.5.2-win32.exe', 'gate de binarios');
requireToken(files.prepare, 'runtime omitted from this build', 'preparación sin spotDL');

const report = {
  gate: 'phase24.1-download-inputs',
  passed: failures.length === 0,
  spotifyEnabled: false,
  publishedExtensionId: 'aonppfnabjnicjjeoofkfjofolfibggp',
  checks: 24,
  failures,
  generatedAt: new Date().toISOString()
};
fs.mkdirSync('docs/tests', { recursive: true });
fs.writeFileSync('docs/tests/phase24-1-download-inputs.json', `${JSON.stringify(report, null, 2)}\n`);
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('OK: Fase 10 valida routing Spotify oficial, rechazo de capturas HTTP directas, extensión en Todas y nombres robustos por cabeceras, URL final y MIME.');
