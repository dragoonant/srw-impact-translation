#!/usr/bin/env python3
"""Build the English SRW Impact disc image from the worksheets.

  build.py [--iso OUT.iso] [--no-iso] [--only logic,bmc,common,strtab,vwf,font]

Steps (each reads a file from the output folder if an earlier step wrote it):
  stage   copy worksheets, composing story/battle English into the game's layout
          (speaker row + word-wrapped body rows, see impact_layout.py)
  logic   MAP/LOGIC.BIN + its directory in the ELF and COMMON.BIN
  bmc     BTL/BMCPACK.BIN + its directory in COMMON.BIN
  common  COMMON.BIN tables, message bank, descriptions
  strtab  in-place strings in the ELF and MAP/TEST.MTI
  vwf     proportional 1-byte English renderer patch (ELF)
  font    composed umlaut glyphs (COMMON.BIN)
  stagetit English stage title cards (MAP/STAGETIT.BIN, textures/stagetit.json)
  roll    English opening/ending crawls and part title cards (BTL/ROLLPACK.BIN, textures/roll.json;
          also a 4-byte ELF patch so part 3 gets its own title cell)
  csl     English battle console atlas: badges, labels, series banners (BTL/CSL_PACK.BIN, textures/csl.json)
  titl    English title wordmark (BTL/TITLPACK.BIN, textures/titl.json)
  sroll   English staff credits (BTL/SROLPACK.BIN, textures/sroll.json)
  iso     fresh copy of the pristine ISO with every changed file written in (files that grew
          move into DUMMY's space; the game opens files by name)
Work folder: ~/srwimpact-work (pristine/disc, build/files, build/stage).
"""
import json
import re
import os
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import impact_layout as L
import impact_text
import iso_tool
import strtab
import vwf_impact
import impact_font

W = os.path.join(os.path.expanduser("~"), "srwimpact-work")
DISC = os.path.join(W, "pristine", "disc")
ISO_IN = os.path.join(REPO, "Super Robot Taisen Impact [Limited Edition] [J].iso")
OUT = os.path.join(W, "build", "files")
STAGE = os.path.join(W, "build", "stage")
WS = os.path.join(REPO, "worksheets")
SPEAKERS = os.path.join(REPO, "glossary", "speakers.tsv")

BATTLE_PX = 400
MSG_PX = 400
DESC_PX = 400


def load_speakers():
    m = {}
    if os.path.exists(SPEAKERS):
        for line in open(SPEAKERS, encoding="utf-8"):
            if line.startswith("#") or "\t" not in line:
                continue
            jp, en = line.rstrip("\n").split("\t")[:2]
            if en:
                m[jp] = en
    return m


def compose_story(s, speakers, problems, where):
    """Worksheet English (body only) -> the string the game shows."""
    jp, en = s["jp"], s["en"].strip()
    if s.get("en_raw") or not en or s.get("keep"):
        return None
    body = en
    if s["kind"] in ("dialogue", "thought", "page"):
        spk_jp = jp.split("@", 1)[0]
        spk = speakers.get(spk_jp)
        if spk is None:
            problems.append(f"{where}: no English speaker for {spk_jp}")
            spk = spk_jp
        rows = L.wrap(body, L.ROW_PX)
        if len(rows) > 2:
            problems.append(f"{where}: {len(rows)} rows: {body[:60]}")
        return spk + "@" + "@".join(rows)
    # choice menus: the Japanese separates options with @; translators write "A / B"
    if "@" in jp and body.count(" / ") == jp.count("@"):
        return "@".join(part.strip() for part in body.split(" / "))
    # numbered win/loss conditions: each number starts a row ("1. ...@2. ...")
    if re.match(r"\s*1\.", body) and re.search(r"\s[2-9]\.\s", body):
        body = re.sub(r"\s+([2-9]\.\s)", r"@\1", body)
    rows = L.wrap(body, L.ROW_PX)
    return "@".join(rows)


def stage():
    shutil.rmtree(STAGE, ignore_errors=True)
    speakers = load_speakers()
    problems = []
    for sub in os.listdir(WS):
        os.makedirs(os.path.join(STAGE, sub), exist_ok=True)
        for fn in os.listdir(os.path.join(WS, sub)):
            ws = json.load(open(os.path.join(WS, sub, fn), encoding="utf-8"))
            for s in ws["strings"]:
                where = f"{fn}#{s['id']}"
                if ws["format"] == "LOGIC":
                    out = compose_story(s, speakers, problems, where)
                    if out is not None:
                        s["en"] = out
                elif ws["format"] == "BMC" and s.get("en") and not s.get("keep") and "@" not in s["en"]:
                    rows = L.wrap(s["en"], BATTLE_PX)
                    s["en"] = "@".join(rows)
                elif ws["format"] == "COMMON" and ws["part"] in ("msg", "desc") and s.get("en") \
                        and not s.get("keep") and "@" not in s["en"] and "@" in s["jp"]:
                    s["en"] = "@".join(L.wrap(s["en"], DESC_PX if ws["part"] == "desc" else MSG_PX))
            json.dump(ws, open(os.path.join(STAGE, sub, fn), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"stage: {len(problems)} problems")
    for p in problems[:20]:
        print("  ", p)
    return problems


def run(tool, *args):
    r = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, tool), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr)
        raise SystemExit(f"{tool} failed")


