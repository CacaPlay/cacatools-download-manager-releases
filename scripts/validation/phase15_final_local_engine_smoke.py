from pathlib import Path
from playwright.sync_api import sync_playwright
import base64, json, time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'screenshots'
REPORT = ROOT / 'docs' / 'tests' / 'phase15-final-local-engine-smoke.json'
OUT.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)
CSS = (ROOT / 'app-ui' / 'styles.css').read_text(encoding='utf-8')
JS_SOURCE = (ROOT / 'app-ui' / 'main.js').read_text(encoding='utf-8')
LOGO = 'data:image/svg+xml;base64,' + base64.b64encode((ROOT / 'app-ui' / 'favicon.svg').read_bytes()).decode()
MEDIA = 'data:image/svg+xml;base64,' + base64.b64encode((ROOT / 'app-ui' / 'media-preview.svg').read_bytes()).decode()


def html_for(query: str) -> str:
    js = JS_SOURCE.replace(
        'const qs = new URLSearchParams(window.location.search);',
        f'const qs = new URLSearchParams({query!r});',
        1,
    )
    js = js.replace('./app-ui/favicon.svg', LOGO).replace('./app-ui/media-preview.svg', MEDIA)
    return f'''<!doctype html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CacaTools</title><style>{CSS}</style></head><body><div id="app"></div><script>{js}</script></body></html>'''


def check(condition, label, results, detail=None):
    results.append({'name': label, 'pass': bool(condition), 'detail': detail})
    if not condition:
        raise AssertionError(f'{label}: {detail}')


results = []
screenshots = []

