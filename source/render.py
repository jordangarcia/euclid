import json, cv2, numpy as np, sys
res=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'fits.json'))
ns=sorted(res,key=int)
tiles=[]
cols={'S':(80,180,80),'B':(60,120,220),'T':(200,140,60),'s':(160,80,200)}
for k in ns:
    r=res[k]; g=np.array(r['grid'],np.uint8); N=g.shape[0]; Z=6
    img=np.full((N*Z,N*Z,3),255,np.uint8)
    img[np.kron(g,np.ones((Z,Z),np.uint8))>0]=(200,200,200)
    for t,pts in r['pieces']:
        p=np.array([[(x*8+N/2)*Z,(y*8+N/2)*Z] for x,y in pts],np.int32)
        ov=img.copy(); cv2.fillPoly(ov,[p],cols[t]); img=cv2.addWeighted(ov,0.55,img,0.45,0)
        cv2.polylines(img,[p],True,(0,0,0),1)
    ys,xs=np.nonzero(g); pad=20
    img=img[max(ys.min()*Z-pad,0):ys.max()*Z+pad,max(xs.min()*Z-pad,0):xs.max()*Z+pad]
    s=180/max(img.shape[:2]); img=cv2.resize(img,None,fx=s,fy=s)
    c=np.full((200,200,3),255,np.uint8); c[15:15+img.shape[0],5:5+img.shape[1]]=img
    cv2.putText(c,f"{k} {r['iou']:.2f} o{r['ovl']}",(3,13),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,255),1)
    tiles.append(c)
C=8
rows=[np.hstack(tiles[i:i+C]+[np.full((200,200,3),255,np.uint8)]*(C-len(tiles[i:i+C]))) for i in range(0,len(tiles),C)]
cv2.imwrite(sys.argv[2] if len(sys.argv)>2 else 'fits.png',np.vstack(rows))
