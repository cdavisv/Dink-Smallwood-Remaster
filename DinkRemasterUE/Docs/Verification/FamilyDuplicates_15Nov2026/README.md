# Cross-screen duplicate placements drawn once (bug A208), 15-16 Nov 2026

What changed: 1997 maps often repeat an object on a neighbouring screen past that screen's edge (only one screen is shown at a
time). The family layer gave every copy its own mesh, variant and yaw, so the remaster drew two to four trees, dead trees or
grass clumps on top of each other. `UDinkFamilyDuplicatesSubsystem` (`DinkCore/Public/DinkFamilyDuplicates.h`) decides once per
world which copy draws the object (same `families.json` row and picture, different screens, within 100 cm and 4 px; the copy whose
ground point lies inside its own screen is kept) and hides the others' cards and meshes. Presentation only: hardness, collision,
scripts and origin IDs unchanged; `dink.FamilyDuplicates 0` at launch restores the old drawing. Rule details: `AGENTS.md`
section "Cross-screen duplicate placements".

Pair list: `pairs.csv` (392 same-class pairs within 1 m; `make_pairs_csv.py`, an offline mirror of the rule). In the game the
one-time build logs `4082 family copies, 175 dropped as the same object as a kept copy on a neighbour screen (169 placement-actor
cards hidden now; 10.0 ms, once)`.

## Proof (16 Nov, private copy built from this branch on master 3ff8cd25, world regenerated with `--export`)

- Captures `cap_before.txt` (launched with `dink.FamilyDuplicates=0`) and `cap_after2.txt`, same views, offscreen game; I looked
  at every frame. `before_after_451_440_223.jpg`: the courtyard willow of 451 was four overlapping willows, now one; the oak of
  440 with a grass clump at its foot (four copies) is now one oak; the dead tree of 223 (three copies) is one tree.
  `before_after_446_209_217.jpg`: 209 and 217 (pairs of pines) look nearly the same from above, since the copies stand within a
  metre; the counts below show the change. On 446 the willow is still its 1997 card (no bound mesh at that spot), before and after.
- `drawn_counts.txt` (`count_audit.py` over the scene audits of both runs): every pair object of the captured screens is drawn by
  1 copy after (2-4 before), except two objects of 440 (S439_P19 / S440_P01 and S440_P16) that one placement draws with two mesh
  parts, unchanged.
- `Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe`: **123/123** (796 s), incl. `Dink.Art.Family.Duplicates.Rule` and
  `.DressOrder` (the 15 Nov run had failed DressOrder because that build still had the old fixture origin ids over 99; fixed in
  the second commit). **All twenty probe md5s equal the baseline** (`Plugins/DinkParity/Docs/packaged_probe.md`).

## Re-verified on master bd6d227a (16 Nov, review of #192)

Branch rebased on bd6d227a (structure sets with `families_yield`, people as class rows, the #141 probe table), copy synced with fresh
timestamps (the build log compiles `DinkArtFamilySubsystem.cpp`), built (0 warnings), world regenerated with `--export` and
`--region stonebrook`. `Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe` **123/123** (838 s); **all twenty probe md5s equal
master's new table** (Ch1 cc2e12fb5c ... Ch20 be28390b9d). Duplicates line now: `4080 family copies, 174 dropped (168 placement-actor
cards hidden now; 6.5 ms, once)`. Structure-set screens before (`dink.FamilyDuplicates=0`) and after
(`structure_sets_before_after_bd6d227a.jpg`, looked at): the 440 two-storey house with its fence runs, the Goodheart castle walls of 400
and the 441 cottage yard with its fence are identical; only the doubled trees changed (the 440 oak and a 441 oak are single).

## Re-verified on master 5ccf38dd (16 Nov, final head)

Rebased on 5ccf38dd (#166 placed effects in `DressActor`, #194 rows, #146/#150 exporter). Conflict in `DressActor` resolved so the
placed-effect return of #166 comes first and the A208 drop after it; `DinkFamilyDuplicates.cpp` now also leaves out every row with an
`effect` (placed fires and sparkles are a card per placement, never merged). Copy synced with fresh timestamps (the build compiles
`DinkArtFamilySubsystem.cpp` and `DinkFamilyDuplicates.cpp`), built (0 warnings), world regenerated with `--export` and `--region
stonebrook`. `Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe` **124/124** (832 s); **all twenty probe md5s equal master's
table** (Ch1 cc2e12fb5c ... Ch20 be28390b9d). Duplicates line: `4105 family copies, 174 dropped (168 placement-actor cards hidden now;
6.6 ms, once)`. `structure_sets_before_after_5ccf38dd.jpg` (looked at): the 440 house with its fence runs and the castle walls of 400 are
identical before and after (only the doubled 440 oak becomes one). Not seen in a frame: a placed fire of #166 (the views of 427, 439 and
161 show none in either run); they are excluded from merging in code.

## Not checked

The packaged build; screens not in the capture list (the rule applies world-wide: 175 copies); a script that hides the kept copy
while its neighbour screen is visible (the dropped copy stays hidden, as written in AGENTS.md); `art_coverage.py` is unchanged on
purpose (both copies stay `final`).
