# Art wiring audit (15 Nov 2026)

Owner's order (15 Nov, 18:15 PT): "check every visual that has been designed is actually in the game ... make sure all
art and animations WORK correctly". This folder records, for every delivered art source, whether it reaches the player
and, if not, why. It audits the wiring (import, binding, cook, draw, clip callers). It is not a look review: whether a
source is good enough to bind is an art decision for the Fable queue.

Tree: master `9cc796b6`. Tool: `DinkRemasterUE/Scripts/art_wiring_audit.py` (read-only, standard library; unit tests in
`Scripts/tests/test_art_wiring_audit.py`, 13 pass). Reviewed reasons for sources that do not reach the player:
`Scripts/art_wiring_known.json` (37 rows; add a row when you decide, drop it when you bind). Two runs on the same inputs
write byte-identical files.

Revised after the independent review of PR #154. The first version took bare asset names out of free-text notes and
`/Game` paths, counted editor-only C++ and `mesh_swaps` keys as bindings, and called every Unclaimed `STATUS.md` note
deliberate. Its "no hidden wiring faults" headline was wrong and is withdrawn. This version finds 15 rows that are
wiring bugs (A204-A207).

## How it was done

```
cd DinkRemasterUE
python3 -I Scripts/art_wiring_audit.py \
  --generated <copy>/Content/Dink/_Generated \
  --cooked <copy>/Saved/Cooked/Linux/DinkRemaster/Metadata/ReferencedSet.txt --cook-commit 0fd28846 \
  --scene-audit <visual sweep>/audit.jsonl --sweep-commit f92915fe \
  --coverage-csv <art_coverage.py output> --placements <copy>/ImportData/placements.json \
  --out Docs/Verification/ArtWiring_15Nov2026/art_wiring.csv --cards-out .../drawn_cards.csv --summary .../summary.md
```

1. **Sources**: every FBX/GLB under `SourceAssets/Art` (LOD files folded into one asset; `_build`, `Working`, `Previews`,
   `ThirdParty` skipped, path separators normalised first). Also every clip of the two `animation_manifest.json` files,
   the creature clip exports, and the flipbook/decal sets of the unclaimed kit. An asset exported by two streams is one
   row, and its `source` column lists every copy in sorted order.
2. **Imported**: a package of the same name (or `<name>_PR`) under `Content/`, every copy listed. `.uasset` bytes are read
   through the LFS store, so an unsmudged worktree works.
3. **Bound**: rows are checked against each of these roots:
   - String values of Data JSON that the runtime reads: a `dink-art/1` manifest (DinkArtSubsystem scans Data/Art for
     that schema), or a file whose name Runtime C++ uses. The rule is narrow:
     - a `/Game` path binds exactly the package it names;
     - a whole-string bare asset name binds only under the folder the runtime resolves it in (town houses), or only
       when the name is unique;
     - keys never bind (so `mesh_swaps` sources do not count);
     - `note`/`about`/`why`/`comment`/`name`/`id` fields never bind;
     - the `assets` validation lists of manifests never bind.
   - String literals of the **Runtime** C++ modules only (DinkCore, DinkNarrative, InkPlusPlus, the game module). The
     Editor modules (DinkImport, DinkParity) and the DeveloperTool module (DinkProbe) are excluded.
   - `Config/*.ini`.
   - The world maps of a regenerated `_Generated` folder.
   - Two composed paths (`SK_<Name>_Photoreal`).
   - Anything reached from one of the roots above through the package reference graph.
4. **Cooked**: the package is in `ReferencedSet.txt` of the newest packaged build: private copy `PlaythroughQA`, cooked 15
   Nov 16:48 from `0fd28846` (ec86f1e6 + #138). A package that commit did not have or bind is flagged `unverified`, not
   `not_cooked`.
5. **Drawn**: the mesh appears in the whole-world scene audit of the visual sweep (master `f92915fe`, 627 screens, one
   camera point each). A mesh that commit did not have or bind is `unverified`. Every bound mesh the sweep did not see
   gets a written reason, built from placements, vision and captured screens.
6. **Played**: a runtime caller asks for the clip (C++ literals, `_Timid`/`_Confident` pairs, `creatures.json` roles), or
   `animation_natural.json` `drop_prefixes` replaces it.
7. **Checks** on each imported mesh, its materials and textures:
   - an engine default or missing material;
   - a material instance pointing at a missing texture;
   - texture colour space against its suffix;
   - Nanite on masked foliage or hair;
   - one LOD over 5,000 triangles with Nanite off.
8. **Drawn cards**: every sprite card the scene audit saw above the ground, classed by its origin's placement (indoor
   cards use a lit material instance) or, without an origin, by its picture. These are joined with `art_coverage.py`
   origin states. The coverage run is that of master `6ef7a590`, which binds the same creatures as the sweep's
   `f92915fe`. The ducks, slimes and pig bound since by #113 are not re-checked here.

