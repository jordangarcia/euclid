import asyncio, json
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':780}); pg=await ctx.new_page()
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.goto('http://localhost:8765/'); 
    await pg.wait_for_function('navigator.serviceWorker.controller!==null || false',timeout=10000) if False else None
    await pg.evaluate('navigator.serviceWorker.ready'); await pg.reload(); await pg.wait_for_timeout(800)
    ctrl=await pg.evaluate('!!navigator.serviceWorker.controller')
    man=await pg.evaluate("fetch('manifest.webmanifest').then(r=>r.json())")
    icons=await pg.evaluate("Promise.all(['icon-192.png','icon-512.png','icon-maskable-512.png','apple-touch-icon.png'].map(u=>fetch(u).then(r=>r.status)))")
    await ctx.set_offline(True); await pg.reload(); await pg.wait_for_timeout(500)
    n=await pg.evaluate('window.__euclid.count()')
    await pg.evaluate('window.__euclid.load(1)')
    print('sw controls page:',ctrl,'| manifest:',man['name'],man['display'],len(man['icons']),'icons | icon status',icons,'| offline reload puzzles:',n,'| errors',errs)
    await b.close()
asyncio.run(main())
