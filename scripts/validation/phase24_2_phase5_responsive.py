#!/usr/bin/env python3
"""Measured responsive gate for CacaTools Fase 11.6."""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "tests" / "phase24-2-phase5-responsive.json"
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


def main() -> int:
    css = (ROOT / "app-ui/download-manager/styles.css").read_text(encoding="utf-8")
    html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<style>html,body,#fixture{{width:100%;height:100%;margin:0;overflow:hidden}}{css}</style>'
        '</head><body><main id="fixture"></main></body></html>'
    )
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

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
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.add_init_script(
            "(() => { const values = new Map([['cacatools.download-manager.v2', "
            "JSON.stringify({section:'downloads',filter:'all',category:'all',query:''})]]); "
            "Object.defineProperty(window, 'localStorage', {configurable:true, value: "
            "{getItem:(key)=>values.get(key)||null,setItem:(key,value)=>values.set(key,String(value)), "
            "removeItem:(key)=>values.delete(key),clear:()=>values.clear(),key:(index)=>Array.from(values.keys())[index]||null, get length(){return values.size;}}}); })();"
        )
        page.set_content(html, wait_until="load")
        page.evaluate("""()=>{const values=new Map([['cacatools.download-manager.v2',JSON.stringify({section:'downloads',filter:'all',category:'all',query:''})]]);Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:(key)=>values.get(key)||null,setItem:(key,value)=>values.set(key,String(value)),removeItem:(key)=>values.delete(key),clear:()=>values.clear(),key:(index)=>Array.from(values.keys())[index]||null,get length(){return values.size;}}});}""")
        page.add_script_tag(content=browser_bundle())

        render = """([size,section='downloads']) => {
          localStorage.setItem('cacatools.download-manager.v2', JSON.stringify({section,filter:'all',category:'all',query:''}));
          if (typeof syncPreferences === 'function') syncPreferences({section,filter:'all',category:'all',query:''});
          const jobs=Array.from({length:size},(_,i)=>({
            id:i+1,title:i===0?'Un título deliberadamente largo para comprobar que el contenido no invade progreso ni acciones '.repeat(3):`video-${i+1}.mp4`,
            detail:i%4===0?'Descargando':'En cola',status:section==='completed'?'completed':(i%4===0?'running':'queued'),progress:section==='completed'?100:(i%4===0?37:0),
            downloaded_bytes:section==='completed'?100_000_000:(i%4===0?37_000_000:0),total_bytes:100_000_000,speed_bps:i%4===0?2_000_000:0,
            eta_seconds:i%4===0?38:null,kind:'video',engine:'yt-dlp',category:i%2?'Video':'HTTP',origin:'yt-dlp',
            thumbnail:'',updated_at:'2026-08-09T20:00:00Z'
          }));
          const context={snapshot:{jobs,playlist_batches:[]},pendingJobs:[],invoke:async()=>null,
            runtimeStatus:{mode:'local'},mediaRuntimeStatus:{},downloadDirectory:'C:\\Downloads',schedules:[],
            onNewDownload:()=>{},onAnalyzeSource:async()=>{},onRefresh:async()=>{},onToast:()=>{},onSection:()=>{},onRerender:()=>{}};
          document.querySelector('#fixture').innerHTML=renderDownloadManager(context);
          const root=document.querySelector('.dm-root'),top=document.querySelector('.dm-zen-top'),head=document.querySelector('.dm-zen-head-actions'),secondary=document.querySelector('.dm-zen-secondary-row'),helpers=document.querySelector('.dm-zen-secondary-actions'),toolbarActions=document.querySelector('.dm-zen-secondary-row>.dm-zen-toolbar-actions'),area=document.querySelector('.dm-download-area'),scroll=document.querySelector('.dm-download-scroll'),row=document.querySelector('.dm-download-item'),progress=document.querySelector('.dm-item-progress'),body=document.querySelector('.dm-item-body');
          const box=(node)=>node?(()=>{const r=node.getBoundingClientRect();return {x:+r.x.toFixed(2),y:+r.y.toFixed(2),width:+r.width.toFixed(2),height:+r.height.toFixed(2)}})():null;
          const secondaryBox=box(secondary),helpersBox=box(helpers),toolbarActionsBox=box(toolbarActions);
          const categoryToggle=document.querySelector('[data-dm-category-toggle]');
          const categoryOptions=[...document.querySelectorAll('[data-dm-category-option]')].map((option)=>({value:option.dataset.dmCategoryOption||'',label:option.textContent.trim()}));
          const headerText=top?.textContent||'';
          const controls=[...document.querySelectorAll('.dm-zen-secondary-row>.dm-zen-secondary-actions .dm-helper-chips button,.dm-zen-secondary-row>.dm-zen-toolbar-actions .dm-selection-toggle,.dm-zen-secondary-row>.dm-zen-toolbar-actions .dm-category-toggle,.dm-zen-secondary-row>.dm-zen-toolbar-actions .dm-details-toggle')];
          const controlMetrics=controls.map((node)=>{const style=getComputedStyle(node);const rect=node.getBoundingClientRect();return {label:node.textContent.trim(),display:style.display,height:+rect.height.toFixed(2),width:+rect.width.toFixed(2),x:+rect.x.toFixed(2),y:+rect.y.toFixed(2),visible:style.display!=='none'&&style.visibility!=='hidden'&&rect.width>0&&rect.height>0}});
          const heights=controlMetrics.map((control)=>control.height);
          return {size,viewport:{width:innerWidth,height:innerHeight},header:box(top),actions:box(head),secondary:secondaryBox,helpers:helpersBox,toolbarActions:toolbarActionsBox,groupsSameRow:Boolean(helpersBox&&toolbarActionsBox&&Math.abs(helpersBox.y-toolbarActionsBox.y)<8&&helpersBox.x<toolbarActionsBox.x),area:box(area),row:box(row),progress:box(progress),body:box(body),rootOverflow:root?root.scrollWidth-root.clientWidth:null,areaOverflow:area?area.scrollWidth-area.clientWidth:null,rows:document.querySelectorAll('.dm-download-item').length,total:Number(scroll?.dataset.dmVirtualTotal||size),virtual:Boolean(scroll?.dataset.dmVirtualList),filters:document.querySelectorAll('[data-dm-filter]').length,helpersCount:document.querySelectorAll('.dm-helper-chips [data-dm-paste-link],.dm-helper-chips [data-dm-add-torrent],.dm-helper-chips [data-dm-new-download],.dm-helper-chips [data-dm-focus-unified]').length,categoryOptions,categoryLabel:categoryToggle?.querySelector('[data-dm-category-label]')?.textContent.trim()||'',categoryTechnicalText:/Estado y tipo|Tipo [/] origen/.test(headerText),controlMetrics,controlHeights:heights,controlsVisible:controlMetrics.every((control)=>control.visible),sameControlHeight:heights.length===7&&heights.every((height)=>height===heights[0]),leftControlLabels:controlMetrics.slice(0,4).map((control)=>control.label),rightControlLabels:controlMetrics.slice(4).map((control)=>control.label)};
        }"""

        samples: dict[str, Any] = {}
        for width, height in ((1600, 900), (1180, 720), (980, 780), (800, 620)):
            page.set_viewport_size({"width": width, "height": height})
            result = page.evaluate(render, [24, "downloads"])
            samples[f"{width}x{height}"] = result
            check(f"Sin overflow horizontal en {width}x{height}", result["rootOverflow"] == 0 and result["areaOverflow"] == 0, result)
            check(f"Conserva las cuatro acciones en {width}x{height}", result["helpersCount"] == 4, result["helpersCount"])
            check(f"Los siete controles de cabecera son visibles en {width}x{height}", result["controlsVisible"], result["controlMetrics"])
            check(f"Los siete controles tienen la misma altura en {width}x{height}", result["sameControlHeight"], result["controlHeights"])
            check(f"Usa un único selector de categorías en {width}x{height}", result["filters"] == 0 and len(result["categoryOptions"]) >= 6 and result["categoryLabel"] == "Todas las categorías" and any(option["value"] == "all" and option["label"] == "Todo" for option in result["categoryOptions"]) and not result["categoryTechnicalText"], result)
            if width >= 1180:
                check(f"Los dos grupos de acciones comparten la segunda fila en {width}x{height}", result["groupsSameRow"], result)
            check(f"Progreso permanece dentro de la fila en {width}x{height}", result["progress"] and result["progress"]["x"] >= result["row"]["x"] and result["progress"]["x"] + result["progress"]["width"] <= result["row"]["x"] + result["row"]["width"] + 1, result)
            check(f"Título largo no invade la fila en {width}x{height}", result["body"] and result["body"]["width"] > 0, result)

        page.set_viewport_size({"width": 1600, "height": 900})
        large = page.evaluate(render, [1000, "completed"])
        check("Virtualización selectiva sigue activa para 1000 trabajos", large["virtual"] and large["rows"] < large["total"], large)
        check("La ventana virtual conserva un número acotado de filas", large["rows"] <= 100, large)

        resize_sequence: list[dict[str, Any]] = []
        for width, height in ((1180, 780), (980, 780), (800, 620), (1600, 900)):
            page.set_viewport_size({"width": width, "height": height})
            resize_sequence.append(page.evaluate("""()=>({width:innerWidth,height:innerHeight,rootOverflow:document.querySelector('.dm-root')?.scrollWidth-document.querySelector('.dm-root')?.clientWidth||0,rows:document.querySelectorAll('.dm-download-item').length})"""))
        check("Resize agrupado conserva el DOM sin overflow", all(item["rootOverflow"] == 0 for item in resize_sequence), resize_sequence)

        browser.close()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"phase": "11.6", "checks": checks, "samples": samples, "passed": all(item["pass"] for item in checks)}
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "checks": len(checks), "report": str(REPORT)}, ensure_ascii=False))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
