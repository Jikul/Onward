# Getting ready for flightsim.to

Done:
- [x] No personal defaults: first-run setup asks for the pilot name and home airfield
- [x] The community MSFS POI map is downloaded at first run, not shipped in the package
- [x] Versioning, changelog and in-app updates from GitHub (public repo onward-sim/Onward)
- [x] User data separate from the program; log file for bug reports (onward.log)
- [x] License: AGPL-3.0-or-later (required in practice by Python-SimConnect, AGPL-3.0)
- [x] Credits for every data source and library (CREDITS.md, and Settings › About and credits)
- [x] Map and data terms checked: satellite map moved from Esri (needs an ArcGIS license) to EOxCloudless (free non-commercial, credited)
- [x] Weather requests kept under Open-Meteo's free limit (daily budget, caching), MET Norway as backup, terrain from AWS Terrain Tiles
- [x] Icon (assets/onward.ico) for the exe and the browser tab
- [x] Windows build tested on GitHub's Windows runners: Onward.exe builds, starts in demo mode, makes offers and plans
- [x] Automated checks: `python tests/smoke.py` (calculations plus every endpoint and a full demo leg)
- [x] Listing screenshots

Still to do before publishing:
- [ ] Permission from the creator of the community "Microsoft Flight Simulator Map" (Google My Maps) to use it in a distributed app
- [ ] A closed beta in the real sim: send-to-sim, landing grades, failures, reconnects, screenshots, GTNXi files, first run of Onward.exe on a gaming PC (Windows firewall prompt)
- [ ] Tag the first public release (git tag v0.x.0 && git push --tags) to publish the Windows zip on GitHub releases
