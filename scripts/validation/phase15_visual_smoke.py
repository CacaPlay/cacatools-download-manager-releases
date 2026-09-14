from playwright.sync_api import sync_playwright
from pathlib import Path
import json, base64
root=Path(__file__).resolve().parents[2]
out=root/'docs/screenshots'; out.mkdir(parents=True, exist_ok=True)
css=(root/'app-ui/styles.css').read_text()
js0=(root/'app-ui/main.js').read_text()
icon_data='data:image/svg+xml;base64,'+base64.b64encode((root/'app-ui/favicon.svg').read_bytes()).decode()
media_data='data:image/svg+xml;base64,'+base64.b64encode((root/'app-ui/media-preview.svg').read_bytes()).decode()

def html_for(query):
    js=js0.replace("const qs = new URLSearchParams(window.location.search);", f"const qs = new URLSearchParams({query!r});",1)
    js=js.replace('./app-ui/favicon.svg',icon_data).replace('./app-ui/media-preview.svg',media_data)
    return f'''<!doctype html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CacaTools Desktop</title><style>{css}</style></head><body><div id="app"></div><script>{js}</script></body></html>'''

pages=[
 ('01-inicio.png','?preview=1&view=home'),
 ('02-descargas.png','?preview=1&view=downloads'),
 ('03-divisas.png','?preview=1&view=currency'),
 ('04-playlist.png','?preview=1&view=home&dialog=playlist&playlist=queue'),
 ('05-utilidades.png','?preview=1&view=utilities'),
 ('06-ajustes.png','?preview=1&view=settings'),
]
report=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--disable-features=BlockInsecurePrivateNetworkRequests'])
    context=browser.new_context(viewport={'width':1536,'height':864}, device_scale_factor=1)
    for name,query in pages:
        page=context.new_page(); console=[]; errors=[]
        page.on('console', lambda msg,c=console: c.append({'type':msg.type,'text':msg.text}) if msg.type in ('error','warning') else None)
        page.on('pageerror', lambda exc,e=errors: e.append(str(exc)))
        page.set_content(html_for(query), wait_until='load', timeout=30000)
        page.wait_for_selector('.desktop-shell', timeout=15000)
        page.wait_for_timeout(600)
        metrics=page.evaluate('''() => ({
          width: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth,
          height: document.documentElement.scrollHeight, clientHeight: document.documentElement.clientHeight,
          workspaceScroll: document.querySelector('.workspace')?.scrollHeight,
          workspaceClient: document.querySelector('.workspace')?.clientHeight,
          cards: document.querySelectorAll('.tool-card').length,
          downloads: document.querySelectorAll('.download-item').length,
          recent: document.querySelectorAll('.recent-item').length,
          shell: !!document.querySelector('.desktop-shell'), fatal: !!document.querySelector('.fatal-screen')
        })''')
        page.screenshot(path=str(out/name), full_page=False)
        report.append({'name':name,'query':query,'metrics':metrics,'console':console,'page_errors':errors})
        page.close()
    page=context.new_page(); page.set_content(html_for('?preview=1&view=currency')); page.wait_for_selector('#currency-amount')
    before=page.locator('#currency-result-value').inner_text(); page.locator('.currency-quick-amount[data-amount="2500"]').click(); after=page.locator('#currency-result-value').inner_text(); page.locator('.currency-swap').click(); swapped=page.locator('#currency-result-code').inner_text()
    report.append({'interaction':'currency','before':before,'after_2500':after,'swapped_code':swapped}); page.close()
    page=context.new_page(); page.set_content(html_for('?preview=1&view=home')); page.wait_for_selector('.new-download-top'); page.locator('.new-download-top').click(); page.wait_for_selector('.download-dialog'); report.append({'interaction':'download_dialog','opened':page.locator('.download-dialog').count()==1,'title':page.locator('#download-dialog-title').inner_text()}); page.close()
    page=context.new_page(); page.set_content(html_for('?preview=1&view=home&dialog=playlist&playlist=queue')); page.wait_for_selector('.playlist-pause'); before=page.locator('.playlist-pause span').inner_text(); page.locator('.playlist-pause').click(); after=page.locator('.playlist-pause span').inner_text(); report.append({'interaction':'playlist_pause','before':before,'after':after}); page.close()
    browser.close()
(out/'visual-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
