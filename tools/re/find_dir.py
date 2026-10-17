import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
L = open(sys.argv[1],'rb').read()
blocks=[]
for p in range(0, len(L), 0x800):
    v0 = struct.unpack_from('<H', L, p)[0]
    if v0 < 4 or v0 % 2 or p + v0 > len(L): continue
    n = v0 // 2
    vals = struct.unpack_from(f'<{n}H', L, p)
    if any(vals[i] >= vals[i+1] for i in range(n-1)): continue
    if not all(L[p+vals[k]-1] == 0 for k in range(1, n)): continue
    blocks.append(p)
for target in sys.argv[2:]:
    D = open(target,'rb').read()
    for unit, conv in (('sector', lambda p: p//0x800), ('byte', lambda p: p)):
        seq = [conv(p) for p in blocks[:6]]
        for fmt, w in (('<H',2),('<I',4)):
            for stride in range(w, 129, w):
                first = struct.pack(fmt, seq[0])
                i = D.find(first)
                while i != -1:
                    ok = all(i + k*stride + w <= len(D) and struct.unpack_from(fmt, D, i+k*stride)[0] == seq[k] for k in range(1, 4))
                    if ok:
                        print(target.split('/')[-1], unit, fmt, 'stride', stride, 'at', hex(i))
                    i = D.find(first, i+1)
print('blocks', len(blocks), [hex(x) for x in blocks[:6]])
