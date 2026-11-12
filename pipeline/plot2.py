import json, math, sys, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
d=json.load(open('net.json'))
x0,x1,y0,y1=map(float,sys.argv[1:5]); name=sys.argv[5]
K=math.cos(math.radians(d.get('lat',39.47))); Z=float(sys.argv[6]) if len(sys.argv)>6 else 16; mpp=78271.517*K/2**Z
wpx=(x1-x0)*K*111320/mpp; hpx=(y1-y0)*111320/mpp
fig=plt.figure(figsize=(wpx/100,hpx/100),dpi=100); ax=fig.add_axes([0,0,1,1])
pt=72/100  # 1px in points
for o in d['out']:
    xs=[p[0] for p in o['pts']]; ys=[p[1] for p in o['pts']]
    ax.plot(xs,ys,color='white',lw=6*pt,solid_capstyle='round'); 
for o in d['out']:
    xs=[p[0] for p in o['pts']]; ys=[p[1] for p in o['pts']]
    ax.plot(xs,ys,color=o['color'],lw=4*pt,solid_capstyle='round')
for s in d['stops']:
    if x0<s[0]<x1 and y0<s[1]<y1: ax.plot(s[0],s[1],'o',mfc='white',mec='gray',ms=5); ax.annotate(s[2],(s[0],s[1]),fontsize=7,xytext=(4,4),textcoords='offset points')
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_facecolor('#ecebe7'); ax.set_xticks([]); ax.set_yticks([])
fig.savefig(name+'.png')