def settle(page, delay=520):
    page.evaluate("document.documentElement.dataset.motion='off'; document.querySelectorAll('.button-ripple').forEach((node)=>node.remove())")
    page.wait_for_timeout(delay)

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path='/usr/bin/chromium',
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
    )

    # Automatic scale contracts.
    for width, height, expected in [(1920, 1080, '130'), (2560, 1440, '150'), (3840, 2160, '170')]:
        context = browser.new_context(viewport={'width': width, 'height': height}, screen={'width': width, 'height': height})
        page = context.new_page()
        page.set_content(html_for('?preview=1&view=settings'), wait_until='load')
        page.wait_for_selector('.settings-view')
        resolved = page.evaluate("document.documentElement.dataset.resolvedScale")
        check(resolved == expected, f'Escala automática {width}x{height}', results, resolved)
        context.close()

    # QHD home with final logo and cards.
    context = browser.new_context(viewport={'width': 2560, 'height': 1440}, screen={'width': 2560, 'height': 1440})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.set_content(html_for('?preview=1&view=home'), wait_until='load')
    page.wait_for_selector('.tool-card')
    page.wait_for_timeout(550)
    cards = page.locator('.tool-card')
    first_box = cards.first.bounding_box()
    check(cards.count() >= 3, 'Carrusel principal renderizado', results, cards.count())
    check(first_box and first_box['height'] >= 270, 'Tarjetas principales grandes', results, first_box)
    logo_src = page.locator('.brand img').get_attribute('src')
    check(bool(logo_src and 'data:image/svg+xml' in logo_src), 'Logo vectorial real en la interfaz', results)
    home_path = OUT / 'final-01-inicio-qhd.png'
    page.screenshot(path=str(home_path))
    screenshots.append(str(home_path))

    # Navigation from main tools.
    page.locator('[data-tool="downloads"] .primary-action').click()
    page.wait_for_selector('.downloads-layout')
    check(page.locator('.downloads-layout').count() == 1, 'Tarjeta Descargas navega', results)
    page.evaluate("appState.activeSection='Inicio'; appState.activeTool=null; render()")
    page.locator('[data-tool="currency"] .primary-action').click()
    page.wait_for_selector('.currency-page-grid')
    check(page.locator('.currency-page-grid').count() == 1, 'Tarjeta Divisas navega', results)

    # Global palette propagation.
    page.evaluate("appState.activeSection='Ajustes'; appState.activeTool=null; render()")
    page.wait_for_selector('.palette-option[data-preset="rose"]')
    before = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent-base').trim()")
    page.locator('.palette-option[data-preset="rose"]').click()
    after = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent-base').trim()")
    check(before.lower() != after.lower() and after.lower() == '#e45e9d', 'Paleta global cambia el acento', results, {'before': before, 'after': after})
    page.locator('.palette-option[data-preset="caca-blue"]').click()
    settle(page)
    settings_path = OUT / 'final-06-ajustes-qhd.png'
    page.screenshot(path=str(settings_path))
    screenshots.append(str(settings_path))
    context.close()

    # Real queue presentation and smoothly advancing progress.
    context = browser.new_context(viewport={'width': 2560, 'height': 1440}, screen={'width': 2560, 'height': 1440})
    page = context.new_page()
    page.set_content(html_for('?preview=1&view=downloads'), wait_until='load')
    page.wait_for_selector('.download-item')
    initial = page.locator('.download-item').first.get_attribute('data-target-progress')
    settle(page)
    downloads_path = OUT / 'final-02-descargas-qhd.png'
    page.screenshot(path=str(downloads_path))
    screenshots.append(str(downloads_path))
    page.evaluate("""
      appState.snapshot.jobs[0].progress = 100;
      appState.snapshot.jobs[0].downloaded_bytes = appState.snapshot.jobs[0].total_bytes;
      appState.snapshot.jobs[0].speed_bps = 0;
      appState.snapshot.jobs[0].eta_seconds = 0;
      patchDynamicSnapshot();
    """)
    page.wait_for_timeout(40)
    early = page.locator('.download-item').first.locator('.download-percent').inner_text()
    page.wait_for_timeout(1250)
    later = page.locator('.download-item').first.locator('.download-percent').inner_text()
    early_n = int(early.rstrip('%'))
    later_n = int(later.rstrip('%'))
    check(early_n < 100 and later_n > early_n, 'Progreso visible avanza gradualmente', results, {'initialTarget': initial, 'early': early, 'later': later})
    check(page.locator('.queue-summary-card dd').nth(3).inner_text() != 'Calculando…', 'Resumen de cola usa velocidad real', results, page.locator('.queue-summary-card').inner_text())
    context.close()

    # Larger utilities and QR generation.
    context = browser.new_context(viewport={'width': 1920, 'height': 1080}, screen={'width': 1920, 'height': 1080})
    page = context.new_page()
    page.set_content(html_for('?preview=1&view=utilities'), wait_until='load')
    page.wait_for_selector('.utility-tile')
    util_box = page.locator('.utility-tile').first.bounding_box()
    check(util_box and util_box['height'] >= 155, 'Herramientas internas ampliadas', results, util_box)
    settle(page)
    utilities_path = OUT / 'final-03-utilidades-1080p.png'
    page.screenshot(path=str(utilities_path))
    screenshots.append(str(utilities_path))
    page.locator('.utility-tile[data-utility="qr"]').click()
    page.wait_for_selector('.qr-studio')
    page.fill('#qr-text', 'https://tools.cacaplay.lat/local-demo')
    page.locator('.generate-qr').click()
    page.wait_for_selector('#qr-svg-host svg')
    check(page.locator('#qr-svg-host svg').count() == 1, 'Generador QR local funciona', results)
    qr_box = page.locator('.qr-preview').bounding_box()
    check(qr_box and qr_box['height'] >= 400, 'Vista QR rediseñada y grande', results, qr_box)
    settle(page, 700)
    qr_path = OUT / 'final-04-qr-1080p.png'
    page.screenshot(path=str(qr_path))
    screenshots.append(str(qr_path))
    context.close()

    # Playlist active state remains fully visible and fits the viewport.
    context = browser.new_context(viewport={'width': 1920, 'height': 1080}, screen={'width': 1920, 'height': 1080})
    page = context.new_page()
    page.set_content(html_for('?preview=1&view=home&dialog=playlist&playlist=queue'), wait_until='load')
    page.wait_for_selector('.playlist-current-card')
    opacity = page.locator('.playlist-current-card').evaluate('(node) => getComputedStyle(node).opacity')
    dialog_box = page.locator('.playlist-dialog').bounding_box()
    check(opacity == '1', 'Elemento activo de playlist no queda opaco', results, opacity)
    check(dialog_box and dialog_box['height'] <= 1080 and dialog_box['y'] >= 0, 'Playlist cabe en 1080p', results, dialog_box)
    settle(page, 650)
    playlist_path = OUT / 'final-05-playlist-1080p.png'
    page.screenshot(path=str(playlist_path))
    screenshots.append(str(playlist_path))
    context.close()

    browser.close()

report = {
    'passed': all(item['pass'] for item in results),
    'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'checks': results,
    'screenshots': screenshots,
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
