# Art wiring audit (15 Nov 2026)

Owner's order (15 Nov, 18:15 PT): "check every visual that has been designed is actually in the game ... make sure all
art and animations WORK correctly". This folder answers the first half for every delivered art source: does it reach
the player, and if not, why. It is an audit of the wiring (import, binding, cook, draw, clip callers), not a look review:
whether a source is good enough to bind is an art decision and goes to the Fable queue.

Tree: master `6ef7a590` (PRs #129, #138, #152 merged). Tool: `DinkRemasterUE/Scripts/art_wiring_audit.py` (new, read-only,
standard library; unit tests `Scripts/tests/test_art_wiring_audit.py`, 8 pass). Reviewed reasons for the sources that do
not reach the player: `Scripts/art_wiring_known.json` (19 rows; add a row when you decide, drop it when you bind).

## How it was done

```
cd DinkRemasterUE
python3 -I Scripts/art_wiring_audit.py \
  --generated <copy>/Content/Dink/_Generated \
  --cooked <copy>/Saved/Cooked/Linux/DinkRemaster/Metadata/ReferencedSet.txt \
  --scene-audit <visual sweep>/audit.jsonl --coverage-csv <art_coverage.py output> \
  --out Docs/Verification/ArtWiring_15Nov2026/art_wiring.csv --cards-out .../drawn_cards.csv --summary .../summary.md
```

1. **Sources**: every FBX/GLB under `SourceAssets/Art` (LOD files folded into one asset; `_build`, `Working`, `Previews`,
   `ThirdParty` skipped; an asset exported by two streams is one row naming both), every clip of the two
   `animation_manifest.json` files and the creature clip exports, and the flipbook/decal sets of the unclaimed kit.
2. **Imported**: a package of the same name under `Content/` (the `.uasset` bytes are read through the LFS store, so an
   unsmudged worktree works).
3. **Bound**: named by a runtime manifest (`Content/Dink/Data/**/*.json` by `/Game` path or bare asset name, e.g.
   `town_houses.json`), by C++ or `Config/*.ini`, by a world map of the regenerated `_Generated` (world maps place the
   kits), or reached from those through the package reference graph (mesh -> material -> texture). Two packages the C++
   loads by a composed path (`SK_<Name>_Photoreal`) are listed in the script.
