"""Find references to an address range in the SRW Impact ELF: jal/j targets, branch targets,
32-bit data words, and lui/addiu (or ori) pairs. Used to prove a code cave is unreferenced.

  refs.py START END            (vaddrs, hex)
  refs.py --candidates         list debug/test functions with no references at all
"""
import os, struct, sys
sys.stdout.reconfigure(encoding="utf-8")
W = os.path.join(os.path.expanduser("~"), "srwimpact-work")
E = open(os.path.join(W, "pristine", "disc", "SLPS_251.03"), "rb").read()
BASE, TEXT0, TEXT1 = 0xFF000, 0x100000, 0x24F3D4
LOAD_END = 0x100000 + 0x2DB705
words = struct.unpack_from(f"<{(LOAD_END - 0x100000) // 4}I", E, 0x1000)
def refs(lo, hi):
    out = []
    lui = {}
    for k, w in enumerate(words):
        a = 0x100000 + 4 * k
        op = w >> 26
        if a < TEXT1:
            if op in (2, 3):                                   # j / jal
                t = ((a + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
                if lo <= t < hi and not (lo <= a < hi): out.append((a, "j" if op == 2 else "jal", t))
            elif op in (1, 4, 5, 6, 7, 20, 21, 22, 23):        # branches
                off = struct.unpack("<h", struct.pack("<H", w & 0xFFFF))[0]
                t = a + 4 + off * 4
                if lo <= t < hi and not (lo <= a < hi): out.append((a, "branch", t))
            if op == 15:                                       # lui rt, imm
                lui[(w >> 16) & 31] = (w & 0xFFFF) << 16
            elif op in (9, 13) and ((w >> 21) & 31) in lui:    # addiu / ori from a lui register
                hi16 = lui[(w >> 21) & 31]
                imm = w & 0xFFFF
                t = hi16 + (imm - 0x10000 if op == 9 and imm & 0x8000 else imm)
                if lo <= t < hi and not (lo <= a < hi): out.append((a, "lui-pair", t))
        if lo <= w < hi and not (lo <= a < hi):
            out.append((a, "word", w))
    return out
if __name__ == "__main__":
    if sys.argv[1] == "--candidates":
        syms = [l.split() for l in open(os.path.join(W, "re", "elf_functions.txt"))]
        import re
        for a, sz, n in syms:
            a, sz = int(a, 16), int(sz)
            if sz >= 200 and re.search(r"debug|Debug|DEBUG|test|TEST|Test|dbg|Dbg|bdt|BDT|pcm|PCM", n):
                r = refs(a, a + sz)
                print(f"{a:#08x} {sz:6} {n:40} refs={len(r)} {[(hex(x[0]), x[1]) for x in r[:3]]}")
    else:
        for r in refs(int(sys.argv[1], 16), int(sys.argv[2], 16)):
            print(hex(r[0]), r[1], hex(r[2]))
