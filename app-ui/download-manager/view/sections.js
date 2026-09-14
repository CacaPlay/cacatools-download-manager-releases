import { categoriesFromJobs, escapeHtml, formatBytes, formatSpeed, statusCounts } from '../core/model.js';
import { dmIcon } from './icons.js';
import { fileGlyph, infrastructureSettings, progressMarkup, settingsFields, statusLabel } from './shared.js';

const actionLabels = { resume: 'Iniciar o reanudar', pause: 'Pausar', cancel: 'Cancelar' };

export function sectionTitle(section) {
  return ({
    downloads: ['Descargas', 'Todos los trabajos locales y sus estados.'],
    panel: ['Panel', 'Vista general del gestor y accesos rápidos.'],
    queue: ['Gestor de cola', 'Ordena lo pendiente y controla qué se ejecuta.'],
    running: ['Descargas activas', 'Trabajos que están transfiriendo datos ahora.'],
    completed: ['Completadas', 'Archivos terminados y validados.'],
    history: ['Historial', 'Trabajos completados, cancelados o con error.'],
    media: ['Multimedia', 'Vídeos, audio y playlists resueltos con yt-dlp.'],
    categories: ['Categorías', 'Organiza y filtra archivos por tipo.'],
    scheduler: ['Programación', 'Inicia, pausa o cancela trabajos automáticamente.'],
    settings: ['Ajustes', 'Diseño, modo visual y colores del gestor.'],
    news: ['Novedades', 'Actualizaciones, información y soporte de CacaTools.']
  })[section] || ['Descargas', 'Gestor local de archivos y multimedia.'];
}

export function sectionHeading(section, count = null) {
  const [title, description] = sectionTitle(section);
  return `<header class="dm-section-heading"><div><span>${dmIcon(section === 'scheduler' ? 'calendar' : section === 'categories' ? 'folder' : section === 'settings' ? 'settings' : section === 'news' ? 'bell' : section === 'media' ? 'video' : 'download', 26)}</span><div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div></div>${count === null ? '' : `<b>${count}</b>`}</header>`;
}

export function categoriesPanel(jobs) {
  const categories = categoriesFromJobs(jobs);
  const cards = categories.map((category) => {
    const items = jobs.filter((job) => job.category === category);
    const running = items.filter((job) => job.status === 'running').length;
    const bytes = items.reduce((total, job) => total + Number(job.totalBytes || job.downloadedBytes || 0), 0);
    return `<button class="dm-category-card" data-dm-category-jump="${escapeHtml(category)}"><span>${dmIcon(category === 'Vídeo' ? 'video' : category === 'Música' ? 'sparkles' : category === 'Torrents' ? 'magnet' : 'folder', 28)}</span><div><strong>${escapeHtml(category)}</strong><small>${items.length} elemento${items.length === 1 ? '' : 's'} · ${formatBytes(bytes)}</small></div><em>${running ? `${running} activa${running === 1 ? '' : 's'}` : 'Abrir'}</em></button>`;
  }).join('');
  return `<section class="dm-section-page">${sectionHeading('categories', jobs.length)}<div class="dm-category-grid">${cards || `<div class="dm-section-empty">${dmIcon('folder', 42)}<strong>No hay categorías todavía</strong><span>Se crearán automáticamente al añadir archivos.</span></div>`}</div></section>`;
}

export function schedulerPanel(jobs, schedules = [], selectedJobId = null) {
  const jobMap = new Map(jobs.map((job) => [Number(job.id), job]));
  const rows = schedules.map((schedule) => {
    const job = jobMap.get(Number(schedule.job_id));
    return `<article class="dm-schedule-row"><span>${dmIcon('calendar', 24)}</span><div><strong>${escapeHtml(job?.title || `Trabajo #${schedule.job_id || '—'}`)}</strong><small>${escapeHtml(actionLabels[schedule.action] || schedule.action)} · ${escapeHtml(String(schedule.run_at || '').replace('T', ' '))}${schedule.repeat_daily ? ' · cada día' : ''}</small></div><em>${schedule.enabled ? 'Activa' : 'Desactivada'}</em><button data-dm-delete-schedule="${schedule.id}" aria-label="Eliminar tarea">${dmIcon('trash', 18)}</button></article>`;
  }).join('');
  return `<section class="dm-section-page">${sectionHeading('scheduler', schedules.length)}<div class="dm-scheduler-page-actions"><div>${dmIcon('clock', 24)}<span><strong>Programador local</strong><small>La aplicación revisa las tareas cada pocos segundos y conserva la programación en SQLite.</small></span></div><button class="dm-primary-button" data-dm-new-schedule data-dm-schedule-job="${selectedJobId || ''}" ${jobs.length ? '' : 'disabled'}>${dmIcon('plus')} Nueva tarea</button></div><div class="dm-schedule-list">${rows || `<div class="dm-section-empty">${dmIcon('calendar', 46)}<strong>No hay tareas programadas</strong><span>Selecciona una descarga y crea una acción con fecha y hora.</span></div>`}</div></section>`;
}

export function settingsPanel(preferences) {
  return `<section class="dm-section-page">${sectionHeading('settings')}<div class="dm-settings-page"><article><span>${dmIcon('palette', 34)}</span><div><strong>Apariencia Zen</strong><small>El gestor usa una única composición Zen, fluida y legible; el usuario controla modo, escala y colores sin alterar el motor.</small></div></article><div class="dm-settings-page-fields">${settingsFields(preferences)}</div><aside>${dmIcon('shield', 22)}<span><strong>Preferencias locales</strong><small>Se guardan únicamente en este equipo y pueden restablecerse sin tocar descargas ni historial.</small></span></aside></div></section>`;
}

