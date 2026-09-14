import { cacaToolsNative, nativeHandshake, isSpotifyUrl, SPOTIFY_DIRECT_CAPTURE_MESSAGE } from './sdk/cacatools-native-client.js';
import { canUseJobAction } from './sdk/compatibility.js';
import { prepareSelection } from './sdk/selection.js';
import { createOperationJournal, selectionFingerprint } from './sdk/operation-journal.js';
import {contextSelection,youtubeSelection} from './sdk/panel-features.js';
import { DEFAULT_ACCENT, iconVariantForColor } from './sdk/appearance.js';

let lastActionIconVariant = '';
async function syncActionIcon(appearance = {}) {
  const variant = iconVariantForColor(appearance.accent || DEFAULT_ACCENT);
  if (variant === lastActionIconVariant) return;
  const path = Object.fromEntries([16, 32, 48, 128].map((size) => [size, `icons/brand/clear-download-manager-${variant}-${size}.png`]));
  try {
    await chrome.action?.setIcon?.({ path });
    await chrome.action?.setTitle?.({ title: 'Abrir Clear Download Manager' });
    lastActionIconVariant = variant;
  } catch {}
}
async function initializeActionIcon() {
  try {
    const saved = await chrome.storage.local.get({ lastAppState: null });
    await syncActionIcon(saved?.lastAppState?.appearance || { accent: DEFAULT_ACCENT });
  } catch {
    await syncActionIcon({ accent: DEFAULT_ACCENT });
  }
}

function configureContextMenu() {
  if (!chrome.contextMenus) return;
  chrome.contextMenus.removeAll(()=>{
    if(chrome.runtime.lastError)return;
    chrome.contextMenus.create({id:'send-to-cdm',title:'Enviar a Clear Download Manager',contexts:['page','link','image','video','audio'],documentUrlPatterns:['http://*/*','https://*/*']},()=>{ void chrome.runtime.lastError; });
  });
}
if (chrome.contextMenus?.onClicked) chrome.contextMenus.onClicked.addListener((info,tab)=>{
  if(info.menuItemId!=='send-to-cdm')return;
  void (async()=>{
    const selection=contextSelection(info,tab);
    const result=await sendSelectionToApp([selection.item],{windowMode:selection.windowMode,preferredQuality:'auto',preferredFormat:'auto'});
    if(result?.ok!==true)throw Error(result?.error||'No se confirmó el envío. Revisa Clear Download Manager.');
    await chrome.storage.local.set({lastContextSend:{ok:true,at:Date.now()}});
    await chrome.action?.setBadgeText?.({text:''});
  })().catch(async error=>{
    const message=String(error.message||error);
    await chrome.storage.local.set({lastContextSend:{ok:false,error:message,at:Date.now()}});
    publish({type:'CONTEXT_SEND_ERROR',message});
    await chrome.action?.setBadgeText?.({text:'!'});
    await chrome.action?.setTitle?.({title:`Enviar a Clear Download Manager: ${message}`});
  });
});

const MAX_DETECTIONS = 100;
const APP_STATE_POLL_MS = 1500;
const DETECTION_RESPONSE_TIMEOUT_MS = 4500;
const EXT_DIAGNOSTICS = false;
const diagnostic = (...args) => { if (EXT_DIAGNOSTICS) console.warn('[CDM EXT DIAG]', ...args); };
const CAPTURE_MODE_KEY = 'browserCaptureMode';
const WINDOW_MODE_KEY = 'extensionWindowMode';
const UPDATE_KEY = 'pendingExtensionUpdate';
// New installations capture supported browser downloads automatically. A
// stored user preference still wins because storage.get preserves it.
const DEFAULT_CAPTURE_MODE = 'automatic';
const DEFAULT_WINDOW_MODE = 'background';
const AUTOMATIC_DETECTION_DOMAINS = ['youtube.com', 'spotify.com', 'pinterest.com', 'tiktok.com'];
const panelPorts = new Set();
const tabCache = new Map();
const processedDownloadKeys = new Set();
const activeCaptures = new Map();
let activeTabId = null;
let appStatePollTimer = null;
const operationJournal = createOperationJournal(chrome.storage.local);

async function configureSidePanel() {
  if (!chrome.sidePanel?.setPanelBehavior) return false;
  try {
    await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
    return true;
  } catch {
    return false;
  }
}

