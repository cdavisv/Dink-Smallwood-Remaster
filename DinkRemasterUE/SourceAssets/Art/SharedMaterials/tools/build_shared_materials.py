#!/usr/bin/env python3
"""Build the shared tileable PBR material library (numpy + Pillow only).

  python3 SourceAssets/Art/SharedMaterials/tools/build_shared_materials.py            # everything
  python3 .../build_shared_materials.py --only CobbleStreet,BrickWall                 # subset
  python3 .../build_shared_materials.py --check                                       # re-audit PNGs on disk

Outputs (relative to SharedMaterials/): Textures/2048 and Textures/1024 (BC/N/ORM/H PNG),
Previews/, contact_sheet.png, tiling_check.png, manifest.json, albedo_report.json,
ledger_rows_proposed.csv. Deterministic: every material has a fixed seed (sm_materials.REGISTRY).
"""
import argparse, csv, hashlib, json, os, sys, time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)  # .../SharedMaterials
UE_ROOT = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))  # DinkRemasterUE

from sm_lib import Ctx, downsample_set, srgb_to_lin, F32
import sm_materials as M
import sm_preview as P

LUMA = np.array([0.2126, 0.7152, 0.0722], F32)

INTENT = {
    "CobbleStreet": ("Terris, Windemere, Joppa Isle and Goodheart Castle street paving", "path, gravel, stone_floor (outdoor)"),
    "DirtRoadRuts": ("Cart roads between towns: Terris wilds, Windemere wilds, KernSin wilds, South coast road", "path, dirt"),
    "ForestFloor": ("Murkwood and the cult woods, forest_canopy under-layer, Terris wilds", "forest_canopy, grass_rocky (shade)"),
    "WetSand": ("South coast, Joppa Isle shoreline, West Seas beaches, Koka Isle shore", "sand"),
    "BeachPebbles": ("Shingle beaches and sand/gravel transitions on the South coast, Koka Isle and Joppa", "sand, gravel"),
    "MossyCaveRock": ("Cave walls and floors: Hellfire cave, Joppa tunnel, Edge of the World caves", "cave_wall, cave_floor, rock_mass"),
    "DungeonMasonry": ("Snow castle, Goodheart Castle hall, Goblin Sanctuary and other dungeon wall faces", "structure_facade (stone), cave_wall (built)"),
    "DungeonFlagstone": ("Castle, dungeon and cellar floors", "stone_floor"),
    "DarklandsSoil": ("Darklands wasteland ground", "wasteland"),
    "SnowFresh": ("Snow castle isle open ground", "snow"),
    "SnowTrampled": ("Snow castle isle paths, doorways and gate approaches", "snow, path"),
    "CliffRock": ("Cliff faces everywhere: mainland cliffs, Edge of the World plateau, East Wilds", "cliff_face, rock_mass"),
    "TimberPlanks": ("Weathered plank cladding and floors for Terris, Windemere and Joppa buildings, docks, bar interior", "structure_facade (timber), wood_floor"),
    "RoofSlate": ("Slate roofs: Goodheart Castle, Terris town hall and well-off houses", "structure_facade (roof)"),
    "RoofShingles": ("Wooden shingle roofs: Windemere and Joppa houses, Terris outbuildings", "structure_facade (roof)"),
    "BrickWall": ("Terris and Windemere brick town buildings and chimneys", "structure_facade (brick)"),
}


def save_rgba(path, rgb8):
    h, w = rgb8.shape[:2]
    a = np.dstack([rgb8, np.full((h, w), 255, np.uint8)])
    Image.fromarray(a, "RGBA").save(path, optimize=False, compress_level=6)


