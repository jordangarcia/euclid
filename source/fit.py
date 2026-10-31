import cv2, numpy as np, math, subprocess, json, sys, os
from shapely.geometry import Polygon
from shapely.ops import unary_union
from targets import get
from lib import CANON, A

R=8; STEP=4; LAM=3
ORDER=['S','B','B','T','T','s','s']
MANUAL={
 65:[(100,195),(280,195),(280,300),(205,300),(205,385),(240,385),(280,470),(125,470),(160,385),(158,300),(100,300)],
 97:[(465,112),(588,40),(715,100),(690,112),(700,180),(695,235),(665,180),(530,180),(505,240),(495,115)],
}

def orients(t):
    base=CANON[t]; out=[]
    for fl in (0,1):
        pts=[(-x,y) if fl else (x,y) for x,y in base]
        for k in range(4):
            q=pts
            for _ in range(k): q=[(-y,x) for x,y in q]
            mx=min(x for x,_ in q); my=min(y for _,y in q)
            out.append([(x-mx,y-my) for x,y in q])
    return out

def rast_poly(pts):
    w=int(round(max(x for x,_ in pts)*R)); h=int(round(max(y for _,y in pts)*R))
    P=Polygon(pts); from shapely import contains_xy
    xs=(np.arange(w)+.5)/R; ys=(np.arange(h)+.5)/R
    X,Y=np.meshgrid(xs,ys)
    m=contains_xy(P,X,Y).astype(np.uint8)
    return w,h,m

PM={t:[rast_poly(o) for o in orients(t)] for t in 'SBTs'}
OR={t:orients(t) for t in 'SBTs'}

def mask_for(n):
    import newmask
    if n in newmask.M: return newmask.get_new(n)
    if n in MANUAL:
        pts=np.array(MANUAL[n],np.int32)
        mx,my=pts.min(0); pts=pts-[mx-20,my-20]
        m=np.zeros((pts[:,1].max()+20,pts[:,0].max()+20),np.uint8)
        cv2.fillPoly(m,[pts],1); return m
    return get(n)

def theta_cands(m):
    cs,_=cv2.findContours(m.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    dirs=[]
    for c in cs:
        ap=cv2.approxPolyDP(c,max(3,0.02*cv2.arcLength(c,True)),True)[:,0,:]
        for i in range(len(ap)):
            a=ap[i];b=ap[(i+1)%len(ap)]; L=math.hypot(*(b-a))
            dirs.append((math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%90,L))
    th=np.arange(0,90,0.5); sc=[]
    for t in th:
        s=0
        for d,L in dirs:
            best=0
            for o in (0,A,90-A):
                dd=abs((d-t-o+45)%90-45); best=max(best,math.exp(-(dd/3)**2))
            s+=L*best
        sc.append(s)
    sc=np.array(sc); order=np.argsort(-sc); picks=[]
    for i in order:
        if all(abs((th[i]-p+45)%90-45)>6 for p in picks): picks.append(th[i])
        if len(picks)==2: break
    return picks

def target_grid(m,theta,phase):
    area=m.sum(); upx=math.sqrt(area/5.0)
    ys,xs=np.nonzero(m); cy,cx=ys.mean(),xs.mean()
    span=max(m.shape)/upx*1.1+2
    N=int(math.ceil(span*R/STEP))*STEP+STEP*2
    t=math.radians(theta); c,s=math.cos(t),math.sin(t)
    j,i=np.mgrid[0:N,0:N].astype(np.float32)
    u=(i+.5+phase[0]-N/2)/R; v=(j+.5+phase[1]-N/2)/R
    sx=cx+(c*u-s*v)*upx; sy=cy+(s*u+c*v)*upx
    g=cv2.remap(m.astype(np.float32),sx.astype(np.float32),sy.astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
    return (g>0.5).astype(np.uint8),N,upx,(cx,cy)

def run(grid,N,iters,seed):
    fn=f'/tmp/in_{os.getpid()}.txt'
    with open(fn,'w') as f:
        f.write(f'{N} {N} {STEP}\n'); f.write(' '.join(map(str,grid.flatten()))+'\n')
        for t in ORDER:
            for w,h,mm in PM[t]: f.write(f'{w} {h} '+' '.join(map(str,mm.flatten()))+'\n')
    out=subprocess.run(['./sa',fn,str(iters),str(seed),str(LAM)],capture_output=True,text=True).stdout.split('\n')
    sc=int(out[0]); st=[tuple(map(int,l.split())) for l in out[1:8]]
    return sc,st

def fit(n,iters=400000):
    m=mask_for(n); best=None
    for th in theta_cands(m):
        for ph in [(0,0),(2,0),(0,2),(2,2)]:
            g,N,upx,cen=target_grid(m,th,ph)
            tot=int(g.sum())
            for seed in (1,2):
                sc,st=run(g,N,iters,seed+n*10)
                if best is None or sc>best[0]: best=(sc,st,th,ph,N,tot,g)
    sc,st,th,ph,N,tot,g=best
    pieces=[]
    for p,(o,x,y) in enumerate(st):
        t=ORDER[p]; pts=[((px+x/R)-(N/2)/R+ph[0]/R,(py+y/R)-(N/2)/R+ph[1]/R) for px,py in OR[t][o]]
        pieces.append((t,pts))
    cov=np.zeros_like(g)
    for p,(o,x,y) in enumerate(st):
        w,h,mm=PM[ORDER[p]][o]; x0,y0=max(x,0),max(y,0)
        cov[y0:y+h,x0:x+w]+=mm[y0-y:,x0-x:][:cov[y0:y+h,x0:x+w].shape[0],:cov[y0:y+h,x0:x+w].shape[1]]
    inter=int(((cov>0)&(g>0)).sum()); uni=int(((cov>0)|(g>0)).sum()); ovl=int((cov>1).sum())
    return dict(n=n,score=sc,iou=inter/uni,ovl=ovl,total=tot,theta=float(th),pieces=pieces,grid=g.tolist())

if __name__=='__main__':
    ns=[int(a) for a in sys.argv[1:]]
    res={}
    if os.path.exists('fits.json'): res=json.load(open('fits.json'))
    for n in ns:
        r=fit(n); res[str(n)]=r
        print(n, round(r['iou'],3), r['ovl'], flush=True)
        json.dump(res,open('fits.json','w'))
