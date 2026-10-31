// usage: sa input.txt iters seed > out
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#define NP 7
#define NO 8
int W,H,STEP; unsigned char *T; int tw[NP][NO],th[NP][NO]; unsigned char *pm[NP][NO];
int *cov; int LAM=2;
int st_o[NP],st_x[NP],st_y[NP];
static unsigned long long rs=88172645463325252ULL;
static inline unsigned long long xr(){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline double ur(){return (xr()>>11)*(1.0/9007199254740992.0);}
// cell value contributions: score = covered&T - covered&!T - 3*over
static inline int cellscore(int c,int t){ if(c==0) return 0; int s = t?10:-10; s-=30*(c-1); return s; }
static inline int occ(int x,int y){ if(x<0||y<0||x>=W||y>=H) return 0; return cov[y*W+x]>0; }
long delta_apply(int p,int o,int x,int y,int sign){
  // add (sign=+1) or remove (-1) piece mask, return score delta
  long d=0; int w=tw[p][o],h=th[p][o]; unsigned char*m=pm[p][o];
  for(int j=0;j<h;j++){int yy=y+j; for(int i=0;i<w;i++){ if(!m[j*w+i]) continue; int xx=x+i;
    if(xx<0||yy<0||xx>=W||yy>=H){ d += sign>0? -40 : 40; continue;}
    int idx=yy*W+xx; int t=T[idx]; int before=cellscore(cov[idx],t); int o0=cov[idx]>0;
    int nb0=0; if(1){ nb0=(occ(xx-1,yy)!=o0)+(occ(xx+1,yy)!=o0)+(occ(xx,yy-1)!=o0)+(occ(xx,yy+1)!=o0);} 
    cov[idx]+=sign; d+=cellscore(cov[idx],t)-before; int o1=cov[idx]>0;
    if(o1!=o0){ int nb1=(occ(xx-1,yy)!=o1)+(occ(xx+1,yy)!=o1)+(occ(xx,yy-1)!=o1)+(occ(xx,yy+1)!=o1); d-=LAM*(nb1-nb0);} }}
  return d;
}
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); long iters=atol(argv[2]); rs ^= (unsigned long long)atol(argv[3])*2654435761ULL+1; if(argc>4) LAM=atoi(argv[4]);
  if(fscanf(f,"%d %d %d",&W,&H,&STEP)!=3) return 1;
  T=malloc(W*H); for(int i=0;i<W*H;i++){int v; fscanf(f,"%d",&v); T[i]=v;}
  for(int p=0;p<NP;p++)for(int o=0;o<NO;o++){fscanf(f,"%d %d",&tw[p][o],&th[p][o]); pm[p][o]=malloc(tw[p][o]*th[p][o]); for(int i=0;i<tw[p][o]*th[p][o];i++){int v;fscanf(f,"%d",&v);pm[p][o][i]=v;}}
  cov=calloc(W*H,sizeof(int));
  int nx=W/STEP, ny=H/STEP;
  long score=0;
  for(int p=0;p<NP;p++){st_o[p]=xr()%NO; st_x[p]=(xr()%nx)*STEP; st_y[p]=(xr()%ny)*STEP; score+=delta_apply(p,st_o[p],st_x[p],st_y[p],1);}
  long best=score; int bo[NP],bx[NP],by[NP]; memcpy(bo,st_o,sizeof bo);memcpy(bx,st_x,sizeof bx);memcpy(by,st_y,sizeof by);
  double T0=60.0,T1=0.5;
  for(long it=0;it<iters;it++){
    double temp=T0*pow(T1/T0,(double)it/iters);
    int mv=xr()%10;
    if(mv<8){
      int p=xr()%NP; int o=st_o[p],x=st_x[p],y=st_y[p]; int no=o,nxp=x,nyp=y;
      int r=xr()%6;
      if(r<4){ int k=(xr()%3==0)?2:1; if(r==0)nxp+=STEP*k; if(r==1)nxp-=STEP*k; if(r==2)nyp+=STEP*k; if(r==3)nyp-=STEP*k; }
      else if(r==4){ no=xr()%NO; }
      else { no=xr()%NO; nxp=(xr()%nx)*STEP; nyp=(xr()%ny)*STEP; }
      long d=delta_apply(p,o,x,y,-1); d+=delta_apply(p,no,nxp,nyp,1);
      if(d>=0 || ur()<exp(d/temp)){ st_o[p]=no;st_x[p]=nxp;st_y[p]=nyp; score+=d; }
      else { delta_apply(p,no,nxp,nyp,-1); delta_apply(p,o,x,y,1); }
    } else {
      // swap positions of two pieces (keep orientation), approx align by bbox origin
      int a=xr()%NP,b=xr()%NP; if(a==b) continue;
      long d=delta_apply(a,st_o[a],st_x[a],st_y[a],-1)+delta_apply(b,st_o[b],st_x[b],st_y[b],-1);
      int ao=xr()%NO, bo2=xr()%NO;
      d+=delta_apply(a,ao,st_x[b],st_y[b],1)+delta_apply(b,bo2,st_x[a],st_y[a],1);
      if(d>=0||ur()<exp(d/temp)){int tx=st_x[a],ty=st_y[a]; st_x[a]=st_x[b];st_y[a]=st_y[b];st_x[b]=tx;st_y[b]=ty;st_o[a]=ao;st_o[b]=bo2;score+=d;}
      else { delta_apply(a,ao,st_x[b],st_y[b],-1); delta_apply(b,bo2,st_x[a],st_y[a],-1); delta_apply(a,st_o[a],st_x[a],st_y[a],1); delta_apply(b,st_o[b],st_x[b],st_y[b],1);}
    }
    if(score>best){best=score;memcpy(bo,st_o,sizeof bo);memcpy(bx,st_x,sizeof bx);memcpy(by,st_y,sizeof by);}
  }
  printf("%ld\n",best);
  for(int p=0;p<NP;p++) printf("%d %d %d\n",bo[p],bx[p],by[p]);
  return 0;
}
