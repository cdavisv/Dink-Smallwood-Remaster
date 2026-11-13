# Unclaimed families: photoreal sources

Blender sources for the sprite families of alpha gate 2 that no stream had claimed (`doc/remaster/ALPHA_GATE2_BACKLOG.md`).

- `STATUS.md`: every unclaimed family as delivered / partial / not started, with one line why, and the validator table.
- `contact_sheet.png`: the final render of every asset.
- `<family>/<Asset>/`: FBX, baked `T_*_BC/N/ORM.png`, source `.blend`, `manifest.json`, final renders. Decal families hold texture sets only; effect families hold a flipbook atlas (`T_FX_*_Flipbook.png`) and a strip of sample frames.
- NPC variants and corpses (`npc_maiden_*`, `npc_soldier`, `corpse_*`, `dink_dead`) are derived from the characters under `PhotorealPass/Characters` and reference their normal and ORM maps.
- The civilian NPCs (`npc_merchant_*`, `npc_peasant`, `npc_old_man`, `npc_girl`, `npc_gnome_purple`, `king_on_throne`) and their corpses are built by `tools/build_people.py` on the CC0 MakeHuman base mesh under `Art/Characters/ThirdParty/MakeHuman` (`tools/mhlib.py` loads it, `tools/people.py` morphs, dresses, rigs and bakes it). Each has its own complete texture set.
- `validation_summary.json`: `tools/blender/dinkasset/validate.py` per asset.
- `tools/`: `bl.sh build_<group>.py <name|all> [review|final]` rebuilds an asset; `make_status.py` regenerates `STATUS.md` and the contact sheet; `validate_all.py` reruns the validator.

These are source candidates: nothing here is imported into Unreal or bound in `families.json`. CC0 scans used by the builds are under the sibling `ThirdParty` directory with their provenance in `downloads.csv`.

An earlier snapshot of this folder (the red pepper and the first tools) reached `master` through a reconciliation commit before the rest was built; this folder supersedes it.
