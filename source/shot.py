import asyncio
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':390,'height':780},device_scale_factor=2)
    await pg.goto('file:///mnt/user-data/outputs/euclid.html'); await pg.evaluate('window.__euclid.load(10)')
    await pg.evaluate("window.__euclid.place([{x:-1,y:-0.5,a:0},{},{},{x:1,y:-0.6,a:0}])")
    await pg.evaluate('window.__euclid.sel(0)'); await pg.screenshot(path='/home/claude/m1.png')
    h=await pg.evaluate('window.__euclid.handle()'); A=await pg.evaluate('window.__euclid.axis(0)')
    x0,y0=await pg.evaluate(f'window.__euclid.svgPoint({h[0]},{h[1]})'); x1,y1=await pg.evaluate(f'window.__euclid.svgPoint({A["c"][0]-0.3},{A["c"][1]})')
    await pg.mouse.move(x0,y0); await pg.mouse.down(); await pg.mouse.move(x1,y1,steps=5); await pg.screenshot(path='/home/claude/m2.png'); await pg.mouse.up()
    await pg.screenshot(path='/home/claude/m3.png'); await b.close()
asyncio.run(main())
