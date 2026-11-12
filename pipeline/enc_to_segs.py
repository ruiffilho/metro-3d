# Junta os pedaços exportados do navegador, confere o hash e grava os segmentos no JSON da cidade.
# Uso: python3 enc_to_segs.py raw.txt <hash> base.json pl.json saida.json
# raw.txt: os pedaços na ordem, separados por uma linha com @@@ (o texto de cada pedaço exatamente como veio).
import sys, json
raw, want, base, plf, out = sys.argv[1:6]
s = ''.join(open(raw).read().rstrip('\n').split('\n@@@\n'))
h = 0
for c in s: h = (h * 31 + ord(c)) & 0xffffffff
h = h - 2**32 if h >= 2**31 else h
if str(h) != want: sys.exit(f'HASH NÃO CONFERE: {h} != {want} (algum pedaço foi copiado errado)')
def dec(e):
    i = lat = lon = 0; o = []
    while i < len(e):
        v = []
        for _ in range(2):
            sh = r = 0
            while True:
                c = ord(e[i]) - 63; i += 1; r |= (c & 0x1f) << sh; sh += 5
                if c < 0x20: break
            v.append(~(r >> 1) if r & 1 else r >> 1)
        lat += v[0]; lon += v[1]; o.append([round(lon / 1e5, 6), round(lat / 1e5, 6)])
    return o
osm = {}
for line in s.split('\n'):
    k, e = line.split(':', 1); a, b, _ = k.split('|'); osm.setdefault(f'{a}|{b}', dec(e))
G = json.load(open(base)); pl = json.load(open(plf))['pl']
miss = [k for k in pl if k not in osm]
if miss: sys.exit(f'faltam segmentos: {miss[:10]}')
G['segs'] = {k: osm[k] for k in pl}
json.dump(G, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
print('ok', len(G['segs']), 'segmentos')
