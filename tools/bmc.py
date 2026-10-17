#!/usr/bin/env python3
"""BTL/BMCPACK.BIN: SRW Impact's battle quotes, one sub-file per pilot.

Layout (little-endian):
  Directory: MAP/COMMON.BIN at 0x400400, 400 u32 byte offsets into BMCPACK.BIN, one per
  pilot id; 0xFFFFFFFF = no quotes (28 ids). 372 sub-files, in file order, each starting
  4-byte aligned; the gap after a sub-file is 0-3 zero bytes.

  Sub-file header: 12 situation records of 24 bytes (u32 first slot, u32 slot count, 16
  bytes of flags), then section data. The u16 at +0x138 is the offset of the string-offset
  table and the u16 at +0x13A the offset of the string pool (both from the sub-file start).
  The table is n strictly increasing u16 offsets from the pool start (the first is 0),
  followed by 0-2 zero words up to the pool. Strings are NUL-terminated Shift-JIS, nearly
  all wrapped in 「」. Other sections (voice clip id per slot, per-slot flags) are kept
  verbatim; only the pool and the table's values change.

  A rebuild may change a sub-file's size: sub-files are laid out again in order and the
  COMMON.BIN directory is remapped.

Usage:
  bmc.py extract DISC WSDIR          one worksheet per sub-file (WSDIR/BMC_ppp.json, ppp = pilot id)
  bmc.py build   DISC WSDIR OUTDIR   OUTDIR/BTL/BMCPACK.BIN and OUTDIR/MAP/COMMON.BIN
                                     (COMMON.BIN is read from OUTDIR if an earlier step wrote it)
  bmc.py roundtrip DISC
  bmc.py info DISC
"""
import json
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BMC = os.path.join("BTL", "BMCPACK.BIN")
COMMON = os.path.join("MAP", "COMMON.BIN")
DIR_AT = 0x400400
N_IDS = 400
NONE = 0xFFFFFFFF


def to_game(text):
    """English -> game bytes (1 byte per character, see impact_text.py)."""
    import impact_text
    return impact_text.to_game(text)


def src(disc, outdir, rel):
    p = os.path.join(outdir, rel) if outdir else None
    return open(p if p and os.path.exists(p) else os.path.join(disc, rel), "rb").read()


def parse_sub(data):
    t, p = struct.unpack_from("<2H", data, 0x138)
    words = struct.unpack_from(f"<{(p - t) // 2}H", data, t)
    assert words[0] == 0, "string table does not start at 0"
    n = 1
    while n < len(words) and words[n] > words[n - 1]:
        n += 1
    assert not any(words[n:]), "non-zero words after the string table"
    # The last string may run to the end of the sub-file with no NUL of its own: the next
    # sub-file's first byte (always 0) terminates it. One sub-file does this.
    raws = []
    for o in words[:n]:
        e = data.find(b"\0", p + o)
        raws.append(data[p + o:e if e >= 0 else len(data)])
    end = min(p + words[n - 1] + len(raws[-1]) + 1, len(data))
    assert not any(data[end:]), "non-zero bytes after the pool"
    return {"table": t, "pool": p, "n": n, "raws": raws, "end": end}


def load(disc, outdir=None):
    common = src(disc, outdir, COMMON)
    data = open(os.path.join(disc, BMC), "rb").read()
    ids = struct.unpack_from(f"<{N_IDS}I", common, DIR_AT)
    starts = sorted({v for v in ids if v != NONE})
    bounds = starts + [len(data)]
    first_id = {}
    for i, v in enumerate(ids):
        if v != NONE:
            first_id.setdefault(v, i)
    subs = []
    for a, b in zip(bounds, bounds[1:]):
        blk = data[a:b]
        subs.append({"start": a, "id": first_id[a], "data": blk, **parse_sub(blk)})
    return bytearray(common), data, ids, subs


def decode(raw):
    try:
        s = raw.decode("cp932")
        if s.encode("cp932") == raw:
            return s, None
    except UnicodeDecodeError:
        pass
    return raw.decode("cp932", "replace"), raw.hex()


