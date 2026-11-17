# Explosion, fire burst and blood burst cards in the game (GP-Q9, CG-6), 16 November 2026

Captured offscreen on screen 439 from a private copy (master `64b84d1a` plus this branch and the stream's other art
branches). The engine plays these sprites in real time (time dilation does not slow them), so the 0.42 s and 0.6 s
explosions are shown one cast per frame, each shot a little later after the cast. BEFORE frames are the same casts
with master's `families.json`.

| sheet | what it shows | what I see |
|---|---|---|
| `1997_161.png`, `1997_167.png`, `1997_70.png`, `1997_164.png` | frames of the four 1997 sequences (3x) | fire burst: mound, stem and cap, collapse, smoke. Explosion: ball, ring, ring of clumps. Small explosion: ball to smoke ring. Blood burst: a dark red ball that bursts into specks |
| `01_fire_burst_161.jpg` | the bomb's burst (`dam-bom`), three BEFORE frames, then fourteen frames 0.07 s apart | before: the three frames caught show only the bomb's own 1997 card; no frame of the 1997 burst was caught. After: an orange and yellow mound, a stem with a rolling cap twice Dink's height, the collapse into a ball of fire, dark red-brown smoke with fire still inside. The phases and colours of 1997, in the round |
| `02_explosion_167_hellfire.jpg` | hellfire bursting on the fence, six casts | before: a small blocky orange card. After: a yellow-white ball, a spreading fireball, then a ring of orange clumps, as the 1997 ring |
| `03_small_explosion_70_fireball.jpg` | the fireball spell bursting on the fence, six casts | a small yellow ball that turns into a red-brown puff of smoke |
| `04_atlases_as_graded.jpg` | the four atlases as stored, and the 1997 blood burst | the fire atlases after `fx_grade.py`; the blood burst as rendered: a dark red ball of drops that breaks into specks |

## Still below the bar

- **The blood burst (164) was not seen in the game**: the game creates no sprite with picture 164. Ducks and pigs burst
  through the creature layer's own class burst; for other sprites without a death picture `UDinkGameplay::AddKillSprite`
  creates nothing. The row and the atlas wait for that code (see `AGENTS.md`). Judged as frames only.
- A thin pale outline still shows round the dark phases (the orange ring of 167, the smoke of 70) at this distance.
- The first frames of each explosion clip to pale yellow-white in daylight.
- One camera-facing card per explosion: no depth against the fence or Dink (he stands inside the burst), nothing is
  scorched, and no light falls on the scene from these rows in this change (the missile PR adds a flash).
- The first two rounds were wrong and are not shown: every flipbook master failed to compile (grey checker cards), then
  the fire drew as a white blob with a white halo. Both are pitfalls in `AGENTS.md`.

## Not checked

- 512 (the falling fireball a script creates) in its story scene; explosions at night or indoors; Seth's and the
  dragons' explosions in their scenes.
