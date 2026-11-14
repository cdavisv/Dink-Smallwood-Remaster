# Corpse kit: the torn dragon bound with its gore (14 Nov 2026)

The owner's rule: keep all the original gore and dark comedy. PR #90 left the dead dragon as a sprite card because the
mesh was cleaner than the 1997 pictures. This step adds a kit whose meshes carry their gore
(`SourceAssets/Art/PhotorealPass/Corpses/`) and binds the dragon remains in `Content/Dink/Data/Art/families.json`.
Visual only: collision, hardboxes, scripts and origin IDs are untouched, and no C++ changed.

The first version of this change also bound the dead knight and seven human bodies. They were taken out in review
(see "Built and rejected") and are sprite cards again.

## Result

| | before | after |
|---|---:|---:|
| `art_coverage.py` final | 4,663 | 4,666 |
| placeholder | 1,792 | 1,789 |
| cut | 152 | 152 |

3 placements of 1 family turned from placeholder to final. 2 rows were added to `families.json`; they use 1 mesh,
imported into `/Game/Dink/Photoreal/Corpses` (`DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh`:
2 materials, 1 module, 0 warnings).

| Family | 1997 picture | Placement (screen) | Mesh |
|---|---|---|---|
| `dragon_corpse` | 212 | S100_P34, S238_P12 | `SM_Dragon_Corpse_PR` |
| `dragon_corpse` | 216 | S158_P07 | `SM_Dragon_Corpse_PR`, turned 180 degrees |

## What a mesh of the kit is

One static mesh, two material slots. Slot 0 is the body on one baked 2048 px atlas: the rigged dragon of
`PhotorealPass/Unclaimed`, posed, pressed to the ground and cut open, with ribs, backbone, raw muscle, entrails, a
torn-off wing and thrown chunks. Slot 1 is an alpha-tested card 6 mm above the ground with the pool, the thrown drops
and the mist (material kind `masked`, new in `import_town_exteriors.py`). A family row places one mesh and nothing
else, so the pool has to be in the mesh. `Scripts/tests/test_corpse_kit.py` fails when a body is bound without its pool card.

## How it was judged

Captured in the running game, offscreen (`Scripts/PhotorealQA/run_capture.sh`, 1280x720): `dink.Goto` to the placement,
`dink.CalAnchor 0 0`, then two fixed cameras with `dink.CalCam`, one at about the play camera (6.5 m back, 5.2 m up;
the sheets crop its middle 2.2 times) and one close (3 m back, 1.9 m up). The same script ran first with master's
`families.json` for the "before" columns. The first column of every row is the 1997 picture
(`ImportData/sprites/<seq>_<frame>.png`, enlarged, on green). Nothing was retouched.

| File | What it shows |
|---|---|
| `before_after_dragon.jpg` | Picture 216 on dry earth (screen 158), picture 212 on grass (238) and in the dark (100). |
| `dragon_screen100_lit.jpg` | Screen 100 again, after only, with the exposure raised (`r.ExposureOffset 5`). |
| `built_and_rejected_in_review.jpg` | The knight and the seven bodies as first built: NOT in this change. |
| `tried_and_left_unbound.jpg` | The mother (screen 1), three blood sprays and two burn holes with trial rows: "after" is what those rows drew. |

What I see:

- **Picture 216, screen 158 (dry earth).** 1997: a carcass torn open, red flesh in blocks, one wing off, the tail
  arched, drops thrown. Game: hide torn open over a rib cage and backbone, raw muscle, loops of gut, a wing lying
  beside it, chunks thrown clear, a wide pool. The muscle is lumpy rather than anatomical and the wing panels are flat.
- **Picture 212, screen 238 (grass).** The body, ribs and thrown flesh show. **The pool card is hidden by the grass
  carpet**: flecks of red between the blades is all that is left of it. Picture 212 has flesh and drops but no pool.
  Open: the pool has to stain the ground (a deferred decal); a family row cannot place one yet.
