import cv2, numpy as np, json
im=cv2.imread('/mnt/user-data/uploads/dccb0944e031f2a8ffc13f588e01eaca189c9c03.jpeg',0)
x0,y0,x1,y1=340,725,860,1390
reg=im[y0:y1,x0:x1]
S=4
big=cv2.resize(reg,None,fx=S,fy=S,interpolation=cv2.INTER_CUBIC)
bg=cv2.GaussianBlur(big,(0,0),20)
diff=bg.astype(int)-big.astype(int)
lines=(diff>12).astype(np.uint8)*255
lines=cv2.morphologyEx(lines,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
K=int(__import__('sys').argv[1])
d=cv2.dilate(lines,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(K,K)))
h,w=d.shape
ff=d.copy(); mask=np.zeros((h+2,w+2),np.uint8)
cv2.floodFill(ff,mask,(0,0),128)
filled=(ff!=128).astype(np.uint8)*255
filled=cv2.erode(filled,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(K,K)))
filled=cv2.morphologyEx(filled,cv2.MORPH_OPEN,np.ones((9,9),np.uint8))
n,lab,st,cen=cv2.connectedComponentsWithStats(filled)
keep=[i for i in range(1,n) if st[i][4]>2500]
print(len(keep))
vis=cv2.cvtColor(big,cv2.COLOR_GRAY2BGR)
vis[filled>0]=(vis[filled>0]*0.5+np.array([0,0,120])).astype(np.uint8)
for i in keep:
    c=cen[i]; cv2.putText(vis,str(i),(int(c[0])-10,int(c[1])),cv2.FONT_HERSHEY_SIMPLEX,0.9,(255,0,0),2)
cv2.imwrite('seg2.png',cv2.resize(vis,None,fx=0.5,fy=0.5))
np.save('lab2.npy',lab); json.dump({int(i):[[int(v) for v in st[i]],[float(cen[i][0]),float(cen[i][1])]] for i in keep},open('comps2.json','w'))
cv2.imwrite('filled.png',filled)
