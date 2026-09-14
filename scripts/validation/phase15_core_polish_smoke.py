#!/usr/bin/env python3
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / 'app-ui/styles.css').read_text(encoding='utf-8')
JS_BASE = (ROOT / 'app-ui/main.js').read_text(encoding='utf-8')
for rel in ('app-ui/favicon.svg', 'app-ui/media-preview.svg'):
    data = 'data:image/svg+xml;base64,' + base64.b64encode((ROOT / rel).read_bytes()).decode()
    JS_BASE = JS_BASE.replace('./' + rel, data)
HTML = '<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div></body></html>'
steps = []

def add(name, passed, detail=None):
    steps.append({'name': name, 'passed': bool(passed), 'detail': detail})

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox', '--disable-dev-shm-usage'])

    def make_page(query, width, height):
        page = browser.new_page(viewport={'width': width, 'height': height}, screen={'width': width, 'height': height}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.add_style_tag(content=CSS)
        js = JS_BASE.replace("const qs = new URLSearchParams(window.location.search);", f"const qs = new URLSearchParams({query!r});", 1)
        page.add_script_tag(content=js)
        page.wait_for_selector('.desktop-shell')
        page.wait_for_timeout(250)
        return page, errors

    expected_scales = {(1920, 1080): 130, (2560, 1440): 150, (3840, 2160): 170}
    for (width, height), expected in expected_scales.items():
        page, errors = make_page('?preview=1&view=settings', width, height)
        resolved = int(page.locator('html').get_attribute('data-resolved-scale') or 0)
        add(f'auto scale {width}x{height}', resolved == expected, {'expected': expected, 'resolved': resolved})
        add(f'no page errors scale {width}x{height}', not errors, errors)
        page.close()

    page, errors = make_page('?preview=1&view=home', 1920, 1080)
    card = page.locator('[data-tool="downloads"]')
    before = card.bounding_box()
    card.hover()
    page.wait_for_timeout(150)
    after = card.bounding_box()
    track = page.locator('.tool-track').bounding_box()
    visible = bool(after and track and after['y'] >= track['y'] - 1)
    add('tool hover remains visible', visible, {'before': before, 'after': after, 'track': track})
    add('no page errors home hover', not errors, errors)
    page.close()

    browser.close()

rust = (ROOT / 'src-tauri/src/lib.rs').read_text(encoding='utf-8')
js = (ROOT / 'app-ui/main.js').read_text(encoding='utf-8')
css = (ROOT / 'app-ui/styles.css').read_text(encoding='utf-8')
config = json.loads((ROOT / 'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))
nsis = config['bundle']['windows']['nsis']
add('playlist terminal polling is stable', 'wasTerminal !== isTerminal' in js and "document.querySelector('#playlist-terminal-card')" in js)
add('appearance reaches embedded modules', "cacatools:appearance" in js and "querySelectorAll('.module-iframe')" in js)
add('global accent progress', 'background: var(--accent-gradient) !important' in css)
add('direct HTTP retry engine', 'request_download_response' in rust and 'run_curl_download_worker_inner' in rust and 'connect_timeout(Duration::from_secs(20))' in rust and 'Reconectando desde' in rust)
add('video concurrent fragments', '--concurrent-fragments' in rust and '--extractor-retries' in rust)
add('installer icon configured', nsis.get('installerIcon') == 'icons/icon.ico')
add('installer header configured', nsis.get('headerImage') == 'windows/nsis-header.bmp')
add('installer sidebar configured', nsis.get('sidebarImage') == 'windows/nsis-sidebar.bmp')
add('new C logo source', 'M385 132' in (ROOT / 'src-tauri/icons/app-icon.svg').read_text(encoding='utf-8') and 'm225 220' in (ROOT / 'src-tauri/icons/app-icon.svg').read_text(encoding='utf-8'))

report = {'suite': 'Phase 15 core polish, installer and download engine', 'passed': all(step['passed'] for step in steps), 'steps': steps}
out = ROOT / 'docs/tests/phase15-core-polish-smoke.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['passed'] else 1)
