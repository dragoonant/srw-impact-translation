import json, glob, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
shape=Counter(); lens=[]; seps=Counter(); ex=[]
for f in sorted(glob.glob(sys.argv[1]+'/BMC_*.json')):
    for s in json.load(open(f,encoding='utf-8'))['strings']:
        t=s['jp']
        k='「」' if re.match(r'^「.*」$',t,re.S) else ('（）' if re.match(r'^（.*）$',t,re.S) else ('empty' if not t else 'other'))
        shape[k]+=1
        if k=='other' and len(ex)<10: ex.append((f[-12:], s['id'], t[:50]))
        for c in re.findall(r'@|\n|\u3000|／|<[^>]*>|[\x00-\x1f]', t): seps[c]+=1
        lens.append(len(t))
lens.sort()
print(shape); print('separators', seps); print('len max', lens[-1], 'p99.5', lens[int(len(lens)*.995)], 'median', lens[len(lens)//2])
print(ex)
