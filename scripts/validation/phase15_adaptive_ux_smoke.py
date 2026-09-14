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
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML)
        page.add_style_tag(content=CSS)
        js = JS_BASE.replace("const qs = new URLSearchParams(window.location.search);", f"const qs = new URLSearchParams({query!r});", 1)
        page.add_script_tag(content=js)
        page.wait_for_selector('.desktop-shell')
        page.wait_for_timeout(500)
        return page, errors

    for width, height in ((1366, 768), (1920, 1080), (2560, 1440)):
        page, errors = make_page('?preview=1&view=downloads&dialog=playlist&playlist=queue', width, height)
        box = page.locator('.playlist-dialog').bounding_box()
        fits = bool(box and box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= width + 1 and box['y'] + box['height'] <= height + 1)
        add(f'playlist fits {width}x{height}', fits, box)
        add(f'no page errors {width}x{height}', not errors, errors)
        page.close()

    page, errors = make_page('?preview=1&view=downloads&dialog=playlist&playlist=selection', 1920, 1080)
    page.evaluate("window.__dialogIdentity = document.querySelector('.playlist-dialog')")
    before = page.locator('.selection-count').inner_text()
    page.locator('.playlist-select-item input').first.uncheck()
    after = page.locator('.selection-count').inner_text()
    same_dialog = page.evaluate("window.__dialogIdentity === document.querySelector('.playlist-dialog')")
    add('selection updates without rerender flicker', same_dialog and before != after, {'before': before, 'after': after, 'sameDialog': same_dialog})
    page.close()

    expectations = {
        'downloads': '.downloads-layout',
        'images': '.module-embed-shell',
        'documents': '.module-grid',
        'currency': '.currency-page-grid',
        'utilities': '.utility-grid',
    }
    for tool, selector in expectations.items():
        page, errors = make_page('?preview=1&view=home', 1920, 1080)
        page.locator(f'[data-tool="{tool}"] .primary-action').click()
        passed = page.locator(selector).count() == 1
        add(f'tool navigation {tool}', passed, selector)
        add(f'no page errors tool {tool}', not errors, errors)
        page.close()

    browser.close()

rust = (ROOT / 'src-tauri/src/lib.rs').read_text(encoding='utf-8')
add('lossy yt-dlp output reader', 'read_until(b\'\\n\'' in rust and 'String::from_utf8_lossy(&bytes)' in rust, None)
report = {'suite': 'Phase 15 adaptive UX and playlist stream', 'passed': all(step['passed'] for step in steps), 'steps': steps}
output = ROOT / 'docs/tests/phase15-adaptive-ux-smoke.json'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['passed'] else 1)
