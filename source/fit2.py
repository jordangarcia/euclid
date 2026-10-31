import numpy as np, math, subprocess, json, sys, os, tempfile
from fit import mask_for, theta_cands, target_grid, PM, OR, R
TYPES=['B','T','S','s']; CNT={'B':2,'T':2,'S':1,'s':2}
def run_bb(g,N,limit,init):
    fn=os.path.join(tempfile.gettempdir(),f'bb_{os.getpid()}.txt')
    with open(fn,'w') as f:
        f.write(f'{N} {N} 4\n'+' '.join(map(str,g.flatten()))+'\n')
        for t in TYPES:
            f.write(f'{CNT[t]}\n')
            for w,h,mm in PM[t]: f.write(f'{w} {h} '+' '.join(map(str,mm.flatten()))+'\n')
    out=subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)),'bb'),fn,str(limit),str(init)],capture_output=True,text=True).stdout.strip().split('\n')
    best,bn,px,py=map(int,out[0].split())
    st=[tuple(map(int,l.split())) for l in out[1:1+bn]]
    return best,st
def fit(n,limit=16_000_000,ths=None):
    m=mask_for(n); best=None
    for th in (ths or theta_cands(m)):
        g,N,upx,cen=target_grid(m,th,(0,0))
        tot=int(g.sum())
        init=int(tot*0.35) if best is None else best[0]
        c,st=run_bb(g,N,limit,init)
        if len(st)==7 and (best is None or c<best[0]): best=(c,st,th,N,tot,g)
    if best is None: return None
    c,st,th,N,tot,g=best
    pieces=[]; cov=np.zeros_like(g)
    for t,o,x,y in st:
        T=TYPES[t]; w,h,mm=PM[T][o]; cov[y:y+h,x:x+w]+=mm
        pieces.append((T,[(px+x/R-(N/2)/R,py+y/R-(N/2)/R) for px,py in OR[T][o]]))
    inter=int(((cov>0)&(g>0)).sum()); uni=int(((cov>0)|(g>0)).sum())
    return dict(n=n,cost=c,iou=inter/uni,ovl=int((cov>1).sum()),total=tot,theta=float(th),pieces=pieces,grid=g.tolist())
if __name__=='__main__':
    out=sys.argv[1]; ns=[int(a) for a in sys.argv[2:]]
    res=json.load(open(out)) if os.path.exists(out) else {}
    for n in ns:
        r=fit(n)
        if r is None: print(n,'FAIL',flush=True); continue
        res[str(n)]=r; print(n,round(r['iou'],3),r['cost'],flush=True)
        json.dump(res,open(out,'w'))
