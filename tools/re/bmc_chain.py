import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
b = open(sys.argv[1],'rb').read()
def parse(p):
    recs = [struct.unpack_from('<6I', b, p+24*i) for i in range(12)]
    slots = struct.unpack_from('<10H', b, p+0x128)
    i = 0
    while slots[i] == 0xFFFF: i += 1
    offs = [slots[i]]
    for x in slots[i+1:]:
        if x <= offs[-1]: break
        offs.append(x)
    assert offs[0] >= 0x13c and len(offs) >= 3, (hex(p), slots)
    tab, pool = offs[-2], offs[-1]
    words = struct.unpack_from(f'<{(pool-tab)//2}H', b, p+tab)
    n = 1
    while n < len(words) and words[n] > words[n-1]: n += 1
    end = b.index(b'\0', p+pool+words[n-1]) + 1
    return recs, offs, words, n, end
subs=[]; p=0
while p < len(b):
    recs, offs, words, n, end = parse(p)
    subs.append((p, n, end, len(words)-n, offs))
    p = (end + 3) & ~3
    if b[p:].strip(b'\0') == b'': break
from collections import Counter
print('subfiles', len(subs), 'last end', hex(subs[-1][2]), 'file', hex(len(b)), 'trailing', len(b)-subs[-1][2])
print('strings', sum(s[1] for s in subs), 'extra table words', Counter(s[3] for s in subs))
print('sections per subfile', Counter(len(s[4]) for s in subs))
open(sys.argv[2],'w').write('\n'.join(f'{p:x} {n} {e:x}' for p,n,e,_,_ in subs))
