#!/usr/bin/env python3
"""Capture script for the landforms pass: play-camera walks and overviews of river, coast, cliff, forest and town-edge screens.

    python3 Scripts/PhotorealQA/landforms_script.py <out dir> [--data <data repo>] [--bundle ImportData] > script.txt
    Scripts/PhotorealQA/run_capture.sh <abs script.txt> [-DinkLandforms=0]     (before: flat ground; after: no switch)

Points are picked from the landforms raster (Scripts/export_landforms.py): walkable ground a few metres from the feature, the
camera looking at it (boom 400 cm, pitch -12 as in the play view), then an oblique overview and one from straight above.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parent.parent
HERE = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
from export_landforms import build, distance, CELL_PX, COLS, SW, SH  # noqa: E402
from remaster_paths import default_data_repo  # noqa: E402


def picks(res, per_class=3):
    h, walk, frac, mpc = res["h"], res["walk"], res["frac"], res["mpp"] * CELL_PX
    by = res["by_num"]
    kind = np.zeros(h.shape, object)
    for s in res["screens"]:
        c, r = s["col"], s["row"]
        kind[r * SH // CELL_PX:(r + 1) * SH // CELL_PX, c * SW // CELL_PX:(c + 1) * SW // CELL_PX] = s["kind"]
    rock = sum(frac["rock_" + k] for k in ("cliff_face", "rock_mass", "cave_wall")) >= 0.5
    sea = np.zeros(h.shape, bool)
    for s in res["screens"]:
        if s["kind"] == "sea" or float(s.get("water_sea", 0) or 0) > 0.6:
            c, r = s["col"], s["row"]
            sea[r * SH // CELL_PX:(r + 1) * SH // CELL_PX, c * SW // CELL_PX:(c + 1) * SW // CELL_PX] = True
    water = res["water"]
    feats = {
        "river": (water & ~sea, lambda: True),
        "coast": (water & sea, lambda: True),
        "cliff": (rock & (h > 1.5), lambda: True),
        "forest": (frac["canopy"] >= 0.5, lambda: True),
        "town_edge": (kind == "settlement", lambda: True),
    }
    out = []
    used = set()
    for name, (mask, _) in feats.items():
        d = distance(mask, 20) * mpc
        cand = walk & (kind == "wilderness") & (d > 2.0) & (d < 4.5) & res["valid"]
        ys, xs = np.nonzero(cand)
        if not len(ys):
            continue
        scr = (ys * CELL_PX // SH) * COLS + (xs * CELL_PX // SW) + 1
        # screens with the most such ground, and the most relief in view
        score = {}
        for n in np.unique(scr):
            sel = scr == n
            score[int(n)] = int(sel.sum())
        best = sorted(score, key=lambda n: -score[n])
        k = 0
        for n in best:
            if n in used or k >= per_class:
                continue
            sel = np.nonzero(scr == n)[0]
            # the point nearest the screen's centre (away from the screen edges), facing the nearest feature cell
            c, r = (n - 1) % COLS, (n - 1) // COLS
            px = xs[sel] * CELL_PX + 2.5 - c * SW
            py = ys[sel] * CELL_PX + 2.5 - r * SH
            i = int(np.argmin((px - 300) ** 2 + (py - 200) ** 2))
            gy, gx = ys[sel][i], xs[sel][i]
            win = mask[max(0, gy - 20):gy + 21, max(0, gx - 20):gx + 21]
            fy, fx = np.nonzero(win)
            j = int(np.argmin((fy + max(0, gy - 20) - gy) ** 2 + (fx + max(0, gx - 20) - gx) ** 2))
            dy, dx = fy[j] + max(0, gy - 20) - gy, fx[j] + max(0, gx - 20) - gx
            yaw = math.degrees(math.atan2(dy, dx))
            out.append((name, n, float(px[i]), float(py[i]), yaw))
            used.add(n)
            k += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--data", default=str(default_data_repo(HERE)))
    ap.add_argument("--bundle", default=str(HERE / "ImportData"))
    ap.add_argument("--audit", action="store_true", help="end with dink.LandformsAudit")
    a = ap.parse_args()
    res = build(Path(a.data), Path(a.bundle), HERE, log=lambda *x: None)
    L = ["wait 8", "dink.Wind 0"]
    for name, n, x, y, yaw in picks(res):
        tag = f"{name}_{n:03d}"
        L += ["dink.CalCam off", f"dink.Goto {n} {x + 20:.0f} {y:.0f}", "dink.CameraDistance 400", "FOV 0", "wait 1",
              f"dink.View {yaw:.0f} -12", "wait 6", "dink.Player", f"fps {tag}_play", f"shot {a.out}/{tag}_play.png", "wait 1",
              f"dink.View {yaw + 180:.0f} -12", "wait 3", f"shot {a.out}/{tag}_back.png", "wait 1"]
        ox, oy = -math.cos(math.radians(yaw)) * 2600, -math.sin(math.radians(yaw)) * 2600
        L += ["dink.CalAnchor 0 0", f"dink.CalCam {ox:.0f} {oy:.0f} 1300 0 0 100 70 1", "wait 3", f"shot {a.out}/{tag}_oblique.png", "wait 1",
              "dink.CalCam 0 1 4200 0 0 0 80", "wait 3", f"shot {a.out}/{tag}_above.png", "wait 1"]
    # a walk over a screen border (462 -> 463, both wilderness with relief): continuity at the play camera
    for k, (n, x) in enumerate(((462, 520), (462, 580), (463, 20), (463, 80))):
        L += ["dink.CalCam off", f"dink.Goto {n} {x + 20} 300", "dink.CameraDistance 400", "FOV 0", "wait 1", "dink.View 0 -12", "wait 4",
              f"fps border_{k}", f"shot {a.out}/border_{k}_{n}_{x}.png", "wait 1"]
    L += ["dink.CalCam off"]
    if a.audit:
        L += ["dink.LandformsAudit 80", "wait 1"]
    L += ["quit"]
    print("\n".join(L))


if __name__ == "__main__":
    main()
