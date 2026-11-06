"""Backup forecast: when Open-Meteo doesn't answer (it has a daily request limit), build the same answer from
MET Norway (api.met.no, free, worldwide). Surface values, cloud cover by layer, wind, fog and precipitation come
straight from MET Norway; the upper levels (temperature, humidity, wind and cloud by height) are worked out from
them with a standard atmosphere, so they are a simpler picture than Open-Meteo's model levels."""
import json
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import version

UA = {"User-Agent": f"Onward/{version.VERSION} github.com/onward-sim/Onward"}  # MET Norway asks apps to name themselves
LEVEL_Z = {1000: 110, 925: 760, 850: 1460, 700: 3010, 600: 4200, 500: 5570, 400: 7180}  # metres, standard atmosphere
MAX_POINTS = 64  # be kind to a free service: bigger grids just fail over to "not available"
_cache, _elev, _lock = {}, {}, threading.Lock()


def _get(url, timeout=20):
    import data
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout, context=data.SSL_CTX) as r:
        return r.read()


def _series(lat, lon):
    key = (round(lat, 2), round(lon, 2))
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < 1800:
            return hit[1]
    ts = json.loads(_get(f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={key[0]}&lon={key[1]}"))["properties"]["timeseries"]
    with _lock:
        _cache[key] = (time.time(), ts)
        if len(_cache) > 2000:
            _cache.clear()
    return ts


def _elevations(pts):
    todo = [p for p in {(round(a, 2), round(b, 2)) for a, b in pts} if p not in _elev]
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        try:
            res = json.loads(_get("https://api.opentopodata.org/v1/srtm90m?locations=" + "|".join(f"{a},{b}" for a, b in chunk)))["results"]
            for p, r in zip(chunk, res):
                _elev[p] = r.get("elevation") or 0
        except Exception:
            for p in chunk:
                _elev[p] = 0
        if i + 100 < len(todo):
            time.sleep(1.1)
    return [_elev.get((round(a, 2), round(b, 2)), 0) for a, b in pts]


def _wcode(sym):
    sym = sym or ""
    for word, code in (("thunder", 95), ("fog", 45), ("heavyrain", 65), ("sleet", 66), ("rain", 61), ("snow", 71)):
        if word in sym:
            return code
    return {"cloudy": 3, "partlycloudy_day": 2, "partlycloudy_night": 2, "fair_day": 1, "fair_night": 1}.get(sym, 0)


def _hourly(ts, elev_m, hours, kn):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    by = {t["time"][:13]: t["data"] for t in ts}
    temps = [t["data"]["instant"]["details"].get("air_temperature") for t in ts[:24]]
    temps = [t for t in temps if t is not None]
    # freezing level from the day's warmest hour brought to sea level (valley mornings sit under an inversion)
    frz_m = max(0.0, (max(temps) if temps else 15) + 6.5 * elev_m / 1000) / 6.5 * 1000
    out, last = {"time": []}, None
    for k in range(hours):
        when = now + timedelta(hours=k)
        d = by.get(when.strftime("%Y-%m-%dT%H")) or last
        if d is None:
            continue
        last = d
        out["time"].append(when.strftime("%Y-%m-%dT%H:00"))
        ins = d["instant"]["details"]
        nx = d.get("next_1_hours") or d.get("next_6_hours") or {}
        sym = (nx.get("summary") or {}).get("symbol_code", "")
        T, Td = ins.get("air_temperature", 15), ins.get("dew_point_temperature", 8)
        fog = ins.get("fog_area_fraction", 0) or 0
        low = max(0.0, ins.get("cloud_area_fraction_low", 0) - fog)  # fog is counted in the low cloud: it's mist, not a ceiling
        mid, high = ins.get("cloud_area_fraction_medium", 0), ins.get("cloud_area_fraction_high", 0)
        conv = 1.94384 if kn else 3.6
        ws, wd = ins.get("wind_speed", 3) * conv, ins.get("wind_from_direction", 270)
        gust = ins.get("wind_speed_of_gust", ins.get("wind_speed", 3) * 1.5) * conv
        precip = (nx.get("details") or {}).get("precipitation_amount", 0) or 0
        vis = max(1600, 24000 * (1 - 0.6 * fog / 100) - 3000 * min(precip, 4))
        base_agl = max(60, (T - Td) * 125)
        vals = {"temperature_2m": T, "dew_point_2m": Td, "cloud_cover": ins.get("cloud_area_fraction", 0), "cloud_cover_low": low,
                "cloud_cover_mid": mid, "cloud_cover_high": high, "visibility": vis, "precipitation": precip, "wind_gusts_10m": gust,
                "freezing_level_height": frz_m, "weather_code": _wcode(sym), "cape": 1200 if "thunder" in sym else 50}
        for L, z in LEVEL_Z.items():
            agl = z - elev_m
            if L >= 850:
                cc = low if base_agl <= agl <= base_agl + 700 else (low * 0.3 if agl > base_agl else 0)
            elif L >= 600:
                cc = mid
            else:
                cc = high
            f = {1000: 1.0, 925: 1.3, 850: 1.6, 700: 2.0, 600: 2.3, 500: 2.6, 400: 3.0}[L]
            vals.update({f"temperature_{L}hPa": round(T - 6.5 * (z - elev_m) / 1000, 1), f"relative_humidity_{L}hPa": round(min(100, 45 + cc * 0.55)),
                         f"cloud_cover_{L}hPa": round(cc), f"geopotential_height_{L}hPa": z, f"wind_speed_{L}hPa": round(ws * f, 1),
                         f"wind_direction_{L}hPa": round((wd + (1 - 1 / f) * 30) % 360)})
        for kk, v in vals.items():
            out.setdefault(kk, []).append(v)
    return out


def forecast(url):
    """Answer an Open-Meteo /v1/forecast URL (same JSON shape) from MET Norway."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    lats = [float(x) for x in q["latitude"][0].split(",")]
    lons = [float(x) for x in q["longitude"][0].split(",")]
    if len(lats) > MAX_POINTS:
        raise ValueError("too many points for the backup forecast")
    want = q.get("hourly", [""])[0].split(",")
    kn = q.get("wind_speed_unit", [""])[0] == "kn"
    hours = int(q["forecast_hours"][0]) if "forecast_hours" in q else int(q.get("forecast_days", ["2"])[0]) * 24
    elev = _elevations(list(zip(lats, lons)))
    with ThreadPoolExecutor(6) as ex:
        series = list(ex.map(lambda i: _series(lats[i], lons[i]), range(len(lats))))
    out = []
    for la, lo, e, ts in zip(lats, lons, elev, series):
        h = _hourly(ts, e, hours, kn)
        out.append({"latitude": la, "longitude": lo, "elevation": e, "source": "MET Norway",
                    "hourly": {"time": h.get("time", []), **{v: h[v] for v in want if v in h}}})
    return json.dumps(out if len(out) > 1 else out[0]).encode()
