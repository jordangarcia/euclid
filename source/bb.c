// bb input.txt nodelimit initbest
// input: W H L ; grid ; then 4 types (S,B,T,s) with counts, each 8 orientations: w h mask
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define NT 4
#define NO 8
int W,H,L; unsigned char *T; int cnt[NT]; int tw[NT][NO],th[NT][NO]; unsigned char*pm[NT][NO];
int ncell[NT][NO]; int cx[NT][NO][256], cy[NT][NO][256]; int area[NT];
int *cov; // 0 free, >0 piece id, -1 skipped
long nodes=0,limit; int best; int phx,phy;
int stT[16],stO[16],stX[16],stY[16],sd=0; int bT[16],bO[16],bX[16],bY[16],bn=0,bphx,bphy;
int remT, remA; int kl[NT][NO][4][4][64]; int kn[NT][NO][4][4];
void dfs(int pos,int cost){
  if(++nodes>limit) return;
  int lb=cost+abs(remT-remA); if(lb>=best) return;
  int c=pos; while(c<W*H && !(T[c] && cov[c]==0)) c++;
  if(c>=W*H){ // all target cells handled; remaining pieces would be outside -> handled by lb (remT=0)
    if(remA==0 && cost<best){best=cost; bn=sd; memcpy(bT,stT,sizeof bT);memcpy(bO,stO,sizeof bO);memcpy(bX,stX,sizeof bX);memcpy(bY,stY,sizeof bY); bphx=phx;bphy=phy;}
    return; }
  int x0=c%W,y0=c/W;
  for(int t=0;t<NT;t++){ if(!cnt[t]) continue;
    for(int o=0;o<NO;o++){
      int n=ncell[t][o]; int rx=((x0-phx)%L+L)%L, ry=((y0-phy)%L+L)%L;
      for(int kk=0;kk<kn[t][o][rx][ry];kk++){ int k=kl[t][o][rx][ry][kk];
        int ox=x0-cx[t][o][k], oy=y0-cy[t][o][k];
        if(ox<0||oy<0||ox+tw[t][o]>W||oy+th[t][o]>H) continue;
        // check
        int ok=1,out=0,inT=0;
        for(int q=0;q<n;q++){ int idx=(oy+cy[t][o][q])*W+ox+cx[t][o][q];
          if(cov[idx]!=0){ok=0;break;}
          if(T[idx]){ if(idx<c){ok=0;break;} inT++; } else out++; }
        if(!ok) continue;
        if(cost+out>=best) continue;
        for(int q=0;q<n;q++){ int idx=(oy+cy[t][o][q])*W+ox+cx[t][o][q]; cov[idx]=sd+1; }
        cnt[t]--; remT-=inT; remA-=n; stT[sd]=t;stO[sd]=o;stX[sd]=ox;stY[sd]=oy; sd++;
        dfs(c+1,cost+out);
        sd--; cnt[t]++; remT+=inT; remA+=n;
        for(int q=0;q<n;q++){ int idx=(oy+cy[t][o][q])*W+ox+cx[t][o][q]; cov[idx]=0; }
        if(nodes>limit) return;
      }
    }
  }
  // skip
  cov[c]=-1; remT--; dfs(c+1,cost+1); remT++; cov[c]=0;
}
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); limit=atol(argv[2]); best=atoi(argv[3]);
  if(fscanf(f,"%d %d %d",&W,&H,&L)!=3) return 1;
  T=malloc(W*H); int tot=0; for(int i=0;i<W*H;i++){int v; if(fscanf(f,"%d",&v)!=1) return 1; T[i]=v; tot+=v;}
  for(int t=0;t<NT;t++){ if(fscanf(f,"%d",&cnt[t])!=1) return 1;
    for(int o=0;o<NO;o++){ if(fscanf(f,"%d %d",&tw[t][o],&th[t][o])!=2) return 1; pm[t][o]=malloc(tw[t][o]*th[t][o]); int n=0;
      for(int j=0;j<th[t][o];j++)for(int i=0;i<tw[t][o];i++){int v; if(fscanf(f,"%d",&v)!=1) return 1; pm[t][o][j*tw[t][o]+i]=v; if(v){cx[t][o][n]=i;cy[t][o][n]=j;n++;}}
      ncell[t][o]=n; area[t]=n; }}
  cov=calloc(W*H,sizeof(int));
  for(int t=0;t<NT;t++)for(int o=0;o<NO;o++)for(int rx=0;rx<L;rx++)for(int ry=0;ry<L;ry++){kn[t][o][rx][ry]=0;
    for(int k=0;k<ncell[t][o];k++){ if(((rx-cx[t][o][k])%L+L)%L==0 && ((ry-cy[t][o][k])%L+L)%L==0){ if(kn[t][o][rx][ry]<64) kl[t][o][rx][ry][kn[t][o][rx][ry]++]=k; }}}
  int A=0; for(int t=0;t<NT;t++) A+=cnt[t]*area[t];
  long per=limit/(L*L); 
  for(phy=0;phy<L;phy++)for(phx=0;phx<L;phx++){ nodes=0; limit=per; remT=tot; remA=A; sd=0; dfs(0,0); }
  printf("%d %d %d %d\n",best,bn,bphx,bphy);
  for(int i=0;i<bn;i++) printf("%d %d %d %d\n",bT[i],bO[i],bX[i],bY[i]);
  return 0;
}
