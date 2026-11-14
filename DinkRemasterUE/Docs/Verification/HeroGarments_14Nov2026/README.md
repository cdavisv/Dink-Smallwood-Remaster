# The hero's garments around the armholes, collar and pack (14 November 2026)

Owner, after playing master `cb842dd2`: "dinks arms look odd around the arm pit". This folder records what was wrong
in the running game, what the rebuild changes, and what the game shows now. Every picture is a capture of the game
(`Scripts/PhotorealQA/run_capture.sh`, screen 438, `dink.CalAnchor` / `dink.CalCam`), not a Blender render.

## What was wrong

1. **Armholes, neckline, collar.** The jerkin's and shirt's game meshes are decimated from the detailed cloth.
   Decimation collapsed the border vertices unevenly: the armhole rim had pointed tabs and notches, its turned-in lip
   folded over itself, the shirt's large triangles came through the leather at the rim as pale spikes, and the cap of
   the jerkin reached 6 cm out over the upper arm, so it stood up as a horn when the arm was raised. The stand collar
   was torn to shreds by the same decimation.
2. **Pack.** The pack hung off the back, and its shoulder straps were snapped to the nearest surface, which under the
   lifted jerkin was the shirt: the straps vanished into the leather.
3. **Dark triangles beside the armholes** (found in the first captures of the rebuilt mesh, and present on master):
   the planar UV charts of the jerkin's and the shirt's shoulder pieces leaned against the slope of the shoulder, so
   each chart folded over at the shoulder line. The chest and the top of the shoulder shared texels, and whichever
   triangle was baked last won. Sheet 05, left column.
4. **Pale triangles and a comb of streaks on the pack flap** (also on master): the flap was baked from a separately
   sampled detailed sheet that lay up to 6 mm off the game mesh at the fold and along the free edge, so the rays of
   whole triangles missed it or met its underside. Sheet 05, left column.

## What changed (sources under `SourceAssets/Art/PhotorealPass/Characters`)

- `Tools/garlib.py`, `Tools/dink_02_garments.py`: every opening is cut a second time after the decimation, 4.5 mm
  inside the first cut, so the rim follows the cut exactly (`finish(recut=...)`, `tidy_rim`); the armhole's corner on
  the shoulder cap is rounded and the cap ends 2 cm outside the joint; the collar band keeps its rings through the
  decimation; the shirt is held under the jerkin near its rims (`tuck_under`); collar clearance is shared between
  neighbouring vertices instead of pushing single vertices.
- `Tools/dink_02a_bodyvol.py`, `Tools/dink_03_gear.py`, `Tools/gearlib.py`, `Tools/dink_06_assemble.py`: the pack sits
  on the back, its straps lie on the outermost layer (`on_outer`) and are re-snapped after smoothing.
- `Tools/dink_02_garments.py`: the planar charts 3/4 (shirt) and 13/14 (jerkin) lean with the shoulder slope; no chart
  folds over any more.
- `Tools/dink_05_bake.py`: thin open sheets (`SELF_HI`, the pack flap) bake from a subdivided copy of the game mesh.
- Rebuilt: the four LOD FBX, `T_Dink_PR_Outfit_*`, `T_Dink_PR_Gear_*`, the `.blend` sources. Imported:
  `SK_Dink_Photoreal` and the six texture packages. The skeleton, the hair, the head and the skin are untouched; both
  shape keys (`Physique_Scrawny`, `Physique_Brawny`) are on all four LODs (`Dink/physique_report.json`).

## What the game shows now

| Sheet | Shows | What I see |
|---|---|---|
| `01_idle_confidence_0_and_1.png` | Standing, `dink.HeroConfidence 0` (top) and `1` (bottom): armhole from the front left and the back right, the back with the pack, the front | The armhole reads as the stitched rim of a sleeveless jerkin over a shirt sleeve, on the scrawny and on the brawny build. No gap, no spike, no see-through. Both pack straps lie on the leather. |
| `02_arms_raised.png` | Bow draw (confidence 0), cast (confidence 1), jump | With the arm overhead the rim stays closed round the sleeve and the cap does not stand up. In the raised armpit the shirt's weave is stretched into streaks (bottom-left of the first tile): still visible close up. |
| `03_swings_walk_run.png` | Sword slash, punch, walk and run at play distance | Nothing opens during the swings. At play distance the shoulders and the pack read cleanly. |
| `04_lods_1_to_3.png` | LOD 1 to 3 forced at close range | The rims hold. On LOD 1 to 3 a shoulder strap stands a little off the jerkin and at LOD 3 the rim is visibly polygonal: these LODs are only drawn far from the camera. |
| `05_triangles_before_after.png` | Left: the rebuilt mesh before the chart and flap fixes. Right: this PR | The dark triangles beside the armhole and the pale triangles and stitched zigzag on the flap are gone. |

## Still open (seen, not fixed here)

- A thin pale line runs along the armhole rim (the edge of the turned-in lip catches the light).
- The shirt's texture stretches in the raised armpit.
- A darker, streaked band across the top of the pack flap is part of the flap's baked wear mask; it reads as a worn
  fold, but it is not a modelled fold.
- The hero carries his arms away from his body when he stands. That is the pose (animation stream), not the mesh.

## Not checked

- A capture of master before any of this was not taken (the editor was shared by seven sessions); the left column of
  sheet 05 is the nearest "before", and it already has the new rims.
- Cloth during the death, hurt and pickup clips; the packaged game; any lighting other than the day scene of screen 438.

## Tests

- `Dink.Art+Dink.Animation+Dink.Movement`: 74/74 in the private project copy with this mesh imported.
- `art_coverage.py`: final 4,334, placeholder 2,121, cut 152, before and after (character art is not counted by
  origin ID, so the ledger `doc/remaster/ALPHA_GATE2_BACKLOG.md` is unchanged).
