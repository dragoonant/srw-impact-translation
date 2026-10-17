"""Press through the game and take regular screenshots, then make contact sheets.

  pcsx2_autoplay.py TAG SECONDS [--keys O] [--every 4] [--gap 0.6]

Presses KEYS (comma list, cycled) every GAP seconds for SECONDS, screenshotting every EVERY
presses into ~/srwimpact-work/ref/shots/TAG_NNN.png, then writes TAG_sheet_K.png contact sheets
(20 shots each). Needs a PCSX2 test session (pcsx2_session.py begin).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcsx2_input as k
import pcsx2_shot as s
from PIL import Image


def main():
    a = sys.argv[1:]
    tag, seconds = a[0], float(a[1])
    opt = lambda n, d: a[a.index(n) + 1] if n in a else d
    keys = opt("--keys", "O").split(",")
    every, gap = int(opt("--every", 4)), float(opt("--gap", 0.6))
    shots, n, t0 = [], 0, time.time()
    while time.time() - t0 < seconds:
        k.run(keys[n % len(keys)])
        n += 1
        time.sleep(gap)
        if n % every == 0:
            try:
                shots.append(s.grab(f"{tag}_{len(shots):03d}"))
            except RuntimeError:
                pass
    for i in range(0, len(shots), 20):
        sheet = Image.new("RGB", (320 * 5, 240 * 4))
        for j, p in enumerate(shots[i:i + 20]):
            sheet.paste(Image.open(p).resize((320, 240)), ((j % 5) * 320, (j // 5) * 240))
        out = os.path.join(s.SHOTS, f"{tag}_sheet_{i // 20}.png")
        sheet.save(out)
        print(out)
    print(f"{n} presses, {len(shots)} shots")


if __name__ == "__main__":
    main()
