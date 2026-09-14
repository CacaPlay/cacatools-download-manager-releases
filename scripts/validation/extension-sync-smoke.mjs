import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const listeners = new Map();
const register = (name) => ({ addListener(handler) { listeners.set(name, handler); } });
const storage = {};
const nativeMessages = [];
let reloadCalled = false;
const sidePanelCalls = [];
const sidePanelOptions = [];

globalThis.chrome = {
  runtime: {
    id: 'aonppfnabjnicjjeoofkfjofolfibggp',
    lastError: undefined,
    onConnect: register('runtime.onConnect'),
    onMessage: register('runtime.onMessage'),
    onInstalled: register('runtime.onInstalled'),
    onStartup: register('runtime.onStartup'),
    onUpdateAvailable: register('runtime.onUpdateAvailable'),
    getManifest: () => ({ version: '0.45.11' }),
    reload() { reloadCalled = true; },
    sendNativeMessage(_host, message, callback) {
      nativeMessages.push(message);
      // Keep the fixture aligned with the production protocol. The former
      // one-shape `{ok:true}` mock could never prove host identity or protocol
      // compatibility and only masked stale handshake assertions.
      const response = message.action === 'ping'
        ? { ok: true, host: 'lat.cacaplay.cacatools.downloadmanager', protocolVersion: 1, hostVersion: '0.45.4', desktopAppVersion: '0.95.0' }
        : message.action === 'capabilities'
          ? { ok: true, protocolVersion: 1, actions: ['ping', 'capabilities', 'enqueue', 'analyze', 'browser_download_capture', 'open_app', 'activate_app', 'open_job', 'open_player', 'list_jobs', 'job_action', 'set_job_options', 'get_status'], sourceTypes: ['video', 'audio', 'playlist', 'direct_file', 'generic_url'], spotifyEnabled: false }
          : message.action === 'get_status'
            ? { ok: true, appRunning: true, state: { appVersion: '0.95.0', updatedAt: Date.now(), jobs: [{ id: 12, status: 'completed' }, { id: 13, status: 'running' }], playlist_batches: [], appearance: { theme: 'dark', accent: '#5f73ff' } } }
            : { ok: true, status: 'accepted' };
      setTimeout(() => callback(response), 0);
    }
  },
  storage: {
    local: {
      async get(defaults) { return { ...defaults, ...storage }; },
      async set(values) { Object.assign(storage, values); },
      async remove(key) { delete storage[key]; }
    }
  },
  downloads: {
    onCreated: register('downloads.onCreated'),
    onChanged: register('downloads.onChanged'),
    onErased: register('downloads.onErased'),
    pause(_id, callback) { callback(); },
    resume(_id, callback) { callback(); },
    cancel(_id, callback) { callback(); }
  },
  scripting: { executeScript: async () => {} },
  tabs: {
    query: async () => [],
    get: async () => ({ url: 'https://example.com' }),
    onActivated: register('tabs.onActivated'),
    onUpdated: register('tabs.onUpdated'),
    sendMessage: async () => ({ detections: [] })
  },
  action: { onClicked: register('action.onClicked') },
  sidePanel: {
    async setPanelBehavior(options) { sidePanelCalls.push({ type: 'behavior', options }); },
    async setOptions(options) { sidePanelOptions.push(options); },
    async open(options) { sidePanelCalls.push({ type: 'open', options }); }
  }
};

const module = await import(`${pathToFileURL('extension/service-worker.js').href}?sync-smoke=${Date.now()}`);
assert.equal(typeof module.sendSelectionToApp, 'function');
await new Promise((resolve) => setTimeout(resolve, 0));
assert.ok(sidePanelCalls.some((entry) => entry.type === 'behavior' && entry.options?.openPanelOnActionClick === true), 'El panel no se configuró al cargar el service worker');
const actionListener = listeners.get('action.onClicked');
assert.equal(typeof actionListener, 'function');
actionListener({ id: 17, windowId: 9 });
await new Promise((resolve) => setTimeout(resolve, 0));
assert.ok(sidePanelOptions.some((entry) => entry.tabId === 17 && entry.enabled === true && entry.path === 'sidepanel.html'), 'No se habilitó el panel para la pestaña activa');
assert.ok(sidePanelCalls.some((entry) => entry.type === 'open' && entry.options?.windowId === 9), 'El clic del icono no abrió el panel lateral');

