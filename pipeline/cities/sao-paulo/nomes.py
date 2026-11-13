# Acrescenta o nome popular de cada linha de São Paulo (mostrado ao lado do número).
import json, sys
f = sys.argv[1]; G = json.load(open(f))
N = {'L1': 'Azul', 'L2': 'Verde', 'L3': 'Vermelha', 'L4': 'Amarela', 'L5': 'Lilás', 'L6': 'Laranja',
     'L7': 'Rubi', 'L8': 'Diamante', 'L9': 'Esmeralda', 'L10': 'Turquesa', 'L11': 'Coral', 'L12': 'Safira',
     'L13': 'Jade', 'L15': 'Prata', 'L17': 'Ouro'}
for k, v in G['lines'].items():
    if k in N: v['sub'] = N[k]
json.dump(G, open(f, 'w'), ensure_ascii=False, separators=(',', ':'))
