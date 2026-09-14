import fs from 'node:fs';
const readFrontendSource = (extension) => fs.readdirSync('app-ui', { recursive: true })
  .filter((file) => file.endsWith(extension) && !file.replaceAll('\\', '/').startsWith('download-manager/'))
  .sort((a, b) => {
    const primary = extension === '.js' ? 'main.js' : 'styles.css';
    return a === primary ? -1 : b === primary ? 1 : a.localeCompare(b);
  })
  .map((file) => fs.readFileSync(`app-ui/${file}`, 'utf8'))
  .join('\n');

const files = {
  main: readFrontendSource('.js'),
  css: fs.readFileSync('app-ui/download-manager/styles.css', 'utf8'),
  appCss: readFrontendSource('.css'),
  unified: fs.readFileSync('app-ui/download-manager/view/unified.js', 'utf8'),
  command: fs.readFileSync('app-ui/download-manager/view/command-center.js', 'utf8'),
  zen: fs.readFileSync('app-ui/download-manager/view/zen-sidebar.js', 'utf8'),
  model: fs.readFileSync('app-ui/download-manager/core/model.js', 'utf8'),
  rust: fs.readdirSync('src-tauri/src', { recursive: true })
    .filter((file) => file.endsWith('.rs'))
    .sort((a, b) => (a === 'lib.rs' ? -1 : b === 'lib.rs' ? 1 : a.localeCompare(b)))
    .map((file) => fs.readFileSync(`src-tauri/src/${file}`, 'utf8'))
    .join('\n')
};
const assertions = [
  ['single unified input', files.unified.includes('data-dm-unified-input')],
  ['predictive suggestions', files.unified.includes('dm-unified-suggestions')],
  ['automatic alternatives', files.unified.includes('dm-inline-alternatives')],
  ['playlist stacked artwork', files.unified.includes('dm-playlist-stack')],
  ['Command Center hero area', files.command.includes('dm-primary-workspace') && !files.command.includes('dm-command-lower')],
  ['Zen hero area', files.zen.includes('dm-zen-workspace') && !files.zen.includes('dm-zen-engines')],
  ['larger default scale', files.model.includes('uiScale: 112') || fs.readFileSync('app-ui/download-manager/core/constants.js','utf8').includes('uiScale: 112')],
  ['Ctrl+wheel scale', files.main.includes('onAnalyzeSource') && fs.readFileSync('app-ui/download-manager/index.js','utf8').includes("event.ctrlKey")],
  ['cohesive analysis view', files.appCss.includes('.analysis-v2-grid') && files.appCss.includes('.playlist-v2-layout')],
  ['responsive compact window', files.css.includes('@media(max-width:820px)')],
  ['theme aware dialog', files.main.includes('dm-dialog-theme-${visual.theme}')],
  ['playlist history snapshot', files.rust.includes('PlaylistBatchSummarySnapshot') && files.model.includes('snapshot.playlist_batches')],
  ['bounded multimedia analysis', files.rust.includes('command_output_with_timeout')],
  ['functional playlist replacement', files.rust.includes('replace_playlist_item_with_alternative') && files.main.includes('data-playlist-alternative-job')],
  ['filter labels protected', files.css.includes('.dm-workspace-toolbar>.dm-filter-row')],
  ['playlist controls protected', files.appCss.includes('.playlist-v2-options>*')],
  ['Zen footer uses themed controls', files.css.includes('.dm-command-sidebar > footer,.dm-zen-nav > footer') && files.css.includes('.dm-command-sidebar > footer button,.dm-zen-nav > footer button')],
  ['medium-width detection does not overlap helpers', files.css.includes('@media(max-width:1100px){\n  .dm-unified-detection{display:none}')]
];
const failed = assertions.filter(([, pass]) => !pass).map(([name]) => name);
if (failed.length) {
  console.error(`Phase 17 UI static gate failed: ${failed.join(', ')}`);
  process.exit(1);
}
console.log(`OK: ${assertions.length} comprobaciones UI Phase 17.`);
