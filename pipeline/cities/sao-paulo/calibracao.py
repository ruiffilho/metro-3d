# Recalibra São Paulo depois do prep_sp.py (o frequencies.txt da SPTrans exagera a oferta).
# Uso: python3 calibracao.py <gtfs_sp.json>   (já aplicado em data/sao-paulo.json)
import json, sys
G = json.load(open(sys.argv[1])); P = G['patterns']; O = G['offsets']
# intervalos (pico, entrepico, noite) em segundos; pico 6–9h e 17–20h
HW = {'L1': (120, 240, 360), 'L2': (150, 300, 420), 'L3': (120, 210, 360), 'L4': (100, 210, 300),
      'L5': (150, 270, 420), 'L15': (240, 480, 600), 'L12': (270, 480, 600)}
def hw(ref, hour, h0):
    if ref not in HW: return h0
    pk, ep, nt = HW[ref]
    if hour < 5: return max(nt * 2, h0)
    if hour == 5: return nt
    if 6 <= hour < 9 or 17 <= hour < 20: return pk
    if hour >= 21: return nt
    return ep
G['freq'] = [[p, a, b, hw(P[p]['line'], a // 3600, h)] for p, a, b, h in G['freq']]
# tempo de viagem de ponta a ponta (min) — os da SPTrans são ~1,5× lentos demais
T = {'L1': 37, 'L2': 27, 'L3': 36, 'L4': 23, 'L5': 32, 'L15': 27, 'L7': 82, 'L8': 70, 'L9': 60, 'L10': 60,
     'L11': 75, 'L12': 50, 'L13': 16, 'L6': 12, 'L17': 12}
for i, p in enumerate(P):
    t = T.get(p['line'])
    if not t or O[i][-1] == 0: continue
    if p['line'] == 'L17' and len(p['stops']) == 2: t = 3
    f = t * 60 / O[i][-1]
    if f < 1: O[i] = [round(x * f) for x in O[i]]
G['tripCount'] = [0] * len(P)
for p, a, b, h in G['freq']: G['tripCount'][p] += (b - a + 60) // h
json.dump(G, open(sys.argv[1], 'w'), ensure_ascii=False, separators=(',', ':'))
