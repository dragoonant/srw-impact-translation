#!/usr/bin/env python3
"""MAP/COMMON.BIN text: SRW Impact's data tables, system messages and database descriptions.

COMMON.BIN appears to be loaded whole, with the code reaching each table at a fixed place, so
no table moves: record fields are edited in place, and the two banks are rebuilt inside the
region they already own.

  Record tables (fixed-width text fields, in place; budget = field width - 1, or less where the
  record's own data starts earlier):
    units    0x16E900-0x1A7600, 0x100-byte records: name +0x00 (34), height +0xD0 (18),
             weight +0xE2 (18)
    pilots   0x1AEA00-0x1DF000, 0x200-byte records: full name +0x00 (36), short name +0x24 (20),
             full name again +0xB8 (64), voice actor +0xF8 (64)
    weapons  0x1EE800-0x22E000, 0x80-byte records: name +0x00 (36)

  Message bank at 0x23E800, region 0x10000 bytes: u16 hdr[36] = section offsets from the bank
  (hdr[0] = 72). Section = u16 offsets from the BANK to its strings (several entries may share a
  string), then the strings (NUL-terminated), then a zero byte to an even offset. Rebuilt with
  strings in their original order; must stay within 65,536 bytes.

  Description bank at 0x2E7400: u32 off[1024] from the bank (duplicates share a record), records
  from +0x1000: u16 n, u16 page_off[n] (from the record), n NUL-terminated pages, zero byte to an
  even offset. Rebuilt in original order; may grow into the zeros up to the next data.

  Other strings (strtab-style in-place slots) outside these regions are listed as "misc".

Usage:
  common.py extract DISC WSDIR        WSDIR/COMMON_{units,pilots,weapons,msg,desc}.json
  common.py build   DISC WSDIR OUTDIR OUTDIR/MAP/COMMON.BIN (read from OUTDIR if a step wrote it)
  common.py roundtrip DISC
"""
import json
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMMON = os.path.join("MAP", "COMMON.BIN")

TABLES = {
    "units": (0x16E900, 0x1A7600, 0x100, [("name", 0x00, 34), ("height", 0xD0, 18), ("weight", 0xE2, 18)]),
    "pilots": (0x1AEA00, 0x1DF000, 0x200, [("name", 0x00, 36), ("short", 0x24, 20), ("name2", 0xB8, 64),
                                           ("voice", 0xF8, 64)]),
    "weapons": (0x1EE800, 0x22E000, 0x80, [("name", 0x00, 36)]),
}
MSG_BASE, MSG_SECTIONS, MSG_REGION = 0x23E800, 36, 0x10000
DESC_BASE, DESC_N = 0x2E7400, 1024


def to_game(text):
    """English -> game bytes (1 byte per character, see impact_text.py)."""
    import impact_text
    return impact_text.to_game(text)


def decode(raw):
    try:
        s = raw.decode("cp932")
        if s.encode("cp932") == raw:
            return s, None
    except UnicodeDecodeError:
        pass
    return raw.decode("cp932", "replace"), raw.hex()


def cstr(data, at):
    return bytes(data[at:data.index(b"\0", at)])


def entry(k, raw, **extra):
    jp, rawhex = decode(raw)
    e = {"id": k, "jp": jp, "en": "", "kind": "", "keep": False, **extra}
    if rawhex:
        e["raw"] = rawhex
    return e


def new_bytes(e, orig):
    if e.get("en_raw"):
        return bytes.fromhex(e["en_raw"])
    if e.get("en") and not e.get("keep"):
        return to_game(e["en"])
    return orig


# ---- record tables ---------------------------------------------------------------------

def table_fields(data, name):
    lo, hi, stride, fields = TABLES[name]
    out = []
    for r in range(lo, hi, stride):
        if data[r] < 0x81:          # every real record starts with a Shift-JIS name
            continue
        for fname, off, width in fields:
            at = r + off
            raw = cstr(data, at)
            end = at + len(raw) + 1
            z = end
            while z < at + width and data[z] == 0:
                z += 1
            # stale bytes inside the field are fine to overwrite only if they are text left over
            # from an older name; anything else ends the slot
            slot = width if z == at + width or data[z] >= 0x81 else z - at
            out.append({"at": at, "raw": raw, "budget": slot - 1, "record": r, "field": fname})
    return out


# ---- message bank ----------------------------------------------------------------------

