"""Start and end a scripted PCSX2 test session without disturbing evilgouki's own setup.

  pcsx2_session.py begin [ISO]   back up PCSX2.ini, snapshot the save-state and snaps folders,
                                 switch Pad1 to the keyboard profile, enable PINE, launch the ISO
  pcsx2_session.py end           close PCSX2, restore PCSX2.ini from the backup, copy new save
                                 states to ~/srwimpact-work/ref/sstates (originals stay put)
  pcsx2_session.py status

Refuses to begin while any PCSX2 is running (the user may be playing). Test states use slots
7-9 (`pine.py save 8`); the user's own slots 1-6 are never touched.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcsx2_pad

EXE = r"C:\Program Files\PCSX2\pcsx2-qt.exe"
INI = pcsx2_pad.INI
ROOT = os.path.dirname(os.path.dirname(INI))
SSTATES = os.path.join(ROOT, "sstates")
WORK = os.path.join(os.path.expanduser("~"), "srwimpact-work")
STATE = os.path.join(WORK, "ref", "session.json")
BACKUP = os.path.join(WORK, "ref", "PCSX2.ini.session-backup")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ISO = os.path.join(REPO, "Super Robot Taisen Impact [Limited Edition] [J].iso")


def pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq pcsx2-qt.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    return [int(l.split('","')[1]) for l in out.splitlines() if l.startswith('"pcsx2')]


def set_key(text, section, key, value):
    """Set key = value inside [section] (adds the key if missing)."""
    m = re.search(rf"^\[{re.escape(section)}\]\r?\n(.*?)(?=^\[|\Z)", text, re.M | re.S)
    body = m.group(1)
    if re.search(rf"^{re.escape(key)} = .*$", body, re.M):
        body2 = re.sub(rf"^{re.escape(key)} = .*$", f"{key} = {value}", body, flags=re.M)
    else:
        body2 = f"{key} = {value}\n" + body
    return text[:m.start(1)] + body2 + text[m.end(1):]


def begin(iso):
    if pids():
        sys.exit("PCSX2 is already running: not starting a test session (the user may be playing).")
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    shutil.copy2(INI, BACKUP)
    snap = {"sstates": sorted(os.listdir(SSTATES)), "time": time.time(), "iso": iso}
    json.dump(snap, open(STATE, "w"), indent=1)
    text = open(INI, encoding="utf-8", newline="").read()
    pre, _, post = pcsx2_pad.split(text)          # the whole INI is restored from BACKUP at end
    text = set_key(pre + pcsx2_pad.KEYBOARD + post, "EmuCore", "EnablePINE", "true")
    # uncompressed save states, so tools can read GS.bin / eeMemory.bin from the .p2s zip
    text = set_key(text, "EmuCore", "SavestateCompressionType", "0")
    open(INI, "w", encoding="utf-8", newline="").write(text)
    p = subprocess.Popen([EXE, "-fastboot", "--", os.path.normpath(iso)])
    print("launched PCSX2 pid", p.pid)


def end():
    for pid in pids():
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    for _ in range(40):
        if not pids():
            break
        time.sleep(0.25)
    if not os.path.exists(STATE):
        sys.exit("no session state: nothing to restore")
    snap = json.load(open(STATE))
    shutil.copy2(BACKUP, INI)
    new = sorted(set(os.listdir(SSTATES)) - set(snap["sstates"]))
    dst = os.path.join(WORK, "ref", "sstates")
    os.makedirs(dst, exist_ok=True)
    for n in new:
        shutil.copy2(os.path.join(SSTATES, n), dst)
    os.remove(STATE)
    print("restored PCSX2.ini; new save states copied to ref/sstates:", new)


def status():
    print("running:", pids(), "| session open:", os.path.exists(STATE))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "begin":
        begin(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_ISO)
    elif cmd == "end":
        end()
    else:
        status()
