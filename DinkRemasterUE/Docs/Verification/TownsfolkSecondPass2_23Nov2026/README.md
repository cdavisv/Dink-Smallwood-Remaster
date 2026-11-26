# Townsfolk 2a: the gnome and the merchants as townsfolk of their own, and the brow fix (23 to 26 November 2026)

Made by stream art-people-7 (Fable 5.2, 23 Nov); brought onto master mechanically by art-finish-1 (Opus, 26 Nov), who made
no change to any mesh, texture or material and judged no look. **FRAMES FOR FABLE: the look of this draft has not been judged
since the brow fix.**

## What it is

- The gnome (`SK_Gnome_Photoreal`) and the merchant (`SK_Merchant_Photoreal`) with the colour twins green, red and purple
  (`MerchantGreen`, `MerchantRed`, `MerchantPurple`) as townsfolk of their own: sources, Blender work files, exports,
  manifests and tools under `SourceAssets/Art/PhotorealPass/Characters/NPC/{Gnome,Merchant,...}` and `Characters/Tools`;
  the five package folders under `Content/Dink/Photoreal/Characters/NPC/` as imported in the copy that the frames below
  were taken in.
- The brow fix: the hair material gains a scalar `BrowScatter` (how much scatter the brow band keeps; default 0.15 = the
  look before), set in `HAIR_LOOK` of `Scripts/import_photoreal_art.py` for the gnome, the merchant, the maiden (and her
  twins through her material) and the old man. Their `M_/MI_*_Hair` packages are in this change; the other NPCs' hair
  materials are master's (their look keeps the default).
- Triangles at LOD0: gnome 29,313, merchant 31,242 (cap 35,000).

## Sheets

| sheet | what it shows |
|---|---|
| `01_gnome_1997_first_pass_now.jpg`, `02_merchant_1997_first_pass_now.jpg` | Blender: the 1997 pictures, the first pass and this pass |
| `03_merchant_and_twins_blender.jpg` | Blender: the merchant and the three colour twins |
| `04_game_t2b_gnome.jpg` | in the game (round t2b, the brow fix): the 1997 pictures, the play camera, the whole figure from four sides and above, the head from eight sides |
| `05_game_t2b_merchant.jpg`, `06_game_t2b_merchant_green.jpg` | the same for the merchant and the green twin |
| `07_game_t2b_maiden_brows.jpg`, `08_game_t2b_old_man_brows.jpg` | the same for the maiden and the old man (only `BrowScatter` changed for them) |

Round t2b: 140 frames, `Saved/CharQA/t2b` of copy `Saved/FableC` (master c0e29cac5 + the stream's integration tree), taken
23 Nov 2026 by art-people-7 and not looked at before this draft. Round t2a (before the brow fix) found the gnome and the
merchants read as their 1997 pictures, with the brows black on both.

## Open for Fable (art judgement)

- Are the brows still dark after `BrowScatter`? If so: raise `BrowScatter` / `BrowGain` in `HAIR_LOOK`, re-import, capture.
- Are the Maiden and OldMan brow rows wanted in this change? If not, take their `BrowScatter` out of `HAIR_LOOK` and drop
  their hair packages from the change.
- Known weak points (art-people-7): gnome: the export found SCALE_RANGE (2.305 m on the rig with the hat's point; 1.28 m in
  the game), hands half a man's after the placement, beard and hat rigid on the head. Merchants: bare-headed (1997 blue,
  green and purple wear a cap of the coat's colour), the pelt is paint on flat cloth, the face a little anxious.
- `npc_variants.py` rewrites `NPC/Soldier/Textures/T_Soldier_PR_Outfit_BC.png` with other pixels than master's file;
  `git checkout` that file after every run (not part of this change).

## Proof (26 Nov 2026, copy `Saved/ArtFinish26Nov` = master `6dd60a8c8` + this change)

- The sources, tools and docs of art-people-7's integration branch replayed onto master (no conflict); the five NPC package
  folders and the hair materials of the maiden, her three twins and the old man taken as imported in copy `Saved/FableC`
  (the copy the t2b frames were taken in; not re-imported).
- Editor build 0 warnings (no C++), game target 0 warnings, `Dink.Art+Dink.Animation` 105/105, `Dink.Gameplay.Probe` 29/29
  with the twenty md5s equal to the world-scale table of `packaged_probe.md` (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`).
  Kernel: no Oops.
- The t2b frames are from copy `Saved/FableC` (master `c0e29cac5`, world scale off); no frame of this change on the new master yet.
