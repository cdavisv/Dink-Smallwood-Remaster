# People and Seth as 3D figures: townsfolk, guards, the gnome wizard, the King, the last enemy (15 and 16 November 2026)

The human sprites of the map (old figure of screen 2, peasants, maidens, girls, merchants, knights, the soldier, the
gnome of screen 6, King Daniel) and the people scripts make were 1997 sprite cards; Seth was a grey cylinder and, since
#148, his 1997 pose card. This change draws them as 3D figures. Presentation only: scripts, brains, hardness, talk, hit
and touch boxes and origin IDs are untouched, and the layer is off in headless runs.

## How they are bound, and why it changed

The first version (15 Nov) wrote 43 origin rows into `characters.json`. Its probe run failed 7 of 29: not a crash. An
origin row gives the actor a drawn body, and `UDinkGameplay::UsesAuthoredGeometry` then talks to, hits and touches it by
that body (1.5 m in front of Dink) instead of the 1997 boxes; the story probe talks to the gravedigger of SCR_408 from
25 px (1.8 m) and no longer reached him. Every later chapter failed only because chapter 1's save was missing.

Now each figure is a **class row of `creatures.json`** (`Scripts/bind_people_classes.py`, 20 rows): every placement of
the sprite class and every sprite a script makes or dresses with the figure's walk pictures is shown by the figure; a
class row adds no body, no collision and no actor tag. `characters.json` equals master's. The probe passes with all
twenty chapter hashes unchanged.

## Sheets (all from the running game unless they say Blender or 1997; sheets 20 to 24: master `84e045b0` + this change, sheets 25 to 31: master `735b78a0` + this change, 16 Nov)

| Sheet | What it shows | What I see |
|---|---|---|
| `00_people_1997.png` | the 1997 graphics | first frame of each human walk base |
| `01_master_play_camera.png` | master, play camera (visual sweep) | the cards this change replaces |
| `20_king_and_knights.jpg` | 1997 picture, front, bust, from behind | **King**: seated facing the hall on a wooden throne with a red back and gilt finials, red robe, purple cloak with an ermine collar, crown, grey beard, green footstool: the 1997 picture. **Blue guards** (287 and 289): they face as their pictures do, the two rows towards the aisle. Dark navy harness, halberd pole upright beside the body. **Silver knight** (the gravedigger of 408): pale steel in daylight. The red knight's three frames are inside a pine: that placement is a parked sprite, see `25`. |
| `21_women_and_old.jpg` | same | **Girl** (126): pink-red dress with white dots, blonde ponytail, flowers and basket in her hands: the 1997 picture. **Blue maiden** (4): this is the capture BEFORE the skin fix: a red patch on her right arm (see "Rejected and rebuilt"); `26` shows her after. **Old figure** (2): brown hooded robe, staff, grey hair and a long grey beard. The red maiden's row is empty for a 1997 reason: the only red maiden of the map (S122_P09, `s7-mom`) is `sp_nodraw`, a voice without a picture; the red maidens of the game are script-made (see `26`). The brown maiden of 410 needs `&nuttree == 1`. |
| `22_men.jpg` | same | **Merchant** in blue with a brown mantle, belt and pouch; **merchant in green** (in a dark cave room); **peasant** with straw hat, cream smock and pole; **gnome wizard** with the purple star hat, yellow sleeves and grey beard: each the 1997 picture's clothes. **Silver knight** of 568 in polished steel. The soldier is not on his screen at the start of the game. |
| `23_halls_play_camera.jpg` | play camera in the castle hall (screens 102 and 70 are one room) | From the door: two rows of four guards facing the aisle, the King on his throne at the end, facing the player. This is the 1997 throne room, in 3D. (Bottom left: the gatehouse of #184, where `Goto 102` at the screen edge left the hall.) |
| `24_play_camera.jpg` | play camera on nine screens | 2 the old figure in the shop, 38 the peasant by the hearth, 126 the girl, 290 the merchant, 408 and 568 the silver knights by their fences: figures that stand on the ground, lit and shadowed like the hero. |
| `25_red_knight.jpg` | the robbery of screen 374 (`dink.Vision 374 1`, as `s1-rob` does one time in five) | **Red knights**: both robbers in a full harness of dark crimson with a closed helm, a mail skirt and a halberd, the traveller in blue between them. The colour is the dark maroon of pictures 271 to 279 and 712, no longer the kit's magenta. The plates are smooth and glossy, the visor is a dark gap with nobody behind it, the pole stands beside the hand. Last frame: the red knight of screen 241 in a pine. He is picture 712 placed at y 564, below the 400 px playfield: a sprite 1997 parks out of sight, drawn here on the neighbouring screen (not checked whether master's card stands there too; queue row SP-08). |
| `26_maidens.jpg` | the blue maiden of screen 4 after the skin fix; the bar of Terris (screen 34) | **Blue maiden**: no red patch on either arm any more; dark blue dress with puffed sleeves, hair in a bun. **Bar of Terris**: `s2-bar` makes three sprites and their scripts dress them by walk base; all three are figures: the wench in the red dress (walk base 220 = the red maiden), an old man in a red hooded robe and one in a straw hat at the table. This is the proof for script-made townsfolk. Against the 1997 picture her hair is too dark and too short (1997: long yellow hair). |
| `30_seth.jpg`, `30_seth_1997.png`, `33_seth_1997_walk.png`, `32_seth_blender.jpg` | Milder's last scene on SCR_086 (`s7-mil` talk, "Take his advice"), his 1997 pictures, the Blender review | **Seth** appears north of Milder (who lies in his blood, as in 1997) as a figure: the hero's body, taller than Dink, a head twice too large, dark red jerkin over slate-blue sleeves, blue trousers, brown boots, the hero's pack on his back (the 1997 walk pictures show the same pack). He stands through the talk, then `s7-boss` walks him at Dink; his explosion is still the 1997 picture card. His eyes have irises (the hero's eye material). Against the 1997 pose: the face is the hero kit's boy, not the grown man of the photograph; the hair is a mop, not the tall swept crest; red cuffs where 1997 has brown gloves; arms hang, not crossed. |
| `31_milder_satin_plate.jpg` | Milder by the pond after the plate roughness change | Gauntlets, pauldrons and knee cops are dull grey steel from the front; from behind a gauntlet still takes a pale green from the grass, far weaker than the bright green mirror of #156. The mail skirt reads as mail. The knee cops still have a jagged white rim from behind (queue row SP-07). The frame "full" is a hill in front of the camera, kept as shot. |
| `10_close_frames_14nov.png`, `11_knights_14nov.png` | the first import (14 Nov), kept for the record | superseded by 20 to 22 |

