#!/usr/bin/env python3
"""Source-to-screen table: does every delivered art source reach the player?

    cd <project dir>            # DinkRemasterUE
    python3 -I Scripts/art_wiring_audit.py [--generated <dir with _Generated>] [--cooked <ReferencedSet.txt>]
                                           [--seen <meshes.csv>] [--out <csv>] [--summary <md>]

Read-only. Pure Python 3 standard library. One row per delivered source asset (a mesh exported as FBX/GLB, an
animation clip of a clip manifest, a flipbook/decal set of the unclaimed kit) and one row per imported art package
that no source row claims. Columns, left to right, follow the asset from the artist to the screen:

  exported     the source file exists (FBX/GLB, or the clip FBX of animation_manifest.json)
  imported     a package of the same name exists under Content/ (LFS pointers are read from the LFS store)
  bound        the package is named by a runtime manifest (Content/Dink/Data/**.json, by /Game path or bare name),
               by C++ or Config, by a world map (--generated), or reached from one of those through the package
               reference graph (a material through its mesh, a texture through its material). `via` names the root.
  cooked       the package is in the cook's ReferencedSet.txt (--cooked; the newest one under Saved/ by default)
  seen         the mesh was drawn in the whole-world visual sweep (--seen, Docs/Verification/VisualSweep_15Nov2026)

and the checks of the imported package: Nanite on masked foliage, a mesh with one LOD over the budget, a mesh without
materials or with an engine default material, a material instance pointing at a missing texture, normal maps not
TC_Normalmap / sRGB off, mask maps (ORM, roughness, AO, height, opacity) with sRGB on, colour maps with sRGB off,
a skeletal mesh on a skeleton no clip of its runtime row uses.

`flag` is the worst finding of the row; `reason` quotes the documented reason for a deliberate gap (Unclaimed
STATUS.md, animation_natural.json drop_prefixes, superseded clip candidates) so a deliberate gap is not reported as
a wiring bug (flag `deliberate`).
"""
import argparse
import collections
import csv
import glob
import json
import os
import re
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ART = os.path.join(PROJECT, "SourceAssets", "Art")
CONTENT = os.path.join(PROJECT, "Content")
LFS_MAGIC = b"version https://git-lfs"
FSTRING = re.compile(rb"([\x01-\xc8])\x00\x00\x00([\x20-\x7e]+)\x00")
GAME_PATH = re.compile(r"/Game/[A-Za-z0-9_/]+(?:\.[A-Za-z0-9_]+)?")
ASSET_NAME = re.compile(r"\b((?:SM|SK|MI|M|AN|A|T|NS|MPC|SP|PA|MF|MM|BS|ABP|DM|MID)_[A-Za-z0-9_]+)\b")
LOD_SUFFIX = re.compile(r"_LOD\d+$", re.I)
# Packages of these folders are art; everything else under Content/Dink is data, audio or generated.
ART_FOLDERS = ("Dink/Photoreal", "Dink/Kits", "Dink/Props", "Dink/Foliage", "Dink/Refinements", "Dink/Hero",
               "Dink/Creatures", "Dink/NPC", "Dink/Materials", "Dink/Textures", "Dink/Camera")
ENGINE_DEFAULTS = ("/Engine/EngineMaterials/WorldGridMaterial", "/Engine/EngineMaterials/DefaultMaterial",
                   "/Engine/BasicShapes/BasicShapeMaterial")
MASK_TEX = re.compile(r"_(ORM|ARM|R|Rough|Roughness|M|Metal|AO|H|Height|Disp|Op|Opacity|Mask|Alpha|SSS_?Mask|Wind)$", re.I)
NORMAL_TEX = re.compile(r"_(N|Normal|NRM)$", re.I)
COLOUR_TEX = re.compile(r"_(BC|D|Diffuse|Albedo|BaseColor|Color|Col|SSS|E|Emissive)$", re.I)
# Packages the C++ loads by a path it builds at run time (no literal to find).
COMPOSED = {
    "/Game/Dink/Photoreal/Characters/Mother/SK_Mother_Photoreal": "DinkArtSubsystem.cpp DinkPhotorealNpcMesh (SK_<Name>_Photoreal)",
    "/Game/Dink/Photoreal/Characters/Milder/SK_Milder_Photoreal": "DinkArtSubsystem.cpp DinkPhotorealNpcMesh (SK_<Name>_Photoreal)",
}
SEVERITY = ["ok", "not_seen", "superseded", "deliberate", "alternate", "queued", "note", "texture", "lod", "nanite", "unbound", "not_cooked",
            "default_material", "missing_texture", "not_imported"]


