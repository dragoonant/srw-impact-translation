"""Press keys, take a PCSX2 screenshot, and copy it to ~/srwimpact-work/ref/shots.

  pcsx2_shot.py NAME ["O,wait2,DOWN"]   -> shots/NAME.png and a 640x480 preview shots/NAME_s.png

The snaps folder sits in OneDrive, which briefly locks new files, so the copy retries.
"""
import os
import shutil
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcsx2_input as k

SHOTS = os.path.join(os.path.expanduser("~"), "srwimpact-work", "ref", "shots")


def grab(name, keys=""):
    os.makedirs(SHOTS, exist_ok=True)
    if keys:
        k.run(keys)
    src = k.shot()
    dst = os.path.join(SHOTS, name + ".png")
    for _ in range(40):
        try:
            shutil.copyfile(src, dst)
            break
        except OSError:
            time.sleep(0.25)
    else:
        raise RuntimeError("screenshot stayed locked: " + src)
    im = Image.open(dst)
    im.thumbnail((640, 480))
    small = os.path.join(SHOTS, name + "_s.png")
    im.save(small)
    return small


if __name__ == "__main__":
    print(grab(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""))
