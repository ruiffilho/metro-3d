import json, math, itertools, collections
import sys, re
nk=lambda l:int(re.sub(r'\D','',str(l)) or 0)
PATH=sys.argv[1] if len(sys.argv)>1 else 'gtfs.json'
G=json.load(open(PATH))
K=math.cos(math.radians(float(sys.argv[2]) if len(sys.argv)>2 else 39.47)); M=111320
xy=lambda p:(p[0]*K*M,p[1]*M)
pats=G['patterns']; key=lambda a,b:f"{min(a,b)}|{max(a,b)}"
if 'tripCount' in G: tp=list(G['tripCount'])
else:
    tp=[0]*len(pats)
    for rows in G['services'].values():
        for r in rows: tp[r[0]]+=1
cnt=collections.defaultdict(collections.Counter)
for i,p in enumerate(pats):
    for a,b in zip(p['stops'],p['stops'][1:]): cnt[key(a,b)][p['line']]+=tp[i]
segLines={k:{l for l,c in v.items() if c>=max(20,0.15*max(v.values()))} for k,v in cnt.items()}

# 1) densifica (20 m)
dense={}
for k,pts in G['segs'].items():
    out=[pts[0]]
    for q in pts[1:]:
        p=out[-1]; A,B=xy(p),xy(q); L=math.hypot(B[0]-A[0],B[1]-A[1]); n=int(L//20)
        for i in range(1,n+1):
            t=i/(n+1); out.append([round(p[0]+(q[0]-p[0])*t,6), round(p[1]+(q[1]-p[1])*t,6)])
        out.append(q)
    dense[k]=out
def tang(pts,i):
    a=xy(pts[max(0,i-1)]); b=xy(pts[min(len(pts)-1,i+1)]); v=(b[0]-a[0],b[1]-a[1]); L=math.hypot(*v) or 1; return (v[0]/L,v[1]/L)

# 2) orientação de cada trecho no sentido de referência de cada linha
lineSign=collections.defaultdict(dict)  # line -> seg -> +1 if ref goes a->b
for l in G['lines']:
    lp=[(i,p) for i,p in enumerate(pats) if p['line']==l]
    lp.sort(key=lambda x:-len(x[1]['stops']))
    adj=collections.defaultdict(list)
    for i,p in lp:
        s=p['stops']
        for k in range(len(s)-2):
            a,b,c=s[k],s[k+1],s[k+2]; k1,k2=key(a,b),key(b,c)
            if k1==k2: continue
            rel=(1 if a<b else -1)*(1 if b<c else -1); adj[k1].append((k2,rel)); adj[k2].append((k1,rel))
    sg=lineSign[l]
    for i,p in lp:
        s=p['stops']; a,b=s[0],s[1]; k0=key(a,b)
        if k0 in sg: continue
        sg[k0]=1 if a<b else -1; q=collections.deque([k0])
        while q:
            u=q.popleft()
            for v,rel in adj[u]:
                if v not in sg: sg[v]=sg[u]*rel; q.append(v)

# 3) amostras por linha (grade espacial)
CELL=30
grid=collections.defaultdict(list)
for k,pts in dense.items():
    for l in segLines.get(k,()):
        sg=lineSign[l].get(k,1)
        for i,p in enumerate(pts):
            P=xy(p); t=tang(pts,i)
            grid[(int(P[0]//CELL),int(P[1]//CELL))].append((l,P,(t[0]*sg,t[1]*sg)))
RAD=float(sys.argv[3]) if len(sys.argv)>3 else 14
CROSS=len(sys.argv)>4 and sys.argv[4]=='1'
WIN=int(sys.argv[5]) if len(sys.argv)>5 else 3
def nearby(P, R=None):
    R=R or RAD
    cx,cy=int(P[0]//CELL),int(P[1]//CELL); best={}
    for i in (-1,0,1):
        for j in (-1,0,1):
            for l,Q,t in grid.get((cx+i,cy+j),()):
                d=math.hypot(P[0]-Q[0],P[1]-Q[1])
                if d<=R and (l not in best or d<best[l][0]): best[l]=(d,Q,t)
    return best

# 4) sinais globais das linhas (para que as referências concordem nos corredores)
votes=collections.Counter()
for k,pts in dense.items():
    for l in segLines.get(k,()):
        sg=lineSign[l].get(k,1)
        for i,p in enumerate(pts[::3]):
            ii=i*3; t=tang(pts,ii); t=(t[0]*sg,t[1]*sg)
            for l2,(d,Q,t2) in nearby(xy(p)).items():
                if l2==l: continue
                dot=t[0]*t2[0]+t[1]*t2[1]
                if abs(dot)>0.7: votes[(min(l,l2,key=nk),max(l,l2,key=nk))]+= 1 if dot>0 else -1
flip={}
lines=sorted(G['lines'],key=nk)
for l0 in lines:
    if l0 in flip: continue
    flip[l0]=1; q=collections.deque([l0])
    while q:
        u=q.popleft()
        for (a,b),v in votes.items():
            if v==0 or u not in (a,b): continue
            o=b if u==a else a
            if o not in flip: flip[o]=flip[u]*(1 if v>0 else -1); q.append(o)
print('flip',flip)
def ref(l,t): return (t[0]*flip[l],t[1]*flip[l])

# 5) restrições de lado onde linhas se separam/juntam
cons=collections.Counter()
for k,pts in dense.items():
    for X in segLines.get(k,()):
        sg=lineSign[X].get(k,1)
        mode=G['lines'][X]['mode']
        near=[]
        for ii,p in enumerate(pts):
            tcc=tang(pts,ii)
            near.append({l:v for l,v in nearby(xy(p)).items() if (CROSS or G['lines'][l]['mode']==mode) and abs(tcc[0]*v[2][0]+tcc[1]*v[2][1])>0.8})
        for i in range(len(pts)):
            for Y,(d,Q,tY) in near[i].items():
                if Y==X: continue
                # olha à frente/atrás ~100 m: se X se afasta de Y, de que lado fica?
                for j in (i+5,i-5):
                    if 0<=j<len(pts) and Y not in near[j]:
                        P=xy(pts[j]); tY2=ref(Y,tY)
                        cr=tY2[0]*(P[1]-Q[1])-tY2[1]*(P[0]-Q[0])
                        if abs(cr)>15: cons[(X,Y) if cr>0 else (Y,X)]+=1   # primeiro fica à esquerda
print('cons',{k:v for k,v in cons.items() if v>2})
rank={}
groups=[lines] if CROSS else [[l for l in lines if G['lines'][l]['mode']==m] for m in sorted({v['mode'] for v in G['lines'].values()})]
def costf(perm):
    pos={l:i for i,l in enumerate(perm)}
    return sum(w for (X,Y),w in cons.items() if X in pos and Y in pos and pos[X]<pos[Y])
for grp in groups:
    if len(grp)<=8:
        best=min(((costf(p),p) for p in itertools.permutations(grp)), key=lambda x:x[0])
    else:
        # busca local: move cada linha para a melhor posição até não melhorar
        cur=list(grp); c=costf(cur); improved=True
        while improved:
            improved=False
            for l in list(cur):
                base=[x for x in cur if x!=l]
                for i in range(len(base)+1):
                    cand=base[:i]+[l]+base[i:]; cc=costf(cand)
                    if cc<c: cur,c,improved=cand,cc,True
        best=(c,tuple(cur))
    print(grp,best)
    for i,l in enumerate(best[1]): rank[l]=i

# 6) por vértice: orientação (o) e fator de faixa por linha (f), suavizados
segO={}; segF={}
BUNDLE=len(sys.argv)>6 and sys.argv[6]=='1'
newpts={}
inv=lambda P:[round(P[0]/(K*M),6), round(P[1]/M,6)]
for k,pts in dense.items():
    Ls=segLines.get(k,set()); n=len(pts)
    o=[]; fl={l:[] for l in Ls}; cen=[]
    for i,p in enumerate(pts):
        tc0=tang(pts,i); mode=G['lines'][next(iter(Ls))]['mode'] if Ls else None
        nb={l:v for l,v in nearby(xy(p)).items() if (CROSS or G['lines'][l]['mode']==mode) and abs(tc0[0]*v[2][0]+tc0[1]*v[2][1])>0.8}
        present=sorted(set(nb)|Ls, key=lambda l:rank[l])
        r=present[0]; tr=ref(r, nb[r][2]) if r in nb else None
        tc=tang(pts,i)
        if tr is None:
            sg=lineSign[r].get(k,1)*flip[r]; tr=(tc[0]*sg,tc[1]*sg)
        o.append(1 if tc[0]*tr[0]+tc[1]*tr[1]>=0 else -1)
        for l in Ls: fl[l].append(present.index(l)-(len(present)-1)/2)
        # centro do corredor: média deste trilho com os trilhos paralelos vizinhos
        P=xy(p); qs=[P]+[v[1] for l2,v in nb.items() if l2 not in Ls]
        cen.append((sum(q[0] for q in qs)/len(qs), sum(q[1] for q in qs)/len(qs)))
    # suaviza f (janela ±3)
    for l in Ls:
        f=fl[l]; fl[l]=[round(sum(f[max(0,i-WIN):i+WIN+1])/len(f[max(0,i-WIN):i+WIN+1]),2) for i in range(n)]
    segO[k]=''.join('+' if x>0 else '-' for x in o); segF[k]=fl
    if BUNDLE:
        sm=[cen[0]]+[(sum(c[0] for c in cen[max(0,i-WIN):i+WIN+1])/len(cen[max(0,i-WIN):i+WIN+1]),
                      sum(c[1] for c in cen[max(0,i-WIN):i+WIN+1])/len(cen[max(0,i-WIN):i+WIN+1])) for i in range(1,n-1)]+[cen[-1]]
        newpts[k]=[inv(c) for c in sm]
if BUNDLE:
    dense=newpts
    # estações acompanham o novo traçado
    for k,v in dense.items():
        a,b=map(int,k.split('|')); G['stops'][a][0],G['stops'][a][1]=v[0]; G['stops'][b][0],G['stops'][b][1]=v[-1]
G['segs']=dense; G['segO']=segO; G['segF']=segF; G.pop('lanes',None)
json.dump(G,open(PATH,'w'),ensure_ascii=False,separators=(',',':'))
print('pts',sum(len(v) for v in dense.values()), 'bytes', len(json.dumps(G,separators=(',',':'),ensure_ascii=False)))
