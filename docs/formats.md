# SRW Impact (SLPS-25103) file formats

Everything here was confirmed on our own dump (Limited Edition). Tools are named per section.
Gaiden's formats (`docs/ogg/formats.md`) are a different engine generation; nothing there
carries over without re-checking.

## Disc (`tools/iso_tool.py`)

Plain ISO9660, 59 files, no `OL/` overlays. See `PLAN.md` for the file list. `DUMMY` (32 MB of
zeros) is the last file on the disc.

## Text carriers (first scan, `tools/textscan.py`)

| File | Shift-JIS runs | Content |
|---|---|---|
| `MAP/LOGIC.BIN` | 60,665 runs / 756k chars | Story scripts (below) |
| `BTL/BMCPACK.BIN` | 21,049 / 280k | Battle quotes |
| `MAP/COMMON.BIN` | 8,817 / 124k | System messages, data tables (to decode) |
| `SLPS_251.03` | 267 / 2k | Executable strings |
| `MAP/TEST.MTI` | 60 | Terrain names (magic `MPTI`) |
| others | | Noise from graphics data, except picture text |

## LOGIC.BIN: stage data (`tools/logic.py`)

A run of sector-aligned (0x800) blocks: 562 blocks of four kinds: 178 string pools, 226 script
code blocks (first u16 = 8), 110 unit placement blocks (magic `UNTD`), 48 others.

**Directory.** The boot ELF holds the block start sectors at file offset 0x157EB8 (vaddr
0x256EB8): 235 records of 3 x (u32 sector, u32 0). An identical copy is in `MAP/COMMON.BIN` at
0x3ED808. Sector 0 and every listed sector start a block, which runs to the next start; the
largest listed value is the file's sector count. Record columns are mostly (pool, UNTD, script)
per stage, but not always, so the tool treats them as plain sector numbers.

**String pool.** u16 `off[n]`, `off[0] = 2n`, strictly increasing, then n NUL-terminated
Shift-JIS strings at `block + off[k]`; a pool is at most 65,535 bytes (largest original: 24,024).
After the last string the original tool left stale bytes up to the sector end; unchanged pools
keep them, rebuilt ones are zero-filled. 34,748 strings in all.

**Dialogue strings.** `Speaker@「body」`, the speaker on the first row of the window and `@`
starting the next row; body rows continue after `@`+U+3000. Example (the first scene, pool
0x6A7): `？？？@「望んでいない…世界…修正…」`.

**Rebuild.** Pools may change size. Blocks are laid out again in their original order and every
sector in both directory copies is remapped. Round trip (no edits) is byte-identical for
`LOGIC.BIN`, the ELF and `COMMON.BIN`; a forced re-serialisation of every pool reproduces every
string.

## BMCPACK.BIN: battle quotes (`tools/bmc.py`)

One sub-file per pilot, 372 in all, 4-byte aligned, zero-padded.

**Directory.** `MAP/COMMON.BIN` at 0x400400: 400 u32 byte offsets, one per pilot id;
0xFFFFFFFF = no quotes (28 ids). Not in the ELF.

**Sub-file.** 12 situation records of 24 bytes (u32 first slot, u32 slot count, 16 bytes of
flags; the 12 situations are presumably attack, hit, miss, damage and so on, to confirm), then
section data. u16 at +0x138 = string-offset table, u16 at +0x13A = string pool (offsets from the
sub-file start). The table is n strictly increasing u16 offsets from the pool start (first 0),
then 0-2 zero words. Other sections (a voice clip id per slot, per-slot flags, and in some
sub-files extra data) stay verbatim. One sub-file's last string has no NUL of its own; the next
sub-file's first byte ends it.

19,959 quotes, 9,465 unique; largest pool 14,096 bytes. No `@` breaks: the battle window
probably wraps by itself (to check in phase 4).

**Rebuild.** Sub-files may change size; they are laid out again in order and the COMMON.BIN
directory is remapped. Round trip byte-identical; `logic.py` then `bmc.py` into one output
folder also reproduces `COMMON.BIN` and the ELF exactly.

## COMMON.BIN: data tables and messages (`tools/common.py`)

4.2 MB of tables, apparently loaded whole into RAM; no section directory was found in the
ELF, so the code probably reaches each table at a fixed address and **tables must not move**
(to confirm with a RAM dump in phase 4). Everything is edited in place or rebuilt inside the
region it already owns.

| Part | Where | Shape | Strings |
|---|---|---|---|
| Units | 0x16E900-0x1A7600 | 0x100-byte records: name +0x00 (34-byte field), height +0xD0 (18), weight +0xE2 (18) | 1,383 fields |
| Pilots | 0x1AEA00-0x1DF000 | 0x200-byte records: full name +0x00 (36), short name +0x24 (20), full name again +0xB8 (64), voice actor +0xF8 (64) | 1,488 |
| Weapons | 0x1EE800-0x22E000 | 0x80-byte records: name +0x00 (36) | 1,635 |
| Message bank | 0x23E800, region 64 KB | u16 hdr[36] section offsets; each section a u16 table of offsets **from the bank** then strings; 52,132 bytes used | 2,349 |
| Description bank | 0x2E7400 | u32 off[1024] from the bank; records `u16 n, u16 page_off[n], pages`; 197,096 bytes, zeros free up to 1 MB | 1,414 pages |
| LOGIC.BIN directory copy | 0x3ED808 | see above | |
| BMCPACK.BIN directory | 0x400400 | see above | |

Field budgets are the field width minus 1, or less where the record's own data starts
earlier (stale text left from an older, longer name inside a field is overwritten).

**Message bank details.** A section's table runs up to its lowest target (not always its first
entry). Entries may point at strings that physically sit in another section, and a target equal
to a section's start is a marker (end of the previous section, or an empty section pointing at
itself), not a string. Sections are padded to even offsets with a byte that is sometimes a stale
0x90. Strings with a `cS`/`cY` prefix carry what look like colour codes. Rebuilt, the bank must
stay within 65,536 bytes (25% more than now).

**Coverage.** After these parts, only two binary-noise matches remain uncovered in COMMON.BIN.
`common.py roundtrip`: both banks re-serialise byte-identically, extract + build is identical,
and `logic.py`, `bmc.py`, `common.py` chained into one output folder reproduce all four files.

## Build order

Several tools patch the same files (`COMMON.BIN`, the ELF). Each build step reads a file from
the output folder if an earlier step wrote it, else from the pristine disc.

**Open:** the RAM buffer a pool is loaded into (largest original 24,024 bytes), to measure in
phase 4 before English makes pools bigger; and whether LOGIC.BIN can grow in place on the disc
(next file's LBA) or must move into `DUMMY`'s space.
