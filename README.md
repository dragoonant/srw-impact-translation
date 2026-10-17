# Super Robot Taisen Impact: English translation

An English translation patch for *Super Robot Taisen Impact* (PlayStation 2, 2002, SLPS-25103,
Limited Edition disc), by **evilgouki**. It follows the team's *2nd Super Robot Wars OG*,
*OG Gaiden* and *The Moon Dwellers* patches, so Banpresto's original characters read the same
across all of them.

> **Status: v0.1, public beta.** All game text is translated and the patch plays from the title
> screen into the first stage. **No human editing pass has been done.** The translation was
> machine-assisted (AI) and checked automatically for fit, line breaks and consistent names;
> nobody has read the script end to end. Expect awkward lines, occasional mistranslations and
> inconsistent terms. Reports are very welcome (see [Reporting problems](#reporting-problems)).

## What's translated

| Part | Entries |
|---|---|
| Story and stage scripts | 34,723 |
| Battle quotes (372 pilots) | 19,908 |
| Unit, pilot and weapon names, voice-actor credits | 3,901 |
| Menus and system messages | 1,599 |
| Database pages | 1,267 |
| Executable strings and terrain names | 829 |

English is drawn proportionally with the game's own Latin letters, through a small patch to the
game's text layout routine. Umlauts (Lüne, Wildwürger) are composed into spare font cells. The
105 stage title cards are redrawn in English.

## How to apply

You need your own copy of the Japanese **Limited Edition** disc as an ISO, matching:

| | |
|---|---|
| Size | 4,220,256,256 bytes |
| MD5 | `c86e93496b5bc923df2df8917050cd3c` |
| SHA-1 | `0b93c19ae88ddfb01b9ede1f7f85caf0a72dd03d` |

Download `SRW_Impact_EN_v0.1.xdelta` from [Releases](../../releases) and apply it with
[xdelta UI](https://www.romhacking.net/utilities/598/), Delta Patcher, or xdelta3:

```
xdelta3 -d -s "Super Robot Taisen Impact [Limited Edition] [J].iso" SRW_Impact_EN_v0.1.xdelta SRW_Impact_EN_v0.1.iso
```

The patched ISO has MD5 `199a1796b93190bed5b426220175cc34`. Play it in **PCSX2** (tested with
2.8.2). Real PS2 hardware and the standard (non-Limited) edition have not been tested.

## Known issues

- **No editing pass** (see above). Names new to this patch series are partly our proposals
  (`glossary/impact_names.tsv`, rows marked `proposal`).
- **Still Japanese (pictures, not text):** the logo on the title-screen backdrop (behind PRESS
  ANY BUTTON; the logo fly-in before it is English) and possibly some other menu graphics. The
  crawls, part title cards, episode numbers, battle-screen badges / labels / series banners, the
  logo fly-in and the staff credits are in English.
- Staff names in the credits are our romanizations; some kanji readings are guesses.
- Played in PCSX2 from a new game through the opening scenes into the first stage: story and map
  dialogue, the map and unit menus, the Spirit screen, the pre-battle screen and battle quotes.
  **The rest of the game has only been checked by tools**, including the intermission menus,
  the database, the stage title cards, the ending crawls and the staff credits in game. Some screens may still have clipped or
  overlapping text.
- Database pages are condensed to the Japanese page sizes; some details are shortened.
- A few 7-byte terrain names are abbreviated (e.g. "DmgWall", "Tobikge").

## Reporting problems

Open an [issue](../../issues) with a screenshot (PCSX2: F8), where you are (stage, or the menu
path), and what is wrong: untranslated text, clipped text, a wrong name or a bad line. Suggested
rewrites are just as welcome.

## Building from source

The repository holds the tools, the English text and the glossary, but **no game data and no
Japanese text**. To build an ISO yourself (Windows; Python 3.12 with Pillow):

1. Extract your disc: `python tools/iso_tool.py extract YOUR.iso ~/srwimpact-work/pristine/disc`
2. Put the Japanese source text back into the worksheets from your disc:
   `python tools/hydrate.py fill ~/srwimpact-work/pristine/disc`
3. Put your ISO in the repository folder under its original name, then run `python tools/build.py`
   (writes `~/srwimpact-work/build/impact_en.iso`).

See [docs/](docs/) for the file formats and the renderer patch.

## Credits

- **evilgouki**: project lead, translation direction, testing.
- Tools, reverse engineering and the AI-assisted first translation pass: Claude (Anthropic).
- Names of Banpresto originals follow the community canon of the OGs and 2nd OG fan patches;
  licensed series follow the official English Super Robot Wars releases where possible. Terms
  researched on the [Akurasu wiki](https://akurasu.net/wiki/Super_Robot_Wars) (see
  `glossary/sources.md`).
- Bandai Namco owns the game. Buy it.

## License

The tools and documentation in this repository are MIT licensed (`LICENSE`). The game, its
text and its data belong to their owners; this repository contains no game data.
