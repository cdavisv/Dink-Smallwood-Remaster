# Burn marks of the burning house as decals on roof and walls (439 and screen 1, vision 1), 23 November 2026

**What changed.** The burn patches of the burning house (pictures 155, 156, 157: three on the roof of 439, three on the
walls of the room of screen 1) were glowing heaps on camera-facing cards that floated in front of the surface. Now each
is projected onto what stands there:

- `"effect_decal": {"size_cm": [w, h], "depth_cm": d, "towards": "down|north|south|east|west", "origins": {...}}` on a
  placed-effect row (`UDinkArtFamilySubsystem::DressPlacedEffect`): the row's effect material is a deferred-decal
  material on a `UDecalComponent` at the card's middle. Presentation only.
- `FableF/burn_mark_fx` (`tools/build_burn_mark.py`, no Blender): three animated sheets, a torn black break with charred
  laths and the fire flickering behind them, bound as `MI_FX_Burn_Mark_A/B/C` (`M_FX_Flipbook_Decal`).
- The fires in depth that this draft used to carry were merged on their own (#236).

**The fault this draft was held for, and its cause.** In the game of 17 and 23 November the roof marks were black shapes
with stepped, blocky edges and a bright column down the middle (sheet 01). `never_stream` on the sheets and a fixed mip
did nothing, because the picture was never the decal's: the blocky black shape was the **magnified 1997 picture** on the
placement's own upright card, and the column was the down-projected decal smeared along that card. The decal branch hid
the card with `SetVisibility(false)`, but `UDinkGreyboxSubsystem::UpdateLegacyCardVisibility` records every card's
visible flag at first sight and sets it again on the card's own screen, so the card came back. Fix: the card of a decal
row is taken out of the render passes (`SetRenderInMainPass(false)`, `SetRenderInDepthPass(false)`,
`SetReceivesDecals(false)`, no Lumen card, no ray tracing) and keeps its flag; the decal is attached to the card with an
absolute transform, so it follows the card's flag as the fire light does (`FollowCardVisibility`: off on neighbour
screens) while staying where it is when the card turns to the camera.

## Seen in the running game

Captured offscreen in the game on master `fd676f34d` + this change (copy `Saved/FableD`, the integration tree of the effect
drafts; capture section `sec_burn`, 20 frames, `Saved/PhotorealPass/fx5/B_*.png`).

| sheet | what it shows | what I see |
|---|---|---|
| `1997_155_156_157_154_158.png` | the 1997 burn pictures (4x) | ragged black breaks with spikes, charred laths and fire glowing between them |
| `01_game_23nov_before_the_fix_card_and_smear.jpg` | before the fix (23 Nov, earlier capture) | the blocky black 1997 picture standing upright on the roof with the decal smeared down it as a bright column; the real decal lies half hidden on the thatch under it |
| `02_game_23nov_burn_marks_after_the_fix.jpg` | top: 439 at the play camera, from the south, the south-east and the roof close; middle: the roof marks S439_P31 (from the camera of sheet 01 and from above), P33 and P32 from above; bottom: the three wall marks of the room and the room at the play camera | **No card and no column any more.** Each roof mark is a charred break lying ON the thatch: a soft black star with soot rays, brown charred laths across it and a heart of fire that flickers between two frames; from the south and at the play camera they are small glowing breaks in the roof below the fires, where 1997 has them. In the room each mark is a black ragged break on the wall, across plaster and timber, with its laths and a red and orange glow. |
| `03_burn_mark_sheets.jpg` | the three sheets over thatch and limewash | A, B (round) and C (two breaks run together), four frames each |

## Still below the bar, not checked

- A decal is flat: the laths do not stand in front of the glow, and from a grazing angle the mark thins out.
- S439_P32 lies across the ridge beside the chimney: its picture is bent over the ridge line.
- The heart of fire is brighter and more yellow than the dark red embers of the 1997 pictures.
- A wall decal also paints what stands within 1.3 m in front of that wall. S001_P38 projects onto the south wall, which
  the play camera never sees from inside.
- Not seen on the burning cottage mesh of #215 (merged after these frames): a mark whose roof point falls inside its
  roof opening would project into the burnt room.
- Whether the marks go off on a neighbour screen with their card (the capture never left the screen).

## How it was proven

- On master `55ab3ae8d` + this commit, nothing else (copy `Saved/FableD`: its 433 source files compared equal to the branch's,
  intermediates deleted): clean build, 0 warnings, 191 s (`DinkArtFamilySubsystem.cpp` compiling).
- `Dink.Art+Dink.Animation+Dink.Gameplay.Probe`: 127/127 passed in 703 s (run `fx5_214`); the twenty chapter md5s equal the
  table of `Plugins/DinkParity/Docs/packaged_probe.md` on master. Kernel: no fault.
- `Dink.Art.Family.PlacedEffectRow` reads a decal row (size, depth, direction, one placement's own direction; an unknown
  direction is dropped).
- The copy's packages of the FableF and HeroWeapons kits are re-imports of the same sources (kit imports of this stream's
  other drafts ran in it), not master's bytes; the frames above were taken on master `fd676f34d`, before #215's burning
  cottage was merged.
