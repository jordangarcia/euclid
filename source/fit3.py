import numpy as np, json, sys, os, time
import fit2
from fit import mask_for
def fit(n):
    m=mask_for(n); cands=[]
    for th in np.arange(0,90,9.0):
        r=fit2.fit(n,limit=400_000,ths=[float(th)])
        if r: cands.append((r['cost'],float(th),r))
    cands.sort(key=lambda c:c[0])
    best=cands[0][2] if cands else None
    tried=set()
    for c,th,_ in cands[:1]:
        for d in (-1.5,0,1.5):
            t=round(th+d,1)
            if t in tried: continue
            tried.add(t)
            r=fit2.fit(n,limit=4_000_000,ths=[t])
            if r and (best is None or r['cost']<best['cost']): best=r
    return best
if __name__=='__main__':
    out=sys.argv[1]; ns=[int(a) for a in sys.argv[2:]]
    res=json.load(open(out)) if os.path.exists(out) else {}
    for n in ns:
        t=time.time(); r=fit(n)
        if r is None: print(n,'FAIL',flush=True); continue
        res[str(n)]=r; print(n,round(r['iou'],3),r['cost'],round(time.time()-t),'s',flush=True)
        json.dump(res,open(out,'w'))
