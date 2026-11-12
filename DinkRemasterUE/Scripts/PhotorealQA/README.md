# Photoreal pass: capture and calibration tools

Review tools of the photoreal art pass (see `SourceAssets/Art/PhotorealPass/IMPORT.md`). They render offscreen
(no display, no input) and write only below `Saved/PhotorealPass/`, which is git-ignored. All paths are derived
from this folder, so they run from any checkout. `UE_ROOT` names the engine (default `~/UnrealEngine/UE_5.8.4`).

- `run_capture.sh <ABSOLUTE script> [engine args]`: runs one capture script (`dink.CaptureScript`: `wait`, `shot`,
  `fps` lines and console commands). In the scripts kept here `<PROJECT>` stands for the `DinkRemasterUE` folder.
- `round.sh <name> [--extra]`: the fixed review cameras into `Saved/PhotorealPass/lighting/<name>/` and a sheet.
- `cal.sh <tag> [--only ...] [--var name='cmd;cmd']` + `cal_compare.py <tag>`: foliage calibration against the
  Cycles review renders; `cal2_script.py`, `cal2_compare.py`, `cal2_patches.json`: structures.
- `pick6.py <out dir> <prefix> [name parts]`: a capture script from the camera blocks of `ingame5a.txt` / `ingame5b.txt`.
- `make_script.py`, `indoor_script.py`, `cal_script.py`: script generators; `*_sheet.py`, `contact_sheet.py`,
  `montage.py`: contact sheets (need Pillow; `cal*_compare.py` also numpy).
- `*.txt`: the capture scripts of the integration rounds as they were run (`ingame6a/b/c.txt` is the final set).
