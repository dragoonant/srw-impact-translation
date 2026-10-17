#!/usr/bin/env python3
"""Staff credits (BTL/SROLPACK.BIN): render the English in textures/sroll.json.

SROLPACK.BIN is a run of 35 P2IG images (p2ig.py), 512x512 4-bit, SROLL_00..SROLL_22: white
centred text on transparency, read by load_sroll / make_sroll_spr and scrolled up the screen.
The pages scroll as one strip, so the spec's lines are strip rows (a line may straddle a page
seam); each line is cleared across the width of its original text and the English drawn
centred in it, then the strip is cut back into pages.

  sroll.py build IN.bin OUT.bin
  sroll.py preview OUTDIR
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p2ig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "textures", "sroll.json")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def pages(data):
    pos = [m.start() for m in re.finditer(b"P2IG", data)]
    return [(p, pos[k + 1] if k + 1 < len(pos) else len(data)) for k, p in enumerate(pos)]


def build(src, dst, preview=None):
    spec = json.load(open(SPEC, encoding="utf-8"))
    font_file = os.path.join(FONTS, spec["font"])
    data = bytearray(open(src, "rb").read())
    spans = pages(data)
    origs = [bytes(data[a:b]) for a, b in spans]
    imgs = [p2ig.to_image(o) for o in origs]
    w, h = imgs[0].size
    strip = Image.new("RGBA", (w, h * len(imgs)), (0, 0, 0, 0))
    for k, im in enumerate(imgs):
        strip.paste(im, (0, k * h))
    px = strip.load()
    d = ImageDraw.Draw(strip)
    for y0, y1, text in spec["lines"]:
        xs = [x for x in range(w) for y in range(y0, y1 + 1) if px[x, y][3] > 0]
        if xs:
            d.rectangle((max(0, min(xs) - 2), y0, min(w - 1, max(xs) + 2), y1), fill=(0, 0, 0, 0))
        pt = spec["pt"]
        while True:                                   # shrink the odd over-long line to fit
            font = ImageFont.truetype(font_file, pt)
            b = font.getbbox(text)
            if b[2] - b[0] <= w - 8 or pt <= 12:
                break
            pt -= 1
        cap = font.getbbox("Hg")
        x = (w - (b[2] - b[0])) // 2 - b[0]
        y = (y0 + y1 + 1 - (cap[3] - cap[1])) // 2 - cap[1]
        d.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    for k, ((a, b), orig) in enumerate(zip(spans, origs)):
        img = strip.crop((0, k * h, w, (k + 1) * h))
        if preview:
            bg = Image.new("RGB", img.size, (30, 30, 50))
            bg.paste(img, (0, 0), img)
            bg.save(os.path.join(preview, f"{p2ig.parse(orig)['name']}.png"))
        new = p2ig.from_image(orig, img)
        assert len(new) == len(orig)
        data[a:b] = new
    if dst:
        open(dst, "wb").write(data)
    print(f"staff credits: {len(spec['lines'])} lines on {len(spans)} pages")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2])
    elif a[0] == "preview":
        os.makedirs(a[1], exist_ok=True)
        src = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc", "BTL", "SROLPACK.BIN")
        build(src, None, a[1])
