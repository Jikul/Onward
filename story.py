"""Words for the journey: job blurbs, journal entries, the people you meet."""
import random

POI_LINES = {
    "historic:castle": ["{name} is on the way. Castles always look better from the air than from the ticket queue.",
                        "Someone at the last café swore {name} is best seen from 1,500 ft. Time to check."],
    "historic:fort": ["{name} sits along the route. Old forts were built to watch the sky, so return the favor."],
    "historic:ruins": ["The ruins of {name} are right on the line. A slow orbit seems polite."],
    "historic:monastery": ["{name} has been sitting quietly up there for centuries. Fly by, keep it quiet."],
    "historic:archaeological_site": ["{name} is close to the route. History looks different from above."],
    "man_made:lighthouse": ["Follow the coast and you'll pass {name}. Lighthouses make excellent waypoints."],
    "waterway:dam": ["{name} is along the way. Big concrete, big water, big photo."],
    "waterway:waterfall": ["There's a waterfall, {name}, near the route. Worth a low, careful pass if the terrain allows."],
    "natural:volcano": ["{name} is on the way. Keep your distance and enjoy the view."],
    "natural:peak": ["{name} is near the route. Mind the terrain and the wind on the lee side."],
    "natural:glacier": ["{name} is on the way. Cold air, smooth air, beautiful light."],
    "natural:cape": ["The route rounds {name}. Coastlines are the best kind of map."],
    "natural:beach": ["{name} is along the way. Can't land there, but you can look."],
    "tourism:viewpoint": ["People drive for hours to reach the {name} viewpoint. You'll fly past it."],
    "tourism:attraction": ["{name} is on the way. The guidebook says go. The guidebook is right."],
    "building:cathedral": ["{name} is close to the route. Spires make great visual references."],
    "bridge": ["{name} crosses the route. Bridges are made for flying alongside."],
    "msfs": ["{name} is a handcrafted spot in the sim, and it's right on the way."],
}
POI_DEFAULT = ["{name} is along the route. Worth a look."]

DEST_LINES = {
    "town": ["{town} is the next stop. A wander, a coffee, maybe a pastry.",
             "Never been to {town}. That's reason enough.",
             "The plan is simple: land at {town}, find something to eat, look at a map."],
    "grass": ["Grass under the wheels today. Short, soft and honest.",
              "A grass strip at {name}. Check the windsock twice."],
    "short": ["The strip at {name} is on the short side for this aircraft. Fly the numbers.",
              "Runway is tight. Stabilized approach or go around, no heroics."],
    "high": ["{name} sits at {elev} ft. Thin air, long takeoff roll, big views.",
             "Density altitude will bite at {name}. Lean properly."],
    "night": ["You'll arrive after dark. Runway lights should be on. Should."],
    "uncharted": ["{name} doesn't have a code the sim knows. Find it on the world map by its coordinates and treat it like an expedition."],
    "unknown": ["Nobody wrote down how long the strip at {name} is. Overfly it first and decide like a bush pilot.",
                "Runway details for {name} are a mystery. Look before you land."],
    "wind": ["The wind at the destination is up. A good day to practice crosswinds, carefully."],
    "weather": ["Weather is marginal along the way. Have a plan B before you start the engine."],
    "big": ["{name} is a proper airport. Expect traffic and long taxis."],
    "handcrafted": ["{name} is one of the sim's handcrafted airports. Take a look around after shutdown."],
    "country": ["New country! First time landing in {country}."],
}

IFR_LINES = [
    "The clouds are down at {ceiling} ft at {name}. File IFR, fly the approach, trust the instruments.",
    "Low cloud everywhere, {ceiling} ft at {name}. A proper day for an instrument flight.",
    "Ceiling {ceiling} ft at {name}. The view will be grey until the runway lights appear.",
]
IFR_LINES_GENERIC = [
    "Grey skies. This one's IFR: departure, en route and an instrument approach into {name}.",
]

TITLES = {
    "tour": ["Sightseeing hop to {town}", "Onward to {town}", "A look at {town}", "Wandering toward {town}"],
    "scenic": ["The scenic way to {town}", "{poi} and on to {town}", "Past {poi} to {town}"],
    "challenge": ["Test yourself at {name}", "Tricky arrival: {name}", "The hard way to {town}"],
    "ride": ["A ride for {friend}", "Taking {friend} to {town}"],
    "ferry": ["Limp to the shop at {name}", "Maintenance run to {town}"],
    "ifr": ["Into the clouds to {town}", "Instruments to {town}", "IFR to {name}", "Through the grey to {town}"],
}

