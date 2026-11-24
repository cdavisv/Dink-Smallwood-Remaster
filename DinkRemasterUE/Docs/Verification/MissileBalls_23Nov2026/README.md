# Fireball and hellfire along their flight (502, 508, 512, 518), 23 November 2026

South (at the camera) and north (away from it) the missile was the side-view card stood upright: a tall flame that read
as Dink burning. It is now a ball of fire seen from ahead and from behind.

**Where the frames come from.** Sheets 01 and 02 are frames of the RUNNING game on screen 446 at the play camera, each
frame its own cast (the engine flies a missile in real time): 01 on master `64b84d1a`/`6bcfdf60` (the upright card),
02 on 17 Nov 00:31 with this change as it stood then. Sheet 03 is the final atlases. Two changes are later than those
game frames (SEEN in the game on 23 Nov, sheets 04 to 06 at the end): the glow lowered from 3.2 to 2.2 (the ball's heart had clipped to white) and a
one-texel blur (fine vertical streaks showed when the missile filled the screen).

| sheet | what it shows | what I see |
|---|---|---|
| `1997_502-508_512-518.png` | the 1997 frames of the eight sequences (3x) | the fireball: a yellow and red ball with a trail of sparks; hellfire: a chain of fat fire balls, the largest in front |
| `01_before_master_south_and_north.jpg` | master, casts south and north | a flame as tall as Dink standing on him, growing as it comes: it reads as the caster on fire |
| `02_after_17nov_south_and_north.jpg` | this change, eight casts | hellfire south at 0.08 s: a ragged ball of fire about a metre across between Dink and the camera, orange tongues round a bright heart: a fireball. The fireball spell south at 0.08 s is still at Dink's shoulder (one frame), at 0.2 s it passes the camera and fills the frame. North: the ball is beyond Dink and hidden by his body in the first frames (a rim of flame at his shoulder); later frames were not caught |
| `03_flipbook_strips_final_atlases.jpg` | the final atlases, every sixth frame: fireball from ahead, from behind, hellfire from ahead, from behind | a ball with flames wrapped round it; from ahead its short trail rises behind it, from behind it is a round ball with a ragged rim |

## Still below the bar, not checked

- North: not one frame shows the ball clear of Dink. It leaves from his chest, so from behind he hides it until it is
  some metres off; finer delays are on the pending list.
- The first frame of a cast south has the ball at Dink's head height.
- Fireball and hellfire differ only in size and fatness; 1997's hellfire is a chain of balls.
- West and east keep #197's side card (additive, paler than these two).
- No sparks to speak of: the projected spark layer is too fine to see in the atlas.

## In-game look, 23 November 2026 (rendered work allowed again)

Captured offscreen in the running game on master `430fd81d2` + this change (copy `Saved/FableD`, the integration tree of the
effect drafts), capture section `missile` (26 frames, `Saved/PhotorealPass/fx2/D_missile_*.png`): fireball (`fb`) and
hellfire (`sfb`) cast south (towards the play camera) and north (away from it), frames 0 to 0.3 s after the cast.

| sheet | what it shows | what I see |
|---|---|---|
| `04_game_23nov_all_frames.jpg` | every frame at the play camera: fireball north, fireball south, hellfire north, hellfire south | SOUTH: a ball of fire that grows as it comes; the hellfire fills the frame within 0.15 s. No upright flame card, no vertical streaks |
| `05_game_23nov_close_south_and_north.jpg` | crops at full size: fireball south (two frames), hellfire south (two), then fireball north (two) and hellfire north (two) | the fireball from ahead is a ragged ball with its tail behind and above it, the heart bright yellow with detail; the hellfire is a wide ragged ball whose heart is cream-white over about a third of its width (bright, at the edge of clipping). NORTH: the ball is behind Dink (the play camera stands behind and above him and the ball flies away along its line of sight): flames show round his body |
| `06_game_23nov_north_later_frames.jpg` | fireball and hellfire north, 0.4 to 1.2 s after the cast (a second capture) | the ball flies away and shrinks, and for the WHOLE flight it stays behind Dink's head: at the play camera a north shot shows only as a glow round his head. Not a fault of the picture (from any other side it is the ball of sheet 05); it is where the play camera stands. Named for the coordinator: a north shot cannot be seen in this camera |

After the coordinator's review of these frames the hellfire's glow went one notch down, 2.2 -> 1.8 (the fireball keeps 2.2), and was
captured again:

| sheet | what it shows | what I see |
|---|---|---|
| `07_game_23nov_hellfire_glow_1_8.jpg` | second row, crops at full size: the hellfire flying south with glow 1.8 (three frames), then the fireball (2.2) | the hellfire's heart is yellow-cream with its detail in it, no longer a white patch; the ball still fills the frame within 0.15 s. (The first row of the sheet is the bow draft's quiver.) |

South is at the bar for both spells as far as I can judge. A shot to the north cannot be seen past Dink at the play camera (above): that is
the camera, not the picture. East and west were not captured again (unchanged by this draft).
