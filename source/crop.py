import cv2,numpy as np,json,sys
from targets import ans
c=json.load(open('comps3.json'))
big=cv2.resize(cv2.imread('/mnt/user-data/uploads/dccb0944e031f2a8ffc13f588e01eaca189c9c03.jpeg',0)[725:1390,340:860],None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
cl=cv2.createCLAHE(3.0,(8,8)); big=cl.apply(big)
out=[]
for n in map(int,sys.argv[2:]):
    ids=ans[n]; bs=[c[str(i)][0] for i in ids]
    x=min(b[0] for b in bs); y=min(b[1] for b in bs); x2=max(b[0]+b[2] for b in bs); y2=max(b[1]+b[3] for b in bs)
    t=big[max(y-20,0):y2+20,max(x-20,0):x2+20]; s=300/max(t.shape); t=cv2.resize(t,None,fx=s,fy=s)
    T=np.full((320,320),255,np.uint8); T[10:10+t.shape[0],10:10+t.shape[1]]=t
    cv2.putText(T,str(n),(2,14),cv2.FONT_HERSHEY_SIMPLEX,0.5,0,1); out.append(T)
rows=[np.hstack(out[i:i+4]+[np.full((320,320),255,np.uint8)]*(4-len(out[i:i+4]))) for i in range(0,len(out),4)]
cv2.imwrite(sys.argv[1],np.vstack(rows))
