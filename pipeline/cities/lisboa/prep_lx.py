import csv, json, collections, datetime, re, math, os, sys
R = '/home/claude/lx_raw'
FEEDS = {
    'metro': 'tld-716-202610230113',
    'cp': 'mdb-2057-202611110001',
    'fert': 'Fertagus_GTFS',
    'mts': 'mdb-2408-202610130122',
    'carris': 'carris',
}
rd = lambda feed, f: list(csv.DictReader(open(f'{R}/{FEEDS[feed]}/{f}', encoding='utf-8-sig'))) if os.path.exists(f'{R}/{FEEDS[feed]}/{f}') else []
def sec(t):
    h, m, s = map(int, t.strip().split(':')); return h * 3600 + m * 60 + s

# linhas: ref numérico (ordenação/faixas) + nome exibido
LINES = {
    '1': dict(name='Azul', color='#4E84C4', mode='metro'),
    '2': dict(name='Amarela', color='#F9B200', mode='metro'),
    '3': dict(name='Verde', color='#00A99D', mode='metro'),
    '4': dict(name='Vermelha', color='#EE2E58', mode='metro'),
    '11': dict(name='Sintra', color='#6CB33F', mode='comboio'),
    '12': dict(name='Cascais', color='#F07D00', mode='comboio'),
    '13': dict(name='Azambuja', color='#A6192E', mode='comboio'),
    '14': dict(name='Sado', color='#0098D8', mode='comboio'),
    '21': dict(name='Fertagus', color='#7B2D8E', mode='comboio'),
    '31': dict(name='MTS 1', color='#00A3E8', mode='metro ligeiro'),
    '32': dict(name='MTS 2', color='#FBCD01', mode='metro ligeiro'),
    '33': dict(name='MTS 3', color='#BBCF16', mode='metro ligeiro'),
    '41': dict(name='12E', color='#B5838D', mode='elétrico'),
    '42': dict(name='15E', color='#E07A5F', mode='elétrico'),
    '43': dict(name='18E', color='#81B29A', mode='elétrico'),
    '44': dict(name='24E', color='#5B7DB1', mode='elétrico'),
    '45': dict(name='25E', color='#A67B5B', mode='elétrico'),
    '46': dict(name='28E', color='#FFD60A', mode='elétrico'),
}
TRAM = {'12E': '41', '15E': '42', '18E': '43', '24E': '44', '25E': '45', '28E': '46'}
CPL = {'Linha de Sintra': '11', 'Linha de Cascais': '12', 'Linha da Azambuja': '13', 'Linha do Sado': '14'}
METRO = {'A': '1', 'B': '2', 'C': '3', 'D': '4'}
FAM = {'metro': 'metro', 'cp': 'rail', 'fert': 'rail', 'mts': 'lrt'}

def line_of(feed, route):
    if feed == 'metro': return METRO.get(route['route_id'])
    if feed == 'cp': return CPL.get(route['route_short_name'])
    if feed == 'fert': return '21'
    if feed == 'mts': return '3' + route['route_short_name']
    if feed == 'carris': return TRAM.get(route['route_short_name'])

