import json, glob, re, sys, os
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')
shapes=Counter(); samples=defaultdict(list); speakers=Counter(); ctl=Counter()
for f in sorted(glob.glob(sys.argv[1]+'/LOGIC_*.json')):
    ws=json.load(open(f,encoding='utf-8'))
    for s in ws['strings']:
        t=s['jp']
        if 'raw' in s: k='undecodable'
        elif t=='': k='empty'
        elif re.match(r'^[^@「」]+@「.*」$', t, re.S): k='dialogue'
        elif re.match(r'^[^@「」]+@（.*）$', t, re.S): k='thought'
        elif re.match(r'^「.*」$', t, re.S): k='quote-no-speaker'
        elif re.match(r'^[\x00-\x7f]+$', t): k='ascii'
        elif '@' in t: k='multi-line other'
        else: k='single-line other'
        shapes[k]+=1
        if len(samples[k])<8: samples[k].append((os.path.basename(f)[6:10], s['id'], t[:60]))
        if k in ('dialogue','thought'): speakers[t.split('@',1)[0]]+=1
        for c in re.findall(r'[\x00-\x1f]|<[^>]*>|#\w*|%\w', t): ctl[c]+=1
print(shapes.most_common())
for k,v in samples.items():
    print('==',k)
    for x in v: print('  ',x)
print('speakers', len(speakers), speakers.most_common(25))
print('control-ish', ctl.most_common(20))
