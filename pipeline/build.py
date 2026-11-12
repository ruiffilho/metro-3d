# Gera o site (index.html + audio/) a partir de pipeline/template.html.
# Os dados finais de cada cidade ficam em data/<cidade>.json (gerados pelo pipeline da cidade).
import os, re, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'pipeline')
s = open(os.path.join(P, 'template.html')).read()
s = re.sub(r'<script id="(chimes|city-[a-z-]+)" type="application/json">__[A-Z]+__</script>\n', '', s)
a0 = "if (typeof window !== 'undefined' && window.maplibregl) (function () {"
assert s.count(a0) == 1
s = s.replace(a0, "if (typeof window !== 'undefined' && window.maplibregl) (async function () {")
a = "  const G = JSON.parse($('city-' + cityId).textContent);"
assert a in s
s = s.replace(a, "  const G = await (await fetch('data/' + cityId + '.json')).json();")
a = "  const CHIMES = JSON.parse($('chimes').textContent);"
assert a in s
s = s.replace(a, "  const CHIMES = new Proxy({}, { get: (_, id) => 'audio/' + id + '.mp3' });")
open(os.path.join(ROOT, 'index.html'), 'w').write(s)
os.makedirs(os.path.join(ROOT, 'audio'), exist_ok=True)
for f in os.listdir(os.path.join(P, 'chimes')):
    shutil.copy(os.path.join(P, 'chimes', f), os.path.join(ROOT, 'audio', f))
ids = re.findall(r"^    '?([a-z-]+)'?: \{ name:", s, re.M)
for cid in ids:
    assert os.path.exists(os.path.join(ROOT, 'data', cid + '.json')), f'falta data/{cid}.json'
    assert os.path.exists(os.path.join(ROOT, 'audio', cid + '.mp3')), f'falta audio/{cid}.mp3'
print('index.html gerado; cidades:', ids)
