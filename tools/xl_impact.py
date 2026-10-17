#!/usr/bin/env python3
"""In-session translation for SRW Impact: export requests, check answers, ingest, prefill.

  xl_impact.py export OUTDIR [--chunk 80] [--only LOGIC,BMC,COMMON,STRTAB] [--files GLOB]
      One request file rNNNNN.json per chunk of untranslated, non-kept, not-yet-seen Japanese
      (identical Japanese of the same format is requested once). Writes OUTDIR/index.json.
  xl_impact.py check OUTDIR [rNNNNN ...]      validate answer files (prints problems)
  xl_impact.py ingest OUTDIR                  write valid answers into the worksheets
  xl_impact.py prefill                        copy English to identical untranslated Japanese
  xl_impact.py stats                          translated / remaining per format

Request item: id ("<worksheet>#<n>"), jp (engine codes shown as {cY} tokens), kind, speaker
(Japanese, English), page ("2/4" for one page of a longer speech), limits: for story and
battle text max_rows and row_px (English is word-wrapped by the build, so the translator writes
one paragraph); for in-place strings max_bytes; for labels max_px.
Answer file rNNNNN.out.json: {"translations":[{"id","en"}]}.
"""
import csv
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import impact_layout as L
import impact_text as T

WS = os.path.join(REPO, "worksheets")
NAMES = os.path.join(REPO, "glossary", "impact_names.tsv")
TERMS = os.path.join(REPO, "glossary", "impact_terms.tsv")
CODE_RE = re.compile(r"c[B-Y]|[%&$#][0-9]|s[0-9]{2}")
JP_RE = re.compile(r"[぀-ヿ㐀-鿿＀-￯「」『』（）]")


def jp_shown(jp):
    return CODE_RE.sub(lambda m: "{" + m.group() + "}", jp)


def ws_paths(only=None, files=None):
    out = []
    for p in sorted(glob.glob(os.path.join(WS, "*", "*.json"))):
        ws = json.load(open(p, encoding="utf-8"))
        if only and ws["format"] not in only:
            continue
        if files and not glob.fnmatch.fnmatch(os.path.basename(p), files):
            continue
        out.append((p, ws))
    return out


def load_glossary():
    g = {}
    for path in (NAMES, TERMS):
        if os.path.exists(path):
            for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"):
                # 2-character kana terms (ムチ, かま, エレ) match inside other words: skip them
                kana_only = all("぀" <= c <= "ヿ" for c in r["jp"])
                if r.get("en") and (len(r["jp"]) >= 3 or (len(r["jp"]) == 2 and not kana_only)):
                    g.setdefault(r["jp"], r["en"])
    return g


def speakers():
    m = {}
    if os.path.exists(NAMES):
        for r in csv.DictReader(open(NAMES, encoding="utf-8"), delimiter="\t"):
            if r["category"] == "speaker" and r["en"]:
                m[r["jp"]] = r["en"]
    return m


def limits(fmt, ws, s):
    kind = s["kind"]
    if fmt == "LOGIC":
        if kind in ("dialogue", "thought", "page"):
            return {"max_rows": 2, "row_px": L.ROW_PX}
        return {"max_rows": max(1, s["jp"].count("@") + 1), "row_px": L.ROW_PX}
    if fmt == "BMC":
        return {"max_rows": 2, "row_px": L.ROW_PX}
    if fmt == "COMMON":
        if ws["part"] in ("desc", "msg") and "@" in s["jp"]:
            return {"max_rows": s["jp"].count("@") + 1, "row_px": L.ROW_PX}
        if ws["part"] == "msg":
            jpw = jp_width(s["jp"])
            return {"max_px": max(160, int(jpw * 2.2)) if jpw <= 320 else max(L.ROW_PX, jpw)}
        return {"max_bytes": s.get("budget", 35)}
    if fmt == "STRTAB":
        return {"max_bytes": s["budget"]}
    return {}


def jp_width(jp):
    import impact_font as F
    w = 0
    for c in CODE_RE.sub("", jp):
        try:
            b = c.encode("cp932")
        except UnicodeEncodeError:
            w += 26
            continue
        w += 18 if len(b) == 1 or F.index_of(int.from_bytes(b, "big")) < 470 else 26
    return w


