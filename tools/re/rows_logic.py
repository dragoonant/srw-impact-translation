import json, glob, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
rows=Counter(); rowlen=Counter(); spk=Counter(); maxrow=[]
for f in sorted(glob.glob(sys.argv[1]+'/LOGIC_*.json')):
    for s in json.load(open(f,encoding='utf-8'))['strings']:
        t=s['jp']
        if '@' not in t: 
            rowlen[min(len(t),60)//5*5]+=0; continue
        parts=t.split('@')
        rows[len(parts)-1]+=1        # body rows after the speaker row
        spk[len(parts[0])]+=1
        for r in parts[1:]:
            n=len(r); rowlen[n]+=1; maxrow.append((n,r))
print('body rows per page', sorted(rows.items()))
print('speaker length (chars)', sorted(spk.items()))
lens=sorted(rowlen.elements()); import statistics
print('row length chars: max', max(lens), 'p99.5', lens[int(len(lens)*0.995)], 'p99', lens[int(len(lens)*0.99)], 'median', statistics.median(lens))
print('longest rows', [r for n,r in sorted(maxrow)[-5:]])
