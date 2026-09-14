#!/usr/bin/env python3
"""Smoke-test the real application entrypoint without relying on local HTTP access.

The CI sandbox blocks localhost/file navigation. This gate therefore loads the real
index body and CSS with Playwright ``set_content`` and executes the real ES modules
through recursively rewritten data-URL imports. Unlike the renderer fixture, this
covers ``app-ui/main.js`` and verifies that the legacy desktop shell cannot become
visible during startup.
"""
from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from phase16_hashing import manager_source_files, source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/tests/phase16-standalone-app-smoke.json"
SCREENSHOTS = ROOT / "docs/screenshots/phase16"
ENTRYPOINT = ROOT / "app-ui/main.js"
INDEX = ROOT / "index.html"


@dataclass(frozen=True)
class Case:
    name: str
    layout: str
    theme: str
    width: int
    height: int


CASES = (
    Case("standalone-command-center-dark-1920x1080", "command-center", "dark", 1920, 1080),
    Case("standalone-zen-light-1366x768", "zen-sidebar", "light", 1366, 768),
    Case("standalone-command-center-dark-720x560", "command-center", "dark", 720, 560),
    Case("standalone-zen-dark-720x560", "zen-sidebar", "dark", 720, 560),
)

IMPORT_RE = re.compile(
    r"(?P<prefix>\b(?:import|export)\s+(?:[^'\";]+?\s+from\s+)?)(?P<quote>['\"])(?P<path>\.[^'\"]+)(?P=quote)",
    re.MULTILINE,
)


def data_url(source: str) -> str:
    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    return f"data:text/javascript;base64,{encoded}"


def module_url(path: Path, cache: dict[Path, str]) -> str:
    resolved = path.resolve()
    if resolved in cache:
        return cache[resolved]
    source = resolved.read_text(encoding="utf-8")

    def replace_import(match: re.Match[str]) -> str:
        dependency = (resolved.parent / match.group("path")).resolve()
        if not dependency.is_file() or ROOT not in dependency.parents:
            raise RuntimeError(f"Importación fuera del proyecto: {dependency}")
        return f"{match.group('prefix')}{match.group('quote')}{module_url(dependency, cache)}{match.group('quote')}"

    transformed = IMPORT_RE.sub(replace_import, source)
    url = data_url(transformed)
    cache[resolved] = url
    return url


def transformed_entrypoint() -> str:
    source = ENTRYPOINT.read_text(encoding="utf-8")
    cache: dict[Path, str] = {}

    def replace_import(match: re.Match[str]) -> str:
        dependency = (ENTRYPOINT.parent / match.group("path")).resolve()
        return f"{match.group('prefix')}{match.group('quote')}{module_url(dependency, cache)}{match.group('quote')}"

    source = IMPORT_RE.sub(replace_import, source)
    source = source.replace("const previewMode = qs.has('preview');", "const previewMode = true;")
    if "const previewMode = true;" not in source:
        raise RuntimeError("No se pudo activar el modo determinista del entrypoint real.")
    return source