const result = await module.sendSelectionToApp([
  { id: 'one', type: 'video', title: 'Vídeo uno', mediaUrl: 'https://www.youtube.com/watch?v=one', selected: true },
  { id: 'two', type: 'video', title: 'Vídeo dos', mediaUrl: 'https://www.youtube.com/watch?v=two', selected: true }
], {
  preferredQuality: '1080p',
  preferredFormat: 'auto',
  windowMode: 'foreground',
  manualPlaylist: true,
  playlistTitle: 'Mi lista'
});
assert.equal(result.ok, true, JSON.stringify(result));
const enqueue = nativeMessages.find((message) => message.action === 'enqueue');
assert.ok(enqueue, 'No se envió la colección al host nativo');
assert.equal(enqueue.payload.windowMode, 'foreground');
assert.equal(enqueue.payload.manualPlaylist, true);
assert.equal(enqueue.payload.playlistTitle, 'Mi lista');
assert.equal(enqueue.payload.items.length, 2);
assert.equal(enqueue.payload.sourceType, 'playlist');
assert.equal(enqueue.payload.provider, 'youtube');
assert.ok(enqueue.payload.commandId && enqueue.payload.idempotencyKey, 'Faltan claves de idempotencia del envío');
assert.equal(nativeMessages.some((message) => message.action === 'open_app'), false, 'El envío no debe abrir la app por una llamada adicional');

const messageListener = listeners.get('runtime.onMessage');
assert.equal(typeof messageListener, 'function');

await new Promise((resolve, reject) => {
  const asyncResponse = messageListener({ type: 'OPEN_JOB', jobId: 12, mode: 'play' }, {}, (response) => {
    try { assert.equal(response.ok, true); resolve(); } catch (error) { reject(error); }
  });
  assert.equal(asyncResponse, true);
});
assert.equal(nativeMessages.filter((message) => message.action === 'open_player').length, 1, 'Reproducir debe usar open_player una sola vez');

await new Promise((resolve, reject) => {
  const asyncResponse = messageListener({ type: 'JOB_ACTION', jobId: 13, action: 'pause' }, {}, (response) => {
    try { assert.equal(response.ok, true); resolve(); } catch (error) { reject(error); }
  });
  assert.equal(asyncResponse, true);
});
assert.equal(nativeMessages.filter((message) => message.action === 'job_action').length, 1, 'La acción de job debe llegar una sola vez');

const updateListener = listeners.get('runtime.onUpdateAvailable');
assert.equal(typeof updateListener, 'function');
updateListener({ version: '0.45.11' });
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(storage.pendingExtensionUpdate.version, '0.45.11');

await new Promise((resolve, reject) => {
  const asyncResponse = messageListener({ type: 'GET_APP_STATUS' }, {}, (response) => {
    try {
      assert.equal(response.ok, true);
      assert.equal(response.result.appRunning, true);
      resolve();
    } catch (error) { reject(error); }
  });
  assert.equal(asyncResponse, true);
});

await new Promise((resolve, reject) => {
  const asyncResponse = messageListener({ type: 'APPLY_EXTENSION_UPDATE' }, {}, (response) => {
    try { assert.equal(response.applying, true); resolve(); } catch (error) { reject(error); }
  });
  assert.equal(asyncResponse, true);
});
await new Promise((resolve) => setTimeout(resolve, 70));
assert.equal(reloadCalled, true);

console.log('OK: apertura del panel, sincronización, modo de ventana, playlists manuales y actualización real de Chrome validados.');