def rel(p, base=PROJECT):
    return os.path.relpath(p, base)


def git_common_dir():
    try:
        out = subprocess.run(["git", "-C", PROJECT, "rev-parse", "--git-common-dir"], capture_output=True, text=True,
                             check=True).stdout.strip()
        return out if os.path.isabs(out) else os.path.join(PROJECT, out)
    except (OSError, subprocess.CalledProcessError):
        return None


class Packages:
    """Every .uasset/.umap under the content roots, with its FStrings read lazily (LFS pointers via the store)."""

    def __init__(self, roots):
        self.lfs = git_common_dir()
        self.files = {}            # game path (no object) -> file
        self.by_name = collections.defaultdict(list)
        for mount, folder in roots:
            for dirpath, _dirs, files in os.walk(folder):
                for f in files:
                    if f.endswith((".uasset", ".umap")):
                        full = os.path.join(dirpath, f)
                        game = mount + rel(full, folder)[:-len(".uasset")].replace(os.sep, "/")
                        if f.endswith(".umap"):
                            game = mount + rel(full, folder)[:-len(".umap")].replace(os.sep, "/")
                        self.files[game] = full
                        self.by_name[os.path.basename(game)].append(game)
        self._strings = {}
        self.unreadable = set()

    def strings(self, game):
        if game in self._strings:
            return self._strings[game]
        data = b""
        try:
            with open(self.files[game], "rb") as h:
                data = h.read()
            if data.startswith(LFS_MAGIC):
                oid = re.search(rb"oid sha256:([0-9a-f]{64})", data)
                data = b""
                if oid and self.lfs:
                    o = oid.group(1).decode()
                    p = os.path.join(self.lfs, "lfs", "objects", o[:2], o[2:4], o)
                    if os.path.isfile(p):
                        with open(p, "rb") as h:
                            data = h.read()
                if not data:
                    self.unreadable.add(game)
        except OSError:
            self.unreadable.add(game)
        out = [m.group(2).decode() for m in FSTRING.finditer(data) if len(m.group(2)) + 1 == m.group(1)[0]]
        self._strings[game] = out
        return out

    def refs(self, game):
        out = set()
        for s in self.strings(game):
            for m in GAME_PATH.findall(s):
                p = m.split(".")[0]
                if p != game:
                    out.add(p)
            if s.startswith("/Engine/"):
                out.add(s.split(".")[0].split("'")[0])
        return out

    def tags(self, game):
        """Asset registry tags: the last value seen for each key (the tag block is at the end of the summary)."""
        s = self.strings(game)
        t = {}
        name = os.path.basename(game)
        cls = None
        for i, v in enumerate(s):
            if v == name and i + 1 < len(s) and re.match(r"^/Script/[A-Za-z0-9]+\.[A-Za-z0-9_]+$", s[i + 1]):
                cls = s[i + 1].split(".")[-1]
        for i, v in enumerate(s[:-1]):
            if re.match(r"^[A-Z][A-Za-z]+$", v):
                t[v] = s[i + 1]
        t["_class"] = cls or guess_class(name)
        return t


