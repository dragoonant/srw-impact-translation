"""Japanese runs in a file not covered by a STRTAB worksheet's slots."""
import json, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
data=open(sys.argv[1],'rb').read(); ws=json.load(open(sys.argv[2],encoding='utf-8'))
cov=bytearray(len(data))
for s in ws['strings']:
    n=len(bytes.fromhex(s['raw'])) if s.get('raw') else len(s['jp'].encode('cp932'))
    cov[s['off']:s['off']+n]=b'\1'*n
pat=re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+')
miss=[]; hit=0
for m in pat.finditer(data):
    b=m.group()
    if len(b)<2: continue
    try: t=b.decode('cp932')
    except: continue
    if not re.search(r'[ぁ-んァ-ヶ一-龯]', t): continue
    # require kana or a plausible name: at least one kana, or 2+ kanji
    if len(re.findall(r'[ぁ-んァ-ヶー]', t)) < 2 or re.search(r'[劔髴鎗癰﨩閒]', t): continue
    if any(cov[m.start():m.end()]): hit+=1; continue
    miss.append((m.start(), t))
print('covered runs', hit, 'missed runs', len(miss))
reg=Counter(o//0x10000 for o,_ in miss); print('missed by 64KB region', sorted(reg.items()))
for o,t in miss[:int(sys.argv[3]) if len(sys.argv)>3 else 40]:
    print(f'  {o:#08x} {data[o-2:o].hex()} {t[:40]}')