FIX = [('Apolonia', 'Apolónia'), ('Sodre', 'Sodré'), ('Alcantara', 'Alcântara'), ('Setubal', 'Setúbal'), ('Sao ', 'São '),
       ('Belem', 'Belém'), ('Alges', 'Algés'), ('Paco', 'Paço'), ('Agualva', 'Agualva'), ('Amadora', 'Amadora'),
       ('Queluz - Belas', 'Queluz-Belas'), ('Monte Abraao', 'Monte Abraão'), ('Merces', 'Mercês'), ('Mira Sintra - Melecas', 'Mira Sintra-Meleças'),
       ('Portela de Sintra', 'Portela de Sintra'), ('Rio de Mouro', 'Rio de Mouro'), ('Algueirao', 'Algueirão'),
       ('Sete Rios', 'Sete Rios'), ('Areeiro', 'Areeiro'), ('Braco de Prata', 'Braço de Prata'), ('Povoa', 'Póvoa'),
       ('Iria', 'Iria'), ('Vila Franca de Xira', 'Vila Franca de Xira'), ('Alhandra', 'Alhandra'), ('Ribatejo', 'Ribatejo'),
       ('Sacavem', 'Sacavém'), ('Bobadela', 'Bobadela'), ('Moscavide', 'Moscavide'), ('Coina', 'Coina'), ('Penalva', 'Penalva'),
       ('Pinhal Novo', 'Pinhal Novo'), ('Venda do Alcaide', 'Venda do Alcaide'), ('Palmela', 'Palmela'), ('Lavradio', 'Lavradio'),
       ('Baixa da Banheira', 'Baixa da Banheira'), ('Alhos Vedros', 'Alhos Vedros'), ('Moita', 'Moita'), ('Santo Amaro', 'Santo Amaro'),
       ('Cruz Quebrada', 'Cruz Quebrada'), ('Caxias', 'Caxias'), ('Paco de Arcos', 'Paço de Arcos'), ('Santo Amaro', 'Santo Amaro'),
       ('Carcavelos', 'Carcavelos'), ('Estoril', 'Estoril'), ('Joao', 'João'), ('Espadanal', 'Espadanal'), ('Vila Nova da Rainha', 'Vila Nova da Rainha'),
       ('Benfica', 'Benfica'), ('Campolide', 'Campolide'), ('Massama', 'Massama'), ('Cacem', 'Cacém'), ('Reboleira', 'Reboleira'),
       ('Praias do Sado-A', 'Praias do Sado-A'), ('Entrecampos', 'Entrecampos'), ('Marvila', 'Marvila'), ('Roma - Areeiro', 'Roma-Areeiro'),
       ('Alverca', 'Alverca'), ('Mouro', 'Mouro'), ('Castanheira', 'Castanheira')]
def fixname(n):
    n = n.strip()
    for a, b in FIX: n = n.replace(a, b)
    n = re.sub(r'^Lisboa ', '', n)
    n = re.sub(r'\s*-\s*', '-', n); n = re.sub(r'\s+', ' ', n).replace(' / ', '-').replace('/', '-') if '/' in n and 'Luz' not in n else re.sub(r'\s+', ' ', n)
    n = {'Praca do Quebedo': 'Praça do Quebedo', 'Sete-Rios': 'Sete Rios', 'Entre Campos': 'Entrecampos', 'Colégio Militar-Luz': 'Colégio Militar/Luz'}.get(n, n)
    return n

stops, sidx = [], {}
CAR, CARP, CARMAP = {}, {}, {}
patterns, pidx, offsets = [], {}, []
day_trips = {'du': [], 'sab': [], 'dom': []}
REP = {'du': datetime.date(2026, 11, 18), 'sab': datetime.date(2026, 11, 21), 'dom': datetime.date(2026, 11, 22)}