async function openSidePanelForTab(tab = {}) {
  if (!chrome.sidePanel?.open) return false;
  await configureSidePanel();
  const tabId = Number.isInteger(tab?.id) ? tab.id : null;
  const windowId = Number.isInteger(tab?.windowId) ? tab.windowId : null;
  if (tabId !== null && chrome.sidePanel.setOptions) {
    await chrome.sidePanel.setOptions({ tabId, path: 'sidepanel.html', enabled: true }).catch(() => {});
  }
  try {
    if (windowId !== null) await chrome.sidePanel.open({ windowId });
    else if (tabId !== null) await chrome.sidePanel.open({ tabId });
    else return false;
    return true;
  } catch {
    if (tabId === null) return false;
    try {
      await chrome.sidePanel.open({ tabId });
      return true;
    } catch {
      return false;
    }
  }
}

void configureSidePanel();

function safePageUrl(value) {
  try {
    const url = new URL(String(value || '').trim());
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

function providerForItem(item = {}) {
  const declared = String(item.provider || item.platform || '').trim().toLowerCase();
  if (declared) return declared.slice(0, 64);
  try {
    const host = new URL(item.canonicalUrl || item.mediaUrl || item.pageUrl || '').hostname.toLowerCase().replace(/^www\./, '');
    if (host === 'youtu.be' || host === 'youtube.com' || host.endsWith('.youtube.com')) return 'youtube';
    if (host === 'tiktok.com' || host.endsWith('.tiktok.com')) return 'tiktok';
    if (host === 'spotify.com' || host.endsWith('.spotify.com') || host === 'scdn.co' || host.endsWith('.scdn.co')) return 'spotify';
    if (host === 'pinterest.com' || host.endsWith('.pinterest.com')) return 'pinterest';
  } catch {}
  return 'generic';
}

function isAutomaticDetectionUrl(value) {
  try {
    const url = new URL(String(value || '').trim());
    if (url.protocol !== 'https:') return false;
    const hostname = url.hostname.toLowerCase().replace(/^www\./, '');
    return hostname === 'youtu.be' || AUTOMATIC_DETECTION_DOMAINS.some((domain) => hostname === domain || hostname.endsWith(`.${domain}`));
  } catch {
    return false;
  }
}

async function collectAutomatically(tabId) {
  if (!Number.isInteger(tabId)) return [];
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  if (!isAutomaticDetectionUrl(tab?.url)) return [];
  return collectFromTab(tabId);
}

function publish(message) {
  for (const port of panelPorts) {
    try {
      port.postMessage(message);
    } catch {
      panelPorts.delete(port);
    }
  }
}

function captureModeValue(value) {
  return ['automatic', 'ask', 'disabled'].includes(value) ? value : DEFAULT_CAPTURE_MODE;
}

function windowModeValue(value) {
  return ['background', 'foreground'].includes(value) ? value : DEFAULT_WINDOW_MODE;
}

async function captureMode() {
  try {
    const value = await chrome.storage.local.get({ [CAPTURE_MODE_KEY]: DEFAULT_CAPTURE_MODE });
    return captureModeValue(value[CAPTURE_MODE_KEY]);
  } catch {
    return DEFAULT_CAPTURE_MODE;
  }
}

async function windowMode() {
  try {
    const value = await chrome.storage.local.get({ [WINDOW_MODE_KEY]: DEFAULT_WINDOW_MODE });
    return windowModeValue(value[WINDOW_MODE_KEY]);
  } catch {
    return DEFAULT_WINDOW_MODE;
  }
}

function downloadApiCall(method, ...args) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      const error = chrome.runtime.lastError;
      if (error) reject(new Error(error.message));
      else callback(value);
    };
    try {
      const result = chrome.downloads[method](...args, (value) => finish(resolve, value));
      if (result && typeof result.then === 'function') {
        result.then((value) => finish(resolve, value), (error) => finish(reject, error));
      }
    } catch (error) {
      finish(reject, error);
    }
  });
}

