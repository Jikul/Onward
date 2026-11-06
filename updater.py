"""Updates from GitHub: check version.json, download the new code, keep a copy of the old one, restart.

Only program files are replaced. Your data folder (career, journal, photos, settings, caches) is never touched.
"""
import io
import json
import os
import shutil
import time
import urllib.request
import zipfile

import data
import version

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUPS = os.path.join(data.DATA, "backups")
KEEP = {"data", ".git", "__pycache__", "dist", "build"}   # never overwritten or removed
RESTART_CODE = 3                                         # start.bat starts Onward again on this exit code


def _parse(v):
    out = []
    for part in str(v).split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out + [0] * (3 - len(out)))


def newer(a, b):
    return _parse(a) > _parse(b)


class Updater:
    def __init__(self, settings, log=print):
        self.settings, self.log = settings, log
        self.status = {"current": version.VERSION, "latest": None, "notes": [], "available": False, "checked": None,
                       "error": None, "busy": False, "frozen": data.FROZEN, "backups": self.backups()}

    # ---------- where from ----------
    def repo(self):
        return (self.settings.get("update_repo") or version.DEFAULT_REPO).strip().strip("/")

    def _get(self, url, accept=None, timeout=30):
        h = dict(data.HEADERS)
        tok = (self.settings.get("update_token") or "").strip()
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        if accept:
            h["Accept"] = accept
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout, context=data.SSL_CTX) as r:
            return r.read()

    def _manifest(self):
        repo, br = self.repo(), version.BRANCH
        if (self.settings.get("update_token") or "").strip():  # private repository: go through the API
            raw = self._get(f"https://api.github.com/repos/{repo}/contents/version.json?ref={br}", accept="application/vnd.github.raw")
        else:
            raw = self._get(f"https://raw.githubusercontent.com/{repo}/{br}/version.json?t={int(time.time())}")
        return json.loads(raw)

    def _zip(self):
        repo, br = self.repo(), version.BRANCH
        if (self.settings.get("update_token") or "").strip():
            return self._get(f"https://api.github.com/repos/{repo}/zipball/{br}", timeout=120)
        return self._get(f"https://codeload.github.com/{repo}/zip/refs/heads/{br}", timeout=120)

    # ---------- check ----------
    def check(self):
        st = self.status
        try:
            m = self._manifest()
            st.update(latest=m.get("version"), notes=m.get("notes") or [], date=m.get("date"), error=None,
                      available=newer(m.get("version", "0"), version.VERSION), checked=time.strftime("%Y-%m-%d %H:%M"))
            if st["available"]:
                self.log(f"Onward {m['version']} is available (you have {version.VERSION}).")
        except Exception as e:
            msg = f"Couldn't find Onward at github.com/{self.repo()}." if "404" in str(e) else f"Couldn't check for updates ({e})."
            st.update(error=msg, checked=time.strftime("%Y-%m-%d %H:%M"))
        return st

    # ---------- install ----------
    def backups(self):
        if not os.path.isdir(BACKUPS):
            return []
        return sorted(os.listdir(BACKUPS), reverse=True)

    def _backup(self):
        dst = os.path.join(BACKUPS, f"{version.VERSION}-{time.strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(PROGRAM_DIR):
            if name in KEEP or name.startswith("."):
                continue
            src = os.path.join(PROGRAM_DIR, name)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dst, name), ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, dst)
        for old in self.backups()[3:]:  # keep the last three
            shutil.rmtree(os.path.join(BACKUPS, old), ignore_errors=True)
        return dst

    def _install_tree(self, root):
        for name in os.listdir(root):
            if name in KEEP or name.startswith("."):
                continue
            src, dst = os.path.join(root, name), os.path.join(PROGRAM_DIR, name)
            if os.path.isdir(src):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    def apply(self):
        """Download and install the latest version. Returns an error message or None (then restart)."""
        if data.FROZEN:
            return f"This is the packaged app: download the new version from https://github.com/{self.repo()}/releases"
        if os.path.isdir(os.path.join(PROGRAM_DIR, ".git")):
            return "This copy of Onward is a git checkout. Update it with git pull instead."
        self.status["busy"] = True
        try:
            blob = self._zip()
            z = zipfile.ZipFile(io.BytesIO(blob))
            tmp = os.path.join(data.DATA, "update_tmp")
            shutil.rmtree(tmp, ignore_errors=True)
            z.extractall(tmp)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            if not os.path.exists(os.path.join(root, "server.py")):
                return "The download doesn't look like Onward. Nothing was changed."
            self.log(f"Backed up the current version to {self._backup()}")
            self._install_tree(root)
            shutil.rmtree(tmp, ignore_errors=True)
            self.log("Update installed. Restarting Onward...")
            return None
        except Exception as e:
            return f"The update failed ({e}). Nothing was changed, or the previous version is in data\\backups."
        finally:
            self.status["busy"] = False

    def rollback(self):
        b = self.backups()
        if not b:
            return "There's no previous version to go back to."
        try:
            self._install_tree(os.path.join(BACKUPS, b[0]))
            shutil.rmtree(os.path.join(BACKUPS, b[0]), ignore_errors=True)
            self.log(f"Went back to {b[0].split('-')[0]}. Restarting Onward...")
            return None
        except Exception as e:
            return f"Couldn't restore the previous version ({e})."
