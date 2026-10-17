#!/usr/bin/env python3
"""Fill entries that need no translator: unit heights and weights (３４．６ｍ -> 34.6m).

  autofill_impact.py
"""
import json, os, sys, unicodedata
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(REPO, "worksheets", "COMMON", "COMMON_units.json")
ws = json.load(open(p, encoding="utf-8"))
n = 0
for s in ws["strings"]:
    if s.get("field") in ("height", "weight") and not s["keep"] and not s.get("en"):
        v = unicodedata.normalize("NFKC", s["jp"]).replace("メット", "m").replace(" ", "")
        if v.isascii():
            s["en"] = v
            n += 1
json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"autofill: {n} heights/weights")
