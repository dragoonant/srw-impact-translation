#!/usr/bin/env python3
"""Proportional 1-byte English for SRW Impact's text renderer.

How the game lays out text (all in the boot ELF, symbols kept):
  font_count_inside (0x1B0D00) counts rows (`@`) and glyphs per row; the per-row glyph count
  sets the canvas stride (count * 32 px). font_decode_inside (0x1B1520) walks the string, copies
  each glyph's pixels into an 8-bit canvas and adds the advance to the row width. Every character
  is read as 2 bytes; ASCII bytes are control codes: `@` row, `c`+B..Y colour, `s`+2 digits
  space, `% & $ #` numbers, `!` inserts a stored string. Glyphs: COMMON.BIN font, 26x26 cells,
  4 bpp; half-width glyphs (JIS rows 1-5) are copied 18 px wide by font_decode_HANKAKU.

This patch:
  * Bytes below 0x80 that are not control codes are single characters: glyph index, left
    bearing and advance come from a 128-entry table; a new routine copies just the advance's
    columns starting at the left bearing (so narrow letters pack tightly), byte by byte.
  * `c` is a colour code only before B..Y, `s` a space code only before two digits; otherwise
    both are letters (in the measuring routine too, so row counts stay right).
  * The encoder (impact_text.py) stores ! # $ % & as bytes 0x1F..0x1B (ASCII ones are control
    codes) and umlauts/accents as 0x18..0x10, drawn from composed glyphs in spare font cells.

Code cave: print_rootmap + print_movemap (0x1947E8-0x194C0C, debug printers nothing references);
table: sceGetstat + sceChstat (0x24A618-0x24A9F4, unused SDK calls). See tools/re/unref.py.

  vwf_impact.py live        patch the running game over PINE (asserts original words)
  vwf_impact.py unlive      restore the original words over PINE
  vwf_impact.py elf IN OUT  patch an ELF file
  vwf_impact.py table       print the width table
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mips import Asm
import impact_font as F

BASE = 0xFF000                 # vaddr - file offset (single PT_LOAD at file 0x1000)
CAVE, CAVE_END = 0x1947E8, 0x194C0C
TABLE, TABLE_END = 0x24A618, 0x24A9F4
GAP = 1                        # columns between glyph ink
SPACE = 6                      # advance of an ASCII space

# original routine addresses
CNV = 0x1B0750                 # cnvSjisToAddr
DEC_LOOP = 0x1B17D8            # font_decode_inside: lbu v0,(s1); bnez -> top
DEC_AFTER_CNV = 0x1B174C       # move a1, v0
DEC_S_BODY = 0x1B16CC          # after lb a1,1(s1); lbu v0,2(s1)
CNT_LOOP = 0x1B0D28            # font_count_inside loop top
CNT_GEN2 = 0x1B0E1C            # generic glyph: addu v0, s2, v0 ...
CNT_S_BODY = 0x1B0DFC          # 's' body after lw v1,0x3c(s1); addiu s0,s0,3

# remapped symbols and composed letters: byte -> character
REMAP = {0x1F: "!", 0x1E: "#", 0x1D: "$", 0x1C: "%", 0x1B: "&", 0x1A: "c", 0x19: "s",
         0x18: "ü", 0x17: "ä", 0x16: "ö", 0x15: "é", 0x14: "Ü", 0x13: "Ö", 0x12: "Ä", 0x11: "è", 0x10: "à"}
# composed glyph cells (unassigned JIS row-1 codes, blank in the font)
COMPOSED = {"ü": 0x81AD, "ä": 0x81AE, "ö": 0x81AF, "é": 0x81B0, "Ü": 0x81B1, "Ö": 0x81B2,
            "Ä": 0x81B3, "è": 0x81B4, "à": 0x81B5}
# ASCII -> full-width code whose glyph is drawn
SPECIAL = {"'": 0x8166, '"': 0x8168, "-": 0x815D, "~": 0x8160, " ": 0x8140}


def glyph_code(ch):
    if ch in COMPOSED:
        return COMPOSED[ch]
    if ch in SPECIAL:
        return SPECIAL[ch]
    return int.from_bytes(F.fullwidth(ch).encode("cp932"), "big")


def table():
    """128 x (u16 glyph index, u8 left bearing, u8 advance)."""
    out = bytearray()
    rows = []
    for b in range(128):
        ch = REMAP.get(b, chr(b) if 0x20 <= b < 0x7F else None)
        if ch is None:
            idx, lb, adv = 0, 0, 0
        elif ch == " ":
            idx, lb, adv = F.index_of(0x8140), 0, SPACE
        else:
            idx = F.index_of(glyph_code(ch))
            ink = F.ink(idx, 18)
            lb, rb = ink if ink else (0, 5)
            adv = rb - lb + 1 + GAP
        out += struct.pack("<HBB", idx, lb, adv)
        rows.append((b, ch, idx, lb, adv))
    return bytes(out), rows


def cave_code():
    a = Asm(CAVE)
    # -- font_decode_inside: generic glyph path (replaces jal cnvSjisToAddr; a0 = s1 already)
    a.label("dispatch")
    a.lbu("t0", 0, "s1"); a.sltiu("t1", "t0", 0x80); a.bnez("t1", "ascii"); a.nop()
    a.jal(CNV); a.nop()
    a.j(DEC_AFTER_CNV); a.nop()
    # -- decode 's': space code only before two digits
    a.label("s_decode")
    for off in (1, 2):
        a.lbu("t0", off, "s1"); a.addiu("t0", "t0", -0x30); a.sltiu("t0", "t0", 10)
        a.beqz("t0", "ascii"); a.nop()
    a.lb("a1", 1, "s1"); a.lbu("v0", 2, "s1"); a.j(DEC_S_BODY); a.nop()
    # -- one 1-byte character
    a.label("ascii")
    a.lbu("t0", 0, "s1")
    a.la("t1", TABLE)
    a.sll("t2", "t0", 2); a.addu("t1", "t1", "t2")
    a.lhu("t3", 0, "t1"); a.lbu("a3", 2, "t1"); a.lbu("t5", 3, "t1")
    a.lw("a1", 0x10, "s3")                      # font base
    a.li("t6", 338); a.mult("t3", "t6"); a.mflo("t7"); a.addu("a1", "a1", "t7")
    a.move("a0", "s3"); a.move("a2", "s2")
    a.jal("draw"); a.nop()
    a.addiu("s1", "s1", 1)
    a.addu("s2", "s2", "t5")
    a.lw("t0", 0x3C, "s3"); a.sll("t0", "t0", 2); a.addu("t0", "s3", "t0")
    a.lw("t1", 0x60, "t0"); a.addu("t1", "t1", "t5"); a.sw("t1", 0x60, "t0")
    a.j(DEC_LOOP); a.nop()
    # -- draw: a0 ctx, a1 glyph, a2 canvas x, a3 left bearing, t5 advance (columns to write)
    a.label("draw")
    a.lw("t0", 0x3C, "a0"); a.sll("t0", "t0", 2); a.addu("t0", "a0", "t0")
    a.lw("t0", 0x1C, "t0"); a.sll("t0", "t0", 5)          # stride = glyphs in row * 32
    a.lhu("t1", -0x70A4, "gp"); a.sll("t1", "t1", 9)       # colour -> palette
    a.la("t2", 0x29DD80); a.addu("t1", "t1", "t2")
    a.li("t2", 26)
    a.label("row")
    a.move("t3", "zero")
    a.beqz("t5", "row_end"); a.nop()
    a.label("col")
    a.addu("t4", "a3", "t3")                               # source column
    a.move("t7", "zero")
    a.sltiu("t6", "t4", 18); a.beqz("t6", "pix"); a.nop()
    a.srl("t6", "t4", 1); a.addu("t6", "a1", "t6"); a.lbu("t7", 0, "t6")
    a.andi("t6", "t4", 1); a.beqz("t6", "low"); a.nop()
    a.srl("t7", "t7", 4); a.b("pix"); a.nop()
    a.label("low")
    a.andi("t7", "t7", 0xF)
    a.label("pix")
    a.sll("t7", "t7", 1); a.addu("t7", "t1", "t7"); a.lbu("t7", 0, "t7")
    a.addu("t6", "a2", "t3"); a.sb("t7", 0, "t6")
    a.addiu("t3", "t3", 1); a.slt("t6", "t3", "t5"); a.bnez("t6", "col"); a.nop()
    a.label("row_end")
    a.addiu("a1", "a1", 13); a.addu("a2", "a2", "t0")
    a.addiu("t2", "t2", -1); a.bgtz("t2", "row"); a.nop()
    a.jr("ra"); a.nop()
    # -- font_count_inside: generic glyph (replaces addiu s0,s0,2; delay sll v0,v0,2 runs)
    a.label("count_gen")
    a.bltz("v1", "count_gen2"); a.addiu("s0", "s0", 2)     # delay slot always runs
    a.addiu("s0", "s0", -1)
    a.label("count_gen2")
    a.j(CNT_GEN2); a.nop()
    # -- count 'c' (replaces b loop; delay addiu s0,s0,2 already ran)
    a.label("c_count")
    a.lbu("t0", -1, "s0"); a.addiu("t0", "t0", -0x42); a.sltiu("t0", "t0", 0x18)
    a.beqz("t0", "c_glyph"); a.nop()
    a.j(CNT_LOOP); a.nop()
    a.label("c_glyph")
    a.addiu("s0", "s0", -2); a.lw("v0", 0x3C, "s1"); a.j("count_hook_site"); a.nop()
    # -- count 's' (replaces lw v1,0x3c(s1); delay addiu s0,s0,3 already ran)
    a.label("s_count")
    for off in (-2, -1):
        a.lbu("t0", off, "s0"); a.addiu("t0", "t0", -0x30); a.sltiu("t0", "t0", 10)
        a.beqz("t0", "s_glyph"); a.nop()
    a.lw("v1", 0x3C, "s1"); a.j(CNT_S_BODY); a.nop()
    a.label("s_glyph")
    a.addiu("s0", "s0", -3); a.lw("v0", 0x3C, "s1"); a.j("count_hook_site"); a.nop()
    a.labels["count_hook_site"] = 0x1B0E14
    words = a.assemble()
    assert CAVE + 4 * len(words) <= CAVE_END, "cave overflow"
    return words, a.labels


def hooks(labels):
    """(address, original word, new word) for every site in the original code."""
    def j(t): return (2 << 26) | ((t >> 2) & 0x3FFFFFF)
    def beqz_v1(pc, t): return (0x04 << 26) | (3 << 21) | (((t - (pc + 4)) >> 2) & 0xFFFF)
    return [
        (0x1B1744, 0x0C06C1D4, j(labels["dispatch"])),        # jal cnvSjisToAddr
        (0x1B1658, 0x1060005E, beqz_v1(0x1B1658, labels["ascii"])),  # beqz v1 -> skip 'c'
        (0x1B16C4, 0x82250001, j(labels["s_decode"])),        # lb a1,1(s1)
        (0x1B0E14, 0x26100002, j(labels["count_gen"])),       # addiu s0,s0,2
        (0x1B0DE4, 0x1000FFD0, j(labels["c_count"])),         # b loop ('c')
        (0x1B0DF4, 0x8E23003C, j(labels["s_count"])),         # lw v1,0x3c(s1) ('s')
    ]


def blob():
    words, labels = cave_code()
    tab, _ = table()
    assert TABLE + len(tab) <= TABLE_END
    return words, labels, tab


def patch_elf(data):
    out = bytearray(data)
    words, labels, tab = blob()
    for addr, orig, new in hooks(labels):
        cur = struct.unpack_from("<I", out, addr - BASE)[0]
        assert cur == orig, f"{addr:#x}: expected {orig:08x}, found {cur:08x}"
        struct.pack_into("<I", out, addr - BASE, new)
    out[CAVE - BASE:CAVE - BASE + 4 * len(words)] = struct.pack(f"<{len(words)}I", *words)
    out[TABLE - BASE:TABLE - BASE + len(tab)] = tab
    return bytes(out)


def live(undo=False):
    from pine import Pine
    p = Pine()
    words, labels, tab = blob()
    if not undo:
        p.write(TABLE, tab)
        p.write(CAVE, struct.pack(f"<{len(words)}I", *words))
    for addr, orig, new in hooks(labels):
        cur = struct.unpack("<I", p.read(addr, 4))[0]
        want, put = (new, orig) if undo else (orig, new)
        assert cur in (want, put), f"{addr:#x}: found {cur:08x}"
        p.write(addr, struct.pack("<I", put))
    print("unpatched" if undo else f"patched live: {len(words)} cave words, {len(tab)} table bytes")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "live":
        live()
    elif a[0] == "unlive":
        live(undo=True)
    elif a[0] == "elf":
        open(a[2], "wb").write(patch_elf(open(a[1], "rb").read()))
        print("patched", a[2])
    elif a[0] == "table":
        for row in table()[1]:
            if row[1]:
                print(row)