def guess_class(name):
    for pre, cls in (("SM_", "StaticMesh"), ("SK_", "SkeletalMesh"), ("AN_", "AnimSequence"), ("A_", "AnimSequence"),
                     ("MI_", "MaterialInstanceConstant"), ("M_", "Material"), ("T_", "Texture2D"),
                     ("NS_", "NiagaraSystem"), ("MPC_", "MaterialParameterCollection"), ("L_", "World")):
        if name.startswith(pre):
            return cls
    return "?"


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def runtime_roots(pk, generated_maps):
    """{package: [where]} named at runtime: Data JSON, C++, Config, world maps."""
    roots = collections.defaultdict(set)
    texts = []
    for f in glob.glob(os.path.join(CONTENT, "Dink", "Data", "**", "*.json"), recursive=True):
        if "/Data/Audio/" in f or "/Hardness/" in f:
            continue
        texts.append(f)
    for pat in ("Plugins/*/Source/**/*.cpp", "Plugins/*/Source/**/*.h", "Source/**/*.cpp", "Source/**/*.h",
                "Config/*.ini"):
        for f in glob.glob(os.path.join(PROJECT, pat), recursive=True):
            if "/Tests/" in f or "/Test/" in f:
                continue
            texts.append(f)
    for f in texts:
        try:
            with open(f, encoding="utf-8", errors="replace") as h:
                txt = h.read()
        except OSError:
            continue
        where = rel(f)
        for m in GAME_PATH.findall(txt):
            p = m.split(".")[0]
            if p in pk.files:
                roots[p].add(where)
            elif os.path.basename(p) in pk.by_name:     # folder + name joined in code: name is enough
                for q in pk.by_name[os.path.basename(p)]:
                    roots[q].add(where)
        for m in ASSET_NAME.findall(txt):
            for q in pk.by_name.get(m, []):
                roots[q].add(where)
    for m in generated_maps:
        roots[m].add("world map " + os.path.basename(m))
    for game, where in COMPOSED.items():
        if game in pk.files:
            roots[game].add(where)
    return roots


def reach(pk, roots):
    """Package -> first root it is reached from (breadth first over package references)."""
    via = {}
    queue = collections.deque()
    for p, where in roots.items():
        via[p] = sorted(where)[0]
        queue.append(p)
    while queue:
        p = queue.popleft()
        if p.startswith("/Engine/") or p not in pk.files:
            continue
        for q in pk.refs(p):
            if q not in via:
                via[q] = "via " + os.path.basename(p) + " (" + via[p].split(" (")[0] + ")"
                queue.append(q)
    return via


def newest_referenced_set():
    c = glob.glob(os.path.join(PROJECT, "Saved", "**", "Metadata", "ReferencedSet.txt"), recursive=True)
    return max(c, key=os.path.getmtime) if c else None


def describe_cook(path):
    """Name a cook without a local path: the private copy it came from and the file's date."""
    parts = os.path.abspath(path).split(os.sep)
    copy = parts[parts.index("Saved") + 1] if "Saved" in parts else "?"
    import time
    return "ReferencedSet.txt of the private copy `%s` (cooked %s)" % (
        copy, time.strftime("%d %b %Y %H:%M", time.localtime(os.path.getmtime(path))))


