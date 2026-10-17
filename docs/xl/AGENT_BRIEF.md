# Translator brief: Super Robot Taisen Impact (PS2, 2002), Japanese -> English

You are one of several translators working in parallel on an English fan patch of SRW Impact,
for its owner (credited as evilgouki). Work only on the request files you were assigned.

## Files

- Request files `rNNNNN.json` in your assigned folder: `glossary` (Japanese -> required English
  for names and terms in that file) and `items`. Each item has `id`, `jp`, `kind`, limits, and
  depending on the kind: `speaker` [Japanese, English], `page` ("2/4" = page 2 of a 4-page
  speech), `context_before` (the preceding Japanese lines of the scene), `pilot_id`, `part`.
- For each assigned `rNNNNN.json` write `rNNNNN.out.json` in the same folder:
  `{"translations":[{"id":"<id copied exactly>","en":"<English>"}]}`. Every id exactly once.
  Valid UTF-8 JSON (escape `"` as `\"`).
- Scratch files ONLY in `~/srwimpact-work\xl\work\<your first file>-<your last file>\`.
  Never write any other `.out.json`.

## Check before you finish (required)

```
python -I "<repo>/tools/xl_impact.py" check <FOLDER> r00012 r00013 ...
```
Fix every reported problem and re-run until it says 0 problems.

## What the English must look like

**Story lines** (`kind` dialogue / thought / page / system): the game shows the speaker's name on
its own row (the build adds it), then the body. Write ONLY the body, as one paragraph: no
speaker name, no `「」`, no `@`, no leading spaces. The build word-wraps it into rows of
`row_px` pixels; it must fit in `max_rows` rows (2 for dialogue): about 70-75 characters in all.
Be concise and natural: keep the meaning, drop filler. Thoughts （…） -> (parentheses).
A `page` item is one window of a longer speech: translate each page so the speech reads
continuously across pages, keep each page's share of the content, and do not merge or move
content between pages.

**Battle quotes** (`kind` quote): same as dialogue (no 「」, one paragraph, max 2 rows); short and
punchy. Many quotes are shared between pilots: keep them speaker-neutral when the Japanese is.

**Menus and messages** (`part` msg): `max_px` labels must fit their pixel width (one row, no
`@`); messages with `max_rows` are wrapped by the build like story text. **Database pages**
(`part` desc): one paragraph per item, wrapped by the build into `max_rows` rows.

**In-place strings** (`max_bytes`): must fit in that many bytes (1 byte per ASCII character).
Abbreviate sensibly if needed.

**Engine codes** in `jp` appear as `{cY}`, `{cG}`, `{cS}` (colour), `{%8}`, `{&8}` (numbers),
`{s52}` (spacing): copy each one into the English exactly once, in the same order, where it
belongs in the sentence (`{%8}` stands for a number, `{cY}` colours what follows).

**Voice actors** (`kind` voice_actor): romanize in Western order, Hepburn, no macrons
(山寺　宏一 -> Koichi Yamadera).

## Style (series rules, decided)

- Natural, contraction-heavy English that keeps each character's voice (Shinobu brash and
  rough, Ryo calm, Sara sharp, Kouji hot-blooded, Amuro measured, Char/Quattro formal,
  Domon intense, Akito reluctant, Yurika bubbly, Ruri deadpan "...Idiot."), Kyosuke terse,
  Excellen playful.
- No honorifics (-san, -sama, -kun, -chan, -dono) except "Rishu-sensei". 様 for villains'
  lords -> "Lord"/"Lady"/"Master" when used as a title, otherwise drop. Ranks in full
  ("Lieutenant", "Captain", "Commander"), never abbreviated.
- `……` -> `...`, `――` -> `--`, `！！` -> `!!` (never more than two), `！？` -> `!?`.
  A line that opens with `！` alone (startle) -> `...!`.
- ASCII only (plus ü ä ö é where a glossary name uses them). No full-width characters, no
  curly quotes, no `<` or `>`, never a literal `@`.
- Names and terms: use the `glossary` forms exactly. In dialogue characters use short forms
  (given names) as the Japanese does.
- Don't add or drop information. No translator notes. Leave gender unspecified where the
  Japanese does.
- Identical Japanese in your files: translate identically.
- Attack names shouted in quotes: use the glossary weapon name if present; otherwise Title Case
  English (official SRW English form if you know it).

## Settled terms (use even if a file's glossary omits them)

| Japanese | English |
|---|---|
| 地球連邦軍 / 連邦軍 / 連邦 | Earth Federation Forces / Federation Forces / the Federation |
| ティターンズ | the Titans |
| エゥーゴ | the AEUG |
| アクシズ / ネオ・ジオン | Axis / Neo Zeon |
| ジオン / ジオン残党 | Zeon / Zeon remnants |
| ディバイン・クルセイダーズ (ＤＣ) | the Divine Crusaders (DC) |
| ゲスト / インスペクター | the Guests / the Inspectors |
| アインスト | the Einst |
| 機械獣 / 戦闘獣 / 恐竜帝国 / 百鬼帝国 | Mechanical Beast / Battle Beast / the Dinosaur Empire / the Hyakki Empire |
| ミケーネ帝国 / ベガ星連合軍 | the Mykene Empire / the Vega Star Federation |
| ムゲ・ゾルバドス帝国 | the Muge Zorbados Empire |
| 木星トカゲ | the Jovian Lizards |
| ガンダムファイト | Gundam Fight |
| 獣戦機隊 | the Cyber Beast Force |
| 光子力研究所 | the Photon Power Laboratory |
| 早乙女研究所 | the Saotome Laboratory |
| ネルガル重工 | Nergal Heavy Industries |
| アーガマ / ラー・カイラム / ナデシコ | the Argama / the Ra Cailum / the Nadesico |
| ロンド・ベル | Londo Bell |
| モビルスーツ / モビルアーマー | mobile suit / mobile armor |
| スーパーロボット | super robot |
| 精神コマンド | Spirit Commands |
| 気力 | Will |
| 底力 / 援護攻撃 / 援護防御 / 統率 / カウンター / ２回行動 | Resolve / Support Attack / Support Defense / Command / Counter / Double Act |
| インターミッション | Intermission |
| 長官 | Commander (head of an organisation, e.g. Commander Hazuki) |
| 艦長 | Captain |
| 博士 | Dr. / Doctor |

(If a file's glossary gives a different form for one of these, the glossary wins.)

## Finish

When every assigned file has an `.out.json` and the checker reports 0 problems, reply with one
line: `done: <first>-<last>, <files> files, <entries> entries, 0 problems` (or what you could not
fix, briefly).
