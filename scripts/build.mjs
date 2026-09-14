import fs from 'node:fs';
import path from 'node:path';
import { transform } from 'esbuild';

const projectRoot = path.resolve();
const outputRoot = path.resolve(process.env.CDM_WEB_DIST_DIR || 'dist');
const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const packageVersion = String(packageJson.version || '').trim();
if (!/^\d+\.\d+\.\d+$/.test(packageVersion)) {
  throw new Error(`Versión inválida en package.json: ${packageVersion}`);
}
const outputRootWithSeparator = `${outputRoot}${path.sep}`;
if (outputRoot === projectRoot || outputRoot === path.parse(outputRoot).root || projectRoot.startsWith(outputRootWithSeparator)) {
  throw new Error(`Directorio de salida inseguro: ${outputRoot}`);
}
const output = (...segments) => path.join(outputRoot, ...segments);

fs.rmSync(outputRoot, { recursive: true, force: true });
fs.mkdirSync(output('app-ui'), { recursive: true });
const indexSource = fs.readFileSync('index.html', 'utf8');
fs.writeFileSync(output('index.html'), indexSource.replaceAll('__CDM_VERSION__', packageVersion));

for (const file of ['main.js', 'subwindow.js', 'subwindow.html', 'subwindow.css', 'styles.css', 'favicon.svg', 'media-preview.svg']) {
  fs.copyFileSync(path.join('app-ui', file), output('app-ui', file));
}

function copyDirectory(source, target) {
  fs.mkdirSync(target, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const from = path.join(source, entry.name);
    const to = path.join(target, entry.name);
    if (entry.isDirectory()) copyDirectory(from, to);
    else fs.copyFileSync(from, to);
  }
}

copyDirectory('app-ui/modules', output('app-ui', 'modules'));
copyDirectory('app-ui/download-manager', output('app-ui', 'download-manager'));
copyDirectory('app-ui/styles', output('app-ui', 'styles'));
copyDirectory('app-ui/player', output('app-ui', 'player'));
copyDirectory('app-ui/assets', output('app-ui', 'assets'));

async function minifyFiles(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await minifyFiles(filePath);
      continue;
    }
    if (!/\.(?:js|css)$/.test(entry.name)) continue;
    const loader = entry.name.endsWith('.css') ? 'css' : 'js';
    const source = fs.readFileSync(filePath, 'utf8');
    const result = await transform(source, { loader, minify: true, legalComments: 'none' });
    fs.writeFileSync(filePath, result.code);
  }
}

await minifyFiles(output('app-ui'));
console.log(`OK: frontend local y módulos integrados construidos en ${outputRoot}.`);
