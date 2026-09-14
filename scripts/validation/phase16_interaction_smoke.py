#!/usr/bin/env python3
"""Browser interaction gate for the Phase16 download manager.

The test runs the real renderer and event bindings with a deterministic native-command
mock. It verifies that critical controls are connected, not merely visible.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from phase16_hashing import source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "tests" / "phase16-interaction-smoke.json"
SCREENSHOT = ROOT / "docs" / "screenshots" / "phase16" / "functional-torrent-recovery.png"
MODULES = (
    "app-ui/download-manager/core/constants.js",
    "app-ui/download-manager/core/model.js",
    "app-ui/download-manager/view/icons.js",
    "app-ui/download-manager/view/shared.js",
    "app-ui/download-manager/view/sections.js",
    "app-ui/download-manager/view/unified.js",
    "app-ui/download-manager/view/zen-sidebar.js",
    "app-ui/download-manager/view/dialogs.js",
    "app-ui/download-manager/index.js",
)


def browser_bundle() -> str:
    parts: list[str] = []
    for relative in MODULES:
        source = (ROOT / relative).read_text(encoding="utf-8")
        source = re.sub(r"^import\s+[^;]+;\s*$", "", source, flags=re.MULTILINE)
        source = re.sub(r"\bexport\s+(?=(?:const|let|var|function|class)\b)", "", source)
        source = re.sub(r"\bexport\s*\{[^}]*\};?", "", source, flags=re.DOTALL)
        parts.append(f"\n/* {relative} */\n{source}\n")
    return "".join(parts)


def browser_executable() -> str | None:
    candidates = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return shutil.which("chromium") or shutil.which("google-chrome")


BOOTSTRAP = r"""
const snapshot = {
  jobs: [
    { id: 1, title: 'ubuntu-24.04.2-desktop-amd64.iso', detail: '2.22 GB de 2.33 GB', status: 'running', progress: 95, downloaded_bytes: 2383700000, total_bytes: 2501800000, speed_bps: 12897484, eta_seconds: 9, kind: 'file', engine: 'http-range', category: 'S.O.', origin: 'HTTP', source_url: 'https://releases.ubuntu.com/24.04/ubuntu.iso', destination: 'C:\\Downloads\\ubuntu.iso' },
    { id: 2, title: 'Vídeo retirado del canal.webm', detail: 'Vídeo no disponible · requiere revisión', status: 'failed', progress: 17, downloaded_bytes: 17200000, total_bytes: 101000000, speed_bps: 0, kind: 'media', engine: 'yt-dlp', category: 'Vídeo', origin: 'yt-dlp', source_url: 'https://example.invalid/video' },
    { id: 3, title: 'manual-equipo.pdf', detail: 'No se pudo conectar después de varios intentos: timeout', status: 'failed', progress: 42, downloaded_bytes: 4200000, total_bytes: 10000000, speed_bps: 0, kind: 'file', engine: 'http-range', category: 'Documentos', origin: 'HTTP', source_url: 'https://downloads.example.com/manual-equipo.pdf' },
    { id: 4, title: 'archivo-completado.zip', detail: 'Completada y verificada', status: 'completed', progress: 100, downloaded_bytes: 24000000, total_bytes: 24000000, speed_bps: 0, kind: 'file', engine: 'http-range', category: 'Archivos', origin: 'HTTP', source_url: 'https://downloads.example.com/archivo-completado.zip', destination: 'C:\Downloads\archivo-completado.zip', updated_at: '2026-07-31T15:30:00Z' },
    { id: 5, title: 'tarea-cancelada.bin', detail: 'Cancelada · parcial eliminado', status: 'cancelled', progress: 0, downloaded_bytes: 0, total_bytes: 5000000, speed_bps: 0, kind: 'file', engine: 'http-range', category: 'Otros', origin: 'HTTP', source_url: 'https://downloads.example.com/tarea-cancelada.bin', updated_at: '2026-07-31T15:20:00Z' }
  ]
};
window.__phase16Calls = [];
window.__phase16Toasts = [];
window.__phase16Copied = '';
Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { readText: async () => '', writeText: async (value) => { window.__phase16Copied = String(value); } } });
const mockedInvoke = async (command, args = {}) => {
  window.__phase16Calls.push({ command, args });
  if (command === 'choose_torrent_file') return 'C:\\Downloads\\linux.torrent';
  if (command === 'queue_torrent_download') return { job_id: 99, filename: 'Linux ISO', destination: 'C:\\Downloads\\Torrents\\Linux ISO', resumable: true };
  if (command === 'job_storage_preview') return { jobId: args.id, title: args.id === 4 ? 'archivo-completado.zip' : 'descarga', status: args.id === 4 ? 'completed' : 'running', active: args.id !== 4, canEmergencyStop: args.id !== 4, managedRoot: 'C:\\Downloads\\CacaTools', finalPaths: args.id === 4 ? ['C:\\Downloads\\CacaTools\\archivo-completado.zip'] : [], partialPaths: args.id === 4 ? [] : ['C:\\Downloads\\CacaTools\\descarga.part'], storageExists: true, safeForStorageDeletion: true, safetyWarning: null };
  if (command === 'emergency_stop_job') return { jobId: args.id, deletePartial: Boolean(args.deletePartial), partialPath: 'C:\\Downloads\\CacaTools\\descarga.part', cleanupPending: Boolean(args.deletePartial) };
  if (command === 'delete_download_job') return { jobId: args.id, deleteStorage: Boolean(args.deleteStorage), recordDeleted: true, stoppedActiveJob: false, removedPaths: args.deleteStorage ? ['C:\\Downloads\\CacaTools\\archivo-completado.zip'] : [] };
  if (command === 'search_media_by_title') return [{ title: 'Nothing’s New (Lyrics)', creator: 'Taj Tracks', source_url: 'https://youtube.com/watch?v=test', duration_label: '3:31', similarity: 97, extractor: 'YouTube', thumbnail: 'data:image/png;base64,broken' }];
  if (command === 'recover_media_source' && args.request?.jobId === 2) return { original_available: false, message: 'La fuente original no respondió.', verification_attempts: 2, recovery_mode: 'media_alternatives', can_retry: true, diagnosis: { code: 'source_unavailable', title: 'Fuente no disponible', summary: 'La fuente confirmó el error.', retryable: true, likely_temporary: false, requires_user_action: false, suggestions: ['Buscar una alternativa fiable', 'Reintentar la fuente original'] }, alternatives: [{ title: 'Vídeo alternativo confirmado', creator: 'Canal alternativo', source_url: 'https://youtube.com/watch?v=alternative', similarity: 94, thumbnail: 'data:image/png;base64,broken', match_reasons: ['Título casi idéntico', 'Duración muy parecida'] }] };
  if (command === 'recover_media_source' && args.request?.jobId === 3) return { original_available: false, message: 'La conexión sigue fallando temporalmente.', verification_attempts: 2, recovery_mode: 'temporary_error', can_retry: true, diagnosis: { code: 'network_failure', title: 'Fallo temporal de conexión', summary: 'La descarga no pudo mantener una conexión estable.', retryable: true, likely_temporary: true, requires_user_action: false, suggestions: ['Comprueba Internet y DNS', 'Reintenta conservando el archivo parcial'] }, alternatives: [] };
  return null;
};
const phase16Context = {
  snapshot,
  pendingJobs: [{ id: 1, title: 'ubuntu-24.04.2-desktop-amd64.iso', detail: 'Pendiente optimista', status: 'queued', progress: 0, kind: 'file' }],
  invoke: mockedInvoke,
  runtimeStatus: { mode: 'local', aria2_available: true, media_available: true },
  mediaRuntimeStatus: { yt_dlp: 'yt-dlp.exe', ffmpeg: 'ffmpeg.exe', ffprobe: 'ffprobe.exe' },
  downloadDirectory: 'C:\\Downloads\\CacaTools',
  schedules: [{ id: 7, job_id: 1, action: 'pause', run_at: '2026-08-01 23:00:00', repeat_daily: true, enabled: true, last_run_at: null }],
  onNewDownload: (url = '') => window.__phase16Calls.push({ command: 'open_download_dialog', args: { url } }),
  onRefresh: async () => { window.__phase16Calls.push({ command: 'refresh', args: {} }); },
  onRerender: () => mountPhase16(),
  onToast: (message, kind) => window.__phase16Toasts.push({ message, kind }),
  onSection: (section) => window.__phase16Calls.push({ command: 'section', args: { section } })
};
function mountPhase16() {
  const fixture = document.querySelector('#fixture');
  fixture.innerHTML = renderDownloadManager(phase16Context);
  bindDownloadManager(phase16Context);
}
mountPhase16();
window.__phase16Ready = true;
"""


def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(condition), "detail": detail})

    css = (ROOT / "app-ui/download-manager/styles.css").read_text(encoding="utf-8")
    html = f"""<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><style>html,body,#fixture{{width:100%;height:100%;margin:0;overflow:hidden;background:#070b10}}{css}</style></head><body><main id=\"fixture\"></main></body></html>"""
    script = browser_bundle() + BOOTSTRAP

    with sync_playwright() as playwright:
        executable = browser_executable()
        if not executable:
            print("SKIP: no se encontró Chrome, Edge o Chromium para el harness", file=sys.stderr)
            return 2
        browser = playwright.chromium.launch(
            executable_path=executable,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.set_default_timeout(5000)
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.set_content(html, wait_until="load")
        page.add_script_tag(content=script)
        page.wait_for_function("window.__phase16Ready === true")

        check("Fusiona trabajos optimistas sin duplicar filas", page.locator('[data-dm-select-job="1"]').count() == 1)
        page.locator("[data-dm-new-download]").first.click()
        check("Abre flujo de descarga general", page.evaluate("window.__phase16Calls.some(x => x.command === 'open_download_dialog')"))

        page.evaluate("""() => {
          const transfer = new DataTransfer();
          transfer.setData('text/plain', 'magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=Drop%20test');
          document.querySelector('.dm-host').dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: transfer }));
        }""")
        check("Acepta magnet por arrastrar y soltar", page.locator('[data-dm-modal="torrent"]').is_visible())
        check("Conserva el magnet soltado", page.locator('#dm-torrent-source').input_value().startswith('magnet:?xt='))
        page.locator('[data-dm-modal-close]').first.click()

        page.locator('body').press('Control+K')
        check("Ctrl+K enfoca el buscador", page.evaluate("document.activeElement?.matches('[data-dm-unified-input]')"))
        page.locator('[data-dm-unified-input]').fill('ubuntu')
        page.wait_for_timeout(180)
        check("La búsqueda conserva foco y texto tras filtrar", page.evaluate("document.activeElement?.matches('[data-dm-unified-input]') && document.activeElement.value === 'ubuntu'"))
        page.locator('[data-dm-unified-input]').fill('')
        page.wait_for_timeout(180)
        page.locator('[data-dm-unified-input]').blur()
        calls_before_shortcut = page.evaluate("window.__phase16Calls.length")
        page.locator('body').press('Control+N')
        check("Ctrl+N enfoca la entrada universal", page.evaluate("document.activeElement?.matches('[data-dm-unified-input]')"))
        page.locator('[data-dm-unified-input]').blur()
        page.locator('body').press('F5')
        check("F5 actualiza el estado local", page.evaluate("window.__phase16Calls.some(x => x.command === 'refresh')"))
        page.locator('body').press('Control+Shift+B')
        check("Ctrl+Shift+B expande la barra lateral inicialmente plegada", page.locator('.dm-root.has-collapsed-sidebar').count() == 0)
        page.locator('body').press('Control+Shift+B')
        check("Ctrl+Shift+B restaura el estado plegado", page.locator('.dm-root.has-collapsed-sidebar').count() == 1)

        page.locator("[data-dm-open-settings]").first.click()
        check("Zen Sidebar permanece como único diseño", page.locator(".dm-zen-sidebar").count() == 1 and page.locator('[data-dm-setting="layout"]').count() == 0)
        check("Mantiene ajustes abiertos", page.locator(".dm-settings-popover").is_visible())
        page.locator('[data-dm-settings-section="appearance"]').click()
        page.locator('[data-dm-setting="accent"]').fill('#4a8fd8')
        check("Aplica el color sin cerrar el panel", page.locator(".dm-settings-popover").is_visible() and '74, 143, 216' in page.locator('.dm-host').evaluate("el => getComputedStyle(el).getPropertyValue('--dm-accent') || el.style.getPropertyValue('--dm-accent')") or page.locator('.dm-host').get_attribute('style').find('#4a8fd8') >= 0)
        page.locator('[data-dm-settings-close]').click()

        page.locator('[data-dm-category-toggle]').click()
        page.locator('[data-dm-category-option="__completed"]').click()
        page.locator('[data-dm-select-job="4"]').click()
        page.locator('[data-dm-toggle="inspector"]').first.click()
        check("Una completada no ofrece reanudar ni cancelar", page.locator('.dm-inspector [data-dm-job-action="resume"]').count() == 0 and page.locator('.dm-inspector [data-dm-cancel-job]').count() == 0)
        check("Una completada permite abrir su archivo", page.locator('.dm-inspector [data-dm-job-action="reveal"]').count() >= 1)
        check("Una completada permite eliminar su registro", page.locator('.dm-inspector [data-dm-delete-job="4"]').count() >= 1)
        page.locator('.dm-inspector [data-dm-delete-job="4"]').click()
        page.wait_for_timeout(80)
        check("La eliminación muestra las rutas administradas", page.locator('[data-dm-modal="delete"]').is_visible() and page.get_by_text('C:\\Downloads\\CacaTools\\archivo-completado.zip').count() >= 1)
        check("El borrado físico empieza bloqueado", page.locator('[data-dm-confirm-delete="storage"]').is_disabled())
        page.locator('[data-dm-delete-storage-ack]').check()
        check("La confirmación habilita el borrado físico", page.locator('[data-dm-confirm-delete="storage"]').is_enabled())
        page.locator('[data-dm-confirm-delete="storage"]').click()
        page.wait_for_timeout(60)
        check("Elimina almacenamiento solo tras confirmación", page.evaluate("window.__phase16Calls.some(x => x.command === 'delete_download_job' && x.args.id === 4 && x.args.deleteStorage === true)"))
        page.locator('[data-dm-category-toggle]').click()
        page.locator('[data-dm-category-option="all"]').click()
        page.locator('[data-dm-category-toggle]').click()
        page.locator('[data-dm-category-option="Documentos"]').click()
        check("Filtra desde el selector de categoría", page.locator('[data-dm-category-label]').inner_text() == 'Documentos')
        page.locator('[data-dm-category-toggle]').click()
        page.locator('[data-dm-category-option="all"]').click()
        page.locator('[data-dm-open-settings]').first.click()
        check("Abre ajustes del gestor", page.locator(".dm-settings-popover").is_visible())
        page.locator('[data-dm-settings-close]').click()
        page.locator('[data-dm-section="downloads"]').click()
        page.locator('[data-dm-category-toggle]').click()
        page.locator('[data-dm-category-option="all"]').click()
        page.locator('[data-dm-select-job="1"]').click()
        page.locator('[data-dm-inspector-tab="files"]').click()
        check("Archivos muestra rutas reales", page.locator('.dm-inspector-file-list').is_visible() and page.get_by_text('C:\\Downloads\\ubuntu.iso').count() >= 1)
        page.locator('.dm-inspector-file-list [data-dm-copy-value]').first.click()
        page.wait_for_timeout(30)
        check("Copia la ruta desde el inspector", page.evaluate("window.__phase16Copied === 'C:\\\\Downloads\\\\ubuntu.iso'"))
        page.locator('[data-dm-inspector-tab="connections"]').click()
        check("Conexiones muestra endpoint y protocolo", page.locator('.dm-connection-list').is_visible() and page.get_by_text('releases.ubuntu.com').count() >= 1 and page.get_by_text('HTTPS').count() >= 1)
        page.locator('[data-dm-inspector-tab="log"]').click()
        check("Registro muestra estado persistente", page.locator('.dm-inspector-log').is_visible() and page.get_by_text('2.22 GB de 2.33 GB').count() >= 1)
        page.locator('[data-dm-inspector-tab="summary"]').click()

        page.locator("[data-dm-add-torrent]").first.click()
        check("Abre diálogo torrent", page.locator('[data-dm-modal="torrent"]').is_visible())
        page.locator("[data-dm-choose-torrent]").click()
        check("Selector nativo rellena la ruta", page.locator("#dm-torrent-source").input_value().endswith("linux.torrent"))
        page.locator("[data-dm-queue-torrent]").click()
        page.wait_for_timeout(80)
        check("Encola torrent", page.evaluate("window.__phase16Calls.some(x => x.command === 'queue_torrent_download' && x.args.source.endsWith('linux.torrent'))"))
        check("Cierra diálogo torrent tras éxito", page.locator('[data-dm-modal="torrent"]').count() == 0)

        page.locator('[data-dm-cancel-job="1"]').click()
        check("Abre cancelación segura", page.locator('[data-dm-modal="cancel"]').is_visible())
        page.locator('[data-dm-confirm-cancel="keep"]').click()
        page.wait_for_timeout(60)
        check("Conserva parcial por elección", page.evaluate("window.__phase16Calls.some(x => x.command === 'emergency_stop_job' && x.args.id === 1 && x.args.deletePartial === false)"))

        page.locator('[data-dm-select-job="2"]').click()
        page.locator('[data-dm-recover-job="2"]').first.click()
        page.locator('[data-dm-run-recovery]').click()
        page.wait_for_timeout(80)
        check("Ejecuta recuperación multimedia", page.evaluate("window.__phase16Calls.some(x => x.command === 'recover_media_source' && x.args.request?.jobId === 2)"))
        check("Muestra alternativa con similitud", page.get_by_text("94% similar").is_visible())
        check("Explica por qué coincide", page.get_by_text("Título casi idéntico").is_visible())
        check("Confirma la fuente dos veces", page.get_by_text("Fuente comprobada 2 veces").is_visible())
        page.wait_for_timeout(40)
        check("Alternativa conserva miniatura estética si falla la imagen", page.locator('.dm-alternative-list .dm-thumbnail-failed').count() == 1)
        page.locator('[data-dm-retry-recovery]').click()
        page.wait_for_timeout(60)
        check("Reintenta conservando el parcial", page.evaluate("window.__phase16Calls.some(x => x.command === 'set_job_status' && x.args.id === 2 && x.args.status === 'running')"))

        page.locator('[data-dm-select-job="3"]').click()
        page.locator('[data-dm-recover-job="3"]').first.click()
        page.locator('[data-dm-run-recovery]').click()
        page.wait_for_timeout(80)
        check("Diagnostica también archivos directos", page.evaluate("window.__phase16Calls.some(x => x.command === 'recover_media_source' && x.args.request?.jobId === 3)"))
        check("Distingue un fallo temporal de red", page.get_by_text("Fallo temporal de conexión").is_visible())
        check("No inventa alternativas para archivos directos", page.get_by_text("No es necesario buscar otro vídeo para este tipo de error").is_visible())
        page.locator('[data-dm-retry-recovery]').click()
        page.wait_for_timeout(60)
        check("Reintenta el archivo directo sin borrar el parcial", page.evaluate("window.__phase16Calls.some(x => x.command === 'set_job_status' && x.args.id === 3 && x.args.status === 'running')"))

        page.locator('[data-dm-select-job="2"]').click()
        page.locator('[data-dm-schedule-job="2"]').click()
        page.locator("#dm-schedule-at").fill("2026-08-01T09:30")
        page.locator("#dm-schedule-action").select_option("resume")
        page.locator("[data-dm-save-schedule]").click()
        page.wait_for_timeout(60)
        check("Guarda tarea programada", page.evaluate("window.__phase16Calls.some(x => x.command === 'create_download_schedule' && x.args.jobId === 2 && x.args.runAt === '2026-08-01T09:30')"))

        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT), full_page=False)
        check("Sin errores JavaScript", not page_errors, page_errors)
        browser.close()

    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        ROOT / "app-ui/download-manager/styles.css",
        *(ROOT / relative for relative in MODULES),
    ])
    report = {
        "gate": "phase16-interaction-smoke",
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "passed": all(item["pass"] for item in checks),
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": checks,
        "screenshot": str(SCREENSHOT.relative_to(ROOT)),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["passed"]:
        print(f"OK: {len(checks)} interacciones Phase16 conectadas y verificadas.")
        return 0
    for item in checks:
        if not item["pass"]:
            print(f"FAIL: {item['name']} · {item.get('detail')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
