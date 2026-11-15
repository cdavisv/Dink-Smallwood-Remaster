# Story, blood and gore: parity audit against the 1997 game (15 Nov 2026)

Owner's order (15 Nov 2026): "make sure the story and blood and gore are up to the original levels. We don't want to
restrict anything or modernize things." This file is the systematic check of the remaster (master `0bf319c9`) against
the 1997 game: every line of text the DinkC scripts show, and every blood, gore and death picture the engine or the
scripts draw. Each gore item is graded **at least 1997**, **less than 1997** or **missing**. What code could fix is fixed
in the follow-up pull request `fix/gore-story-parity` (section 4); what needs new art is in `doc/remaster/FABLE_ART_QUEUE.md`.

Sources of truth: the 1997 scripts `bin/dink/story/*.c`, the engine `source/dink/dink.cpp` (cited `D:<line>`), the
sprite data `bin/dink/dink.ini` (through `tools/dinkex`). Nothing under `bin/` or `source/` was changed.

## 1. Method

**Text.** `tools/parity_audit/text_audit.py` reads the 1997 scripts with its own scanner (not `tools/dinkc`): every
`say`, `say_stop`, `say_xy`, `say_stop_xy` and `say_stop_npc` string, every option line between `choice_start()` and
`choice_end()`, and every line between `title_start()` and `title_end()` (dink.cpp:5080-5200 reads menus that way;
a line starting with `//` is a comment, D:7113). It then walks the story the game ships,
`DinkRemasterUE/Content/Dink/Data/Story/dink.json` (compiled Ink, not `tools/dinkink`'s tables), and joins the two by
script and source line (`#src` tag) or, for options and titles, by script and text. Normalisation is only what the 1997
engine itself does before drawing: a leading colour code (`` `3 ``, D:11810-11834) is dropped (the remaster carries it
as `#col`), `&variables` are compared as placeholders (both engines substitute them at run time), U+00A0 is a space (the
remaster's one display transform, `DinkNarrative::ToDisplayText`). The current `tools/dinkink` build reproduces the
shipped `dink.json` byte for byte (checked with `cmp`), so the shipped story is the converter's output of the 1997
scripts. The runtime was searched for any text filter (`censor`, `profan`, `sanitiz`, `swear`, `bleep`, `soften`):
none; text is drawn as stored (`DinkNarrativePresentation.cpp`, word wrap only).

**Voice.** `tools/parity_audit/voice_audit.py` checks every spoken line id of the story against
`Content/Dink/Data/Audio/voice.json` (what plays) and the generation manifests in `SourceAssets/Audio/Voice/*_manifest.json`
(the exact text sent to the speech model, `tts_text`): the words sent must equal the words of the line, after removing
stage directions (`<sob>`) and the model's tags (`[sobs]`).

**Gore.** The 1997 gore was listed from the engine (`random_blood` D:6675-6700, `add_kill_sprite` D:12359-12420,
`duck_brain` D:12723-12801, `one_time_brain` D:15741-15768, the hit paths D:9953, 14398-14403, 15567, 15672), from every
monster script's `sp_base_death` / `sp_base_walk` (`tools/dinkc` `enemies.json`) with the death sequences in `dink.ini`,
and from every placed picture whose class is blood, a burn, a corpse, a head, bones or a skull
(`tools/parity_audit/gore_placements.py`: 241 placements, joined with `Scripts/art_coverage.py` and the importer's card
sizes). For each, the remaster's drawing was found in `creatures.json`, `families.json`, `environment.json`, the
Stonebrook manifests and the runtime C++ (`DinkCreaturePresenter.cpp`, `DinkEnvironmentSubsystem.cpp`,
`DinkGameplay.cpp`, `DinkBrains.cpp`), and in the latest verification sheets.

Rerun: `cd tools/dinkc && python3 -m dinkc build ...` and `cd tools/dinkex && python3 -m dinkex extract ...` (AGENTS.md),
then from the repository root `python3 -I tools/parity_audit/text_audit.py . <out>`,
`python3 -I tools/parity_audit/voice_audit.py . <out>` (needs `tools/dinkink/out/line_ids.csv`), and
`python3 -I tools/parity_audit/gore_placements.py . <out>/gore_placements.csv` (needs `DinkRemasterUE/Saved/gore_cov.csv`
from `Scripts/art_coverage.py --out Saved/gore_cov.csv`).

## 2. Story text

| 1997 text | Lines | Identical in the shipped story | Differs |
|---|---:|---:|---:|
| `say*` lines (spoken, signs, the ending, death and system lines) | 2,125 | 2,125 | 0 |
| choice options | 359 | 299 literal + 60 filled by the engine at run time (`&savegameinfo` 50, `&buttoninfo` 10: the remaster's Ink calls the same functions) | 0 |
| choice titles (`title_start` ... `title_end`) | 68 | 68 | 0 |
| **all** | **2,552** | **2,552** | **0** |

Nothing is missing, reworded, softened or cut. The lines the owner named are there word for word, among them the
burnt-house scene (`s1-h1-s`), Milder, the pig tax ("my family got royally screwed by the crown each year", `king.c:151`),
the duck and pig lines, the cult (`s2-cult`: "A girl is about to die in a cult ritual. What do you do?"), the murderer
"who stalks and kills the pets of the people" (`s1-wand`), Jack's widow, Seth's "EAT IT!" and the whole ending and
credits of `king.c` (including "Justin - sorry I made you draw blood ;)").

Where the remaster's text differs from what the 1997 *engine* showed, it shows more, never less: the four owner-approved
typo fixes of 9 Nov 2026 (`overrides.py` `OWNER_DECISIONS`) make four written lines speak that the 1997 engine
silently dropped: `s2-jack.c:171` "I guess I just killed your husband." (opening `'` instead of `"`), `s3-chick.c:42`,
`s4-sign3.c:17` "Long live the ducks.", and the bed of `s1-h3-8.c:13` (all four texts identical to the script). The
other twelve `fix_` switches stay `false`, so the engine's 1997 behaviour is live (for example `s1-wand2.c:187` shows
"Hello, I'm Chance \`Zands" with its stray backtick, as 1997 did: only leading colour codes are stripped, D:11810).

Not in 1997 and therefore not compared: the remaster's own item names in the item screen of the unmerged PR #128
(`Data/Presentation/items.csv`: "Longsword", "Acid Rain"; 1997 shows only pictures) and its speaker names. They add
text and remove none.

**Voice** (2,125 spoken lines):

| | Lines |
|---|---:|
| voiced, the recording was generated from exactly the line's words | 2,006 |
| voiced with the recording of an identical line of the same voice (82 copies, see the voice README) | 82 |
| not voiced: system lines (gold found, "Game saved", `<Casts harm>`, "* POWER SHOT *" ...) | 33 |
| not voiced: lines that are only a stage direction (`<chortles>`, `<sniff>`, `<sob>`, `<groan>`) | 4 |
| voiced with text that differs from the line | 0 |

No speech-to-text check of the audio exists, so whether each recording *says* its text (no dropped or swallowed word)
is checked only as far as what was sent to the model; nobody has listened to all 2,088. That is the one open text item.

## 3. Blood, gore and death

Grades are for master `0bf319c9` unless the column says otherwise. "Card" = the greybox shows the 1997 picture itself on
an upright card at the 1997 size, which is at the 1997 level of gore but not photoreal.

| # | 1997 (engine / data) | Remaster on master | Grade | Notes, evidence |
|---|---|---|---|---|
| G1 | **Hit blood.** Every damaging hit makes `random_blood`: spurt 187-189 (`spurt`, `sprtl`, `sprtr`, last frames 39x56 / 39x56 / 51x56 px) at the victim, played once and then drawn into the background, where it stays until the screen is drawn again (D:6675-6700, brain 5 D:15741-15768). Paths: Dink's blow and a monster's blow (D:14398-14403), missiles (D:15567), touch damage (D:15672), the DinkC `hurt` (D:9953). | Nothing. The simulation does not record it (`DinkBrains.cpp` header: "not ported: ... random_blood") and nothing is drawn. | **missing** -> F1 | The most frequent gore in the game: every fight. |
| G2 | Headless duck bleeds: 1 in 100 frames a `random_blood` (D:12798-12802). | Nothing (the roll is made, the blood not drawn). | missing | PR #113 (unmerged) draws a neck fountain and stains instead; not touched here (coordinator: creature gore is #113's). |
| G3 | Pillbug killed: corpse 141/143 until the screen changes (add_kill_sprite D:12359-12420). | Class corpse `SM_Pillbug_Corpse_PR` with a 620 cm blood decal, removed on screen change (`creatures.json`, `DinkCreaturePresenter.cpp`). | at least 1997 | `Docs/Verification/CreatureClassBinding_13Nov2026`. |
| G4 | Bonca, purple bonca, grey bonca, Bong (550+dir, bodies in pools, 79-96 px), slayers (645, 94x67 px), goblins (765, 785, 805: 73-119 px), stone giants (825, 106x67 px), dragons (212/216), killed people (Jack, the Joppa family, `s7-dgirl`: base_walk + 5, e.g. 345, 365, 225, 415, 335). Each lies until the screen changes. | Nothing is left. The card of the live sprite is hidden at death and only class-bound creatures leave a corpse (`DinkCreaturePresenter::Present`: brains 9/10 and a class row; master binds only the pillbug). Brain 16 kills (people) are not handled by the presenter at all. | **missing** | 13 death pictures across about 120 placed monsters plus script spawns. Needs a body per family (Fable queue GP-Q1-Q4) and, as a code stop-gap, the 1997 death picture on a card (code queue C1). |
| G5 | The dying itself: the death sequence plays before it freezes (add_kill_sprite brain 5). | Pillbug corpse appears at once; others: nothing. | missing | With G4. |
| G6 | Duck: first blow, the head (121-129) flies off and lands in blood; the body runs on headless spraying (111-119); second blow, burst 164 (D:12723-12775). | Master: the duck is a card; the simulation marks it headless but nothing changes on screen. | missing (master) | PR #113 round 4 (its `DinkRemasterUE/Docs/Verification/CreatureGore_14Nov2026`, read on the branch): head flies and lands with a pool, bloody stump, fountain from the neck, burst 2.1 m with drops and feathers, stains; its own weakness list: stain hard to see in tall grass. On those sheets: at least 1997. |
| G7 | Pig killed: burst 164 (pig_brain D:13367-13382). | Screen 407 pigs (origin rows): the body is hidden, nothing drawn. Other pigs: card hidden. | missing (master) | #113: burst 2.1 m; its sheet `gore_3_slime_and_pig.jpg` (looked at): the ball reads pink-red and lighter than the dark 1997 ball of 164; another agent is darkening it now. |
| G8 | Slimes killed: splatter 661/681/701 (26x23 px, brown-red / blue / olive) until the screen changes. | Card hidden, nothing left. | missing (master) | #113: gel blobs and a splatter decal; on `gore_3` the red slime's splash is a small orange-red spot, smaller and lighter than 701 (less than 1997 on that sheet; being fixed in #113). |
| G9 | 46 blood splats placed on screens 60, 61, 91, 94, 122, 126, 154, 158, 190, 191 (187/188/189, cards 0.37-2.4 m wide, up to 3.4 m: S091_P09 at size 243). | All are background placements (greybox instances): the 1997 picture on a card at its size. The environment decal (`decals.blood_splat`, a fixed 90 cm) applies only to actor cards, so it never touches them. | at least 1997 (card) | `doc/remaster/gore_story_parity/gore_placements.csv`. The unpushed `art/gate2-static-decals` / `art/blood-decals-1997` work (decals on instances, sized per picture) is in the Fable queue (GP-Q6): if it lands with the fixed 90/170 cm size it would show *less* than these cards. |
| G10 | Burn holes 158/154 on screens 5, 66, 533, 536 (live cards, 1.0-4.0 m). | Replaced by a deferred decal of a fixed 120 cm (`environment.json` `decals.burn_hole_decal.size_cm`, `ApplyDecals`). On 533/536 the cards are 2.2 x 2.0 m and 4.0 x 3.9 m. | **less than 1997** -> F2 | S005_P27 and the 158/3 cards are the largest. |
| G11 | Burn holes of the burnt house, screen 1 vision 2 (S001_P44-P49, 1.0-1.8 m) and screen 439 (14 holes, 2.3-8.9 m). | Dressed screens keep their manifests: on screen 1 the 1997 cards stay; on 439 the burnt-cottage state swap hides the holes and shows its own burnt model. | at least 1997 (card) on 1; 439 not looked at | The photoreal holes for screen 1 are built on the unpushed branch `art/stonebrook-mother-burnholes` (GP-Q5). |
| G12 | The mother's burnt body, screen 1 vision 1 (S001_P34, picture 355, 1.70 x 1.25 m card; `s1-h1-s.c:3-6`). | The 1997 picture on a card. | at least 1997 (card) | Photoreal body (red head to foot, charred, in a pool) exists on the unpushed branch `art/stonebrook-mother-burnholes` (one clean commit `d404721d`, captures c6 seen by its author, probe and Dink.Art not run): GP-Q5. |
| G13 | Placed corpses: woman in red (S091), knight, girl, two merchants, peasant, dragon 216. | Photoreal corpses in pools sized at least to the 1997 red (PRs #103, #110-#112, #119, #122). | at least 1997 | `Docs/Verification/CorpseBloodExtent_14Nov2026`, `CorpsePeople_14Nov2026`. |
| G14 | Placed corpses still on cards: dragon 212 (S100, S238), Milder the soldier (S086, picture 405), the dead Dink of the cutscene (S058, 436/16), pillbug corpses (3), duck body and head (121/127), 90 duck heads on screen 145. | The 1997 pictures on cards. | at least 1997 (card) | Milder and the dead Dink exist as photoreal meshes on the unpushed branch above (GP-Q5); dragon 212 and the rest: GP-Q7. |
| G15 | Bones and skulls (59 placements). | Photoreal family art. | at least 1997 | `art_coverage.py`: final. |
| G16 | **Dink's death**: `dinfo.c` `die` sets `sp_seq(1, 436)`: 16 frames of Dink falling, then he lies dead for 3 s before the menu. | The hero has no clip for 436 (`hero_actions.json` maps only the fist 102-108): he stands frozen while the menu opens. | **missing** | Fable queue GP-Q8 (death clip), code queue C2. |
| G17 | Seth's death (`s7-boss.c` `die`: "EAT IT!", eight explosions 167), explosions and fire of bombs and spells, the burst 164 of anything else. | A script-made sprite with no family effect row is a small grey marker (`ADinkScriptSpriteActor`); only the gold twinkle (165/166) has an effect row. | missing (not looked at in game) | Fable queue GP-Q9; the #113 README mentions the grey marker beside the dead duck. |
| G18 | Damage numbers over a hit sprite (`draw_damage`, D:12340). | Not drawn (not ported). | missing (not gore; listed for completeness) | Code queue C3. |

Count (18 items, master `0bf319c9`): **at least 1997: 7** (G3, G9, G11, G12, G13, G14, G15; G9, G11, G12 and G14 only as
the 1997 picture on a card), **less than 1997: 1** (G10), **missing: 10** (G1, G2, G4, G5, G6, G7, G8, G16, G17, G18).
After `fix/gore-story-parity`: G1 and G10 at least 1997 (in-game proof in section 4), so 9 / 0 / 8. G2 and G6-G8 come to at
least 1997 if PR #113 lands as its round-4 sheets show (G7/G8 colour and size still being fixed there).

**Parity finding (simulation, not changed).** The 1997 `random_blood` draws one `rand()` for the spurt (D:6693) after
every damaging hit, and the headless duck's bleed draws a second one when its 1-in-100 roll hits. The remaster's
simulation draws neither, so after the first damaging hit its random stream is no longer the 1997 stream. Adding the draw
is a one-line change but moves every probe trace with a fight in it; the probe table (`packaged_probe.md`) would have to
be re-baselined. That is the owner's call, so it is not done; the blood here takes its spurt number
from a hash and leaves the stream alone. Bug list A25.

## 4. Fixes (pull request `fix/gore-story-parity`; code and data only, no new art)

**F1 hit blood (G1).** `UDinkGameplay::NoteBlood` records every `random_blood` call of the 1997 engine where the port
has the same path: the melee blow both ways (`RunThroughTagList`, D:14398-14403), missiles (`MissileBrain`,
D:15567-15568), touch damage (`RunThroughTouchDamageList` -> `HurtAndBleed`, D:15672-15673) and the DinkC `hurt`
command (D:9953-9954), each only when the hit did damage, as in 1997. Recording draws nothing from the random stream and
writes nothing to the event trace (test). A new presentation layer, `UDinkBloodPresenter` (DinkNarrative), lays a blood
decal on the ground under the hit sprite for each new event, its side the longer side of the spurt's last 1997 frame at
the placed splats' 2.5 cm per pixel times 1.15 (161 cm for 187/188, as the 1.40 m picture), spreading over 0.25 s (the
spurt's frames), and removes them all when the screen changes or the director recreates its sprites (a load), as the
1997 background redraw does. Materials: the existing `MI_Decal_BloodSplat_0..3` (`environment.json` `hit_blood`).
`dink.HitBlood 0` turns it off. Not drawn in processes that cannot render (tests and the probe run headless).

**F2 card-sized ground decals (G10).** `UDinkEnvironmentSubsystem::ApplyDecals` now sizes the decal that replaces a
placement's card from that card (`CardDecalSquare`: the larger of the class size and the card's longer side x 1.15) and
centres it where the picture lay. The fixed 120 cm burn holes of screens 5, 66, 533 and 536 become 1.2-4.6 m.

Tests, the probe hashes and the before/after frames: in that pull request
(`DinkRemasterUE/Docs/Verification/GoreParity_15Nov2026/README.md`).

## 5. Open

- G4/G5 corpses of every unbound monster and of killed people (largest gap), G16 Dink's death, G17 explosions: art in the
  Fable queue; a code stop-gap (the 1997 death picture on a card, which needs the death frames in the import bundle) is
  code queue C1.
- G2, G6-G8: PR #113.
- The random stream (A25): owner decision.
- Voice recordings against their text: no automatic check exists.
- Not looked at in the game for this audit: screen 439's burnt cottage, Seth's death, explosions, the cult scene, the
  dragons of screens 100/238.

Code queue (no art needed, not done here):
- C1: leave the 1997 death picture of an unbound killed sprite on a card until the screen changes (needs the death
  sequences' last frames in `ImportData/sprites` and their card materials, then a corpse card in
  `DinkCreaturePresenter` for brains 9, 10 and 16).
- C2: Dink's death until a clip exists: let the hero's mesh fall (ragdoll from `SK_Dink_PhysicsAsset`) when `sp_seq(1, 436)`
  is set; presentation only.
- C3: damage numbers (`draw_damage`).
