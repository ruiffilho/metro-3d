import csv, json, math, collections, re, sys
SRC='/home/claude/sp_raw'
rd=lambda f: list(csv.DictReader(open(f'{SRC}/{f}',encoding='utf-8-sig')))
def sec(t): h,m,s=map(int,t.strip().split(':')); return h*3600+m*60+s
LAT=-23.55; K=math.cos(math.radians(LAT)); M=111320
xy=lambda p:(p[0]*K*M,p[1]*M)

routes={r['route_id']:r for r in rd('routes.txt') if r['route_type']!='3'}
def ref_of(rid):
    m=re.search(r'(\d+)',rid.replace('METRÔ17','METRÔ 17')); return 'L'+str(int(m.group(1)))
# cores oficiais (Metrô/CPTM)
COL={'L1':'#0455A1','L2':'#007E5E','L3':'#EE372F','L4':'#FFD400','L5':'#9B3894','L6':'#F37021',
     'L7':'#CA016B','L8':'#97A098','L9':'#01A9A7','L10':'#049FC3','L11':'#F68368','L12':'#133C8D','L13':'#00B352',
     'L15':'#9EA3A6','L17':'#D48500'}
MODE={'L15':'monotrilho','L17':'monotrilho'}
lines={}
for rid,r in routes.items():
    ref=ref_of(rid); lines[ref]={'color':COL.get(ref,'#'+r['route_color']),'mode':MODE.get(ref,'CPTM' if rid.startswith('CPTM') else 'metrô')}
