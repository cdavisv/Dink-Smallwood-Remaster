#!/usr/bin/env python3
"""Draw the terrain-layer masks of a block of screens side by side as the 1997 map lays them out, one flat colour per
layer, so layer outlines and their continuity across screen borders can be looked at without the game.

    python3 -I Scripts/PhotorealQA/ground_mask_mosaic.py <ImportData dir> <out.png> <screen> [<screen> ...] [--radius 1] [--scale 3]

Each named screen is drawn with `radius` screens round it (map order, 32 columns). The weights are the mask's RGB
(layers 1-3 of the screen's `ground_layers`) and the remainder (layer 4); water (alpha below 0.5) is drawn blue.
Several centres are stacked top to bottom. Screens without a mask are grey."""
import argparse
import json
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

FIXED = {"MeadowTurf": (88, 140, 52), "RockyGrass": (170, 180, 120), "WildGrass": (120, 160, 60), "EarthPath": (150, 105, 65),
         "TransitionDirt": (180, 130, 80), "ForestFloor": (95, 80, 50), "DrySand": (225, 205, 150), "WetSand": (150, 130, 95),
         "ShingleBeach": (160, 160, 150), "CliffRock": (110, 105, 100), "CaveRock": (80, 75, 70), "CobbleStreet": (130, 120, 115),
         "Snow": (240, 240, 245), "SnowTrampled": (205, 210, 220), "ScorchedSoil": (70, 50, 40), "PondMud": (90, 80, 55)}


def colour(name):
    if name in FIXED:
        return np.array(FIXED[name], float)
    h = zlib.crc32(name.encode())
    return np.array([(h >> s) & 255 for s in (0, 8, 16)], float)


def screen_image(bundle, rec, scale):
    w, h = 96 * scale, 64 * scale
    if not rec or not rec.get("ground_mask"):
        return Image.new("RGB", (w, h), (60, 60, 60))
    m = np.asarray(Image.open(bundle / rec["ground_mask"]).convert("RGBA"), float) / 255.0
    names = [l["name"] for l in rec["ground_layers"]]
    weights = [m[:, :, i] for i in range(min(3, len(names)))]
    if len(names) == 4:
        weights.append(np.clip(1.0 - m[:, :, 0] - m[:, :, 1] - m[:, :, 2], 0.0, 1.0))
    total = sum(weights) if weights else np.ones(m.shape[:2])
    rgb = sum(wi[:, :, None] * colour(n)[None, None] for wi, n in zip(weights, names)) / np.maximum(total, 1e-6)[:, :, None]
    water = np.clip((0.5 - m[:, :, 3]) * 4.0, 0.0, 1.0)[:, :, None]
    rgb = rgb * (1 - water) + np.array([40, 90, 150], float) * water
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("out"); ap.add_argument("screens", nargs="+", type=int)
    ap.add_argument("--radius", type=int, default=1); ap.add_argument("--scale", type=int, default=3)
    a = ap.parse_args()
    bundle = Path(a.bundle)
    recs = {s["screen"]: s for s in json.loads((bundle / "screens.json").read_text())["screens"]}
    side = 2 * a.radius + 1
    w, h = 96 * a.scale, 64 * a.scale
    sheet = Image.new("RGB", (side * w, len(a.screens) * side * h), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for k, centre in enumerate(a.screens):
        col, row = (centre - 1) % 32, (centre - 1) // 32
        for dr in range(-a.radius, a.radius + 1):
            for dc in range(-a.radius, a.radius + 1):
                c, r = col + dc, row + dr
                n = r * 32 + c + 1 if 0 <= c < 32 and r >= 0 else None
                x, y = (dc + a.radius) * w, (k * side + dr + a.radius) * h
                sheet.paste(screen_image(bundle, recs.get(n), a.scale), (x, y))
                draw.text((x + 4, y + 2), str(n), fill=(255, 255, 255))
    sheet.save(a.out)


if __name__ == "__main__":
    main()
