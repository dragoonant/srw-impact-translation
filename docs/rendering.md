# Rendering English in SRW Impact

Phase 4 notes. Verified in PCSX2 from a fresh boot on 2026-10-16: the opening scene in English
(proportional text, wrapped rows, English speaker names, face portraits unaffected).

## The ELF is not stripped

`SLPS_251.03` keeps its section headers, `.symtab`/`.strtab` (3,350 function symbols) and
`.mdebug`. The full list is written by the inventory step to `~/srwimpact-work/re/elf_functions.txt`
(`address size name`). Sections: `.text` file 0x1000-0x1503D4 (vaddr 0x100000), `.vutext`
0x1503E0-0x155340, `.data` 0x155380 (vaddr 0x254380), `.rodata` 0x2CCF80, VU microcode overlays
from 0x376CA8. File offset = vaddr - 0xFF000 for the loaded segment.

## Text routines by name (candidates)

| vaddr | Name | Guess |
|---|---|---|
| 0x1B0750 | `cnvSjisToAddr` | Shift-JIS code -> glyph address |
| 0x1B0CC8.. | `font_init`, `font_count`, `font_count_inside` | measure |
| 0x1B0E90 | `font_decode_HANKAKU` | **1-byte (half-width) glyph path already exists** |
| 0x1B0F90 | `font_decode_ZENKAKU` | 2-byte glyphs |
| 0x1B10E0 | `font_decode_SPACE` | |
| 0x1B1158 | `font_decode_number` | |
| 0x1B1520 / 0x1B1808 | `font_decode_inside`, `font_decode` | dispatcher |
| 0x1B1A30 | `font_packet_ex` | GS packet per glyph (advance?) |
| 0x1B2298 | `fontDraw` | |
| 0x1BDBC8 / 0x1BEE48 / 0x1C14C0 | `fontdisp_main`, `fontdisp_draw`, `fontdisp_draw2` | message window renderer |
| 0x1E4B78 | `get_max_x_font` | width measure for windows |
| 0x1ED308 | `wpf_font_packet` | menu (wpf*) font |
| 0x126070 | `maplogic_message_disp` | script command that shows a dialogue page |
| 0x1272A0 | `maplogic_face_read` | face portrait load (check whether it uses the speaker text) |
| 0x11FC50 | `maplogic_stage_title` | stage title card |

The prologue crawl already shows half-width Latin (`00XX`, `Dr.`) in a proportional-looking
serif font, so a half-width path is live somewhere. Next step: test ASCII in a dialogue line.

## How text is laid out (confirmed)

`font_decode` (about 160 callers: dialogue, menus, map; battle text reaches it through
`fontDraw`) runs `font_count_inside` to count rows and glyphs per row, then
`font_decode_inside` to copy glyph pixels into an 8-bit canvas. Every character is read as
2 bytes; `cnvSjisToAddr` gives index = JIS row*94 + column (some rare kanji remapped to spare
slots), glyph address = font base + index*338. The font is in `MAP/COMMON.BIN` at +0x2400;
COMMON.BIN is loaded at RAM 0xA00000 (so its tables sit at fixed addresses). Glyph cells are
26x26 at 4 bpp (low nibble = left pixel); indices below 470 are drawn 18 px wide
(`font_decode_HANKAKU`), the rest 26 px. A 256-entry palette per colour maps each source byte
to two canvas pixels. The canvas stride of a row is (glyphs in row) * 32 px.

ASCII bytes are control codes: `@` next row, `c`+B..Y colour, `s`+2 digits space,
`% & $ #`+digit numbers, `!` inserts a stored string. Plain ASCII therefore drew garbage, and
full-width Latin drew monospaced 18-px cells (about 24 characters per row).

## The patch (`tools/vwf_impact.py`)

Six original words are replaced (each asserted first); new code lives in `print_rootmap` /
`print_movemap` (unreferenced debug printers, 0x1947E8), the width table in `sceGetstat` /
`sceChstat` (unused SDK calls, 0x24A618). Unreferenced = no j/jal/branch, data pointer or
lui/addiu pair anywhere in the ELF (`tools/re/unref.py`).

* Bytes below 0x80 that are not control codes are 1-byte characters: table entry = glyph index,
  left bearing, advance (ink width + 1). The new draw routine writes exactly `advance` columns
  starting at the left bearing, byte by byte, so narrow letters pack tightly and nothing
  overlaps. The row width (ctx+0x60) grows by the advance.
* `c` is a colour code only before B..Y and `s` a space code only before two digits, in both
  the layout and the counting routine; otherwise they are letters.
* `impact_text.py` encodes English: `! # $ % &` as 0x1F..0x1B, ambiguous `c`/`s` as 0x1A/0x19,
  ü ä ö é Ü Ö Ä è à as 0x18..0x10 (glyphs composed by `impact_font.compose` into blank JIS cells
  0x81AD..0x81B5), engine codes written as `{cY}` `{%8}` `{s52}` tokens in the worksheets.
* The game's own Latin glyphs are kept (no repainted font): they read well proportionally.

## Budgets

Body rows are 400 canvas px (99.5th percentile of Japanese rows; a row next to a face shows
about 443 px). English averages 10.7 px per character, so about 37 characters per row and 2 body
rows per page. `impact_layout.wrap` wraps by pixels; `build.py` adds the speaker row from
`glossary/speakers.tsv`.

Still to check in game: battle quote window width, menus with long labels, the database and
help pages, and whether there is a message log.
