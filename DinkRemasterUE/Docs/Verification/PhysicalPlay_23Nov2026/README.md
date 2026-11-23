# Physical play layer, 23 Nov 2026 (PR #160 on master 78867e7bc: A41 + A353)

Headless only (machine rule), private copy `Saved/Collision21Nov`, clean rebuild of the changed modules.

| gate | result |
|---|---|
| build | 0 warnings |
| `Dink.PhysicalPlay` | 9/9 (new: `MissileAtDrawnDink`, `NoFallbackThroughWalls`; Blockages walks at bpotion S166_P23 and gheart S157_P09; RealScreens checks the relaxed boxes of the 16 screens with most of them) |
| `Dink.Gameplay.Probe`, layer off | 29/29, all 20 md5s equal to the A41 table of `packaged_probe.md` (`probe_layer_off_hashes.txt`) |
| `Dink.Gameplay.Probe`, layer on (Mode=2, all parts) | chapters 1-20 complete, chained from a new game (`probe_layer_on_chapters.txt`); `Repeatable` fails as before (layer-on runs are not deterministic: physics and the bot's teleports) |
| full `Dink` suite | 397/397 |

Chapter 12 (the Joppa dragons) also from its save on four other random streams (`DINK_PROBE_RESEED`, run on master 11290aa3e before A41): 4/4 (`ch12_reseeded_runs.txt`).
The earlier failures were no hitbox defect: en-drag.c's harm is `hurt(&target, 20)` with no missile or range (as in 1997); the bot
stood "fleeing" beside the second dragon while the first had 3 hit points, and the family died. Missiles at Dink now meet his drawn
body anyway (part CreatureReach), the consistent rule for drawn contact.

`probe_layer_on_unreachable.txt`: what the bot's assist could still not step next to. The two potions of S166 are blows the bot swung
while beside them (both are collected by walking up: the pickup fallback); S521 knight and S536 duck are single frames during fights
that completed.