def cmd_extract(disc, wsdir):
    _, _, _, subs = load(disc)
    os.makedirs(wsdir, exist_ok=True)
    total = 0
    for s in subs:
        strings = []
        for k, raw in enumerate(s["raws"]):
            jp, rawhex = decode(raw)
            e = {"id": k, "jp": jp, "en": "", "kind": "", "keep": False}
            if rawhex:
                e["raw"] = rawhex
            strings.append(e)
        path = os.path.join(wsdir, f"BMC_{s['id']:03d}.json")
        if os.path.exists(path):   # keep existing English
            old = {x["id"]: x for x in json.load(open(path, encoding="utf-8"))["strings"]}
            for x in strings:
                o = old.get(x["id"])
                if o and o.get("jp") == x["jp"]:
                    for key in ("en", "kind", "keep", "en_raw", "notes"):
                        if key in o:
                            x[key] = o[key]
        ws = {"file": "BTL/BMCPACK.BIN", "format": "BMC", "pilot": s["id"], "strings": strings}
        json.dump(ws, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        total += len(strings)
    print(f"{len(subs)} worksheets, {total} strings -> {wsdir}")


def string_bytes(x, orig):
    if x.get("en_raw"):
        return bytes.fromhex(x["en_raw"])
    if x.get("en") and not x.get("keep"):
        return to_game(x["en"])
    return orig


def build_sub(s, ws):
    new = [string_bytes(x, s["raws"][x["id"]]) for x in ws["strings"]]
    assert len(new) == s["n"], f"pilot {s['id']}: string count changed"
    if new == s["raws"]:
        return s["data"]
    out = bytearray(s["data"][:s["pool"]])
    pool = bytearray()
    for k, r in enumerate(new):
        if len(pool) > 0xFFFF:
            raise ValueError(f"pilot {s['id']}: pool exceeds 65,535 bytes")
        struct.pack_into("<H", out, s["table"] + 2 * k, len(pool))
        pool += r + b"\0"
    out += pool
    out += bytes(-len(out) % 4)
    return bytes(out)


def cmd_build(disc, wsdir, outdir):
    common, data, ids, subs = load(disc, outdir)
    body = bytearray()
    remap = {}
    changed = 0
    for s in subs:
        remap[s["start"]] = len(body)
        blk = s["data"]
        path = os.path.join(wsdir, f"BMC_{s['id']:03d}.json")
        if os.path.exists(path):
            blk = build_sub(s, json.load(open(path, encoding="utf-8")))
            changed += blk is not s["data"]
        body += blk
    struct.pack_into(f"<{N_IDS}I", common, DIR_AT, *[NONE if v == NONE else remap[v] for v in ids])
    os.makedirs(os.path.join(outdir, "BTL"), exist_ok=True)
    os.makedirs(os.path.join(outdir, "MAP"), exist_ok=True)
    open(os.path.join(outdir, BMC), "wb").write(body)
    open(os.path.join(outdir, COMMON), "wb").write(common)
    print(f"BMCPACK.BIN {len(data):,} -> {len(body):,} bytes; {changed} sub-files rebuilt")


def cmd_roundtrip(disc):
    with tempfile.TemporaryDirectory() as t:
        ws, out = os.path.join(t, "ws"), os.path.join(t, "out")
        cmd_extract(disc, ws)
        cmd_build(disc, ws, out)
        ok = True
        for f in (BMC, COMMON):
            same = open(os.path.join(disc, f), "rb").read() == open(os.path.join(out, f), "rb").read()
            print(f"  {f}: {'identical' if same else 'DIFFERS'}")
            ok &= same
        _, _, _, subs = load(disc)
        bad = 0
        for s in subs:   # forced re-serialisation with the original bytes
            ws_ = {"strings": [{"id": k, "en_raw": r.hex()} for k, r in enumerate(s["raws"])]}
            s2 = dict(s, raws=[None] * s["n"])   # make every string count as changed
            if build_sub(s2, ws_) != s["data"]:
                bad += 1
        print(f"  forced sub-file rebuild: {bad} differ")
        sys.exit(0 if ok and not bad else 1)


def cmd_info(disc):
    _, data, ids, subs = load(disc)
    n = sum(s["n"] for s in subs)
    uniq = len({r for s in subs for r in s["raws"]})
    pools = [s["end"] - s["pool"] for s in subs]
    print(f"BMCPACK.BIN {len(data):,} bytes, {len(subs)} sub-files ({sum(v == NONE for v in ids)} "
          f"empty ids), {n:,} strings ({uniq:,} unique), pool max {max(pools):,} bytes")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    {"extract": lambda: cmd_extract(a[1], a[2]), "build": lambda: cmd_build(a[1], a[2], a[3]),
     "roundtrip": lambda: cmd_roundtrip(a[1]), "info": lambda: cmd_info(a[1])}[a[0]]()
