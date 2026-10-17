"""Disassemble SRW Impact ELF functions by name or address, with symbol names for calls.

  dis.py NAME_OR_HEXADDR [more ...] [--len N]
Reads ~/srwimpact-work/pristine/disc/SLPS_251.03 and ~/srwimpact-work/re/elf_functions.txt.
"""
import os, struct, sys
import capstone
sys.stdout.reconfigure(encoding="utf-8")
W = os.path.join(os.path.expanduser("~"), "srwimpact-work")
ELF = open(os.path.join(W, "pristine", "disc", "SLPS_251.03"), "rb").read()
BASE = 0xFF000                       # vaddr - file offset for the loaded segment
syms, byname = {}, {}
for line in open(os.path.join(W, "re", "elf_functions.txt")):
    a, sz, n = line.split()
    syms[int(a, 16)] = (n, int(sz)); byname[n] = (int(a, 16), int(sz))
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS64 + capstone.CS_MODE_LITTLE_ENDIAN)
md.skipdata = True
def name_of(a):
    if a in syms: return syms[a][0]
    best = max((s for s in syms if s <= a), default=None)
    return f"{syms[best][0]}+{a-best:#x}" if best is not None else hex(a)
def dis(start, size):
    code = ELF[start - BASE:start - BASE + size]
    for i in md.disasm(code, start):
        note = ""
        if i.mnemonic in ("jal", "j") and i.op_str.startswith("0x"):
            note = "  ; " + name_of(int(i.op_str, 16))
        print(f"{i.address:08x}: {struct.unpack_from('<I', ELF, i.address - BASE)[0]:08x}  {i.mnemonic:8} {i.op_str}{note}")
if __name__ == "__main__":
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--len"]
    ln = int(sys.argv[sys.argv.index("--len") + 1], 0) if "--len" in sys.argv else None
    for a in args:
        if a in byname: s, sz = byname[a]
        else: s, sz = int(a, 16), 0x100
        print(f"== {name_of(s)} {s:#x} ({sz} bytes)")
        dis(s, ln or sz)
