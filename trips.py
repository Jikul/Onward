"""Plan a trip: what to show on the trip map, place cards, your map so far, trips with via stops, and trip ideas."""
import math
import threading
import time

import geo

AIRFIELD_TYPES = ("small_airport", "medium_airport", "large_airport")


def _town(a):
    return a.get("town") or a.get("municipality") or a["name"]


def _paved(a):
    return any(r.get("surface") == "paved" for r in a.get("runways") or [])


def _longest(a):
    return round(max((r.get("length") or 0 for r in a.get("runways") or []), default=0))


class Trips:
    def __init__(self, world, gen_engine, log=print):
        self.world, self.gen, self.log = world, gen_engine, log
        self._ideas = {}            # (where, aircraft, visited count) -> (time, ideas)
        self._lock = threading.Lock()

    # ---------- what counts as a place you can fly to ----------
    def flyable(self, a, uncharted=False):
        if a["type"] not in AIRFIELD_TYPES or a.get("military"):
            return False
        if not uncharted and (not a.get("code") or a.get("rw_unknown")):
            return False
        return True

    def ranges(self, career):
        """How far one comfortable leg goes, and one day of flying (two legs, about three hours)."""
        prof = career.profile()
        leg = self.gen.trip_leg_nm(prof)
        day = min(2 * leg, (180 - 30) / 60 * prof["cruise_kt"])
        return {"leg_nm": round(leg), "day_nm": round(day)}

    # ---------- the trip map ----------
    def map_markers(self, career, s, w, n, e, zoom, uncharted=False):
        """Highlights at any zoom (photogrammetry cities, handcrafted airports); every airfield when zoomed in."""
        visited = set(career.s.get("visited", []))
        highlights = []
        for p in self.world.msfs_pois:
            if p.get("label") == "MSFS photogrammetry city" and s <= p["lat"] <= n and w <= p["lon"] <= e:
                highlights.append({"kind": "photo", "name": p["name"], "lat": p["lat"], "lon": p["lon"]})
        for ident in self.world.handcrafted:
            a = self.world.airports.get(ident)
            if a and s <= a["lat"] <= n and w <= a["lon"] <= e:
                highlights.append({"kind": "hand", "name": a["name"], "lat": a["lat"], "lon": a["lon"], "ident": ident,
                                   "code": a.get("code") or ident, "visited": ident in visited})
        airfields = []
        if zoom >= 8:
            for i in range(math.floor(s), math.floor(n) + 1):
                for j in range(math.floor(w), math.floor(e) + 1):
                    for a in self.world.grid.get((i, ((j + 180) % 360) - 180), ()):
                        if not (s <= a["lat"] <= n and w <= a["lon"] <= e) or not self.flyable(a, uncharted):
                            continue
                        if a["ident"] in self.world.handcrafted:
                            continue
                        airfields.append({"ident": a["ident"], "code": a.get("code") or "", "name": a["name"], "lat": a["lat"], "lon": a["lon"],
                                          "paved": _paved(a), "len": _longest(a), "visited": a["ident"] in visited})
                        if len(airfields) >= 2500:
                            break
        return {"highlights": highlights, "airfields": airfields}

    def place(self, career, ident=None, lat=None, lon=None, uncharted=False):
        """The card for one place: an airfield by ident, or the nearest airfield to a point on the map."""
        a = self.world.airports.get(ident or "")
        if not a and lat is not None:
            _, a = self.world.nearest(lat, lon, 40, pred=lambda x: self.flyable(x, uncharted))
        if not a:
            return None
        here = career.loc()
        rg = self.ranges(career)
        d = geo.dist_nm(here["lat"], here["lon"], a["lat"], a["lon"])
        legs = max(1, math.ceil(d / rg["leg_nm"]))
        tags = []
        if a["ident"] in self.world.handcrafted:
            tags.append("Handcrafted airport")
        photo = [p for p in self.world.msfs_near(a["lat"], a["lon"], 10) if p.get("label") == "MSFS photogrammetry city"]
        if photo:
            tags.append(f"Photogrammetry: {photo[0]['name']}")
        pois = [p for p in self.world.msfs_near(a["lat"], a["lon"], 15) if p.get("label") != "MSFS photogrammetry city"]
        if pois:
            tags.append(f"{len(pois)} MSFS POI{'s' if len(pois) > 1 else ''} nearby")
        return {"ident": a["ident"], "code": a.get("code") or a["ident"], "name": a["name"], "town": _town(a), "lat": a["lat"], "lon": a["lon"],
                "country": self.world.countries.get(a["country"], a["country"]), "dist": round(d), "legs": legs,
                "days": max(1, math.ceil(d / max(1, rg["day_nm"]))), "one_leg": d <= career.profile()["range_nm"] * 0.85 and legs == 1,
                "here": a["ident"] == here["ident"], "paved": _paved(a), "len": _longest(a), "tags": tags,
                "visited": a["ident"] in career.s.get("visited", [])}

    # ---------- your map so far ----------
    def stats(self, career):
        st = career.stats()
        here = career.loc()
        been = set(career.s.get("countries", []))
        best = None
        for a in self.world.airports.values():
            if a["country"] in been or not self.flyable(a):
                continue
            d = geo.dist_nm(here["lat"], here["lon"], a["lat"], a["lon"])
            if best is None or d < best[0]:
                best = (d, a)
        msfs_seen = sum(1 for x in career.s.get("sights", []) if str(x.get("kind", "")).startswith(("MSFS", "National park")))
        out = {"airfields": st["airfields"], "countries": st["countries"], "nm": st["nm"], "msfs_seen": msfs_seen, "legs": st["legs"]}
        if best:
            d, a = best
            out["next_country"] = {"name": self.world.countries.get(a["country"], a["country"]), "nm": round(d), "town": _town(a),
                                   "ident": a["ident"]}
        return out

    # ---------- a trip: destination, via stops, maybe home again ----------
    def plan(self, career, dest_ident=None, via=None, round_trip=False, leg_nm=None):
        """Via items are airfields ({"ident"}) you land at, or sights ({"name","lat","lon"}) the route flies over."""
        prof = career.profile()
        here = career.loc()
        max_leg = float(leg_nm or self.gen.trip_leg_nm(prof))
        via = via or []
        landings, sights = [], []
        for v in via:
            if v.get("ident") and self.world.airports.get(v["ident"]):
                landings.append(self.world.airports[v["ident"]])
            elif v.get("lat") is not None:
                sights.append({"name": v.get("name") or "Sight", "lat": float(v["lat"]), "lon": float(v["lon"]),
                               "label": v.get("label") or "sight", "source": v.get("source") or "msfs"})
        dest = self.world.airports.get(dest_ident or "")
        targets = landings + ([dest] if dest else [])
        if round_trip:
            targets.append(here)
        targets = [t for k, t in enumerate(targets) if k == 0 or t["ident"] != targets[k - 1]["ident"]]
        if targets and targets[0]["ident"] == here["ident"]:
            targets = targets[1:]
        if not targets and sights:  # only sights: fly to them and come home
            far = max(sights, key=lambda p: geo.dist_nm(here["lat"], here["lon"], p["lat"], p["lon"]))
            _, near = self.world.nearest(far["lat"], far["lon"], 40, pred=self.flyable)
            targets = [t for t in (near, here if round_trip else None) if t]
        if not targets:
            return None, "Pick where to go, or add a stop."
        # sights first go to the stretch between landings where they cost the least detour
        stretch = [here] + targets
        per = {k: [] for k in range(len(targets))}
        for p in sights:
            k = min(range(len(targets)), key=lambda k: geo.dist_nm(stretch[k]["lat"], stretch[k]["lon"], p["lat"], p["lon"])
                    + geo.dist_nm(p["lat"], p["lon"], stretch[k + 1]["lat"], stretch[k + 1]["lon"])
                    - geo.dist_nm(stretch[k]["lat"], stretch[k]["lon"], stretch[k + 1]["lat"], stretch[k + 1]["lon"]))
            per[k].append(p)
        stops, used, marks = [here], {here["ident"]}, {}
        via_ids = {a["ident"] for a in landings}
        for k, t in enumerate(targets):
            # the sights of this stretch, nearest first from where it starts: the stops follow the way through them
            pos, chain, left = stops[-1], [], list(per[k])
            while left:
                nxt = min(left, key=lambda p: geo.dist_nm(pos["lat"], pos["lon"], p["lat"], p["lon"]))
                chain.append(nxt); left.remove(nxt); pos = nxt
            seg = self.gen.trip_stops(career, stops[-1], t, max_leg, used - {here["ident"]} if (round_trip and k == len(targets) - 1) else used,
                                      path=[(p["lat"], p["lon"]) for p in chain])
            first = len(stops) - 1
            stops += seg
            used |= {x["ident"] for x in seg}
            # each sight joins the leg of this stretch where it fits best
            for p in per[k]:
                best = min(range(first, len(stops) - 1), key=lambda i: geo.dist_nm(stops[i]["lat"], stops[i]["lon"], p["lat"], p["lon"])
                           + geo.dist_nm(p["lat"], p["lon"], stops[i + 1]["lat"], stops[i + 1]["lon"]))
                marks.setdefault(best, {}).setdefault("sights", []).append(p)
        for i in range(len(stops) - 1):
            if stops[i + 1]["ident"] in via_ids:
                marks.setdefault(i, {})["via"] = True
        for i, m in marks.items():  # sights in the order you reach them
            if m.get("sights"):
                a = stops[i]
                m["sights"].sort(key=lambda p: geo.dist_nm(a["lat"], a["lon"], p["lat"], p["lon"]))
        trip = self.gen.trip_legs(career, stops, max_leg, marks)
        for leg in trip["legs"]:
            if leg.get("nm", 0) > prof["range_nm"] * 0.85:
                return None, f"The leg to {leg['to_name']} is too long for the {prof['name']}. Add a stop on the way, or pick shorter legs."
            if leg.get("nm", 0) > max_leg * 1.7:  # no airfield to stop at on the way: open sea, most likely
                return None, (f"There's nowhere to stop between {leg['from_name']} and {leg['to_name']} ({leg['nm']} nm, probably over water). "
                              "Add a via stop to go around, or pick longer legs.")
        trip.update(via=via, round_trip=bool(round_trip), dest=(dest or targets[-1])["ident"])
        return trip, None

    def name_for(self, career, trip):
        here = career.loc()
        last = self.world.airports.get(trip["legs"][-1]["to"]) if trip["legs"] else None
        if trip.get("round_trip"):
            far = max(trip["legs"], key=lambda l: geo.dist_nm(here["lat"], here["lon"], l["lat"], l["lon"]))
            return f"{_town(here)} to {far['to_name']} and back"
        return f"{_town(here)} to {_town(last) if last else 'somewhere'}"

    # ---------- trip ideas ----------
    def ideas(self, career, uncharted=False):
        here = career.loc()
        key = (here["ident"], career.s.get("aircraft"), len(career.s.get("visited", [])), len(career.s.get("sights", [])))
        with self._lock:
            hit = self._ideas.get(key)
            if hit and time.time() - hit[0] < 3600:
                return hit[1]
        out = []
        try:
            out = self._make_ideas(career, uncharted)
        except Exception as e:
            self.log(f"Trip ideas failed: {e}")
        with self._lock:
            self._ideas = {key: (time.time(), out)}
        return out

    def _make_ideas(self, career, uncharted):
        here = career.loc()
        rg = self.ranges(career)
        reach = rg["day_nm"] * 2.2           # about two days out
        visited = set(career.s.get("visited", []))
        seen = {x["name"] for x in career.s.get("sights", [])}
        dist = lambda a: geo.dist_nm(here["lat"], here["lon"], a["lat"], a["lon"])
        good = lambda a: self.flyable(a, uncharted) and a["ident"] != here["ident"]
        ideas, used_dest = [], set()

        def add(kind, title, why, dest=None, via=None, round_trip=False):
            if dest and dest["ident"] in used_dest:
                return
            trip, err = self.plan(career, dest and dest["ident"], via, round_trip)
            if err or not trip or not trip["legs"]:
                return
            if dest:
                used_dest.add(dest["ident"])
            ideas.append({"id": f"i{len(ideas)}", "kind": kind, "title": title, "why": why, "dest": trip["dest"], "via": via or [],
                          "round_trip": round_trip, "trip": trip})

        def best_field(lat, lon, radius=25):
            cands = [(d, a) for d, a in self.world.near(lat, lon, radius) if good(a)]
            if not cands:
                return None
            return max(cands, key=lambda x: -x[0] + (25 if x[1]["ident"] in self.world.handcrafted else 0)
                       + {"medium_airport": 8, "small_airport": 4, "large_airport": -6}.get(x[1]["type"], 0))[1]

        # 1. a World Update's sights, the biggest group within reach that you haven't seen
        groups = {}
        for p in self.world.msfs_near(here["lat"], here["lon"], reach):
            if p.get("note") and p["name"] not in seen and dist(p) > rg["leg_nm"] * 0.5:
                groups.setdefault(p["note"], []).append(p)
        if groups:
            note, pois = max(groups.items(), key=lambda kv: len(kv[1]))
            if len(pois) >= 2:
                route, pos, left = [], here, list(pois)
                while left and len(route) < 4:  # a chain outwards from here, nearest first
                    nxt = min(left, key=lambda p: geo.dist_nm(pos["lat"], pos["lon"], p["lat"], p["lon"]))
                    if route and geo.dist_nm(pos["lat"], pos["lon"], nxt["lat"], nxt["lon"]) > rg["day_nm"]:
                        break
                    route.append(nxt); left.remove(nxt); pos = nxt
                dest = best_field(route[-1]["lat"], route[-1]["lon"], 30)
                if dest:
                    names = [p["name"] for p in route]
                    add("update", f"{note} sights, to {_town(dest)}",
                        ", ".join(names[:-1]) + (" and " if len(names) > 1 else "") + names[-1] + ".",
                        dest, [{"name": p["name"], "lat": p["lat"], "lon": p["lon"], "label": p.get("label"), "source": "msfs"} for p in route])

        # 2. the nearest photogrammetry city you haven't landed at
        cities = sorted((p for p in self.world.msfs_pois if p.get("label") == "MSFS photogrammetry city" and rg["leg_nm"] * 0.6 < dist(p) < reach), key=dist)
        for c in cities[:8]:
            dest = best_field(c["lat"], c["lon"], 15)
            if dest and dest["ident"] not in visited and dest["ident"] not in used_dest:
                add("photo", f"To {c['name']}, in photogrammetry", f"{round(dist(c))} nm. The city is a 3D scan in MSFS, worth a slow pass before landing.", dest)
                break

        # 3. a country you haven't landed in
        st = self.stats(career)
        nc = st.get("next_country")
        if nc and nc["nm"] < reach:
            first = self.world.airports.get(nc["ident"])
            cands = [(d, a) for d, a in self.world.near(first["lat"], first["lon"], rg["leg_nm"] * 1.2)
                     if good(a) and a["country"] == first["country"] and a["ident"] not in used_dest and dist(a) < reach]
            if cands:
                dest = max(cands, key=lambda x: -abs(dist(x[1]) - max(nc["nm"], rg["leg_nm"] * 0.8)) * 0.3
                           + (25 if x[1]["ident"] in self.world.handcrafted else 0) + 5 * min(3, len(self.world.msfs_near(x[1]["lat"], x[1]["lon"], 15)))
                           + {"medium_airport": 12, "small_airport": 4}.get(x[1]["type"], 0))[1]
                add("country", f"Across the border into {nc['name']}", f"Your first landing in {nc['name']}, at {dest['name']}.", dest)

        # 4. a handcrafted airport you haven't been to
        hand = sorted((self.world.airports[i] for i in self.world.handcrafted if i in self.world.airports), key=dist)
        for a in hand:
            if a["ident"] not in visited and a["ident"] not in used_dest and good(a) and 30 < dist(a) < reach:
                add("hand", f"To {a['name']}, handcrafted", f"{round(dist(a))} nm to {_town(a)}, an airport built by hand for MSFS.", a)
                break

        # 4b. a longer trip: the place two days out with the most to see around it
        far = [p for p in self.world.msfs_pois if p.get("label") == "MSFS photogrammetry city" and rg["day_nm"] * 1.2 < dist(p) < reach]
        far.sort(key=lambda c: -len(self.world.msfs_near(c["lat"], c["lon"], 25)))
        for c in far[:6]:
            dest = best_field(c["lat"], c["lon"], 15)
            if dest and dest["ident"] not in used_dest:
                n_poi = len(self.world.msfs_near(c["lat"], c["lon"], 25))
                add("far", f"The long way to {c['name']}", f"{round(dist(c))} nm, a proper journey" + (f", with {n_poi} MSFS POIs around the city." if n_poi > 1 else "."), dest)
                break

        # 5. a loop: two airfields out, then home, in a day or two
        prof = career.profile()
        best = None
        for brg in range(0, 360, 30):
            p1 = geo.destination(here["lat"], here["lon"], brg, rg["leg_nm"] * 0.8)
            p2 = geo.destination(here["lat"], here["lon"], brg + 70, rg["leg_nm"] * 0.8)
            a1, a2 = best_field(p1[0], p1[1], 25), best_field(p2[0], p2[1], 25)
            if not a1 or not a2 or a1["ident"] == a2["ident"] or {a1["ident"], a2["ident"]} & used_dest:
                continue
            score = (a1["ident"] not in visited) * 10 + (a2["ident"] not in visited) * 10
            score += 4 * min(3, len(self.world.msfs_near(a1["lat"], a1["lon"], 20))) + 4 * min(3, len(self.world.msfs_near(a2["lat"], a2["lon"], 20)))
            if prof.get("bush") or career.s.get("prefs", {}).get("bush"):
                score += 8 * ((not _paved(a1)) + (not _paved(a2)))
            if best is None or score > best[0]:
                best = (score, a1, a2)
        if best:
            _, a1, a2 = best
            add("loop", f"A loop by {_town(a1)} and {_town(a2)}, and home", "Out one way, back another, and you end the trip where you started.",
                None, [{"ident": a1["ident"]}, {"ident": a2["ident"]}], True)
        return ideas
