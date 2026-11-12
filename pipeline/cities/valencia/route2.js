window.PL = __PL__;
window.ST3 = 'start';
(async () => {
const q = `[out:json][timeout:120];(way["railway"~"^(subway|light_rail|tram|narrow_gauge|rail)$"](38.95,-0.80,39.80,-0.15););out geom;`;
for (const u of ['https://overpass.private.coffee/api/interpreter','https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']) {
  try { window.ST3='fetch '+u; const t = await (await fetch(u,{method:'POST',body:'data='+encodeURIComponent(q),headers:{'Content-Type':'application/x-www-form-urlencoded'}})).text();
    if (t.trim()[0]==='{') { window.RAW = JSON.parse(t); break; } } catch(e) {}
}
if (!window.RAW) { window.ST3='no data'; return; }
window.ST3='routing';
const K = Math.cos(39.47*Math.PI/180), M = 111320, xy = p => [p[0]*K*M, p[1]*M], dd = (a,b) => Math.hypot(a[0]-b[0], a[1]-b[1]);
const ways = RAW.elements.filter(w => { const t = w.tags || {}; if (t.service === 'yard') return false;
  return /^(subway|tram|light_rail|narrow_gauge)$/.test(t.railway) || /(^|;)1000(;|$)/.test(t.gauge || ''); });
const C = new Map(), A = new Map(), TRAM = new Set(); let vid = -1;
const link = (a,b,w) => { if(!A.has(a)) A.set(a,[]); A.get(a).push([b,w]); };
for (const w of ways) {
  const tram = w.tags.railway === 'tram';
  for (let i=0;i<w.nodes.length;i++) { C.set(w.nodes[i], [w.geometry[i].lon, w.geometry[i].lat]); if (tram) TRAM.add(w.nodes[i]); }
  for (let i=1;i<w.nodes.length;i++) {
    const a=w.nodes[i-1], b=w.nodes[i], pa=C.get(a), pb=C.get(b), L=dd(xy(pa),xy(pb)), n=Math.floor(L/40);
    let prevId=a, prevP=pa;
    for (let k=1;k<=n;k++){ const f=k/(n+1), p=[pa[0]+(pb[0]-pa[0])*f, pa[1]+(pb[1]-pa[1])*f], id=vid--; C.set(id,p); if (tram) TRAM.add(id); const l=dd(xy(prevP),xy(p)); link(prevId,id,l); link(id,prevId,l); prevId=id; prevP=p; }
    const l=dd(xy(prevP),xy(pb)); link(prevId,b,l); link(b,prevId,l);
  }
}
const G = new Map(), cell = p => Math.floor(p[0]/0.002)+','+Math.floor(p[1]/0.002);
for (const [id,p] of C) { const k=cell(p); if(!G.has(k)) G.set(k,[]); G.get(k).push(id); }
function near(p, R, tram) { const out=[], cx=Math.floor(p[0]/0.002), cy=Math.floor(p[1]/0.002), P0=xy(p), rx=Math.ceil(R/170)+1, ry=Math.ceil(R/220)+1;
  for (let i=-rx;i<=rx;i++) for (let j=-ry;j<=ry;j++) for (const id of (G.get((cx+i)+','+(cy+j))||[])) {
    if (tram !== undefined && TRAM.has(id) !== tram) continue;
    const d=dd(P0,xy(C.get(id))); if (d<=R) out.push([id,d]); }
  return out.sort((a,b)=>a[1]-b[1]); }
for (const [id, nb] of [...A]) { if (nb.length !== 1 || id < 0) continue; const nbr = new Set(nb.map(x=>x[0]));
  for (const [o, d] of near(C.get(id), 30)) { if (o === id || nbr.has(o)) continue; link(id,o,d+5); link(o,id,d+5); break; } }
class H { constructor(){this.a=[];} push(x){const a=this.a;a.push(x);let i=a.length-1;while(i>0){const p=(i-1)>>1;if(a[p][0]<=a[i][0])break;[a[p],a[i]]=[a[i],a[p]];i=p;}}
  pop(){const a=this.a,t=a[0],l=a.pop();if(a.length){a[0]=l;let i=0;for(;;){let m=i;const L=2*i+1,R=L+1;if(L<a.length&&a[L][0]<a[m][0])m=L;if(R<a.length&&a[R][0]<a[m][0])m=R;if(m===i)break;[a[m],a[i]]=[a[i],a[m]];i=m;}}return t;} get size(){return this.a.length;} }
function dij(S, T, limit) {
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
const S = PL.stops, results = {}, ends = {}; // ends[station|line] = [node,...]
// fase 1: rota livre por (trecho, linha), com encaixe no tipo de via da linha
for (const [pair, lines] of Object.entries(PL.pl)) {
  const [a,b] = pair.split('|');
  for (const l of lines) {
    const tram = PL.mode[l] === 'tram'; let ids = null;
    for (const R of [150, 300, 500]) {
      const Sa = near(S[a], R, tram).slice(0,80).map(([id,d])=>[id,3*d]), Tb = new Map(near(S[b], R, tram).slice(0,80).map(([id,d])=>[id,3*d]));
      if (!Sa.length || !Tb.size) continue;
      ids = dij(Sa, Tb, 4*dd(xy(S[a]),xy(S[b]))+3000+6*R); if (ids) break;
    }
    if (!ids) continue;
    results[pair+'|'+l] = ids;
    (ends[a+'|'+l] ||= []).push(ids[0]); (ends[b+'|'+l] ||= []).push(ids[ids.length-1]);
  }
}
// fase 2: um único ponto por (estação, linha); refaz as rotas entre esses pontos
const canon = {};
for (const [k, list] of Object.entries(ends)) { const st = S[k.split('|')[0]]; canon[k] = list.slice().sort((x,y)=>dd(xy(C.get(x)),xy(st))-dd(xy(C.get(y)),xy(st)))[0]; }
let rerouted = 0, kept = 0;
for (const key of Object.keys(results)) {
  const [a,b,l] = key.split('|'); const na = canon[a+'|'+l], nb = canon[b+'|'+l];
  if (results[key][0] === na && results[key].at(-1) === nb) continue;
  const ids = dij([[na,0]], new Map([[nb,0]]), 6*dd(xy(S[a]),xy(S[b]))+5000);
  if (ids) { results[key] = ids; rerouted++; } else kept++;
}
function dp(pts, tol) { if (pts.length < 3) return pts; const X = pts.map(xy), keep = new Uint8Array(pts.length); keep[0]=keep[pts.length-1]=1; const st=[[0,pts.length-1]];
  while (st.length) { const [i,j]=st.pop(); let md=0, mi=-1; const a=X[i], b=X[j], dx=b[0]-a[0], dy=b[1]-a[1], L=Math.hypot(dx,dy)||1;
    for (let k=i+1;k<j;k++){ const d=Math.abs(dy*X[k][0]-dx*X[k][1]+b[0]*a[1]-b[1]*a[0])/L; if(d>md){md=d;mi=k;} } if (md>tol) { keep[mi]=1; st.push([i,mi],[mi,j]); } }
  return pts.filter((_,i)=>keep[i]); }
function enc(pts){let o='',pl=0,pn=0;const e=v=>{v=v<0?~(v<<1):(v<<1);let s='';while(v>=0x20){s+=String.fromCharCode((0x20|(v&0x1f))+63);v>>=5;}return s+String.fromCharCode(v+63);};for(const [lon,lat] of pts){const la=Math.round(lat*1e5),lo=Math.round(lon*1e5);o+=e(la-pl)+e(lo-pn);pl=la;pn=lo;}return o;}
// agrupa linhas com o mesmo traçado no mesmo trecho
const byPair = {};
for (const [key, ids] of Object.entries(results)) { const [a,b,l] = key.split('|'); const e = enc(dp(ids.map(i=>C.get(i)), 1.5));
  const g = (byPair[a+'|'+b] ||= {}); (g[e] ||= []).push(l); }
const lines = [];
for (const [pair, g] of Object.entries(byPair)) for (const [e, ls] of Object.entries(g)) lines.push(pair+'|'+ls.join(',')+':'+e);
window.ENC2 = lines.join('\n');
let miss = []; for (const [pair, ls] of Object.entries(PL.pl)) for (const l of ls) if (!results[pair+'|'+l]) miss.push(pair+'|'+l);
window.ST3 = JSON.stringify({done:true, rerouted, kept, miss, n: lines.length, len: ENC2.length});
})();
'started'
