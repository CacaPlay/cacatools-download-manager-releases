import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [,, layout = 'command-center', theme = 'dark', output = '', modal = ''] = process.argv;
const preferences = {
  layout,
  theme,
  accent: '#2f9bff',
  success: '#51c987',
  warning: '#e8b04c',
  danger: '#ef6b72',
  sidebarCollapsed: false,
  inspectorCollapsed: false,
  lowerPanelCollapsed: false,
  compactRows: false,
  filter: 'all',
  category: 'all',
  query: '',
  selectedJobId: 1,
  inspectorTab: 'summary',
  commandPanel: 'overview'
};

globalThis.localStorage = {
  getItem: () => JSON.stringify(preferences),
  setItem: () => {},
  removeItem: () => {}
};
globalThis.window = { matchMedia: () => ({ matches: theme === 'light' }) };

const moduleUrl = pathToFileURL(path.resolve('app-ui/download-manager/index.js')).href;
const { openDownloadManagerModal, renderDownloadManager } = await import(moduleUrl);
if (modal) openDownloadManagerModal(modal);
const snapshot = {
  jobs: [
    { id: 1, title: 'whql-amd-software-adrenalin-edition-26.7.1-win11-a.exe', detail: '523.4 MB de 941 MB · 16 conexiones', status: 'running', progress: 68, downloaded_bytes: 548824000, total_bytes: 986710000, speed_bps: 9122611, eta_seconds: 48, kind: 'file', engine: 'aria2c', category: 'Drivers', origin: 'Directo', destination: 'C:\\Users\\jerem\\Downloads\\Drivers\\whql-amd.exe', source_url: 'https://drivers.amd.com/file.exe' },
    { id: 2, title: 'ubuntu-24.04.2-desktop-amd64.iso', detail: '2.22 GB de 2.33 GB · 24 conexiones', status: 'running', progress: 95, downloaded_bytes: 2383700000, total_bytes: 2501800000, speed_bps: 12897484, eta_seconds: 9, kind: 'file', engine: 'aria2c', category: 'S.O.', origin: 'HTTP', destination: 'C:\\Users\\jerem\\Downloads\\ISO\\ubuntu.iso' },
    { id: 3, title: 'Video_4K_Cinematic_Walkthrough.mp4', detail: '1.15 GB de 2.69 GB · 8 conexiones', status: 'paused', progress: 42, downloaded_bytes: 1234800000, total_bytes: 2888100000, speed_bps: 0, eta_seconds: 157, kind: 'media', engine: 'yt-dlp', category: 'Vídeo', origin: 'yt-dlp', thumbnail: 'https://i.ytimg.com/vi/aqz-KE-bpKQ/hqdefault.jpg', source_url: 'https://youtube.com/watch?v=aqz-KE-bpKQ' },
    { id: 4, title: 'project-assets.zip', detail: '820.1 MB · Alta prioridad', status: 'queued', progress: 0, downloaded_bytes: 0, total_bytes: 859937177, speed_bps: 0, kind: 'file', engine: 'aria2c', category: 'Archivos', origin: 'Directo' },
    { id: 5, title: 'documentacion-api.pdf', detail: '12.4 MB · Verificado', status: 'completed', progress: 100, downloaded_bytes: 13002342, total_bytes: 13002342, speed_bps: 0, kind: 'file', engine: 'aria2c', category: 'Documentos', origin: 'Directo' },
    { id: 6, title: 'Playlist privada - episodio 03.webm', detail: 'Vídeo no disponible · requiere revisión', status: 'failed', progress: 17, downloaded_bytes: 17200000, total_bytes: 101000000, speed_bps: 0, kind: 'media', engine: 'yt-dlp', category: 'Vídeo', origin: 'yt-dlp', source_url: 'https://example.invalid/video' }
  ]
};
const markup = renderDownloadManager({ snapshot, pendingJobs: [], runtimeStatus: { mode: 'local', aria2_available: true, media_available: true }, mediaRuntimeStatus: { yt_dlp: 'yt-dlp.exe', ffmpeg: 'ffmpeg.exe', ffprobe: 'ffprobe.exe' }, downloadDirectory: 'C:\\Users\\jerem\\Downloads\\CacaTools' });
const css = fs.readFileSync('app-ui/download-manager/styles.css', 'utf8');
const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#070b10}${css}</style></head><body>${markup}</body></html>`;
if (output) fs.writeFileSync(output, html);
else process.stdout.write(html);
