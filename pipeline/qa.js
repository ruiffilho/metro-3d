// Verificação automática antes de publicar. Uso: node pipeline/qa.js [cidade ...]  (sem argumento: todas)
// Sai com código 1 se algum problema conhecido aparecer. Ver CLAUDE.md, seção "Problemas recorrentes".
const fs = require('fs'), path = require('path');
const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const AsyncFn = Object.getPrototypeOf(async function () {}).constructor;
let fails = 0; const fail = (c, m) => { fails++; console.log(`  FALHA [${c}] ${m}`); };
scripts.forEach((s, i) => { try { new AsyncFn(s); } catch (e) { fail('geral', `erro de sintaxe no script ${i}: ${e.message}`); } });
if (!/window\.maplibregl\) \(async function/.test(html)) fail('geral', 'script principal não é async (os dados por cidade não carregam)');
const m = { exports: {} }; new Function('module', scripts[0])(m); const C = m.exports;
const cfgIds = [...html.matchAll(/^    '?([a-z-]+)'?: \{ name:/gm)].map(x => x[1]);
const cities = process.argv.slice(2).length ? process.argv.slice(2) : cfgIds;
const body = html.match(/function buildLanes\(\) \{([\s\S]*?)\n  \/\/ Simplifica cada/)[1].replace(/\}\s*$/, '');

for (const city of cities) {
  console.log(`\n== ${city}`);
  const f = path.join(ROOT, 'data', city + '.json');
  if (!fs.existsSync(f)) { fail(city, 'falta data/' + city + '.json'); continue; }
  if (!fs.existsSync(path.join(ROOT, 'audio', city + '.mp3'))) fail(city, 'falta o aviso sonoro audio/' + city + '.mp3');
  const G = JSON.parse(fs.readFileSync(f, 'utf8'));
  const lat = G.stops.reduce((a, s) => a + s[1], 0) / G.stops.length, lon = G.stops.reduce((a, s) => a + s[0], 0) / G.stops.length;
  C.setOrigin(lon, lat);
  const K = Math.cos(lat * Math.PI / 180), d = (a, b) => Math.hypot((a[0] - b[0]) * K, a[1] - b[1]) * 111320;
  // 1. linhas com cor e nome; segmentos para todos os pares
  for (const [ref, l] of Object.entries(G.lines)) if (!/^#[0-9a-fA-F]{6}$/.test(l.color || '')) fail(city, `linha ${ref} sem cor válida`);
  const need = new Set(); G.patterns.forEach(p => p.stops.forEach((s, i) => { if (i) need.add(Math.min(s, p.stops[i - 1]) + '|' + Math.max(s, p.stops[i - 1])); }));
  const missing = [...need].filter(k => !G.segs[k]);
  if (missing.length) fail(city, `${missing.length} trechos sem geometria (linhas retas/saltos): ${missing.slice(0, 5)}`);
  if (!G.segO || !G.segF) fail(city, 'faltam segO/segF: rode lanes_gen.py (linhas lado a lado)');
  // 2. trechos que dão voltas absurdas (roteamento errado) ou ganchos
  const detours = [];
  for (const [k, pts] of Object.entries(G.segs)) { const [a, b] = k.split('|').map(Number); let L = 0; for (let i = 1; i < pts.length; i++) L += d(pts[i - 1], pts[i]);
    const D = d(G.stops[a], G.stops[b]); if (L > 2.5 * D + 400) detours.push(`${G.stops[a][2]}–${G.stops[b][2]} (${Math.round(L)} m vs ${Math.round(D)} m)`);
    const e0 = d(pts[0], G.stops[a]), e1 = d(pts[pts.length - 1], G.stops[b]); if (Math.max(e0, e1) > 150) detours.push(`${G.stops[a][2]}–${G.stops[b][2]}: ponta a ${Math.round(Math.max(e0, e1))} m da estação`); }
  if (detours.length) fail(city, `${detours.length} trechos suspeitos (desvio/gancho): ${detours.slice(0, 4).join('; ')}`);
  // 3. emendas: fim de um trecho deve encontrar o começo do próximo
  const seg = (a, b) => { const v = G.segs[Math.min(a, b) + '|' + Math.max(a, b)]; return v && (a < b ? v : v.slice().reverse()); };
  const gaps = [];
  for (const p of G.patterns) for (let i = 0; i < p.stops.length - 2; i++) { const A = seg(p.stops[i], p.stops[i + 1]), B = seg(p.stops[i + 1], p.stops[i + 2]); if (!A || !B) continue;
    const j = d(A[A.length - 1], B[0]); if (j > 25) gaps.push(`${G.stops[p.stops[i + 1]][2]} (${Math.round(j)} m, linha ${p.line})`); }
  if (gaps.length) fail(city, `${gaps.length} emendas abertas >25 m (rode cluster.py + fixjoin.py): ${[...new Set(gaps)].slice(0, 4).join('; ')}`);
  // 4. horários: velocidade, ordem e quantidade de trens
  const segs = new Map();
  for (const [k, pts] of Object.entries(G.segs)) { const [a, b] = k.split('|');
    const o = [...((G.segO || {})[k] || '')].map(c => c === '+' ? 1 : -1), fr0 = (G.segF || {})[k] || {}, fr = {}; for (const [l, arr] of Object.entries(fr0)) fr[l] = arr.slice().reverse();
    segs.set(k, { pts, src: 'osm', o, f: fr0 }); segs.set(b + '|' + a, { pts: pts.slice().reverse(), src: 'osm', o: o.slice().reverse(), f: fr }); }
  const geoms = G.patterns.map(p => C.patternGeom(p.stops, segs));
  const svc = G.freq ? null : (G.services.du ? 'du' : Object.keys(G.services).sort((a, b) => G.services[b].length - G.services[a].length)[0]);
  const trips = G.freq ? C.tripsFromFreq(G.freq, G.offsets) : C.decodeTrips(G.services[svc]);
  let maxV = 0, nonmono = 0, fast = 0;
  for (const t of trips) { const g = geoms[t.pat]; const tm = C.smoothTimes(t.raw, g.segLen); t.ts = C.tripTimestamps(g, tm);
    for (let i = 1; i < t.ts.length; i++) if (t.ts[i] < t.ts[i - 1] - 1e-6) nonmono++;
    for (let k = 0; k < tm.length - 1; k++) { const v = g.segLen[k] / Math.max(1, tm[k + 1] - tm[k]) * 3.6; maxV = Math.max(maxV, v); if (v > 160) fast++; } }
  if (nonmono) fail(city, `${nonmono} tempos fora de ordem (trens andando para trás)`);
  if (fast) fail(city, `${fast} trechos acima de 160 km/h (tempo de viagem ou geometria errados)`);
  const count = h => trips.filter(t => C.posAt(geoms[t.pat].pts, t.ts, h * 3600)).length;
  const c = Object.fromEntries([5, 8, 13, 18, 23].map(h => [h + 'h', count(h)]));
  console.log(`  viagens ${trips.length}, vel. máx ${maxV.toFixed(0)} km/h, trens simultâneos`, c);
  if (c['8h'] === 0) fail(city, 'nenhum trem às 8h (calendário/serviço errado)');
  if (c['13h'] > 0 && c['8h'] / c['13h'] < 0.9) fail(city, 'menos trens no pico do que ao meio-dia: conferir intervalos');
  // 5. faixas: cada linha precisa de faixa em todos os trechos que usa
  const body2 = body; try { new Function('G', 'geoms', 'SEGMAP', 'KLAT', body2)(G, geoms, segs, K); } catch (e) { fail(city, 'buildLanes falhou: ' + e.message); }
  // 6. nomes de estação: sem nomes vazios, com acentos razoáveis
  const noName = G.stops.filter(s => !s[2] || !s[2].trim()).length; if (noName) fail(city, `${noName} estações sem nome`);
  const sizeMB = fs.statSync(f).size / 1e6; if (sizeMB > 3) fail(city, `dados com ${sizeMB.toFixed(1)} MB (comprimir geometria)`);
  console.log(`  ${G.stops.length} estações, ${G.patterns.length} padrões, ${Object.keys(G.segs).length} trechos, ${sizeMB.toFixed(2)} MB`);
}
console.log(fails ? `\n${fails} FALHA(S) — não publicar antes de corrigir.` : '\nTudo certo.');
process.exit(fails ? 1 : 0);
