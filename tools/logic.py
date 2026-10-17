#!/usr/bin/env python3
"""MAP/LOGIC.BIN: SRW Impact's stage data (story scripts, unit placement, script code).

Layout (all little-endian, 0x800-byte sectors):
  The file is a run of sector-aligned blocks. Their start sectors are listed in a
  directory in the boot ELF SLPS_251.03 at file offset 0x157EB8 (vaddr 0x256EB8):
  235 records of 3 x (u32 sector, u32 0). An identical copy sits in MAP/COMMON.BIN at
  0x3ED808. The largest value is the file's sector count (end of file). Sector 0 is a
  block too. Every listed sector (plus 0) starts a block that runs to the next start.
  Block kinds: string pools, script code (first u16 = 8), unit placement ("UNTD"), others.

  String pool: u16 off[n] (off[0] = 2n, strictly increasing), then n NUL-terminated
  Shift-JIS strings at block + off[k]; u16 offsets cap a pool at 65,535 bytes. After the
  last string the original tool left stale bytes (old string fragments) up to the sector
  end; an unchanged pool keeps them verbatim, a rebuilt one is zero-filled.
  Dialogue strings look like `Speaker@「body」` with `@`+U+3000 continuation breaks.

  A rebuild may change pool sizes: blocks are laid out again in their original order and
  every sector in the ELF directory and the COMMON.BIN copy is remapped.

Usage:
  logic.py extract DISC WSDIR          one worksheet per string pool (WSDIR/LOGIC_ssss.json)
  logic.py build   DISC WSDIR OUTDIR   writes OUTDIR/MAP/LOGIC.BIN, OUTDIR/SLPS_251.03,
                                       OUTDIR/MAP/COMMON.BIN
  logic.py roundtrip DISC              extract + build with no edits; must be byte-identical
  logic.py info DISC
DISC is the extracted disc folder (SLPS_251.03, MAP/...).
"""
import json
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SECTOR = 0x800
DIR_ELF = 0x157EB8
DIR_COMMON = 0x3ED808
N_RECS = 235
MAX_POOL_SECTORS = 12        # largest original pool (24,024 bytes) rounded up
ELF = "SLPS_251.03"
LOGIC = os.path.join("MAP", "LOGIC.BIN")
COMMON = os.path.join("MAP", "COMMON.BIN")


def to_game(text):
    """English -> game bytes (1 byte per character, see impact_text.py)."""
    import impact_text
    return impact_text.to_game(text)


def read_dir(elf):
    recs = []
    for i in range(N_RECS):
        r = struct.unpack_from("<6I", elf, DIR_ELF + 24 * i)
        assert r[1] == r[3] == r[5] == 0, f"directory record {i} has a non-zero high word"
        recs.append([r[0], r[2], r[4]])
    return recs


def write_dir(buf, at, recs):
    for i, r in enumerate(recs):
        struct.pack_into("<6I", buf, at + 24 * i, r[0], 0, r[1], 0, r[2], 0)


def parse_pool(blk):
    """(offsets, end of last string) if blk starts with a string pool, else None."""
    if len(blk) < 6:
        return None
    v0 = struct.unpack_from("<H", blk, 0)[0]
    if v0 < 4 or v0 % 2 or v0 > len(blk):
        return None
    n = v0 // 2
    offs = struct.unpack_from(f"<{n}H", blk, 0)
    if any(offs[k] >= offs[k + 1] for k in range(n - 1)) or offs[-1] >= len(blk):
        return None
    if not all(blk[offs[k] - 1] == 0 for k in range(1, n)):
        return None
    end = blk.find(b"\0", offs[-1])
    if end < 0:
        return None
    return offs, end + 1


def blocks(disc):
    elf = open(os.path.join(disc, ELF), "rb").read()
    data = open(os.path.join(disc, LOGIC), "rb").read()
    recs = read_dir(elf)
    starts = sorted({s for r in recs for s in r} | {0})
    assert starts[-1] * SECTOR == len(data), "directory end does not match LOGIC.BIN size"
    out = []
    for a, b in zip(starts, starts[1:]):
        blk = data[a * SECTOR:b * SECTOR]
        out.append({"sector": a, "data": blk, "pool": parse_pool(blk)})
    return elf, data, recs, out


def decode(raw):
    try:
        s = raw.decode("cp932")
        if s.encode("cp932") == raw:
            return s, None
    except UnicodeDecodeError:
        pass
    return raw.decode("cp932", "replace"), raw.hex()