## Result (853 rows, `art_wiring.csv`; counts by kind in `summary.md`)

| flag | rows | meaning |
|---|---:|---|
| ok | 300 | imported, bound, cooked, and drawn in the sweep (meshes) or asked for at runtime (clips) |
| replaced | 26 | bound, and by design the runtime draws or plays another asset in its place: 16 Pass1 clips replaced by mocap (`drop_prefixes`, including `Jump_Start`, `Land` and the NPC walks), the headless manifest meshes (`SK_Mother`, `SK_Milder`, `SK_Dink`/`SK_Dink_Hands`, the old pillbug), the dense grass patches the tall ones replace, the screen-1 fireplace replaced by its refinement, and `mesh_swaps` sources that only authored manifests place |
| not_seen | 160 | bound and cooked but not in the sweep, each with its reason in `detail`: 104 `stonebrook_fields_471.json` meshes (screen 471 was not captured), 49 vista meshes outside the play screen, 3 family meshes whose placements are vision-gated (catapult, monument, note), 1 scripted placement, 1 burnable pine (`burnable`), 1 burnt cottage (`state_swaps`), and Milder's photoreal mesh (script-made character, story beat not played). **0 unexplained.** |
| unverified | 20 | added by PR #113 after the cook and the sweep (duck, slime, pig, gore meshes, their clips). Needs a cook and a sweep of current master. |
| lod | 10 | **A200**: drawn meshes with one LOD and Nanite off (corpse kit 15-55k triangles, three set pieces 6-9k). perf-stutter owns it. |
| bug | 15 | **A204**: brazier and candle light props never placed. **A205**: seven #113 creature clips no role plays. **A206**: `fence_rail_ew` draws the old kit fence. **A207**: the render-only vista draws old meshes (`SM_Grass_Meadow_01` 17 times on screen 1, oak, pine V3, boulder, cottage). |
| queued | 69 | an open branch or Fable row owns it (Structures Misc/Castle and Stonebrook yard pieces VS-01/02/05/14; chests VS-07; effects and decals GP-Q6, GP-Q9, VS-08, VS-11, DS-06; GP-Q5) |
| alternate | 195 | a finished source beside the bound asset, waiting for an art decision: DS-01 (22), DS-03 (13), DS-02 (2), DS-05 (158) |
| documented | 36 | only the unclaimed kit's `STATUS.md` explains why it is out (rigged people and creatures whose review faulted the look, wall/shelf/table items, multi-sprite buildings, the clean corpses). Written down but not reviewed here; the VS-03/04 and GP rows cover most. |
| deliberate | 8 | a reviewed reason (table-top fruit, the town house's unused narrow wall, the door header and right jamb, the screen-1 ceiling listed only for its size check, a diagnostic export) |
| superseded | 13 | another delivered asset of the family is the one shown (scatter clusters, Codex refinements on screen 1, `AN_Dink_Fist`, the slime splat colour variants, `SM_Pine_Stonebrook_01`) |
| not_imported | 1 | `SM_Slime_Trail` (A205) |

Other checks:

- **Cook**: of the 524 bound packages, 504 are in the 16:48 cook. The other 20 are the #113 packages that commit did not
  have (`unverified`), so no bound package that existed at the cook is missing from it. `package.sh` cooks every
  `Dink/*` content folder, `Characters` (the mannequin mocap clips) and `Input`. `Data` is staged as files.
- **Textures**: 819 textures under the art folders. 755 match a suffix rule (normal / mask / colour / emissive mask); 0
  are flagged. The other 64 have no suffix the tool can judge and were not checked by it.
- **Materials**: 0 art meshes on an engine default material; 0 material instances with a missing texture (all imported
  meshes and their direct materials).
- **Clips**: 14 of the 30 Pass1 clips are asked for by the C++. 16 are replaced on purpose by the mocap clips; the mocap
  `MM_Jump` plays for the jump, so `AN_Jump_Start` is unused by design. 7 pig and pillbug clips play through
  `creatures.json`. Of the 15 duck and slime clips that #113 imported, 8 play (`unverified` until a cook/sweep) and 7
  play nowhere (A205).
- **Cards over final art**: 728 drawn cards. 644 carry an origin ID, and 0 of those sit on an origin `art_coverage.py`
  counts final. The 84 decor and instanced cards carry no origin and are outside this check.

## Findings

| row | what | owner |
|---|---|---|
| A200 | ten bound meshes with one LOD, Nanite off | perf-stutter (branch `perf/stutter-framerate` carries the LOD script) |
| A201 = A55 / PQ-Q2 | north-south and diagonal fence cards. First bind the split-rail module per angle with `span`/`yaw_offset` (in-game fit check); PQ-Q2 new art only for angles that do not fit | art-wiring-audit sub-agent, branch `fix/fence-runs` |
| A202 | scripted placements of bound classes still draw cards: thorn S192_P05, willows S414_P02/S446_P02, pine S534_P10, cabinets S003_P15/P16. S474_P01 (nut tree) and S693_P06 (giant oak) stay with VS-10 | branches `fix/art-wiring-scripted-static` (thorn; the willows wait for A208) and `fix/family-script-allowance` (pine, cabinets) |
| A208 | one object placed on two screens is drawn as two family meshes (about 200 pairs drawn twice in the sweep: willows, pines, oaks, forest strips, dungeon walls, statues, boulders) | sub-agent branch `fix/family-duplicates` |
| A203 / DS-04 | no weapon meshes. 1997 shows the armed weapon in idle, walk and attack, so the attach must show it in all three while armed | Fable (meshes), then code |
| A204 | brazier and candle light props loaded but never placed | open: needs a placement rule |
| A205 | duck Death/HeadlessDeath/Hit/Peck/Quack and slime Attack/Death clips imported, played by no role; `SM_Slime_Trail` not imported | creature stream / anim-motion |
| A206 | `fence_rail_ew` family row draws the old stylised kit fence; the photoreal one is only swapped in on authored screens | branch `fix/fence-runs` |
| A207 | context (vista) manifests skip `mesh_swaps`: old grass, oak, pine, boulder and cottage drawn around Stonebrook | open: one swap call in `ADinkArtContextActor`, needs a look through SCR_001/439 windows |
| DS-01 | StonebrookRuins kit (burning 439, burnt SCR_001 interior) never imported. GP-Q5 owns the Mother's body S001_P34 and burn holes S001_P44-P49 | Fable decision |
| DS-02 | interim dungeon ivy/breach walls never imported; plain stand-ins drawn | Fable decision |
| DS-03 | Stonebrook440 house + farm tools + yard never imported; competes with VS-01's two-storey cottage | Fable decision |
| DS-05 | 158 alternate sources to keep or delete | Fable decision |
| DS-06 | hearth fire and sparkle flipbooks never imported. The hearth of 163 is drawn as a card; the sparkle placements were not seen drawn | Fable |

`drawn_cards.csv` lists every drawn card class with its screens and the delivered meshes made for it (70 classes have
one). Most are owned elsewhere:

- monsters: VS-03/VS-04 (rigged, not imported; their review faulted the look);
- cottages, castle, huts, bridges, wells: VS-01/02/05/14;
- chests: VS-07;
- holes: VS-08;
- trees: VS-10;
- fountain: VS-11;
- corpses: GP-Q1..Q7;
- blood and burn decals: GP-Q6.

The scripted boulders and script-made people are rows VS-15 and VS-16 of PR #148 (not merged: pending).

## Not checked

- Nothing here was run in the game. The columns come from packages, manifests, the 16:48 cook's reference set and the
  sweep of master `f92915fe`. A cook and a sweep of current master are needed to settle the 20 `unverified` rows.
- Not looked at: T-pose or anim-instance state of skeletal meshes at runtime, hair, cloth, LOD switching distances
  (anim-motion and hair-cloth-physics streams).
- The sweep did not capture 17 screens (471 among them). It audited one camera point per screen and only the story state
  at entry.
- 64 textures without a judgeable suffix.
- No look judgement: whether an alternate or interim source is better than what the game shows is for Fable.

## Files

| file | what |
|---|---|
| `art_wiring.csv` | one row per delivered source or unclaimed art package: asset, kind, stream, source (every copy), exported, imported (every package), bound (root or `via`), cooked, seen (sweep screens, clip caller, or player pawn), flag, detail (checks, stale twins, the not-seen reason), reason, covered_by |
| `drawn_cards.csv` | drawn sprite cards per class: count, how many carry an origin, screens, cards on final origins, family row, meshes made for the class |
| `summary.md` | counts by flag and by kind, texture coverage, card coverage, unexplained not_seen rows |