function delay(milliseconds) { return new Promise((resolve) => setTimeout(resolve, milliseconds)); }
function withTimeout(promise, timeoutMs, message) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), timeoutMs);
  });
  return Promise.race([Promise.resolve(promise), timeout]).finally(() => clearTimeout(timer));
}
function youtubeVideoId(value) {
  try {
    const url = new URL(String(value || ''));
    const host = url.hostname.replace(/^www\./, '').toLowerCase();
    if (host === 'youtu.be') return url.pathname.split('/').filter(Boolean)[0] || '';
    return url.searchParams.get('v') || url.pathname.match(/^\/(?:shorts|embed|live)\/([\w-]{6,})/i)?.[1] || '';
  } catch { return ''; }
}
function youtubeUrlFallback(value) {
  const pageUrl = safePageUrl(value);
  if (!pageUrl) return [];
  try {
    const parsed = new URL(pageUrl);
    const host = parsed.hostname.toLowerCase().replace(/^www\./, '');
    if (!['youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtu.be'].includes(host)) return [];
    const id = youtubeVideoId(pageUrl);
    if (!id) return [];
    const canonicalUrl = `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
    return [{
      id: `youtube:url:${id}`,
      type: 'video',
      mediaKind: 'video',
      pageUrl,
      mediaUrl: canonicalUrl,
      canonicalUrl,
      title: 'Vídeo de YouTube',
      author: '',
      duration: '',
      thumbnail: '',
      thumbnailCandidates: [],
      platform: host,
      sourceKind: 'provider_page',
      provider: 'youtube',
      confidence: 70,
      requiresDesktopAnalysis: true,
      urlFallback: true
    }];
  } catch { return []; }
}
async function resolveLinkMetadata(value) {
  const url = safePageUrl(value);
  if (!url) return { ok: false, error: 'El enlace no es válido.' };
  const videoId = youtubeVideoId(url);
  if (videoId) {
    const fallback = { title: `Vídeo de YouTube · ${videoId}`, author: 'YouTube', thumbnail: `https://i.ytimg.com/vi/${encodeURIComponent(videoId)}/mqdefault.jpg` };
    try {
      const endpoint = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
      const response = await fetch(endpoint, { method: 'GET', credentials: 'omit', redirect: 'follow', cache: 'no-store' });
      if (!response.ok) return { ok: true, metadata: fallback };
      const contentType = String(response.headers.get('content-type') || '');
      if (!contentType.includes('application/json')) return { ok: true, metadata: fallback };
      const data = await response.json();
      return { ok: true, metadata: { title: String(data?.title || fallback.title).slice(0, 220), author: String(data?.author_name || fallback.author).slice(0, 120), thumbnail: safePageUrl(data?.thumbnail_url) || fallback.thumbnail } };
    } catch { return { ok: true, metadata: fallback }; }
  }
  try {
    const parsed = new URL(url);
    const segment = decodeURIComponent(parsed.pathname.split('/').filter(Boolean).pop() || '').replace(/[-_]+/g, ' ').trim();
    return { ok: true, metadata: { title: segment || parsed.hostname.replace(/^www\./, ''), author: parsed.hostname.replace(/^www\./, ''), thumbnail: '' } };
  } catch { return { ok: false, error: 'No se pudieron obtener los metadatos.' }; }
}

function downloadUrls(item) {
  return [safePageUrl(item?.finalUrl), safePageUrl(item?.url)].filter(Boolean);
}

