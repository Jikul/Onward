"""A few sentences and a photo about a sight, from Wikipedia. Cached on disk."""
import difflib
import json
import os
import re
import threading
import time
import urllib.parse

import data

CACHE = os.path.join(data.DATA, "wiki_cache.json")


class Wiki:
    def __init__(self, log=print):
        self.log = log
        self.lock = threading.Lock()
        try:
            with open(CACHE, encoding="utf-8") as f:
                self.cache = json.load(f)
        except Exception:
            self.cache = {}
        self.backoff_until = 0

    def _get(self, url):
        return json.loads(data.http_get(url, timeout=15))

    def _save(self):
        try:
            with open(CACHE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def _norm(s):
        s = (s or "").lower()
        s = re.sub(r"\(.*?\)", "", s)
        return re.sub(r"[^\w ]", " ", s).strip()

    def _summary(self, lang, title):
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'))}"
        d = self._get(url)
        if d.get("type") == "disambiguation" or not d.get("extract"):
            return None
        extract = d["extract"]
        sentences = re.split(r"(?<=[.!?])\s+", extract)
        short = " ".join(sentences[:3])
        return {"title": d.get("title", title), "extract": short[:600],
                "thumb": (d.get("thumbnail") or {}).get("source"),
                "url": ((d.get("content_urls") or {}).get("desktop") or {}).get("page"), "lang": lang}

    def lookup(self, name, lat=None, lon=None, wiki_tag=""):
        key = f"{name}|{round(lat or 0, 3)}|{round(lon or 0, 3)}"
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        if time.time() < self.backoff_until:
            return {"error": "Wikipedia is busy right now. Try again in a minute."}
        result = None
        try:
            # 1. an explicit wikipedia tag from OpenStreetMap ("pt:Bom Jesus do Monte")
            if wiki_tag and ":" in wiki_tag:
                lang, title = wiki_tag.split(":", 1)
                if lang == "en":
                    result = self._summary("en", title)
                else:
                    ll = self._get(f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=langlinks&lllang=en&format=json&titles="
                                   + urllib.parse.quote(title))
                    en = None
                    for page in ll.get("query", {}).get("pages", {}).values():
                        for link in page.get("langlinks", []):
                            en = link.get("*")
                    result = self._summary("en", en) if en else self._summary(lang, title)
            # 2. articles near the spot whose title looks like the name
            if not result and lat is not None:
                gs = self._get("https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gsradius=3000&gslimit=20&format=json"
                               f"&gscoord={lat}|{lon}")
                best, score = None, 0.0
                n = self._norm(name)
                for g in gs.get("query", {}).get("geosearch", []):
                    t = self._norm(g["title"])
                    sc = difflib.SequenceMatcher(None, n, t).ratio()
                    if n and (n in t or t in n):
                        sc = max(sc, 0.8)
                    if sc > score:
                        best, score = g["title"], sc
                if best and score >= 0.55:
                    result = self._summary("en", best)
            # 3. a plain search by name
            if not result:
                os_ = self._get("https://en.wikipedia.org/w/api.php?action=opensearch&limit=1&format=json&search="
                                + urllib.parse.quote(name))
                if len(os_) > 1 and os_[1]:
                    cand = os_[1][0]
                    if difflib.SequenceMatcher(None, self._norm(name), self._norm(cand)).ratio() >= 0.6:
                        result = self._summary("en", cand)
        except Exception as e:
            msg = str(e)
            self.log(f"Wikipedia lookup for {name} failed: {msg[:100]}")
            if "429" in msg:
                self.backoff_until = time.time() + 60
            return {"error": "Couldn't reach Wikipedia right now."}
        result = result or {"none": True}
        with self.lock:
            self.cache[key] = result
            self._save()
        return result
