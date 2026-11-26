# GP-Q7 rest: placed pillbug splats and duck heads take the creature classes' meshes (26 November 2026)

Rows made by art-gore-5 / art-gore-6 (Fable 5.2, 23 Nov; not seen there). Brought onto master `6dd60a8c8`, proven and captured
mechanically by art-finish-1 (Opus, 26 Nov), who changed nothing and judged no look. **FRAMES FOR FABLE.** Keep all original gore.

- `families.json` row `pillbug_corpse`: the three PLACED pillbug splats (141 on S098_P04 and S100_P26, 143 on S100_P25) draw the
  burst carcass a killed pillbug leaves (`SM_Pillbug_Corpse_PR`, class scale 0.55) instead of the 1997 picture on a card. A placed
  carcass lies without the class corpse's blood-pool decal (only the creature layer spawns it).
- `families.json` row `duck_head`: the ninety duck heads of SCR_145 (121, frame 1) draw the severed head a struck duck leaves
  (`SM_Duck_Head_PR`, scale 1.5).
- Not in this change: a mesh for `duck_corpse` (two placements); the stone giant, bonca and slayer follow-ups.

| sheet | what it shows |
|---|---|
| `01_frames_for_fable_26nov_pillbugs_and_duck_heads.jpg` | the 1997 pictures 141, 143 and 121 beside S098_P04, S100_P25/P26 and SCR_145 at the play camera, close and from above |

Captured with art-gore-6's `cap_q7rest_r1.txt` (coordinates guessed from the origins; output folder changed only).

Proof in copy `Saved/ArtFinish26Nov` (master `6dd60a8c8` + this change): editor build 0 warnings (no C++), game target 0
warnings, `Dink.Art` 88/88, `Dink.Gameplay.Probe` 29/29 with the twenty md5s equal to the world-scale table of
`packaged_probe.md` (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`). Kernel: no Oops.
