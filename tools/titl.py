#!/usr/bin/env python3
"""Title logo (BTL/TITLPACK.BIN): replace the katakana wordmark with English, per textures/titl.json.

TITLPACK.BIN is 6 textures at a stride of 0x100800: a 1 KB RGBA palette (GS CSM1 order, alpha
0x80 = opaque), 1024x1024 8-bit pixels stored linear, 0x400 bytes of padding (load_title).
Texture 0/1 = title menu rings (already English), 2 = IMPACT build-up frames, 3 = IMPACT alone,
the wordmark alone and the two combined, 4 = lightning, 5 = the combined logo twice (plain and
with a blue glow) plus lightning.

The wordmark is cut out where it differs from the standalone IMPACT (texture 3, top left), the
IMPACT art under it is restored from that standalone copy, and the English wordmark is drawn
in its place: our own lettering (gold face, dark edge, light rim), slanted like the original.

  titl.py build IN.bin OUT.bin
  titl.py preview OUTDIR
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "textures", "titl.json")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
STRIDE, PAL, SIDE = 0x100800, 0x400, 1024


def csm(i):
    return (i & ~0x18) | ((i & 8) << 1) | ((i & 0x10) >> 1)


def palette(data, k):
    o = k * STRIDE
    return [tuple(data[o + csm(i) * 4:o + csm(i) * 4 + 4]) for i in range(256)]


def to_rgba(data, k):
    pal = [(r, g, b, min(255, a * 255 // 128)) for r, g, b, a in palette(data, k)]
    o = k * STRIDE + PAL
    idx = np.frombuffer(data[o:o + SIDE * SIDE], dtype=np.uint8)
    return Image.fromarray(np.array(pal, dtype=np.uint8)[idx].reshape(SIDE, SIDE, 4), "RGBA")


def from_rgba(data, k, im, region):
    """Write im back into texture k for pixels inside region (x0, y0, x1, y1) only."""
    pal = np.array([(r, g, b, min(255, a * 255 // 128)) for r, g, b, a in palette(data, k)], dtype=int)
    clear = [i for i in range(256) if pal[i][3] == 0]
    solid = [i for i in range(256) if pal[i][3] > 0]
    o = k * STRIDE + PAL
    x0, y0, x1, y1 = region
    arr = np.asarray(im).astype(int)
    cache = {}
    for y in range(y0, y1):
        row = o + y * SIDE
        for x in range(x0, x1):
            px = tuple(arr[y, x])
            old = data[row + x]
            if tuple(pal[old]) == px:
                continue
            if px not in cache:
                if px[3] < 16:
                    cache[px] = clear[0]
                else:
                    d = ((pal[solid] - np.array(px)) ** 2 * np.array([1, 1, 1, 2])).sum(1)
                    cache[px] = solid[int(d.argmin())]
            data[row + x] = cache[px]


def wordmark(size, text_lines, font_file, shear, glow=None):
    """Our English wordmark on a transparent canvas of `size`."""
    w, h = size
    big = 4                                        # draw large, then shrink, for smooth edges
    W, H = w * big, h * big
    lines = text_lines
    for pt in range(400, 40, -4):
        f = ImageFont.truetype(font_file, pt)
        boxes = [f.getbbox(t) for t in lines]
        lh = max(b[3] - b[1] for b in boxes)
        tw = max(b[2] - b[0] for b in boxes) + int(shear * lh * len(lines))
        if tw <= W * 0.92 and lh * len(lines) + (len(lines) - 1) * lh * 0.12 <= H * 0.86:
            break
    gap = int(lh * 0.12)
    total = lh * len(lines) + gap * (len(lines) - 1)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    y = (H - total) // 2
    for t, b in zip(lines, boxes):
        d.text(((W - (b[2] - b[0])) // 2 - b[0], y - b[1]), t, fill=255, font=f)
        y += lh + gap
    # slant to the right like the original lettering
    mask = mask.transform((W, H), Image.AFFINE, (1, shear, -shear * H / 2, 0, 1, 0), Image.BICUBIC)
    dark = mask.filter(ImageFilter.MaxFilter(4 * big + 1))
    rim = dark.filter(ImageFilter.MaxFilter(2 * big + 1))
    grad = Image.linear_gradient("L").resize((W, H))
    face = Image.merge("RGB", (
        grad.point(lambda v: 255 - v * 20 // 255),
        grad.point(lambda v: 236 - v * 120 // 255),
        grad.point(lambda v: 140 - v * 130 // 255)))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if glow:
        halo = rim.filter(ImageFilter.MaxFilter(3 * big + 1)).filter(ImageFilter.GaussianBlur(5 * big))
        out.paste(tuple(glow) + (255,), (0, 0), halo)
    out.paste((214, 218, 226, 255), (0, 0), rim)
    out.paste((28, 14, 6, 255), (0, 0), dark)
    out.paste(face, (0, 0), mask)
    return out.resize((w, h), Image.LANCZOS)


def build(src, dst, preview=None):
    spec = json.load(open(SPEC, encoding="utf-8"))
    font_file = os.path.join(FONTS, spec["font"])
    data = bytearray(open(src, "rb").read())
    base = to_rgba(data, 3)
    sx0, sy0, sx1, sy1 = spec["impact_alone"]
    impact = base.crop((sx0, sy0, sx1, sy1))
    lines = spec["text"]
    edited = {}
    for item in spec["logos"]:
        k = item["texture"]
        img = edited.get(k) or to_rgba(data, k)
        x0, y0, x1, y1 = item["box"]
        if "impact_at" in item:
            # restore the IMPACT art under the wordmark (only inside the wordmark's own pixels)
            ix, iy = item["impact_at"]
            under = Image.new("RGBA", img.size, (0, 0, 0, 0))
            under.paste(impact, (ix, iy))
            a = np.asarray(img).astype(int)
            b = np.asarray(under).astype(int)
            diff = (np.abs(a - b).sum(2) > item.get("threshold", 60)).astype(np.uint8) * 255
            m = Image.fromarray(diff, "L")
            box_mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(box_mask).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
            m = ImageChops.multiply(m.filter(ImageFilter.MaxFilter(5)), box_mask)
            img.paste(under, (0, 0), m)
        else:
            ImageDraw.Draw(img).rectangle((x0, y0, x1 - 1, y1 - 1), fill=(0, 0, 0, 0))
        mark = wordmark((x1 - x0, y1 - y0), lines, font_file, spec["shear"], item.get("glow"))
        img.alpha_composite(mark, (x0, y0))
        edited[k] = img
    for k, img in edited.items():
        if preview:
            bg = Image.new("RGBA", img.size, (40, 40, 60, 255))
            bg.alpha_composite(img)
            bg.convert("RGB").save(os.path.join(preview, f"titl_{k}.png"))
        regions = [it["box"] for it in spec["logos"] if it["texture"] == k]
        for r in regions:
            from_rgba(data, k, img, r)
    if dst:
        open(dst, "wb").write(data)
    print(f"title logo: {len(spec['logos'])} wordmarks rendered")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2])
    elif a[0] == "preview":
        os.makedirs(a[1], exist_ok=True)
        src = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc", "BTL", "TITLPACK.BIN")
        build(src, None, a[1])
