#!/usr/bin/env python3
"""Unify spellings and terms that parallel translators rendered differently.

  consistency_impact.py [--dry-run]

Each rule: (Japanese trigger or None, regex on the English, replacement). With a trigger, the
rule only touches entries whose Japanese contains it (so "Lieutenant" is changed to "Captain"
only where the Japanese says 大尉). Runs over story, battle, message and description English.
Afterwards run `xl_impact.py fitcheck` (a longer replacement can overflow a row).
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES = [
    # ranks: series rule (choices.md 19)
    ("少尉", r"\bEnsign\b", "Lieutenant"),
    ("少佐", r"\bLieutenant Commander\b", "Major"),
    ("大尉", r"\bLieutenant (Quattro|Bajeena|Burning|Amuro|Kelly)\b", r"Captain \1"),
    ("中佐", r"\bCommander (Cima)\b", r"Lieutenant Colonel \1"),
    # settled terms (glossary/impact_terms.tsv)
    (None, r"\bGandler\b", "Gyandlar"),
    (None, r"\bPersein\b", "Person-Lichkeit"),
    (None, r"\bPerzein Lichkeit\b", "Person-Lichkeit"),
    (None, r"\bKilhasium\b", "Kirhasium"),
    (None, r"\b(Ladorio|Radrio)\b", "Radorio"),
    (None, r"\bChronos\b", "Cronos"),
    (None, r"\bMirene\b", "Mylene"),
    (None, r"\bYoma Empire\b", "Demon Empire"),
    (None, r"\bKimen Castle\b", "Demon Mask Castle"),
    (None, r"\bCelestial True Sword\b", "Tenku Shinken"),
    (None, r"\bMechasaurus\b", "Mechasaur"),
    (None, r"\bMechasauruses\b", "Mechasaurs"),
    (None, r"\bWarrior Beast", "Battle Beast"),
    (None, r"\bInes\b", "Inez"),
    (None, r"\bKuroshishi\b", "Kurojishi"),
    (None, r"\bHoraiou\b", "Houraiou"),
    (None, r"\bDarkron\b", "Darklon"),
    (None, r"\bHi-Libido\b", "Hyper Libido"),
    (None, r"\bYujin Squadron\b", "Superior Human Corps"),
    (None, r"\bMars Development Base\b", "Mars Frontier Base"),
    ("巨烈獣", r"\bGiant Beasts?\b", lambda m: "Kyoretsu Beast" + ("s" if m.group(0).endswith("s") else "")),
    (None, r"\bZedan's Gate\b", "the Gate of Zedan"),
    (None, r"\bCooplander\b", "Copelander"),
    (None, r"\bKonpeitou\b", "Konpeito"),
    ("龍の命", r"\bRyu's life\b", "the dragon's life"),
]


def main(dry):
    changed, per_rule = 0, {}
    for p in sorted(glob.glob(os.path.join(REPO, "worksheets", "*", "*.json"))):
        ws = json.load(open(p, encoding="utf-8"))
        if ws["format"] not in ("LOGIC", "BMC", "COMMON"):
            continue
        if ws["format"] == "COMMON" and ws["part"] not in ("msg", "desc"):
            continue
        dirty = False
        for s in ws["strings"]:
            en = s.get("en")
            if not en or s["keep"]:
                continue
            new = en
            for k, (trig, rx, rep) in enumerate(RULES):
                if trig and trig not in s["jp"]:
                    continue
                new2 = re.sub(rx, rep, new)
                if new2 != new:
                    per_rule[rx] = per_rule.get(rx, 0) + 1
                    new = new2
            new = new.replace("the the ", "the ")
            if new != en:
                changed += 1
                if not dry:
                    s["en"] = new
                    dirty = True
        if dirty:
            json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for rx, n in sorted(per_rule.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5}  {rx}")
    print(f"{'would change' if dry else 'changed'} {changed} entries")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
