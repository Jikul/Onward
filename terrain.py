"""Ground elevation from the free AWS Terrain Tiles (Terrarium PNGs, Mapzen/Tilezen, SRTM and other sources).

One 256 px tile at zoom 11 covers about 15 km with ~75 m pixels, so a whole route needs a handful of downloads
instead of one web request per point. Tiles are kept on disk, so a second look at the same area is free."""
import io
import math
import os
import threading
import urllib.request

import data

Z = 11
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
DIR = os.path.join(data.DATA, "terrain_tiles")
_mem, _lock = {}, threading.Lock()
_failed = {}


def _tile(x, y):
    key = (x, y)
    with _lock:
        if key in _mem:
            return _mem[key]
    path = os.path.join(DIR, str(Z), str(x), f"{y}.png")
    raw = None
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = f.read()
    else:
        raw = data.http_get(URL.format(z=Z, x=x, y=y), timeout=20)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(raw)
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    px = im.load()
    with _lock:
        if len(_mem) > 400:
            _mem.clear()
        _mem[key] = px
    return px


def _height(px, i, j):
    r, g, b = px[min(255, max(0, i)), min(255, max(0, j))]
    return r * 256 + g + b / 256 - 32768


def elevation_m(lat, lon):
    """Highest of the four pixels around the point (a little conservative for terrain clearance)."""
    n = 2 ** Z
    lat = max(-85.0, min(85.0, lat))
    xf = (lon + 180) / 360 * n
    yf = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    x, y = int(xf), int(yf)
    px = _tile(x % n, y)
    i, j = int((xf - x) * 256), int((yf - y) * 256)
    h = max(_height(px, i, j), _height(px, i + 1, j), _height(px, i, j + 1), _height(px, i + 1, j + 1))
    return max(h, 0.0)  # the sea is zero


def elevations_m(pts):
    """[(lat, lon)] -> metres, raises if the tiles can't be had (the caller falls back to the web services)."""
    return [elevation_m(a, b) for a, b in pts]
