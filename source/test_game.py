import sys, json, math, asyncio
from playwright.async_api import async_playwright
URL='file://'+sys.argv[1]

JS_SNAPTEST = """
(n)=>{
 const E=window.__euclid; E.load(n);
 const sol=E.solution(); const ps=E.pieces();
 // map solution piece to tray piece index by type
 const used=new Set(); const map=sol.map(s=>{const i=ps.findIndex((p,k)=>p.t===s.t&&!used.has(k)); used.add(i); return i;});
 const angs=E.angles();
 const angOK=sol.every(s=>angs.some(a=>Math.abs(((a-s.a)%360+540)%360-180)<1e-3));
 const c0=E.coverage();
 // sequential perturbed placement + snapping
 let pending=sol.map((s,k)=>k), placed=new Set(), guard=0, fails=[];
 const OX=0.6,OY=-0.4; let first=true, retryExact=false;
 while(pending.length && guard<20){guard++; const next=[];
  for(const k of pending){ const i=map[k], s=sol[k];
    const dx=first?0:(Math.random()-.5)*0.25, dy=first?0:(Math.random()-.5)*0.25; first=false;
    const arr=E.pieces().map(p=>({})); arr[i]={x:s.x+OX+dx,y:s.y+OY+dy,a:s.a,f:s.f};
    E.place(arr); E.snap(i);
    const p=E.pieces()[i];
    if(Math.hypot(p.x-s.x-OX,p.y-s.y-OY)<2e-3) placed.add(k);
    else { // put back to tray-ish far away
      const far=E.pieces().map(()=>({})); far[i]={x:s.x+50,y:s.y+50}; E.place(far); next.push(k);} }
  if(next.length===pending.length){ if(!retryExact){retryExact=true; first=true; pending=next; continue;} fails=next; break;} retryExact=false; pending=next; }
 const snapSolved=E.isSolved();
 // exact placement
 E.load(n); const arr=E.pieces().map(()=>({})); sol.forEach((s,k)=>arr[map[k]]={x:s.x+1.1,y:s.y-0.3,a:s.a,f:s.f}); E.place(arr);
 const exact=E.isSolved();
 // near-miss: shift one piece by 0.3 => must NOT be solved
 E.load(n); const arr2=E.pieces().map(()=>({})); sol.forEach((s,k)=>arr2[map[k]]={x:s.x+(k===0?0.35:0),y:s.y,a:s.a,f:s.f}); E.place(arr2);
 const miss=E.isSolved();
 return {n,angOK,c0,snapSolved,fails:fails.length,exact,miss,multi:E.parts()>1};
}
"""

