#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'screenshots' / 'phase17-dialogs'
REPORT = ROOT / 'docs' / 'tests' / 'phase17-dialog-visual-smoke.json'
CASES = [
    ('command-dark-video-1180x780', 'command-center', 'dark', 'video', 'selection', 1180, 780),
    ('command-light-video-1180x780', 'command-center', 'light', 'video', 'selection', 1180, 780),
    ('command-dark-playlist-selection-1180x780', 'command-center', 'dark', 'playlist', 'selection', 1180, 780),
    ('command-dark-playlist-queue-1180x780', 'command-center', 'dark', 'playlist', 'queue', 1180, 780),
    ('zen-dark-video-1180x780', 'zen-sidebar', 'dark', 'video', 'selection', 1180, 780),
    ('zen-light-playlist-selection-1180x780', 'zen-sidebar', 'light', 'playlist', 'selection', 1180, 780),
    ('zen-dark-playlist-queue-1180x780', 'zen-sidebar', 'dark', 'playlist', 'queue', 1180, 780),
    ('command-light-direct-1180x780', 'command-center', 'light', 'direct', 'selection', 1180, 780),
]
OUT.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)
results = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--disable-gpu', '--no-sandbox'])
    for name, layout, theme, dialog, stage, width, height in CASES:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, dir=ROOT) as tmp:
            html_path = Path(tmp.name)
        subprocess.run(['node', 'scripts/validation/phase17_dialog_fixture.mjs', layout, theme, dialog, stage, str(html_path)], cwd=ROOT, check=True)
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(html_path.read_text(encoding='utf-8'), wait_until='load')
        page.wait_for_timeout(900)
        metrics = page.evaluate('''({width,height})=>{const q=s=>document.querySelector(s),r=e=>e?.getBoundingClientRect();const dialog=q('.download-dialog-v2');const body=q('.dialog-body');return {dialog:r(dialog),body:r(body),document:[document.body.scrollWidth,document.body.scrollHeight],nested:document.querySelectorAll('button button').length,entry:!!q('.dialog-unified-entry'),hero:!!q('.analysis-v2-hero,.direct-hero,.playlist-v2-hero,.playlist-summary-card'),alternatives:document.querySelectorAll('.analysis-alternative,.playlist-side-alternatives>button').length,playlistSide:!!q('.playlist-queue-side'),footer:!!q('.dialog-footer'),overflow:dialog?{sw:dialog.scrollWidth,cw:dialog.clientWidth,sh:dialog.scrollHeight,ch:dialog.clientHeight}:null,outside:[...document.querySelectorAll('.download-dialog-v2 button,.download-dialog-v2 input,.download-dialog-v2 select')].filter(e=>{const x=r(e),s=getComputedStyle(e);return x&&s.display!=='none'&&(x.right>width+1||x.left<-1||x.top<-1||x.bottom>height+1)&&!e.closest('.dialog-body')}).length}}''', {'width': width, 'height': height})
        failures = []
        if errors: failures.append('JS: ' + str(errors))
        if not metrics['dialog'] or metrics['dialog']['width'] < 700: failures.append('dialog missing or too small')
        if metrics['dialog'] and (metrics['dialog']['right'] > width + 1 or metrics['dialog']['bottom'] > height + 1): failures.append('dialog outside viewport')
        if metrics['nested']: failures.append('nested buttons')
        if not metrics['hero']: failures.append('analysis/playlist hero missing')
        if not metrics['footer']: failures.append('dialog footer missing')
        if dialog == 'playlist' and stage == 'queue' and (not metrics['playlistSide'] or metrics['alternatives'] < 3): failures.append('playlist alternatives/history panel missing')
        if dialog != 'playlist' or stage != 'queue':
            if not metrics['entry']: failures.append('unified dialog entry missing')
        if metrics['outside']: failures.append(f"{metrics['outside']} fixed controls outside viewport")
        page.screenshot(path=str(OUT / f'{name}.png'), full_page=False)
        results.append({'name': name, 'layout': layout, 'theme': theme, 'dialog': dialog, 'stage': stage, 'viewport': [width, height], 'metrics': metrics, 'page_errors': errors, 'failures': failures, 'pass': not failures})
        page.close()
        html_path.unlink(missing_ok=True)
    browser.close()
REPORT.write_text(json.dumps({'passed': all(item['pass'] for item in results), 'cases': results}, indent=2, ensure_ascii=False), encoding='utf-8')
if not all(item['pass'] for item in results):
    print(json.dumps(results, indent=2, ensure_ascii=False))
    raise SystemExit(1)
print(f'OK: {len(results)} visual cases de diálogos Phase 17')