def parse_msg(data):
    B = MSG_BASE
    hdr = struct.unpack_from(f"<{MSG_SECTIONS}H", data, B)
    sections = []
    for i, off in enumerate(hdr):
        S = B + off
        # the table runs up to its lowest target, which need not be its first entry
        cnt = (B + struct.unpack_from("<H", data, S)[0] - S) // 2
        while True:
            vals = struct.unpack_from(f"<{cnt}H", data, S)
            c2 = (B + min(vals) - S) // 2
            if c2 >= cnt:
                break
            cnt = c2
        sections.append({"vals": vals, "start": off})
    # Entries may point at a string that physically sits in another section, so strings are
    # owned by the section whose span holds them, and every table resolves through one map.
    # A target equal to a section's start is a marker, not a string: "end of the previous
    # section" or an empty section pointing at itself. It follows that section's new start.
    starts = set(hdr)
    targets = sorted({v for s in sections for v in s["vals"]} - starts)
    strings = {v: cstr(data, B + v) for v in targets}
    for i, s in enumerate(sections):
        lo, hi = hdr[i], hdr[i + 1] if i + 1 < MSG_SECTIONS else MSG_REGION
        s["phys"] = [v for v in targets if lo <= v < hi]
        # the alignment byte before the next section is sometimes stale (0x90), not zero
        s["pad"] = data[B + hi - 1:B + hi] if i + 1 < MSG_SECTIONS else b"\0"
    end = B + targets[-1] + len(strings[targets[-1]]) + 1
    return hdr, sections, strings, end


def build_msg(sections, texts):
    """texts[v] = new bytes for the string originally at bank offset v."""
    out = bytearray(2 * MSG_SECTIONS)
    hdr, tabs, pos = [], [], {}
    for i, sec in enumerate(sections):
        hdr.append(len(out))
        pos[sec["start"]] = len(out)
        tabs.append(len(out))
        out += bytes(2 * len(sec["vals"]))
        for v in sec["phys"]:
            pos[v] = len(out)
            out += texts[v] + b"\0"
        if i + 1 < len(sections) and len(out) % 2:
            out += sec["pad"]
    for sec, at in zip(sections, tabs):
        for k, v in enumerate(sec["vals"]):
            if pos[v] > 0xFFFF:
                raise ValueError("message bank offset exceeds 65,535")
            struct.pack_into("<H", out, at + 2 * k, pos[v])
    struct.pack_into(f"<{MSG_SECTIONS}H", out, 0, *hdr)
    if len(out) > MSG_REGION:
        raise ValueError(f"message bank is {len(out):,} bytes; the region holds {MSG_REGION:,}")
    return bytes(out) + bytes(MSG_REGION - len(out))


# ---- description bank ------------------------------------------------------------------

def parse_desc(data):
    D = DESC_BASE
    offs = struct.unpack_from(f"<{DESC_N}I", data, D)
    order = sorted(set(offs))
    recs = []
    end = D
    for o in order:
        n = struct.unpack_from("<H", data, D + o)[0]
        po = struct.unpack_from(f"<{n}H", data, D + o + 2)
        pages = [cstr(data, D + o + p) for p in po]
        recs.append({"off": o, "pages": pages})
        end = max(end, D + o + 2 + 2 * n, *[D + o + p + len(t) + 1 for p, t in zip(po, pages)])
    limit = end
    while limit < len(data) and data[limit] == 0:
        limit += 1
    return offs, order, recs, end, limit


def build_desc(offs, order, recs, texts, region):
    out = bytearray(4 * DESC_N)
    out += bytes(order[0] - len(out))             # first record sits at +0x1000
    where = {}
    for r, rec in zip(order, recs):
        where[r] = len(out)
        pages = texts[r]
        head = bytearray(2 + 2 * len(pages))
        struct.pack_into("<H", head, 0, len(pages))
        body = bytearray()
        for k, p in enumerate(pages):
            struct.pack_into("<H", head, 2 + 2 * k, len(head) + len(body))
            body += p + b"\0"
        out += head + body
        if len(out) % 2:
            out += b"\0"
    struct.pack_into(f"<{DESC_N}I", out, 0, *[where[o] for o in offs])
    if len(out) > region:
        raise ValueError(f"description bank is {len(out):,} bytes; the region holds {region:,}")
    return bytes(out)


# ---- commands --------------------------------------------------------------------------