4. **Cooked**: the package is in `ReferencedSet.txt` of the newest packaged build on the machine (private copy
   `PlaythroughQA`, cooked 15 Nov 2026 16:48, master ~ec86f1e6 + #138).
5. **Drawn**: the mesh appears in the whole-world scene audit of the visual sweep (`dink.SceneAudit`, 627 screens, master
   `f92915fe`). Clips: does any runtime caller ask for the clip (C++ `TEXT("...")` literals, composed `_Timid`/`_Confident`
   pairs, `creatures.json`/`characters.json`/`hero_actions.json`), or does `animation_natural.json` `drop_prefixes`
   replace it.
6. **Checks** on every imported mesh, its materials and textures: engine default or missing material, a material
   instance pointing at a missing texture, normal maps not `TC_Normalmap`/linear, mask maps sRGB, colour maps linear,
   Nanite on masked foliage or hair, one LOD over 5,000 triangles with Nanite off. Every Nanite mesh's base materials were
   also listed (275 meshes; the only water ones use `MI_Fields_StreamWater`/`M_Env_Water`, both opaque; A16 covers the
   rest).
7. **Drawn cards**: every sprite card the scene audit saw above the ground (620 cards, 84 classes; 66 decor cards parked
   under the ground are not counted), joined with `art_coverage.py` origin states (run in a smudged private copy: in an
   unsmudged worktree it counts the Mother S001_P26 placeholder because `SK_Mother` is a pointer) and with the sprite
   classes each unbound or unimported source was made for.

## Result

842 rows (`art_wiring.csv`; `summary.md` has the counts by kind).

| flag | rows | meaning |
|---|---:|---|
| ok | 320 | imported, bound, cooked, and drawn in the sweep (meshes) or asked for at runtime (clips) |
| not_seen | 179 | bound and cooked but not in the sweep's scene audit: 105 `stonebrook_fields_471.json` meshes (screen 471 was not captured), 49 vista tiles outside the play screen, story-state art (burnt pine, burnt cottage, vision-gated catapult S489_P01, monument S536_P01, note S006_P24), headless-only meshes (`SK_Mother`, `SK_Milder`, `SK_Pillbug`) |
| lod | 10 | **A200**: drawn meshes with one LOD and Nanite off (corpse kit 15-55k triangles, three unclaimed set pieces 6-9k) |
| queued | 64 | an open PR or Fable packet owns the work (duck/slime #113; Structures Misc/Castle kits and Stonebrook cottage/yard/well pieces VS-01/02/05/14 on branch `art/gate2-static-structures`; chests VS-07 / presentation-fixes) |
| alternate | 194 | a finished source beside the bound asset, waiting for an art decision (DS-01, DS-02, DS-03, DS-05) |
| deliberate | 65 | a written decision keeps it out (Unclaimed `STATUS.md`: wall/shelf/table items, multi-sprite buildings, partial creatures, the clean corpses that are less gory than 1997; the town-house narrow wall; a diagnostic export) |
| superseded | 10 | another delivered asset of the family is the one shown (scatter clusters, Codex refinements on screen 1) |

What the audit did **not** find (each checked over all 509 bound packages):

- **Cook**: 0 bound packages missing from the packaged build. `package.sh` cooks every `Dink/*` content folder,
  `Characters` (the mannequin mocap clips) and `Input`; `Data` is staged as files.
- **Materials**: 0 art meshes on an engine default material; 0 material instances with a missing texture.
- **Textures**: 778 textures, all with the right compression and colour space (`_N` normal map linear, ORM/mask linear,
  colour sRGB); the lava `_E` map is a linear mask by design (`import_environment_materials.py`: `E.r` drives the glow).
- **Clips**: of the 30 Pass1 clips, 14 are asked for by the C++ (`Fist_*` timid/confident pairs, `Sword_Slash_1/2`,
  `Sword_Chop`, `Bow_Draw`, `Bow_Release`, `Cast`, `Hurt`, `Stumble`), 16 (`Idle_*`, `Walk_*`, `Run_*`, `Shuffle`, `Fall`,
  `Land`, `Jump_Start`, `NpcF_*`, `NpcM_*`) are replaced on purpose by the motion-capture clips of
  `animation_natural.json` (`drop_prefixes`; the mocap `MM_Jump` plays for the jump, so `AN_Jump_Start` is unused by
  design, not by a wiring fault); `AN_Dink_Fist` is the superseded candidate of `Characters/Animations/Unarmed`. The 7
  pig and pillbug clips are played through `creatures.json`. The 13 duck and slime clips are not imported on master
  (PR #113).
- **Cards over final art**: 0 of the 620 drawn cards sit on an origin `art_coverage.py` counts final (the 9 `Card`
  components on screens 1 and 439 carry their replacement meshes, not sprites).

## Findings (bug rows A200-A203, Fable rows DS-01 to DS-06)

| row | what | owner |
|---|---|---|
| A200 | ten bound meshes with one LOD, Nanite off (corpses up to 55,020 triangles) | perf-stutter |
| A201 | 30 north-south and diagonal fence cards drawn (`fence_rail_ns`, `_diag_nw`, `_diag_ne`); the split-rail module is bound only for east-west runs; `span: height` + `yaw_offset` could lay it without new art | physical-mapping fix PR (owns the fence span rows) |
| A202 | scripted placements whose script never changes the picture keep their card (thorn S192_P05, willows S414_P02/S446_P02, talking pine S534_P10, big willow S149_P02, cabinets S003_P15/P16): the family layer allows scripted placements per class only | data fix for thorn/willow (follow-up PR of this stream); per-script allowance in `UDinkArtFamilySubsystem::Decide` + `art_coverage.py` for the rest |
| A203 / DS-04 | no weapon meshes: the sword and bow clips play with empty hands; 1997 shows the armed weapon in idle, walk and attack | Fable (meshes), then code (attach) |
| DS-01 | StonebrookRuins kit (burning 439 with fire sockets, burnt interior of SCR_001, the Mother's remains) never imported | Fable decision |
| DS-02 | interim dungeon ivy/breach wall modules never imported; plain stand-ins drawn | Fable decision |
| DS-03 | Stonebrook440 house + farm tools + yard never imported; competes with VS-01's two-storey cottage for the worst card of the sweep | Fable decision |
| DS-05 | 194 alternate sources (shared vista, beach pebbles per frame, barrel V4, trousers V33, Mother clothing V1, photoreal-pass barrel/feed sack/fireplace) | Fable decision: keep or delete |
| DS-06 | hearth fire and sparkle flipbooks never imported; cards drawn | Fable |

`drawn_cards.csv` lists every drawn card class with the screens and the delivered meshes made for it (58 classes have
one). Most are owned: monsters VS-03/VS-04 (rigged, not imported: their last review faulted the look), cottages, castle,
huts, bridges, wells VS-01/02/05/14, chests VS-07, holes VS-08, trees VS-10, fountain VS-11, scripted boulders VS-15
(binding the field boulders was tried and dropped), people made by scripts VS-16, corpses GP-Q1..Q7, blood/burn decals
GP-Q6.

## Not checked

- Nothing here was run in the game: the columns come from files (packages, manifests, the cook's reference set, the
  sweep's scene audit of master `f92915fe`). In particular T-pose / anim instance state of skeletal meshes at runtime,
  hair and cloth, and LOD switching distances were not looked at (anim-motion and hair-cloth-physics streams).
- The sweep did not capture 17 screens (471 among them) and audited one camera position per screen; story states other
  than the one at entry were not audited.
- The cooked set is the 16:48 packaged build of the `PlaythroughQA` copy, not a cook of `6ef7a590`.
- No look judgement: whether an alternate or interim source is better than what the game shows is for Fable.

## Files

| file | what |
|---|---|
| `art_wiring.csv` | one row per delivered source: asset, kind, stream, source, exported, imported, bound (root or `via`), cooked, seen (sweep screens, or clip caller), flag, detail, reason, covered_by |
| `drawn_cards.csv` | drawn sprite cards per class: count, screens, cards on final origins, family row, meshes made for the class |
| `summary.md` | counts by flag and by kind |
