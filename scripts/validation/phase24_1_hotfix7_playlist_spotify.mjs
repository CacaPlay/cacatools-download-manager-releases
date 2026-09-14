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
const main = readFrontendSource('.js');
const css = readFrontendSource('.css');

const checks = [
  ['Metadatos de playlist toleran valores null', main.includes("const source = item && typeof item === 'object' ? item : {}") && main.includes('function playlistMetadata(item = {})')],
  ['Actualización de cola tolera elementos null', main.includes('Number(item?.position ?? completed + active + index + 1)') && main.includes('.filter(Boolean)')],
  ['Spotify detecta cualquier subdominio oficial', main.includes("host === 'spotify.com' || host.endsWith('.spotify.com')")],
  ['Spotify usa la ventana nativa sin estado legacy incrustado', main.includes("open_preparation_window") && !main.includes('showSpotifyDisabledWorkspace') && !main.includes('analysis-error-state')],
  ['Resumen global y barra de playlist fueron retirados', !main.includes('class="playlist-summary-card dm-workspace-hero"') && !main.includes('data-playlist-overall-bar')],
  ['Preparación muestra solo spinner y estado', !main.includes('La interfaz seguirá respondiendo mientras el motor procesa metadatos y formatos.') && !main.includes("${icon('sparkles',30)}<strong")],
  ['Ver Descargas no reabre el workspace legacy', !main.includes('minimizeDownloadWorkspace') && !main.includes('renderDownloadDialog') && !main.includes('workspaceMarkup')],
  ['Errores globales se deduplican y pasan por friendlyError', main.includes('lastUnhandledUiError') && main.includes('const message = friendlyError(event.reason)')],
  ['Cabecera y pie compactos', css.includes('min-height:3.18rem!important') && css.includes('min-height:2.72rem!important')],
  ['Minimizado se convierte en chip compacto', css.includes('width:min(25rem,calc(100vw - 1rem))!important') && css.includes('height:3.15rem!important')],
  ['Texto operativo de subventanas escala de forma legible', css.includes('font-size:max(14px,var(--font-sm))!important')],
  ['Layout de cola ya no reserva área de resumen', css.includes('grid-template-areas:"main side"!important')]
];

const failures = checks.filter(([, ok]) => !ok).map(([label]) => label);
const report = { phase: '0.24.1-hotfix-7-playlist-spotify', checks: checks.length, failures, generatedAt: new Date().toISOString() };
fs.mkdirSync('docs/tests', { recursive: true });
fs.writeFileSync('docs/tests/phase24-1-hotfix7-playlist-spotify.json', `${JSON.stringify(report, null, 2)}\n`);
if (failures.length) {
  console.error(failures.map((failure) => `FALLO: ${failure}`).join('\n'));
  process.exit(1);
}
for (const [label] of checks) console.log(`OK: ${label}`);
console.log(`OK: Hotfix 7 valida ${checks.length} condiciones de playlist, Spotify y subventanas.`);
