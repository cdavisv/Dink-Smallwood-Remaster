# Dragon remains, pictures 216 and 212 (GP-Q7), 23 Nov 2026

## What changed
- `SM_Dragon_Corpse_PR` (corpse kit, `SourceAssets/Art/PhotorealPass/Corpses/Dragon_Corpse`) is rebuilt as **v4**, laid out as
  picture 216 shows the remains (mesh frame: +X screen right, +Y north): the dragon on its side with its back to the north, the
  belly torn open towards the camera (ribs standing over raw muscle, entrails run out to the south), neck and head along the
  ground to the west, the long tail curled round from the east to the south, **one** wing lying on the ground to the south,
  the other torn off. The hide keeps the brown and orange of the living dragon: blood only at the wounds and where the body
  lies in the pool (v3 soaked the whole hide and was rejected in the game on 23 Nov: "a red star of flat shards with two pale kites").
- The pool is drawn in the one blood look of the knight's pool and the placed splats (`gore_sheets.blood_sheet(look='fresh',
  **FRESH_1997)`; `gore_sheets.py` here is byte-identical to the file in #216 and #224). The pool card is 3.1 m: the grass
  clearing opens only under props up to 3.2 m (`environment.json` `clear_max_span_cm`), v3 was 4.2 m and its pool lay under the grass on 238.
- `Corpses/tools/build_gore.py` `dragon()` rewritten (pose bone by bone, every bone sunk onto the ground by its own lowest point,
  `membrane()` for the wing, `vattr()`); new `Corpses/tools/fbx_lods.py`: LOD1 / LOD2 are authored in the FBX with the thrown
  chunks kept whole (14,015 / 7,178 / 5,391 triangles; the engine's reduction pulled the chunks in and the kit import refused the mesh).
- `families.json`: a row for picture **212** (S100_P34, S238_P12; the same mesh turned half round, as 212 shows the remains from
  the other side) with `offset_cm` S100_P34 `[0, -170, 0]` (at its origin the remains stood inside the south wall block of
  screen 100); the row of picture **216** (S158_P07) loses its half turn, the mesh now is that picture's layout.

## Seen in the game (copy `Saved/FableA`, 960 x 540 offscreen through `unreal_turn.sh`, three short capture sections)
`dragon_ingame.jpg`: the 1997 pictures beside the game.
- **158 (picture 216)**: at the play camera the remains read as the picture: orange-brown neck and head to the west, the tail
  curled from the east to the south, the red opened body with pale ribs, the grey-green wing going tan towards its bloody tip, the pool.
- **238 (picture 212, on grass)**: the clearing opens under the card, the pool lies on bare earth; tail curled on the left, wing behind the body, as 212.
- **100 (picture 212)**: the remains stand clear of the wall block (steep camera and from the north). The screen is dark.
- Three looks were needed (bottom row of the sheet): look 1 showed the wing cream-white (its baked colour sRGB 111, 127, 98 is
  shown about two stops brighter on the dry-earth screens) and the pool card (6 mm up) under the ground's own relief on 158;
  look 2 with the membrane at 0.3 of its colour and the card 2 cm up; look 3 (this commit) with the membrane at 0.16 and eight folds across the fan.

## Still below the picture (named, not hidden)
- The wing is the flat panel of the source mesh with straight edges; its folds are a normal map and dark creases and stay faint
  in the game; on the grass of 238, seen across the body, it is still pale in the sun.
- On 158 the east side of the pool card lies under the ground's relief; the pool's edge is a cut (alpha-tested) card, as the knight's.
- The flesh is one procedural muscle material over a union of lumps (glossy, no modelled anatomy beyond ribs, backbone, three loops of gut).
- 2.7 m across, the size of the sprite card: far smaller than the living dragon.
- On 100 the capture script's play camera sat inside the wall block; that placement was judged from the steep and the north camera only.

## Proof
See the pull request: clean build, `Dink.Art`, `Dink.Gore`, the probe's twenty md5s against
`Plugins/DinkParity/Docs/packaged_probe.md`, the python unit suite, all on master + this commit together with #215, #216 and #224.

## Not checked
- The 212 row in the play camera on screen 100 (see above). A kill of a living dragon is not touched: the creature class keeps its
  own corpse mesh (`Creatures/Dragon/SM_Dragon_Corpse_PR`).
- Rebuild: `DINK_CPU=1 ../tools/bl.sh ../../Corpses/tools/build_gore.py Dragon_Corpse` from `Unclaimed/dragon` (6 minutes with the
  bake on the CPU), then `../tools/bl.sh ../../Corpses/tools/fbx_lods.py Dragon_Corpse`, `python3 -I tools/make_kit_manifest.py` in
  `Corpses`, and the kit import `DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh`.
