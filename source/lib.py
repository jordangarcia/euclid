import math, json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity

A = math.degrees(math.atan(0.5))  # 26.565
CANON = {
    'S': [(0,0),(1,0),(1,1),(0,1)],
    'B': [(0,0),(2,0),(0,1)],
    'T': [(0,0),(1,0),(1,0.5),(0,1)],
    's': [(0,0),(1,0),(0,0.5)],
}
COUNT = {'S':1,'B':2,'T':2,'s':2}

def sig(pts):
    n=len(pts); L=[]
    for i in range(n):
        a=pts[i]; b=pts[(i+1)%n]
        L.append(round(math.hypot(b[0]-a[0],b[1]-a[1]),4))
    return sorted(L)

CSIG = {k: sig(v) for k,v in CANON.items()}

def rot(pts, ang, c=(0,0)):
    r=math.radians(ang); cs,sn=math.cos(r),math.sin(r)
    return [(c[0]+(x-c[0])*cs-(y-c[1])*sn, c[1]+(x-c[0])*sn+(y-c[1])*cs) for x,y in pts]

def build(p):
    """p: {'pieces':[(type, pts[, ang, center])], 'rot': deg}"""
    out=[]
    for pc in p['pieces']:
        t,pts=pc[0],pc[1]
        if len(pc)>2: pts=rot(pts,pc[2],pc[3] if len(pc)>3 else (0,0))
        out.append((t,pts))
    if p.get('rot'): out=[(t,rot(pts,p['rot'])) for t,pts in out]
    return out

def validate(n,p):
    pcs=build(p); errs=[]
    cnt={}
    for t,pts in pcs:
        cnt[t]=cnt.get(t,0)+1
        if sig(pts)!=CSIG[t]: errs.append(f'{t} not congruent {sig(pts)}')
    if cnt!=COUNT: errs.append(f'counts {cnt}')
    polys=[Polygon(pts) for _,pts in pcs]
    for i in range(len(polys)):
        for j in range(i+1,len(polys)):
            a=polys[i].intersection(polys[j]).area
            if a>1e-6: errs.append(f'overlap {i},{j} {a:.3f}')
    U=unary_union([q.buffer(1e-7,join_style=2) for q in polys]).buffer(-1e-7,join_style=2)
    if abs(U.area-5)>1e-4: errs.append(f'area {U.area}')
    return errs,pcs,U

def outline(U):
    U=U.simplify(1e-6)
    geoms=list(U.geoms) if U.geom_type=='MultiPolygon' else [U]
    res=[]
    for g in geoms:
        rings=[list(g.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in g.interiors]
        res.append([[ [round(x,5),round(y,5)] for x,y in r] for r in rings])
    return res
