# Creature one-shots: hit, attack, idle and death clips over the 1997 sprite (16 Nov 2026)

Branch `anim/creature-oneshots`. Owner decision of 16 Nov 2026 (COMMON_RULES "OWNER DECISIONS", item 9): creature hit and
death clips play as presentation one-shots, including the five once left out on gore grounds; "We want to keep the
deaths." No creature hit or death clip is withheld: all 18 (`art_wiring_audit.py`: bound, flag ok).

## What plays (presentation only; the sprite, its hardness, scripts, the kill's timing, the corpse and the blood are the simulation's)
- Hit: a hit that costs life plays the class's `Hit` over the body (bonca, slayer, stone giant, dragon from the spine up,
  goblins). The duck's first hit (duck_brain beheads it, dink.cpp:12748-12775) plays `AN_Duck_Hit` as the head flies off.
- Attack: the dragon's `Attack` on the upper body when its fireball appears; a slime's `Attack` when Dink loses life
  beside it. Idle: the duck pecks and quacks while it stands.
- Death into the corpse (brain 9/10 kills, add_kill_sprite dink.cpp:12359): the corpse, its pool and the hit blood are
  left at the kill as in 1997; a copy of the body plays `Death` from its last pose and the corpse mesh is shown where the
  clip ends, moved by the art export's offset (`corpse.json` -> `align_cm`). Bonca, slayer, stone giant, dragon (its own
  torn remains are now its death pose), goblins, and the slimes (`AN_Slime_Death` before the splat).
- Burst kill (the headless duck's second hit, dink.cpp:12728-12740): new `burst_death` spec: the headless body plays
  `AN_Duck_HeadlessDeath` and the burst of sequence 164 (same drops, stain, feathers) comes where it ends.
- `AN_Duck_Death`: no 1997 event kills a duck with its head on, so it is wired as the duck's death and shown by the review
  command `dink.Creature.ShowDeath duck` only.
- Switches: `dink.Creature.OneShots 0` = the 1997 behaviour exactly; `dink.Creature.DeathClips 0` = deaths only.
- Review commands: `dink.Creature.ShowDeath <class> [burst]`, `dink.Creature.Hurt <class> <damage>` (the simulation's own
  damage path; review captures only).

## Sheets (running game, private copy, offscreen; top row one-shots off = 1997, then on)
- `01_bonca`: off, the body swaps to its bloody remains in one frame; on, the striped body falls over about 1 s on its
  pool (the pool is there from the kill frame), then the remains take its place. Seen: the hand-over is a colour change
  (the living skin, then the blood-soaked remains). Hit: the body hunches.
- `02_dragon`: on, the dragon rears and falls over its pool, wings flailing, then its torn remains; the tears and the flat
  wing appear at the hand-over (the remains are reshaped). Hit: a small upper-body flinch.
- `03_duck`: the first hit: the head flies, the neck sprays, the headless body staggers (`Hit`); the second hit: off, the
  burst at once; on, the headless body falls on its side, then the same burst. The `owndeath` row did not catch the copy
  (it plays 1.5 m to the side, outside the frame): not verified by eye.
- `04_stone_giant`: on, the giant pitches forward and the heap takes over close to where it lands.
- `05_slime` (play camera, round 5 build): on, the slime sinks, then the splat; off, the splat at once.
- `06_goblin`: the goblins of screen 712 draw as 1997 picture cards in this build (no class body), so the goblin hit and
  death clips are wired and tested in data but NOT seen in the game.

## Fixed on the way
- A dying body wearing the corpse's material drew in the engine's grey default (those materials are not compiled for
  skinned meshes); now it keeps its own skin unless the corpse material has skeletal-mesh usage. Fable/import row AN-03.

## Tests and probe
- `Dink.Creature+Dink.Art.CreatureClass+Dink.Art.CreatureRigMaterialsAndMotion`: 11/11 (new
  `Dink.Creature.OneShots.DuckHeadPopAndBurstDeath`; `BurstOnlyOnAKillAndStainsReused` now waits for the headless fall).
- Full `Dink`: 340/340 on master bd6d227a5 + this branch (before the material guard and the capture cameras; targeted tests
  re-run after them, 11/11). Probe: all twenty chapter md5s equal `packaged_probe.md`.
- `python3 -m unittest Scripts.tests.test_art_wiring_audit`: 41 OK.
- Not checked: packaged build, goblins in game, the duck's own death by eye, frame cost (one extra skeletal mesh per
  dying creature for 1-1.6 s).
