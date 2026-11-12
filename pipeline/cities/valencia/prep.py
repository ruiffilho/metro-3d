import csv, json, collections, sys, os
src = sys.argv[1]; out = sys.argv[2]
rd = lambda f: list(csv.DictReader(open(os.path.join(src, f), encoding='utf-8-sig')))
def sec(t):
    h, m, s = map(int, t.strip().split(':')); return h*3600 + m*60 + s

stops_raw = rd('stops.txt')
sidx = {}; stops = []
for s in stops_raw:
    sidx[s['stop_id']] = len(stops)
    stops.append([round(float(s['stop_lon']), 6), round(float(s['stop_lat']), 6), s['stop_name']])

routes = {r['route_id']: r for r in rd('routes.txt')}
# cor majoritária por linha (ponderada pelo nº de viagens)
trips = {t['trip_id']: t for t in rd('trips.txt')}
cnt = collections.defaultdict(collections.Counter)
for t in trips.values():
    r = routes[t['route_id']]; cnt[r['route_short_name']][r['route_color'].upper()] += 1
lines = {}
for ref, c in cnt.items():
    rtypes = collections.Counter(routes[t['route_id']]['route_type'] for t in trips.values() if routes[t['route_id']]['route_short_name'] == ref)
    lines[ref] = {'color': '#' + c.most_common(1)[0][0], 'mode': 'tram' if rtypes.most_common(1)[0][0] == '0' else 'metro'}

shapes = collections.defaultdict(list)
for r in rd('shapes.txt'):
    shapes[r['shape_id']].append((int(r['shape_pt_sequence']), round(float(r['shape_pt_lon']), 6), round(float(r['shape_pt_lat']), 6)))
shapes = {k: [[x, y] for _, x, y in sorted(v)] for k, v in shapes.items()}

st = collections.defaultdict(list)
for r in rd('stop_times.txt'):
    st[r['trip_id']].append((int(r['stop_sequence']), sidx[r['stop_id']], sec(r['departure_time'] or r['arrival_time'])))

pat_key = {}; patterns = []
services = collections.defaultdict(list)
for tid, rows in st.items():
    rows.sort(); t = trips[tid]; r = routes[t['route_id']]
    seq = tuple(x[1] for x in rows)
    key = (r['route_short_name'], seq)
    if key not in pat_key:
        pat_key[key] = len(patterns)
        patterns.append({'line': r['route_short_name'], 'stops': list(seq), 'head': t['trip_headsign'], 'name': r['route_long_name']})
    times = [x[2] for x in rows]
    deltas = [(times[i] - times[i-1]) // 60 for i in range(1, len(times))]
    services[t['service_id']].append([pat_key[key], times[0] // 60] + deltas)
for v in services.values(): v.sort(key=lambda x: x[1])

cal = {r['date']: r['service_id'] for r in rd('calendar_dates.txt') if r['exception_type'].strip() == '1'}
labels = {}
import datetime
wd = collections.defaultdict(collections.Counter)
for d, s in cal.items():
    wd[s][datetime.date(int(d[:4]), int(d[4:6]), int(d[6:])).weekday()] += 1
names = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
for s, c in wd.items():
    days = sorted(c)
    labels[s] = names[days[0]] + ('–' + names[days[-1]] if len(days) > 1 else '')
data = {'stops': stops, 'lines': lines, 'shapes': shapes, 'patterns': patterns, 'services': services,
        'calendar': cal, 'labels': labels, 'nTrips': {k: len(v) for k, v in services.items()}}
json.dump(data, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
print('patterns', len(patterns), 'labels', labels, 'lines', lines, 'bytes', os.path.getsize(out))
