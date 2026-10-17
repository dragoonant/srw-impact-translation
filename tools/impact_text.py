"""English text -> SRW Impact game bytes (for the proportional renderer in vwf_impact.py).

Worksheet English is plain text with these conventions:
  @          row break (story/battle rows; the engine's own marker)
  {cY} {cG} {cS} ...   colour codes, {%8} {&8} number codes, {s52} space codes: copied as
             raw ASCII exactly where the Japanese has them (`jp_codes` lists them)
Everything else is stored 1 byte per character:
  ASCII letters, digits, space and most punctuation as themselves;
  ! # $ % &  as 0x1F 0x1E 0x1D 0x1C 0x1B (their ASCII bytes are engine control codes);
  'c' before B..Y and 's' before two digits as 0x1A / 0x19 (so they are not read as codes);
  ü ä ö é Ü Ö Ä è à as 0x18..0x10 (composed glyphs);
  typographic quotes/dashes/ellipsis are folded to ASCII (' " - ...).
Characters with no glyph raise ValueError so the checker can report them.
"""
import re

CODE = re.compile(r"c[B-Y]|[%&$#][0-9]|s[0-9]{2}")
TOKEN = re.compile(r"\{(c[B-Y]|[%&$#][0-9]|s[0-9]{2})\}")
SYMBOL = {"!": 0x1F, "#": 0x1E, "$": 0x1D, "%": 0x1C, "&": 0x1B,
          "ü": 0x18, "ä": 0x17, "ö": 0x16, "é": 0x15, "Ü": 0x14, "Ö": 0x13, "Ä": 0x12, "è": 0x11, "à": 0x10}
FOLD = {"’": "'", "‘": "'", "“": '"', "”": '"', "—": "--", "–": "-", "…": "...", "　": " ",
        "～": "~", "！": "!", "？": "?", "♪": "~"}
GLYPH_BYTES = {v: k for k, v in SYMBOL.items()}
GLYPH_BYTES.update({0x1A: "c", 0x19: "s"})


def jp_codes(jp):
    """Control codes in a Japanese string, in order (as worksheet tokens)."""
    return ["{" + m.group() + "}" for m in CODE.finditer(jp)]


def en_codes(en):
    return ["{" + m.group(1) + "}" for m in TOKEN.finditer(en)]


def to_game(en):
    out = bytearray()
    pos = 0
    for m in list(TOKEN.finditer(en)) + [None]:
        seg = en[pos:m.start() if m else len(en)]
        for c in "".join(FOLD.get(ch, ch) for ch in seg):
            out.append(0)              # placeholder, fixed below
            out[-1] = _byte(c)
        if m:
            out += m.group(1).encode("ascii")
            pos = m.end()
    # disambiguate letters that would read as control codes
    i = 0
    while i < len(out):
        b = out[i]
        if b == ord("c") and i + 1 < len(out) and 0x42 <= out[i + 1] <= 0x59 and not _is_token_at(en, out, i):
            out[i] = 0x1A
        elif b == ord("s") and i + 2 < len(out) and _digit(out[i + 1]) and _digit(out[i + 2]) \
                and not _is_token_at(en, out, i):
            out[i] = 0x19
        i += 1
    return bytes(out)


def _digit(b):
    return 0x30 <= b <= 0x39


_token_spans = {}


def _is_token_at(en, out, i):
    """True if out[i] starts a raw control code that came from a {token}."""
    spans = _spans(en)
    return i in spans


def _spans(en):
    key = en
    if key in _token_spans:
        return _token_spans[key]
    starts, n, pos = set(), 0, 0
    for m in TOKEN.finditer(en):
        seg = "".join(FOLD.get(ch, ch) for ch in en[pos:m.start()])
        n += len(seg)
        starts.add(n)
        n += len(m.group(1))
        pos = m.end()
    _token_spans[key] = starts
    return starts


def _byte(c):
    if c in SYMBOL:
        return SYMBOL[c]
    o = ord(c)
    if c == "@" or 0x20 <= o < 0x7F:
        return o
    raise ValueError(f"no glyph for {c!r}")


def to_display(b):
    """Game bytes -> readable text (for checks)."""
    return "".join(GLYPH_BYTES.get(x, chr(x)) if x < 0x80 else "�" for x in b)