def load_ws(wsdir, name):
    p = os.path.join(wsdir, f"COMMON_{name}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def save_ws(wsdir, name, strings, extra=None):
    path = os.path.join(wsdir, f"COMMON_{name}.json")
    if os.path.exists(path):        # keep existing English
        old = {x["id"]: x for x in json.load(open(path, encoding="utf-8"))["strings"]}
        for x in strings:
            o = old.get(x["id"])
            if o and o.get("jp") == x["jp"]:
                for key in ("en", "kind", "keep", "en_raw", "notes"):
                    if key in o:
                        x[key] = o[key]
    ws = {"file": "MAP/COMMON.BIN", "format": "COMMON", "part": name, **(extra or {}), "strings": strings}
    json.dump(ws, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return len(strings)


def cmd_extract(disc, wsdir):
    data = open(os.path.join(disc, COMMON), "rb").read()
    os.makedirs(wsdir, exist_ok=True)
    counts = {}
    for name in TABLES:
        fl = table_fields(data, name)
        counts[name] = save_ws(wsdir, name, [entry(k, f["raw"], at=f["at"], field=f["field"], budget=f["budget"])
                                             for k, f in enumerate(fl)])
    _, sections, strings, _ = parse_msg(data)
    refs = {}
    for sec in sections:
        for v in sec["vals"]:
            refs[v] = refs.get(v, 0) + 1
    ms = []
    for i, sec in enumerate(sections):
        for j, v in enumerate(sec["phys"]):
            ms.append(entry(len(ms), strings[v], section=i, index=j, refs=refs[v]))
    counts["msg"] = save_ws(wsdir, "msg", ms)
    _, order, recs, _, _ = parse_desc(data)
    ds = []
    for rec in recs:
        for k, raw in enumerate(rec["pages"]):
            ds.append(entry(len(ds), raw, record=rec["off"], page=k))
    counts["desc"] = save_ws(wsdir, "desc", ds)
    print("COMMON.BIN:", ", ".join(f"{k} {v:,}" for k, v in counts.items()), "->", wsdir)


def cmd_build(disc, wsdir, outdir):
    pristine = open(os.path.join(disc, COMMON), "rb").read()
    cur = os.path.join(outdir, COMMON)
    out = bytearray(open(cur if os.path.exists(cur) else os.path.join(disc, COMMON), "rb").read())
    over = []
    for name in TABLES:
        ws = load_ws(wsdir, name)
        if not ws:
            continue
        for f, e in zip(table_fields(pristine, name), ws["strings"]):
            assert e["at"] == f["at"]
            b = new_bytes(e, f["raw"])
            if b == f["raw"]:
                continue
            if len(b) > f["budget"]:
                over.append((name, e["id"], e["en"], len(b), f["budget"]))
                continue
            out[f["at"]:f["at"] + f["budget"] + 1] = b + bytes(f["budget"] + 1 - len(b))
    hdr, sections, strings, msg_end = parse_msg(pristine)
    ws = load_ws(wsdir, "msg")
    if ws:
        texts = dict(strings)
        changed = False
        for e in ws["strings"]:
            v = sections[e["section"]]["phys"][e["index"]]
            b = new_bytes(e, strings[v])
            changed |= b != strings[v]
            texts[v] = b
        if changed:
            out[MSG_BASE:MSG_BASE + MSG_REGION] = build_msg(sections, texts)
    offs, order, recs, desc_end, limit = parse_desc(pristine)
    ws = load_ws(wsdir, "desc")
    if ws:
        texts = {rec["off"]: list(rec["pages"]) for rec in recs}
        changed = False
        for e in ws["strings"]:
            orig = texts[e["record"]][e["page"]]
            b = new_bytes(e, orig)
            changed |= b != orig
            texts[e["record"]][e["page"]] = b
        if changed:
            blob = build_desc(offs, order, recs, texts, limit - DESC_BASE)
            out[DESC_BASE:limit] = blob + bytes(limit - DESC_BASE - len(blob))
    os.makedirs(os.path.join(outdir, "MAP"), exist_ok=True)
    open(cur, "wb").write(out)
    for o in over[:20]:
        print("  over budget (kept Japanese):", o)
    print(f"COMMON.BIN built; {len(over)} fields over budget")


def cmd_roundtrip(disc):
    data = open(os.path.join(disc, COMMON), "rb").read()
    ok = True
    # banks re-serialised from their parsed strings must reproduce the original bytes
    hdr, sections, strings, msg_end = parse_msg(data)
    blob = build_msg(sections, strings)
    same = blob == data[MSG_BASE:MSG_BASE + MSG_REGION]
    print(f"  message bank ({msg_end - MSG_BASE:,} of {MSG_REGION:,} bytes): {'identical' if same else 'DIFFERS'}")
    ok &= same
    offs, order, recs, end, limit = parse_desc(data)
    blob = build_desc(offs, order, recs, {r["off"]: r["pages"] for r in recs}, limit - DESC_BASE)
    same = blob + bytes(limit - DESC_BASE - len(blob)) == data[DESC_BASE:limit]
    print(f"  description bank ({end - DESC_BASE:,} bytes, room to {limit - DESC_BASE:,}): "
          f"{'identical' if same else 'DIFFERS'}")
    ok &= same
    with tempfile.TemporaryDirectory() as t:
        ws, out = os.path.join(t, "ws"), os.path.join(t, "out")
        cmd_extract(disc, ws)
        cmd_build(disc, ws, out)
        same = open(os.path.join(out, COMMON), "rb").read() == data
        print(f"  extract + build: {'identical' if same else 'DIFFERS'}")
        ok &= same
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    {"extract": lambda: cmd_extract(a[1], a[2]), "build": lambda: cmd_build(a[1], a[2], a[3]),
     "roundtrip": lambda: cmd_roundtrip(a[1])}[a[0]]()
