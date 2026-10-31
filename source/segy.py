import cv2, numpy as np, json
im=cv2.imread('/mnt/user-data/uploads/dccb0944e031f2a8ffc13f588e01eaca189c9c03.jpeg')
panels=[(95,455,352,690),(362,430,638,690),(650,430,935,690),(950,430,1195,680)]
S=4; out={}
for pi,(x0,y0,x1,y1) in enumerate(panels):
    big=cv2.resize(im[y0:y1,x0:x1],None,fx=S,fy=S,interpolation=cv2.INTER_CUBIC)
    hsv=cv2.cvtColor(big,cv2.COLOR_BGR2HSV).astype(np.float32)
    V=hsv[...,2]
    bg=cv2.GaussianBlur(cv2.dilate(V,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(121,121))),(0,0),25)
    m=(V<0.6*bg).astype(np.uint8)*255
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    n,lab,st,cen=cv2.connectedComponentsWithStats(m)
    H,W=m.shape
    vis=big.copy(); 
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if a<2500 or x<=2 or y<=2 or x+w>=W-2 or y+h>=H-2: continue
        vis[lab==i]=(0,0,220)
        out[f'{pi}_{i}']=dict(box=[int(v) for v in st[i]],c=[float(cen[i][0]),float(cen[i][1])])
        cv2.putText(vis,str(i),(int(cen[i][0])-14,int(cen[i][1])+8),cv2.FONT_HERSHEY_SIMPLEX,1.4,(255,255,0),3)
    np.save(f'laby{pi}.npy',lab)
    cv2.imwrite(f'segy{pi}.png',cv2.resize(vis,None,fx=0.5,fy=0.5))
json.dump(out,open('compsy.json','w')); print(len(out))
