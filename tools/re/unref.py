"""List ELF functions that nothing references (no j/jal/branch into them from outside, no
32-bit word pointing into them, no lui/addiu or lui/ori pair building an address inside them).
Candidates for code caves; still play-test past the screens that might use them."""
import os, struct, sys, bisect
sys.stdout.reconfigure(encoding="utf-8")
W = os.path.join(os.path.expanduser("~"), "srwimpact-work")
E = open(os.path.join(W, "pristine", "disc", "SLPS_251.03"), "rb").read()
LOAD_END = 0x100000 + 0x2DB705
TEXT1 = 0x24F3D4
words = struct.unpack_from(f"<{(LOAD_END - 0x100000) // 4}I", E, 0x1000)
syms = sorted((int(a, 16), int(s), n) for a, s, n in (l.split() for l in open(os.path.join(W, "re", "elf_functions.txt"))))
starts = [s[0] for s in syms]
def owner(a):
    i = bisect.bisect_right(starts, a) - 1
    if i >= 0 and syms[i][0] <= a < syms[i][0] + max(syms[i][1], 4): return i
    return None
referenced = set()
lui = {}
for k, w in enumerate(words):
    a = 0x100000 + 4 * k
    op = w >> 26
    src = owner(a)
    def hit(t):
        o = owner(t)
        if o is not None and o != src: referenced.add(o)
    if a < TEXT1:
        if op in (2, 3): hit(((a + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
        elif op in (1, 4, 5, 6, 7, 20, 21, 22, 23):
            off = struct.unpack("<h", struct.pack("<H", w & 0xFFFF))[0]; hit(a + 4 + off * 4)
        if op == 15: lui[(w >> 16) & 31] = (w & 0xFFFF) << 16
        elif op in (9, 13) and ((w >> 21) & 31) in lui:
            imm = w & 0xFFFF
            hit(lui[(w >> 21) & 31] + (imm - 0x10000 if op == 9 and imm & 0x8000 else imm))
    if 0x100000 <= w < TEXT1: hit(w)
free = [(s, sz, n) for i, (s, sz, n) in enumerate(syms) if i not in referenced and s < TEXT1]
print(len(free), "unreferenced functions,", sum(f[1] for f in free), "bytes")
# merge adjacent runs
runs = []
for s, sz, n in free:
    if runs and runs[-1][1] == s: runs[-1][1] = s + sz; runs[-1][2].append(n)
    else: runs.append([s, s + sz, [n]])
for a, b, ns in sorted(runs, key=lambda r: -(r[1] - r[0]))[:25]:
    print(f"{a:#08x}-{b:#08x} {b-a:6} {', '.join(ns)[:110]}")
