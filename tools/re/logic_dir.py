import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
D = sys.argv[1]
e = open(D + '/SLPS_251.03','rb').read()
L = open(D + '/MAP/LOGIC.BIN','rb').read()
def kind(sec):
    p = sec*0x800
    if p >= len(L): return 'EOF'
    w = struct.unpack_from('<2H', L, p)
    if L[p:p+4] == b'UNTD': return 'UNTD'
    v0 = w[0]
    if v0 >= 4 and v0 % 2 == 0:
        n = v0//2
        if p + v0 <= len(L):
            vals = struct.unpack_from(f'<{n}H', L, p)
            if all(vals[i] < vals[i+1] for i in range(n-1)) and all(L[p+vals[k]-1]==0 for k in range(1,n)):
                return f'STR{n}'
    if v0 == 8: return 'SCR'
    return 'raw:' + L[p:p+8].hex()
recs=[]; p = 0x157eb8
while True:
    r = struct.unpack_from('<6I', e, p)
    if r[1] or r[3] or r[5] or not r[0]: break
    recs.append((r[0], r[2], r[4])); p += 24
print('records', len(recs), 'table end', hex(p), 'next bytes', e[p:p+48].hex(' '))
for i, r in enumerate(recs[:12]):
    print(i, [hex(x) for x in r], [kind(x) for x in r])
print('...')
for i, r in enumerate(recs[-4:], len(recs)-4):
    print(i, [hex(x) for x in r], [kind(x) for x in r])
allsec = sorted({x for r in recs for x in r})
print('distinct sectors', len(allsec), 'file sectors', len(L)//0x800, 'last', hex(allsec[-1]))
from collections import Counter
print(Counter(kind(x).split(':')[0].rstrip('0123456789') for x in allsec))

# --- coverage and copies
scan=[]
for p in range(0, len(L), 0x800):
    k = kind(p//0x800)
    if k.startswith('STR'): scan.append(p//0x800)
ref = set(allsec)
missing = [s for s in scan if s not in ref]
print('string blocks', len(scan), 'not referenced:', [hex(s) for s in missing])
for s in missing:
    prev = max(x for x in ref if x < s); print('  ', hex(s), 'inside block starting', hex(prev), kind(prev))
sizes=[]
for s in scan:
    p=s*0x800; n=struct.unpack_from('<H',L,p)[0]//2; last=struct.unpack_from('<H',L,p+2*(n-1))[0]
    sizes.append(L.index(b'\0', p+last)+1-p)
print('string block bytes: max', max(sizes), 'mean', sum(sizes)//len(sizes))
C = open(D + '/MAP/COMMON.BIN','rb').read()
tbl = e[0x157eb8:0x1594c0]
i = C.find(tbl[:240]); print('COMMON copy at', hex(i), 'identical full table:', C[i:i+len(tbl)] == tbl if i>=0 else None)
# other references to LOGIC sectors? is the table address referenced in code (lui/addiu of 0x256eb8)?
va = 0x157eb8 - 0x1000 + 0x100000
print('table vaddr', hex(va))
