import sys, re, struct
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')
C=open(sys.argv[1],'rb').read()
SJ=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+')
def fields(lo,hi,stride):
    base = lo - lo % stride
    offs=Counter(); maxlen=defaultdict(int); recs=0; first=None; last=None
    for r in range(base, hi, stride):
        rec=C[r:r+stride]; found=False
        for m in SJ.finditer(rec):
            t=m.group()
            if len(t)<2 or not any(c>=0x81 for c in t): continue
            if m.start()>0 and rec[m.start()-1]!=0: continue
            offs[m.start()]+=1; maxlen[m.start()]=max(maxlen[m.start()], len(t)); found=True
        if found:
            recs+=1; first = first or r; last=r
    print(f'stride {stride:#x} records with text {recs}, first {first:#x} last {last:#x}')
    for o,c in sorted(offs.items()):
        if c>=5: print(f'   field +{o:#05x}  used {c:4}  max {maxlen[o]} bytes')
fields(0x16e000,0x1aea00,0x100)
fields(0x1aea00,0x1ee800,0x200)
fields(0x1ee800,0x23e900,0x80)
