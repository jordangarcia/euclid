import cv2, numpy as np, json
files={'A':'IMG_7668.PNG','B':'IMG_7669.PNG','C':'IMG_7670.PNG','D':'IMG_7671.PNG'}
# crop paper regions (y ranges) to avoid answer sheet / carpet
crops={'A':(560,1420,120,1180),'B':(460,1400,90,1165),'C':(510,1400,20,1170),'D':(440,1370,165,1150)}
out={}
for k,f in files.items():
    im=cv2.imread('/mnt/user-data/uploads/'+f); y0,y1,x0,x1=crops[k]; im=im[y0:y1,x0:x1]
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV).astype(np.float32); V=hsv[...,2]
    bg=cv2.GaussianBlur(cv2.dilate(V,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(81,81))),(0,0),20)
    m=(V<(0.68 if k=='A' else 0.6)*bg).astype(np.uint8)*255
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((5,5),np.uint8)); m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    ff=cv2.copyMakeBorder(m,1,1,1,1,cv2.BORDER_CONSTANT,value=0); mk=np.zeros((ff.shape[0]+2,ff.shape[1]+2),np.uint8); cv2.floodFill(ff,mk,(0,0),128); m[ff[1:-1,1:-1]==0]=255
    n,lab,st,cen=cv2.connectedComponentsWithStats(m)
    vis=im.copy(); H,W=m.shape
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if a<2500 or w>600 or h>600: continue
        vis[lab==i]=(0,0,200)
        cv2.putText(vis,str(i),(int(cen[i][0])-12,int(cen[i][1])+8),cv2.FONT_HERSHEY_SIMPLEX,1.0,(255,255,0),3)
        out[f'{k}{i}']=dict(f=k,i=int(i),box=[int(v) for v in st[i]])
    np.save(f'labn_{k}.npy',lab); cv2.imwrite(f'segn_{k}.png',cv2.resize(vis,None,fx=0.5,fy=0.5))
json.dump(out,open('compsn.json','w')); print(len(out))
