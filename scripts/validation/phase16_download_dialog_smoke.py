#!/usr/bin/env python3
"""Exercise the real Phase 16 add-download dialog through the actual app entrypoint.

This gate covers direct files, single media and playlists, including selectors and
compact-window behavior. It reuses the standalone entrypoint harness because the
CI sandbox blocks localhost and file:// module loading.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from phase16_hashing import manager_source_files, source_fingerprint

from phase16_standalone_app_smoke import (
    ENTRYPOINT,
    IMPORT_RE,
    ROOT,
    SCREENSHOTS,
    inline_document,
    module_url,
)

REPORT = ROOT / "docs/tests/phase16-download-dialog-smoke.json"


@dataclass(frozen=True)
class Case:
    name: str
    dialog: str
    width: int
    height: int


CASES = (
    Case("dialog-direct-1280x800", "direct", 1280, 800),
    Case("dialog-video-1440x900", "video", 1440, 900),
    Case("dialog-page-resources-1280x800", "page", 1280, 800),
    Case("dialog-page-alternatives-1280x800", "page-empty", 1280, 800),
    Case("dialog-page-alternatives-compact-720x560", "page-empty", 720, 560),
    Case("dialog-playlist-1440x900", "playlist", 1440, 900),
    Case("dialog-playlist-compact-720x560", "playlist", 720, 560),
)


def transformed_entrypoint(dialog: str) -> str:
    source = ENTRYPOINT.read_text(encoding="utf-8")
    cache: dict[Path, str] = {}

    def replace_import(match: re.Match[str]) -> str:
        dependency = (ENTRYPOINT.parent / match.group("path")).resolve()
        return f"{match.group('prefix')}{match.group('quote')}{module_url(dependency, cache)}{match.group('quote')}"

    source = IMPORT_RE.sub(replace_import, source)
    source = source.replace("const previewMode = qs.has('preview');", "const previewMode = true;")
    source = source.replace("const previewDialog = qs.get('dialog') || '';", f"const previewDialog = {json.dumps(dialog)};")
    if "const previewMode = true;" not in source or f"const previewDialog = {json.dumps(dialog)};" not in source:
        raise RuntimeError("No se pudo configurar el diálogo determinista del entrypoint real.")
    return source


def preferences() -> dict[str, Any]:
    return {
        "layout": "command-center",
        "theme": "dark",
        "section": "downloads",
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


def common_metrics(page: Any, case: Case) -> dict[str, Any]:
    return page.evaluate(
        """
        ({ width, height }) => {
          const dialog = document.querySelector('.download-dialog');
          const rect = dialog?.getBoundingClientRect();
          const visible = (element) => {
            if (!element) return false;
            const box = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return box.width > 0 && box.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
          };
          const controls = [...document.querySelectorAll('.download-dialog button, .download-dialog input, .download-dialog select')]
            .filter(visible)
            .map((element) => ({
              label: (element.innerText || element.value || element.getAttribute('aria-label') || '').trim().slice(0, 72),
              rect: element.getBoundingClientRect()
            }));
          const horizontalOverflow = controls
            .filter(({ rect: item }) => item.left < -1 || item.right > width + 1)
            .map(({ label, rect: item }) => ({ label, left: Math.round(item.left), right: Math.round(item.right) }));
          return {
            dialog: Boolean(dialog),
            dialogRect: rect ? [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)] : null,
            dialogScroll: dialog ? [dialog.scrollWidth, dialog.clientWidth, dialog.scrollHeight, dialog.clientHeight] : null,
            documentScroll: [document.documentElement.scrollWidth, document.documentElement.clientWidth],
            horizontalOverflow,
            confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null,
            fatal: document.querySelector('.fatal-screen')?.innerText || '',
            viewport: [width, height]
          };
        }
        """,
        {"width": case.width, "height": case.height},
    )


def exercise(page: Any, case: Case) -> dict[str, Any]:
    if case.dialog == "direct":
        before = page.evaluate(
            """() => ({
              result: Boolean(document.querySelector('.direct-result')),
              filename: document.querySelector('#direct-filename')?.value || '',
              action: document.querySelector('.confirm-download')?.textContent?.trim() || ''
            })"""
        )
        page.click(".confirm-download")
        page.wait_for_timeout(60)
        return {"before": before, "closedAfterConfirm": not page.locator(".download-dialog").count()}

    if case.dialog == "video":
        before = page.evaluate(
            """() => ({
              result: Boolean(document.querySelector('.video-result')),
              thumbnail: Boolean(document.querySelector('.media-thumbnail img')),
              thumbnailFallback: document.querySelector('.media-thumbnail')?.classList.contains('thumbnail-load-failed') ?? false,
              formatButtons: document.querySelectorAll('[data-media-format]').length,
              qualityOptions: document.querySelectorAll('#media-format-select option').length,
              outputOptions: document.querySelectorAll('#media-output-mode option').length,
              title: document.querySelector('.video-result h3')?.textContent?.trim() || ''
            })"""
        )
        buttons = page.locator("[data-media-format]")
        if buttons.count() > 1:
            buttons.nth(1).click()
            page.wait_for_timeout(60)
        after = page.evaluate(
            """() => ({
              selectedButtons: document.querySelectorAll('[data-media-format].selected').length,
              selectedQuality: document.querySelector('#media-format-select')?.value || '',
              output: document.querySelector('#media-output-mode')?.value || ''
            })"""
        )
        return {"before": before, "afterFormatSelection": after}

    if case.dialog == "page":
        before = page.evaluate(
            """() => ({
              result: Boolean(document.querySelector('.page-discovery-result')),
              items: document.querySelectorAll('.page-resource-item').length,
              selected: document.querySelectorAll('.page-resource-item input:checked').length,
              numbered: [...document.querySelectorAll('.page-resource-number')].every((node, index) => node.textContent.trim() === String(index + 1)),
              confirmText: document.querySelector('.confirm-download')?.textContent?.trim() || '',
              confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
            })"""
        )
        select_all = page.locator("#page-select-all")
        if select_all.count():
            select_all.check()
            page.wait_for_timeout(25)
            select_all.uncheck()
            page.wait_for_timeout(40)
        after_none = page.evaluate(
            """() => ({
              selected: document.querySelectorAll('.page-resource-item input:checked').length,
              confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
            })"""
        )
        if select_all.count():
            select_all.check()
            page.wait_for_timeout(40)
        after_all = page.evaluate(
            """() => ({
              selected: document.querySelectorAll('.page-resource-item input:checked').length,
              confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null,
              confirmText: document.querySelector('.confirm-download')?.textContent?.trim() || ''
            })"""
        )
        return {"before": before, "afterNone": after_none, "afterAll": after_all}

    if case.dialog == "page-empty":
        before = page.evaluate(
            """() => ({
              result: Boolean(document.querySelector('.page-discovery-result')),
              empty: Boolean(document.querySelector('.page-resource-empty')),
              searchButton: Boolean(document.querySelector('.page-search-alternatives')),
              queryText: document.querySelector('.page-discovery-hero h3')?.textContent?.trim() || '',
              confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
            })"""
        )
        page.click(".page-search-alternatives")
        page.wait_for_timeout(110)
        after_search = page.evaluate(
            """() => ({
              alternatives: document.querySelectorAll('.page-alternative-card').length,
              similarity: document.querySelector('.page-alternative-card em')?.textContent?.trim() || '',
              analyzeButtons: document.querySelectorAll('.page-analyze-alternative').length,
              busy: Boolean(document.querySelector('.page-alternative-loading'))
            })"""
        )
        page.click(".page-analyze-alternative")
        page.wait_for_timeout(110)
        after_analyze = page.evaluate(
            """() => ({
              videoResult: Boolean(document.querySelector('.video-result')),
              title: document.querySelector('.video-result h3')?.textContent?.trim() || '',
              formats: document.querySelectorAll('[data-media-format]').length,
              confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
            })"""
        )
        return {"before": before, "afterSearch": after_search, "afterAnalyze": after_analyze}

    before = page.evaluate(
        """() => ({
          result: Boolean(document.querySelector('.playlist-selection-view')),
          items: document.querySelectorAll('.playlist-select-item').length,
          numbered: [...document.querySelectorAll('.playlist-select-item > b')].every((node, index) => node.textContent.trim() === `#${index + 1}`),
          selected: document.querySelectorAll('.playlist-select-item input:checked').length,
          title: document.querySelector('.playlist-heading h3')?.textContent?.trim() || '',
          formatOptions: document.querySelectorAll('#playlist-format option').length
        })"""
    )
    first = page.locator(".playlist-select-item input").first
    if first.count():
        first.uncheck()
        page.wait_for_timeout(40)
    after_one = page.evaluate(
        """() => ({
          selected: document.querySelectorAll('.playlist-select-item input:checked').length,
          countText: document.querySelector('.selection-count')?.textContent?.trim() || '',
          confirmText: document.querySelector('.confirm-download')?.textContent?.trim() || '',
          confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
        })"""
    )
    select_all = page.locator(".playlist-select-all input")
    if select_all.count():
        # From an indeterminate state the first normal click selects all; the
        # second click clears all, matching native checkbox behavior.
        select_all.click()
        page.wait_for_timeout(30)
        select_all.click()
        page.wait_for_timeout(40)
    after_none = page.evaluate(
        """() => ({
          selected: document.querySelectorAll('.playlist-select-item input:checked').length,
          confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
        })"""
    )
    if select_all.count():
        select_all.check()
        page.wait_for_timeout(40)
    after_all = page.evaluate(
        """() => ({
          selected: document.querySelectorAll('.playlist-select-item input:checked').length,
          confirmDisabled: document.querySelector('.confirm-download')?.disabled ?? null
        })"""
    )
    return {"before": before, "afterOne": after_one, "afterNone": after_none, "afterAll": after_all}


def validate(case: Case, common: dict[str, Any], interaction: dict[str, Any], errors: list[str]) -> list[str]:
    failures: list[str] = []
    if errors:
        failures.append(f"errores JS: {errors}")
    if common["fatal"]:
        failures.append(f"pantalla fatal: {common['fatal'][:160]}")
    if not common["dialog"]:
        failures.append("el diálogo real no abrió")
    if common["documentScroll"][0] > case.width + 1 or common["dialogScroll"][0] > common["dialogScroll"][1] + 1:
        failures.append(f"desbordamiento horizontal: {common['documentScroll']}/{common['dialogScroll']}")
    if common["horizontalOverflow"]:
        failures.append(f"controles cortados: {common['horizontalOverflow'][:4]}")

    before = interaction.get("before", {})
    if case.dialog == "direct":
        if not before.get("result") or not before.get("filename") or before.get("action") != "Añadir archivo":
            failures.append(f"vista directa incompleta: {before}")
        if not interaction.get("closedAfterConfirm"):
            failures.append("la confirmación directa no cerró el diálogo en preview")
    elif case.dialog == "video":
        if not before.get("result") or not before.get("thumbnail") or before.get("formatButtons", 0) < 2:
            failures.append(f"vista de vídeo incompleta: {before}")
        if not before.get("thumbnailFallback"):
            failures.append("la miniatura inválida no activó el fallback visual")
        if before.get("qualityOptions", 0) < 2 or before.get("outputOptions", 0) < 4:
            failures.append(f"selectores multimedia incompletos: {before}")
        after = interaction.get("afterFormatSelection", {})
        if after.get("selectedButtons") != 1 or not after.get("selectedQuality"):
            failures.append(f"selección de formato inestable: {after}")
    elif case.dialog == "page":
        if not before.get("result") or before.get("items", 0) < 3 or not before.get("numbered"):
            failures.append(f"explorador de página incompleto: {before}")
        if before.get("selected", 0) < 1 or before.get("confirmDisabled") is not False:
            failures.append(f"selección inicial de recursos inválida: {before}")
        if interaction.get("afterNone", {}).get("selected") != 0 or interaction.get("afterNone", {}).get("confirmDisabled") is not True:
            failures.append(f"el explorador no bloquea una cola vacía: {interaction.get('afterNone')}")
        if interaction.get("afterAll", {}).get("selected") != before.get("items") or interaction.get("afterAll", {}).get("confirmDisabled") is not False:
            failures.append(f"seleccionar todos los recursos falló: {interaction.get('afterAll')}")
    elif case.dialog == "page-empty":
        if not before.get("result") or not before.get("empty") or not before.get("searchButton"):
            failures.append(f"estado vacío de exploración incompleto: {before}")
        if before.get("confirmDisabled") is not True:
            failures.append(f"el estado vacío permite confirmar sin selección: {before}")
        after_search = interaction.get("afterSearch", {})
        if after_search.get("alternatives", 0) < 3 or after_search.get("analyzeButtons", 0) < 3 or after_search.get("busy"):
            failures.append(f"búsqueda de alternativas incompleta: {after_search}")
        if "% similar" not in after_search.get("similarity", ""):
            failures.append(f"la alternativa no muestra similitud: {after_search}")
        after_analyze = interaction.get("afterAnalyze", {})
        if not after_analyze.get("videoResult") or after_analyze.get("formats", 0) < 3 or after_analyze.get("confirmDisabled") is not False:
            failures.append(f"analizar alternativa no abrió el flujo multimedia: {after_analyze}")
    else:
        if not before.get("result") or before.get("items", 0) < 3 or not before.get("numbered"):
            failures.append(f"playlist incompleta: {before}")
        if before.get("formatOptions", 0) < 4:
            failures.append("faltan formatos de playlist")
        if interaction.get("afterOne", {}).get("selected") != before.get("selected", 0) - 1:
            failures.append(f"la selección individual no actualizó la lista: {interaction.get('afterOne')}")
        if interaction.get("afterNone", {}).get("selected") != 0 or interaction.get("afterNone", {}).get("confirmDisabled") is not True:
            failures.append(f"el estado sin selección no bloquea la descarga: {interaction.get('afterNone')}")
        if interaction.get("afterAll", {}).get("selected") != before.get("items") or interaction.get("afterAll", {}).get("confirmDisabled") is not False:
            failures.append(f"seleccionar todo no restauró la playlist: {interaction.get('afterAll')}")
    return failures


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
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
                errors: list[str] = []
                page.on("pageerror", lambda error, target=errors: target.append(str(error)))
                page.set_content(inline_document(preferences()), wait_until="load")
                page.add_script_tag(type="module", content=transformed_entrypoint(case.dialog))
                page.wait_for_selector(".download-dialog", timeout=15_000)
                page.wait_for_timeout(120)
                common = common_metrics(page, case)
                interaction = exercise(page, case)
                failures = validate(case, common, interaction, errors)
                screenshot = SCREENSHOTS / f"{case.name}.png"
                page.screenshot(path=str(screenshot), full_page=False)
                results.append({
                    "case": asdict(case),
                    "passed": not failures,
                    "failures": failures,
                    "metrics": common,
                    "interaction": interaction,
                    "screenshot": str(screenshot.relative_to(ROOT)),
                })
                page.close()
        finally:
            browser.close()

    source_files, source_hash = source_fingerprint([
        Path(__file__),
        ROOT / "scripts/validation/phase16_hashing.py",
        ROOT / "scripts/validation/phase16_standalone_app_smoke.py",
        ROOT / "index.html",
        ENTRYPOINT,
        ROOT / "app-ui/styles.css",
        *manager_source_files(),
    ])
    payload = {
        "gate": "phase16-download-dialog-smoke",
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
    print(f"OK: {len(results)} flujos reales del diálogo de descarga funcionan y responden en compacto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
