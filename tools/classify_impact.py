#!/usr/bin/env python3
"""Set `kind` and `keep` on every SRW Impact worksheet entry.

  classify_impact.py [WSDIR]      (default: worksheets/)

Kinds
  LOGIC   dialogue (Speaker@「...」), thought (Speaker@（...）), page (one page of a longer
          speech: opens, continues or closes a 「」 across strings), system (no speaker: skill
          and level-up messages, objectives)
  BMC     quote
  COMMON  unit_name, height, weight, pilot_name, pilot_short, pilot_name2, voice_actor,
          weapon_name, ui (message bank), desc (database page)
  STRTAB  ui (ELF), terrain (TEST.MTI)
Keep (never translated)
  - empty strings, developer placeholders (ＩＭキャラです！, 開発中, 未定義, ＮＵＬＬ, ダミー)
  - ELF strings inside executable sections (.text, .vutext, VU overlays): code bytes that decode
    as Shift-JIS; writing them crashes the game (Moon Dwellers, knowledge base Part D #49)
Re-run after any extractor change.
"""
import glob
import json
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PLACEHOLDER = re.compile(r"^(ＩＭキャラです！|ＮＵＬＬ|未定義|－+|ダミー|（ダミー）|[^@]*@「開発中」)$")
DISC = os.path.join(os.path.expanduser("~"), "srwimpact-work", "pristine", "disc")


def exec_ranges(elf_path):
    e = open(elf_path, "rb").read()
    shoff = struct.unpack_from("<I", e, 0x20)[0]
    entsize, num, _ = struct.unpack_from("<3H", e, 0x2E)
    out = []
    for i in range(num):
        _, typ, flags, _, off, size = struct.unpack_from("<6I", e, shoff + i * entsize)
        if flags & 4 and size:
            out.append((off, off + size))
    return out


SPEAKER = r"^[^@「」（）『』　]{1,25}@"


def logic_kind(t):
    if re.match(SPEAKER + r"[「『].*[」』]$", t, re.S):
        return "dialogue"
    if re.match(SPEAKER + r"（.*）$", t, re.S):
        return "thought"
    # one page of a longer speech or thought: opens, continues or closes across strings
    if re.match(SPEAKER + r"[「『（　]", t) or (re.match(SPEAKER, t) and re.search(r"[」』）]$", t)):
        return "page"
    return "system"


COMMON_KIND = {("units", "name"): "unit_name", ("units", "height"): "height", ("units", "weight"): "weight",
               ("pilots", "name"): "pilot_name", ("pilots", "short"): "pilot_short",
               ("pilots", "name2"): "pilot_name2", ("pilots", "voice"): "voice_actor",
               ("weapons", "name"): "weapon_name"}


def classify(wsdir):
    ex = exec_ranges(os.path.join(DISC, "SLPS_251.03"))
    totals = {}
    for path in sorted(glob.glob(os.path.join(wsdir, "*", "*.json"))):
        ws = json.load(open(path, encoding="utf-8"))
        fmt = ws["format"]
        for s in ws["strings"]:
            t = s["jp"]
            if fmt == "LOGIC":
                kind = logic_kind(t)
            elif fmt == "BMC":
                kind = "quote"
            elif fmt == "COMMON":
                part = ws["part"]
                kind = COMMON_KIND.get((part, s.get("field")), {"msg": "ui", "desc": "desc"}.get(part, part))
            elif fmt == "STRTAB":
                kind = "terrain" if ws["file"].endswith("TEST.MTI") else "ui"
            else:
                kind = s.get("kind") or "text"
            # "raw" marks bytes that do not round-trip through cp932, except in STRTAB worksheets,
            # which store every entry's original bytes there
            keep = not t.strip() or bool(PLACEHOLDER.search(t)) or ("raw" in s and fmt != "STRTAB")
            if fmt == "STRTAB" and ws["file"].endswith("SLPS_251.03"):
                if any(a <= s["off"] < b for a, b in ex):
                    keep, kind = True, "code"
            s["kind"], s["keep"] = kind, keep
            if keep and s.get("en"):
                print(f"  note: {os.path.basename(path)} #{s['id']} is keep but has English")
            k = (fmt, kind, keep)
            totals[k] = totals.get(k, 0) + 1
        json.dump(ws, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for (fmt, kind, keep), n in sorted(totals.items()):
        print(f"  {fmt:7} {kind:12} {'keep' if keep else '    '} {n:7,}")


if __name__ == "__main__":
    classify(sys.argv[1] if len(sys.argv) > 1 else "worksheets")
