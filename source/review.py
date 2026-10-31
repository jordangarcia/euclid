import json, cv2, numpy as np, sys
from fit import mask_for
data=json.load(open('puzzles.json'))
tiles=[]
for p in data:
    n=p['n']; m=mask_for(n).astype(np.uint8)*255
    h,w=m.shape; s=110/max(h,w); a=cv2.resize(m,(int(w*s),int(h*s)))
    A=np.full((120,120),255,np.uint8); A[5:5+a.shape[0],5:5+a.shape[1]]=255-a
    xs=[v[0] for poly in p['outline'] for r in poly for v in r]; ys=[v[1] for poly in p['outline'] for r in poly for v in r]
    sc=110/max(max(xs)-min(xs),max(ys)-min(ys))
    B=np.full((120,120),255,np.uint8)
    for poly in p['outline']:
        for r in poly:
            pts=np.array([[(x-min(xs))*sc+5,(y-min(ys))*sc+5] for x,y in r],np.int32)
            cv2.fillPoly(B,[pts],0 if r is poly[0] else 255)
    t=np.hstack([A,np.full((120,4),180,np.uint8),B])
    t=cv2.copyMakeBorder(t,14,4,2,2,cv2.BORDER_CONSTANT,value=255)
    cv2.putText(t,f"{n} {p['iou']}",(3,11),cv2.FONT_HERSHEY_SIMPLEX,0.38,0,1)
    tiles.append(t)
C=6; e=np.full_like(tiles[0],255)
rows=[np.hstack(tiles[i:i+C]+[e]*(C-len(tiles[i:i+C]))) for i in range(0,len(tiles),C)]
img=np.vstack(rows)
for k in range(0,img.shape[0],1100): cv2.imwrite(f'review{k//1100}.png',img[k:k+1100])
print((img.shape[0]+1099)//1100)
