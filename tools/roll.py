#!/usr/bin/env python3
"""Opening / ending text crawls (BTL/ROLLPACK.BIN): render the English in textures/roll.json.

ROLLPACK.BIN is a run of 26 P2IG images (p2ig.py), 512x512 8-bit: R_TIT (the part title
cards, see render_titles) and the crawl pages OP1_1..ED3_4: white serif text, left aligned, on 16 row slots
32 px apart. Each translated row is cleared and redrawn; rows listed in `keep` (already English
in the original art: credits, "THE END", episode titles) keep their pixels. Sizes do not change.

  roll.py build IN.bin OUT.bin
  roll.py preview OUTDIR
"""
import json
import os
import re
import struct
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p2ig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "textures", "roll.json")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
ROW, X0, PT = 32, 3, 19


def pages(data):
    pos = [m.start() for m in re.finditer(b"P2IG", data)]
    return [(p, pos[k + 1] if k + 1 < len(pos) else len(data)) for k, p in enumerate(pos)]


def render(orig_img, rows, keep, font):
    img = orig_img.copy()
    d = ImageDraw.Draw(img)
    for r, text in enumerate(rows):
        if r + 1 in keep:
            continue
        y = r * ROW
        d.rectangle((0, y, 511, y + ROW - 1), fill=(0, 0, 0, 0))
        if text:
            # thin dark edge, then the white text, as in the original pages
            for dx, dy in ((1, 1), (-1, 0), (0, -1), (1, 0), (0, 1)):
                d.text((X0 + dx, y + 4 + dy), text, font=font, fill=(16, 16, 24, 255))
            d.text((X0, y + 4), text, font=font, fill=(255, 255, 255, 255))
    return img


def render_titles(orig_img, pt_spec, font_file):
    """R_TIT: the part title cards. Each part draws two sprites side by side (make_rt_spr):
    a 448-px strip at x=40 and a 112-px cell at x=488 (the 篇 kanji), so one title is drawn
    across 560 px and sliced into the two rects."""
    img = orig_img.copy()
    ImageDraw.Draw(img).rectangle(tuple(pt_spec["clear"]), fill=(0, 0, 0, 0))
    texts = pt_spec["text"]
    for pt in range(72, 20, -1):
        font = ImageFont.truetype(font_file, pt)
        if all(font.getbbox(t)[2] - font.getbbox(t)[0] <= 540 for t in texts):
            break
    for text, main, cell in zip(texts, pt_spec["main"], pt_spec["suffix"]):
        mw, h = main[2] - main[0], main[3] - main[1]
        cw = cell[2] - cell[0]
        mask = Image.new("L", (mw + cw, h), 0)
        b = font.getbbox(text)
        x = (mw + cw - (b[2] - b[0])) // 2 - b[0]
        cap = font.getbbox("H")
        y = (h - (cap[3] - cap[1])) // 2 - cap[1]
        ImageDraw.Draw(mask).text((x, y), text, fill=255, font=font)
        # silver face (white at the top, grey at the foot) over a dark edge, like the kanji
        face = Image.linear_gradient("L").resize((mw + cw, h)).point(lambda v: 255 - v * 105 // 255)
        strip = Image.new("RGBA", (mw + cw, h), (0, 0, 0, 0))
        strip.paste((24, 24, 32, 255), (0, 0), mask.filter(ImageFilter.MaxFilter(5)))
        strip.paste(Image.merge("RGBA", (face, face, face, Image.new("L", face.size, 255))), (0, 0), mask)
        img.paste(strip.crop((0, 0, mw, h)), (main[0], main[1]))
        img.paste(strip.crop((mw, 0, mw + cw, h)), (cell[0], cell[1]))
    return img


def patch_elf(elf):
    """Part 3 shares part 2's 篇 cell; point it at its own cell (u0, u1 of its record)."""
    elf = bytearray(elf)
    spec = json.load(open(SPEC, encoding="utf-8"))["part_titles"]
    u0, _, u1, _ = spec["suffix"][2]
    off = 0x269020 + 2 * 0x14 + 8 - 0xFF000
    assert struct.unpack_from("<hh", elf, off) == (112, 328), "unexpected roll title table"
    struct.pack_into("<h", elf, off, u0)
    struct.pack_into("<h", elf, off + 4, u1)
    return bytes(elf)


def build(src, dst, preview=None):
    spec = json.load(open(SPEC, encoding="utf-8"))
    font = ImageFont.truetype(os.path.join(FONTS, spec.get("font", "georgia.ttf")), spec.get("pt", PT))
    data = bytearray(open(src, "rb").read())
    n = 0
    for a, b in pages(data):
        orig = bytes(data[a:b])
        name = p2ig.parse(orig)["name"]
        if name == "R_TIT" and "part_titles" in spec:
            img = render_titles(p2ig.to_image(orig), spec["part_titles"],
                                os.path.join(FONTS, spec["part_titles"]["font"]))
            if preview:
                bg = Image.new("RGB", img.size, (30, 30, 50))
                bg.paste(img, (0, 0), img)
                bg.save(os.path.join(preview, f"{name}.png"))
            data[a:b] = p2ig.from_image(orig, img)
            n += 1
            continue
        rows = spec["pages"].get(name)
        if not rows:
            continue
        assert len(rows) == 16, name
        img = render(p2ig.to_image(orig), rows, set(spec.get("keep", {}).get(name, [])), font)
        if preview:
            bg = Image.new("RGB", img.size, (30, 30, 50))
            bg.paste(img, (0, 0), img)
            bg.save(os.path.join(preview, f"{name}.png"))
        new = p2ig.from_image(orig, img)
        assert len(new) == len(orig)
        data[a:b] = new
        n += 1
    if dst:
        open(dst, "wb").write(data)
    print(f"crawl: {n} pages rendered")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2])
    elif a[0] == "preview":
        os.makedirs(a[1], exist_ok=True)
        src = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc", "BTL", "ROLLPACK.BIN")
        build(src, None, a[1])
