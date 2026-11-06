"""Quick SimConnect check. Run simtest.bat with MSFS loaded in the cockpit."""
import time
print("Connecting to MSFS...")
try:
    from SimConnect import SimConnect, AircraftRequests, Request
except Exception as e:
    print("The SimConnect package isn't installed:", e)
    raise SystemExit
try:
    sm = SimConnect()
except Exception as e:
    print("Could not connect:", repr(e))
    print("Make sure MSFS is running on this PC, and that MSFS and this window run with the same rights (both normal, or both as administrator).")
    raise SystemExit
print("Connected. ok =", getattr(sm, "ok", None))
aq = AircraftRequests(sm, _time=200)
for i in range(5):
    print("Library read   :", "lat", aq.get("PLANE_LATITUDE"), "lon", aq.get("PLANE_LONGITUDE"), "alt", aq.get("PLANE_ALTITUDE"), "ias", aq.get("AIRSPEED_INDICATED"))
    time.sleep(1)
r = Request((b"PLANE LATITUDE", b"degrees"), sm, _time=0)
t = Request((b"TITLE", b"String"), sm, _time=0)
for i in range(5):
    print("Onward read    :", "lat", r.value, "title", t.value)
    time.sleep(1)
sm.exit()
print("Done. Send a screenshot of this window.")
