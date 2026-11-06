"""Screenshots taken during a leg: found in the usual capture folders, copied into Onward and placed on the map."""
import glob
import os
import shutil
import time

import data

PHOTO_DIR = os.path.join(data.DATA, "photos")
EXTS = (".png", ".jpg", ".jpeg", ".webp")
MSFS_STEAM_APPS = ("2537590", "1250410")  # MSFS 2024, MSFS 2020

try:
    from PIL import Image
except Exception:  # thumbnails are optional
    Image = None


def _steam_roots():
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(winreg.QueryValueEx(k, name)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam", r"D:\Steam", r"E:\Steam", r"E:\SteamLibrary"]
    return [os.path.normpath(r) for r in roots]


def default_folders():
    """Where Windows, Steam and MSFS usually put screenshots."""
    home = os.path.expanduser("~")
    out = [os.path.join(home, "Videos", "Captures"),            # Xbox Game Bar (Win+Alt+PrtScn)
           os.path.join(home, "Pictures", "Screenshots"),       # Win+PrtScn and Snipping Tool
           os.path.join(home, "OneDrive", "Pictures", "Screenshots"),
           os.path.join(home, "Pictures", "Microsoft Flight Simulator 2024")]
    for root in _steam_roots():
        for app in MSFS_STEAM_APPS:
            out += glob.glob(os.path.join(root, "userdata", "*", "760", "remote", app, "screenshots"))
    seen, res = set(), []
    for p in out:
        k = os.path.normcase(p)
        if k not in seen and os.path.isdir(p):
            seen.add(k)
            res.append(p)
    return res


def folders(settings):
    extra = [l.strip().strip('"') for l in (settings.get("photo_folders") or "").splitlines() if l.strip()]
    res = default_folders()
    for p in extra:
        if os.path.isdir(p) and os.path.normcase(p) not in {os.path.normcase(x) for x in res}:
            res.append(p)
    return res


def scan(dirs, since, known):
    """New image files modified after `since` (top level of each folder only: Steam keeps its own thumbnails below)."""
    found = []
    for d in dirs:
        try:
            for e in os.scandir(d):
                if not e.is_file() or not e.name.lower().endswith(EXTS):
                    continue
                if e.path in known:
                    continue
                m = e.stat().st_mtime
                if m >= since:
                    found.append((m, e.path))
        except OSError:
            continue
    return sorted(found)


def store(src, leg_id, idx):
    """Copy a screenshot into data/photos/<leg>/ and make a small thumbnail. Returns (file, thumb) relative names."""
    folder = os.path.join(PHOTO_DIR, leg_id)
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    name = f"{idx:02d}{ext}"
    dst = os.path.join(folder, name)
    for _ in range(10):  # the game may still be writing the file
        try:
            size = os.path.getsize(src)
            time.sleep(0.4)
            if size and size == os.path.getsize(src):
                break
        except OSError:
            time.sleep(0.4)
    shutil.copy2(src, dst)
    thumb = None
    if Image:
        try:
            with Image.open(dst) as im:
                im = im.convert("RGB")
                im.thumbnail((640, 640))
                thumb = f"{idx:02d}_t.jpg"
                im.save(os.path.join(folder, thumb), "JPEG", quality=82)
        except Exception:
            thumb = None
    return f"{leg_id}/{name}", (f"{leg_id}/{thumb}" if thumb else f"{leg_id}/{name}")