export function newsPanel(context = {}) {
  const messages = Array.isArray(context.newsMessages) ? context.newsMessages : [];
  const iconFor = (message) => message.type === 'update' ? 'download' : message.type === 'extension' ? 'link' : message.type === 'release' ? 'sparkles' : message.type === 'manual' ? 'globe' : 'shield';
  const actionsFor = (message) => {
    if (message.type === 'update') return `<button type="button" data-dm-news-action="open-update-modal">Actualizar</button><button type="button" data-dm-news-action="dismiss-update">Más tarde</button>`;
    if (message.type === 'extension') return `<button type="button" data-dm-news-action="open-extension-modal">Ver extensión</button><button type="button" data-dm-news-action="decline-extension">No gracias</button>`;
    if (message.action?.type === 'open-feedback') return `<button type="button" data-dm-news-action="feedback">Comentarios y sugerencias</button>`;
    if (message.action?.type === 'open-url') return `<button type="button" data-dm-news-action="open-news-url" data-news-url="${escapeHtml(message.action.url || '')}">${escapeHtml(message.action.label || 'Abrir')}</button>`;
    return '';
  };
  const markup = messages.map((message) => `<article class="dm-news-item ${message.actionRequired ? 'dm-news-action' : ''} ${message.read ? 'is-read' : ''}" data-news-id="${escapeHtml(message.id)}"><span>${message.thumbnail ? `<img class="dm-news-thumbnail" src="${escapeHtml(message.thumbnail)}" alt="" loading="lazy" decoding="async">` : dmIcon(iconFor(message), 22)}</span><div><strong>${escapeHtml(message.title)}</strong><small>${escapeHtml(message.body)}</small>${actionsFor(message) ? `<div class="dm-news-actions">${actionsFor(message)}</div>` : ''}</div></article>`).join('');
  const empty = `<div class="dm-section-empty dm-news-empty">${dmIcon('bell', 42)}<strong>No hay novedades nuevas</strong><span>Las actualizaciones, avisos y soporte aparecerán aquí.</span></div>`;
  return `<section class="dm-section-page dm-news-page">${sectionHeading('news', messages.filter((message) => !message.read || message.actionRequired).length || null)}<div class="dm-news-list">${markup || empty}</div><footer class="dm-news-footer"><button type="button" data-dm-news-action="check-update">${dmIcon('retry', 16)} Buscar actualizaciones</button><button type="button" data-dm-news-action="feedback">${dmIcon('clipboard', 16)} Comentarios y sugerencias</button></footer></section>`;
}

export function mediaOverview(jobs) {
  const mediaJobs = jobs.filter((job) => ['media', 'video', 'audio'].includes(job.kind) || job.origin === 'yt-dlp');
  const cards = mediaJobs.slice(0, 24).map((job) => `<article class="dm-media-card" data-dm-select-job="${job.id}" role="button" tabindex="0">${fileGlyph(job, true)}<div><strong title="${escapeHtml(job.title)}">${escapeHtml(job.title)}</strong><small>${escapeHtml(statusLabel(job.status))} · ${escapeHtml(job.category)} · ${formatSpeed(job.speedBps)}</small>${progressMarkup(job, false)}</div><button data-dm-job-action="${job.status === 'running' ? 'pause' : 'resume'}" data-job-id="${job.id}">${dmIcon(job.status === 'running' ? 'pause' : 'play')}</button></article>`).join('');
  return `<section class="dm-media-overview"><div class="dm-media-overview-head"><div>${dmIcon('library', 30)}<span><strong>Biblioteca multimedia</strong><small>Miniaturas, pistas, playlists y conversiones locales.</small></span></div><button data-dm-video-search>${dmIcon('search')} Buscar vídeo</button></div><div class="dm-media-grid">${cards || `<div class="dm-section-empty">${dmIcon('video', 44)}<strong>No hay trabajos multimedia</strong><span>Busca un título o analiza un enlace de vídeo o playlist.</span></div>`}</div></section>`;
}

export function overviewCards(jobs) {
  const counts = statusCounts(jobs);
  const speed = jobs.filter((job) => job.status === 'running').reduce((total, job) => total + Number(job.speedBps || 0), 0);
  return `<section class="dm-overview-cards"><article>${dmIcon('download', 28)}<div><small>Activas</small><strong>${counts.running}</strong><span>${counts.queued} en cola</span></div></article><article>${dmIcon('check', 28)}<div><small>Completadas</small><strong>${counts.completed}</strong><span>${counts.failed} con error</span></div></article><article>${dmIcon('globe', 28)}<div><small>Velocidad total</small><strong>${formatSpeed(speed)}</strong><span>Motor local</span></div></article></section>`;
}

export function specialSectionPanel(section, context) {
  if (section === 'categories') return categoriesPanel(context.jobs || []);
  if (section === 'scheduler') return schedulerPanel(context.jobs || [], context.schedules || [], context.preferences?.selectedJobId);
  if (section === 'settings') return `${settingsPanel(context.preferences)}${infrastructureSettings(context)}`;
  if (section === 'news') return newsPanel(context);
  return '';
}
