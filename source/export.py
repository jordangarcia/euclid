import json, math, sys
from shapely.geometry import Polygon
from shapely.ops import unary_union
from lib import CANON, A, validate, outline
NICE=[0,A,45,90-A]
def centroid(p): return Polygon(p).centroid.coords[0]
LOCAL={t:[(x-centroid(v)[0],y-centroid(v)[1]) for x,y in v] for t,v in CANON.items()}
def ang(v): return math.degrees(math.atan2(v[1],v[0]))
def match(t,pts0):
    n=len(pts0)
    for f in (0,1):
        L=[(-x,y) if f else (x,y) for x,y in LOCAL[t]]
        for d in (1,-1):
            for k in range(n):
                pts=[pts0[(k+d*i)%n] for i in range(n)]
                a=ang((pts[1][0]-pts[0][0],pts[1][1]-pts[0][1]))-ang((L[1][0]-L[0][0],L[1][1]-L[0][1]))
                r=math.radians(a); c,s=math.cos(r),math.sin(r)
                rl=[(c*x-s*y,s*x+c*y) for x,y in L]
                dx=pts[0][0]-rl[0][0]; dy=pts[0][1]-rl[0][1]
                if all(abs(rl[i][0]+dx-pts[i][0])<1e-6 and abs(rl[i][1]+dy-pts[i][1])<1e-6 for i in range(n)):
                    return dict(t=t,a=round(a%360,4),f=bool(f),x=dx,y=dy)
    raise Exception('nomatch')
def nice_phi(th):
    best=None
    for k in range(4):
        for o in NICE:
            v=o+90*k; d=abs((th-v+180)%360-180)
            if best is None or d<best[0]: best=(d,v)
    return best[1]
def export(fits, order):
    out=[]
    for n in order:
        r=fits[str(n)]; phi=nice_phi(r['theta']); t=math.radians(phi); c,s=math.cos(t),math.sin(t)
        raw=[(T,[tuple(q) for q in pts]) for T,pts in r['pieces']]
        errs,_,U0=validate(n,{'pieces':raw})
        if errs: print('ERR',n,errs)
        rotp=lambda q:(c*q[0]-s*q[1],s*q[0]+c*q[1])
        ol=[[[rotp(v) for v in ring] for ring in poly] for poly in outline(U0)]
        xs=[v[0] for p in ol for r_ in p for v in r_]; ys=[v[1] for p in ol for r_ in p for v in r_]
        cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
        ol=[[[[round(v[0]-cx,5),round(v[1]-cy,5)] for v in ring] for ring in poly] for poly in ol]
        pcs=[(T,[(rotp(q)[0]-cx,rotp(q)[1]-cy) for q in pts]) for T,pts in raw]
        sol=[]
        for T,pts in pcs:
            m=match(T,pts); m['x']=round(m['x'],5); m['y']=round(m['y'],5); sol.append(m)
        out.append(dict(n=n,pieces=sol,outline=ol,angles=sorted(set(p['a'] for p in sol)),iou=round(r['iou'],3)))
    return out
if __name__=='__main__':
    fits=json.load(open(sys.argv[1]))
    import os
    if os.path.exists('manual.json'): fits.update(json.load(open('manual.json')))
    order=sorted(map(int,fits))
    data=export(fits,order)
    json.dump(data,open('puzzles.json','w'),separators=(',',':'))
    html=open('game_template.html').read().replace('/*DATA*/[]',json.dumps(data,separators=(',',':')))
    open(sys.argv[2],'w').write(html); print(len(data),'puzzles')
