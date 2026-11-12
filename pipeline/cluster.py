import json, math, sys
path=sys.argv[1]; LAT=float(sys.argv[2])
G=json.load(open(path))
K=math.cos(math.radians(LAT)); M=111320
def d(a,b): return math.hypot((a[0]-b[0])*K*M,(a[1]-b[1])*M)
segs=G['segs']
def ep_pt(k,end): return segs[k][0] if end==0 else segs[k][-1]
def ep_of(a,b): k=f"{min(a,b)}|{max(a,b)}"; return (k,0) if a<b else (k,1)
def ep_at_end(a,b): k=f"{min(a,b)}|{max(a,b)}"; return (k,1) if a<b else (k,0)
parent={}
def find(x):
    parent.setdefault(x,x)
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
for k in segs: find((k,0)); find((k,1))
for p in G['patterns']:
    s=p['stops']
    for i in range(len(s)-2):
        e1=ep_at_end(s[i],s[i+1]); e2=ep_of(s[i+1],s[i+2])
        if d(ep_pt(*e1),ep_pt(*e2))<200: parent[find(e1)]=find(e2)
groups={}
for x in list(parent): groups.setdefault(find(x),[]).append(x)
pos={}
for g in groups.values():
    pts=[ep_pt(*e) for e in g]; c=[round(sum(p[0] for p in pts)/len(pts),6), round(sum(p[1] for p in pts)/len(pts),6)]
    for (k,end) in g:
        if end==0: segs[k][0]=c
        else: segs[k][-1]=c
    a,b=map(int,g[0][0].split('|')); st=a if g[0][1]==0 else b
    dist=d(c,G['stops'][st])
    if st not in pos or dist<pos[st][1]: pos[st]=(c,dist)
for st,(c,_) in pos.items(): G['stops'][st][0],G['stops'][st][1]=c
json.dump(G,open(path,'w'),ensure_ascii=False,separators=(',',':'))
print('groups',len(groups))