def cur(rel):
    p = os.path.join(OUT, rel)
    return open(p if os.path.exists(p) else os.path.join(DISC, rel), "rb").read()


def step_strtab():
    for rel in ("SLPS_251.03", os.path.join("MAP", "TEST.MTI")):
        ws_path = os.path.join(STAGE, "STRTAB", os.path.basename(rel) + ".json")
        ws = json.load(open(ws_path, encoding="utf-8"))
        data, over = strtab.build(cur(rel), ws, lambda en, budget=None: impact_text.to_game(en))
        os.makedirs(os.path.dirname(os.path.join(OUT, rel)) or OUT, exist_ok=True)
        open(os.path.join(OUT, rel), "wb").write(data)
        print(f"strtab {rel}: {len(over)} over budget")
        for o in over[:10]:
            print("   over:", o)


def step_vwf():
    rel = "SLPS_251.03"
    data = vwf_impact.patch_elf(cur(rel))
    open(os.path.join(OUT, rel), "wb").write(data)
    print("vwf: renderer patched")


def step_font():
    rel = os.path.join("MAP", "COMMON.BIN")
    buf = bytearray(cur(rel))
    impact_font.compose(buf)
    open(os.path.join(OUT, rel), "wb").write(buf)
    print("font: composed glyphs written")


def step_stagetit():
    rel = os.path.join("MAP", "STAGETIT.BIN")
    import stagetit
    stagetit.build(os.path.join(DISC, rel), os.path.join(OUT, rel))


def step_roll():
    rel = os.path.join("BTL", "ROLLPACK.BIN")
    import roll
    roll.build(os.path.join(DISC, rel), os.path.join(OUT, rel))
    elf = roll.patch_elf(cur("SLPS_251.03"))
    open(os.path.join(OUT, "SLPS_251.03"), "wb").write(elf)
    print("roll: part 3 title cell patched")


def step_csl():
    rel = os.path.join("BTL", "CSL_PACK.BIN")
    import csl
    csl.build(os.path.join(DISC, rel), os.path.join(OUT, rel))


def step_titl():
    rel = os.path.join("BTL", "TITLPACK.BIN")
    import titl
    titl.build(os.path.join(DISC, rel), os.path.join(OUT, rel))


def step_sroll():
    rel = os.path.join("BTL", "SROLPACK.BIN")
    import sroll
    sroll.build(os.path.join(DISC, rel), os.path.join(OUT, rel))


def step_iso(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print("iso: copying the pristine image ...")
    shutil.copyfile(ISO_IN, path)
    changed = []
    for root, _, files in os.walk(OUT):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, OUT).replace("\\", "/")
            data = open(full, "rb").read()
            if data != open(os.path.join(DISC, rel), "rb").read():
                lba = iso_tool.write_data(path, rel, data)
                changed.append((rel, len(data), lba))
    for c in changed:
        print(f"   {c[0]}: {c[1]:,} bytes at LBA {c[2]}")
    print("iso:", path)


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1].split(",") if "--only" in a else None
    iso = a[a.index("--iso") + 1] if "--iso" in a else os.path.join(W, "build", "impact_en.iso")
    want = lambda s: only is None or s in only
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    stage()
    if want("logic"):
        run("logic.py", "build", DISC, os.path.join(STAGE, "LOGIC"), OUT)
    if want("bmc"):
        run("bmc.py", "build", DISC, os.path.join(STAGE, "BMC"), OUT)
    if want("common"):
        run("common.py", "build", DISC, os.path.join(STAGE, "COMMON"), OUT)
    if want("strtab"):
        step_strtab()
    if want("vwf"):
        step_vwf()
    if want("font"):
        step_font()
    if want("stagetit"):
        step_stagetit()
    if want("roll"):
        os.makedirs(os.path.join(OUT, "BTL"), exist_ok=True)
        step_roll()
    if want("csl"):
        os.makedirs(os.path.join(OUT, "BTL"), exist_ok=True)
        step_csl()
    if want("titl"):
        os.makedirs(os.path.join(OUT, "BTL"), exist_ok=True)
        step_titl()
    if want("sroll") and os.path.exists(os.path.join(REPO, "textures", "sroll.json")):
        os.makedirs(os.path.join(OUT, "BTL"), exist_ok=True)
        step_sroll()
    if "--no-iso" not in a:
        step_iso(iso)


if __name__ == "__main__":
    main()