def inline_document(preferences: dict[str, Any]) -> str:
    index_source = INDEX.read_text(encoding="utf-8")
    body_match = re.search(r"<body>(.*?)</body>", index_source, flags=re.DOTALL | re.IGNORECASE)
    if not body_match:
        raise RuntimeError("index.html no contiene un body válido")
    body = re.sub(r"<script\b[^>]*>.*?</script>", "", body_match.group(1), flags=re.DOTALL | re.IGNORECASE)
    manager_css = (ROOT / "app-ui/download-manager/styles.css").read_text(encoding="utf-8")
    app_css = (ROOT / "app-ui/styles.css").read_text(encoding="utf-8")
    app_css = re.sub(r"^@import\s+url\([^)]*download-manager/styles\.css[^)]*\);\s*", "", app_css)
    store = {
        "cacatools.download-manager.v1": json.dumps(preferences, ensure_ascii=False),
        "cacatools.desktop.appearance.v1": json.dumps({
            "preset": "custom",
            "accent": preferences["accent"],
            "tone": 8,
            "intensity": 82,
            "contrast": 108,
            "scale": 100,
            "autoScale": True,
            "motion": False,
        }, ensure_ascii=False),
    }
    bootstrap = f"""
      (() => {{
        const values = {json.dumps(store, ensure_ascii=False)};
        const storage = {{
          getItem(key) {{ return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null; }},
          setItem(key, value) {{ values[key] = String(value); }},
          removeItem(key) {{ delete values[key]; }},
          clear() {{ Object.keys(values).forEach((key) => delete values[key]); }},
          key(index) {{ return Object.keys(values)[index] ?? null; }},
          get length() {{ return Object.keys(values).length; }}
        }};
        Object.defineProperty(window, 'localStorage', {{ configurable: true, value: storage }});
        window.matchMedia ||= (query) => ({{ matches: false, media: query, addEventListener() {{}}, removeEventListener() {{}} }});
      }})();
    """
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CacaTools Download Manager</title><style>{manager_css}\n{app_css}</style><script>{bootstrap}</script></head><body>{body}</body></html>"""


def inspect(page: Any, case: Case) -> dict[str, Any]:
    return page.evaluate(
        """
        ({ width, height }) => {
          const host = document.querySelector('.dm-host');
          const root = document.querySelector('.dm-root');
          const visible = (element) => {
            if (!element) return false;
            const rect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.left < width && rect.bottom > 0 && rect.top < height && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
          };
          const overflow = [...document.querySelectorAll('button,input,select')]
            .filter(visible)
            .map((element) => ({ element, rect: element.getBoundingClientRect() }))
            .filter(({ rect }) => rect.left < -1 || rect.right > width + 1)
            .map(({ element, rect }) => ({
              text: (element.innerText || element.getAttribute('aria-label') || '').trim().slice(0, 60),
              rect: [Math.round(rect.left), Math.round(rect.right)]
            }));
          return {
            title: document.title,
            host: Boolean(host),
            root: Boolean(root),
            theme: host?.dataset.dmTheme || '',
            layout: host?.dataset.dmLayout || '',
            standaloneClass: document.body.classList.contains('download-manager-standalone'),
            oldShell: Boolean(document.querySelector('.desktop-shell')),
            oldNavigation: document.querySelectorAll('.sidebar > .side-nav').length,
            managerSearch: visible(document.querySelector('[data-dm-search]')),
            managerRows: document.querySelectorAll('[data-dm-select-job]').length,
            managerControls: document.querySelectorAll('[data-dm-new-download], [data-dm-video-search], [data-dm-toggle]').length,
            dimensions: root ? [root.scrollWidth, root.clientWidth, root.scrollHeight, root.clientHeight] : null,
            body: [document.body.scrollWidth, document.body.clientWidth, document.body.scrollHeight, document.body.clientHeight],
            overflow,
            fatal: document.querySelector('.fatal-screen')?.innerText || '',
            bootVisible: visible(document.querySelector('.boot-screen')),
            viewport: [width, height]
          };
        }
        """,
        {"width": case.width, "height": case.height},
    )


def validate(case: Case, metrics: dict[str, Any], errors: list[str]) -> list[str]:
    failures: list[str] = []
    if errors:
        failures.append(f"errores JS: {errors}")
    if metrics["fatal"]:
        failures.append(f"pantalla fatal: {metrics['fatal'][:160]}")
    if not metrics["host"] or not metrics["root"]:
        failures.append("el entrypoint real no montó el gestor")
    if not metrics["standaloneClass"]:
        failures.append("el modo standalone no quedó marcado en el body")
    if metrics["oldShell"] or metrics["oldNavigation"]:
        failures.append("el shell heredado sigue visible")
    if metrics["bootVisible"]:
        failures.append("la pantalla de arranque no se retiró")
    if metrics["layout"] != case.layout or metrics["theme"] != case.theme:
        failures.append(f"preferencias incorrectas: {metrics['layout']}/{metrics['theme']}")
    if not metrics["managerSearch"] or metrics["managerRows"] < 1 or metrics["managerControls"] < 3:
        failures.append("faltan controles esenciales del gestor")
    if metrics["body"][0] > case.width + 1 or metrics["dimensions"] and metrics["dimensions"][0] > case.width + 1:
        failures.append(f"desbordamiento horizontal: {metrics['body']}/{metrics['dimensions']}")
    if metrics["overflow"]:
        failures.append(f"controles recortados: {metrics['overflow'][:4]}")
    return failures


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    entrypoint = transformed_entrypoint()
    results: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            for case in CASES:
                page = browser.new_page(viewport={"width": case.width, "height": case.height})
                preferences = {
                    "layout": case.layout,
                    "theme": case.theme,
                    "section": "panel" if case.layout == "zen-sidebar" else "downloads",
                    "accent": "#2f9bff",
                    "success": "#51c987",
                    "warning": "#e8b04c",
                    "danger": "#ef6b72",
                    "sidebarCollapsed": False,
                    "inspectorCollapsed": False,
                    "lowerPanelCollapsed": False,
                    "compactRows": False,
                    "filter": "all",
                    "category": "all",
                    "query": "",
                    "inspectorTab": "summary",
                }
                errors: list[str] = []
                page.on("pageerror", lambda error, target=errors: target.append(str(error)))
                page.set_content(inline_document(preferences), wait_until="load")
                page.add_script_tag(type="module", content=entrypoint)
                page.wait_for_selector(".dm-host", timeout=15_000)
                page.wait_for_timeout(160)
                metrics = inspect(page, case)
                failures = validate(case, metrics, errors)
                screenshot = SCREENSHOTS / f"{case.name}.png"
                page.screenshot(path=str(screenshot), full_page=False)
                results.append({
                    "case": asdict(case),
                    "passed": not failures,
                    "failures": failures,
                    "metrics": metrics,
                    "screenshot": str(screenshot.relative_to(ROOT)),
                })
                page.close()
        finally:
            browser.close()

    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        INDEX,
        ENTRYPOINT,
        ROOT / "app-ui/styles.css",
        *manager_source_files(),
    ])
    payload = {
        "gate": "phase16-standalone-app-smoke",
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": all(result["passed"] for result in results),
        "cases": results,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not payload["passed"]:
        for result in results:
            if not result["passed"]:
                print(f"FAIL {result['case']['name']}: {'; '.join(result['failures'])}")
        return 1
    print(f"OK: {len(results)} vistas del entrypoint real abren únicamente el gestor aislado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
