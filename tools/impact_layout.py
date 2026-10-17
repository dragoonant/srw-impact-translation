"""Pixel widths and word wrapping for SRW Impact English, using the renderer's own table.

Widths are canvas pixels (the unit font_decode_inside adds to a row): English characters use
the advance table in vwf_impact.py; Japanese characters 18 (JIS rows 1-5) or 26 (kanji).

Story pages: speaker row, then at most 2 body rows of ROW_PX each. ROW_PX = 400, the 99.5th
percentile of Japanese body rows (a row next to a face portrait shows about 443 px).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import impact_text
import vwf_impact

ROW_PX = 400
SPEAKER_PX = 400
_ADV = None


def _adv():
    global _ADV
    if _ADV is None:
        _ADV = {b: adv for b, ch, idx, lb, adv in vwf_impact.table()[1]}
    return _ADV


def width(en):
    """Pixel width of one row of English (tokens such as {cY} draw nothing)."""
    adv = _adv()
    b = impact_text.to_game(en)
    w, i = 0, 0
    while i < len(b):
        if b[i] == ord("c") and i + 1 < len(b) and 0x42 <= b[i + 1] <= 0x59:
            i += 2
            continue
        if b[i] in (0x25, 0x26, 0x24, 0x23) and i + 1 < len(b):
            w += 2 * 18                                  # a number: assume 2 digits
            i += 2
            continue
        if b[i] == ord("s") and i + 2 < len(b) and 0x30 <= b[i + 1] <= 0x39 and 0x30 <= b[i + 2] <= 0x39:
            w += int(b[i + 1:i + 3])                      # space code: NN blank columns (font_decode_SPACE)
            i += 3
            continue
        w += adv.get(b[i], 10)
        i += 1
    return w


def wrap(text, limit=ROW_PX):
    """Greedy word wrap into rows no wider than `limit`. Existing @ forces a break."""
    rows = []
    for para in text.split("@"):
        words = para.split(" ")
        cur = ""
        for wd in words:
            cand = wd if not cur else cur + " " + wd
            if width(cand) <= limit or not cur:
                cur = cand
            else:
                rows.append(cur)
                cur = wd
        rows.append(cur)
    return rows
