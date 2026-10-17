#!/usr/bin/env python3
"""Stage title cards (MAP/STAGETIT.BIN): render the English titles in textures/stagetit.json.

STAGETIT.BIN is a run of P2IG images (see p2ig.py): STIT000 (digit atlas) then STIT001-105,
512x128 8-bit, a white serif title with a dark outline on transparency. Each English title is
drawn white with a dark outline, centred, shrunk to fit, `|` = line break; the image is mapped
onto the card's own palette (p2ig.from_image) and written back in place (sizes do not change).

  stagetit.py build IN.bin OUT.bin
  stagetit.py preview OUTDIR          PNGs of the rendered cards
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p2ig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "textures", "stagetit.json")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def cards(data):
    pos = [m.start() for m in re.finditer(b"P2IG", data)]
    return [(p, pos[k + 1] if k + 1 < len(pos) else len(data)) for k, p in enumerate(pos)]


def render(title, size, font_file):
    w, h = size
    lines = title.split("|")
    for pt in range(44, 10, -2):          # 44 pt cap keeps one- and two-line cards alike
        font = ImageFont.truetype(font_file, pt)
        boxes = [font.getbbox(ln) for ln in lines]
        tw = max(b[2] - b[0] for b in boxes)
        lh = max(b[3] - b[1] for b in boxes) + 4
        if tw <= w - min(24, w // 6) and lh * len(lines) <= h - 12:
            break
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    y0 = (h - lh * len(lines)) // 2
    for i, ln in enumerate(lines):
        b = font.getbbox(ln)
        x = (w - (b[2] - b[0])) // 2 - b[0]
        d.text((x, y0 + i * lh - b[1]), ln, fill=255, font=font)
    outline = mask.filter(ImageFilter.MaxFilter(5))
    img.paste((24, 24, 32, 255), (0, 0), outline)
    img.paste((255, 255, 255, 255), (0, 0), mask)
    return img


def render_atlas(orig_img, atlas, font_file):
    """STIT000: replace the 第/話/最/終 cells, keep the digits."""
    img = orig_img.copy()
    x0, y0, x1, y1 = atlas["clear"]
    ImageDraw.Draw(img).rectangle((x0, y0, x1, y1), fill=(0, 0, 0, 0))
    # one font size for every cell; text that continues into the next cell (FIN|AL) is aligned
    # to the shared edge so the halves read as one word
    texts = [t for _, _, t in atlas["cells"] if t]
    cw = min(c1 - c0 + 1 for c0, c1, _ in atlas["cells"])
    for pt in range(40, 10, -1):
        font = ImageFont.truetype(font_file, pt)
        if max(font.getbbox(t)[2] - font.getbbox(t)[0] for t in texts) <= cw - 2:
            break
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    cells = atlas["cells"]
    for i, (cx0, cx1, text) in enumerate(cells):
        if not text:
            continue
        b = font.getbbox(text)
        tw, th = b[2] - b[0], b[3] - b[1]
        joins_next = i + 1 < len(cells) and cells[i + 1][2]
        joins_prev = i > 0 and cells[i - 1][2] and text != "EP."
        if joins_next:
            x = cx1 - tw - b[0]
        elif joins_prev:
            x = cx0 - b[0]
        else:
            x = cx0 + (cx1 - cx0 + 1 - tw) // 2 - b[0]
        d.text((x, y0 + (y1 - y0 - th) // 2 - b[1]), text, fill=255, font=font)
    outline = mask.filter(ImageFilter.MaxFilter(5))
    img.paste((24, 24, 32, 255), (0, 0), outline)
    img.paste((255, 255, 255, 255), (0, 0), mask)
    return img


def build(src, dst, preview=None):
    spec = json.load(open(SPEC, encoding="utf-8"))
    font_file = os.path.join(FONTS, spec["font"])
    data = bytearray(open(src, "rb").read())
    n = 0
    atlas = spec.get("atlas")
    for k, (a, b) in enumerate(cards(data)):
        if atlas and k == atlas["card"]:
            orig = bytes(data[a:b])
            img = render_atlas(p2ig.to_image(orig), atlas, font_file)
            if preview:
                img.save(os.path.join(preview, f"stit_{k:03d}.png"))
            data[a:b] = p2ig.from_image(orig, img)
            n += 1
            continue
        title = spec["titles"].get(str(k))
        if not title:
            continue
        orig = bytes(data[a:b])
        h = p2ig.parse(orig)
        img = render(title, (h["w"], h["h"]), font_file)
        if preview:
            img.save(os.path.join(preview, f"stit_{k:03d}.png"))
        new = p2ig.from_image(orig, img)
        assert len(new) == len(orig)
        data[a:b] = new
        n += 1
    if dst:
        open(dst, "wb").write(data)
    print(f"stage titles: {n} cards rendered")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2])
    elif a[0] == "preview":
        os.makedirs(a[1], exist_ok=True)
        src = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc", "MAP", "STAGETIT.BIN")
        build(src, None, a[1])
