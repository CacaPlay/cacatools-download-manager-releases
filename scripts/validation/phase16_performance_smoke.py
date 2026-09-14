#!/usr/bin/env python3
"""Performance and scalability gate for the Phase16 download manager.

The gate mounts the real renderer and bindings with a queue of 1,000 jobs, then
measures initial render, debounced filtering, layout switching and compact-mode
fit. Thresholds are deliberately generous enough for CI while still catching
accidental quadratic work, synchronous image loading or layout regressions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from phase16_hashing import source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "tests" / "phase16-performance-smoke.json"
MODULES = (
    "app-ui/download-manager/core/constants.js",
    "app-ui/download-manager/core/model.js",
    "app-ui/download-manager/view/icons.js",
    "app-ui/download-manager/view/shared.js",
    "app-ui/download-manager/view/sections.js",
    "app-ui/download-manager/view/command-center.js",
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


BOOTSTRAP = r"""
const statuses = ['running', 'queued', 'paused', 'failed', 'completed', 'cancelled'];
const categories = ['Vídeo', 'Software', 'Documentos', 'Música', 'S.O.', 'Archivos'];
const jobs = Array.from({ length: 1000 }, (_, index) => {
  const number = index + 1;
  const status = statuses[index % statuses.length];
  const running = status === 'running';
  const total = 25_000_000 + (index * 31_337);
  const progress = status === 'completed' ? 100 : status === 'cancelled' ? 0 : (index * 17) % 99;
  return {
    id: number,
    title: `archivo-${String(number).padStart(4, '0')}-${index % 5 === 0 ? 'video' : 'paquete'}.${index % 5 === 0 ? 'mp4' : 'zip'}`,
    detail: `Elemento de rendimiento ${number}`,
    status,
    progress,
    downloaded_bytes: Math.round(total * progress / 100),
    total_bytes: total,
    speed_bps: running ? 1_500_000 + (index % 20) * 120_000 : 0,
    eta_seconds: running ? 15 + (index % 420) : 0,
    kind: index % 5 === 0 ? 'media' : 'file',
    engine: index % 5 === 0 ? 'yt-dlp' : 'aria2c',
    category: categories[index % categories.length],
    origin: index % 5 === 0 ? 'yt-dlp' : 'HTTP',
    source_url: `https://downloads.example.test/files/${number}`,
    destination: `C:\\Downloads\\CacaTools\\archivo-${number}`,
    updated_at: new Date(Date.UTC(2026, 6, 31, 16, 0, index % 60)).toISOString(),
    active_connections: running ? 8 : 0,
    max_connections: running ? 16 : 0
  };
});
const phase16Context = {
  snapshot: { jobs },
  pendingJobs: [],
  invoke: async () => null,
  runtimeStatus: { mode: 'local', aria2_available: true, media_available: true },
  mediaRuntimeStatus: { yt_dlp: 'yt-dlp.exe', ffmpeg: 'ffmpeg.exe', ffprobe: 'ffprobe.exe' },
  downloadDirectory: 'C:\\Downloads\\CacaTools',
  schedules: [],
  onNewDownload: () => {},
  onRefresh: async () => {},
  onToast: () => {},
  onSection: () => {},
  onRerender: () => mountPhase16()
};
function mountPhase16() {
  const started = performance.now();
  const fixture = document.querySelector('#fixture');
  fixture.innerHTML = renderDownloadManager(phase16Context);
  bindDownloadManager(phase16Context);
  window.__phase16LastMountMs = performance.now() - started;
  window.__phase16MountCount = (window.__phase16MountCount || 0) + 1;
}
const initialStarted = performance.now();
mountPhase16();
window.__phase16InitialMs = performance.now() - initialStarted;
window.__phase16Ready = true;
"""


def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(condition), "detail": detail})

    css = (ROOT / "app-ui/download-manager/styles.css").read_text(encoding="utf-8")
    html = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<style>html,body,#fixture{{width:100%;height:100%;margin:0;overflow:hidden;background:#070b10}}{css}</style>'
        '</head><body><main id="fixture"></main></body></html>'
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.set_content(html, wait_until="load")
        page.add_script_tag(content=browser_bundle() + BOOTSTRAP)
        page.wait_for_function("window.__phase16Ready === true")

        initial_ms = float(page.evaluate("window.__phase16InitialMs"))
        row_count = page.locator(".dm-command-row").count()
        content_visibility = page.locator(".dm-command-row").first.evaluate(
            "node => getComputedStyle(node).contentVisibility"
        )
        desktop_overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )

        check("Renderiza una cola de 1,000 trabajos", row_count == 1000, row_count)
        check("Render inicial dentro del presupuesto", initial_ms < 2500, round(initial_ms, 2))
        check("Filas fuera de pantalla usan content-visibility", content_visibility == "auto", content_visibility)
        check("Sin desbordamiento horizontal de documento en 1920x1080", desktop_overflow <= 2, desktop_overflow)

        search = page.locator("[data-dm-search]")
        search.focus()
        filter_started = page.evaluate("performance.now()")
        search.fill("archivo-0999")
        page.wait_for_timeout(220)
        filter_ms = float(page.evaluate("performance.now()")) - float(filter_started)
        filtered_rows = page.locator(".dm-command-row").count()
        focus_preserved = page.evaluate(
            "document.activeElement?.matches('[data-dm-search]') && document.activeElement.value === 'archivo-0999'"
        )
        check("Filtrado de 1,000 trabajos responde", filtered_rows == 1, filtered_rows)
        check("Filtrado completo dentro del presupuesto", filter_ms < 1500, round(filter_ms, 2))
        check("El buscador conserva foco y texto", focus_preserved)

        search.fill("")
        page.wait_for_timeout(220)
        page.locator("[data-dm-open-settings]").first.click()
        layout_select = page.locator('[data-dm-setting="layout"]')
        layout_started = page.evaluate("performance.now()")
        layout_select.select_option("zen-sidebar")
        page.wait_for_function("document.querySelector('.dm-host')?.dataset.dmLayout === 'zen-sidebar'")
        layout_ms = float(page.evaluate("performance.now()")) - float(layout_started)
        zen_rows = page.locator(".dm-zen-row").count()
        check("Cambio real a Zen Sidebar conserva los 1,000 trabajos", zen_rows == 1000, zen_rows)
        check("Cambio de diseño dentro del presupuesto", layout_ms < 2000, round(layout_ms, 2))

        compact_search = page.locator('[data-dm-search]')
        compact_search.fill('archivo-0001')
        page.wait_for_timeout(180)
        close_settings = page.locator('[data-dm-settings-close]')
        if close_settings.count():
            close_settings.click()
        page.set_viewport_size({"width": 720, "height": 560})
        page.wait_for_timeout(100)
        compact_overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        compact_offenders = page.evaluate(
            """() => [...document.querySelectorAll('button,input,select')]
              .filter((node) => {
                const rect = node.getBoundingClientRect();
                const style = getComputedStyle(node);
                const intersectsViewport = rect.right > 0 && rect.left < innerWidth && rect.bottom > 0 && rect.top < innerHeight;
                const hiddenMobilePanel = Boolean(node.closest('.dm-zen-nav,.dm-command-sidebar,.dm-inspector'));
                return !hiddenMobilePanel && style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0 && intersectsViewport && (rect.left < -1 || rect.right > innerWidth + 1);
              })
              .map((node) => {
                const rect = node.getBoundingClientRect();
                return { tag: node.tagName, text: (node.textContent || node.getAttribute('aria-label') || '').trim().slice(0, 80), left: Math.round(rect.left), right: Math.round(rect.right), className: node.className || '' };
              })"""
        )
        compact_controls = not compact_offenders
        check("Sin desbordamiento horizontal de documento en 720x560", compact_overflow <= 2, compact_overflow)
        check("Controles principales compactos permanecen alcanzables", compact_controls, compact_offenders)

        page.evaluate("document.querySelector('.dm-mobile-menu')?.click()")
        page.wait_for_timeout(30)
        sidebar_rect = page.locator('.dm-zen-nav').evaluate("node => { const r = node.getBoundingClientRect(); return { left:r.left, right:r.right, width:r.width }; }")
        check("Sidebar móvil se abre completamente dentro de la pantalla", sidebar_rect["left"] >= -1 and sidebar_rect["right"] <= 721, sidebar_rect)
        page.evaluate("document.querySelector('.dm-mobile-menu')?.click()")
        page.wait_for_timeout(30)

        page.evaluate("document.querySelector('.dm-zen-row')?.click()")
        page.wait_for_timeout(30)
        inspector_rect = page.locator('.dm-inspector').evaluate("node => { const r = node.getBoundingClientRect(); return { left:r.left, right:r.right, width:r.width }; }")
        check("Inspector móvil se abre completamente dentro de la pantalla", inspector_rect["left"] >= -1 and inspector_rect["right"] <= 721, inspector_rect)
        page.evaluate("document.querySelector('.dm-inspector [data-dm-toggle=\"inspector\"]')?.click()")
        page.wait_for_timeout(30)
        check("Sin errores JavaScript", not page_errors, page_errors)
        browser.close()

    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        *(ROOT / relative for relative in MODULES),
        ROOT / "app-ui/download-manager/styles.css",
    ])
    report = {
        "gate": "phase16-performance-smoke",
        "passed": all(item["pass"] for item in checks),
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "queueSize": 1000,
        "thresholdsMs": {"initialRender": 2500, "filter": 1500, "layoutSwitch": 2000},
        "measurementsMs": {
            "initialRender": round(initial_ms, 2),
            "filter": round(filter_ms, 2),
            "layoutSwitch": round(layout_ms, 2),
        },
        "checks": checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [item for item in checks if not item["pass"]]
    if failed:
        for item in failed:
            print(f"FAIL: {item['name']} -> {item.get('detail')}")
        return 1
    print(
        "OK: cola de 1,000 trabajos validada "
        f"(render {initial_ms:.1f} ms, filtro {filter_ms:.1f} ms, diseño {layout_ms:.1f} ms)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
