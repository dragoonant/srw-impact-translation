#!/usr/bin/env python3
"""Title-screen backdrop (MAP/IMNBG.BIN entry 76): replace the katakana wordmark with English.

The backdrop behind PRESS ANY BUTTON is not drawn from TITLPACK: the title calls load_im(0x4C),
which loads IMNBG.BIN entry 76 (earth, moon, lightning, with the logo painted in), and
title_base_draw / imnbg_draw show it. IMNBG.BIN starts with a table of sector offsets; each
entry is a 1 KB RGBA palette (GS CSM1 order, alpha 0x80) and 768x512 8-bit pixels stored linear,
of which the top-left 640x448 is shown.

The painted logo is TITLPACK texture 3's combined logo at 1:1 (offset in textures/titl.json),
with a heavier dark outline. The katakana is cut out where texture 3 differs from the standalone
IMPACT; under it the IMPACT art is restored from that standalone copy and the rest (earth,
space, lightning) is inpainted. Then the same English wordmark as titl.py is drawn with an
extra dark outline, and the changed pixels are mapped back onto the entry's own palette.

  titlbg.py build IMNBG.BIN TITLPACK.BIN OUT.bin   (both inputs pristine)
  titlbg.py preview OUTDIR
"""
import json
import os
import struct
import sys

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titl

W, H, SHOW_W, SHOW_H = 768, 512, 640, 448


def entry_offset(data, n):
    return struct.unpack_from("<I", data, n * 4)[0] * 2048


def load_entry(data, o):
    pal = np.array([tuple(data[o + titl.csm(i) * 4:o + titl.csm(i) * 4 + 4]) for i in range(256)],
                   dtype=np.uint8)
    idx = np.frombuffer(data, np.uint8, W * H, o + 0x400).reshape(H, W).copy()
    return pal, idx


def compose(imnbg, titlpack, spec):
    bg_spec = spec["backdrop"]
    o = entry_offset(imnbg, bg_spec["entry"])
    pal, idx = load_entry(imnbg, o)
    rgb = pal[idx][..., :3].copy()
    dx, dy = bg_spec["offset"]                   # texture-3 pixel (x, y) -> backdrop (x+dx, y+dy)
    item = next(it for it in spec["logos"] if it["texture"] == 3 and "impact_at" in it)
    x0, y0, x1, y1 = item["box"]
    ix, iy = item["impact_at"]

    tex = titl.to_rgba(titlpack, 3)
    sx0, sy0, sx1, sy1 = spec["impact_alone"]
    under = Image.new("RGBA", tex.size, (0, 0, 0, 0))
    under.paste(tex.crop((sx0, sy0, sx1, sy1)), (ix, iy))
    a = np.asarray(tex).astype(int)
    b = np.asarray(under).astype(int)
    diff = Image.fromarray((np.abs(a - b).sum(2) > item.get("threshold", 60)).astype(np.uint8) * 255)
    box = Image.new("L", tex.size, 0)
    bp = bg_spec["box_pad"]                      # the painted wordmark's outline reaches past the box
    ImageDraw.Draw(box).rectangle((x0 - bp, y0 - bp, x1 - 1 + bp, y1 - 1 + bp), fill=255)
    cut = ImageChops.multiply(diff.filter(ImageFilter.MaxFilter(bg_spec["cut_grow"])), box)

    # move texture-space layers into backdrop space
    def place(im):
        out = Image.new(im.mode, (W, H), 0 if im.mode == "L" else (0, 0, 0, 0))
        out.paste(im, (dx, dy))
        return out
    cut = np.asarray(place(cut)) > 0
    under = np.asarray(place(under))
    impact = cut & (under[..., 3] > 200)
    # dark outline pixels just outside the cut belong to the painted wordmark too
    luma = rgb.astype(int) @ np.array([3, 6, 1]) // 10
    band = cv2.dilate(cut.astype(np.uint8), np.ones((bg_spec["dark_band"],) * 2, np.uint8)) > 0
    rest = (cut | (band & (luma < bg_spec["dark_luma"]))) & ~impact & (under[..., 3] == 0)
    rest |= cut & ~impact

    out = rgb.copy()
    out[impact] = under[..., :3][impact]          # inpaint from the restored IMPACT, not the katakana
    filled = cv2.inpaint(np.ascontiguousarray(out[..., ::-1]), rest.astype(np.uint8) * 255,
                         bg_spec["inpaint_radius"], cv2.INPAINT_TELEA)[..., ::-1]
    out[rest] = filled[rest]

    # English wordmark, same lettering as the TITLPACK logos, plus the backdrop's dark outline
    mark = titl.wordmark((x1 - x0, y1 - y0), spec["text"], os.path.join(titl.FONTS, spec["font"]),
                         spec["shear"])
    pad = bg_spec["outline"] + 2
    canvas = Image.new("RGBA", (mark.width + 2 * pad, mark.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(mark, (pad, pad))
    edge = canvas.getchannel("A").point(lambda v: 255 if v > 40 else 0) \
        .filter(ImageFilter.MaxFilter(2 * bg_spec["outline"] + 1)).filter(ImageFilter.GaussianBlur(0.8))
    stroked = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    stroked.paste(tuple(bg_spec["outline_rgb"]) + (255,), (0, 0), edge)
    stroked.alpha_composite(canvas)
    img = Image.fromarray(out).convert("RGBA")
    img.alpha_composite(stroked, (x0 + dx - pad, y0 + dy - pad))
    return pal, idx, o, np.asarray(img.convert("RGB"))


def requantize(pal, idx, new):
    """Indices for `new`, keeping the palette: unchanged pixels keep their index."""
    old = pal[idx][..., :3]
    changed = np.any(old != new, axis=2)
    changed[SHOW_H:, :] = False
    changed[:, SHOW_W:] = False
    p = pal[:, :3].astype(np.int32)
    px = new[changed].astype(np.int32)
    # weighted nearest colour (green counts most), in chunks
    wts = np.array([3, 4, 2])
    best = np.empty(len(px), np.uint8)
    for i in range(0, len(px), 4096):
        d = (((px[i:i + 4096, None, :] - p[None, :, :]) ** 2) * wts).sum(2)
        best[i:i + 4096] = d.argmin(1)
    out = idx.copy()
    out[changed] = best
    return out, int(changed.sum())


def build(imnbg_path, titl_path, dst, preview=None):
    spec = json.load(open(titl.SPEC, encoding="utf-8"))
    data = bytearray(open(imnbg_path, "rb").read())
    titlpack = open(titl_path, "rb").read()
    pal, idx, o, new = compose(data, titlpack, spec)
    out, n = requantize(pal, idx, new)
    data[o + 0x400:o + 0x400 + W * H] = out.tobytes()
    if preview:
        Image.fromarray(pal[out][:SHOW_H, :SHOW_W, :3]).save(os.path.join(preview, "titlbg.png"))
        Image.fromarray(pal[idx][:SHOW_H, :SHOW_W, :3]).save(os.path.join(preview, "titlbg_jp.png"))
    if dst:
        open(dst, "wb").write(data)
    print(f"title backdrop: IMNBG entry {spec['backdrop']['entry']}, {n:,} pixels redrawn")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "build":
        build(a[1], a[2], a[3])
    elif a[0] == "preview":
        os.makedirs(a[1], exist_ok=True)
        disc = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc")
        build(os.path.join(disc, "MAP", "IMNBG.BIN"), os.path.join(disc, "BTL", "TITLPACK.BIN"),
              None, a[1])
