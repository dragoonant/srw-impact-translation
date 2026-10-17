import struct, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
D=sys.argv[1]
C=open(D+'/MAP/COMMON.BIN','rb').read(); b=open(D+'/BTL/BMCPACK.BIN','rb').read()
tab=struct.unpack_from('<400I', C, 0x400400)
starts=sorted({v for v in tab if v!=0xFFFFFFFF})
bounds=starts+[len(b)]
bad=[]; ok=0; tails=Counter(); nstr=0; nsec=Counter(); extra=Counter()
for s,e in zip(bounds, bounds[1:]):
    try:
        slots=struct.unpack_from('<10H', b, s+0x128)
        i=0
        while slots[i]==0xFFFF: i+=1
        offs=[slots[i]]
        for x in slots[i+1:]:
            if x<=offs[-1]: break
            offs.append(x)
        t,pool=offs[-2],offs[-1]
        words=struct.unpack_from(f'<{(pool-t)//2}H', b, s+t)
        n=1
        while n<len(words) and words[n]>words[n-1]: n+=1
        end=b.index(b'\0', s+pool+words[n-1])+1
        assert words[0]==0
        tails[e-end]+=1; nstr+=n; nsec[len(offs)]+=1; extra[tuple(words[n:])]+=1
        if e-end>3: bad.append((hex(s), 'tail', e-end))
        else: ok+=1
    except Exception as ex:
        bad.append((hex(s), repr(ex)[:60]))
print('ok', ok, 'bad', len(bad), bad[:10]); print('tails', tails); print('strings', nstr)
print('sections', nsec); print('extra table words', extra.most_common(5))