FIRST = {
    "PT": ["Inês", "João", "Rita", "Tiago", "Beatriz", "Miguel", "Sofia", "Duarte"],
    "ES": ["Lucía", "Javier", "Marta", "Pablo", "Carmen", "Diego", "Elena", "Álvaro"],
    "FR": ["Camille", "Julien", "Léa", "Mathieu", "Chloé", "Antoine", "Manon", "Hugo"],
    "IT": ["Giulia", "Marco", "Chiara", "Luca", "Francesca", "Matteo", "Sara", "Davide"],
    "DE": ["Anna", "Lukas", "Lena", "Jonas", "Marie", "Felix", "Hannah", "Paul"],
    "AT": ["Katharina", "Florian", "Lisa", "Maximilian"], "CH": ["Laura", "Nico", "Seraina", "Reto"],
    "GB": ["Olivia", "Harry", "Amelia", "George", "Isla", "Jack", "Freya", "Alfie"],
    "IE": ["Aoife", "Cian", "Niamh", "Seán"], "NL": ["Sanne", "Daan", "Fleur", "Bram"],
    "BE": ["Lotte", "Wout", "Elise", "Arthur"], "NO": ["Ingrid", "Sindre", "Silje", "Magnus"],
    "SE": ["Elsa", "Oskar", "Maja", "Viktor"], "DK": ["Ida", "Mads", "Freja", "Rasmus"],
    "FI": ["Aino", "Eetu", "Venla", "Onni"], "IS": ["Sigrún", "Gunnar", "Hekla", "Bjarki"],
    "PL": ["Zofia", "Kacper", "Maja", "Jakub"], "GR": ["Eleni", "Nikos", "Maria", "Giorgos"],
    "US": ["Emma", "Jake", "Madison", "Tyler", "Ava", "Cody", "Hailey", "Wyatt"],
    "CA": ["Chloé", "Liam", "Maya", "Owen"], "AU": ["Matilda", "Lachlan", "Ruby", "Hamish"],
    "NZ": ["Aroha", "Nikau", "Ella", "Tama"], "BR": ["Ana", "Thiago", "Luana", "Rafael"],
    "MA": ["Yasmine", "Karim", "Salma", "Youssef"], "JP": ["Yui", "Haruto", "Sakura", "Ren"],
}
FIRST_DEFAULT = ["Sam", "Alex", "Noor", "Kai", "Mira", "Leo", "Tess", "Ravi"]

MEETINGS = [
    "At the café by the apron you got talking to {friend}, who lives near {town}. If you're heading that way, there's a seat for them.",
    "{friend} helped you tie down the plane and mentioned family near {town}. You offered a lift some day.",
    "{friend}, a local glider pilot, has been trying to get to {town} all week. Your plane has a spare seat.",
    "The fuel guy's cousin, {friend}, needs to get to {town}. Word gets around at small airfields.",
]

RIDE_DONE = [
    "{friend} insisted on buying lunch. You let them.",
    "{friend} took about a hundred photos out the window and promised to send the good ones.",
    "Dropped {friend} off near {town}. They said to come back in summer.",
]

LANDING_WORDS = [
    (60, "a greaser, barely felt it"),
    (180, "a soft, tidy landing"),
    (300, "a solid, ordinary landing"),
    (450, "a firm arrival"),
    (650, "a hard landing that rattled the panel"),
    (1000, "a very hard landing, the kind that gets a plane inspected"),
    (99999, "an arrival the airframe will remember"),
]

ARRIVAL = [
    "Tied down at {name}.", "Engine off at {name}. The silence is the best part.",
    "Rolled out at {name} and found a quiet corner of the apron.", "{name}. Another dot on the map.",
]

NIGHT_ARRIVAL = ["Landed under the runway lights. Night flying never gets old."]
DIVERT = ["Plans changed and you ended up at {name} instead. That's travelling."]
CRASH = ["The flight ended badly near {name}. You're fine. The plane is not."]


def pick(lst, **kw):
    return random.choice(lst).format(**kw)


def friend_name(country):
    return random.choice(FIRST.get(country, FIRST_DEFAULT))


def landing_words(fpm):
    for lim, w in LANDING_WORDS:
        if fpm <= lim:
            return w
    return LANDING_WORDS[-1][1]


def poi_line(p):
    if p.get("label") == "MSFS photogrammetry city":
        return pick(["{name} is on the way, in full photogrammetry. Fly low enough to enjoy it, legally.",
                     "The route crosses {name}, one of the sim's 3D photogrammetry cities."], name=p["name"])
    if p.get("source") == "msfs":
        return pick(POI_LINES["msfs"], name=p["name"])
    return pick(POI_LINES.get(p.get("kind", ""), POI_DEFAULT), name=p["name"])


def kind_label(kind):
    if not kind:
        return "landmark"
    k = kind.split(":")[-1].replace("_", " ")
    return {"attraction": "attraction", "viewpoint": "viewpoint", "place of worship": "church"}.get(k, k)
