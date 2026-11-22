# The armed weapon in Dink's hand (bug A203), 19 Nov 2026

Branch `anim/hero-weapon-attach`. 1997 draws the armed weapon in every idle, walk and attack picture of Dink (arming reloads
those sequences: `item-sw1.c` `graphics\dink\sword\...`, `item-b1.c` `graphics\dink\bow\...`); the remaster's hero swung,
chopped and drew a bow with empty hands.

## What changed (presentation only)
- `Content/Dink/Data/Art/hero_weapons.json`: armed item script -> mesh, hand bone and grip transform, from the art kit of
  PR #157 (swords and axe on `hand_r` at (-7, 3, -0.5) cm, pitch 90 roll 90; bows on `hand_l` at (7, -3, 0.5), pitch -90
  roll 90). Fists (`item-fst`) and the bomb carry nothing.
- `UDinkHeroWeaponSubsystem` (DinkNarrative, `DinkHeroWeapon.h`): every frame, the armed item
  (`UDinkGameplay::GetWeaponInstance`, its script) decides the mesh in the hand; one tagged static mesh component on the
  hero, no collision; empty when nothing is armed, fists, a bomb, or `&life` < 1. `dink.Hero.Weapons 0`: off.
- Review command `dink.Hero.GiveWeapon <item>` (add_item + arm, as buying and choosing it) for captures.
- Test `Dink.Art.HeroWeapon.RowsAndAttach` (every weapon item has a row and an imported mesh; arm, swap to the bow's left
  hand on the same component, fists empty, off empty, one component however often re-armed).

## Sheets (running game, private copy, offscreen; `Scripts/AnimationQA/weapon_capture.py`)
- `01_idle_each_weapon.jpg`: fists (empty), long sword, claw sword, light sword, axe, wood bow, blue bow. Seen: each mesh is
  in the hand and changes with the armed item. The swords stick straight out forward at hip height in the idle (the idle
  clip's open hand), which reads stiff; the bows hang at his side and are hard to see from this side; the axe shows its
  double head beside the hand.
- `02_attack_sword_axe_bow.jpg`: the sword follows the overhead slash and chop; the bow is drawn to full draw with
  `Bow_Draw`; the axe has no attack clip (1997 throws it; the hero just stands): Fable row AN-06.
- A first capture armed the wrong slot (the review command's off-by-one, fixed); there the mesh followed the simulation's
  armed item exactly, the attack clip and the hand agreeing.

## Still wrong / not done
- No closed fist round the grip and no bending bow or string (code/animation, left for a follow-up; AN-05 asks for a
  carry pose of the hand and blade).
- Not checked: packaged build, the item screen while armed, a save/load while armed (the mesh follows the armed item each
  frame, so it should; not seen), arrows.

## Tests and probe (master f4743990 + this branch, world from a copy regenerated with `--export` on the same master)
- `Dink.Art.HeroWeapon+Dink.Art.PlayerAction+Dink.Animation`: 14/14.
- Full `Dink`: 352/352. Probe: all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md`.