def page_info(strings):
    """For LOGIC: {index: "k/n"} for strings that are pages of one speech."""
    info, run = {}, []
    for k, s in enumerate(strings):
        if s["kind"] != "page":
            run = []
            continue
        body = s["jp"].split("@", 1)[1] if "@" in s["jp"] else s["jp"]
        if body.startswith("「") or not run:
            run = [k]
        else:
            run.append(k)
        if s["jp"].endswith("」"):
            for i, kk in enumerate(run):
                info[kk] = f"{i + 1}/{len(run)}"
            run = []
    return info


def cmd_export(out, chunk=80, only=None, files=None):
    os.makedirs(out, exist_ok=True)
    g = load_glossary()
    spk = speakers()
    seen = set()
    for p, ws in ws_paths():
        for s in ws["strings"]:
            if s.get("en"):
                seen.add((ws["format"], s["jp"]))
    reqs, cur, ctx = [], [], []
    for p, ws in ws_paths(only, files):
        fmt = ws["format"]
        name = os.path.basename(p)[:-5]
        pages = page_info(ws["strings"]) if fmt == "LOGIC" else {}
        ctx = []
        for k, s in enumerate(ws["strings"]):
            if fmt == "LOGIC":
                ctx.append(s["jp"])
                ctx = ctx[-8:]
            if s["keep"] or s.get("en") or not s["jp"].strip() or (fmt, s["jp"]) in seen:
                continue
            if fmt == "COMMON" and (ws["part"] in ("units", "weapons") or
                                    (ws["part"] == "pilots" and s.get("field") != "voice")):
                continue                     # names come from glossary/impact_names.tsv
            seen.add((fmt, s["jp"]))
            item = {"id": f"{name}#{s['id']}", "jp": jp_shown(s["jp"]), "kind": s["kind"], **limits(fmt, ws, s)}
            if fmt == "LOGIC" and "@" in s["jp"] and s["kind"] != "system":
                sj = s["jp"].split("@", 1)[0]
                item["speaker"] = [sj, spk.get(sj, "")]
            if k in pages:
                item["page"] = pages[k]
            if fmt == "BMC":
                item["pilot_id"] = ws["pilot"]
            if fmt == "COMMON":
                item["part"] = ws["part"]
            if fmt == "LOGIC":
                item["context_before"] = ctx[:-1][-4:]
            cur.append(item)
            if len(cur) >= chunk:
                reqs.append(cur)
                cur = []
        if cur and fmt != "LOGIC":
            pass
    if cur:
        reqs.append(cur)
    index = []
    for n, items in enumerate(reqs, 1):
        text = " ".join(i["jp"] for i in items)
        gl = {jp: en for jp, en in g.items() if jp in text}
        req = {"glossary": dict(sorted(gl.items(), key=lambda kv: -len(kv[0]))), "items": items}
        fn = f"r{n:05d}.json"
        json.dump(req, open(os.path.join(out, fn), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        index.append({"file": fn, "items": len(items), "first": items[0]["id"]})
    json.dump(index, open(os.path.join(out, "index.json"), "w"), indent=1)
    print(f"{sum(len(r) for r in reqs)} items in {len(reqs)} request files -> {out}")


def problems_for(item, en):
    pr = []
    if not en or not en.strip():
        return ["empty"]
    if JP_RE.search(en):
        pr.append("Japanese or full-width characters left")
    try:
        T.to_game(en)
    except ValueError as e:
        pr.append(str(e))
        return pr
    jc, ec = re.findall(r"\{[^}]+\}", item["jp"]), T.en_codes(en)
    if jc != ec:
        pr.append(f"codes {ec} must equal {jc}")
    if "<" in en or ">" in en:
        pr.append("no < or >")
    if "max_rows" in item and "@" in item["jp"] and en.count(" / ") == item["jp"].count("@") and en.count(" / "):
        # a choice menu: the build puts each option on its own row (build.compose_story)
        for opt in en.split(" / "):
            if L.width(opt.strip()) > item["row_px"]:
                pr.append(f"option wider than {item['row_px']} px: {opt[:30]}")
    elif "max_rows" in item:
        rows = L.wrap(en, item["row_px"])
        if len(rows) > item["max_rows"]:
            pr.append(f"{len(rows)} rows after wrapping at {item['row_px']} px (max {item['max_rows']}); "
                      f"{L.width(en)} px of text")
        for r in rows:
            if L.width(r) > item["row_px"]:
                pr.append(f"word too long for a row: {r[:30]}")
    if "max_bytes" in item:
        n = len(T.to_game(en))
        if n > item["max_bytes"]:
            pr.append(f"{n} bytes (max {item['max_bytes']})")
    if "max_px" in item:
        if "@" in en:
            pr.append("no @ in a label")
        if L.width(en) > item["max_px"]:
            pr.append(f"{L.width(en)} px (max {item['max_px']})")
    if item.get("kind") in ("dialogue", "page", "quote") and re.search(r"[「」]", en):
        pr.append("no 「」")
    return pr


def cmd_check(out, names=None, quiet=False):
    files = names or [os.path.basename(p)[:-5] for p in sorted(glob.glob(os.path.join(out, "r*.json")))
                      if not p.endswith(".out.json")]
    total = 0
    report = []
    for f in files:
        f = f.replace(".json", "")
        req = json.load(open(os.path.join(out, f + ".json"), encoding="utf-8"))
        ap = os.path.join(out, f + ".out.json")
        if not os.path.exists(ap):
            report.append(f"{f}: no answer file")
            total += 1
            continue
        try:
            ans = json.load(open(ap, encoding="utf-8"))["translations"]
        except Exception as e:
            report.append(f"{f}: bad JSON: {e}")
            total += 1
            continue
        got = {}
        for t in ans:
            if t["id"] in got:
                report.append(f"{f}: {t['id']} twice")
            got[t["id"]] = t.get("en", "")
        for it in req["items"]:
            if it["id"] not in got:
                report.append(f"{f}: {it['id']} missing")
                total += 1
                continue
            for pr in problems_for(it, got[it["id"]]):
                report.append(f"{f}: {it['id']}: {pr} | {got[it['id']][:70]}")
                total += 1
    if not quiet:
        for r in report:
            print(r)
    print(f"{len(files)} files, {total} problems")
    return total


def cmd_ingest(out):
    by_ws = {}
    n = bad = 0
    for ap in sorted(glob.glob(os.path.join(out, "r*.out.json"))):
        req = json.load(open(ap.replace(".out.json", ".json"), encoding="utf-8"))
        items = {i["id"]: i for i in req["items"]}
        try:
            ans = json.load(open(ap, encoding="utf-8"))["translations"]
        except Exception:
            continue
        for t in ans:
            it = items.get(t["id"])
            if not it:
                continue
            if problems_for(it, t.get("en", "")):
                bad += 1
                continue
            name, sid = t["id"].rsplit("#", 1)
            by_ws.setdefault(name, {})[int(sid)] = t["en"].strip()
            n += 1
    for p, ws in ws_paths():
        name = os.path.basename(p)[:-5]
        if name not in by_ws:
            continue
        for s in ws["strings"]:
            if s["id"] in by_ws[name]:
                s["en"] = by_ws[name][s["id"]]
        json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ingested {n} translations ({bad} skipped with problems)")
    cmd_prefill()


def cmd_prefill():
    tm = {}
    allws = ws_paths()
    for p, ws in allws:
        for s in ws["strings"]:
            if s.get("en") and not s["keep"]:
                tm.setdefault((ws["format"], s["jp"]), s["en"])
    n = 0
    for p, ws in allws:
        changed = False
        for s in ws["strings"]:
            if not s.get("en") and not s["keep"] and (ws["format"], s["jp"]) in tm:
                s["en"] = tm[(ws["format"], s["jp"])]
                n += 1
                changed = True
        if changed:
            json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"prefill: {n} duplicates filled")


def cmd_fitcheck(out_json=None):
    """Check every translated worksheet entry with the translators' limits."""
    fails = []
    for p, ws in ws_paths():
        name = os.path.basename(p)[:-5]
        for s in ws["strings"]:
            if not s.get("en") or s["keep"] or s.get("en_raw"):
                continue
            if ws["format"] == "COMMON" and ws["part"] in ("units", "weapons", "pilots") and s.get("field") != "voice":
                lim = {"max_bytes": s.get("budget", 35)}
            else:
                lim = limits(ws["format"], ws, s)
            item = {"id": f"{name}#{s['id']}", "jp": jp_shown(s["jp"]), "kind": s["kind"], **lim}
            for pr in problems_for(item, s["en"]):
                fails.append({"id": item["id"], "problem": pr, "en": s["en"]})
    for f in fails[:40]:
        print(f"{f['id']}: {f['problem']} | {f['en'][:60]}")
    print(f"fitcheck: {len(fails)} problems")
    if out_json:
        json.dump(fails, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return fails


def cmd_retry(out):
    """Clear English that fails fitcheck and export those entries again with the failure noted."""
    fails = cmd_fitcheck()
    ids = {}
    for f in fails:
        ids.setdefault(f["id"], []).append(f["problem"])
    prev = {}
    for p, ws in ws_paths():
        name = os.path.basename(p)[:-5]
        changed = False
        for s in ws["strings"]:
            k = f"{name}#{s['id']}"
            if k in ids:
                prev[(ws["format"], s["jp"])] = (s["en"], "; ".join(ids[k]))
                s["en"] = ""
                changed = True
        if changed:
            json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # clear identical Japanese too, so prefill does not bring the failing English back
    for p, ws in ws_paths():
        changed = False
        for s in ws["strings"]:
            if s.get("en") and (ws["format"], s["jp"]) in prev:
                s["en"] = ""
                changed = True
        if changed:
            json.dump(ws, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cmd_export(out, 60)
    for rp in glob.glob(os.path.join(out, "r*.json")):
        if rp.endswith(".out.json"):
            continue
        req = json.load(open(rp, encoding="utf-8"))
        for it in req["items"]:
            name, sid = it["id"].rsplit("#", 1)
        json.dump(req, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # attach the failed attempt and reason
    by_jp = {jp: v for (fmt, jp), v in prev.items()}
    for rp in glob.glob(os.path.join(out, "r*.json")):
        if rp.endswith(".out.json"):
            continue
        req = json.load(open(rp, encoding="utf-8"))
        for it in req["items"]:
            raw = CODE_RE.sub(lambda m: m.group(), it["jp"].replace("{", "").replace("}", ""))
            for jp, (en, why) in by_jp.items():
                if jp_shown(jp) == it["jp"]:
                    it["previous_attempt"] = en
                    it["problem"] = why
                    break
        json.dump(req, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cmd_stats():
    from collections import Counter
    done, todo = Counter(), Counter()
    for p, ws in ws_paths():
        k = ws["format"] + ("/" + ws["part"] if "part" in ws else "")
        for s in ws["strings"]:
            if s["keep"] or not s["jp"].strip():
                continue
            (done if s.get("en") else todo)[k] += 1
    for k in sorted(set(done) | set(todo)):
        print(f"{k:16} {done[k]:7,} done {todo[k]:7,} to do")
    print(f"{'total':16} {sum(done.values()):7,} done {sum(todo.values()):7,} to do")


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if a[0] == "export":
        only = opt("--only")
        cmd_export(a[1], int(opt("--chunk", 80)), only.split(",") if only else None, opt("--files"))
    elif a[0] == "check":
        cmd_check(a[1], [x for x in a[2:] if not x.startswith("-")] or None)
    elif a[0] == "ingest":
        cmd_ingest(a[1])
    elif a[0] == "prefill":
        cmd_prefill()
    elif a[0] == "stats":
        cmd_stats()
    elif a[0] == "fitcheck":
        sys.exit(1 if cmd_fitcheck(opt("--json")) else 0)
    elif a[0] == "retry":
        cmd_retry(a[1])