- **Picture 212, screen 100.** Nearly black in the normal capture. With the exposure raised (`dragon_screen100_lit.jpg`): **most of the
  remains stand inside a greybox wall block**; only the pool, a foot and a few chunks show in front of it. The placement
  is at map y 396, the bottom edge of a dark indoor screen. Not better than the card there (the card is in the same
  place and as dark); the row is per picture, so it cannot leave this one placement out. Counted final by the audit; I
  would not call it done. No lit "before" was captured.
- **Blood.** Too vivid and too flat in the game (review): the middle is not dark enough, there is no damp fringe soaked
  into the earth, the thin rim is a bright red line. Open.
- **Size, measured.** Sprite cards (`placements.json` `card.width_m`): 2.35 m for picture 216, 2.62 m for 212. The mesh:
  body and the dense part of the pool 2.9 m across (pool card columns with more than 3 % cover), furthest drops 3.9 m,
  card 4.9 m. So the remains are 1.1 to 1.25 times the sprite's footprint, more with the outer drops.

## Built and rejected

`built_and_rejected_in_review.jpg` shows the dead knight (275) and the bodies of pictures 345, 385, 335, 415, 245,
405 and 436 as first built and captured. The coordinator's review rejected them, and they are not in this change:

- Knight: one glossy red all over, a plastic toy; the picture is grey-brown steel lying in blood.
- People: intact bodies with surface gashes, while pictures 335 and 245 are bodies torn open and the others hacked:
  less gory than 1997. Stiff poses with arms in the air, a full-body red tint that hides the clothing colours, sharp
  frozen hems.
- Size, measured afterwards: sprite cards 1.45 to 2.02 m wide (girl 1.45, woman in red 1.57, merchants and soldier
  1.85, knight 2.02; the peasant with his pole 2.85, Dink 2.60) against meshes of 2.5 to 3.3 m with their pools:
  about 1.6 times too large for most.

`tools/build_gore.py` still holds their recipes (`HUMANS`, `knight()`); none of their assets is in the repository.

## Left unbound, with the cause

Read from `Plugins/DinkCore/Source/DinkCore/Private/DinkArtFamilySubsystem.cpp` and `DinkEnvironmentSubsystem.cpp`:

- **`corpse_mom`** (S001_P34, screen 1). `Content/Dink/Data/Art/stonebrook.json` lists screen 1 under
  `hide_screen_visuals` and `authored_collision_screens`; `FDinkFamilyPrecedence::AddManifest` puts such screens into
  `Precedence.Screens`, and `DinkArtFamily::Decide` returns `ScreenDressed` for every placement of them before it looks
  at the rows. Only the Stonebrook manifest can dress her.
- **`burn_hole_decal`** (26 placements), three causes: 16 are on the dressed screens 1 and 439 (`ScreenDressed`, as above); 2 are
  scripted and the trial rows had no `"scripted": true` (`Decide` returns `Scripted`); for the unscripted actors
  `UDinkEnvironmentSubsystem::ApplyDecals` hides the card and draws the deferred decal of `environment.json`, and
  `UDinkArtFamilySubsystem::DressActor` returns early for a card that is hidden. That the decal comes first is read
  from the captures (rows of screens 533 and 536: the same decal before and after), not from a log.
- **`blood_splat`** (46, all background instances): the trial cards did bind. They came out as one small flat splat,
  smaller and plainer than the 1997 spray: not better than the sprite, so the rows were removed.

## Checks

- `python3 -m unittest discover -s Scripts/tests`: 853 tests, OK, with the new `test_corpse_kit.py`.
- `Scripts/test.sh Dink.Art`: 58/58 passed in the private copy with only this kit imported, on master `96a9b31a`. The branch was then rebased over PRs #104, #105 and #107 (which change C++); the run on the rebased tree is in the PR text if it has been made.
- `Scripts/scrub_private_paths.py --check`, `tools/lfs_audit.py HEAD`, `Scripts/verify_sources.py --metadata-only`: results in the PR text.
- The probe was not run: no C++ and no gameplay data changed (family rows are presentation only).

## Not checked

- The live play camera with the player walking round the remains: not looked at.
- A packaged build: `Scripts/package.sh` cooks `Content/Dink/Photoreal` since PR #102, so the kit should be in it, but no package was made here.
- Captures are from the editor's game mode in a private copy whose generated world is of 12 Nov.
