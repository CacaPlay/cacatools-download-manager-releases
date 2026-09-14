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
  main: readFrontendSource('.js'), css: read('app-ui/download-manager/styles.css'), appCss: readFrontendSource('.css'),
  constants: read('app-ui/download-manager/core/constants.js'), model: read('app-ui/download-manager/core/model.js'),
  index: read('app-ui/download-manager/index.js'), unified: read('app-ui/download-manager/view/unified.js'),
  command: read('app-ui/download-manager/view/command-center.js'), zen: read('app-ui/download-manager/view/zen-sidebar.js'),
  icons: read('app-ui/download-manager/view/icons.js'), rust: fs.readdirSync('src-tauri/src', { recursive: true })
    .filter((file) => file.endsWith('.rs'))
    .sort((a, b) => (a === 'lib.rs' ? -1 : b === 'lib.rs' ? 1 : a.localeCompare(b)))
    .map((file) => fs.readFileSync(`src-tauri/src/${file}`, 'utf8'))
    .join('\n')
};
const assertions = [
  ['Zen default', files.constants.includes("layout: 'zen-sidebar'")],
  ['phase18 appearance revision', files.constants.includes('appearanceRevision: 3') && files.model.includes('appearanceRevision: 3')],
  ['larger default scale', files.constants.includes('uiScale: 118')],
  ['Command secondary selectable', files.model.includes("value.layout === 'command-center'")],
  ['stable unified input repaint', files.index.includes('function paintUnifiedSearch') && files.index.includes("input?.closest?.('.dm-unified-search')")],
  ['debounced suggestions', files.index.includes('window.setTimeout(async () =>') && files.index.includes('280')],
  ['stale request protection', files.index.includes('runtimeState.unifiedRequestId')],
  ['bounded remote suggestion search', files.index.includes('4500')],
  ['single search border', files.css.includes('border:0!important') && files.css.includes('El borde pertenece al contenedor')],
  ['larger navigation icons', files.css.includes('width:24px;height:24px')],
  ['distinct Command table', files.command.includes('dm-primary-workspace') && files.css.includes('.dm-command-center .dm-download-area>header')],
  ['distinct Zen cards', files.zen.includes('dm-zen-workspace') && files.css.includes('.dm-zen-sidebar .dm-download-area>header{display:none}')],
  ['video thumbnails persisted', files.rust.includes("thumbnail TEXT NOT NULL DEFAULT ''") && files.rust.includes('NULLIF(media_jobs.thumbnail')],
  ['thumbnail passed from frontend', files.main.includes("thumbnail: appState.mediaAnalysis?.thumbnail || ''")],
  ['extension art', files.unified.includes("['document', 'document']") && files.unified.includes("['package', 'software']")],
  ['playlist stacked covers', files.unified.includes('dm-playlist-stack')],
  ['dialog full viewport center', files.appCss.includes('Phase 18 · diálogo de descarga centrado') && files.appCss.includes('place-items:center!important')],
  ['dialog draggable', files.main.includes('bindFloatingDownloadDialog') && files.main.includes('data-dialog-drag-handle')],
  ['dialog resizable', files.appCss.includes('resize:both')],
  ['playlist options enlarged', files.appCss.includes('.playlist-v2-list .playlist-select-item{min-height:4.8rem')],
  ['automatic alternatives', files.unified.includes('dm-inline-alternatives') && files.main.includes('data-playlist-alternative-job')],
  ['playlist persistent history', files.model.includes('snapshot.playlist_batches') && files.rust.includes('PlaylistBatchSummarySnapshot')],
  ['real-time manager refresh', files.main.includes("document.querySelector('.dm-host')")],
  ['no old technical blocks', !files.command.includes('dm-command-lower') && !files.zen.includes('dm-zen-engines')],
  ['version 0.18.0', JSON.parse(read('package.json')).version === '0.18.0']
];
const failed = assertions.filter(([, pass]) => !pass).map(([name]) => name);
if (failed.length) { console.error(`Phase 18 UI static gate failed: ${failed.join(', ')}`); process.exit(1); }
console.log(`OK: ${assertions.length} comprobaciones UI Phase 18.`);
