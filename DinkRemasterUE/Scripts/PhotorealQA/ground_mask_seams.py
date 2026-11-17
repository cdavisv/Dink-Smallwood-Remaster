#!/usr/bin/env python3
"""How much the ground-layer weights step across screen borders, over the whole world.

    python3 -I Scripts/PhotorealQA/ground_mask_seams.py <ImportData dir> [--top 10]

For every pair of outdoor screens that lie against each other on the 1997 map and in the world layout (shared
corners), the edge texels of both terrain masks along the shared edge are compared layer by layer (by name; a layer
one side lacks counts as 0 there; the fourth layer is the remainder of R + G + B). Prints the number of borders, how
many step by more than 0.15 / 0.5 anywhere along the edge, the mean largest step, and the worst borders. With the
edge-aligned masks of the natural outlines both screens hold the same weights on the edge (step 0 up to 8-bit
rounding); the tile-shaped masks hold each screen's own tiles half a texel in from it."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image


def weights(bundle, rec):
    m = np.asarray(Image.open(bundle / rec["ground_mask"]).convert("RGBA"), float) / 255.0
    names = [l["name"] for l in rec["ground_layers"]]
    out = {}
    for i, n in enumerate(names[:3]):
        out[n] = out.get(n, 0) + m[:, :, i]
    if len(names) == 4:
        out[names[3]] = out.get(names[3], 0) + np.clip(1.0 - m[:, :, 0] - m[:, :, 1] - m[:, :, 2], 0.0, 1.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    bundle = Path(a.bundle)
    recs = {s["screen"]: s for s in json.loads((bundle / "screens.json").read_text())["screens"]}
    usable = {n: r for n, r in recs.items() if r.get("ground_mask") and not r.get("indoor")}
    steps = []
    for n, r in sorted(usable.items()):
        col = (n - 1) % 32
        for m, own, theirs in ((n + 1, ("ne", "se"), ("nw", "sw")), (n + 32, ("sw", "se"), ("nw", "ne"))):
            if m not in usable or (m == n + 1 and col == 31):
                continue
            o = usable[m]
            if not all(math.dist(r["corners"][p], o["corners"][q]) < 0.01 for p, q in zip(own, theirs)):
                continue
            wa, wb = weights(bundle, r), weights(bundle, o)
            east = m == n + 1
            worst = 0.0
            for k in set(wa) | set(wb):
                ea = wa[k][:, -1] if k in wa and east else wa[k][-1, :] if k in wa else 0.0
                eb = wb[k][:, 0] if k in wb and east else wb[k][0, :] if k in wb else 0.0
                worst = max(worst, float(np.max(np.abs(np.asarray(ea) - np.asarray(eb)))))
            steps.append((worst, n, m))
    s = np.array([w for w, _, _ in steps]) if steps else np.zeros(1)
    print(f"{len(steps)} borders between outdoor screens; step > 0.15: {int((s > 0.15).sum())}, > 0.5: {int((s > 0.5).sum())}; "
          f"mean largest step {s.mean():.3f}")
    for w, n, m in sorted(steps, reverse=True)[:a.top]:
        print(f"  {n:03d}|{m:03d}  {w:.2f}")


if __name__ == "__main__":
    main()
