# Two stray sparkles cut: 1997 never drew them (art row DS-06), 23 November 2026

## What changed

- `Scripts/art_coverage.py`: `NEVER_DRAWN` marks the placements `S001_P37` and `S045_P01` as `cut` with the reason. They were the whole of the open family `sparkle_fx`.
- `doc/remaster/ALPHA_GATE2_BACKLOG.md` regenerated (`Scripts/gate2_backlog.py`): 69 open families (was 70), 812 origin IDs, 501 placements; art_coverage rows: cut 154 (was 152), placeholder 837.
  The regeneration also brings in what master's own data had already changed since the page was last generated on 16 November: one pine placement (`S534_P10`) counts as final by family, so `tree_pine_large` goes from 7 IDs to 6. On master alone, without this change, the generator gives 70 families, 814 IDs, 503 placements.
- `AGENTS.md` and `doc/remaster/FABLE_ART_QUEUE.md` (row DS-06) say so.
- Nothing the game reads is changed: no C++, no content, no data file.

## Why they are cut

| placement | picture | at (editor) | picture size, origin | window x of the picture | script, brain, vision |
|---|---|---|---|---|---|
| `S001_P37` | 165 frame 5 (`effects/shiny/shiny-`) | (0, 0) | 20 x 20, (8, 9) | -8 .. 12 | none, 0, 0 |
| `S045_P01` | 166 frame 1 (`effects/sparks/spark-`) | (0, 0) | 23 x 27, (12, 14) | -12 .. 11 | none, 0, 0 |

The play field of the 1997 window starts 20 px in from the left edge. `get_box` clips every sprite to it and does not draw a sprite whose right edge lies left of it (`source/dink/dink.cpp:3170`, `:3317`: `if (pDstRect->right-1 < mplayl) goto nodraw;`). Both pictures end at window x 11 or 12. Neither placement has a script, a brain or a vision, so nothing moves it into view: no player of the 1997 game has seen either. They are sprites the map's author left at the editor's origin.

`01_under_the_left_border_x8.png`: the top left 60 x 40 px of the window of screens 1 and 45, eight times enlarged; grey is the border (x < 20), green the play field. The few pixels of each sparkle that fall inside the window are all on the border.

## How it was checked

- `Scripts/tests/test_never_drawn_placements.py`: the two rows, and against the extracted 1997 data (`tools/dinkex/out`, set `DINK_DINKEX_OUT`) that each picture's right edge is left of the play field and that the placement has no script, brain or vision. 3 tests pass with the data, 1 passes and 2 skip without it (CI has no extraction).
- `python3 -m unittest discover -s DinkRemasterUE/Scripts/tests -p 'test_*.py'`: 1005 tests, 995 pass, 10 errors; master 9ada93f1a in the same checkout: 1002 tests, the same 10 errors (they need FBX fixtures that are Git LFS pointers in this checkout; CI hydrates them).
- `Scripts/check_public_paths.py`, `Scripts/verify_sources.py --metadata-only`: pass.
- Unreal: this branch gives the engine nothing new to compile or load. The copy the other drafts of this stream were verified in holds this `art_coverage.py`: copy `Saved/FableD` = master 9ada93f1a + the seven drafts of this stream (it holds this `art_coverage.py`): clean build 0 warnings, world regenerated, `Dink.Art+Dink.Animation+Dink.Gameplay.Probe` 118/118 in 734 s, the twenty probe md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master.

## Not checked

- No rendered game was run (machine rule of 21 November). There is nothing to look for in the game: the remaster already drew no effect for these two placements (placed-effect path, 16 November); this change is the audit's state for them.