trips={t['trip_id']:t for t in rd('trips.txt') if t['route_id'] in routes}
stops_all={s['stop_id']:s for s in rd('stops.txt')}
st=collections.defaultdict(list)
with open(f'{SRC}/stop_times.txt',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['trip_id'] in trips: st[r['trip_id']].append((int(r['stop_sequence']),r['stop_id'],sec(r['departure_time'] or r['arrival_time'])))
sidx={}; stops=[]
def S(sid):
    if sid not in sidx:
        s=stops_all[sid]; sidx[sid]=len(stops)
        name=s['stop_name'].strip()
        name=re.sub(r'\s*\((monotrilho)\)','',name,flags=re.I)
        stops.append([round(float(s['stop_lon']),6),round(float(s['stop_lat']),6),name])
    return sidx[sid]
patterns=[]; offsets=[]; patOf={}
for tid,rows in st.items():
    rows.sort(); t=trips[tid]; ref=ref_of(t['route_id'])
    patOf[tid]=len(patterns)
    patterns.append({'line':ref,'stops':[S(x[1]) for x in rows],'head':t['trip_headsign'].title(),'name':routes[t['route_id']]['route_long_name'].title()})
    offsets.append([x[2]-rows[0][2] for x in rows])
freq=[]
for f in rd('frequencies.txt'):
    if f['trip_id'] in patOf: freq.append([patOf[f['trip_id']],sec(f['start_time']),sec(f['end_time']),int(f['headway_secs'])])
# intervalos calibrados (dia útil): SPTrans traz picos de 60 s nas L1/L2 e L5/L15 esparsas demais
# (pico, entrepico, noite) em segundos
HW={'L1':(120,240,360),'L2':(150,300,420),'L3':(120,210,360),'L4':(100,210,300),
    'L5':(150,270,420),'L15':(240,480,600),'L12':(270,480,600)}
def hw_for(ref,hour,h0):
    if ref not in HW: return h0
    pk,ep,nt=HW[ref]
    if hour<5: return max(nt*2,h0)
    if hour==5: return nt
    if 6<=hour<9 or 17<=hour<20: return pk
    if hour>=21: return nt
    return ep
freq=[[p,a,b,hw_for(patterns[p]['line'],a//3600,h)] for p,a,b,h in freq]
tripCount=[0]*len(patterns)
for p,a,b,h in freq: tripCount[p]+=(b-a+60)//h

# ---- geometria: shapes do GTFS como candidatos, trecho a trecho
shp_ids={t['shape_id'] for t in trips.values()}
sh=collections.defaultdict(list)
with open(f'{SRC}/shapes.txt',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['shape_id'] in shp_ids: sh[r['shape_id']].append((int(r['shape_pt_sequence']),float(r['shape_pt_lon']),float(r['shape_pt_lat'])))
cands={}
for k,v in sh.items():
    ll=[(x,y) for _,x,y in sorted(v)]; X=[xy(p) for p in ll]; cum=[0]
    for i in range(1,len(X)): cum.append(cum[-1]+math.hypot(X[i][0]-X[i-1][0],X[i][1]-X[i-1][1]))
    cands[k]=(ll,X,cum)
shapeLine={t['shape_id']:ref_of(t['route_id']) for t in trips.values()}
def project(c,P):
    ll,X,cum=c; best=(1e18,0,0,0)
    for i in range(len(X)-1):
        a,b=X[i],X[i+1]; dx,dy=b[0]-a[0],b[1]-a[1]; L=dx*dx+dy*dy
        t=0 if L==0 else max(0,min(1,((P[0]-a[0])*dx+(P[1]-a[1])*dy)/L))
        q=(a[0]+t*dx,a[1]+t*dy); d=math.hypot(P[0]-q[0],P[1]-q[1])
        if d<best[0]: best=(d,i,t,cum[i]+t*math.sqrt(L))
    return best
def lerp(c,pr): ll=c[0]; a,b=ll[pr[1]],ll[pr[1]+1]; t=pr[2]; return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
def sub(c,pa,pb):
    if pa[3]<=pb[3]:
        return [lerp(c,pa)]+[c[0][i] for i in range(pa[1]+1,pb[1]+1)]+[lerp(c,pb)]
    return sub(c,pb,pa)[::-1]
def despike(pts):
    # remove idas-e-voltas: trechos em que o traçado sai e volta quase ao mesmo ponto
    P=[xy(p) for p in pts]; i=0; out=[pts[0]]; n=len(pts)
    while i<n-1:
        jump=None
        for j in range(n-1,i+1,-1):
            dij=math.hypot(P[j][0]-P[i][0],P[j][1]-P[i][1])
            if dij<35:
                far=max(math.hypot(P[k][0]-P[i][0],P[k][1]-P[i][1]) for k in range(i+1,j))
                if far>dij+12: jump=j; break
        if jump: i=jump
        else: i+=1
        out.append(pts[i])
    # remove pontas agudas (virada > 150°)
    changed=True
    while changed and len(out)>2:
        changed=False
        for k in range(1,len(out)-1):
            a,b,c=xy(out[k-1]),xy(out[k]),xy(out[k+1])
            v1=(b[0]-a[0],b[1]-a[1]); v2=(c[0]-b[0],c[1]-b[1]); l1=math.hypot(*v1); l2=math.hypot(*v2)
            if l1>0 and l2>0 and (v1[0]*v2[0]+v1[1]*v2[1])/(l1*l2)<-0.5: del out[k]; changed=True; break
    return out
def chaikin(pts,it=2):
    for _ in range(it):
        if len(pts)<3: return pts
        out=[pts[0]]
        for i in range(len(pts)-1):
            a,b=pts[i],pts[i+1]
            out.append((0.75*a[0]+0.25*b[0],0.75*a[1]+0.25*b[1])); out.append((0.25*a[0]+0.75*b[0],0.25*a[1]+0.75*b[1]))
        out.append(pts[-1]); pts=out
    return pts
segs={}; bad=[]
pairLines=collections.defaultdict(set)
for p in patterns:
    for a_,b_ in zip(p['stops'],p['stops'][1:]): pairLines[(min(a_,b_),max(a_,b_))].add(p['line'])
# trilhos do OpenStreetMap (roteados no grafo de trilhos, ver route_sp.js)
def dec(s):
    i=lat=lon=0; out=[]
    while i<len(s):
        v=[]
        for _ in range(2):
            sh=r=0
            while True:
                c=ord(s[i])-63; i+=1; r|=(c&0x1f)<<sh; sh+=5
                if c<0x20: break
            v.append(~(r>>1) if r&1 else r>>1)
        lat+=v[0]; lon+=v[1]; out.append([round(lon/1e5,6),round(lat/1e5,6)])
    return out
osm={}
for line in open('/home/claude/build/sp/enc/all.txt').read().split('\n'):
    k,e=line.split(':',1); a_,b_,ls=k.split('|')
    osm.setdefault((int(a_),int(b_)),dec(e))
for (a,b),ls in pairLines.items():
    if (a,b) in osm: segs[f'{a}|{b}']=osm[(a,b)]
    else: bad.append((stops[a][2],stops[b][2])); segs[f'{a}|{b}']=[stops[a][:2],stops[b][:2]]
print('pairs',len(segs),'sem trilho',bad)
G={'meta':{},'stops':stops,'lines':lines,'patterns':patterns,'offsets':offsets,'freq':freq,'tripCount':tripCount,'segs':segs}
json.dump(G,open('/home/claude/build/sp/gtfs_sp.json','w'),ensure_ascii=False,separators=(',',':'))
print('patterns',len(patterns),'stops',len(stops),'lines',sorted(lines,key=lambda x:int(x[1:])))