function isBrowserUpdate(url, filename) {
  const haystack = `${url} ${filename}`.toLowerCase();
  return /clients2\.google\.com\/service\/update2|update\.googleapis\.com|edge\.microsoft\.com\/.*update|\.crx(?:$|[?#])|browser[-_ ]?update/.test(haystack);
}

function isSmallInternalResource(item) {
  const mime = String(item?.mime || '').toLowerCase();
  const filename = String(item?.filename || '').toLowerCase();
  const small = Number(item?.fileSize || item?.totalBytes || 0);
  const internalMime = /javascript|ecmascript|css|font|woff|woff2|x-icon/.test(mime);
  const internalExtension = /\.(?:js|mjs|css|map|woff2?|ttf|ico)$/i.test(filename);
  return small > 0 && small < 8192 && (internalMime || internalExtension);
}

function captureDownloadKey(item) {
  return [item?.id, item?.url, item?.finalUrl, item?.filename, item?.startTime]
    .map((value) => String(value || ''))
    .join('|');
}

function shouldIgnoreDownload(item) {
  if (!item || item.state !== 'in_progress') return true;
  if (item.incognito || item.paused) return true;
  if (Number.isInteger(item.id) && activeCaptures.has(item.id)) return true;
  if (item.byExtensionId && item.byExtensionId === chrome.runtime.id) return true;
  if (String(item.byExtensionName || '').toLowerCase().includes('cacatools')) return true;
  const urls = downloadUrls(item);
  if (!urls.length || urls.some((url) => isBrowserUpdate(url, item.filename))) return true;
  if (isSmallInternalResource(item)) return true;
  const mime = String(item.mime || '').toLowerCase();
  if (mime === 'application/x-chrome-extension' || mime === 'application/x-msdownload') {
    return urls.some((url) => isBrowserUpdate(url, item.filename));
  }
  return false;
}

function downloadFilenameLooksFinal(value) {
  const basename = String(value || '').split(/[\\/]/).pop().trim();
  if (!basename || /\.(?:crdownload|part|tmp)$/i.test(basename) || /^unconfirmed(?:[ _-]|$)/i.test(basename)) return false;
  return /\.[a-z0-9]{1,12}$/i.test(basename);
}

async function refreshDownloadMetadata(item) {
  if (!Number.isInteger(item?.id)) return item;
  let best = item;
  const waits = [0, 70, 130, 210];
  for (const wait of waits) {
    if (wait) await delay(wait);
    try {
      const matches = await downloadApiCall('search', { id: item.id });
      const fresh = Array.isArray(matches) ? matches[0] : null;
      if (!fresh) continue;
      // chrome.downloads can populate filename/finalUrl/mime after onCreated,
      // and on some servers it takes more than one event loop after pausing.
      // Poll briefly (<=410 ms) and keep the best non-empty metadata gathered.
      best = {
        ...best,
        ...fresh,
        url: safePageUrl(fresh.url) || safePageUrl(best.url) || safePageUrl(item.url),
        finalUrl: safePageUrl(fresh.finalUrl) || safePageUrl(best.finalUrl) || safePageUrl(item.finalUrl),
        filename: String(fresh.filename || best.filename || item.filename || ''),
        mime: String(fresh.mime || best.mime || item.mime || '')
      };
      const usefulFilename = downloadFilenameLooksFinal(best.filename);
      const usefulMime = Boolean(String(best.mime || '').trim());
      const usefulFinalUrl = Boolean(safePageUrl(best.finalUrl));
      if (usefulFilename && (usefulMime || usefulFinalUrl)) break;
    } catch {
      // Keep the last good snapshot and try the next short retry. Browser
      // download capture must always fall back to the native/browser download.
    }
  }
  return best;
}

function capturePayload(item, requestedWindowMode) {
  const urls = downloadUrls(item);
  return {
    type: 'browser_download_capture',
    downloadId: item.id,
    url: urls[1] || urls[0] || '',
    finalUrl: urls[0] || '',
    referrer: safePageUrl(item.referrer),
    filename: String(item.filename || '').slice(0, 1024),
    mime: String(item.mime || '').slice(0, 160),
    totalBytes: Number.isFinite(item.totalBytes) ? item.totalBytes : null,
    fileSize: Number.isFinite(item.fileSize) ? item.fileSize : null,
    state: item.state,
    danger: item.danger,
    incognito: Boolean(item.incognito),
    startTime: item.startTime || '',
    byExtensionId: item.byExtensionId || '',
    byExtensionName: item.byExtensionName || '',
    windowMode: windowModeValue(requestedWindowMode)
  };
}

async function captureDownload(item) {
  if (shouldIgnoreDownload(item)) return;
  const key = captureDownloadKey(item);
  if (processedDownloadKeys.has(key)) return;
  processedDownloadKeys.add(key);
  const mode = await captureMode();
  if (mode === 'disabled') return;
  const requestedWindowMode = await windowMode();
  let capture = capturePayload(item, requestedWindowMode);
  if (mode === 'ask') {
    publish({ type: 'CAPTURE_AVAILABLE', item: capture });
    return;
  }
  if (isSpotifyUrl(capture.finalUrl || capture.url)) {
    publish({
      type: 'CAPTURE_FALLBACK',
      item: capture,
      response: { ok: false, status: 'spotify_direct_capture_ignored', error: SPOTIFY_DIRECT_CAPTURE_MESSAGE }
    });
    return;
  }

  // Check compatibility while the browser download is still running.
  try {
    const bridge = await nativeHandshake();
    if (!bridge.actions.includes('browser_download_capture')) throw new Error('El puente instalado no admite transferir descargas.');
  } catch (error) {
    publish({type:'CAPTURE_FALLBACK',item:capture,response:{ok:false,error:String(error.message || error)}});
    return;
  }

  activeCaptures.set(item.id, key);
  let paused = false;
  try {
    await downloadApiCall('pause', item.id);
    paused = true;
    const refreshedItem = await refreshDownloadMetadata(item);
    capture = capturePayload(refreshedItem, requestedWindowMode);
    publish({ type: 'CAPTURE_PENDING', item: capture });
    // A lost response is not a rejection. Resuming here could create two transfers.
    await chrome.storage.local.set({pendingCaptureReview: {downloadId:item.id, at:Date.now()}});
    const fingerprint = await selectionFingerprint({downloadId:item.id,startTime:item.startTime,url:capture.finalUrl});
    const response = await operationJournal.run(`capture-${fingerprint}`,fingerprint,()=>cacaToolsNative.captureDownload(capture));
    const status = String(response?.status || '').toLowerCase();
    if (response?.uncertain || status === 'temporary_failure') {
      publish({type:'CAPTURE_FALLBACK',response:{ok:false,error:'Transferencia sin confirmar. La descarga del navegador queda pausada. Revisa Clear Download Manager antes de reanudarla manualmente en el navegador.'}});
      return;
    }
    if (response?.ok === true && status === 'accepted') {
      try { await downloadApiCall('cancel', item.id); }
      catch {
        publish({type:'CAPTURE_FALLBACK',item:capture,response:{ok:false,error:'Clear Download Manager aceptó la descarga, pero no se pudo cancelar la copia del navegador. Revisa ambas descargas.'}});
        return;
      }
      publish({ type: 'CAPTURE_ACCEPTED', item: capture, response });
      await chrome.storage.local.remove('pendingCaptureReview');
      void refreshAppStatus();
      return;
    }
    if (paused) await downloadApiCall('resume', item.id);
    await chrome.storage.local.remove('pendingCaptureReview');
    publish({ type: 'CAPTURE_FALLBACK', item: capture, response });
  } catch (error) {
    // Do not guess whether the app accepted a request if communication failed.
    publish({
      type: 'CAPTURE_FALLBACK',
      item: capture,
      response: { status: 'temporary_failure', error: paused ? 'La captura no se confirmó. Revisa Clear Download Manager y la descarga pausada del navegador antes de reanudar.' : String(error) }
    });
  } finally {
    activeCaptures.delete(item.id);
  }
}

function detectionQuality(items) {
  return (Array.isArray(items) ? items : []).reduce((score, item) => score + 10 + (item?.title && !/^(youtube|contenido multimedia)$/i.test(String(item.title).trim()) ? 7 : 0) + (item?.thumbnail ? 5 : 0) + (item?.author ? 3 : 0) + (item?.duration ? 2 : 0), 0);
}

function extensionFilenameMetadata(item = {}, preferences = {}) {
  const preferredFormat = String(preferences?.preferredFormat || 'auto').toLowerCase();
  const preferredQuality = String(preferences?.preferredQuality || 'auto').toLowerCase();
  const expectedExtension = preferredFormat === 'mp3'
    ? 'mp3'
    : preferredFormat === 'm4a'
      ? 'm4a'
      : ['1080p', '720p'].includes(preferredQuality)
        ? 'mp4'
        : '';
  const title = String(preferences?.filename || item?.title || '').trim().slice(0, 220);
  const filename = title && expectedExtension && !new RegExp(`\\.${expectedExtension}$`, 'i').test(title)
    ? `${title}.${expectedExtension}`
    : title;
  const mime = String(preferences?.mime || (
    preferredFormat === 'mp3' ? 'audio/mpeg'
      : preferredFormat === 'm4a' ? 'audio/mp4'
        : ['1080p', '720p'].includes(preferredQuality) ? 'video/mp4' : ''
  )).slice(0, 160);
  return { filename, mime, expectedExtension };
}
async function collectFromTab(tabId) {
  if (!Number.isInteger(tabId)) return [];
  const originalTab = await chrome.tabs.get(tabId).catch(()=>null);
  if ((await activeTab())?.id !== tabId) return [];
  const originalUrl = safePageUrl(originalTab?.url);
  activeTabId = tabId;
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ['content/detector.js'] }).catch((error) => {
      if (!String(error?.message || '').includes('already')) throw error;
    });
    let bestResponse = null;
    for (const wait of [0, 320, 780]) {
      if (wait) await delay(wait);
      const response = await withTimeout(
        chrome.tabs.sendMessage(tabId, { type: 'CACATOOLS_COLLECT' }),
        DETECTION_RESPONSE_TIMEOUT_MS,
        `El detector no respondió en ${DETECTION_RESPONSE_TIMEOUT_MS} ms.`
      );
      if (!bestResponse || detectionQuality(response?.detections) > detectionQuality(bestResponse?.detections)) bestResponse = response;
      const items = Array.isArray(bestResponse?.detections) ? bestResponse.detections : [];
      if (items.length && detectionQuality(items) >= items.length * 19) break;
    }
    let detections = Array.isArray(bestResponse?.detections)
      ? bestResponse.detections.filter((item) => item?.type !== 'playlist').slice(0, MAX_DETECTIONS)
      : [];
    if (!detections.length) detections = youtubeUrlFallback(originalUrl);
    const status = String(bestResponse?.status || (detections.length ? 'media_found' : 'no_media'));
    const tab = await chrome.tabs.get(tabId);
    const pageUrl = safePageUrl(tab?.url);
    if ((await activeTab())?.id !== tabId || pageUrl !== originalUrl) return [];
    const normalized = detections
      .map((item) => ({ ...item, pageUrl: safePageUrl(item.pageUrl) || pageUrl }))
      .filter((item) => item.pageUrl && safePageUrl(item.mediaUrl || item.canonicalUrl || item.pageUrl));
    tabCache.set(`${tabId}:${pageUrl}`, normalized);
    publish({ type: 'DETECTIONS', tabId, pageUrl, status, detections: normalized, updatedAt: Date.now() });
    return normalized;
  } catch (error) {
    if ((await activeTab())?.id !== tabId) return [];
    const message = String(error?.message || error || 'No se pudo analizar la pestaña');
    diagnostic('collectFromTab failed:', { tabId, message });
    publish({ type: 'DETECTION_ERROR', tabId, message: message.includes('Cannot access') ? 'Esta página no permite análisis desde extensiones.' : message });
    return [];
  }
}

