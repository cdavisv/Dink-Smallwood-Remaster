# A50: the bow-shop softlock (owner-approved deviation, 21 Nov 2026)

What: s3-st2p.c:30-42. If Dink chooses "Buy a Bow" with all 16 item slots full, Arturous says "You are carrying too much" and
the script `return`s while Dink and the shopkeeper are still frozen. That is a 1997 softlock. By owner decision of 16 Nov 2026
the converter switch `fix_s3_st2p_l42` (tools/dinkink `overrides.py` owner additions) unfreezes both before the return. It is
listed in the deviations table of `doc/remaster/DINKC_PARITY.md`.

How it was proven (headless, private copy = master a00ec71a0 + this branch):
- `python3 -m unittest discover -s tests` in tools/dinkink: 45/45.
- `Scripts/sync_story.py --rebuild` reproduces the committed story files (only a line-ending difference in names.csv).
- `Scripts/build.sh`: BUILD OK, 0 warnings (DinkOwnerDecisionTests.cpp compiled).
- `Scripts/test.sh Dink`: 383/384 in 1015 s, including `Dink.Narrative.OwnerDecisions.BowShopFullInventoryUnfreezes`. The one failure, `Dink.Art.Family.BarrelCookedGameSurface`, was a leftover of the previous suite run in the same copy: it refuses to overwrite `Saved/Automation/BarrelCookGame.*`. With those files deleted it passed alone (1/1). A50 does not touch it.
- The probe chapters in that suite: twenty md5s equal to the table in `Plugins/DinkParity/Docs/packaged_probe.md` (the probe never
  reaches the bow shop with a full inventory).

Not checked: no rendered run (machine rule), no packaged run.
