# Fireball and hellfire in flight (502 to 508, 512 to 518), 16 November 2026

Captured offscreen on screen 446 (open grass) at the play camera, from a private copy (master `64b84d1a` plus this
branch and the stream's other art branches). The engine moves a missile in real time, so every frame is its own cast:
three casts per direction, shot 0, 0.1 and 0.2 s after the cast. BEFORE frames are casts with master's data.

| sheet | what it shows | what I see |
|---|---|---|
| `1997_502-508_512-518.png` | the first 1997 frame of each of the eight sequences (3x) | the fireball spell: a small red and yellow head with a trail of sparks; hellfire: a chain of fire balls; each drawn for its direction |
| `01_fireball_spell_four_directions.jpg` | the fireball spell cast south, west, east and north | west and east: a bright head leads and the flame trails behind it, flat over the grass at chest height. South (towards the camera): a ball of fire in front of Dink with its flame standing up above it, growing as it comes. North: the fire shows round Dink's shoulders as it leaves, its flame above his head |
| `02_hellfire_four_directions.jpg` | hellfire cast in the four directions | south and west as the fireball, lower over the ground. East: the missile had already burst (the frames show #158's explosion). North: a flame above Dink's head as it leaves |
| `03_before_1997_pictures.jpg` | before: casts with master's data | the missile is its 1997 picture: a few red and yellow pixels on a small card |

## Still below the bar

- **South and north use the upright card**: a ball with a tall thin flame standing straight up, which is right for a
  flame but not for a missile coming at the camera; from behind, Dink hides most of it. A ball-shaped flipbook for these
  two directions was tried twice with the kit's noise generator and looked worse (a flat mound, then a ragged flame); it
  is not in this change.
- The fireball spell (a small head with sparks in 1997) and hellfire (a chain of balls) share one flipbook at two sizes.
- The travelling light and the explosions' flash are too weak to see on grass in daylight; not judged at night or
  indoors.
- A card has no depth: the missile does not light or scorch what it passes.

## Not checked

- Hellfire flying east and north in flight (it burst at once in the east casts). Missiles of monsters (none use these
  sequences as far as I read the scripts). Night and indoor casts.