async function activeTab() {
  const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tabs[0] || null;
}

async function refreshAppStatus() {
  try {
    const bridge = await nativeHandshake();
    const result = { ...await cacaToolsNative.status(), bridge };
    await syncActionIcon(result?.state?.appearance || {});
    if (result?.state) await chrome.storage.local.set({ lastAppState: result.state });
    publish({ type: 'APP_STATE', result });
    return { ok: result?.ok === true, result };
  } catch (error) {
    const response = { ok: false, error: String(error) };
    publish({ type: 'APP_STATE', result: { ok: false, appRunning: false } });
    return response;
  }
}

function stopAppStatePollingIfIdle() {
  if (panelPorts.size || !appStatePollTimer) return;
  clearInterval(appStatePollTimer);
  appStatePollTimer = null;
}

function startAppStatePolling() {
  if (!appStatePollTimer) {
    appStatePollTimer = setInterval(() => {
      if (panelPorts.size) void refreshAppStatus();
      else stopAppStatePollingIfIdle();
    }, APP_STATE_POLL_MS);
  }
  void refreshAppStatus();
}

async function publishPendingUpdate() {
  const value = await chrome.storage.local.get({ [UPDATE_KEY]: null });
  if (value[UPDATE_KEY]) publish({ type: 'EXTENSION_UPDATE_AVAILABLE', update: value[UPDATE_KEY] });
}

