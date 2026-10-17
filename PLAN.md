# Super Robot Taisen Impact: English fan translation plan

Read `KNOWLEDGE-BASE.md` first (series-wide process and pitfalls; Part C covers PS2). This
file holds only Impact-specific facts and status. PS2 reference: `docs/ogg/` (OG Gaiden's
formats and renderer) and `tools/ogg/` (Gaiden's format tools, kept for porting).

## Target

- **Game:** Super Robot Taisen Impact, PS2, 2002, serial **SLPS-25103**, Limited Edition disc.
  `SYSTEM.CNF`: `BOOT2 = cdrom0:\SLPS_251.03;1`, `VER = 1.05`, NTSC.
- **Dump:** `Super Robot Taisen Impact [Limited Edition] [J].iso`, 4,220,256,256 bytes, plain ISO9660, 59 files.
  - CRC32 `dd514f92`
  - MD5 `c86e93496b5bc923df2df8917050cd3c`
  - SHA-1 `0b93c19ae88ddfb01b9ede1f7f85caf0a72dd03d`
  - SHA-256 `85ec3accb78ba280f6561468edde9f9875d9b04495875527fc3d1301aaddb956`
  - Not yet checked against redump.
- **Work folder:** `%USERPROFILE%\srwimpact-work\` (`pristine/disc` = extracted files,
  `pristine/SHA256SUMS.txt`, `pristine/ISO_HASHES.txt`, `pristine/inventory.json`).
- **Emulator:** PCSX2 only (as on Gaiden).

## Decisions (evilgouki, 2026-10-16)

| # | Decision |
|---|---|
| I1 | **Names:** Banpresto originals (Masaki, Shu, DC, Granzon...) follow our OGs / 2nd OG / Gaiden / MD canon (KB D1). **Licensed series** (Gundam, Mazinger, Getter, Dancougar...) follow the official Bandai Namco Asia English SRW releases (V, X, T, 30) first, then each show's official English release, then Akurasu, then our proposals. |
| I2 | **Translation:** in-session subagents, no API key (Moon Dwellers flow: `translate_batch.py export` → subagents → `check_chunk.py` → `ingest`). |
| I3 | **Distribution:** xdelta against the Limited Edition ISO above, with checksums in the README. |
| I4 | **Release bar:** AI-only beta (KB D2). |
| I5 | **Working mode:** Claude runs without waiting; assumptions are logged in `choices.md` as *assumed* for evilgouki to overturn. |

Standing series decisions D3–D6 apply (D3 is replaced by I3 for PS2): the Japanese script
never leaves this private repo; the public repo gets English-only worksheets.

## Disc layout (first look)

| Path | Size | First look |
|---|---|---|
| `SLPS_251.03` | 3.8 MB | Boot ELF (MIPS R5900). No `OL/` overlay folder on this disc |
| `MAP/LOGIC.BIN` | 4.9 MB | **Story scripts**: plain Shift-JIS `Speaker@「body」`, break `@`+U+3000 (Gaiden convention). ~34,700 text runs. Header = u16 table |
| `MAP/COMMON.BIN` | 4.2 MB | u16 offset table header; content looks packed |
| `MAP/MAPUNIT.BIN` | 0.9 MB | u32 offset table header; packed |
| `MAP/TEST.MTI` | 132 KB | Magic `MPTI`: terrain names (コンクリート...) |
| `MAP/STAGETIT.BIN` | 7.2 MB | Stage title cards (picture text) |
| `MAP/{MALL,LAYOUT,LAYOU1,GRID,IMNBG,MAPGRAPH}.BIN` | | Map graphics and layouts |
| `BTL/BMCPACK.BIN` | 0.9 MB | **Battle quotes**: plain `「...」` Shift-JIS, ~19,500 runs |
| `BTL/{TITLPACK,ROLLPACK,SROLPACK,CSL_PACK,FACEPACK,BTLEFCT,BTL_BG_P}.BIN` | | Title, staff roll, battle console, faces, effects, backgrounds |
| `STRM.BIN` / `SOUND.BIN` | 1.7 GB / 84 MB | Voice and music |
| `PSS/M000..M022.PSS` | | 23 MPEG-PS movies |
| `DUMMY` | 32 MB | Zero padding |

## Phase 1 results (2026-10-16)

- **Boots in PCSX2** (installed at `C:\Program Files\PCSX2`, BIOS `scph39001.bin`, `-fastboot`).
  PINE reports `SLPS-25103 | スーパーロボット大戦IMPACT [限定版]`; save-state CRC `216658F6`.
- **Test sessions:** `tools/pcsx2_session.py begin|end` backs up `PCSX2.ini`, switches Pad1 to the
  keyboard profile and enables PINE, and restores the whole INI at the end. `tools/pcsx2_shot.py NAME
  "keys"` presses keys, takes an F8 screenshot (retrying past OneDrive's file lock) and writes a
  640x480 preview to `~/srwimpact-work/ref/shots`.
- **Reference save states** (slots 7-9 in PCSX2's `sstates`, copies in `~/srwimpact-work/ref/sstates`):
  7 = title screen ("PRESS ANY BUTTON"), 8 = new-game prologue crawl, 9 = first story dialogue.
- **What the first minutes show:**
  - Health warning: Japanese text in a gothic bitmap font (probably a picture; check in phase 3).
  - Title menu (START / CONTINUE) is already English picture text.
  - Prologue crawl: a serif font with **half-width proportional Latin** (`00XX`, `Dr.`). Probably
    pre-rendered pictures or a separate text path; to identify in phase 3.
  - Story dialogue: two windows (top and bottom), speaker on the first row, body in 「」 on the
    next, **fixed-width glyphs** (each `？` takes a full cell). The first lines are in
    `MAP/LOGIC.BIN` at 0x353B0D as `？？？@「望んでいない…世界…修正…」`; each line occurs twice
    in the file (two copies of the scene, or two routes; phase 2 will tell).

## Phase status

| # | Phase | Status |
|---|---|---|
| 1 | Data in hand | **Done** 2026-10-16 (see *Phase 1 results*). Redump hash check still to do |
| 2 | Round-trip tools | **Text carriers done** 2026-10-16: `logic.py` (story, 34,748 strings), `bmc.py` (battle quotes, 19,959), `strtab.py` (ELF, COMMON.BIN, TEST.MTI in place). All byte-identical, and the tools chain through one output folder. See `docs/formats.md`. Picture-text containers (STAGETIT, TITLPACK, CSL_PACK, IMNBG...) are decoded when picture text is done |
| 3 | Text inventory | **Done** 2026-10-16. `docs/text-inventory.md`: 63,831 entries (46,507 unique, 2% in the old TMs), classified; COMMON.BIN fully mapped by `common.py`. The ELF is unstripped (3,350 symbols), see `docs/rendering.md` |
| 4 | Make English render | **Done** 2026-10-16: proportional 1-byte English (`vwf_impact.py`), encoder, wrapper, `build.py` → patched ISO; opening scene verified from a fresh boot. See `docs/rendering.md` |
| 5 | Glossary | **Done** 2026-10-16: `glossary/impact_names.tsv` (1,793 names; official SRW / show English, OG canon, Akurasu, 667 proposals) and `glossary/impact_terms.tsv` (settled terms) |
| 6 | Pilot chapter | **Done** 2026-10-16: story and battle pilots by subagents, 0 checker problems |
| 7 | Full pass | **Done** 2026-10-17: 62,227 entries by in-session subagents (`tools/xl_impact.py`, brief in `docs/xl/`); consistency pass; fitcheck 0 problems |
| 8 | Playtest and fix | **Started**: opening scenes, map dialogue, map/unit menus, Spirit screen, pre-battle screen and battle quotes verified in PCSX2; label fixes applied. Intermission, database and title cards not yet seen in game. Picture text 2026-10-17: crawls, part title cards and episode numbers in English (opening crawl and part 1 card seen in game); battle console atlas, logo fly-in and staff credits done too (choices 23-25; ATK badge and fly-in seen in game). Only the title-screen backdrop logo is still Japanese (source not found) |
| 9 | Edit pass | Optional (I4) |
| 10 | Release | **Packaged locally** 2026-10-17: `~/srwimpact-work/release/SRW_Impact_EN_v0.1.xdelta` (2.41 MB, round-trip verified; rebuilt with all picture text), README, CHANGELOG, public tree from `tools/export_public.py`. Not published (needs evilgouki's OK) |
