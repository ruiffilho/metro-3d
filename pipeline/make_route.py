# Gera o script de roteamento OSM para colar no navegador.
# Uso: python3 make_route.py cities/<id>/pl.json "<sul>,<oeste>,<norte>,<leste>" <lat> > /tmp/route.js
import sys, os
here = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(here, 'osm_route.js')).read()
print(s.replace('__PL__', open(sys.argv[1]).read().strip()).replace('__BBOX__', sys.argv[2]).replace('__LAT__', sys.argv[3]))
