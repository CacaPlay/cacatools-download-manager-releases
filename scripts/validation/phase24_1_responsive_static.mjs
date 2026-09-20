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
const json = (file) => JSON.parse(read(file));
const files = {
  main: readFrontendSource('.js'),
  dmIndex: read('app-ui/download-manager/index.js'),
  dmCss: read('app-ui/download-manager/styles.css'),
  dmView: read('app-ui/download-manager/view/unified.js'),
  tauri: json('src-tauri/tauri.conf.json'),
  extensionHtml: read('extension/sidepanel.html'),
  extensionCss: read('extension/sidepanel.css'),
  extensionJs: read('extension/sidepanel.js'),
  worker: read('extension/service-worker.js'),
  manifest: json('extension/manifest.json')
};
const win = files.tauri.app.windows.find((entry) => entry.label === 'main');
const checks = [
  ['La ventana mantiene el mínimo funcional 1180 × 720', win?.minWidth === 1180 && win?.minHeight === 720],
  ['La densidad ofrece Compacta, Normal, Equilibrada y Amplia', ['compact','normal','balanced','spacious'].every((value) => files.main.includes(`value="${value}"`))],
  ['La densidad histórica se migra sin inflar filas existentes', files.main.includes("raw.density === 'balanced' ? 'normal'") && files.main.includes('APPEARANCE_REVISION = 7')],
  ['La densidad global llega al Centro de descargas', files.main.includes('appearanceDensity: appState.appearance.density') && files.dmIndex.includes('data-dm-density="${density}"')],
  ['Cada densidad define separación y altura propias', ['compact','balanced','spacious'].every((value) => files.dmCss.includes(`data-dm-density="${value}"`)) && files.dmCss.includes('--dm-download-list-gap')],
  ['La fila normal tiene respiración inferior adicional', files.dmCss.includes('--dm-row-padding-block:.76rem') && files.dmCss.includes('padding-bottom:.66rem')],
  ['El estado conserva texto y puede reducirse al punto', files.dmView.includes('aria-label="${escapeHtml(statusText)}"') && files.dmCss.includes('@container download-center (max-width:560px)') && files.dmCss.includes('.dm-item-status span{position:absolute')],
  ['El responsive continúa usando container queries', files.dmCss.includes('container-name:download-center') && files.dmCss.includes('@container download-center')],
  ['La extensión distingue app cerrada de puente ausente', files.extensionJs.includes("connected ? 'Disponible' : sleeping ? 'App cerrada' : 'No disponible'")],
  ['El estado de la extensión conserva tres estados semánticos', files.extensionCss.includes('.status::before') && files.extensionCss.includes('data-state="connected"') && files.extensionCss.includes('data-state="sleeping"') && files.extensionCss.includes('data-state="offline"')],
  ['En anchura estrecha la extensión oculta solo el texto del estado', files.extensionCss.includes('@media(max-width:390px)') && files.extensionCss.includes('font-size:0')],
  ['El service worker configura el panel también al arrancar', files.worker.includes('void configureSidePanel();') && files.worker.includes('openPanelOnActionClick: true')],
  ['El clic del icono tiene apertura explícita de respaldo', files.worker.includes('chrome.action.onClicked.addListener') && files.worker.includes('openSidePanelForTab') && files.worker.includes("path: 'sidepanel.html'" )],
  ['Manifest V3 y permisos de Chrome permanecen limpios', files.manifest.manifest_version === 3 && JSON.stringify(files.manifest.permissions) === JSON.stringify(['activeTab','scripting','downloads','storage','sidePanel','nativeMessaging'])],
  ['No se añadió popup que compita con el panel lateral', !files.manifest.action?.default_popup && files.manifest.side_panel?.default_path === 'sidepanel.html']
];
const failures = checks.filter(([, ok]) => !ok).map(([label]) => label);
fs.mkdirSync('docs/tests', { recursive: true });
fs.writeFileSync('docs/tests/phase24-1-responsive-static.json', `${JSON.stringify({ phase: '0.24.1-fase-7-responsive', checks: checks.length, failures, generatedAt: new Date().toISOString() }, null, 2)}\n`);
if (failures.length) {
  console.error(failures.map((failure) => `FALLO: ${failure}`).join('\n'));
  process.exit(1);
}
for (const [label] of checks) console.log(`OK: ${label}`);
console.log(`OK: Fase 7 valida ${checks.length} condiciones responsive y de apertura de extensión.`);
