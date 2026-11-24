# The fountain's spray (94), 23 November 2026

1997: a wide blue dome of spray over the whole fountain (80 px where the stone is 102). Master: a narrow pale jet on an
unlit card, faint by day and glowing in the dungeon of 260.

**Where the frames come from.** Sheets 01 and 02 are frames of the RUNNING game: 01 on master, 02 on 17 Nov 00:31 with
this change as it stood then (KernSin's square 586 by day, the dungeon 260). After that capture the dome was made
wider and denser (13000 drops, reach 0.9 m, a stronger curtain and basin band): sheet 03 is that final atlas, NOT
seen in the game.

| sheet | what it shows | what I see |
|---|---|---|
| `1997_94.png` | the 1997 frames | a dome of light blue drops, fullest at the top, falling all round |
| `01_before_master.jpg` | master by day and in the dungeon | a thin white jet, hard to find against the sunlit earth; a bright white plume in the dark room |
| `02_after_17nov_day_and_dungeon.jpg` | this change, play camera and three fixed views, both fountains | by day a blue-white dome stands over the bowl and is plain against the earth; in the dungeon it takes the lamp's light and is no brighter than the stone beside it. The dome was narrower than 1997's (about 1.4 m): below the bowl's rim little of the falling water showed by day |
| `03_final_atlas_day_and_dark_wider_than_the_frames_above.png` | the final atlas over earth and over dark, as the lit material shades it | water thrown out all round in strands, a full crown, a curtain of drops down to a band of splashes on the basin, 2.2 m across |

## Still below the bar, not checked

- The final, wider atlas has not been seen in the game.
- A card through the fountain's middle: the bowl does not hide the far half, nothing wets the stone, no rings on the
  basin's water.
- Lit without a highlight of its own: it does not sparkle in the sun.

## In-game look, 23 November 2026 (rendered work allowed again)

Captured offscreen in the running game on master `430fd81d2` + this change (copy `Saved/FableD`, the integration tree of the
effect drafts): section `fountain` (12 frames, `Saved/PhotorealPass/fx2/D_fountain*.png`), then two short captures from the
south, east, west and south-east (`G_fountain*.png` before the fix below, `H_fountain*.png` after it).

| sheet | what it shows | what I see |
|---|---|---|
| `04_game_23nov_first_look_spray_off_the_bowl_on_586.jpg` | the first look: dungeon 260 (top row and the first two of the second) and the town square of 586 by day | 260: the final wide dome stands on the bowl, falls into the basin, is lit by the lamp and does not glow. 586: FAULT, the dome stood about 1.15 m NORTH of the bowl (centred from the south camera, beside the bowl from the south-east, east and west): the two fountains do not stand alike on their placement points, and the row gave both the same offset |
| `05_game_23nov_after_the_offset_fix.jpg` | after the fix (`offset_cm` of `S586_P14` 0.95 m -> 2.10 m south): 586 at the play camera, from the south, east, west and south-east; 260 again | 586: the dome is on the bowl from every side, wide, bright blue-white by day, falling into the basin. 260 unchanged and good. At the bar |
