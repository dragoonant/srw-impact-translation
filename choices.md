# Choices for evilgouki

Every decision made on this project, newest at the bottom of each section. Claude keeps
working on its own (I5 in `PLAN.md`) and logs each assumption here, so you can overturn any of
them: write your answer under the item.

Status key: **done** (you decided), **assumed** (Claude picked a default and kept going; say if
you disagree), **open** (needs you, but nothing is blocked on it yet).

## Project setup

1. **Name canon for licensed series**: done (2026-10-16). Official SRW English releases first (I1).
2. **Translation method**: done. In-session subagents, no API (I2).
3. **Distribution**: done. xdelta against the Limited Edition ISO (I3).
4. **Release bar**: done. AI-only beta (I4).
5. **Work folder**: assumed. `%USERPROFILE%\srwimpact-work`, outside OneDrive, short path.
6. **Repo**: assumed. Local git repo in this folder, never pushed (it holds the Japanese). A
   public English-only repo, e.g. `dragoonant/srw-impact-translation`, is created only at release,
   with your OK.
7. **Standard edition**: assumed. Not supported (we only have the Limited Edition dump). If you
   get a standard-edition ISO, a second xdelta is cheap.
8. **Hardware**: assumed. PCSX2 only, as on Gaiden; real PS2 / OPL not tested.
9. **Font**: assumed. Fira Sans (OFL), as on Gaiden, unless Impact's own font turns out usable.
10. **Style guide**: assumed. Carried over unchanged from Moon Dwellers (no honorifics except
    Rishu-sensei, ranks in full, no quote marks on spoken lines, thoughts in parentheses).
11. **Tools carried over**: assumed. Moon Dwellers' pipeline tools (newest) plus Gaiden's PS2 tools;
    Gaiden's format tools are in `tools/ogg/` as porting references only.
12. **Test save-state slots**: assumed. Claude's scripted tests use PCSX2 slots 7-9 for Impact and
    never touch slots 1-6, which stay yours.
13. **Title menu** (START / CONTINUE): assumed. Already English on the disc; left as is.

## Rendering and layout (2026-10-16)

14. **Font**: assumed (replaces 9). The game's own Latin glyphs, drawn proportionally; Fira Sans is
    not needed. Umlauts and é/è/à are composed from the game's glyphs.
15. **No 「」 on English dialogue**: assumed. English pages are `Speaker` row + body rows; the
    Japanese brackets and the full-width spaces that aligned continuation rows are dropped
    (same no-quote-marks rule as our other patches). Thoughts stay in (parentheses).
16. **Row budget**: assumed. 400 px per body row, 2 body rows per page, wrapped by the build.
17. **Exclamation marks and %**: done in the encoder; translators type them normally.

## Names (2026-10-16)

18. **Name glossary**: assumed. `glossary/impact_names.tsv` holds every unit, pilot, weapon and
    speaker name (1,793). Sources: official SRW / show English 958, our OG canon 99, Akurasu 69,
    **proposals 667** (rows with `source` = proposal, many with a note on what was unsure: minor
    villains, Machine Robo and Daitarn 3 enemies, Einst attack readings, G Gundam moves kept in
    romaji). Fix any row and re-run `tools/names_impact.py apply` (the build then uses it).
19. **Military ranks**: assumed. One series rule for every faction, as in our 2nd OG and Moon
    Dwellers patches: 少尉/中尉 Lieutenant, 大尉 Captain, 少佐 Major, 中佐 Lieutenant Colonel,
    大佐 Colonel; never "Ensign" or "Lieutenant Commander" (the Gundam dubs differ; say if you
    prefer the dub ranks). A post-pass unifies translators' variants.
20. **Database pages condensed**: assumed for now. Description pages keep the Japanese row count
    at 400 px per row, so some English is condensed. To check in game: if the database window
    holds more rows or scrolls, the limit will be raised and those pages expanded.

## Picture text (2026-10-17)

21. **Opening / ending crawls**: done (assumed wording). All 25 ROLLPACK pages redrawn in English
    (`textures/roll.json`, Times New Roman); rows that were already English in the original
    (credits, THE END, episode titles) keep their art.
21a. **Part title cards** (R_TIT: 地上激動篇 / 宇宙激震篇 / 銀河決戦篇): done, using the menu names
    "Earth Upheaval Arc", "Space Tremor Arc", "Galactic Battle Arc". Each card is two sprites
    (a 448-px strip and the 篇 cell); the title is drawn across both, and part 3 gets its own cell
    (it shared part 2's) via a 4-byte patch to the sprite table in the ELF. Part 1 seen in game.
22. **Episode numbers**: assumed. 第N話 shows as "EP. N" and 最終話 as "FINAL" (STIT000 atlas).
23. **Battle console atlas** (CSL_PACK): done. The sheet is 1024x256 8-bit (the game samples it
    1024 wide; viewed 512 wide it looked like overlapping images). Label rects come from the
    game's sprite records. Badges 攻反防避援同戦 -> ATK CTR DEF EVA SUP DUO BTL (assumed: 同 =
    simultaneous attack -> "DUO", 戦 -> "BTL"); 同時攻撃 -> "Dual Attack" (assumed), support labels
    shortened to "Sup. Attack" / "Sup. Defense" to fit 96 px; skill labels use the game-text
    terms (Afterimage, Parry, Shin Mach Special, ...). The 24 series banners use official English
    series titles. ATK badge seen in game.
24. **Title logo** (TITLPACK and the title-screen backdrop): done, both seen in game. Our own
    "SUPER ROBOT WARS" lettering replaces the katakana wordmark; the IMPACT art is kept. The
    backdrop behind PRESS ANY BUTTON is a separate picture with the logo painted in: IMNBG.BIN
    entry 76 (the title calls `load_im(0x4C)`), 640x448 8-bit. `tools/titlbg.py` cuts the
    katakana out (where TITLPACK texture 3 differs from the standalone IMPACT, at 1:1 offset
    (85, -290)), restores the IMPACT art under it, inpaints the earth/space around it, and draws
    the same English wordmark with a dark outline like the painted logo's (assumed style). Pixels
    keep the picture's own palette. Patch file for this fix assumed to be named v0.1.1 (v0.1 is
    already published); publishing it is evilgouki's call.
25. **Staff credits** (SROLPACK): done (assumed). Roles in standard English credit titles; names
    romanized in Western order, Hepburn without macrons; established readings for well-known
    staff; character names as in the glossary; cast lines "Character - Actor". 104 readings are
    uncertain (kanji names with several possible readings) and are listed in the private work
    notes; corrections welcome. Lines that straddle a page seam are laid out on the whole roll.
    Not yet seen in game (needs the ending).