chrome.downloads.onCreated.addListener((item) => { void captureDownload(item); });
chrome.downloads.onChanged.addListener((delta) => {
  if (delta.state?.current && ['complete', 'interrupted'].includes(delta.state.current)) {
    activeCaptures.delete(delta.id);
  }
});
chrome.downloads.onErased.addListener((downloadId) => activeCaptures.delete(downloadId));

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== 'cacatools-sidepanel') return;
  panelPorts.add(port);
  port.onDisconnect.addListener(() => {
    panelPorts.delete(port);
    stopAppStatePollingIfIdle();
  });
  startAppStatePolling();
  void publishPendingUpdate();
  void chrome.storage.local.get({pendingCaptureReview:null}).then(value=>{
    if (value.pendingCaptureReview) publish({type:'CAPTURE_FALLBACK',response:{error:'Hay una captura pendiente de revisión. Comprueba Clear Download Manager y las descargas del navegador antes de reanudar o reenviar.'}});
  });
  void activeTab().then((tab) => tab?.id && collectFromTab(tab.id));
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const ownPanel = sender.id === chrome.runtime.id && String(sender.url||'').split(/[?#]/)[0] === chrome.runtime.getURL?.('sidepanel.html');
  if (sender.tab && !ownPanel && message?.type !== 'CONTENT_DETECTIONS') {
    sendResponse({ok:false,error:'Acción disponible únicamente desde el panel de la extensión.'});
    return false;
  }
  if (message?.type === 'ANALYZE_ACTIVE') {
    void activeTab()
      .then((tab) => collectFromTab(tab?.id))
      .then((detections) => sendResponse({ ok: true, detections }))
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'CONTENT_DETECTIONS') {
    const tabId = sender.tab?.id;
    if (!Number.isInteger(tabId)) return false;
    void activeTab().then(tab => {
      if (tab?.id !== tabId || safePageUrl(tab.url) !== safePageUrl(message.pageUrl)) return;
    let detections = (message.detections || []).filter((item) => item?.type !== 'playlist').slice(0, MAX_DETECTIONS);
    if (!detections.length) detections = youtubeUrlFallback(message.pageUrl);
    publish({
      type: 'DETECTIONS',
      tabId,
      pageUrl: safePageUrl(message.pageUrl),
      status: message.status || (detections.length ? 'media_found' : 'no_media'),
      detections,
      updatedAt: Date.now()
    });
    }).catch(() => {});
  }
  if (message?.type === 'RESOLVE_LINK_METADATA') {
    void resolveLinkMetadata(message.url).then(sendResponse).catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'GET_CAPTURE_MODE') {
    void captureMode().then((mode) => sendResponse({ ok: true, mode }));
    return true;
  }
  if (message?.type === 'GET_APP_STATUS') {
    void refreshAppStatus().then(sendResponse);
    return true;
  }
  if (message?.type === 'GET_HOST_STATUS') {
    void cacaToolsNative.ping()
      .then((response) => sendResponse({ ok: response?.ok === true, error:response?.error, response }))
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'OPEN_APP') {
    void cacaToolsNative.open()
      .then((response) => sendResponse({ ok: response?.ok === true, error:response?.error, response }))
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'OPEN_JOB') {
    const operation = dispatchJobAction({...message,action:message.mode === 'play' ? 'play' : 'open'});
    void operation
      .then((response) => sendResponse({ ok: response?.ok === true, error:response?.error, response }))
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'JOB_ACTION') {
    void dispatchJobAction(message)
      .then((response) => sendResponse({ ok: response?.ok === true, error:response?.error, response }))
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'SET_JOB_OPTIONS') {
    sendResponse({ok:false,error:'Las opciones se eligen antes de iniciar la descarga, desde Clear Download Manager.'});
    return false;
  }
  if (message?.type === 'SET_CAPTURE_MODE') {
    const mode = captureModeValue(message.mode);
    void chrome.storage.local.set({ [CAPTURE_MODE_KEY]: mode })
      .then(() => {
        publish({ type: 'CAPTURE_MODE', mode });
        sendResponse({ ok: true, mode });
      })
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'SEND_TO_APP') {
    void sendSelectionToApp(message.items, message.preferences)
      .then(sendResponse)
      .catch((error) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  if (message?.type === 'APPLY_EXTENSION_UPDATE') {
    sendResponse({ ok: true, applying: true });
    setTimeout(() => chrome.runtime.reload(), 50);
    return true;
  }
  return false;
});

chrome.tabs.onActivated.addListener(({ tabId }) => {
  activeTabId = tabId;
  publish({type:'DETECTIONS',tabId,status:'analyzing',detections:[]});
  if (panelPorts.size) void collectFromTab(tabId);
});
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (panelPorts.size && (changeInfo.status === 'complete' || changeInfo.url)) {
    void collectAutomatically(tabId);
  }
});

