import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
b = open(sys.argv[1],'rb').read()
blocks=[]
for p in range(0, len(b), 0x800):
    v0 = struct.unpack_from('<H', b, p)[0]
    if v0 < 4 or v0 % 2 or p + v0 > len(b): continue
    n = v0 // 2
    vals = struct.unpack_from(f'<{n}H', b, p)
    if any(vals[i] >= vals[i+1] for i in range(n-1)): continue
    # each string boundary: byte before vals[k] (k>0) must be NUL
    if not all(b[p+vals[k]-1] == 0 for k in range(1, n)): continue
    end = b.index(b'\0', p + vals[-1]) + 1
    blocks.append((p, n, end - p))
print(len(blocks), 'blocks')
tot = sum(x[1] for x in blocks); print('strings', tot)
cov = sum(x[2] for x in blocks); print('bytes covered', cov, 'of', len(b))
gaps=[]; prev=0
for p,n,sz in blocks:
    if p > prev: gaps.append((prev, p-prev))
    prev = (p+sz+0x7ff)//0x800*0x800
print('first blocks', [(hex(p),n,sz) for p,n,sz in blocks[:8]])
print('gaps (not string blocks):', len(gaps), 'total', sum(g[1] for g in gaps)); print([(hex(a),hex(l)) for a,l in gaps[:15]])
