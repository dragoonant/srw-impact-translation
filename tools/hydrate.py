#!/usr/bin/env python3
"""Public worksheets carry English only; the Japanese comes from the player's own disc.

  hydrate.py strip SRC_DIR OUT_DIR   English-only copies of every worksheet (drops "jp"/"raw")
  hydrate.py fill DISC [WORKSHEET_DIR]
                                     put the Japanese back: extract every worksheet from the
                                     extracted disc folder DISC (iso_tool.py extract) with the
                                     format tools, then copy "jp"/"raw" across by string id
  hydrate.py check [WORKSHEET_DIR]   report worksheets that still lack their Japanese
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SECRET = ("jp", "raw")


def load(p):
    return json.load(open(p, encoding="utf-8"))


def save(p, ws):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ws, f, ensure_ascii=False, indent=1)


def strip(src, out):
    n = 0
    for p in glob.glob(os.path.join(src, "**", "*.json"), recursive=True):
        ws = load(p)
        for e in ws.get("strings", []):
            for k in SECRET:
                e.pop(k, None)
        dst = os.path.join(out, os.path.relpath(p, src))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        save(dst, ws)
        n += 1
    return n


def extract_all(disc, out):
    for tool, sub in (("logic.py", "LOGIC"), ("bmc.py", "BMC"), ("common.py", "COMMON")):
        subprocess.run([sys.executable, "-I", os.path.join(HERE, tool), "extract", disc, os.path.join(out, sub)],
                       check=True, capture_output=True)
    os.makedirs(os.path.join(out, "STRTAB"), exist_ok=True)
    for rel in ("SLPS_251.03", os.path.join("MAP", "TEST.MTI")):
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "strtab.py"), "extract", os.path.join(disc, rel),
                        os.path.join(out, "STRTAB", os.path.basename(rel) + ".json")], check=True, capture_output=True)


def fill(disc, wsdir):
    with tempfile.TemporaryDirectory() as t:
        extract_all(disc, t)
        done = bad = 0
        for p in glob.glob(os.path.join(wsdir, "**", "*.json"), recursive=True):
            src = os.path.join(t, os.path.relpath(p, wsdir))
            if not os.path.exists(src):
                print("  no source for", os.path.relpath(p, wsdir))
                bad += 1
                continue
            ws, ref = load(p), {e["id"]: e for e in load(src)["strings"]}
            for e in ws["strings"]:
                r = ref.get(e["id"])
                if r is None:
                    bad += 1
                    continue
                for k in SECRET:
                    if k in r:
                        e[k] = r[k]
            save(p, ws)
            done += 1
    print(f"filled {done} worksheets, {bad} mismatches")
    return bad


def check(wsdir):
    missing = [p for p in glob.glob(os.path.join(wsdir, "**", "*.json"), recursive=True)
               if any("jp" not in e for e in load(p)["strings"])]
    print(f"{len(missing)} worksheets lack Japanese")
    return missing


if __name__ == "__main__":
    a = sys.argv[1:]
    ws = os.path.join(REPO, "worksheets")
    if a[0] == "strip":
        print(strip(a[1], a[2]), "worksheets stripped")
    elif a[0] == "fill":
        sys.exit(1 if fill(a[1], a[2] if len(a) > 2 else ws) else 0)
    elif a[0] == "check":
        check(a[1] if len(a) > 1 else ws)
