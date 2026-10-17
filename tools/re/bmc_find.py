import struct, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
D=sys.argv[1]
C=open(D+'/MAP/COMMON.BIN','rb').read(); b=open(D+'/BTL/BMCPACK.BIN','rb').read()
tab=struct.unpack_from('<400I', C, 0x400400)
starts=sorted({v for v in tab if v!=0xFFFFFFFF}); bounds=starts+[len(b)]
def try_pair(s,e,t,p):
    if not (0 < t < p < e-s) or (p-t)%2 or p-t < 2: return None
    words=struct.unpack_from(f'<{(p-t)//2}H', b, s+t)
    if words[0]!=0: return None
    n=1
    while n<len(words) and words[n]>words[n-1]: n+=1
    if any(w for w in words[n:]): return None
    if s+p+words[n-1] >= e: return None
    if not all(b[s+p+words[k]-1]==0 for k in range(1,n)): return None
    end=b.index(b'\0', s+p+words[n-1])+1
    if not (0 <= e-end <= 3): return None
    return n
where=Counter(); fails=[]
for s,e in zip(bounds,bounds[1:]):
    found=None
    for q in range(s, min(s+0x600, e-4), 2):
        t,p=struct.unpack_from('<2H', b, q)
        n=try_pair(s,e,t,p)
        if n: found=(q-s,t,p,n); break
    if found: where[found[0]]+=1
    else: fails.append(hex(s))
print('pair position within header:', sorted(where.items()))
print('no pair found:', len(fails), fails[:10])