def cooked_set(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as h:
        return {l.strip().lower() for l in h if l.startswith("/")}


def seen_meshes(path):
    out = {}
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as h:
            for r in csv.DictReader(h):
                out[r["mesh"].split(".")[0]] = r
    return out


def unclaimed_status():
    """{asset name: (status, in game, note)} from the unclaimed kit's STATUS.md (and family -> same)."""
    out = {}
    p = os.path.join(ART, "PhotorealPass", "Unclaimed", "STATUS.md")
    try:
        lines = open(p, encoding="utf-8").read().splitlines()
    except OSError:
        return out
    for l in lines:
        c = [x.strip() for x in l.split("|")[1:-1]]
        if len(c) >= 8 and c[0].isdigit():
            fam = c[1].strip("`")
            info = (c[4], c[6], c[7])
            out["family:" + fam] = info
            for a in re.findall(r"`([A-Za-z0-9_]+)`", c[5]):
                out[a] = info
    return out


def unclaimed_family_of(path):
    parts = rel(path, ART).split(os.sep)
    if len(parts) > 2 and parts[0] == "PhotorealPass" and parts[1] == "Unclaimed":
        return parts[2]
    return None


def sources():
    """Delivered source assets: (name, kind, source file, stream)."""
    rows = {}
    skip_dirs = ("/ThirdParty/", "/_build/", "/Working/", "/Previews/", "/Preview/", "/History/", "/ReedLOD/")
    for f in glob.glob(os.path.join(ART, "**", "*"), recursive=True):
        low = f.lower()
        if not low.endswith((".fbx", ".glb")) or any(s.lower() in low for s in skip_dirs):
            continue
        stem = LOD_SUFFIX.sub("", os.path.splitext(os.path.basename(f))[0])
        kind = "clip" if stem.startswith(("A_", "AN_")) else "mesh"
        if kind == "clip":
            if "/Animations/" in f:
                continue                   # hero/NPC clips come from the clip manifests (names differ from files)
            stem = "AN_" + stem[2:] if stem.startswith("A_") else stem
        stream = "/".join(rel(f, ART).split(os.sep)[:2])
        key = (stem, kind)
        # the same asset exported by two streams (an older source tree and the photoreal pass): keep the newest file,
        # name both streams
        if key in rows:
            old = rows[key]
            keep = f if os.path.getmtime(f) >= os.path.getmtime(old[2]) else old[2]
            streams = " + ".join(sorted(set(old[3].split(" + ")) | {stream}))
            rows[key] = (stem, kind, keep, streams)
        else:
            rows[key] = (stem, kind, f, stream)
    for man in glob.glob(os.path.join(ART, "**", "animation_manifest.json"), recursive=True):
        m = read_json(man) or {}
        base = os.path.dirname(man)
        clips = m.get("clips") or m.get("animations") or {}
        for key, c in clips.items():
            name = c.get("asset_name") or ("AN_" + key)
            fbx = os.path.join(base, c.get("fbx", ""))
            rows[(name, "clip")] = (name, "clip", fbx if os.path.isfile(fbx) else "", "/".join(rel(man, ART).split(os.sep)[:3]))
    # Flipbooks and decal sets of the unclaimed kit: a folder with T_*_BC but no mesh source.
    for d in glob.glob(os.path.join(ART, "PhotorealPass", "Unclaimed", "*", "*")):
        if not os.path.isdir(d) or glob.glob(os.path.join(d, "*.fbx")) or glob.glob(os.path.join(d, "*.glb")):
            continue
        bcs = glob.glob(os.path.join(d, "T_*_BC.png")) + glob.glob(os.path.join(d, "T_*_Flipbook*.png"))
        if bcs:
            name = os.path.basename(d)
            rows[(name, "fx")] = (name, "decal/flipbook", bcs[0], "PhotorealPass/Unclaimed")
    return sorted(rows.values(), key=lambda r: (r[3], r[0]))


def known_rows():
    d = read_json(os.path.join(PROJECT, "Scripts", "art_wiring_known.json")) or {}
    return [(re.compile(r["match"]), re.compile(r["source"]) if r.get("source") else None, r["kind"], r["why"])
            for r in d.get("rows", [])]


def known_reason(name, src, rows):
    """-> (kind, why) of the first reviewed row matching the asset, or None."""
    for m, srx, kind, why in rows:
        if m.search(name) and (srx is None or (src and srx.search(src.replace(os.sep, "/")))):
            return kind, why
    return None


def deliberate_clip_reason(name, natural, superseded):
    key = name[3:] if name.startswith("AN_") else name
    for pre in natural.get("drop_prefixes", []):
        if key.startswith(pre):
            return "animation_natural.json drop_prefixes '%s': the motion-capture clip of the same role plays instead" % pre
    if name in superseded:
        return superseded[name]
    return ""


def cpp_literals():
    out = set()
    for f in glob.glob(os.path.join(PROJECT, "Plugins", "*", "Source", "**", "*.cpp"), recursive=True) + \
            glob.glob(os.path.join(PROJECT, "Plugins", "*", "Source", "**", "*.h"), recursive=True):
        if "/Tests/" in f:
            continue
        with open(f, encoding="utf-8", errors="replace") as h:
            out.update(re.findall(r'TEXT\("([A-Za-z0-9_]+)"\)', h.read()))
    return out


def clip_played(name, reason, literals, roots, games):
    """-> "yes (...)" / "no (...)": does the runtime ever ask for this clip?"""
    if reason:
        return "no (deliberate)"
    key = name[3:] if name.startswith("AN_") else name
    base = re.sub(r"_(Timid|Confident)$", "", key)
    if key in literals or base in literals:
        return "yes (C++ asks for '%s')" % (key if key in literals else base)
    for g in games:
        for w in roots.get(g, ()):
            if w.endswith(("creatures.json", "characters.json", "hero_actions.json")):
                return "yes (%s)" % os.path.basename(w)
    return "no (no runtime caller found)"


def coverage_index():
    """{id: text} of the Fable queue rows and packets, to cite instead of re-reporting."""
    out = {}
    q = os.path.join(os.path.dirname(PROJECT), "doc", "remaster")
    for f in glob.glob(os.path.join(q, "fable_packets", "*.md")):
        out[os.path.splitext(os.path.basename(f))[0]] = open(f, encoding="utf-8").read()
    try:
        for l in open(os.path.join(q, "FABLE_ART_QUEUE.md"), encoding="utf-8"):
            m = re.match(r"\| *([A-Z]+-[A-Z0-9]+) *\|", l)
            if m:
                out[m.group(1)] = out.get(m.group(1), "") + l
    except OSError:
        pass
    return out


def covered_by(name, index):
    ids = sorted(k for k, t in index.items() if re.search(r"\b%s\b" % re.escape(name), t) and re.match(r"^[A-Z]+-", k))
    return " ".join(ids)


def check_package(pk, game, tags, budget_tris=5000):
    """-> list of (flag, detail)."""
    out = []
    cls = tags.get("_class")
    if re.search(r"_(PhysicsAsset|Skeleton|PhysAsset)$", game) or cls in ("PhysicsAsset", "Skeleton"):
        return out
    refs = pk.refs(game)
    if cls in ("StaticMesh", "SkeletalMesh"):
        mats = [r for r in refs if os.path.basename(r).startswith(("MI_", "M_", "MID_")) or r.startswith(ENGINE_DEFAULTS)]
        if any(r.startswith(ENGINE_DEFAULTS) for r in refs):
            out.append(("default_material", "references an engine default material"))
        elif not mats:
            out.append(("default_material", "no material referenced (draws the default material)"))
        for m in mats:
            if m.startswith("/Game/") and m not in pk.files:
                out.append(("missing_texture", "material %s missing" % m))
        try:
            tris = int(tags.get("Triangles", "0"))
            lods = int(tags.get("LODs", "1"))
        except ValueError:
            tris, lods = 0, 1
        nanite = tags.get("NaniteEnabled") == "True"
        if cls == "StaticMesh" and lods <= 1 and not nanite and tris > budget_tris:
            out.append(("lod", "one LOD, %d triangles, Nanite off" % tris))
        folded = game.lower()
        if nanite and re.search(r"/vegetation/|/foliage/|grass|reed|leaf|(^|[/_])hair([_/]|$)|/scatter/", folded.replace("chair", "")):
            out.append(("nanite", "Nanite on a masked foliage/hair mesh"))
    if cls == "MaterialInstanceConstant":
        for r in refs:
            if os.path.basename(r).startswith("T_") and r.startswith("/Game/") and r not in pk.files:
                out.append(("missing_texture", "texture %s missing" % r))
    if cls == "Texture2D":
        n = os.path.basename(game)
        srgb = tags.get("SRGB")
        comp = tags.get("CompressionSettings", "")
        if NORMAL_TEX.search(n) and (comp != "TC_Normalmap" or srgb == "True"):
            out.append(("texture", "normal map with %s, sRGB %s" % (comp, srgb)))
        elif (MASK_TEX.search(n) or (n.endswith("_E") and comp == "TC_Masks")) and srgb == "True":
            out.append(("texture", "mask map with sRGB on (%s)" % comp))
        elif COLOUR_TEX.search(n) and srgb == "False" and comp not in ("TC_HDR", "TC_HDR_Compressed", "TC_Masks"):
            out.append(("texture", "colour map with sRGB off (%s)" % comp))
    return out


def card_table(audit_path, coverage_path, families_path, unbound_by_class):
    """Sprite cards the scene audit saw drawn (above ground), per sprite class, with what could replace them.

    -> rows: class, cards, screens, final_origin_cards (cards on an origin art_coverage counts final: a wiring bug),
    family_row (families.json binds the class), mesh_available (an imported or delivered mesh names the class)."""
    classes = {}
    try:
        with open(os.path.join(os.path.dirname(PROJECT), "tools", "data", "sprite_classes.csv"), encoding="utf-8") as h:
            for r in csv.DictReader(h):
                classes[(r["seq"], r["frame"])] = r["class_id"]
    except OSError:
        return []
    state = {}
    if coverage_path and os.path.isfile(coverage_path):
        with open(coverage_path, encoding="utf-8") as h:
            state = {r["origin_id"]: r["state"] for r in csv.DictReader(h)}
    fam = {f.get("family") for f in (read_json(families_path) or {}).get("families", [])}
    cards = collections.defaultdict(lambda: {"cards": 0, "screens": set(), "final": [], "buried": 0})
    with open(audit_path, encoding="utf-8") as h:
        for line in h:
            d = json.loads(line)
            for p in d.get("prims", []):
                m = re.search(r"MI_Sprite_(\d+)_(\d+)", json.dumps(p.get("mats", [])))
                cn = p.get("cn", "")
                if not m or not (cn == "Card" or cn.startswith("Decor")):
                    continue
                cls = classes.get((m.group(1), str(int(m.group(2)))), "seq %s/%s" % m.groups())
                c = cards[cls]
                if p.get("max", [0, 0, 0])[2] < -500:      # parked under the ground: not drawn
                    c["buried"] += 1
                    continue
                c["cards"] += 1
                c["screens"].add(d["screen"])
                if p.get("o") and state.get(p["o"]) == "final":
                    c["final"].append(p["o"])
    out = []
    for cls, c in sorted(cards.items(), key=lambda x: -x[1]["cards"]):
        if not c["cards"]:
            continue
        out.append({"class": cls, "cards": c["cards"], "screens": " ".join(str(x) for x in sorted(c["screens"])),
                    "final_origin_cards": " ".join(c["final"]), "family_row": "yes" if cls in fam else "",
                    "mesh_available": " ".join(sorted(unbound_by_class.get(cls, [])))})
    return out


def gap_flag(reason, cov):
    """The flag of a source that does not reach the player, from the reason written for it."""
    for kind in ("queued", "alternate", "superseded", "deliberate"):
        if reason.startswith(kind + ":"):
            return kind
    if reason.startswith("queued") or cov:
        return "queued"
    return "deliberate" if reason else None


def worst(flags):
    return max(flags, key=SEVERITY.index) if flags else "ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--generated", help="a Content/Dink/_Generated folder (world maps place the kits)")
    ap.add_argument("--cooked", help="ReferencedSet.txt of a cook (default: newest under Saved/)")
    ap.add_argument("--seen", default=os.path.join(PROJECT, "Docs", "Verification", "VisualSweep_15Nov2026", "meshes.csv"))
    ap.add_argument("--out", default=os.path.join(PROJECT, "Saved", "ArtWiring", "art_wiring.csv"))
    ap.add_argument("--summary", help="write a Markdown summary here too")
    ap.add_argument("--scene-audit", help="audit.jsonl of a dink.SceneAudit sweep: adds the drawn-card table")
    ap.add_argument("--coverage-csv", help="art_coverage.py output (origin states) for the drawn-card table")
    ap.add_argument("--cards-out", help="CSV for the drawn-card table (default: <out> with _cards)")
    a = ap.parse_args()

    roots_dirs = [("/Game/", CONTENT)]
    pk = Packages(roots_dirs)
    # the project's own _Generated is git-ignored and often stale; take maps from --generated when given
    gen_maps = []
    if a.generated:
        gpk = Packages([("/Game/Dink/_Generated/", a.generated)])
        for g, f in gpk.files.items():
            pk.files[g] = f
            pk.by_name[os.path.basename(g)].append(g)
        gen_maps = [g for g, f in gpk.files.items() if f.endswith(".umap")]
    else:
        gen_maps = [g for g, f in pk.files.items() if f.endswith(".umap")]

    roots = runtime_roots(pk, gen_maps)
    via = reach(pk, roots)
    cooked_path = a.cooked or newest_referenced_set()
    cooked = cooked_set(cooked_path)
    seen = seen_meshes(a.seen)
    status = unclaimed_status()
    natural = read_json(os.path.join(CONTENT, "Dink", "Data", "Art", "animation_natural.json")) or {}
    superseded = {"AN_Dink_Fist": "superseded candidate (Characters/Animations/Unarmed, status 'candidate'): the "
                                  "Pass1 Fist_Jab/Cross/Swing clips of animation_pass.json play the punch"}

    known = known_rows()
    literals = cpp_literals()
    index = coverage_index()
    rows = []
    claimed = set()
    for name, kind, src, stream in sources():
        games = [g for g in pk.by_name.get(name, []) if "/_Generated/" not in g]
        if kind == "mesh" and not games:
            # an FBX of the same object exported again under an alternate name (_PR, _Game) is not a separate asset
            games = [g for g in pk.by_name.get(name + "_PR", [])]
        flags, details = [], []
        reason = ""
        fam = unclaimed_family_of(src) if src else None
        st = status.get(name) or (status.get("family:" + fam) if fam else None)
        if kind == "clip":
            reason = deliberate_clip_reason(name, natural, superseded)
        if st and ("not imported" in st[1] or "not bound" in st[1]):
            reason = (st[1] + "; " + st[2])[:300]
        cov0 = covered_by(name, index)
        if not reason:
            k = known_reason(name, src, known)
            if k:
                reason = "%s: %s" % k
                if k[0] == "queued":
                    cov0 = cov0 or "see reason"
        if not games:
            flags.append(gap_flag(reason, cov0) or "not_imported")
        bound_where, cooked_s, seen_s = "", "", ""
        for g in games:
            claimed.add(g)
            t = pk.tags(g)
            for f, d in check_package(pk, g, t):
                flags.append(f)
                details.append(d)
            for r in pk.refs(g):
                if r in pk.files:
                    claimed.add(r)
                    rt = pk.tags(r)
                    for f, d in check_package(pk, r, rt):
                        flags.append(f)
                        details.append(os.path.basename(r) + ": " + d)
                    for rr in pk.refs(r):
                        if rr in pk.files and os.path.basename(rr).startswith("T_"):
                            claimed.add(rr)
                            for f, d in check_package(pk, rr, pk.tags(rr)):
                                flags.append(f)
                                details.append(os.path.basename(rr) + ": " + d)
            if g in via:
                bound_where = via[g]
            if cooked is not None:
                cooked_s = "yes" if g.lower() in cooked else "no"
            if g in seen:
                seen_s = "yes (%s uses, screens %s)" % (seen[g]["uses"], " ".join(seen[g]["screens"].split()[:6]))
        if games and not bound_where:
            flags.append(gap_flag(reason, cov0) or "unbound")
        if games and bound_where and cooked_s == "no":
            flags.append("not_cooked")
        if games and bound_where and kind == "mesh" and not seen_s and seen and "/Hero/" not in games[0]:
            flags.append("not_seen")
        played = ""
        if kind == "clip":
            played = clip_played(name, reason, literals, roots, games) if games else ""
            if games and bound_where and played.startswith("no (no runtime"):
                flags.append("unbound")
                details.append("bound by a manifest but no runtime caller plays it")
        cov = covered_by(name, index)
        if cov and not reason and any(f in ("not_imported", "unbound") for f in flags):
            reason = "queued: " + cov
        rows.append({
            "asset": name, "kind": kind, "stream": stream, "source": rel(src) if src else "",
            "exported": "yes" if src and os.path.isfile(src) else "no",
            "imported": " ".join(games), "bound": bound_where, "cooked": cooked_s, "seen": seen_s or played,
            "covered_by": cov,
            "flag": worst(flags), "detail": "; ".join(dict.fromkeys(details)), "reason": reason,
        })

    # Imported art packages no source claims (meshes and clips only: materials and textures follow their mesh)
    for g, f in sorted(pk.files.items()):
        if g in claimed or not g.startswith(tuple("/Game/" + x for x in ART_FOLDERS)):
            continue
        n = os.path.basename(g)
        if not n.startswith(("SM_", "SK_", "AN_")):
            continue
        t = pk.tags(g)
        flags, details = [], []
        for fl, d in check_package(pk, g, t):
            flags.append(fl)
            details.append(d)
        bound_where = via.get(g, "")
        cooked_s = "" if cooked is None else ("yes" if g.lower() in cooked else "no")
        seen_s = "yes" if g in seen else ""
        if not bound_where:
            flags.append("unbound")
        elif cooked_s == "no":
            flags.append("not_cooked")
        rows.append({"asset": n, "kind": "package only", "stream": "/".join(g.split("/")[2:4]), "source": "",
                     "exported": "?", "imported": g, "bound": bound_where, "cooked": cooked_s, "seen": seen_s,
                     "covered_by": covered_by(n, index),
                     "flag": worst(flags), "detail": "; ".join(dict.fromkeys(details)), "reason": ""})

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cols = ["asset", "kind", "stream", "source", "exported", "imported", "bound", "cooked", "seen", "flag", "detail",
            "reason", "covered_by"]
    with open(a.out, "w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    card_rows = []
    if a.scene_audit:
        # which sprite classes an existing but unbound / unimported mesh was made for (source manifests' families)
        unbound_by_class = collections.defaultdict(set)
        names = {r["asset"] for r in rows if r["flag"] in ("unbound", "not_imported", "queued", "deliberate")}
        for man in glob.glob(os.path.join(ART, "**", "manifest.json"), recursive=True):
            m = read_json(man) or {}
            for mod in (m.get("modules") or m.get("assets") or []):
                if not isinstance(mod, dict) or mod.get("name") not in names:
                    continue
                for f in mod.get("families") or []:
                    for tok in re.findall(r"[a-z][a-z0-9_]+", str(f)):
                        unbound_by_class[tok].add(mod["name"])
        for key, (st, ingame, _note) in unclaimed_status().items():
            if key.startswith("family:") and "bound" not in ingame.replace("not bound", ""):
                for asset, info in unclaimed_status().items():
                    if not asset.startswith("family:") and info == (st, ingame, _note):
                        unbound_by_class[key[7:]].add(asset)
        card_rows = card_table(a.scene_audit, a.coverage_csv,
                               os.path.join(CONTENT, "Dink", "Data", "Art", "families.json"), unbound_by_class)
        cards_out = a.cards_out or os.path.splitext(a.out)[0] + "_cards.csv"
        with open(cards_out, "w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, lineterminator="\n", fieldnames=["class", "cards", "screens", "final_origin_cards", "family_row", "mesh_available"])
            w.writeheader()
            w.writerows(card_rows)

    by_flag = collections.Counter(r["flag"] for r in rows)
    by_kind = collections.Counter((r["kind"], r["flag"]) for r in rows)
    lines = ["# Art wiring audit", "",
             "cooked set: %s" % (describe_cook(cooked_path) if cooked_path else "none (cooked column empty)"),
             "rows: %d; unreadable packages (LFS object missing): %d" % (len(rows), len(pk.unreadable)), "",
             "| flag | rows |", "|---|---:|"]
    for f in SEVERITY[::-1]:
        if by_flag.get(f):
            lines.append("| %s | %d |" % (f, by_flag[f]))
    lines += ["", "| kind | flag | rows |", "|---|---|---:|"]
    for (k, f), n in sorted(by_kind.items()):
        lines.append("| %s | %s | %d |" % (k, f, n))
    if card_rows:
        lines += ["", "Drawn sprite cards (scene audit): %d cards of %d classes; on an origin counted final: %d; "
                  "classes with a delivered mesh made for them: %d" % (
                      sum(r["cards"] for r in card_rows), len(card_rows),
                      sum(len(r["final_origin_cards"].split()) for r in card_rows),
                      sum(1 for r in card_rows if r["mesh_available"]))]
    txt = "\n".join(lines) + "\n"
    print(txt)
    print("wrote", rel(a.out) if a.out.startswith(PROJECT) else a.out)
    if a.summary:
        with open(a.summary, "w", encoding="utf-8") as h:
            h.write(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
