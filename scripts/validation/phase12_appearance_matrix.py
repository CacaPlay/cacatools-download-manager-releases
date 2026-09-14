#!/usr/bin/env python3
"""Windows appearance, scale and color-preview gate for Fase 12."""
from __future__ import annotations

import json
import shutil
import socket
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "tests" / "phase12-appearance-matrix.json"
SCREENSHOTS = ROOT / "docs" / "screenshots" / "phase12-appearance"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


def browser_executable() -> str | None:
    candidates = (
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return shutil.which("msedge") or shutil.which("chromium") or shutil.which("google-chrome")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def appearance_state(theme: str, accent: str, scale: int, text_scale: int) -> dict[str, Any]:
    return {
        "theme": theme,
        "preset": "caca-green" if accent.lower() == "#03fc20" else "custom",
        "accent": accent,
        "tone": 8,
        "intensity": 88,
        "contrast": 108,
        "scale": scale,
        "textScale": text_scale,
        "density": "normal",
        "thumbnailSize": "large",
        "autoScale": False,
        "motion": False,
        "appearanceRevision": 7,
    }


def dm_state(theme: str, accent: str, scale: int, text_scale: int) -> dict[str, Any]:
    return {
        "layout": "zen-sidebar",
        "section": "downloads",
        "theme": theme,
        "accent": accent,
        "accentIntensity": 88,
        "success": "#51c987",
        "successCustomized": False,
        "warning": "#e8b04c",
        "danger": "#ef6b72",
        "sidebarCollapsed": True,
        "inspectorCollapsed": True,
        "lowerPanelCollapsed": True,
        "compactRows": False,
        "filter": "all",
        "category": "all",
        "query": "",
        "selectedJobId": None,
        "inspectorTab": "summary",
        "commandPanel": "overview",
        "uiScale": scale,
        "textScale": text_scale,
        "appearanceRevision": 8,
    }


def main() -> int:
    executable = browser_executable()
    if not executable:
        print("FAIL: no se encontró Edge, Chrome o Chromium para la matriz de apariencia")
        return 1

    port = free_port()
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks: list[dict[str, Any]] = []
    samples: dict[str, Any] = {}
    performance: dict[str, Any] = {}

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    cases = (
        ("dark-default-1600", 1600, 900, "dark", "#03fc20", 100, 100),
        ("light-default-1180", 1180, 780, "light", "#03fc20", 100, 100),
        ("dark-custom-minimum", 1180, 720, "dark", "#d94fff", 100, 100),
        ("light-custom-1600", 1600, 900, "light", "#2f78d0", 100, 100),
        ("dark-maximum-1600", 1600, 900, "dark", "#03fc20", 130, 120),
        ("light-minimum-1180", 1180, 720, "light", "#2f78d0", 50, 80),
    )

    try:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=executable,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            for name, width, height, theme, accent, scale, text_scale in cases:
                context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
                page = context.new_page()
                page_errors: list[str] = []
                page.on("pageerror", lambda error, target=page_errors: target.append(str(error)))
                seed = {
                    "appearance": appearance_state(theme, accent, scale, text_scale),
                    "manager": dm_state(theme, accent, scale, text_scale),
                }
                page.add_init_script(
                    """(() => {
                      const seed = %s;
                      localStorage.setItem('cacatools.desktop.appearance.v1', JSON.stringify(seed.appearance));
                      localStorage.setItem('cacatools.download-manager.v2', JSON.stringify(seed.manager));
                    })();""" % json.dumps(seed)
                )
                started = time.perf_counter()
                page.goto(f"http://127.0.0.1:{port}/?preview=1", wait_until="domcontentloaded", timeout=20_000)
                page.wait_for_selector(".dm-host", timeout=10_000)
                startup_ms = (time.perf_counter() - started) * 1000
                page.locator("[data-dm-open-settings]").first.click()
                page.locator('[data-dm-settings-section="appearance"]').click()
                page.wait_for_selector('[data-dm-settings-panel="appearance"]', timeout=5_000)
                metrics = page.evaluate(
                    """() => {
                      const host=document.querySelector('.dm-host');
                      const root=document.documentElement;
                      const panel=document.querySelector('[data-dm-settings-panel="appearance"]');
                      const themeSelect=panel?.querySelector('[data-dm-setting="theme"]');
                      const ui=panel?.querySelector('[data-dm-setting="uiScale"]');
                      const font=panel?.querySelector('[data-dm-setting="textScale"]');
                      const styles=getComputedStyle(root);
                      const hostStyles=getComputedStyle(host);
                      const parse=(value)=>{const m=String(value).match(/[0-9.]+/g)||[];return m.slice(0,3).map(Number)};
                      const lum=(value)=>parse(value).map(v=>{const n=v/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
                      const contrast=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
                      const textColor=getComputedStyle(panel).color;
                      const surfaceColor=getComputedStyle(document.querySelector('.dm-settings-popover')).backgroundColor;
                      const selectStyle=getComputedStyle(themeSelect);
                      const controls=[...document.querySelectorAll('.dm-zen-secondary-row>.dm-zen-secondary-actions .dm-helper-chips button,.dm-zen-secondary-row>.dm-zen-toolbar-actions .dm-selection-toggle,.dm-zen-secondary-row>.dm-zen-toolbar-actions .dm-category-toggle,.dm-zen-secondary-row>.dm-zen-toolbar-actions .dm-details-toggle')];
                      const heights=controls.map(node=>+node.getBoundingClientRect().height.toFixed(2));
                      return {
                        viewport:{width:innerWidth,height:innerHeight}, rootTheme:root.dataset.theme, hostTheme:host?.dataset.dmTheme,
                        uiScale:ui?.value, textScale:font?.value, resolvedScale:root.dataset.resolvedScale,
                        rootFont:getComputedStyle(root).fontSize, documentOverflow:root.scrollWidth-root.clientWidth,
                        managerOverflow:host.scrollWidth-host.clientWidth, panelContrast:+contrast(textColor,surfaceColor).toFixed(2), textColor, surfaceColor,
                        selectBackground:selectStyle.backgroundColor, selectLuminance:+lum(selectStyle.backgroundColor).toFixed(3),
                        accent:hostStyles.getPropertyValue('--dm-accent').trim(), success:hostStyles.getPropertyValue('--dm-success').trim(),
                        warning:hostStyles.getPropertyValue('--dm-warning').trim(), danger:hostStyles.getPropertyValue('--dm-danger').trim(),
                        controlHeights:heights, controlsSameHeight:heights.length===7&&Math.max(...heights)-Math.min(...heights)<=1,
                        settingsInsideViewport:panel.getBoundingClientRect().right<=innerWidth+1&&panel.getBoundingClientRect().bottom<=innerHeight+1
                      };
                    }"""
                )
                metrics["startupMs"] = round(startup_ms, 2)
                metrics["pageErrors"] = page_errors
                samples[name] = metrics
                check(f"{name}: tema global y manager coinciden", metrics["rootTheme"] == theme and metrics["hostTheme"] == theme, metrics)
                check(f"{name}: escala y fuente aplican el valor solicitado", metrics["uiScale"] == str(scale) and metrics["textScale"] == str(text_scale) and metrics["resolvedScale"] == str(scale), metrics)
                check(f"{name}: sin overflow horizontal", metrics["documentOverflow"] == 0 and metrics["managerOverflow"] == 0, metrics)
                check(f"{name}: texto principal supera contraste práctico", metrics["panelContrast"] >= 4.5, metrics["panelContrast"])
                check(f"{name}: controles de toolbar mantienen altura", metrics["controlsSameHeight"], metrics["controlHeights"])
                check(f"{name}: Ajustes permanece dentro del viewport", metrics["settingsInsideViewport"], metrics)
                check(f"{name}: estados semánticos no colapsan al acento", len({metrics["accent"], metrics["success"], metrics["warning"], metrics["danger"]}) == 4, metrics)
                check(f"{name}: sin errores JavaScript", not page_errors, page_errors)
                if theme == "light":
                    check(f"{name}: dropdown usa superficie clara", metrics["selectLuminance"] >= 0.72, metrics["selectBackground"])
                if "default" in name and scale == 100 and text_scale == 100:
                    check(f"{name}: defaults visibles 100/100", metrics["uiScale"] == "100" and metrics["textScale"] == "100", metrics)
                page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=False, animations="disabled")

                if name == "dark-default-1600":
                    performance = page.evaluate(
                        """async () => {
                          const metrics=window.__cacatoolsAppearancePerformance;
                          for(const key of ['previewEvents','previewCommits','persistenceWrites','globalRendersDuringPreview','totalPreviewLatencyMs','maxPreviewLatencyMs']) metrics[key]=0;
                          const app=document.querySelector('#app');
                          let managerReplacements=0;
                          const observer=new MutationObserver(records=>{for(const record of records){for(const node of record.removedNodes){if(node.nodeType===1&&(node.matches?.('.dm-host')||node.querySelector?.('.dm-host'))) managerReplacements+=1;}}});
                          observer.observe(app,{childList:true});
                          const input=document.querySelector('[data-dm-setting="accent"]');
                          const started=performance.now();
                          for(let frame=0;frame<12;frame+=1){
                            for(let i=0;i<15;i+=1){const n=frame*15+i;input.value=`#${((n*7919)%0xffffff).toString(16).padStart(6,'0')}`;input.dispatchEvent(new Event('input',{bubbles:true}));}
                            await new Promise(resolve=>requestAnimationFrame(resolve));
                          }
                          await new Promise(resolve=>requestAnimationFrame(resolve));
                          const dragMs=performance.now()-started;
                          const beforeCommit={...metrics,managerReplacements};
                          input.dispatchEvent(new Event('change',{bubbles:true}));
                          await new Promise(resolve=>setTimeout(resolve,320));
                          observer.disconnect();
                          return {events:180,dragMs:+dragMs.toFixed(2),beforeCommit,afterCommit:{...metrics,managerReplacements},averageEventMs:+(dragMs/180).toFixed(3)};
                        }"""
                    )
                    check("Color drag: 180 eventos se agrupan por frame", performance["beforeCommit"]["previewEvents"] == 180 and performance["beforeCommit"]["previewCommits"] <= 13, performance)
                    check("Color drag: cero persistencias antes de change", performance["beforeCommit"]["persistenceWrites"] == 0, performance)
                    check("Color drag: una persistencia final", performance["afterCommit"]["persistenceWrites"] == 1, performance)
                    check("Color drag: el manager no se reconstruye", performance["afterCommit"]["managerReplacements"] == 0, performance)
                    check("Color drag: preview media por evento menor a un frame", performance["averageEventMs"] < 16.7, performance)
                context.close()

            context = browser.new_context(viewport={"width": 1180, "height": 780}, reduced_motion="reduce")
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{port}/?preview=1", wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_selector(".dm-host", timeout=10_000)
            page.locator("[data-dm-open-settings]").first.click()
            page.locator('[data-dm-settings-section="appearance"]').click()
            fresh = page.evaluate(
                """() => ({
                  ui: document.querySelector('[data-dm-setting="uiScale"]')?.value,
                  font: document.querySelector('[data-dm-setting="textScale"]')?.value,
                  appearance: JSON.parse(localStorage.getItem('cacatools.desktop.appearance.v1') || '{}'),
                  manager: JSON.parse(localStorage.getItem('cacatools.download-manager.v2') || '{}')
                })"""
            )
            check("InstalaciÃ³n limpia nace en 100/100", fresh["ui"] == "100" and fresh["font"] == "100" and fresh["appearance"].get("appearanceRevision") == 7, fresh)
            context.close()

            context = browser.new_context(viewport={"width": 1180, "height": 780}, reduced_motion="reduce")
            page = context.new_page()
            page.add_init_script(
                """(() => {
                  localStorage.setItem('cacatools.desktop.appearance.v1', JSON.stringify({theme:'dark',preset:'caca-green',accent:'#03fc20',tone:8,intensity:88,contrast:108,scale:125,textScale:120,density:'normal',thumbnailSize:'large',autoScale:false,motion:true,appearanceRevision:6}));
                  localStorage.setItem('cacatools.download-manager.v2', JSON.stringify({layout:'zen-sidebar',theme:'dark',accent:'#03fc20',accentIntensity:88,success:'#51c987',warning:'#e8b04c',danger:'#ef6b72',uiScale:125,textScale:120,appearanceRevision:7}));
                })();"""
            )
            page.goto(f"http://127.0.0.1:{port}/?preview=1", wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_selector(".dm-host", timeout=10_000)
            page.locator("[data-dm-open-settings]").first.click()
            page.locator('[data-dm-settings-section="appearance"]').click()
            migrated = page.evaluate(
                """() => ({
                  ui: document.querySelector('[data-dm-setting="uiScale"]')?.value,
                  font: document.querySelector('[data-dm-setting="textScale"]')?.value,
                  resolvedScale: document.documentElement.dataset.resolvedScale,
                  effectiveUi: getComputedStyle(document.documentElement).getPropertyValue('--ui-scale').trim(),
                  appearance: JSON.parse(localStorage.getItem('cacatools.desktop.appearance.v1') || '{}'),
                  manager: JSON.parse(localStorage.getItem('cacatools.download-manager.v2') || '{}')
                })"""
            )
            check("MigraciÃ³n histÃ³rica 125/120 -> 100/100 preserva factor visual", migrated["ui"] == "100" and migrated["font"] == "100" and migrated["resolvedScale"] == "100" and abs(float(migrated["effectiveUi"]) - 1.24) < 0.001 and migrated["appearance"].get("appearanceRevision") == 7 and migrated["manager"].get("appearanceRevision") == 8, migrated)
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    payload = {
        "phase": 12,
        "browser": executable,
        "passed": all(item["pass"] for item in checks),
        "checks": checks,
        "samples": samples,
        "performance": performance,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "checks": len(checks), "report": str(REPORT), "performance": performance}, ensure_ascii=False))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
