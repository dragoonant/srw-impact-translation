# Name brief: Super Robot Taisen Impact (PS2, 2002), Japanese -> English

You are one of several translators working in parallel on a fan translation of SRW Impact
(the "Classic" continuity: Divine Crusaders, Guests/Inspectors, Masaki and Shu, plus licensed
series such as Mobile Suit Gundam 0079/0080/0083/Z/ZZ/CCA/F91/V, G Gundam, Gundam W?, Mazinger Z,
Great Mazinger, UFO Robo Grendizer, Getter Robo / G / Shin Getter, Combattler V, Voltes V,
Daimos, Daitarn 3, Zambot 3, Dancougar, Dunbine, L-Gaim, Nadesico, Gunbuster, Godmars,
Dangaioh, Baxinger, Layzner, Gaiking? and more, and Banpresto originals such as Kyosuke Nanbu,
Excellen Browning, Alteisen, Weissritter, the Einst).

## Your job

Translate every item in your assigned request file `nNN.json` (folder
`~/srwimpact-work\xl\names\`). Write `nNN.out.json` in the same folder:

```json
{"translations": [{"id": "<id copied exactly>", "en": "<English>", "source": "official|og|show|akurasu|proposal", "note": "optional short note"}]}
```

Every id exactly once, valid UTF-8 JSON. Work only on your file. Scratch files only in
`~/srwimpact-work\xl\work\names-nNN\`.

## Canon order (the project owner decided this)

1. **Banpresto originals** (Masaki Andoh, Shu Shirakawa, Lune, Bian Zoldark, Gilliam Yeager,
   Kyosuke, Excellen, the Einst, Guest/Inspector characters, Huckebein, Gespenst, Granzon,
   Cybuster, Valsione...): use the established English of the OG fan patches (OGs / 2nd OG
   style): short vowels (Kyosuke, Ryusei, Shu, Kota), "Andoh", "Zoldark", "Lüne" with ü,
   German umlauts where the original is German (Wildwürger, Sänger, Rätsel). Kai -> "Custom",
   Shiki -> "Type".
2. **Licensed series:** the official English of Bandai Namco's English Super Robot Wars
   releases (SRW V, X, T, 30) when you know it; otherwise the series' own official English
   release/romanization (e.g. Amuro Ray, Char Aznable, Quattro Bajeena, Bright Noa, Kamille
   Bidan, Judau Ashta, Koji Kabuto, Tetsuya Tsurugi, Duke Fleed, Ryoma Nagare, Hayato Jin,
   Musashi Tomoe, Benkei Kuruma, Hyoma Aoi, Kenichi Go, Kazuya Ryuzaki, Banjo Haran, Shinobu
   Fujiwara, Sara Yuki, Masato Shikibu, Ryo Shiba, Akito Tenkawa, Yurika Misumaru, Ruri Hoshino,
   Domon Kasshu, Show Zama, Noriko Takaya, Kazumi Amano). Then Akurasu-wiki romanization, then
   your own proposal.
3. Where an earlier choice is unsure, still give one form and add `"note"`.

## Form

- Pilot full names: given name first, Western order, as the official English writes them
  (`シャア＝アズナブル` -> `Char Aznable`; `＝` and `・` between name parts become a space).
  Japanese-style names also given name first (`兜甲児` -> `Koji Kabuto`).
- `pilot_short` / `speaker`: the short form the game shows in name rows and speaker lines,
  usually the given name (`甲児` -> `Koji`, `アムロ` -> `Amuro`). Speakers can also be generic
  ("連邦兵" -> "Federation Soldier", "？？？" -> "???", "オペレーター" -> "Operator",
  "兵士Ａ" -> "Soldier A"). Keep a speaker consistent with the same character's pilot_short.
- Units: Title Case, keep model codes as written (`ガンダムＮＴ－１アレックス` -> `Gundam NT-1 Alex`,
  `ゲシュペンスト` -> `Gespenst`, `ザク改` -> `Zaku II Kai`? -> follow official English: "Zaku II
  FZ" / "Zaku Kai" as the official SRW English writes it). Mobile suit codes from the shows.
- Weapons/attacks: Title Case. Use official SRW English attack names (`ロケットパンチ` ->
  `Rocket Punch`, `ブレストファイヤー` -> `Breast Fire`, `ゲッタービーム` -> `Getter Beam`,
  `ビーム・サーベル` -> `Beam Saber`, `頭部バルカン` -> `Head Vulcan`). Kanji attack names: the
  official English if known, otherwise translate or keep the well-known romaji as the official
  releases do. Keep suffixes such as `（騎乗）` as a short English tag, e.g. "(Mounted)".
- ASCII only plus ü ä ö é where canon needs them. No full-width characters, no `「」`.
  Fit `max_bytes` (1 byte per ASCII character). Shorten sensibly if needed (e.g. drop "Mobile
  Suit"), and note it.
- The same Japanese in different categories must agree (a pilot's short name, speaker form and
  the given name in the full name).

## Finish

Check: your JSON loads, every id from your file appears once, no `en` is empty, every `en` is
ASCII (plus ü ä ö é) and within `max_bytes`. Then reply with one line:
`done: nNN, <count> names` (and anything you were unsure about, briefly).
