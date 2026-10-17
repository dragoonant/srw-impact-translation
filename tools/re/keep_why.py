import json, glob, sys, os
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
c=Counter()
for f in glob.glob('worksheets/*/*.json'):
    sub=os.path.basename(os.path.dirname(f))
    for s in json.load(open(f,encoding='utf-8'))['strings']:
        if s['keep']:
            why='empty' if not s['jp'].strip() else ('undecodable' if 'raw' in s and sub!='STRTAB' else s['jp'][:14])
            c[(sub, s['kind'], why)]+=1
for k,v in c.most_common(30): print(v,k)