def cmd_extract(disc, wsdir):
    _, _, _, bl = blocks(disc)
    os.makedirs(wsdir, exist_ok=True)
    n_ws = n_str = 0
    for b in bl:
        if not b["pool"]:
            continue
        offs, _ = b["pool"]
        strings = []
        for k, o in enumerate(offs):
            raw = b["data"][o:b["data"].index(b"\0", o)]
            jp, rawhex = decode(raw)
            e = {"id": k, "jp": jp, "en": "", "kind": "", "keep": False}
            if rawhex:
                e["raw"] = rawhex
            strings.append(e)
        ws = {"file": "MAP/LOGIC.BIN", "format": "LOGIC", "block": b["sector"], "strings": strings}
        path = os.path.join(wsdir, f"LOGIC_{b['sector']:04x}.json")
        prev = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
        if prev:   # keep existing English and tags; refresh the Japanese
            old = {s["id"]: s for s in prev["strings"]}
            for s in strings:
                o = old.get(s["id"])
                if o and o.get("jp") == s["jp"]:
                    for key in ("en", "kind", "keep", "en_raw", "notes"):
                        if key in o:
                            s[key] = o[key]
        json.dump(ws, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n_ws += 1
        n_str += len(strings)
    print(f"{n_ws} worksheets, {n_str} strings -> {wsdir}")


def string_bytes(s, orig_raw):
    if s.get("en_raw"):
        return bytes.fromhex(s["en_raw"])
    if s.get("en") and not s.get("keep"):
        return to_game(s["en"])
    return orig_raw


def build_pool(b, ws):
    offs, end = b["pool"]
    data = b["data"]
    raws = [data[o:data.index(b"\0", o)] for o in offs]
    new = [string_bytes(s, raws[s["id"]]) for s in ws["strings"]]
    assert len(new) == len(offs), f"block {b['sector']:#x}: string count changed"
    if new == raws:
        return data                      # unchanged: original bytes, stale tail included
    out = bytearray(2 * len(new))
    for k, r in enumerate(new):
        if len(out) > 0xFFFF:
            raise ValueError(f"block {b['sector']:#x}: pool exceeds 65,535 bytes")
        struct.pack_into("<H", out, 2 * k, len(out))
        out += r + b"\0"
    if len(out) > 0xFFFF + 1:
        raise ValueError(f"block {b['sector']:#x}: pool exceeds 65,535 bytes")
    out += bytes(-len(out) % SECTOR)
    # The largest Japanese pool is 24,024 bytes = 12 sectors; the game reads whole sectors, so a
    # pool must not need more than that (the RAM buffer is not proven larger).
    if len(out) > MAX_POOL_SECTORS * SECTOR:
        raise ValueError(f"block {b['sector']:#x}: pool needs {len(out) // SECTOR} sectors "
                         f"(max {MAX_POOL_SECTORS}); shorten its English")
    return bytes(out)


def cmd_build(disc, wsdir, outdir):
    elf, data, recs, bl = blocks(disc)
    # The directory comes from the pristine ELF; the patched copies are written into whatever
    # an earlier build step left in OUTDIR (other tools patch the ELF and COMMON.BIN too).
    def current(rel):
        p = os.path.join(outdir, rel)
        return bytearray(open(p if os.path.exists(p) else os.path.join(disc, rel), "rb").read())
    common = current(COMMON)
    assert common[DIR_COMMON:DIR_COMMON + 24 * N_RECS] == elf[DIR_ELF:DIR_ELF + 24 * N_RECS], \
        "COMMON.BIN directory copy differs from the ELF's"
    elf_out = current(ELF)
    body = bytearray()
    remap = {}
    changed = 0
    for b in bl:
        remap[b["sector"]] = len(body) // SECTOR
        blk = b["data"]
        if b["pool"]:
            path = os.path.join(wsdir, f"LOGIC_{b['sector']:04x}.json")
            if os.path.exists(path):
                blk = build_pool(b, json.load(open(path, encoding="utf-8")))
                changed += blk is not b["data"]
        body += blk
    remap[len(data) // SECTOR] = len(body) // SECTOR
    new_recs = [[remap[s] for s in r] for r in recs]
    elf2 = elf_out
    write_dir(elf2, DIR_ELF, new_recs)
    write_dir(common, DIR_COMMON, new_recs)
    os.makedirs(os.path.join(outdir, "MAP"), exist_ok=True)
    open(os.path.join(outdir, LOGIC), "wb").write(body)
    open(os.path.join(outdir, ELF), "wb").write(elf2)
    open(os.path.join(outdir, COMMON), "wb").write(common)
    print(f"LOGIC.BIN {len(data):,} -> {len(body):,} bytes; {changed} pools rebuilt")


def cmd_roundtrip(disc):
    with tempfile.TemporaryDirectory() as t:
        ws, out = os.path.join(t, "ws"), os.path.join(t, "out")
        cmd_extract(disc, ws)
        cmd_build(disc, ws, out)
        ok = True
        for f in (LOGIC, ELF, COMMON):
            same = open(os.path.join(disc, f), "rb").read() == open(os.path.join(out, f), "rb").read()
            print(f"  {f}: {'identical' if same else 'DIFFERS'}")
            ok &= same
        # forced rebuild: every pool re-serialised, strings unchanged
        _, data, _, bl = blocks(disc)
        bad = 0
        for b in bl:
            if b["pool"]:
                offs, end = b["pool"]
                ws_ = {"strings": [{"id": k, "en_raw": b["data"][o:b["data"].index(b"\0", o)].hex()}
                                   for k, o in enumerate(offs)]}
                rebuilt = build_pool(b, ws_)
                if rebuilt is b["data"]:
                    continue
                if rebuilt[:end] != b["data"][:end]:
                    bad += 1
        print(f"  forced pool rebuild: {bad} pools differ before their stale tail")
        sys.exit(0 if ok and not bad else 1)


def cmd_info(disc):
    _, data, recs, bl = blocks(disc)
    pools = [b for b in bl if b["pool"]]
    kinds = {}
    for b in bl:
        k = "pool" if b["pool"] else ("UNTD" if b["data"][:4] == b"UNTD" else
                                      "script" if b["data"][:2] == b"\x08\x00" else "other")
        kinds[k] = kinds.get(k, 0) + 1
    print(f"LOGIC.BIN {len(data):,} bytes, {len(bl)} blocks {kinds}, {N_RECS} directory records")
    sizes = [b["pool"][1] for b in pools]
    print(f"pools: {len(pools)}, strings {sum(len(b['pool'][0]) for b in pools):,}, "
          f"bytes max {max(sizes):,} mean {sum(sizes) // len(sizes):,}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    {"extract": lambda: cmd_extract(a[1], a[2]), "build": lambda: cmd_build(a[1], a[2], a[3]),
     "roundtrip": lambda: cmd_roundtrip(a[1]), "info": lambda: cmd_info(a[1])}[a[0]]()
