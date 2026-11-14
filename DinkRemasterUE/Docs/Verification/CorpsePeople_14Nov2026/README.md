# Five dead people, opened as their pictures show, at the measured footprint (14 Nov 2026)

Review of PR #103 rejected the first bodies on both rules: intact bodies with surface gashes (less gory than 1997),
and stiff dolls dipped in red, arms in the air, about 1.6 times too large. This is the rebuild
(`person2()` and the table `PEOPLE` in `SourceAssets/Art/PhotorealPass/Corpses/tools/build_gore.py`). Visual only;
no C++. Stacked on the blood rework (PR #110) and the knight (PR #111).

## Bound

| Family | Picture | Placement | Mesh | What is open |
|---|---|---|---|---|
| `corpse_girl` | 335 | S222_P04 | `SM_Corpse_Girl_PR` | belly and chest torn open over ribs and entrails; a lower leg and a forearm torn off |
| `corpse_maiden` | 245 | S091_P21 | `SM_Corpse_Maiden_PR` | torn open from throat to belly, ribs bare, entrails out |
| `corpse_merchant` | 345 (blue) | S094_P01 | `SM_Corpse_Merchant_PR` | chest split to the ribs, belly cut open with entrails out, a forearm struck off |
| `corpse_merchant` | 385 (green) | S092_P01 | `SM_Corpse_Merchant_Green_PR` | belly cut across with entrails out, shoulder and chest split |
| `corpse_peasant` | 415 | S222_P05 | `SM_Corpse_Peasant_PR` | chest split to the ribs, belly cut open; his long-handled sickle beside him |

## How a body is made

- **Pose:** from the rigged character of `PhotorealPass/Unclaimed`, not the frozen "corpse" meshes: upper and lower
  arms and legs are aimed into the plane of the back, bent at elbow and knee, so they lie on the ground; the head is
  rolled to a side; each limb is then sunk to the ground towards its end, and a wide skirt is folded towards the body.
  No cloth simulation.
- **Opened:** the front is cut away over a ragged patch, the edge turned inwards as raw flesh, and inside lie a mass
  of muscle, rib rods (some snapped) and loops of gut pulled out over the side onto the ground. Severed parts are split
  off at the joint, thrown a little way, with a stump of flesh and bone at both ends.
- **Blood:** only round the wounds, where the body lies in the pool, and in a few thrown spots: the clothes keep
  their blue, green, pink and linen. The pool is the blood of PR #110.
- **Size, measured:** the body is scaled (never up) so that body and pool, drops included, stay inside the card
  width of the placement in `placements.json`. `Scripts/tests/test_corpse_kit.py` now checks that from the manifests.

| Asset | sprite card | pool incl. drops | body scale |
|---|---:|---:|---:|
| Girl | 1.45 m | 1.27 m | 1.00 |
| Maiden | 1.57 m | 1.56 m | 0.83 |
| Merchant (blue) | 1.85 m | 1.78 m | 1.00 |
| Merchant (green) | 1.85 m | 1.77 m | 0.97 |
| Peasant | 2.85 m | 1.89 m | 1.00 |

## Seen in the game

`people_1_girl_maiden_merchant.jpg`, `people_2_merchant_peasant.jpg`: 1997 picture, the sprite card before, this
change at the play camera, the rejected first version close, this change close (the cameras of PR #103's sheets).

- All five read as bodies cut open and left lying: entrails on the ground, ribs showing, limbs flat, clothes in
  their own colours, a dark pool under them. The girl is in pieces, as her picture is.
- **Where they fall short, plainly:**
  - The 1997 pictures are red almost all over. These have far less red: the pools are small (they must fit the
    footprint) and the clothes are mostly clean. More is cut open than in 1997's pixels can show; less is covered in
    blood.
  - The entrails are even tubes, like thick noodles; ribs are plain rods; there are no organs. The woman in red
    shows a row of ribs but little depth behind them.
  - Faces are doll-like and soft from the re-bake; eyes bake dark. Hands of the woman in red tilt up off the ground.
  - The woman in red is 0.83 of her living size to fit 1.57 m; next to living characters she will look small.
  - 30,000 to 55,000 triangles each (LOD0 of the character plus the gore), no LODs.
- The peasant's card is 2.85 m wide because the picture includes his long pole; his pool is 1.89 m.

## Left unbound

- **Soldier (405, S086_P01, scripted):** built the same way (`left_unbound_soldier.jpg`). Screen 86 is dark: the dark
  pool can hardly be told from the ground and the wounds cannot be judged; a gauntlet stands up off the ground. Not
  bound until it has been looked at in light. Its asset is not in the repository; `PEOPLE['Corpse_Soldier']` builds it.
- **Dink (436, S058_P06, scripted)** and **the mother (355, screen 1)**: not rebuilt. Dink's rig is the hero file, which
  `person2()` does not read yet; the mother cannot be bound by a family row (screen 1 is dressed by its manifest).

| `art_coverage.py` | before (PR #111) | after |
|---|---:|---:|
| final | 4,913 | 4,918 |
| placeholder | 1,542 | 1,537 |

## Not checked

- The captures used the private copy's binaries of master `80ff12f1`. Night, a packaged build, the live play camera
  with the player walking round the bodies.
- The maiden's capture shows the unrelated flower-girl sprite standing next to her (another placement).
