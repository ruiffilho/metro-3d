window.PL = __PL__;
window.ST = 'start';
(async () => {
const q = `[out:json][timeout:180];(way["railway"~"^(subway|light_rail|monorail|rail)$"](-23.85,-47.05,-23.0,-46.1););out geom;`;
for (const u of ['https://overpass.private.coffee/api/interpreter','https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']) {
  try { window.ST='fetch '+u; const t = await (await fetch(u,{method:'POST',body:'data='+encodeURIComponent(q),headers:{'Content-Type':'application/x-www-form-urlencoded'}})).text();
    if (t.trim()[0]==='{') { window.RAW = JSON.parse(t); break; } else window.ST='bad '+u+' '+t.slice(0,60); } catch(e) { window.ST='err '+e; }
}
if (!window.RAW) { window.ST='no data'; return; }
window.ST='routing';
const K = Math.cos(-23.55*Math.PI/180), M = 111320, xy = p => [p[0]*K*M, p[1]*M], dd = (a,b) => Math.hypot(a[0]-b[0], a[1]-b[1]);
const famOf = w => { const r = w.tags.railway; if (w.tags.service === 'yard') return null; return r === 'monorail' ? 'mono' : (r === 'rail' ? 'cptm' : 'metro'); };
const NET = {};
for (const f of ['metro','mono','cptm']) NET[f] = { C: new Map(), A: new Map(), G: new Map() };
let vid = -1;
for (const w of RAW.elements) {
  const f = famOf(w); if (!f) continue; const {C, A} = NET[f];
  const link = (a,b,l) => { if(!A.has(a)) A.set(a,[]); A.get(a).push([b,l]); };
  for (let i=0;i<w.nodes.length;i++) C.set(w.nodes[i], [w.geometry[i].lon, w.geometry[i].lat]);
  for (let i=1;i<w.nodes.length;i++) {
    const a=w.nodes[i-1], b=w.nodes[i], pa=C.get(a), pb=C.get(b), L=dd(xy(pa),xy(pb)), n=Math.floor(L/40);
    let prevId=a, prevP=pa;
    for (let k=1;k<=n;k++){ const t=k/(n+1), p=[pa[0]+(pb[0]-pa[0])*t, pa[1]+(pb[1]-pa[1])*t], id=vid--; C.set(id,p); const l=dd(xy(prevP),xy(p)); link(prevId,id,l); link(id,prevId,l); prevId=id; prevP=p; }
    const l=dd(xy(prevP),xy(pb)); link(prevId,b,l); link(b,prevId,l);
  }
}
const cell = p => Math.floor(p[0]/0.002)+','+Math.floor(p[1]/0.002);
for (const f in NET) for (const [id,p] of NET[f].C) { const k=cell(p); if(!NET[f].G.has(k)) NET[f].G.set(k,[]); NET[f].G.get(k).push(id); }
function near(f, p, R) { const {C,G}=NET[f]; const out=[], cx=Math.floor(p[0]/0.002), cy=Math.floor(p[1]/0.002), P0=xy(p), rx=Math.ceil(R/200)+1, ry=Math.ceil(R/220)+1;
  for (let i=-rx;i<=rx;i++) for (let j=-ry;j<=ry;j++) for (const id of (G.get((cx+i)+','+(cy+j))||[])) { const d=dd(P0,xy(C.get(id))); if (d<=R) out.push([id,d]); }
  return out.sort((a,b)=>a[1]-b[1]); }
for (const f in NET) { const {C,A}=NET[f];
  for (const [id, nb] of [...A]) { if (nb.length !== 1 || id < 0) continue; const nbr = new Set(nb.map(x=>x[0]));
    for (const [o, d] of near(f, C.get(id), 30)) { if (o === id || nbr.has(o)) continue; A.get(id).push([o,d+5]); if(!A.has(o)) A.set(o,[]); A.get(o).push([id,d+5]); break; } } }
class H { constructor(){this.a=[];} push(x){const a=this.a;a.push(x);let i=a.length-1;while(i>0){const p=(i-1)>>1;if(a[p][0]<=a[i][0])break;[a[p],a[i]]=[a[i],a[p]];i=p;}}
  pop(){const a=this.a,t=a[0],l=a.pop();if(a.length){a[0]=l;let i=0;for(;;){let m=i;const L=2*i+1,R=L+1;if(L<a.length&&a[L][0]<a[m][0])m=L;if(R<a.length&&a[R][0]<a[m][0])m=R;if(m===i)break;[a[m],a[i]]=[a[i],a[m]];i=m;}}return t;} get size(){return this.a.length;} }
function dij(f, S, T, limit) { const A=NET[f].A;
  const dist = new Map(), prev = new Map(), h = new H();
  for (const [id,d] of S) { dist.set(id, d); h.push([d, id]); }
  let best = null, bestC = Infinity;
  while (h.size) { const [c,u] = h.pop(); if (c > (dist.get(u) ?? Infinity) + 1e-9) continue; if (c >= bestC || c > limit) break;
    if (T.has(u)) { const tc = c + T.get(u); if (tc < bestC) { bestC = tc; best = u; } }
    for (const [v,w] of A.get(u) || []) { const nc = c + w; if (nc < (dist.get(v) ?? Infinity)) { dist.set(v,nc); prev.set(v,u); h.push([nc,v]); } } }
  if (best === null) return null;
  const ids = []; let n = best; while (n !== undefined) { ids.push(n); n = prev.get(n); }
  return ids.reverse();
}
const S = PL.stops, results = {}, ends = {};
for (const [pair, lines] of Object.entries(PL.pl)) {
  const [a,b] = pair.split('|');
  for (const l of lines) {
    const f = PL.fam[l]; let ids = null;
    for (const R of [150, 300, 600]) {
      const Sa = near(f, S[a], R).slice(0,80).map(([id,d])=>[id,3*d]), Tb = new Map(near(f, S[b], R).slice(0,80).map(([id,d])=>[id,3*d]));
      if (!Sa.length || !Tb.size) continue;
      ids = dij(f, Sa, Tb, 4*dd(xy(S[a]),xy(S[b]))+3000+6*R); if (ids) break;
    }
    if (!ids) continue;
    results[pair+'|'+l] = ids;
    (ends[a+'|'+l] ||= []).push(ids[0]); (ends[b+'|'+l] ||= []).push(ids[ids.length-1]);
  }
}
const canon = {};
for (const [k, list] of Object.entries(ends)) { const [st,l] = k.split('|'); const C = NET[PL.fam[l]].C; canon[k] = list.slice().sort((x,y)=>dd(xy(C.get(x)),xy(S[st]))-dd(xy(C.get(y)),xy(S[st])))[0]; }
for (const key of Object.keys(results)) {
  const [a,b,l] = key.split('|'); const na = canon[a+'|'+l], nb = canon[b+'|'+l];
  if (results[key][0] === na && results[key].at(-1) === nb) continue;
  const ids = dij(PL.fam[l], [[na,0]], new Map([[nb,0]]), 6*dd(xy(S[a]),xy(S[b]))+5000);
  if (ids) results[key] = ids;
}
function dp(pts, tol) { if (pts.length < 3) return pts; const X = pts.map(xy), keep = new Uint8Array(pts.length); keep[0]=keep[pts.length-1]=1; const st=[[0,pts.length-1]];
  while (st.length) { const [i,j]=st.pop(); let md=0, mi=-1; const a=X[i], b=X[j], dx=b[0]-a[0], dy=b[1]-a[1], L=Math.hypot(dx,dy)||1;
    for (let k=i+1;k<j;k++){ const d=Math.abs(dy*X[k][0]-dx*X[k][1]+b[0]*a[1]-b[1]*a[0])/L; if(d>md){md=d;mi=k;} } if (md>tol) { keep[mi]=1; st.push([i,mi],[mi,j]); } }
  return pts.filter((_,i)=>keep[i]); }
function enc(pts){let o='',pl=0,pn=0;const e=v=>{v=v<0?~(v<<1):(v<<1);let s='';while(v>=0x20){s+=String.fromCharCode((0x20|(v&0x1f))+63);v>>=5;}return s+String.fromCharCode(v+63);};for(const [lon,lat] of pts){const la=Math.round(lat*1e5),lo=Math.round(lon*1e5);o+=e(la-pl)+e(lo-pn);pl=la;pn=lo;}return o;}
const byPair = {};
for (const [key, ids] of Object.entries(results)) { const [a,b,l] = key.split('|'); const C = NET[PL.fam[l]].C; const e = enc(dp(ids.map(i=>C.get(i)), 2.5));
  const g = (byPair[a+'|'+b] ||= {}); (g[e] ||= []).push(l); }
const lines = []; for (const [pair, g] of Object.entries(byPair)) for (const [e, ls] of Object.entries(g)) lines.push(pair+'|'+ls.join(',')+':'+e);
window.ENC = lines.join('\n');
const miss = []; for (const [pair, ls] of Object.entries(PL.pl)) for (const l of ls) if (!results[pair+'|'+l]) miss.push(pair+'|'+l);
const ratios = []; for (const [key, ids] of Object.entries(results)) { const [a,b,l]=key.split('|'); const C = NET[PL.fam[l]].C; let L=0; for (let i=1;i<ids.length;i++) L+=dd(xy(C.get(ids[i-1])),xy(C.get(ids[i]))); ratios.push([key, +(L/Math.max(1,dd(xy(S[a]),xy(S[b])))).toFixed(2)]); }
window.ST = JSON.stringify({ done: true, miss, n: lines.length, len: ENC.length, worst: ratios.sort((x,y)=>y[1]-x[1]).slice(0,8), ways: RAW.elements.length });
})();
'started'
