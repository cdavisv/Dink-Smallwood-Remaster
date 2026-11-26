# Burn marks on the ground: a black scorch, not a grey cracked slab (picture 158 outdoors), 23 November 2026

**The fault.** The outdoor burn marks (picture 158 frames 1 to 3 as class `burn_hole_decal` of `environment.json`: screens
533 and 536, the yard of 439 after the fire; 26 placements) read in the game as a pale grey slab of cracked plates lying on
the grass (another stream's frame of screen 536, and sheet 01 here). Three causes, all in the decal set `BurnHole` of
`Props/Decals`:

- the decal material took the engine's default specular (0.5): a lit black decal is grey in the sun;
- the Voronoi crazing with its strong normal read as stone plates;
- the ash mask covered wide patches.

**The change.**

- `Props/tools/decals.py` `burn` / `burn_set` rewritten: each mark is a ragged black star (a solid black heart, short
  soot spikes thrown out of it, a singed brown rim torn by fine noise), ash only as sparse fine flecks, a shallow hollow
  with fine grain instead of plates, roughness 1. The set row carries `"specular": 0.0`.
- `Scripts/import_town_exteriors.py`: the decal sheet master `M_Decal_Sheet` gains a scalar `Specular` (default 0.5, so
  the blood splats keep their gloss); a set's `"specular"` sets it on that set's four instances.
- `Props/manifest.json`: its `decals` block is `decals.json` again. `T_Decal_BloodSplat_*` are untouched (decals.py
  rewrites them with other bytes on this machine: they were put back from git).

## Seen in the running game

Captured offscreen in the game on master `fd676f34d` + the integration tree of the effect drafts (copy `Saved/FableD`),
before (`Saved/PhotorealPass/fx5/G_*.png`) and after the decal set was imported (`fx5/G2_*.png`), eight frames each.

| sheet | what it shows | what I see |
|---|---|---|
| `1997_158_frames_1_to_3.png` | the 1997 pictures (4x) | small black blots with spikes, dark red-brown in them |
| `01_game_23nov_before_and_after.jpg` | top: before; bottom: after. Screen 536 from above and low over the grass, screen 533 from above and at the play camera | **Before**: a pale grey slab of cracked plates with white patches, as bright as dry earth. **After**: a black scorch with soot spikes and a brown singed rim, lying on the grass (536) and on bare earth (533); from low over the grass it is a black patch between the blades, at the play camera of 533 a small dark mark by the wall. It reads as a burn and as the 1997 picture |
| `02_new_sheet_over_grass_green.jpg` | the four variants of the new sheet composited over a flat green | four different stars |

## Still below the bar, not checked

- Flat: no burnt stubble standing in it, no depth. The dark red-brown of the 1997 blots is only in the rim.
- The grass is cleared in a square patch round the mark (the decal's footprint), paler than the lawn: as before this change.
- The yard of 439 after the fire (vision 2) and the remaining placements were not looked at; four variants only.

## How it was proven

Rebased mechanically onto master `6dd60a8c8` (world scale on) by art-finish-1 (Opus, 26 Nov), who changed no texture or
material and judged no look; only the `DinkRemasterUE/AGENTS.md` section conflicted (both kept). The scrub rewrote the source
path inside the three `T_Decal_BurnHole_*` packages. In copy `Saved/ArtFinish26Nov` (master + this change): editor build 0
warnings (no C++), game target 0 warnings, `Dink.Art+Dink.Gore` 99/99, `Dink.Gameplay.Probe` 29/29 with the twenty md5s equal
to the world-scale table of `packaged_probe.md` (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`). Kernel: no Oops.

**Frames for Fable** (`03_frames_for_fable_26nov_533_536.jpg`): the 1997 pictures 158 beside the marks of SCR_533 and SCR_536
at the play camera, from above and from the side, taken with art-fx-5's `sec_scorch2` script on the new master.
