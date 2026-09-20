import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const exists = (relative) => fs.existsSync(path.join(root, relative));
const referenceRoot = 'docs/ui-reference/CacaTools-UI-Reference-v3';
const referenceFiles = ['README.md', 'index.html', 'app.js', 'styles.css'];
const referenceReadme = read(`${referenceRoot}/README.md`);
const referenceHtml = read(`${referenceRoot}/index.html`);
const referenceCss = read(`${referenceRoot}/styles.css`);
const subwindow = read('app-ui/subwindow.js');
const subwindowCss = read('app-ui/subwindow.css');
const subwindowHtml = read('app-ui/subwindow.html');
const lucide = read('app-ui/assets/icons/lucide.js');
const playlistRow = subwindow.slice(subwindow.indexOf('function playlistRow('), subwindow.indexOf('function playlistListMarkup('));
const checks = [
  ['La referencia v3 conserva sus cuatro archivos contractuales', referenceFiles.every((file) => exists(`${referenceRoot}/${file}`))],
  ['La referencia v3 declara playlist siempre en dos columnas', referenceReadme.includes('dos columnas') && referenceCss.includes('.track-grid') && /\.track-grid\s*\{[\s\S]*?grid-template-columns:\s*1fr\s+1fr/.test(referenceCss)],
  ['La referencia v3 no apila el layout de playlist en ventanas estrechas', !/\.playlist-layout\{grid-template-columns:1fr\}/.test(referenceCss)],
  ['La preparación carga la hoja V5 después de la base', subwindowHtml.indexOf('styles.css') < subwindowHtml.indexOf('subwindow.css')],
  ['El marcado multimedia conserva miniatura 16:9 y elimina el microtexto de merge', /class="media-thumb"[\s\S]*?data-role="thumbnail"/.test(subwindow) && subwindowCss.includes('.media-thumb{') && subwindowCss.includes('aspect-ratio:16/9') && !subwindow.includes('Video + audio se combinarán automáticamente.')],
  ['La playlist real contiene únicamente miniatura, título y canal', /data-role="item-check"[\s\S]*?data-action="preview-track"[\s\S]*?track-copy[\s\S]*?item\.creator/.test(playlistRow) && !playlistRow.includes('data-sp-') && !subwindow.includes('sp-analysis-note')],
  ['La virtualización mantiene dos columnas en producción', subwindow.includes('const columns = 2;') && /\.track-grid\{[\s\S]*?grid-template-columns:1fr 1fr;/.test(subwindowCss)],
  ['La playlist conserva dos columnas también en los breakpoints', !/\.playlist-layout\s*\{[^}]*grid-template-columns:\s*1fr[;}]/.test(subwindowCss) && subwindowCss.includes('grid-template-columns:minmax(0,1.66fr)')],
  ['Los iconos genéricos usan un único set SVG local', subwindow.includes("import { lucideIcon } from './assets/icons/lucide.js';") && lucide.includes('export function lucideIcon') && !/playlist\s*:\s*['"`][^'"`]*[♫▶▣⚙×−□▰✦✓•]/.test(subwindow)],
  ['Los logos de plataformas usan assets locales proporcionados', exists('app-ui/assets/platforms/youtube.ico') && exists('app-ui/assets/platforms/media_social_tiktok_icon_124256.ico') && subwindow.includes("'youtube.ico'") && subwindow.includes("'media_social_tiktok_icon_124256.ico'")],
  ['El acento de preparación permanece semántico y configurable', subwindow.includes("setProperty('--sp-accent-base'") && subwindowCss.includes('var(--sp-accent)') && !subwindowCss.includes('rgba(3,252,32')],
  ['HTTP mantiene identidad de archivo y zona de destino separadas', subwindow.includes('http-info') && subwindow.includes('http-destination') && subwindowCss.includes('.http-layout')],
  ['No queda la regla visual previa de una playlist de una columna en la capa final', !/\.playlist-layout\s*\{[^}]*grid-template-columns:\s*1fr[;}]/.test(subwindowCss)]
];
for (const [label, pass] of checks) console.log(`${pass ? 'OK' : 'FAIL'}: ${label}`);
const failures = checks.filter(([, pass]) => !pass).map(([label]) => label);
if (failures.length) {
  console.error(`\nUI Reference v3 falló: ${failures.length}/${checks.length}.`);
  process.exit(1);
}
console.log(`\nOK: UI Reference v3 validada (${checks.length} condiciones).`);