for feed in FEEDS:
    routes = {r['route_id']: r for r in rd(feed, 'routes.txt')}
    S = {s['stop_id']: s for s in rd(feed, 'stops.txt')}
    cal = {c['service_id']: c for c in rd(feed, 'calendar.txt')}
    cd = collections.defaultdict(dict)
    for c in rd(feed, 'calendar_dates.txt'): cd[c['service_id']][c['date']] = c['exception_type']
    def active(sid, d):
        ds = d.strftime('%Y%m%d')
        if ds in cd[sid]: return cd[sid][ds] == '1'
        c = cal.get(sid)
        if not c: return False
        wd = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][d.weekday()]
        return c[wd] == '1' and c['start_date'] <= ds <= c['end_date']
    trips = {}
    for t in rd(feed, 'trips.txt'):
        r = routes.get(t['route_id']);
        if not r: continue
        l = line_of(feed, r)
        if l: trips[t['trip_id']] = (t, l)
    st = collections.defaultdict(list)
    with open(f'{R}/{FEEDS[feed]}/stop_times.txt', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['trip_id'] in trips: st[r['trip_id']].append((int(r['stop_sequence']), r['stop_id'], sec(r['arrival_time'] or r['departure_time']), sec(r['departure_time'] or r['arrival_time'])))
    def SI(sid):
        s = S[sid]
        if s.get('parent_station') and s['parent_station'] in S: s = S[s['parent_station']]
        key = (feed, s['stop_id'])
        if feed == 'carris' and key not in sidx:
            # elétricos: junta as paragens dos dois sentidos (mesmo nome, até 200 m) num só ponto
            nm = fixname(s['stop_name']); P = (float(s['stop_lon']), float(s['stop_lat']))
            for j in CAR.get(nm, []):
                q = CARP[j]
                if math.hypot((q[0] / q[2] - P[0]) * 0.78, q[1] / q[2] - P[1]) * 111320 < 200:
                    q[0] += P[0]; q[1] += P[1]; q[2] += 1; sidx[key] = j; break
            else:
                j = len(stops); sidx[key] = j; stops.append([0, 0, nm]); CAR.setdefault(nm, []).append(j); CARP[j] = [P[0], P[1], 1]
            CARMAP[s['stop_id']] = sidx[key]
        if key not in sidx:
            sidx[key] = len(stops); stops.append([round(float(s['stop_lon']), 6), round(float(s['stop_lat']), 6), fixname(s['stop_name'])])
        return sidx[key]
    for tid, rows in st.items():
        rows.sort(); t, l = trips[tid]
        days = [k for k, d in REP.items() if active(t['service_id'], d)]
        if not days or len(rows) < 2: continue
        seq = tuple(SI(r[1]) for r in rows)
        # remove paradas repetidas consecutivas (mesmo cais)
        keep = [0] + [i for i in range(1, len(seq)) if seq[i] != seq[i - 1]]
        rows = [rows[i] for i in keep]; seq = tuple(seq[i] for i in keep)
        if len(seq) < 2: continue
        k = (l, seq)
        if k not in pidx:
            pidx[k] = len(patterns)
            head = t.get('trip_headsign') or stops[seq[-1]][2]
            patterns.append({'line': l, 'stops': list(seq), 'head': fixname(head), 'name': f"{LINES[l]['name']} · {stops[seq[0]][2]} – {stops[seq[-1]][2]}"})
        p = pidx[k]
        t0 = rows[0][3]
        mins = [round(t0 / 60)] + [round(r[2] / 60) for r in rows[1:]]
        # tempos em minutos, monotônicos
        for i in range(1, len(mins)):
            if mins[i] <= mins[i - 1]: mins[i] = mins[i - 1] + 1 if i == len(mins) - 1 or True else mins[i]
        enc = [p, mins[0]] + [mins[i] - mins[i - 1] for i in range(1, len(mins))]
        for d in days: day_trips[d].append(enc)

for j, q in CARP.items(): stops[j][0] = round(q[0] / q[2], 6); stops[j][1] = round(q[1] / q[2], 6)
json.dump(CARMAP, open('/home/claude/build/lx/carmap.json', 'w'))
# calendário: datas → tipo de dia (feriados nacionais como domingo)
HOL = {'20261201', '20261208', '20261225', '20270101'}
calendar = {}
d = datetime.date(2026, 11, 1)
while d <= datetime.date(2027, 1, 31):
    ds = d.strftime('%Y%m%d')
    calendar[ds] = 'dom' if ds in HOL or d.weekday() == 6 else ('sab' if d.weekday() == 5 else 'du')
    d += datetime.timedelta(days=1)
for v in day_trips.values(): v.sort(key=lambda r: r[1])
lines = {k: {'color': v['color'], 'mode': v['mode'], 'name': v['name']} for k, v in LINES.items()}
G = {'stops': stops, 'lines': lines, 'patterns': patterns, 'services': day_trips,
     'calendar': calendar, 'labels': {'du': 'Dia útil', 'sab': 'Sábado', 'dom': 'Domingo e feriado'},
     'nTrips': {k: len(v) for k, v in day_trips.items()}, 'feedDate': '11/11/2026', 'range': ['20261101', '20270131']}
pl = collections.defaultdict(set)
for p in patterns:
    for a, b in zip(p['stops'], p['stops'][1:]): pl[f'{min(a,b)}|{max(a,b)}'].add(p['line'])
fam = {}
for l in LINES:
    fam[l] = 'metro' if LINES[l]['mode'] == 'metro' else ('lrt' if l[0] in '34' and len(l) == 2 else 'rail')
json.dump(G, open('/home/claude/build/lx/gtfs_lx_base.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump({'stops': [s[:2] for s in stops], 'pl': {k: sorted(v) for k, v in pl.items()}, 'fam': fam}, open('/home/claude/build/lx/pl_lx.json', 'w'), separators=(',', ':'))
print('stops', len(stops), 'patterns', len(patterns), 'pairs', len(pl), {k: len(v) for k, v in day_trips.items()})
print(collections.Counter(p['line'] for p in patterns))
print(sorted({s[2] for s in stops}))
