# Gate 2 static batch 1 (13 and 14 November 2026)

Props at the size the 1997 sprites show them, sprites that scripts create, thorn hedges, signposts, shells, potions.
Visual only: collision, hardness, scripts, warps and origin IDs are untouched.

All sheets are from the running game (a private project copy, offscreen, 1280 x 720). "before" is master `cb842dd2`
(the captures of the faceting sweep), "after" is this change. Each placement is shown from the play camera's height and
close up.

## Coverage (`Scripts/art_coverage.py`)

| | final | placeholder | cut |
|---|---:|---:|---:|
| master `8ba0e903` | 4093 | 2362 | 152 |
| this change on that master | 4421 | 2034 | 152 |
| master `8905d4f8` (screen grounds counted) | 4335 | 2120 | 152 |
| this change on that master | 4663 | 1792 | 152 |

328 placements turn final: thorn hedges 138 (124 `thorn_bush`, 11 and 3 on the two frame rows), clams 66, starfish 47,
signposts 30, potions 35, and 12 scripted bushes, weeds and round tables. The regenerated ledger (`doc/remaster/ALPHA_GATE2_BACKLOG.md`)
is made on master `8905d4f8`.

## What each sheet shows and what I see

| Sheet | Shows | Seen |
|---|---|---|
| `boulders_size_before_after.jpg`, `placements_boulders.jpg` | the five unclaimed boulders rebuilt 1.7 times larger; screen 244 and 671 before and after | Boulders stand about as high as the hero, as their sprites do, textured and smooth. The two rock mounds of screen 671 are the large boulder now: hero-high like the sprite, but pale grey where the sprite is a dark cone. Before: grey faceted lumps (default material). The white pair still shows a few flat planes close up. |
| `field_boulders_ao_before_after.jpg` | the three field boulders before and after the occlusion rebake | The black patches on every shaded face are gone; shaded sides read as rock in shadow. On the mossy boulder of screen 244 one dark crevice of a few centimetres remains between two strata at the moss edge. |
| `stumps_thorns_before_after.jpg`, `placements_stumps.jpg` | stumps and thorn bushes, old and new mesh; a stump on screen 179 | The root flares are rounded and mossy instead of flat pointed fins. In the grass the stump reads as a stump. |
| `placements_thorn.jpg` | thorn hedges on screens 26, 59, 60 | Two or three tangles of smooth thorny canes fill the width of each card, with thorns visible close up. They are lower (0.7 to 1.5 m) and more open than the sprite's wall of dark coils, and the canes are of one brown; still far better than the stretched card. |
| `placements_sign.jpg` | signposts on screens 132, 244, 65, 184 | Weathered posts with one, two or three boards, real size (2.3 m), standing on the ground; the cards were 6 m tall. |
| `placements_shells.jpg` | clam clusters and starfish on screens 258, 351, 257 | Close up: bedded clams and an orange starfish, clearly shells. From the play camera they are small (15 to 46 cm) and in two of the play shots the hero stands on them. Screens 257 and 258 are very dark (known, the ground review). |
| `placements_potions.jpg` | red, purple and blue potions | Glass flasks with a cork and coloured liquid, visible from the play camera. |
| `placements_scripted.jpg` | scripted bush, weed sprig, round table; the gold heaps of screen 352 | Bush, sprig and table are meshes now. Before, the gold heaps of screen 352 are grey domes under grey cylinders; after, gold heaps and nothing above them (see "Grey cylinders"). |
| `script_sprites_0.jpg` | gold and a small heart created by `make.c` beside the hero | A small gold heap and a red heart lie in the grass where the script dropped them; no cylinder. They are small from the play camera. |
| `behaviour_story5_screen446.jpg` | screen 446 before and after `&story` 5 | The scripted bushes leave with their sprites: the mesh goes with its actor. |
| `behaviour_touch_0.jpg` | hero beside a thorn hedge and two potions | Proves nothing about touch: the hero did not walk in the capture. Kept only as close views. |
| `new_meshes_0.jpg` | every new or changed mesh alone on grass | Textured, smooth shaded, none drawn with the default material. |

## Grey cylinders

A sprite made by `create_sprite` was a grey cylinder. Two kinds were on screen:

1. the pickup itself (gold heap, heart, potion): it now shows the mesh of its picture's family;
2. the twinkle a gold heap's script creates over the heap (sequence 165, brain 15, bound to the heap by `sp_brain_parm`).
   The first capture of this change still showed that cylinder above every heap. It has no art, so its marker is now hidden while the sprite it rides on shows a family mesh.

**Not drawn: the twinkle itself.** The 1997 game shows a small animated sparkle on gold. It needs an effect, not a
mesh; until then gold lies still. That is a difference from 1997 for the owner to accept or to order an effect for.

## Left unbound, and why

- `island_totem_pole` (10): the only mesh is a thin torch pole; the sprite is a thick carved totem.
- `fireplace_brick` (3): the mesh is grey fieldstone at half the size of the red brick sprite.
- Scripted willows, the scripted oak and `cabinet_wood` placements with scripts: two earlier captures show a tree
  where master shows no card at all; not understood, so not bound.
- `chest_small` (14, scripted): `SM_Chest_Small_PR` and `_Open_PR` exist and look right, but the chest must open with
  its sprite; the next change.

## Tests

- `Scripts/test.sh Dink.Art`: see the pull request text for the counts of the final build.
- `Scripts/test.sh Dink.Gameplay.Probe` on a world regenerated by the current importer: the twenty chapter md5s equal
  `Plugins/DinkParity/Docs/packaged_probe.md`.
- `python3 -m unittest discover -s Scripts/tests`.

## Not checked

- Pickup by touch in a capture (see `behaviour_touch_0.jpg`). Script sprites are covered by the PIE test
  `Dink.Art.Family.ScriptSpriteShowsFamilyMesh`; placed potions keep the 1997 touch box and their scripts.
- Thorn touch damage in a capture (the hardbox and the script are unchanged).
- The 126 thorn placements beyond the screens above, the 47 stumps beyond screen 179, and shells on screens other
  than 257, 258 and 351 were not looked at one by one.
- A packaged build.
- One crash was seen once in a capture run on entering screen 64 (slimes and a pillbug): a read of a freed skeletal
  mesh in `UDinkHumanoidComponent::TickComponent`. It did not happen again when the same screen was entered later; this
  change does not touch skeletal meshes. Reported to the coordinator.
