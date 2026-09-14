#!/usr/bin/env python3
"""Deterministic visual/layout smoke gate for the Phase 16 download manager.

The fixture is rendered locally with demo data. No network request or native runtime is
required. This gate checks the two independent layouts, both color modes and the
responsive breakpoints that matter for the Windows desktop application.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from phase16_hashing import manager_source_files, source_fingerprint

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = ROOT / "docs" / "screenshots" / "phase16"
REPORT_PATH = ROOT / "docs" / "tests" / "phase16-visual-smoke.json"


@dataclass(frozen=True)
class VisualCase:
    name: str
    layout: str
    theme: str
    width: int
    height: int
    modal: str = ""


CASES = (
    VisualCase("command-center-dark-1920x1080", "command-center", "dark", 1920, 1080),
    VisualCase("zen-sidebar-dark-1920x1080", "zen-sidebar", "dark", 1920, 1080),
    VisualCase("command-center-light-1920x1080", "command-center", "light", 1920, 1080),
    VisualCase("zen-sidebar-light-1920x1080", "zen-sidebar", "light", 1920, 1080),
    VisualCase("command-center-dark-1366x768", "command-center", "dark", 1366, 768),
    VisualCase("zen-sidebar-dark-1366x768", "zen-sidebar", "dark", 1366, 768),
    VisualCase("command-center-dark-1024x720", "command-center", "dark", 1024, 720),
    VisualCase("zen-sidebar-dark-1024x720", "zen-sidebar", "dark", 1024, 720),
    VisualCase("command-center-dark-760x720", "command-center", "dark", 760, 720),
    VisualCase("zen-sidebar-light-760x720", "zen-sidebar", "light", 760, 720),
    VisualCase("command-center-dark-720x560", "command-center", "dark", 720, 560),
    VisualCase("zen-sidebar-dark-720x560", "zen-sidebar", "dark", 720, 560),
    VisualCase("torrent-dialog-dark-1024x720", "command-center", "dark", 1024, 720, "torrent"),
    VisualCase("torrent-dialog-light-760x720", "zen-sidebar", "light", 760, 720, "torrent"),
)


def render_fixture(case: VisualCase, destination: Path) -> None:
    subprocess.run(
        [
            "node",
            "scripts/validation/phase16_render_fixture.mjs",
            case.layout,
            case.theme,
            str(destination),
            case.modal,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def inspect_page(page: Any, case: VisualCase) -> dict[str, Any]:
    return page.evaluate(
        """
        ({ width, height, layout, isMobile }) => {
          const root = document.querySelector('.dm-root');
          const filterRow = document.querySelector('.dm-filter-row');
          const sidebar = document.querySelector('.dm-command-sidebar, .dm-zen-nav');
          const inspector = document.querySelector('.dm-inspector');
          const main = document.querySelector('.dm-command-main, .dm-zen-main');
          const modal = document.querySelector('.dm-modal');
          const visible = (element) => {
            if (!element) return false;
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.left < width;
          };
          const interactiveOverflow = [...document.querySelectorAll('button,select,input')]
            .filter(visible)
            .filter((element) => {
              const rect = element.getBoundingClientRect();
              return rect.right > width + 1 || rect.left < -1;
            })
            .map((element) => ({
              tag: element.tagName,
              text: (element.innerText || element.getAttribute('aria-label') || '').trim().slice(0, 80),
              rect: [element.getBoundingClientRect().left, element.getBoundingClientRect().right]
            }));
          const sidebarRect = sidebar?.getBoundingClientRect();
          const inspectorRect = inspector?.getBoundingClientRect();
          return {
            body: [document.body.scrollWidth, document.body.scrollHeight],
            root: root ? [root.scrollWidth, root.scrollHeight, root.clientWidth, root.clientHeight] : null,
            mainVisible: visible(main),
            filter: filterRow ? [filterRow.scrollWidth, filterRow.clientWidth] : null,
            nestedButtons: document.querySelectorAll('button button').length,
            layoutClass: root?.className || '',
            theme: document.querySelector('.dm-host')?.dataset.dmTheme || '',
            mobileSidebarClosed: !isMobile || !sidebarRect || sidebarRect.right <= 1,
            mobileInspectorClosed: !isMobile || !inspectorRect || inspectorRect.left >= width - 1,
            desktopSidebarVisible: isMobile || visible(sidebar),
            desktopInspectorVisible: isMobile || visible(inspector),
            quickActions: document.querySelectorAll('.dm-quick-actions button').length,
            commandWidgets: document.querySelectorAll('.dm-command-lower > article').length,
            modalVisible: !modal || visible(modal),
            modalRect: modal ? [modal.getBoundingClientRect().left, modal.getBoundingClientRect().right, modal.getBoundingClientRect().top, modal.getBoundingClientRect().bottom] : null,
            interactiveOverflow,
          };
        }
        """,
        {
            "width": case.width,
            "height": case.height,
            "layout": case.layout,
            "isMobile": case.width <= 820,
        },
    )


def validate_metrics(case: VisualCase, metrics: dict[str, Any], page_errors: list[str]) -> list[str]:
    failures: list[str] = []
    expected_class = "dm-command-center" if case.layout == "command-center" else "dm-zen-sidebar"
    if page_errors:
        failures.append(f"errores JS: {page_errors}")
    if not metrics["root"]:
        failures.append("no se encontró .dm-root")
        return failures
    if metrics["body"][0] > case.width + 1 or metrics["root"][0] > case.width + 1:
        failures.append(f"desbordamiento horizontal: body/root={metrics['body'][0]}/{metrics['root'][0]}")
    if not metrics["mainVisible"]:
        failures.append("el panel principal no está visible")
    if expected_class not in metrics["layoutClass"]:
        failures.append(f"layout incorrecto: {metrics['layoutClass']}")
    if metrics["theme"] != case.theme:
        failures.append(f"tema incorrecto: {metrics['theme']}")
    if metrics["nestedButtons"]:
        failures.append(f"HTML interactivo anidado: {metrics['nestedButtons']}")
    if metrics["filter"] and metrics["filter"][0] > metrics["filter"][1] + 1:
        failures.append(f"filtros recortados: {metrics['filter']}")
    if metrics["interactiveOverflow"]:
        failures.append(f"controles fuera de pantalla: {metrics['interactiveOverflow'][:5]}")
    if case.modal:
        if not metrics["modalRect"] or not metrics["modalVisible"]:
            failures.append(f"el diálogo {case.modal} no está visible")
        elif metrics["modalRect"][0] < -1 or metrics["modalRect"][1] > case.width + 1:
            failures.append(f"el diálogo {case.modal} está recortado horizontalmente: {metrics['modalRect']}")
    if case.width <= 820:
        if not metrics["mobileSidebarClosed"]:
            failures.append("la barra lateral móvil invade el contenido al iniciar")
        if not metrics["mobileInspectorClosed"]:
            failures.append("el inspector móvil invade el contenido al iniciar")
    else:
        if not metrics["desktopSidebarVisible"]:
            failures.append("la barra lateral de escritorio no está visible")
        if not metrics["desktopInspectorVisible"]:
            failures.append("el inspector de escritorio no está visible")
    if case.layout == "zen-sidebar" and metrics["quickActions"] < 4:
        failures.append("faltan acciones rápidas de Zen Sidebar")
    if case.layout == "command-center" and metrics["commandWidgets"] < 3:
        failures.append("faltan widgets inferiores de Command Center")
    return failures


def main() -> int:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="cacatools-phase16-") as temporary:
        temp_dir = Path(temporary)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                for case in CASES:
                    fixture = temp_dir / f"{case.name}.html"
                    render_fixture(case, fixture)
                    page = browser.new_page(viewport={"width": case.width, "height": case.height})
                    page_errors: list[str] = []
                    page.on("pageerror", lambda error, target=page_errors: target.append(str(error)))
                    page.set_content(fixture.read_text(encoding="utf-8"), wait_until="load")
                    page.wait_for_timeout(80)
                    metrics = inspect_page(page, case)
                    failures = validate_metrics(case, metrics, page_errors)
                    screenshot = SCREENSHOT_DIR / f"{case.name}.png"
                    page.screenshot(path=str(screenshot), full_page=False)
                    results.append(
                        {
                            "case": asdict(case),
                            "passed": not failures,
                            "failures": failures,
                            "metrics": metrics,
                            "screenshot": str(screenshot.relative_to(ROOT)),
                        }
                    )
                    page.close()
            finally:
                browser.close()

    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        ROOT / "scripts/validation/phase16_render_fixture.mjs",
        *manager_source_files(),
    ])
    report = {
        "gate": "phase16-visual-smoke",
        "sourceFiles": source_files,
        "sourceHash": source_hash,
        "passed": all(result["passed"] for result in results),
        "cases": results,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        for result in results:
            if not result["passed"]:
                print(f"FAIL {result['case']['name']}: {'; '.join(result['failures'])}")
        return 1
    print(f"OK: {len(results)} vistas Phase16 sin desbordamientos ni controles recortados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
