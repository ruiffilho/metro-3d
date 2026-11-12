import json,sys
path=sys.argv[1]; G=json.load(open(path))
def ends(a,b):
    k=f"{min(a,b)}|{max(a,b)}"; return (k,0 if a<b else -1),(k,-1 if a<b else 0)
for _ in range(3):
    for p in G['patterns']:
        s=p['stops']
        for i in range(len(s)-2):
            _,e1=ends(s[i],s[i+1]); e2,_=ends(s[i+1],s[i+2])
            A=G['segs'][e1[0]][e1[1]]; B=G['segs'][e2[0]][e2[1]]
            m=[round((A[0]+B[0])/2,6),round((A[1]+B[1])/2,6)]
            G['segs'][e1[0]][e1[1]]=m; G['segs'][e2[0]][e2[1]]=list(m)
json.dump(G,open(path,'w'),ensure_ascii=False,separators=(',',':'))
