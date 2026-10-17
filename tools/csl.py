#!/usr/bin/env python3
"""Battle console atlas (BTL/CSL_PACK.BIN): render the English in textures/csl.json.

CSL_PACK.BIN is 25 chunks of 0x40400 bytes, one per series (CslPackLoad reads chunk n at
n * 0x40400): a 1 KB RGBA palette in GS CSM1 order, then 1024x256 8-bit pixels stored linear.
The game uploads it as a 1024-wide PSMT8 texture (TEX0 TBW 16), so it must be viewed 1024 wide;
read 512 wide every second row looks like an overlapping second image. Magenta is transparent.

Repainted, in every chunk: the 7 command badges (攻反防避援同戦), the command labels (support /
dual / combo attack, counter) and the skill / defense labels in their ovals, all inside the
game's own sprite rects; in chunks 1-24 the series-name banner. Sizes do not change.

  csl.py build IN.bin OUT.bin
  csl.py preview OUTDIR
"""
import json
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "textures", "csl.json")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
CHUNK, W, H = 0x40400, 1024, 256
KEY = (254, 2, 254)                 # transparent magenta (palette alpha 0)
EDGE = (1, 1, 1)


def csm(i):
    return (i & ~0x18) | ((i & 8) << 1) | ((i & 0x10) >> 1)


def palette(chunk):
    return [tuple(chunk[csm(i) * 4:csm(i) * 4 + 4]) for i in range(256)]


def to_image(chunk):
    pal = palette(chunk)
    im = Image.new("RGB", (W, H))
    im.putdata([pal[v][:3] for v in chunk[0x400:]])
    return im


def from_image(chunk, im):
    pal = palette(chunk)
    rgb = [p[:3] for p in pal]
    cache = {}
    old = chunk[0x400:]
    out = bytearray(chunk)
    for i, px in enumerate(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()):
        if px == rgb[old[i]]:
            continue                # unchanged pixel keeps its exact index
        if px not in cache:
            cands = range(256)
            if px != KEY:           # never map a drawn pixel onto a transparent entry
                cands = [k for k in cands if pal[k][3] > 0]
            cache[px] = min(cands, key=lambda k: sum((a - b) ** 2 for a, b in zip(rgb[k], px)))
        out[0x400 + i] = cache[px]
    return bytes(out)


def fit(font_file, text, w, h, start=24, low=9):
    for pt in range(start, low - 1, -1):
        f = ImageFont.truetype(font_file, pt)
        b = f.getbbox(text)
        if b[2] - b[0] <= w and b[3] - b[1] <= h:
            return f
    return ImageFont.truetype(font_file, low)


def draw_text(img, box, text, font, fill, edge=EDGE, edge_px=3):
    """Text centred in box (x0, y0, x1, y1) with a dark edge, clipped to the box."""
    x0, y0, x1, y1 = box
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    b = font.getbbox(text)
    cap = font.getbbox("H")
    x = x0 + (x1 - x0 - (b[2] - b[0])) // 2 - b[0]
    y = y0 + (y1 - y0 - (cap[3] - cap[1])) // 2 - cap[1]
    d.text((x, y), text, fill=255, font=font)
    clip = Image.new("L", img.size, 0)
    ImageDraw.Draw(clip).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    from PIL import ImageChops
    mask = ImageChops.multiply(mask.point(lambda v: 255 if v > 110 else 0), clip)
    grown = mask.filter(ImageFilter.MaxFilter(edge_px)) if edge_px >= 3 else mask
    outline = ImageChops.multiply(grown, clip)
    img.paste(edge, (0, 0), outline)
    img.paste(fill, (0, 0), mask)


def main_colour(img, rect):
    x0, y0, x1, y1 = rect
    c = Counter(img.getpixel((x, y)) for x in range(x0, x1) for y in range(y0, y1))
    for col, _ in c.most_common():
        if col != KEY and sum(col) > 120:
            return col
    return (255, 255, 255)


def render(img, spec, k, font_file):
    img = img.copy()
    d = ImageDraw.Draw(img)
    # badges: keep the green frame, repaint the dark inside
    by0, by1 = spec["badges"]["y"]
    bfont = ImageFont.truetype(font_file, min(
        fit(font_file, t, x1 - x0 - 6, 14, 14, 8).size for (x0, x1), t in zip(spec["badges"]["x"], spec["badges"]["text"])))
    for (bx0, bx1), text in zip(spec["badges"]["x"], spec["badges"]["text"]):
        inner = (bx0 + 4, by0 + 4, bx1 - 3, by1 - 3)
        fill = next(c for c, _ in Counter(img.getpixel((x, y)) for x in range(inner[0], inner[2])
                    for y in range(inner[1], inner[3])).most_common() if sum(c) < 300)
        d.rectangle(inner, fill=fill)
        draw_text(img, (inner[0], inner[1], inner[2] + 1, inner[3] + 1), text,
                  bfont, (255, 255, 255), edge_px=3)
    # plain coloured command labels
    # one size per group, set by the tightest label, so neighbours match
    pt = min(fit(font_file, t, r[2] - r[0] - 2, 23, 20).size for r, t in spec["plain"])
    font = ImageFont.truetype(font_file, pt)
    for rect, text in spec["plain"]:
        col = main_colour(img, rect)
        d.rectangle((rect[0], rect[1], rect[2] - 1, rect[3] - 1), fill=KEY)
        draw_text(img, rect, text, font, col)
    # skill / defense labels in black ovals
    pt = min(fit(font_file, t, r[2] - r[0] - 16, 18, 20).size for r, t in spec["oval"])
    font = ImageFont.truetype(font_file, pt)
    for rect, text in spec["oval"]:
        x0, y0, x1, y1 = rect
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=KEY)
        d.ellipse((x0 + 1, y0 + 2, x1 - 2, y1 - 3), outline=EDGE, width=2)
        draw_text(img, (x0 + 6, y0, x1 - 6, y1), text, font, (246, 253, 253))
    # series banner: wipe the title with a text-free column of the panel, then redraw
    title = spec["banner"]["titles"].get(str(k))
    if title:
        bx0, by0, bx1, by1 = spec["banner"]["rect"]
        sx = spec["banner"]["source_x"]
        col = img.crop((sx, by0, sx + 1, by1))
        for x in range(bx0, bx1):
            img.paste(col, (x, by0))
        draw_text(img, (bx0 + 6, by0, bx1 - 6, by1), title,
                  fit(font_file, title, bx1 - bx0 - 20, 34, 34, 14), (255, 255, 255), edge_px=3)
    return img


def build(src, dst, preview=None):
    spec = json.load(open(SPEC, encoding="utf-8"))
    font_file = os.path.join(FONTS, spec["font"])
    data = bytearray(open(src, "rb").read())
    assert len(data) == 25 * CHUNK
    for k in range(25):
        chunk = bytes(data[k * CHUNK:(k + 1) * CHUNK])
        img = render(to_image(chunk), spec, k, font_file)
        if preview:
            img.save(os.path.join(preview, f"csl_{k:02d}.png"))
        data[k * CHUNK:(k + 1) * CHUNK] = from_image(chunk, img)
    if dst:
        open(dst, "wb").write(data)
    print("battle console: 25 chunks rendered")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2])
    elif a[0] == "preview":
        os.makedirs(a[1], exist_ok=True)
        src = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc", "BTL", "CSL_PACK.BIN")
        build(src, None, a[1])