chrome.runtime.onInstalled.addListener(async (details) => {
  configureContextMenu();
  await configureSidePanel();
  await initializeActionIcon();
  const existing = await chrome.storage.local.get({
    [CAPTURE_MODE_KEY]: DEFAULT_CAPTURE_MODE,
    [WINDOW_MODE_KEY]: DEFAULT_WINDOW_MODE
  });
  if (details?.reason === 'update' && chrome.storage.local.remove) {
    await chrome.storage.local.remove(UPDATE_KEY);
  }
  await chrome.storage.local.set({
    ...existing,
    extensionVersion: chrome.runtime.getManifest().version
  });
});
chrome.runtime.onStartup.addListener(() => {
  configureContextMenu();
  void configureSidePanel();
  void initializeActionIcon();
});

if (chrome.action?.onClicked?.addListener) {
  chrome.action.onClicked.addListener((tab) => {
    void openSidePanelForTab(tab);
  });
}

if (chrome.runtime.onUpdateAvailable?.addListener) {
  chrome.runtime.onUpdateAvailable.addListener((details) => {
    const update = { version: String(details?.version || 'nueva'), detectedAt: Date.now() };
    void chrome.storage.local.set({ [UPDATE_KEY]: update });
    publish({ type: 'EXTENSION_UPDATE_AVAILABLE', update });
  });
}

async function ensurePlayerAppReady() {
  const current = await cacaToolsNative.status();
  if (current?.appRunning === true) return;
  const opened = await cacaToolsNative.open();
  if (opened?.ok !== true) throw new Error(opened?.error || 'No se pudo abrir Clear Download Manager para reproducir.');
  for (let attempt = 0; attempt < 10; attempt += 1) {
    await delay(200);
    const status = await cacaToolsNative.status();
    if (status?.appRunning === true) return;
  }
  throw new Error('Clear Download Manager todavía está iniciando. Vuelve a pulsar Reproducir cuando la app esté disponible.');
}

