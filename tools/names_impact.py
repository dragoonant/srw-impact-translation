#!/usr/bin/env python3
"""SRW Impact name glossary: collect, prefill from our earlier canon, export for translators,
ingest, and apply.

  names_impact.py collect          glossary/impact_names.tsv from the worksheets (keeps filled rows)
  names_impact.py export DIR N     write the unfilled rows as N request files for translators
  names_impact.py ingest DIR       read DIR/*.out.json into impact_names.tsv
  names_impact.py apply            fill COMMON name fields and glossary/speakers.tsv from the TSV

Columns: category, jp, en, source, notes. Categories: pilot (full names), pilot_short, speaker,
unit, weapon. Canon (PLAN.md I1): Banpresto originals from our OGs / 2nd OG / Gaiden / MD
glossaries; licensed series from the official English SRW releases, then the show's official
English, then Akurasu, then a proposal.
"""
import csv
import glob
import json
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.join(REPO, "worksheets")
GL = os.path.join(REPO, "glossary")
TSV = os.path.join(GL, "impact_names.tsv")
COLS = ["category", "jp", "en", "source", "notes"]


def norm(s):
    return unicodedata.normalize("NFKC", s).replace("・", "").replace("＝", "=").replace("=", "").replace(" ", "")


def canon():
    """jp (normalised) -> en from the earlier projects' name lists."""
    m = {}
    files = ["md_fixed.tsv", "md_names.tsv", "signoff.tsv", "pilots.tsv", "units.tsv", "attacks.tsv",
             "skills.tsv", "spirits.tsv", "factions.tsv", "parts.tsv"]
    for fn in reversed(files):           # earlier files win
        p = os.path.join(GL, fn)
        if not os.path.exists(p):
            continue
        rows = list(csv.reader(open(p, encoding="utf-8"), delimiter="\t"))
        if not rows:
            continue
        head = rows[0]
        try:
            jcol, ecol = head.index("jp"), head.index("en")
        except ValueError:
            jcol, ecol = 1, 2
        for r in rows[1:]:
            if len(r) > max(jcol, ecol) and r[jcol] and r[ecol]:
                m[norm(r[jcol])] = r[ecol]
    return m


def load():
    if not os.path.exists(TSV):
        return []
    return list(csv.DictReader(open(TSV, encoding="utf-8"), delimiter="\t"))


def save(rows):
    w = csv.DictWriter(open(TSV, "w", encoding="utf-8", newline=""), COLS, delimiter="\t")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in COLS})


def collect():
    have = {(r["category"], r["jp"]): r for r in load()}
    found = {}

    def add(cat, jp):
        if jp and not re.fullmatch(r"[－ー\-\s　]*", jp):
            found.setdefault((cat, jp), 0)
            found[(cat, jp)] += 1

    for name, part_fields in (("units", {"name": "unit"}), ("pilots", {"name": "pilot", "short": "pilot_short",
                                                                      "name2": "pilot"}),
                              ("weapons", {"name": "weapon"})):
        ws = json.load(open(os.path.join(WS, "COMMON", f"COMMON_{name}.json"), encoding="utf-8"))
        for s in ws["strings"]:
            cat = part_fields.get(s.get("field"))
            if cat and not s["keep"]:
                add(cat, s["jp"])
    for p in glob.glob(os.path.join(WS, "LOGIC", "*.json")):
        for s in json.load(open(p, encoding="utf-8"))["strings"]:
            if s["kind"] in ("dialogue", "thought", "page") and "@" in s["jp"]:
                add("speaker", s["jp"].split("@", 1)[0])
    cn = canon()
    rows = []
    pre = 0
    for (cat, jp), n in sorted(found.items()):
        r = have.get((cat, jp)) or {"category": cat, "jp": jp, "en": "", "source": "", "notes": ""}
        if not r["en"] and norm(jp) in cn:
            r["en"], r["source"] = cn[norm(jp)], "og-canon"
            pre += 1
        r["notes"] = r.get("notes") or f"uses={n}"
        rows.append(r)
    save(rows)
    filled = sum(1 for r in rows if r["en"])
    print(f"{len(rows)} names ({filled} filled, {pre} newly from OG canon) -> {TSV}")


def export(out, n):
    rows = [r for r in load() if not r["en"]]
    os.makedirs(out, exist_ok=True)
    # keep a pilot's full name, short name and speaker form in the same file
    rows.sort(key=lambda r: ({"pilot": 0, "pilot_short": 0, "speaker": 0, "unit": 1, "weapon": 2}[r["category"]], r["jp"]))
    per = -(-len(rows) // n)
    for k in range(n):
        part = rows[k * per:(k + 1) * per]
        if not part:
            continue
        items = [{"id": f"{r['category']}|{r['jp']}", "category": r["category"], "jp": r["jp"],
                  "max_bytes": {"unit": 33, "pilot": 35, "pilot_short": 19, "speaker": 40, "weapon": 35}[r["category"]]}
                 for r in part]
        json.dump({"items": items}, open(os.path.join(out, f"n{k + 1:02d}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{len(rows)} unfilled names -> {n} files in {out}")


def ingest(src):
    rows = load()
    idx = {f"{r['category']}|{r['jp']}": r for r in rows}
    got = 0
    for p in sorted(glob.glob(os.path.join(src, "n*.out.json"))):
        for t in json.load(open(p, encoding="utf-8"))["translations"]:
            r = idx.get(t["id"])
            if r and t.get("en"):
                r["en"] = t["en"].strip()
                r["source"] = t.get("source", "proposal")
                if t.get("note"):
                    r["notes"] = (r["notes"] + "; " + t["note"]).strip("; ")
                got += 1
    save(rows)
    print(f"ingested {got} names")


def apply():
    rows = load()
    by = {(r["category"], r["jp"]): r["en"] for r in rows if r["en"]}
    total = 0
    for name, cats in (("units", {"name": "unit"}), ("pilots", {"name": "pilot", "short": "pilot_short", "name2": "pilot"}),
                       ("weapons", {"name": "weapon"})):
        p = os.path.join(WS, "COMMON", f"COMMON_{name}.json")
        ws = json.load(open(p, encoding="utf-8"))
        for s in ws["strings"]:
            cat = cats.get(s.get("field"))
            if cat and (cat, s["jp"]) in by and not s["keep"]:
                s["en"] = by[(cat, s["jp"])]
                total += 1
        json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sp = [(jp, en) for (cat, jp), en in sorted(by.items()) if cat == "speaker"]
    with open(os.path.join(GL, "speakers.tsv"), "w", encoding="utf-8") as f:
        f.write("# jp\ten (generated by names_impact.py apply from impact_names.tsv)\n")
        for jp, en in sp:
            f.write(f"{jp}\t{en}\n")
    print(f"applied {total} name fields; {len(sp)} speakers")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"collect": lambda: collect(), "export": lambda: export(a[1], int(a[2])), "ingest": lambda: ingest(a[1]),
     "apply": lambda: apply()}[a[0]]()