async def flip_drag(pg,i,full):
    h=await pg.evaluate('window.__euclid.handle()')
    A=await pg.evaluate(f'window.__euclid.axis({i})')
    c=A['c']; n=A['n']; d=(h[0]-c[0])*n[0]+(h[1]-c[1])*n[1]
    tgt = -d if full else d*0.4
    x0,y0=await pg.evaluate(f'window.__euclid.svgPoint({h[0]},{h[1]})')
    x1,y1=await pg.evaluate(f'window.__euclid.svgPoint({c[0]+n[0]*tgt},{c[1]+n[1]*tgt})')
    await pg.mouse.move(x0,y0); await pg.mouse.down(); await pg.mouse.move((x0+x1)/2,(y0+y1)/2,steps=6)
    if full: await pg.screenshot(path='/home/claude/shot_midflip.png')
    await pg.mouse.move(x1,y1,steps=6); await pg.mouse.up(); await pg.wait_for_timeout(50)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1200,'height':820})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: m.type=='error' and errs.append(m.text))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        N=await pg.evaluate('window.__euclid.count()')
        bad=[]
        for n in range(1,N+1):
            r=await pg.evaluate(JS_SNAPTEST,n)
            ok = r['angOK'] and r['exact'] and (not r['miss'] or r['multi']) and r['c0']<0.6 and (r['snapSolved'] or r['multi'])
            if not ok: bad.append(r)
        print('puzzles',N,'bad',len(bad))
        for r in bad: print(r)
        # real mouse interaction on puzzle 2
        await pg.evaluate('window.__euclid.load(2)')
        sol=await pg.evaluate('window.__euclid.solution()')
        ps=await pg.evaluate('window.__euclid.pieces()')
        used=set(); order=[]
        for s in sol:
            i=next(k for k,q in enumerate(ps) if q['t']==s['t'] and k not in used); used.add(i); order.append((i,s))
        for i,s in order:
            # rotate by tapping until angle/flip match
            for _ in range(10):
                cur=(await pg.evaluate('window.__euclid.pieces()'))[i]
                if cur['f']!=s['f']:
                    await pg.evaluate(f'(()=>{{}})()')
                    # select by tapping first then press F (tap rotates, so compensate)
                    x,y=await pg.evaluate(f'window.__euclid.svgPoint({cur["x"]},{cur["y"]})')
                    await pg.mouse.click(x,y); await pg.keyboard.press('f'); continue
                d=((cur['a']-s['a'])%360+540)%360-180
                if abs(d)<1e-3: break
                x,y=await pg.evaluate(f'window.__euclid.svgPoint({cur["x"]},{cur["y"]})')
                await pg.mouse.click(x,y); await pg.keyboard.press('r')
            cur=(await pg.evaluate('window.__euclid.pieces()'))[i]
            x0,y0=await pg.evaluate(f'window.__euclid.svgPoint({cur["x"]},{cur["y"]})')
            x1,y1=await pg.evaluate(f'window.__euclid.svgPoint({s["x"]+0.07},{s["y"]-0.05})')
            await pg.mouse.move(x0,y0); await pg.mouse.down(); await pg.mouse.move((x0+x1)/2,(y0+y1)/2,steps=5); await pg.mouse.move(x1,y1,steps=5); await pg.mouse.up()
        solved=await pg.evaluate('window.__euclid.isSolved()')
        print('mouse-solve puzzle 2:',solved)
        await pg.screenshot(path='/home/claude/shot_desktop.png')
        await pg.wait_for_timeout(300); await pg.click('#toastnext'); await pg.wait_for_timeout(200)
        print('after next:', await pg.inner_text('#num'))
        await pg.click('#goal'); await pg.wait_for_timeout(100)
        print('fullscreen shown:', await pg.is_visible('#full'))
        await pg.screenshot(path='/home/claude/shot_full.png')
        await pg.click('#full'); print('fullscreen closed:', not await pg.is_visible('#full'))
        # green dot: rotate by dragging around, flip by pulling through the middle
        await pg.evaluate('window.__euclid.load(5)')
        import math
        async def dot_path(i,pts_fn,shot=None):
            h=await pg.evaluate('window.__euclid.handle()'); A=await pg.evaluate(f'window.__euclid.axis({i})'); c=A['c']
            r=math.hypot(h[0]-c[0],h[1]-c[1]); a0=math.atan2(h[1]-c[1],h[0]-c[0])
            sp=await pg.evaluate(f'window.__euclid.svgPoint({h[0]},{h[1]})'); await pg.mouse.move(*sp); await pg.mouse.down()
            for k,(rr,aa) in enumerate(pts_fn(r,a0)):
                q=await pg.evaluate(f'window.__euclid.svgPoint({c[0]+rr*math.cos(aa)},{c[1]+rr*math.sin(aa)})'); await pg.mouse.move(*q)
                if shot and k==shot[0]: await pg.screenshot(path=shot[1])
            await pg.mouse.up(); await pg.wait_for_timeout(30)
        for i in range(7):
            p0=(await pg.evaluate('window.__euclid.pieces()'))[i]
            x,y=await pg.evaluate(f'window.__euclid.svgPoint({p0["x"]},{p0["y"]})'); await pg.mouse.click(x,y)
            pA=(await pg.evaluate('window.__euclid.pieces()'))[i]
            await dot_path(i,lambda r,a0:[(r,a0+math.radians(t)) for t in range(0,91,10)], (5,'/home/claude/shot_rot.png') if i==0 else None)
            pB=(await pg.evaluate('window.__euclid.pieces()'))[i]
            await dot_path(i,lambda r,a0:[(r*(1-2*k/12),a0) for k in range(13)], (6,'/home/claude/shot_midflip.png') if i==0 else None)
            pC=(await pg.evaluate('window.__euclid.pieces()'))[i]
            await dot_path(i,lambda r,a0:[(r*(1-1.6*k/10),a0) for k in range(11)]+[(r*(-0.6+1.6*k/10),a0) for k in range(11)])
            pD=(await pg.evaluate('window.__euclid.pieces()'))[i]
            da=((pB['a']-pA['a'])%360+540)%360-180
            print(p0['t'],'tap no turn:',abs(pA['a']-p0['a'])<1e-6,'| drag 90:',round(da,2),'| pull through flips:',pC['f']!=pB['f'],'| through & back no flip:',pD['f']==pC['f'])
        angs=await pg.evaluate('window.__euclid.angles()'); print('angles',angs)
        print('answer button gone:', await pg.query_selector('#answer') is None)
        await pg.click('#numbtn'); await pg.wait_for_timeout(300); await pg.screenshot(path='/home/claude/shot_picker.png')
        await pg.keyboard.press('Escape')
        m=await b.new_page(viewport={'width':390,'height':780},device_scale_factor=2,has_touch=True)
        await m.goto(URL); await m.wait_for_timeout(400); await m.evaluate('window.__euclid.load(Math.min(42,window.__euclid.count()))')
        await m.screenshot(path='/home/claude/shot_mobile.png')
        d=await b.new_page(viewport={'width':390,'height':780},color_scheme='dark')
        await d.goto(URL); await d.wait_for_timeout(400); await d.evaluate('window.__euclid.load(Math.min(14,window.__euclid.count()))'); await d.screenshot(path='/home/claude/shot_dark.png')
        print('errors',errs)
        await b.close()
asyncio.run(main())
