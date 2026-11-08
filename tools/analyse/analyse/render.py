"""PNG renderings: connectivity.png, regions.png, layout_preview.png."""

import colorsys
import hashlib
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .ir import W, H, GRID_W, GRID_H, col_row

DS = 5                       # downsample of world_tiles.png (120 x 80 per screen)
SW, SH = W // DS, H // DS


def font(size, bold=False):
    for p in ("/usr/share/fonts/liberation/LiberationSans-%s.ttf" % ("Bold" if bold else "Regular"),
              "/usr/share/fonts/TTF/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def colour(key, s=0.75, v=0.95):
    h = int(hashlib.md5(str(key).encode()).hexdigest()[:6], 16) / 0xFFFFFF
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def outlined(d, xy, text, f, fill=(255, 255, 255), anchor="mm"):
    x, y = xy
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx or dy:
                d.text((x + dx, y + dy), text, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text((x, y), text, font=f, fill=fill, anchor=anchor)


def base_map(ir, dim=0.45):
    im = Image.open(os.path.join(ir.dir, "world_tiles.png")).convert("RGB")
    a = np.asarray(im).astype(np.float32) * dim
    return a


def render_connectivity(ir, comps, reached, group_of, comp_water_kind, crossings, warps, swarps, path,
                        min_pocket_px):
    a = base_map(ir, 0.35)
    cls_col = {"water": (40, 90, 200), "canopy": (20, 70, 30), "void": (0, 0, 0), "blocked": (90, 70, 50)}
    wk_col = {"sea": (30, 60, 170), "lake": (60, 140, 230), "river": (80, 200, 255), "puddle": (60, 140, 230)}
    for n in ir.used:
        c, r = col_row(n)
        sc = comps[n]
        lab = sc.labels[::DS, ::DS]
        tile = a[r * SH:(r + 1) * SH, c * SW:(c + 1) * SW]
        out = tile.copy()
        for k in range(1, sc.count + 1):
            m = lab == k
            if not m.any():
                continue
            cl = sc.terrain_class(k)
            if (n, k) in reached:
                col = colour(group_of[(n, k)], 0.55, 0.95)
                alpha = 0.55
            elif cl in cls_col:
                col = wk_col.get(comp_water_kind.get((n, k)), cls_col[cl])
                alpha = 0.5
            elif sc.area[k] >= min_pocket_px:
                col, alpha = (255, 40, 40), 0.75          # unreached land pocket
            else:
                col, alpha = (120, 120, 120), 0.4
            out[m] = tile[m] * (1 - alpha) + np.array(col) * alpha
        a[r * SH:(r + 1) * SH, c * SW:(c + 1) * SW] = out
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    im = im.resize((im.width * 2 // 2, im.height * 2 // 2))
    d = ImageDraw.Draw(im)
    # grid
    for c in range(GRID_W + 1):
        d.line([(c * SW, 0), (c * SW, GRID_H * SH)], fill=(70, 70, 70))
    for r in range(GRID_H + 1):
        d.line([(0, r * SH), (GRID_W * SW, r * SH)], fill=(70, 70, 70))
    # crossings
    for x in crossings:
        if not x.get("walkable"):
            continue
        ca, ra = col_row(x["a"])
        colr = (255, 255, 255) if x.get("reached") else (255, 80, 80)
        if x["axis"] == "y":
            X = (ca + 1) * SW
            d.line([(X, ra * SH + x["from"] / DS), (X, ra * SH + x["to"] / DS)], fill=colr, width=3)
        else:
            Y = (ra + 1) * SH
            d.line([(ca * SW + x["from"] / DS, Y), (ca * SW + x["to"] / DS, Y)], fill=colr, width=3)
    # warps
    for w in warps:
        if not w["dst_screen_exists"]:
            continue
        cs, rs = col_row(w["src_screen"])
        cd, rd = col_row(w["dst_screen"])
        p0 = (cs * SW + w["x"] / DS, rs * SH + w["y"] / DS)
        p1 = (cd * SW + w["dst_x"] / DS, rd * SH + w["dst_y"] / DS)
        d.line([p0, p1], fill=(255, 220, 0), width=1)
        d.ellipse([p0[0] - 3, p0[1] - 3, p0[0] + 3, p0[1] + 3], outline=(255, 220, 0), width=2)
        d.rectangle([p1[0] - 2, p1[1] - 2, p1[0] + 2, p1[1] + 2], fill=(255, 220, 0))
    for w in swarps:
        if not w["dst_screen_exists"] or w["dst_x"] is None:
            continue
        cd, rd = col_row(w["dst_screen"])
        p1 = (cd * SW + w["dst_x"] / DS, rd * SH + w["dst_y"] / DS)
        for s in w["src_screens"]:
            cs, rs = col_row(s)
            p0 = (cs * SW + SW / 2, rs * SH + SH / 2)
            d.line([p0, p1], fill=(255, 0, 255), width=1)
        d.rectangle([p1[0] - 2, p1[1] - 2, p1[0] + 2, p1[1] + 2], fill=(255, 0, 255))
    f = font(22, True)
    legend = [((255, 255, 255), "walkable edge crossing (reached)"), ((255, 80, 80), "walkable crossing, unreached"),
              ((255, 40, 40), "unreached land pocket"), ((255, 220, 0), "sprite warp (o src, # dst)"),
              ((255, 0, 255), "script warp"), ((30, 60, 170), "sea"), ((60, 140, 230), "lake"),
              ((80, 200, 255), "river"), ((20, 70, 30), "forest canopy")]
    y = GRID_H * SH - 30 * len(legend) - 10
    for col, txt in legend:
        d.rectangle([10, y, 34, y + 20], fill=col)
        outlined(d, (42, y + 10), txt, f, anchor="lm")
        y += 30
    outlined(d, (10, 12), "Reached land: one tint per walk group (connected by walking).", font(22, True), anchor="lm")
    im.save(path, optimize=True)


def render_regions(ir, screen_rows, path):
    a = base_map(ir, 0.6)
    regs = {}
    for row in screen_rows:
        n = row["screen"]
        c, r = col_row(n)
        col = np.array(colour(row["region"], 0.7, 0.95), np.float32)
        tile = a[r * SH:(r + 1) * SH, c * SW:(c + 1) * SW]
        alpha = 0.55 if row["kind"] in ("settlement", "interior", "dungeon") else 0.35
        a[r * SH:(r + 1) * SH, c * SW:(c + 1) * SW] = tile * (1 - alpha) + col * alpha
        regs.setdefault(row["region_name"], []).append((c, r, row))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for row in screen_rows:
        c, r = col_row(row["screen"])
        if row["kind"] == "settlement":
            d.rectangle([c * SW + 2, r * SH + 2, (c + 1) * SW - 3, (r + 1) * SH - 3], outline=(255, 255, 255), width=2)
        elif row["kind"] == "dungeon":
            d.rectangle([c * SW + 2, r * SH + 2, (c + 1) * SW - 3, (r + 1) * SH - 3], outline=(255, 60, 60), width=2)
        if row["confidence"] == "low":
            d.line([(c * SW + 4, r * SH + 4), (c * SW + 20, r * SH + 20)], fill=(255, 0, 0), width=3)
    # region borders
    reg_at = {col_row(row["screen"]): row["region"] for row in screen_rows}
    for (c, r), g in reg_at.items():
        if reg_at.get((c + 1, r), g) != g:
            d.line([((c + 1) * SW, r * SH), ((c + 1) * SW, (r + 1) * SH)], fill=(255, 255, 255), width=2)
        if reg_at.get((c, r + 1), g) != g:
            d.line([(c * SW, (r + 1) * SH), ((c + 1) * SW, (r + 1) * SH)], fill=(255, 255, 255), width=2)
    f = font(26, True)
    for name, cells in regs.items():
        outdoor = [(c, r) for c, r, row in cells if not row["indoor"]] or [(c, r) for c, r, _ in cells]
        cx = np.mean([c for c, r in outdoor]) * SW + SW / 2
        cy = np.mean([r for c, r in outdoor]) * SH + SH / 2
        outlined(d, (cx, cy), name, f)
    fs = font(20, True)
    y = 10
    for txt, col in (("white frame: settlement", (255, 255, 255)), ("red frame: dungeon", (255, 60, 60)),
                     ("red tick: low-confidence assignment", (255, 0, 0)),
                     ("indoor screens are coloured by the region of their door", (255, 255, 255))):
        outlined(d, (GRID_W * SW - 10, y + 10), txt, fs, fill=col, anchor="rm")
        y += 26
    im.save(path, optimize=True)


def _inverse_bilinear(P, X, Y, iters=8):
    """Vectorised inverse of the screen map; returns u, v in [0,1] coordinates."""
    u = np.full(X.shape, 0.5)
    v = np.full(X.shape, 0.5)
    for _ in range(iters):
        px = (1 - u) * (1 - v) * P[0, 0] + u * (1 - v) * P[1, 0] + (1 - u) * v * P[2, 0] + u * v * P[3, 0] - X
        py = (1 - u) * (1 - v) * P[0, 1] + u * (1 - v) * P[1, 1] + (1 - u) * v * P[2, 1] + u * v * P[3, 1] - Y
        dxu = (1 - v) * (P[1, 0] - P[0, 0]) + v * (P[3, 0] - P[2, 0])
        dyu = (1 - v) * (P[1, 1] - P[0, 1]) + v * (P[3, 1] - P[2, 1])
        dxv = (1 - u) * (P[2, 0] - P[0, 0]) + u * (P[3, 0] - P[1, 0])
        dyv = (1 - u) * (P[2, 1] - P[0, 1]) + u * (P[3, 1] - P[1, 1])
        det = dxu * dyv - dxv * dyu
        u = u - (px * dyv - py * dxv) / det
        v = v - (py * dxu - px * dyu) / det
    return u, v


def _panel(ir, L, info, tiles, x0, y0, x1, y1, width_px, title, label_size=22):
    mpp = (x1 - x0) / width_px
    hgt = int((y1 - y0) / mpp) + 1
    canvas = np.zeros((hgt, width_px, 3), np.uint8)
    canvas[:] = (12, 22, 40)
    for n, P in L.corners.items():
        Q = (P - [x0, y0]) / mpp
        bx0, by0 = np.floor(Q.min(0)).astype(int)
        bx1, by1 = np.ceil(Q.max(0)).astype(int)
        if bx1 < 0 or by1 < 0 or bx0 >= width_px or by0 >= hgt:
            continue
        bx0, by0 = max(bx0, 0), max(by0, 0)
        bx1, by1 = min(bx1, width_px - 1), min(by1, hgt - 1)
        ys, xs = np.mgrid[by0:by1 + 1, bx0:bx1 + 1]
        u, v = _inverse_bilinear(Q, xs + 0.5, ys + 0.5)
        ok = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
        c, r = col_row(n)
        sx = np.clip((u * SW).astype(int), 0, SW - 1) + c * SW
        sy = np.clip((v * SH).astype(int), 0, SH - 1) + r * SH
        canvas[ys[ok], xs[ok]] = tiles[sy[ok], sx[ok]]
    im = Image.fromarray(canvas)
    d = ImageDraw.Draw(im)
    for n, P in L.corners.items():
        Q = (P - [x0, y0]) / mpp
        poly = [tuple(Q[0]), tuple(Q[1]), tuple(Q[3]), tuple(Q[2])]
        d.polygon(poly, outline=colour(info[n]["region"], 0.7, 0.95))
    f = font(label_size, True)
    groups = {}
    for n, P in L.corners.items():
        row = info[n]
        key = row["region_name"] if not row["indoor"] else "Interiors"
        groups.setdefault(key, []).append(P.mean(0))
    for name, cs in groups.items():
        cxy = (np.mean(cs, 0) - [x0, y0]) / mpp
        if 0 <= cxy[0] < width_px and 0 <= cxy[1] < hgt:
            outlined(d, tuple(cxy), name, f)
    # scale bar: 1 km on the overview, 200 m on the detail
    bar_m = 1000.0 if mpp > 1.0 else 200.0
    bx, by = 40, hgt - 50
    d.rectangle([bx, by, bx + bar_m / mpp, by + 12], fill=(255, 255, 255))
    d.rectangle([bx, by, bx + bar_m / 2 / mpp, by + 12], fill=(0, 0, 0), outline=(255, 255, 255))
    outlined(d, (bx, by - 18), "0", font(20, True), anchor="lm")
    outlined(d, (bx + bar_m / 2 / mpp, by - 18), "%d m" % (bar_m / 2), font(20, True))
    outlined(d, (bx + bar_m / mpp, by - 18), "%d m" % bar_m, font(20, True))
    outlined(d, (20, 20), title + "  (%.2f m per image pixel)" % mpp, font(24, True), anchor="lm")
    return im


def render_layout(ir, L, screen_rows, summary, path, width_px=2600):
    tiles = np.asarray(Image.open(os.path.join(ir.dir, "world_tiles.png")).convert("RGB"))
    info = {row["screen"]: row for row in screen_rows}
    pts = np.concatenate([P for P in L.corners.values()])
    x0, y0 = pts.min(0) - 150
    x1, y1 = pts.max(0) + 150
    over = _panel(ir, L, info, tiles, x0, y0, x1, y1, width_px,
                  "Whole world to scale: detached sheets and packed interiors")
    d = ImageDraw.Draw(over)
    lines = ["Mainland land %.3f km2; all outdoor %.3f km2; interiors %.4f km2" % (
                 summary["area_km2"]["mainland_land"], summary["area_km2"]["outdoor_total"],
                 summary["area_km2"]["interiors"]),
             "Mainland %.0f x %.0f m: straight run E-W %.0f s, N-S %.0f s at 6 m/s" % (
                 summary["mainland"]["width_m"], summary["mainland"]["height_m"],
                 summary["mainland"]["run_ew_s"], summary["mainland"]["run_ns_s"]),
             "Gap to mainland (m): " + ", ".join("%s %.0f" % kv for kv in summary["sheet_gap_to_mainland_m"].items())]
    for i, t in enumerate(lines):
        outlined(d, (20, 56 + 28 * i), t, font(22, True), anchor="lm")
    m = np.array(summary["sheets"]["mainland"]["bbox_m"])
    det = _panel(ir, L, info, tiles, m[0] - 40, m[1] - 40, m[2] + 40, m[3] + 40, width_px,
                 "Mainland detail (screen outlines coloured by region)", 20)
    out = Image.new("RGB", (width_px, over.height + det.height + 10), (255, 255, 255))
    out.paste(over, (0, 0))
    out.paste(det, (0, over.height + 10))
    out.save(path, optimize=True)
