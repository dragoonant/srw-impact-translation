"""SRW Impact's dialogue font (MAP/COMMON.BIN + 0x2400): glyph lookup, ink metrics, previews.

Glyph i is 338 bytes at COMMON.BIN + 0x2400 + i*338: 26 rows of 13 bytes, 4 bits per pixel
(26x26 cell). Index = row*94 + col from the ELF's lead/trail tables (vaddr 0x29ED80/0x29EE80);
indices below 470 (JIS rows 1-5: symbols, digits, Latin, kana) are half-width and drawn 18 px
wide, the rest 26 px. Some rare kanji are remapped to spare slots (cnvSjisToAddr); not needed here.

  impact_font.py preview OUT.png TEXT     render TEXT with the proportional metrics
  impact_font.py metrics                  print ink extents of the ASCII-equivalent glyphs
"""
import os, struct, sys
sys.stdout.reconfigure(encoding="utf-8")
DISC = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc")
FONT_AT, GLYPH, ROWB, ROWS = 0x2400, 338, 13, 26
_common = _elf = None


def _load():
    global _common, _elf
    if _common is None:
        _common = open(os.path.join(DISC, "MAP", "COMMON.BIN"), "rb").read()
        _elf = open(os.path.join(DISC, "SLPS_251.03"), "rb").read()


def index_of(code):
    """Glyph index of a 2-byte Shift-JIS code (rows 1-5 only)."""
    _load()
    lead, trail = code >> 8, code & 0xFF
    r = _elf[0x29ED80 - 0xFF000 + lead]
    c = _elf[0x29EE80 - 0xFF000 + trail]
    if trail >= 0x9F:
        r += 1
    return r * 94 + c


def pixels(idx):
    _load()
    g = _common[FONT_AT + idx * GLYPH:FONT_AT + (idx + 1) * GLYPH]
    out = []
    for y in range(ROWS):
        row = []
        for b in g[y * ROWB:(y + 1) * ROWB]:
            row += [b & 0xF, b >> 4]
        out.append(row)
    return out


def ink(idx, width=18):
    px = pixels(idx)
    cols = [x for x in range(width) if any(px[y][x] for y in range(ROWS))]
    return (cols[0], cols[-1]) if cols else None


def fullwidth(ch):
    if ch == " ":
        return "\u3000"
    if "!" <= ch <= "~":
        return {"'": "’", '"': "”", "-": "－", "~": "～", "\\": "＼"}.get(ch, chr(ord(ch) + 0xFEE0))
    return ch


ASCII = [chr(c) for c in range(0x20, 0x7F)]

if __name__ == "__main__":
    if sys.argv[1] == "metrics":
        for ch in ASCII:
            code = int.from_bytes(fullwidth(ch).encode("cp932"), "big")
            i = index_of(code)
            print(repr(ch), hex(code), i, ink(i))


# ---- composed glyphs (umlauts / accents) written into blank cells at build time ---------

DOT = [[1, 1, 1], [1, 0xE, 1], [1, 1, 1]]


def _set_pixels(buf, idx, px):
    at = FONT_AT + idx * GLYPH
    for y in range(ROWS):
        for x in range(0, 26, 2):
            buf[at + y * ROWB + x // 2] = (px[y][x] & 0xF) | ((px[y][x + 1] & 0xF) << 4)


def compose(buf):
    """Draw ü ä ö é Ü Ö Ä è à into their spare cells (see vwf_impact.COMPOSED). buf: COMMON.BIN."""
    global _common
    import vwf_impact
    _load()
    base = {"ü": "u", "ä": "a", "ö": "o", "é": "e", "Ü": "U", "Ö": "O", "Ä": "A", "è": "e", "à": "a"}
    for ch, code in vwf_impact.COMPOSED.items():
        b = base[ch]
        src = index_of(int.from_bytes(fullwidth(b).encode("cp932"), "big"))
        px = [row[:] for row in pixels(src)]
        lb, rb = ink(src, 18)
        top = 0 if b.isupper() else 4
        if ch in "üäöÜÖÄ":
            mid = (lb + rb) // 2
            for dx in (mid - 4, mid + 2):
                for y in range(3):
                    for x in range(3):
                        if 0 <= dx + x < 18:
                            px[top + y][dx + x] = DOT[y][x]
        else:                       # acute (é) or grave (è, à): a short diagonal
            mid = (lb + rb) // 2
            for k in range(4):
                x = mid - 1 + k if ch == "é" else mid + 2 - k
                y = top + 3 - k if ch == "é" else top + 3 - k
                for xx, v in ((x - 1, 1), (x, 0xE), (x + 1, 1)):
                    if 0 <= xx < 18 and 0 <= y < ROWS:
                        px[y][xx] = max(px[y][xx], v)
        _set_pixels(buf, index_of(code), px)
    return buf


def preview(path, text, scale=3):
    """Render text (game bytes or str) with the proportional metrics into a PNG."""
    from PIL import Image
    import vwf_impact, impact_text
    _load()
    rows = vwf_impact.table()[1]
    tab = {b: (idx, lb, adv) for b, ch, idx, lb, adv in rows}
    data = impact_text.to_game(text) if isinstance(text, str) else text
    lines = data.split(b"@")
    W = max(sum(tab.get(c, (0, 0, 10))[2] for c in ln) for ln in lines) + 4
    img = Image.new("L", (W, 28 * len(lines)), 0)
    for li, ln in enumerate(lines):
        x = 2
        for c in ln:
            idx, lb, adv = tab.get(c, (0, 0, 10))
            px = pixels(idx)
            for y in range(ROWS):
                for cx in range(adv):
                    sc = lb + cx
                    if sc < 18 and px[y][sc]:
                        img.putpixel((x + cx, li * 28 + y), 40 + px[y][sc] * 14)
            x += adv
    img.resize((img.width * scale, img.height * scale), Image.NEAREST).save(path)
