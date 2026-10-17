import sys, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
C=open(sys.argv[1],'rb').read()
SJ=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+')
def is_text(b):
    try: t=b.decode('cp932')
    except: return False
    return sum(1 for c in t if ord(c)>0x7f)>=1
for name, lo, hi, stride in (('units',0x16e900,0x1a7600,0x100),('pilots',0x1aea00,0x1df000,0x200),('weapons',0x1ee800,0x22e000,0x80)):
    recs=[r for r in range(lo,hi,stride) if is_text(C[r:r+4]) or C[r]>=0x81]
    starts=defaultdict(int)
    for r in recs:
        rec=C[r:r+stride]
        for m in SJ.finditer(rec):
            if is_text(m.group()) and m.group()[0]>=0x81 and (m.end()<len(rec) and rec[m.end()]==0):
                starts[m.start()]+=1
    fields=[o for o,c in sorted(starts.items()) if c>=3]
    print(f'== {name}: {len(recs)} records, stride {stride:#x}')
    for o in fields:
        minslot=10**9; maxlen=0; used=0; prev_nonzero=set()
        for r in recs:
            rec=C[r:r+stride]
            e=o
            while e<stride and rec[e]!=0: e+=1
            n=e-o
            if n:
                used+=1; maxlen=max(maxlen,n)
            z=e
            while z<stride and rec[z]==0: z+=1
            minslot=min(minslot, z-o)
            if o>0: prev_nonzero.add(rec[o-1])
        print(f'   +{o:#05x} used {used:4} maxlen {maxlen:3} min slot {minslot:3} (budget {minslot-1}) byte-before {sorted(prev_nonzero)[:4]}')
