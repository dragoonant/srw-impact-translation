import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
C=open(sys.argv[1],'rb').read(); B=int(sys.argv[2],16)
h0=struct.unpack_from('<H',C,B)[0]; n=h0//2
hdr=struct.unpack_from(f'<{n}H',C,B)
bounds=list(hdr)
def ok_start(a): return C[a-1]==0
for i,off in enumerate(hdr):
    S=B+off; end=B+(hdr[i+1] if i+1<n else None) if i+1<n else None
    v0=struct.unpack_from('<H',C,S)[0]
    # try base = B and base = S
    res=[]
    for name,base in (('bank',B),('sect',S)):
        first=base+v0
        # table length if strings start at first
        cnt=(first-S)//2 if first>S else 0
        if cnt<=0 or cnt>4000: res.append((name,'-')); continue
        vals=struct.unpack_from(f'<{cnt}H',C,S)
        good=sum(ok_start(base+v) for v in vals)
        res.append((name,cnt,good))
    sample=C[B+v0:C.index(b'\0',B+v0)].decode('cp932','replace')[:20] if B+v0<len(C) else ''
    print(i, hex(S), 'v0', v0, res, sample)
