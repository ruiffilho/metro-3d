import json, math, itertools, collections
G=json.load(open('gtfs.json'))
K=math.cos(math.radians(39.47)); M=111320
xy=lambda p:(p[0]*K*M,p[1]*M)
pats=G['patterns']; key=lambda a,b:f"{min(a,b)}|{max(a,b)}"
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
def nearby(P, R=14):
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
                if abs(dot)>0.7: votes[(min(l,l2,key=int),max(l,l2,key=int))]+= 1 if dot>0 else -1
flip={}
lines=sorted(G['lines'],key=int)
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
        near=[{l:v for l,v in nearby(xy(p)).items() if G['lines'][l]['mode']==mode} for p in pts]
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
for grp in ([l for l in lines if G['lines'][l]['mode']=='metro'],[l for l in lines if G['lines'][l]['mode']=='tram']):
    best=None
    for perm in itertools.permutations(grp):
        pos={l:i for i,l in enumerate(perm)}
        cost=sum(w for (X,Y),w in cons.items() if X in pos and Y in pos and pos[X]<pos[Y])
        if best is None or cost<best[0]: best=(cost,perm)
    print(grp,best)
    for i,l in enumerate(best[1]): rank[l]=i

# 6) por vértice: orientação (o) e fator de faixa por linha (f), suavizados
segO={}; segF={}
for k,pts in dense.items():
    Ls=segLines.get(k,set()); n=len(pts)
    o=[]; fl={l:[] for l in Ls}
    for i,p in enumerate(pts):
        tc0=tang(pts,i); mode=G['lines'][next(iter(Ls))]['mode'] if Ls else None
        nb={l:v for l,v in nearby(xy(p)).items() if G['lines'][l]['mode']==mode and abs(tc0[0]*v[2][0]+tc0[1]*v[2][1])>0.8}
        present=sorted(set(nb)|Ls, key=lambda l:rank[l])
        r=present[0]; tr=ref(r, nb[r][2]) if r in nb else None
        tc=tang(pts,i)
        if tr is None:
            sg=lineSign[r].get(k,1)*flip[r]; tr=(tc[0]*sg,tc[1]*sg)
        o.append(1 if tc[0]*tr[0]+tc[1]*tr[1]>=0 else -1)
        for l in Ls: fl[l].append(present.index(l)-(len(present)-1)/2)
    # suaviza f (janela ±3)
    for l in Ls:
        f=fl[l]; fl[l]=[round(sum(f[max(0,i-3):i+4])/len(f[max(0,i-3):i+4]),2) for i in range(n)]
    segO[k]=''.join('+' if x>0 else '-' for x in o); segF[k]=fl
G['segs']=dense; G['segO']=segO; G['segF']=segF; G.pop('lanes',None)
json.dump(G,open('gtfs.json','w'),ensure_ascii=False,separators=(',',':'))
print('pts',sum(len(v) for v in dense.values()), 'bytes', len(json.dumps(G,separators=(',',':'),ensure_ascii=False)))
