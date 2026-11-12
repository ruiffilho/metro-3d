import csv, json, math, collections
R='/home/claude/lx_raw/carris'
rd=lambda f: list(csv.DictReader(open(f'{R}/{f}',encoding='utf-8-sig')))
G=json.load(open('gtfs_lx_base.json')); CM=json.load(open('carmap.json'))
K=math.cos(math.radians(38.72)); M=111320
xy=lambda p:(p[0]*K*M,p[1]*M)
TRAM={'12E','15E','18E','24E','25E','28E'}
routes={r['route_id'] for r in rd('routes.txt') if r['route_short_name'] in TRAM}
S={s['stop_id']:s for s in rd('stops.txt')}
idx={(round(float(s[0]),6),round(float(s[1]),6)):i for i,s in enumerate(G['stops'])}
trips={t['trip_id']:t['shape_id'] for t in rd('trips.txt') if t['route_id'] in routes}
st=collections.defaultdict(list)
for r in csv.DictReader(open(f'{R}/stop_times.txt',encoding='utf-8-sig')):
    if r['trip_id'] in trips: st[r['trip_id']].append((int(r['stop_sequence']),r['stop_id']))
sh=collections.defaultdict(list)
need=set(trips.values())
for r in csv.DictReader(open(f'{R}/shapes.txt',encoding='utf-8-sig')):
    if r['shape_id'] in need: sh[r['shape_id']].append((int(r['shape_pt_sequence']),float(r['shape_pt_lon']),float(r['shape_pt_lat'])))
shapes={k:[(x,y) for _,x,y in sorted(v)] for k,v in sh.items()}
def proj(X,P,start):
    best=(1e18,start,0.0)
    for i in range(start,len(X)-1):
        a,b=X[i],X[i+1]; dx,dy=b[0]-a[0],b[1]-a[1]; L=dx*dx+dy*dy
        t=0 if L==0 else max(0,min(1,((P[0]-a[0])*dx+(P[1]-a[1])*dy)/L))
        d=math.hypot(P[0]-a[0]-t*dx,P[1]-a[1]-t*dy)
        if d<best[0]-1e-9: best=(d,i,t)
        if best[0]<15 and d>best[0]+400: break   # já passou do ponto mais próximo
    return best
segs={}
for tid,rows in st.items():
    rows.sort(); ll=shapes.get(trips[tid])
    if not ll: continue
    X=[xy(p) for p in ll]
    seq=[CM.get(s) for _,s in rows]
    seq=[x for i,x in enumerate(seq) if i==0 or x!=seq[i-1]]
    if None in seq: continue
    pos=0; prevpt=None; prev=None
    for k,si in enumerate(seq):
        d,i,t=proj(X,xy(G['stops'][si]),pos)
        a,b=ll[i],ll[i+1]; pt=[round(a[0]+(b[0]-a[0])*t,6),round(a[1]+(b[1]-a[1])*t,6)]
        if prev is not None and prev!=si:
            pts=[prevpt[1]]+[list(map(lambda v:round(v,6),ll[j])) for j in range(prevpt[0]+1,i+1)]+[pt]
            key=f'{min(prev,si)}|{max(prev,si)}'
            if prev>si: pts=pts[::-1]
            if key not in segs or len(pts)>len(segs[key]): segs[key]=pts
        prev=si; prevpt=(i,pt); pos=i
json.dump(segs,open('tram_segs.json','w'))
pl=json.load(open('pl_lx.json'))['pl']
tram={k for k,v in pl.items() if any(l in ('41','42','43','44','45','46') for l in v)}
print('tram pairs',len(tram),'got',len(tram&set(segs)),'missing',sorted(tram-set(segs))[:10])