export async function dispatchJobAction(message) {
  if (message.action === 'play') await ensurePlayerAppReady();
  const bridge = await nativeHandshake({force:true});
  const result = await cacaToolsNative.status();
  const job = result?.state?.jobs?.find(j=>Number(j.id)===Number(message.jobId));
  const fresh = result?.appRunning === true && Date.now()-Number(result?.state?.updatedAt||0) < 15000;
  if (!canUseJobAction(bridge,message.action,job,fresh)) throw new Error('La acción no está disponible con este puente o estado. Abre Clear Download Manager para realizarla.');
  if (message.action === 'play') return cacaToolsNative.openPlayer(message.jobId);
  if (message.action === 'open') return cacaToolsNative.openJob(message.jobId);
  return cacaToolsNative.jobAction(message.jobId,message.action,{confirmed:message.confirmed === true});
}

export async function sendSelectionToApp(items, preferences = {}) {
  const normalizedItems=(Array.isArray(items)?items:[]).map(item=>{
    if(item?.type!=='playlist')return item;
    const source=item.mediaUrl||item.canonicalUrl||item.url||item.pageUrl;
    const selection=youtubeSelection(source);
    return selection?{...item,mediaUrl:selection.url,canonicalUrl:selection.url}:item;
  });
  const safeItems = prepareSelection(normalizedItems).map(item=>({...item,provider:providerForItem(item)}));
  if (!safeItems.length) return { ok: false, error: 'No hay elementos válidos seleccionados.' };
  const bridge = await nativeHandshake();
  if (!bridge.actions.includes('enqueue')) return {ok:false,error:'El puente instalado no admite nuevos envíos.'};
  if (!bridge.spotifyEnabled && safeItems.some(i=>isSpotifyUrl(i.mediaUrl))) return {ok:false,status:'spotify_disabled',error:'Spotify está desactivado en esta app.'};
  const explicitPlaylist = safeItems.filter(i=>i.type === 'playlist');
  if (safeItems.length > 1 && explicitPlaylist.length) return {ok:false,error:'Envía la playlist completa por separado para evitar duplicar el vídeo actual.'};
  if (safeItems.length > 1 && safeItems.some(i=>['direct_file','generic_url'].includes(i.type))) return {ok:false,error:'Envía los archivos y enlaces sin clasificar uno por uno. Esta app agrupa los lotes como playlist multimedia.'};
  const source = safeItems[0].mediaUrl || safeItems[0].canonicalUrl || safeItems[0].pageUrl;
  const requestedWindowMode = windowModeValue(preferences?.windowMode || await windowMode());
  const extensionFilename = extensionFilenameMetadata(safeItems[0], preferences);
  const metadata = {
    items: safeItems,
    source: 'chrome-side-panel',
    sourceType: safeItems.length > 1 || safeItems.some((item) => item.type === 'playlist') ? 'playlist' : (safeItems[0].type || 'generic_url'),
    provider: providerForItem(safeItems[0]),
    canonicalUrl: safeItems[0].canonicalUrl,
    mediaUrl: safeItems[0].mediaUrl,
    pageUrl: safeItems[0].pageUrl,
    commandId: preferences.operationId || `send-${crypto.randomUUID()}`,
    preferredQuality: String(preferences?.preferredQuality || 'auto').slice(0, 32),
    preferredFormat: String(preferences?.preferredFormat || 'auto').slice(0, 32),
    filename: extensionFilename.filename,
    mime: extensionFilename.mime,
    expectedExtension: extensionFilename.expectedExtension,
    windowMode: requestedWindowMode,
    manualPlaylist: Boolean(preferences?.manualPlaylist && safeItems.every(i=>['video','audio'].includes(i.type))),
    playlistTitle: safeItems.every(i=>['video','audio','playlist'].includes(i.type)) ? String(preferences?.playlistTitle || '').trim().slice(0, 120) : ''
  };
  metadata.idempotencyKey = metadata.commandId;
  const fingerprint = await selectionFingerprint({items:safeItems.map(i=>[i.type,i.mediaUrl]),format:metadata.preferredFormat,quality:metadata.preferredQuality,windowMode:metadata.windowMode,manualPlaylist:metadata.manualPlaylist,playlistTitle:metadata.playlistTitle,filename:metadata.filename});
  const result = await operationJournal.run(metadata.commandId,fingerprint,()=>cacaToolsNative.enqueue(source,metadata),{allowUncertainRetry:preferences.allowUncertainRetry === true});
  if (result?.ok === true) void refreshAppStatus();
  return result;
}