## Checks (master `735b78a0` + this change, 16 Nov; master's later #185 touches the title menu and audio only)

- `Scripts/test.sh Dink.Art+Dink.Animation+Dink.Movement`: 91 of 91 passed.
- `Scripts/test.sh Dink.Gameplay.Probe`: 29 of 29 passed; all twenty chapter hashes equal `Plugins/DinkParity/Docs/packaged_probe.md`
  (Ch1 `b4ad88c02c` to Ch20 `84f33687af`). The first version of this binding failed 7 of 29 here.
- `Scripts/art_coverage.py`: final 5502 -> 5557 of 6607 rows, placeholder 953 -> 898; `doc/remaster/ALPHA_GATE2_BACKLOG.md`
  regenerated (99 -> 83 open families). Still open: the two background red knights of screen 149 (baked background sprites).
- Import (`DINK_PHOTOREAL_ONLY=npcs`): 19 figures, 0 warnings.

## Rejected and rebuilt on the way

- **Everyone faced east** in the capture of 15 Nov: the King sat sideways to the hall, both rows of guards looked right.
  A standing sprite never gets a direction from its brain; the class layer reads it from the picture's sequence number.
- **The red knight was magenta pink** in daylight (the kit's red map). His map is now the blue knight's map turned to
  the dark maroon of pictures 271 to 279.
- **The maidens were the Mother with brown hair**; 1997 has two blondes and an auburn. Hair tints raised.
- **A red patch on the maidens' arms**: their younger skin set had been baked at 2048 px, the Mother's at 4096, and the
  bake packs the skin charts with a pixel margin, so the charts lay elsewhere and the mouth's red chart landed on the arm.
  Rebaked at 4096 on the Mother's layout (`NPC/Maiden/cfg/skin.json`).
- **Seth was first built as the gnome's twin** (dink.ini loads `people/gnome/green` at 581 to 589). Wrong: `s7-mil.c`
  loads `effects/magic/seth1w..9w` and `pose` over 580 to 589 before he appears. His real pictures are the hero's own
  body, 1.65 times as tall, in a dark red tunic over slate blue, with a head twice too large. Rebuilt from the hero's
  mesh (`Characters/Tools/seth_build.py`).
- **Seth's hair** hung over his brow as the hero's fringe, then stood up with a black hollow under it (the opaque cap
  lifted with the cards). The cap now stays on the skull and only the cards stand.
- **Milder's plate mirrored the meadow bright green** (roughness 0.4). `post_tex.py` `METAL_ROUGH`: satin 0.6.
- #148's 1997 picture card would have been drawn through a class figure: the card now yields to a class body
  (`DinkArtFamilySubsystem.cpp`, `DinkGreyboxSubsystem.cpp`, one condition each).

## Still below the bar

- **Close-ups of the ported people** (girl, merchants, peasant, gnome, old figure): plain smooth faces, hair as a
  modelled cap, simple hands, and **their eyes show no iris in the game**: pale balls under half-closed lids, although
  the Blender sources look right. Not found why (the eye map and its UVs are right in the exported FBX). At the play
  camera it does not show; in a dialogue close-up it would.
- **Knights**: smooth toy-like plates, nobody inside, the halberd stands beside the body instead of in the hand; the
  blue harness is near black in the dim hall. No attack clip: the fighting knights of 374 and 402 stand and walk.
- **The old figure of screen 2** is a bearded man in the 1997 art's own naming (`people/oldman`); the script calls her
  Ethel.
- **The King** is one piece with his throne: he does not move.
- **Seth**: the hero kit's young face, not the grown man's of the 1997 photograph; the hair does not stand up as his
  crest; no crossed-arms pose and no red flash; bare hands where the picture has gloves; trousers a clearer blue than
  the 1997 slate; he walks with the mannequin's walk at his size.
- **Maidens**: all three wear the Mother's bun; 1997 has long loose hair, yellow on the blue and the red one.
- No talking, sitting or working poses; no hair cards on the ported people.

## Not checked

- The soldier and the brown maiden (screen 410, `&nuttree == 1`) and the gold knight: not seen in the game.
- Script-made townsfolk were seen in the bar of Terris only (sheet `26`); the scenes of Joppa, KernSin and the Cast
  camp use the same mechanism and were not captured.
- The fighting knights' attack (no attack clip: they stand and walk) was not captured in a fight.
- Night, rain, low scalability levels, the packaged build.
