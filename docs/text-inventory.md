# SRW Impact text inventory (phase 3)

Every Japanese run on the disc is accounted for: translated, kept, or not text. Worksheets are
in `worksheets/` (one JSON per game file or table), classified by `tools/classify_impact.py`.

## Carriers

| Worksheets | Tool | Entries | Unique | Notes |
|---|---|---|---|---|
| `LOGIC/` (178) | `logic.py` | 34,748 | 32,044 | Story scripts. In the earlier OG translation memories: 0 |
| `BMC/` (372) | `bmc.py` | 19,959 | 9,464 | Battle quotes, one worksheet per pilot id |
| `COMMON/COMMON_units` | `common.py` | 1,383 | 637 | Unit name, height, weight |
| `COMMON/COMMON_pilots` | `common.py` | 1,488 | 585 | Full name, short name, full name again, voice actor |
| `COMMON/COMMON_weapons` | `common.py` | 1,635 | 631 | Weapon names |
| `COMMON/COMMON_msg` | `common.py` | 2,349 | 1,467 | Menus, system messages, item messages, stage recaps |
| `COMMON/COMMON_desc` | `common.py` | 1,414 | 1,244 | Database pages (characters, units) |
| `STRTAB/SLPS_251.03` | `strtab.py` | 480 | 433 | ELF strings (series names, skills, debug menus) |
| `STRTAB/TEST.MTI` | `strtab.py` | 376 | 120 | Terrain names |
| **Total** | | **63,831** | **46,507** | about 1.11 million unique Japanese characters |

Only 935 unique strings (2%) are already in the carried-over 2nd OG / Gaiden translation
memories, mostly names and short UI strings: Impact's licensed-series script is new work.

Coverage: `COMMON.BIN` has two binary-noise matches left outside these tables; `LOGIC.BIN`
and `BMCPACK.BIN` are covered in full by their pools; the ELF scan covers `.data`/`.rodata`.
Not yet inventoried: picture text (title cards, battle console, menus drawn as sprites).

## Kinds (after classification)

| Format | Kind | Translate | Keep |
|---|---|---|---|
| LOGIC | dialogue `Speaker@「...」` | 20,576 | 25 (`クワトロ@「開発中」` placeholders) |
| LOGIC | page (part of a longer speech) | 13,389 | |
| LOGIC | thought `Speaker@（...）` | 259 | |
| LOGIC | system (skill / level messages, no speaker) | 495 | |
| BMC | quote | 19,906 | 51 (`ＩＭキャラです！` placeholders, 1 empty) |
| COMMON | unit / pilot / weapon names | 461 / 1,116 / 1,635 | |
| COMMON | height / weight | 251 / 228 | 210 / 233 (dash placeholders; 27 weights with NEC characters kept byte-exact) |
| COMMON | voice actor | 210 | 162 (dashes) |
| COMMON | ui (message bank) | 1,599 | 750 (`未定義` "undefined" slots, dashes, `ＮＵＬＬ`) |
| COMMON | desc | 1,267 | 147 (`ダミー` pages) |
| STRTAB | ui (ELF) | 453 | 12 code-section fakes, 15 dash runs |
| STRTAB | terrain | 376 | |

## Shapes that matter for translation

- **Story pages.** A window shows the speaker on row 1 and at most **2 body rows** (16,211
  one-row pages, 18,217 two-row pages). Rows split at `@`; continuation rows start with U+3000.
  A long speech spans several strings, one per page: the first opens 「, the middle ones start
  `Speaker@　`, the last closes 」. The page count must stay the same, so translators need the
  whole speech as context and must keep each page's share of it.
- Japanese body rows: median 14 characters, 99.5th percentile 21, max 30.
- 247 distinct speakers. Whether the engine uses the speaker text to pick a face portrait is
  open (`maplogic_face_read`); test before translating speaker names.
- **Battle quotes** also use `@`+U+3000 row breaks (2,115 of them).
- **Message bank strings** may start with `cS`/`cY` (colour codes, keep as is).
- **Fixed fields** (names, heights): byte budgets 17-63; English must be 1-byte ASCII to fit.