def pack_set(m, hmin, hmax):
    bc = np.clip(m["alb"] + 0.5, 0, 255).astype(np.uint8)
    nrm = np.clip((m["normal"] * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)
    orm = np.stack([np.clip(m["ao"] * 255 + 0.5, 0, 255), np.clip(m["rough"] * 255 + 0.5, 0, 255),
                    np.zeros_like(m["ao"])], -1).astype(np.uint8)
    hh = np.clip((m["height"] - hmin) / (hmax - hmin) * 65535 + 0.5, 0, 65535).astype(np.uint16)
    return bc, nrm, orm, hh


def write_set(name, size, m, hmin, hmax):
    d = os.path.join(ROOT, "Textures", str(size))
    os.makedirs(d, exist_ok=True)
    bc, nrm, orm, hh = pack_set(m, hmin, hmax)
    files = {}
    for suf, arr in (("BC", bc), ("N", nrm), ("ORM", orm)):
        p = os.path.join(d, "T_Shared_%s_%s.png" % (name, suf))
        save_rgba(p, arr)
        files[suf] = p
    p = os.path.join(d, "T_Shared_%s_H.png" % name)
    Image.fromarray(hh).save(p, compress_level=6)  # 16-bit greyscale
    files["H"] = p
    return files, bc, nrm, orm


def seam_metric(img8):
    """mean |wrap-edge difference| / mean |interior neighbour difference| (1.0 = seamless)."""
    a = img8.astype(np.float32)
    out = []
    for ax in (0, 1):
        wrap = np.abs(np.take(a, 0, ax) - np.take(a, -1, ax)).mean()
        inner = np.abs(np.diff(a, axis=ax)).mean()
        out.append(float(wrap / max(inner, 1e-6)))
    return out


def albedo_stats(bc):
    a = bc[..., :3].astype(np.float32)
    luma = a @ LUMA
    mx = a.max(-1)
    return dict(luma_min=float(luma.min()), luma_p01=float(np.percentile(luma, 0.1)), luma_p1=float(np.percentile(luma, 1)),
                luma_mean=float(luma.mean()), luma_p99=float(np.percentile(luma, 99)), luma_p999=float(np.percentile(luma, 99.9)),
                luma_max=float(luma.max()), channel_max=float(mx.max()), channel_min=float(a.min()),
                pct_luma_below_30=float((luma < 30).mean() * 100), pct_channel_above_240=float((mx > 240).mean() * 100),
                pct_luma_at_floor=float((luma < 34).mean() * 100),
                mean_rgb=[float(x) for x in a.mean((0, 1))])


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_set(name, size):
    d = os.path.join(ROOT, "Textures", str(size))
    bc = np.asarray(Image.open(os.path.join(d, "T_Shared_%s_BC.png" % name)))[..., :3]
    nr = np.asarray(Image.open(os.path.join(d, "T_Shared_%s_N.png" % name)))[..., :3].astype(F32) / 255 * 2 - 1
    orm = np.asarray(Image.open(os.path.join(d, "T_Shared_%s_ORM.png" % name)))[..., :3].astype(F32) / 255
    nr /= np.maximum(np.linalg.norm(nr, axis=-1, keepdims=True), 1e-4)
    return dict(alb=bc.astype(F32), normal=nr, ao=orm[..., 0], rough=orm[..., 1])


def contact_sheets(names):
    cell = 480
    cols = 4
    rows = (len(names) + cols - 1) // cols
    lit = Image.new("RGB", (cols * cell, rows * cell))
    til = Image.new("RGB", (cols * cell, rows * cell))
    for i, n in enumerate(names):
        m = load_set(n, 1024)
        a = P.render_plane(m, 1)
        r = np.roll(np.roll(a, 512, 0), 512, 1)  # seams to the centre
        for im, arr in ((lit, a), (til, r)):
            t = Image.fromarray(arr).resize((cell, cell), Image.LANCZOS)
            im.paste(Image.fromarray(P.label(np.asarray(t), "%s  (%.0f m tile)" % (n, M.REGISTRY[n][1]))), ((i % cols) * cell, (i // cols) * cell))
    lit.save(os.path.join(ROOT, "contact_sheet.png"))
    til.save(os.path.join(ROOT, "tiling_check.png"))
    # 2x2 repeat of albedo only, one big sheet, for the repetition check
    cell2 = 480
    rep = Image.new("RGB", (cols * cell2, rows * cell2))
    for i, n in enumerate(names):
        bc = np.asarray(Image.open(os.path.join(ROOT, "Textures", "1024", "T_Shared_%s_BC.png" % n)))[..., :3]
        t = np.tile(bc, (2, 2, 1))
        t = Image.fromarray(t).resize((cell2, cell2), Image.LANCZOS)
        rep.paste(Image.fromarray(P.label(np.asarray(t), "%s 2x2 albedo" % n)), ((i % cols) * cell2, (i // cols) * cell2))
    rep.save(os.path.join(ROOT, "repeat_check_2x2.png"))


def build(only, previews=True):
    os.makedirs(os.path.join(ROOT, "Previews"), exist_ok=True)
    names = list(M.REGISTRY.keys())
    todo = [n for n in names if (not only or n in only)]
    mp = os.path.join(ROOT, "manifest.json")
    manifest = json.load(open(mp)) if os.path.exists(mp) else {"materials": {}}
    for n in todo:
        fn, T, seed = M.REGISTRY[n]
        t0 = time.time()
        c = Ctx(2048, T, seed)
        m = fn(c)
        hmin, hmax = float(m["height"].min()), float(m["height"].max())
        files2k, bc2, nrm2, orm2 = write_set(n, 2048, m, hmin, hmax)
        m1 = downsample_set(m, c.px)
        files1k, bc1, nrm1, orm1 = write_set(n, 1024, m1, hmin, hmax)
        if previews:
            img = P.preview_sheet(m1, "%s  -  %.0f m tile, 1024 variant" % (n, T))
            Image.fromarray(img).save(os.path.join(ROOT, "Previews", "%s_preview.png" % n))
        st2, st1 = albedo_stats(bc2), albedo_stats(bc1)
        region, classes = INTENT[n]
        rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
        manifest["materials"][n] = dict(
            generator="sm_materials.%s" % fn.__name__, seed=seed, tile_size_m=T,
            texel_density=dict(px_per_m_2048=round(2048 / T, 1), mm_per_px_2048=round(T / 2.048, 3),
                               px_per_m_1024=round(1024 / T, 1), mm_per_px_1024=round(T / 1.024, 3)),
            files={str(s): {k: rel(v) for k, v in f.items()} for s, f in ((2048, files2k), (1024, files1k))},
            colour_space=dict(BC="sRGB (RGB 8-bit, opaque alpha)", N="linear, OpenGL tangent space (+Y up): flip green in Unreal; normal compression",
                              ORM="linear mask: R=AO, G=roughness, B=metallic (0); 8-bit, opaque alpha",
                              H="linear 16-bit greyscale, 0..65535 spans height_range_m"),
            height_range_m=[round(hmin, 5), round(hmax, 5)], relief_m=round(hmax - hmin, 5),
            normal_gain_authored=m["normal_gain"],
            intended_region=region, tile_classes=classes,
            albedo_2048=st2, albedo_1024=st1,
            seam_ratio_2048_xy=seam_metric(bc2), seam_ratio_1024_xy=seam_metric(bc1),
            roughness_range=[float(orm2[..., 1].min()) / 255, float(orm2[..., 1].max()) / 255],
            sha256={str(s): {k: sha(v) for k, v in f.items()} for s, f in ((2048, files2k), (1024, files1k))},
        )
        print("%-16s %5.1fs  luma %.0f..%.0f (mean %.0f)  maxch %.0f  floor%% %.2f  seam %s" % (
            n, time.time() - t0, st2["luma_min"], st2["luma_max"], st2["luma_mean"], st2["channel_max"], st2["pct_luma_at_floor"],
            ["%.2f" % x for x in manifest["materials"][n]["seam_ratio_2048_xy"]]), flush=True)
        del m, m1
    manifest["materials"] = {k: manifest["materials"][k] for k in names if k in manifest["materials"]}
    manifest["library"] = dict(
        name="Dink remaster shared PBR material library", version="shared-materials-v1", generated_on="2026-11-08",
        conventions=dict(maps=["BC", "N", "ORM", "H"], sizes=[2048, 1024], normal="OpenGL (matches Stonebrook kit); Unreal: flip green, reduced XY strength ~0.35 as in the existing bridge",
                         orm="R=AO G=Roughness B=Metallic (linear), as Stonebrook kit", licence="Original project asset; no third-party source material",
                         tool="python3 + numpy + Pillow; no downloaded or generated-by-model images"))
    json.dump(manifest, open(mp, "w"), indent=1)
    return names


def write_reports(names):
    mp = os.path.join(ROOT, "manifest.json")
    man = json.load(open(mp))
    rep = {}
    for n in names:
        mm = man["materials"][n]
        rep[n] = dict(a2048=mm["albedo_2048"], a1024=mm["albedo_1024"], seam2048=mm["seam_ratio_2048_xy"], seam1024=mm["seam_ratio_1024_xy"])
    json.dump(rep, open(os.path.join(ROOT, "albedo_report.json"), "w"), indent=1)
    # proposed ledger rows (exact columns of SourceAssets/asset_ledger.csv)
    cols = ["asset_path", "derived_path", "kind", "replaces", "source", "tool_model", "prompt", "parameters", "generation_id", "flow_id",
            "generated_on", "credits", "licence", "sha256", "duration_s", "status", "notes"]
    led = os.path.join(UE_ROOT, "SourceAssets", "asset_ledger.csv")
    with open(led, newline="") as f:
        assert next(csv.reader(f)) == cols, "ledger columns changed"
    rows = []
    for n in names:
        mm = man["materials"][n]
        for size in ("2048", "1024"):
            for k in ("BC", "N", "ORM", "H"):
                rel = "SourceAssets/Art/SharedMaterials/" + mm["files"][size][k]
                derived = "Content/Dink/Textures/Shared/T_Shared_%s_%s.uasset" % (n, k) if size == "2048" else ""
                note = ("Shared material library candidate; rebuild with SourceAssets/Art/SharedMaterials/tools/build_shared_materials.py --only %s; "
                        "%s; human art approval pending." % (n, "2048 px master" if size == "2048" else
                                                              "1024 px variant (2x box-filtered from the 2048 master, normal rebuilt from height); not imported by default"))
                rows.append([rel, derived, "texture", "Placeholder terrain/building colours for: " + mm["intended_region"],
                             "Original project-authored procedural texture synthesis",
                             "Python 3 numpy + Pillow (FFT noise, wrapped Voronoi, ragged-row layouts); no generative model or external input assets",
                             "Tileable photoreal PBR %s, %s" % (n, mm["intended_region"]),
                             "seed=%d; tile=%.1f m; %s px; map=%s; %s" % (mm["seed"], mm["tile_size_m"], size, k,
                                                                           {"BC": "sRGB", "N": "OpenGL tangent normal", "ORM": "linear R=AO G=Rough B=Metal", "H": "16-bit linear height"}[k]),
                             "shared-materials-v1", "", "2026-11-08", "0", "Original project asset; no third-party source material",
                             mm["sha256"][size][k], "", "candidate", note])
    with open(os.path.join(ROOT, "ledger_rows_proposed.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return rep


def check(names):
    """Audit PNGs on disk."""
    ok = True
    print("%-16s %5s | luma min p.1 mean p99.9 max | chan max | %%<30 %%>240 | seam x,y" % ("material", "size"))
    for n in names:
        for size in (2048, 1024):
            bc = np.asarray(Image.open(os.path.join(ROOT, "Textures", str(size), "T_Shared_%s_BC.png" % n)))
            st = albedo_stats(bc[..., :3])
            sm = seam_metric(bc[..., :3])
            bad = st["luma_min"] < 30 or st["channel_max"] > 240
            ok &= not bad
            print("%-16s %5d | %5.1f %5.1f %5.1f %5.1f %5.1f | %5.0f | %.3f %.3f | %.2f %.2f %s" % (
                n, size, st["luma_min"], st["luma_p01"], st["luma_mean"], st["luma_p999"], st["luma_max"], st["channel_max"],
                st["pct_luma_below_30"], st["pct_channel_above_240"], sm[0], sm[1], "FAIL" if bad else "ok"))
    print("ALBEDO CHECK:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-previews", action="store_true")
    a = ap.parse_args()
    only = [s for s in a.only.split(",") if s]
    names = list(M.REGISTRY.keys())
    if a.check:
        sys.exit(0 if check(names) else 1)
    build(only, not a.no_previews)
    write_reports(names)
    contact_sheets(names)
    check(names)
