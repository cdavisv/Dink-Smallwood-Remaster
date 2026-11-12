# Unclaimed families: photoreal sources

Blender sources for the sprite families of alpha gate 2 that no stream had claimed (`doc/remaster/ALPHA_GATE2_BACKLOG.md`).

- `STATUS.md`: every unclaimed family as delivered / partial / not started, with one line why, and the validator table.
- `contact_sheet.png`: the final render of every asset.
- `<family>/<Asset>/`: FBX, baked `T_*_BC/N/ORM.png`, source `.blend`, `manifest.json`, final renders.
- `validation_summary.json`: `tools/blender/dinkasset/validate.py` per asset.
- `tools/`: `bl.sh build_<group>.py <name|all> [review|final]` rebuilds an asset; `make_status.py` regenerates `STATUS.md` and the contact sheet; `validate_all.py` reruns the validator.

These are source candidates: nothing here is imported into Unreal or bound in `families.json`. CC0 scans used by the builds are under the sibling `ThirdParty` directory with their provenance in `downloads.csv`.

An earlier snapshot of this folder (the red pepper and the first tools) reached `master` through a reconciliation commit before the rest was built; this folder supersedes it.
