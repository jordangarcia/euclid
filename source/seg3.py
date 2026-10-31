import cv2, numpy as np, json
filled=cv2.imread('filled.png',0)
big=cv2.resize(cv2.imread('/mnt/user-data/uploads/dccb0944e031f2a8ffc13f588e01eaca189c9c03.jpeg',0)[725:1390,340:860],None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
o=cv2.morphologyEx(filled,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(17,17)))
n,lab,st,cen=cv2.connectedComponentsWithStats(o)
keep=[i for i in range(1,n) if st[i][4]>3000]
# order: rows by y
print(len(keep))
vis=cv2.cvtColor(big,cv2.COLOR_GRAY2BGR)
vis[o>0]=(vis[o>0]*0.5+np.array([0,0,120])).astype(np.uint8)
for i in keep:
    c=cen[i]; cv2.putText(vis,str(i),(int(c[0])-14,int(c[1])+8),cv2.FONT_HERSHEY_SIMPLEX,1.1,(255,0,0),3)
cv2.imwrite('seg3.png',cv2.resize(vis,None,fx=0.5,fy=0.5))
np.save('lab3.npy',lab); json.dump({int(i):[[int(v) for v in st[i]],[float(cen[i][0]),float(cen[i][1])]] for i in keep},open('comps3.json','w'))
