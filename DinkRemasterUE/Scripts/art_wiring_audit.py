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
LOD_DIR = re.compile(r"/(LODs?|LOD_V\d+|FBX|Export(_V\d+|V\d+)?)$", re.I)   # an export's own LOD/FBX folder is one delivery
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
SEVERITY = ["ok", "replaced", "unverified", "not_seen", "superseded", "deliberate", "documented", "alternate", "queued", "note", "bug", "texture", "lod", "nanite", "unbound", "not_cooked",
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


# JSON keys whose string values are prose, labels or identifiers, never a binding (review of 15 Nov 2026)
FREE_TEXT_KEY = re.compile(r"note|about|comment|why|desc|reason|weak|readme|help|todo|history|schema|generated_by|^name$|^id$|^label$",
                           re.I)
# Bare asset names in these manifests are resolved by the runtime under one folder (DinkEnvironmentSubsystem.cpp
# builds "/Game/Dink/Photoreal/TownExteriors/" + mesh); elsewhere a bare name binds only when it is unique.
BARE_PREFIX = {"town_houses.json": "/Game/Dink/Photoreal/TownExteriors/"}
CPP_LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
WHOLE_NAME = re.compile(r"^" + ASSET_NAME.pattern.replace(r"\b", "") + r"$")


def runtime_module_dirs():
    """Source folders of the modules a packaged game loads (.uplugin/.uproject module type Runtime only):
    Editor modules (DinkImport, DinkParity) and DeveloperTool modules (DinkProbe) draw nothing for a player."""
    dirs = []
    for desc in sorted(glob.glob(os.path.join(PROJECT, "Plugins", "*", "*.uplugin")) + [os.path.join(PROJECT, "DinkRemaster.uproject")]):
        d = read_json(desc) or {}
        for m in d.get("Modules", []):
            if m.get("Type") == "Runtime":
                dirs.append(os.path.join(os.path.dirname(desc), "Source", m["Name"]))
    return dirs


def bind_string(text, where, pk, roots, bare_prefix=None):
    """A string value binds the package its /Game path names (exactly), or, when the whole string is an asset name,
    the package of that name (under bare_prefix when the manifest has one; only a unique name otherwise)."""
    for m in GAME_PATH.findall(text):
        p = m.split(".")[0]
        if p in pk.files:
            roots[p].add(where)
    if WHOLE_NAME.match(text):
        cands = sorted(pk.by_name.get(text, []))
        if bare_prefix:
            cands = [c for c in cands if c.startswith(bare_prefix)]
        if len(cands) == 1:
            roots[cands[0]].add(where)


def walk_json(value, where, pk, roots, bare_prefix=None, key=""):
    if isinstance(value, dict):
        for k, v in value.items():                      # keys never bind (mesh_swaps sources, slot names)
            if k == "assets":                           # the asset list a manifest validates (sizes, skeletons), not a placement
                continue
            walk_json(v, where, pk, roots, bare_prefix, k)
    elif isinstance(value, list):
        for v in value:
            walk_json(v, where, pk, roots, bare_prefix, key)
    elif isinstance(value, str) and not FREE_TEXT_KEY.search(key):
        bind_string(value, where, pk, roots, bare_prefix)


def swapped_sources():
    """{package: [targets]} that environment.json mesh_swaps replaces at runtime, and {package: actor tag} of
    mesh_swap_only_tag (the swap then runs only on owners with that tag, e.g. DinkArtScreen_439)."""
    env = read_json(os.path.join(CONTENT, "Dink", "Data", "Environment", "environment.json")) or {}
    swaps = {k.split(".")[0]: v for k, v in (env.get("mesh_swaps") or {}).items()}
    only = {k.split(".")[0]: v for k, v in (env.get("mesh_swap_only_tag") or {}).items()}
    return swaps, only


def swap_status(games, roots, swapped, only_tag, authored, context):
    """How mesh_swaps treats a swap source, per root (DinkArtSubsystem DinkApplyEnvironmentMeshSwap runs only for
    elements of authored, non-context dink-art manifests, and with mesh_swap_only_tag only on owners tagged
    DinkArtScreen_<screen>). -> (swapped roots, roots unswapped by a written only-tag decision, roots unswapped by
    the wiring). camera_*.json name meshes for the fade rules only and place nothing."""
    done, decided, missed = [], [], []
    for g in games:
        if g not in swapped:
            continue
        tag = only_tag.get(g)
        for w in sorted(roots.get(g, set())):
            if os.path.basename(w).startswith("camera_"):
                continue
            if w in authored and (tag is None or tag == "DinkArtScreen_%s" % authored[w]):
                done.append(w)
            elif tag is not None and (w in authored or w in context):
                decided.append(w)
            else:
                missed.append(w)
    return sorted(set(done)), sorted(set(decided)), sorted(set(missed))


def runtime_roots(pk, generated_maps):
    """{package: {where}} named at runtime: Data JSON values, string literals of Runtime C++ modules, Config, world
    maps, and the composed paths of COMPOSED."""
    roots = collections.defaultdict(set)
    literals = []
    for d in runtime_module_dirs():
        for f in sorted(glob.glob(os.path.join(d, "**", "*.cpp"), recursive=True) + glob.glob(os.path.join(d, "**", "*.h"), recursive=True)):
            if "/Tests/" not in f.replace(os.sep, "/"):
                with open(f, encoding="utf-8", errors="replace") as h:
                    literals += CPP_LITERAL.findall(h.read())
    named = "\n".join(literals)
    for f in sorted(glob.glob(os.path.join(CONTENT, "Dink", "Data", "**", "*.json"), recursive=True)):
        if "/Data/Audio/" in f.replace(os.sep, "/") or "/Hardness/" in f.replace(os.sep, "/"):
            continue
        data = read_json(f)
        if data is None:
            continue
        # a Data file is read at runtime when it is a dink-art/1 manifest (DinkArtSubsystem scans Data/Art for that
        # schema) or when Runtime C++ names its file; others (hero_actions.json, ground_review.json) bind nothing
        stem = os.path.splitext(os.path.basename(f))[0]
        if not (isinstance(data, dict) and data.get("schema") == "dink-art/1") and stem not in named:
            continue
        walk_json(data, rel(f), pk, roots, BARE_PREFIX.get(os.path.basename(f)))
    for d in runtime_module_dirs():
        for f in sorted(glob.glob(os.path.join(d, "**", "*.cpp"), recursive=True) + glob.glob(os.path.join(d, "**", "*.h"), recursive=True)):
            if "/Tests/" in f.replace(os.sep, "/"):
                continue
            with open(f, encoding="utf-8", errors="replace") as h:
                for lit in CPP_LITERAL.findall(h.read()):
                    bind_string(lit, rel(f), pk, roots)
    for f in sorted(glob.glob(os.path.join(PROJECT, "Config", "*.ini"))):
        with open(f, encoding="utf-8", errors="replace") as h:
            for m in GAME_PATH.findall(h.read()):
                if m.split(".")[0] in pk.files:
                    roots[m.split(".")[0]].add(rel(f))
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
    for p, where in sorted(roots.items()):
        via[p] = sorted(where)[0]
        ROOT_OF[p] = p
        queue.append(p)
    while queue:
        p = queue.popleft()
        if p.startswith("/Engine/") or p not in pk.files:
            continue
        for q in pk.refs(p):
            if q not in via:
                via[q] = "via " + os.path.basename(p) + " (" + via[p].split(" (")[0] + ")"
                ROOT_OF[q] = ROOT_OF[p]
                queue.append(q)
    return via


ROOT_OF = {}    # package -> the root package it is reached from (filled by reach)


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
    for f in sorted(glob.glob(os.path.join(ART, "**", "*"), recursive=True)):
        low = f.replace(os.sep, "/").lower()
        if not low.endswith((".fbx", ".glb")) or any(s.lower() in low for s in skip_dirs):
            continue
        stem = LOD_SUFFIX.sub("", os.path.splitext(os.path.basename(f))[0])
        kind = "clip" if stem.startswith(("A_", "AN_")) else "mesh"
        if kind == "clip":
            if "/Animations/" in f.replace(os.sep, "/"):
                continue                   # hero/NPC clips come from the clip manifests (names differ from files)
            stem = "AN_" + stem[2:] if stem.startswith("A_") else stem
        stream = "/".join(rel(f, ART).split(os.sep)[:2])
        key = (stem, kind)
        # the same asset exported by two streams (an older source tree and the photoreal pass): one row that lists
        # every copy (sorted, so the table regenerates byte-identically) and names both streams
        if key in rows:
            old = rows[key]
            copies = sorted(set(old[2].split(" | ")) | {f})
            streams = " + ".join(sorted(set(old[3].split(" + ")) | {stream}))
            rows[key] = (stem, kind, " | ".join(copies), streams)
        else:
            rows[key] = (stem, kind, f, stream)
    for man in sorted(glob.glob(os.path.join(ART, "**", "animation_manifest.json"), recursive=True)):
        m = read_json(man) or {}
        base = os.path.dirname(man)
        clips = m.get("clips") or m.get("animations") or {}
        for key, c in clips.items():
            name = c.get("asset_name") or ("AN_" + key)
            fbx = os.path.join(base, c.get("fbx", ""))
            rows[(name, "clip")] = (name, "clip", fbx if os.path.isfile(fbx) else "", "/".join(rel(man, ART).split(os.sep)[:3]))
    # Flipbooks and decal sets of the unclaimed kit: a folder with T_*_BC but no mesh source.
    for d in sorted(glob.glob(os.path.join(ART, "PhotorealPass", "Unclaimed", "*", "*"))):
        if not os.path.isdir(d) or glob.glob(os.path.join(d, "*.fbx")) or glob.glob(os.path.join(d, "*.glb")):
            continue
        bcs = sorted(glob.glob(os.path.join(d, "T_*_BC.png")) + glob.glob(os.path.join(d, "T_*_Flipbook*.png")))
        if bcs:
            name = os.path.basename(d)
            rows[(name, "fx")] = (name, "decal/flipbook", bcs[0], "PhotorealPass/Unclaimed")
    return sorted(rows.values(), key=lambda r: (r[3], r[0]))


OWNER_ID = re.compile(r"\b(?:[A-Z]{2}-Q?\d+|A\d{2,3})\b")


def table_ids():
    """Row ids of doc/remaster/ALPHA_BUG_LIST.md and FABLE_ART_QUEUE.md (first cell of each table row)."""
    ids = set()
    for name in ("ALPHA_BUG_LIST.md", "FABLE_ART_QUEUE.md"):
        try:
            with open(os.path.join(os.path.dirname(PROJECT), "doc", "remaster", name), encoding="utf-8") as h:
                ids.update(m.group(1) for m in re.finditer(r"^\| *([A-Z]{1,2}-?Q?[0-9]+[a-z]?) *\|", h.read(), re.M))
        except OSError:
            pass
    return ids


def known_rows(check_ids=True):
    """The reviewed reasons. Every owner id a reason names (A204, DS-07, PQ-Q5, ...) must be a row of the bug list or
    the art queue: a typo or a renumbered row stops the run (review of PR #154)."""
    d = read_json(os.path.join(PROJECT, "Scripts", "art_wiring_known.json")) or {}
    if check_ids:
        ids = table_ids()
        # a row may name an id that an open PR adds (`pending_ids`); every other id must exist now
        missing = sorted({i for r in d.get("rows", []) for i in OWNER_ID.findall(r["why"]) if i not in r.get("pending_ids", [])} - ids)
        if ids and missing:
            sys.exit("art_wiring_audit: art_wiring_known.json names rows that ALPHA_BUG_LIST.md / FABLE_ART_QUEUE.md do "
                     "not have: " + ", ".join(missing))
    return [(re.compile(r["match"]), re.compile(r["source"]) if r.get("source") else None, r["kind"], r["why"])
            for r in d.get("rows", [])]


def known_reason(name, src, rows):
    """-> (kind, why) of the first reviewed row matching the asset, or None."""
    for m, srx, kind, why in rows:
        if m.search(name) and (srx is None or (src and srx.search(src.replace(os.sep, "/").replace("\\", "/")))):
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
    """TEXT("...") literals of the Runtime modules (Editor and DeveloperTool modules play nothing for a player)."""
    out = set()
    for d in runtime_module_dirs():
      for f in sorted(glob.glob(os.path.join(d, "**", "*.cpp"), recursive=True) + glob.glob(os.path.join(d, "**", "*.h"), recursive=True)):
        if "/Tests/" in f.replace(os.sep, "/"):
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


def card_table(audit_path, coverage_path, families_path, unbound_by_class, placements=()):
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
    by_origin = {p["id"]: p.get("class_id") for p in placements}
    cards = collections.defaultdict(lambda: {"cards": 0, "screens": set(), "final": [], "buried": 0, "with_origin": 0})
    with open(audit_path, encoding="utf-8") as h:
        for line in h:
            d = json.loads(line)
            for p in d.get("prims", []):
                m = re.search(r"MI_Sprite_(\d+)_(\d+)", json.dumps(p.get("mats", [])))
                cn = p.get("cn", "")
                o = p.get("o")
                # a card is a sprite picture on a Card / Decor component (indoor cards use a lit material instance, so
                # an origin on the stock card mesh counts too); replacement meshes on a Card component do not
                if not (cn == "Card" or cn.startswith("Decor")):
                    continue
                if not m and not (o in by_origin and "DinkCard" in (p.get("mesh") or "")):
                    continue
                cls = by_origin.get(o) or (classes.get((m.group(1), str(int(m.group(2)))), "seq %s/%s" % m.groups()) if m else "?")
                c = cards[cls]
                if p.get("max", [0, 0, 0])[2] < -500:      # parked under the ground: not drawn
                    c["buried"] += 1
                    continue
                c["cards"] += 1
                c["with_origin"] += 1 if o else 0
                c["screens"].add(d["screen"])
                if p.get("o") and state.get(p["o"]) == "final":
                    c["final"].append(p["o"])
    out = []
    for cls, c in sorted(cards.items(), key=lambda x: (-x[1]["cards"], x[0])):
        if not c["cards"]:
            continue
        out.append({"class": cls, "cards": c["cards"], "with_origin": c["with_origin"], "screens": " ".join(str(x) for x in sorted(c["screens"])),
                    "final_origin_cards": " ".join(c["final"]), "family_row": "yes" if cls in fam else "",
                    "mesh_available": " ".join(sorted(unbound_by_class.get(cls, [])))})
    return out


KNOWN_KINDS = ("queued", "alternate", "superseded", "deliberate", "replaced", "bug")


def gap_flag(reason, cov):
    """The flag of a source that does not reach the player. Only a reviewed reason (art_wiring_known.json, prefixed
    with its kind) is deliberate / alternate / superseded / replaced / bug; a queue row that names the asset makes it
    queued; a note in the unclaimed kit's STATUS.md alone is `documented` (written down, not reviewed here)."""
    for kind in KNOWN_KINDS:
        if reason.startswith(kind + ":"):
            return kind
    if cov:
        return "queued"
    if reason.startswith("STATUS.md"):
        return "documented"
    return None


def worst(flags):
    return max(flags, key=SEVERITY.index) if flags else "ok"


HERO_MESHES = {"/Game/Dink/Photoreal/Characters/Dink/SK_Dink_Photoreal", "/Game/Dink/Hero/SK_Dink"}


_COMMIT_CACHE = {}


class _CommitPackages:
    """The package names of a commit's Content (from git ls-tree), shaped like Packages for bind_string."""

    def __init__(self, files):
        self.files = {"/Game/" + f[len("Content/"):].rsplit(".", 1)[0]: f for f in files if f.endswith((".uasset", ".umap"))}
        self.by_name = collections.defaultdict(list)
        for g in self.files:
            self.by_name[os.path.basename(g)].append(g)


def commit_roots(commit):
    """(package files, direct roots) at `commit`, by the same binding rules as runtime_roots: Data JSON that the
    runtime reads there (dink-art/1, or named by that commit's Runtime C++), the string literals of its Runtime
    modules, and the composed paths."""
    if commit in _COMMIT_CACHE:
        return _COMMIT_CACHE[commit]

    def git(*args):
        return subprocess.run(["git", "-C", PROJECT] + list(args), capture_output=True, text=True).stdout
    if subprocess.run(["git", "-C", PROJECT, "cat-file", "-e", commit + "^{commit}"], capture_output=True).returncode != 0:
        sys.exit("art_wiring_audit: unknown commit %r (--cook-commit / --sweep-commit)" % commit)
    prefix = git("rev-parse", "--show-prefix").strip()
    every = [f[len(prefix):] if prefix and f.startswith(prefix) else f
             for f in git("ls-tree", "-r", "--name-only", commit, "--", ".").splitlines()]
    cpk = _CommitPackages([f for f in every if f.startswith("Content/")])
    roots = collections.defaultdict(set)
    module_dirs = [os.path.relpath(d, PROJECT).replace(os.sep, "/") + "/" for d in runtime_module_dirs()]
    literals = []
    for f in sorted(every):
        if f.endswith((".cpp", ".h")) and "/Tests/" not in f and any(f.startswith(d) for d in module_dirs):
            for lit in CPP_LITERAL.findall(git("show", "%s:./%s" % (commit, f))):
                literals.append(lit)
                bind_string(lit, "C++ at " + commit, cpk, roots)
    named = "\n".join(literals)
    for f in sorted(every):
        if f.startswith("Content/Dink/Data/") and f.endswith(".json") and "/Audio/" not in f and "/Hardness/" not in f:
            try:
                data = json.loads(git("show", "%s:./%s" % (commit, f)))
            except ValueError:
                continue
            stem = os.path.splitext(os.path.basename(f))[0]
            if (isinstance(data, dict) and data.get("schema") == "dink-art/1") or stem in named:
                walk_json(data, f, cpk, roots, BARE_PREFIX.get(os.path.basename(f)))
    for game, where in COMPOSED.items():
        if game in cpk.files:
            roots[game].add(where)
    _COMMIT_CACHE[commit] = (set(cpk.files), roots)
    return _COMMIT_CACHE[commit]


def in_commit(game, commit, via_here):
    """Was the package there and bound at `commit` (the tree a cook or sweep ran on)? Its package must exist there, and
    the root it is reached from today must have been a root there too (same binding rules); a package reached from
    a world map counts as bound when it existed (the maps of that commit are not in git)."""
    files, roots = commit_roots(commit)
    if game not in files:
        return False
    root = ROOT_OF.get(game, game)
    if via_here.get(root, "").startswith("world map"):
        return True
    return root in roots


def captured_screens(audit_path):
    out = set()
    with open(audit_path, encoding="utf-8") as h:
        for line in h:
            out.add(json.loads(line).get("screen"))
    return out


def load_placements(path):
    """placements.json of a world export -> list of placements (empty without --placements)."""
    d = read_json(path) if path else None
    return (d or {}).get("placements", []) if isinstance(d, dict) else []


def unseen_reason(games, via, families, placements, captured, environment):
    """Why a bound mesh is absent from the sweep's scene audit, or 'UNEXPLAINED'."""
    roots = " ".join(via[g] for g in games)
    if "stonebrook_fields_471" in roots:
        return "bound by stonebrook_fields_471.json; screen 471 was not captured by the sweep"
    if "stonebrook_vista" in roots:
        return "vista mesh outside the play screen (the scene audit lists only primitives whose centre is on the player's screen)"
    if "DinkPhotorealNpcMesh" in roots:
        return ("drawn for the characters.json placement or script profile it replaces (Milder: script profile s1-bul, "
                "a sprite his script creates); the sweep entered each screen once and did not play that story beat")
    if "creatures.json" in roots:
        cr = read_json(os.path.join(CONTENT, "Dink", "Data", "Art", "creatures.json")) or {}
        corpses = json.dumps([c.get("corpses", []) for c in cr.get("classes", [])] + [p.get("corpse") for p in cr.get("placements", [])])
        if any(g in corpses for g in games):
            return "creatures.json corpse: drawn only after a kill (add_kill_sprite); the sweep killed nothing"
    if "environment.json" in roots:
        texts = {k: json.dumps(v) for k, v in environment.items()}
        sections = sorted(k for k, t in texts.items() if any(g in t for g in games))
        if sections:
            return "environment.json %s: drawn only in that state or place (burn, state swap, light props); not in the sweep's states" % "/".join(sections)
    classes = set()
    for f in families:
        meshes = [f.get("mesh", "")] + list(f.get("variants", [])) + [f.get("span_fill", "")]
        if any(m.split(".")[0] in games for m in meshes if m):
            classes.add((f.get("family"), f.get("frame")))
    if classes and placements:
        mine = [p for p in placements if any(c == p.get("class_id") or (str(c) == str(p.get("seq")) and (fr is None or fr == p.get("frame")))
                                             for c, fr in classes)]
        if not mine:
            return "family row with no placement of its class in the world export"
        visible = [p for p in mine if p.get("screen") in captured and not p.get("vision") and not p.get("script")]
        if not visible:
            parts = []
            vg = sum(1 for p in mine if p.get("vision"))
            nc = sum(1 for p in mine if p.get("screen") not in captured)
            sc = sum(1 for p in mine if p.get("script") and not p.get("vision"))
            if vg: parts.append("%d vision-gated (story state)" % vg)
            if nc: parts.append("%d on screens not captured" % nc)
            if sc: parts.append("%d scripted (keep their card unless the row is scripted)" % sc)
            return "its %d placement(s): %s (%s)" % (len(mine), ", ".join(parts), " ".join(sorted(p["id"] for p in mine)[:6]))
        return "UNEXPLAINED: %d unscripted placement(s) on captured screens at vision 0, e.g. %s" % (
            len(visible), " ".join(sorted(p["id"] for p in visible)[:4]))
    if "families.json" in roots:
        return "UNEXPLAINED (families.json row; pass --placements to check its placements)"
    return "UNEXPLAINED (%s)" % roots[:120]


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
    ap.add_argument("--cook-commit", help="git commit the --cooked set was cooked from: a bound package that commit did not "
                                          "have or bind postdates the cook (flag unverified, not not_cooked)")
    ap.add_argument("--sweep-commit", help="git commit the --scene-audit sweep ran on: a bound mesh that commit did not "
                                           "have or bind postdates the sweep (flag unverified, not not_seen)")
    ap.add_argument("--placements", help="ImportData/placements.json of a world export: origin -> class for the card table, "
                                         "and the reason a bound mesh is not seen")
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
    swapped, only_tag = swapped_sources()
    authored, context = {}, set()       # authored dink-art manifests -> screen; render-only context manifests
    for f in sorted(glob.glob(os.path.join(CONTENT, "Dink", "Data", "Art", "*.json"))):
        d = read_json(f) or {}
        if str(d.get("schema", "")).startswith("dink-art/"):
            if "context" in d:
                context.add(rel(f))
            else:
                authored[rel(f)] = d.get("screen", 1)
    captured = captured_screens(a.scene_audit) if a.scene_audit else set()
    placements = load_placements(a.placements)
    families = (read_json(os.path.join(CONTENT, "Dink", "Data", "Art", "families.json")) or {}).get("families", [])
    environment = read_json(os.path.join(CONTENT, "Dink", "Data", "Environment", "environment.json")) or {}
    rows = []
    claimed = set()
    for name, kind, src_all, stream in sources():
        srcs = src_all.split(" | ") if src_all else []
        src = srcs[0] if srcs else ""
        games = sorted(g for g in pk.by_name.get(name, []) if "/_Generated/" not in g)
        if kind == "mesh" and not games:
            # an FBX of the same object exported again under an alternate name (_PR) is not a separate asset
            games = sorted(pk.by_name.get(name + "_PR", []))
        if kind == "clip" and not games:
            games = sorted(pk.by_name.get(name.replace("AN_", "AN_", 1) + "_PR", []))
        flags, details = [], []
        reason = ""
        deliveries = sorted({LOD_DIR.sub("", os.path.dirname(rel(x)).replace(os.sep, "/")) for x in srcs})
        if kind != "clip" and len(deliveries) > 1:
            details.append("%d separate deliveries share this name (%s); the package does not record which one was "
                           "imported" % (len(deliveries), "; ".join(deliveries)))
        fam = unclaimed_family_of(src) if src else None
        st = status.get(name) or (status.get("family:" + fam) if fam else None)
        k = known_reason(name, src_all, known)
        if k:
            reason = "%s: %s" % k
        elif kind == "clip" and deliberate_clip_reason(name, natural, {}):
            reason = "replaced: " + deliberate_clip_reason(name, natural, {})
        elif st and ("not imported" in st[1] or "not bound" in st[1]) and not any(g in via for g in games):
            # the unclaimed kit's note explains a gap; it says nothing about a same-named asset another kit delivered
            # and the game draws (the corpse kit's bodies share names with the unclaimed kit's corpses)
            reason = ("STATUS.md: " + st[1] + "; " + st[2])[:300]
        cov = covered_by(name, index)
        if not cov and k:       # the reviewed reason names its owner row (A2xx, DS-07, PQ-Q5, ...)
            cov = " ".join(dict.fromkeys(OWNER_ID.findall(k[1])))
        if not games:
            flags.append(gap_flag(reason, cov) or "not_imported")
        bound_where, cooked_s, seen_s = "", "", ""
        for g in games:
            claimed.add(g)
            for f, d in check_package(pk, g, pk.tags(g)):
                flags.append(f)
                details.append(d)
            for r in sorted(pk.refs(g)):
                if r in pk.files:
                    claimed.add(r)
                    for f, d in check_package(pk, r, pk.tags(r)):
                        flags.append(f)
                        details.append(os.path.basename(r) + ": " + d)
                    for rr in sorted(pk.refs(r)):
                        if rr in pk.files and os.path.basename(rr).startswith("T_"):
                            claimed.add(rr)
                            for f, d in check_package(pk, rr, pk.tags(rr)):
                                flags.append(f)
                                details.append(os.path.basename(rr) + ": " + d)
            if g in via and not bound_where:
                bound_where = via[g]
            if cooked is not None and g in via:
                cooked_s = "yes" if g.lower() in cooked else "no"
            if g in seen and not seen_s:
                seen_s = "yes (%s uses, screens %s)" % (seen[g]["uses"], " ".join(seen[g]["screens"].split()[:6]))
        bound_games = [g for g in games if g in via]
        if games and not bound_where:
            flags.append(gap_flag(reason, cov) or "unbound")
            if len(games) > 1:
                details.append("%d packages of this name, none bound" % len(games))
        elif len(games) > 1 and len(bound_games) < len(games):
            details.append("stale twin(s), not bound: " + " ".join(g for g in games if g not in via))
        newer = [g for g in bound_games if not in_commit(g, a.cook_commit, via)] if a.cook_commit else []
        if bound_games and cooked_s == "no":
            if newer:
                flags.append("unverified")
                details.append("not in the tree that was cooked (added after that cook)")
            else:
                flags.append("not_cooked")
        after_sweep = bool(a.sweep_commit) and all(not in_commit(g, a.sweep_commit, via) for g in bound_games)
        if bound_games and kind != "clip":
            if any(g in swapped for g in bound_games):
                targets = " / ".join(sorted({os.path.basename(t.split(".")[0]) for g in bound_games for t in swapped.get(g, [])}))
                done, decided, missed = swap_status(bound_games, roots, swapped, only_tag, authored, context)
                if missed:
                    flags.append("bug")
                    cov = cov or " ".join(x for x, hit in (("A206", any(os.path.basename(w) == "families.json" for w in missed)),
                                                           ("A207", any(w in context for w in missed))) if hit)
                    details.append("drawn unswapped by %s: mesh_swaps (-> %s) runs only for elements of authored (non-context) "
                                   "dink-art manifests%s" % (", ".join(missed), targets, "; seen in the sweep: " + seen_s if seen_s else ""))
                elif decided:
                    flags.append("deliberate")
                    reason = reason or ("deliberate: environment.json mesh_swap_only_tag limits the swap to %s; %s keep the old "
                                        "mesh on purpose (environment.json note)" % (
                                            only_tag.get(bound_games[0], "?"), ", ".join(decided)))
                elif seen_s:
                    flags.append("bug")
                    details.append("drawn unswapped in the sweep (%s) although every root is swapped (-> %s)" % (seen_s, targets))
                else:
                    flags.append("replaced")
                    reason = reason or "replaced: environment.json mesh_swaps draws %s in its place" % targets
            elif k and k[0] in ("replaced", "bug", "superseded"):
                flags.append(k[0])
            elif any(g in HERO_MESHES for g in bound_games):
                seen_s = seen_s or "player pawn (the scene audit lists the screen, not the pawn; the hero is in every frame)"
            elif not seen_s and seen and kind == "mesh" and after_sweep:
                flags.append("unverified")
                details.append("not seen: added after the sweep (not in its tree)")
            elif not seen_s and seen and kind == "mesh":
                why = unseen_reason(bound_games, via, families, placements, captured, environment)
                flags.append("not_seen")
                details.append("not seen: " + why)
        played = ""
        if kind == "clip" and bound_games:
            played = clip_played(name, reason, literals, roots, games)
            if reason.startswith("replaced:"):
                flags.append("replaced")
            elif played.startswith("no (no runtime"):
                flags.append("unbound")
                details.append("bound by a manifest but no runtime caller plays it")
        if cov and not reason and any(f in ("not_imported", "unbound") for f in flags):
            reason = "queued: " + cov
        rows.append({
            "asset": name, "kind": kind, "stream": stream, "source": " | ".join(rel(x) for x in srcs),
            "exported": "yes" if srcs and all(os.path.isfile(x) for x in srcs) else "no",
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
        cooked_s = "" if cooked is None or not bound_where else ("yes" if g.lower() in cooked else "no")
        seen_s = "yes" if g in seen else ""
        k = known_reason(n, g, known)
        reason = "%s: %s" % k if k else ""
        if not bound_where:
            flags.append(gap_flag(reason, covered_by(n, index)) or "unbound")
        elif cooked_s == "no" and a.cook_commit and not in_commit(g, a.cook_commit, via):
            flags.append("unverified")
            details.append("not in the tree that was cooked (added after that cook)")
        elif cooked_s == "no":
            flags.append("not_cooked")
        elif g in swapped:
            done, decided, missed = swap_status([g], roots, swapped, only_tag, authored, context)
            flags.append("bug" if missed else "deliberate" if decided else "replaced")
            reason = reason or ("replaced: environment.json mesh_swaps" if not (missed or decided) else "")
        elif k and k[0] in ("replaced", "bug", "superseded"):
            flags.append(k[0])
        elif g in HERO_MESHES:
            seen_s = "player pawn"
        elif not seen_s and seen and n.startswith("SM_") and a.sweep_commit and not in_commit(g, a.sweep_commit, via):
            flags.append("unverified")
            details.append("not seen: added after the sweep (not bound in its tree)")
        elif not seen_s and seen and n.startswith("SM_"):
            flags.append("not_seen")
            details.append("not seen: " + unseen_reason([g], via, families, placements, captured, environment))
        rows.append({"asset": n, "kind": "package only", "stream": "/".join(g.split("/")[2:4]), "source": "",
                     "exported": "?", "imported": g, "bound": bound_where, "cooked": cooked_s, "seen": seen_s,
                     "covered_by": covered_by(n, index),
                     "flag": worst(flags), "detail": "; ".join(dict.fromkeys(details)), "reason": reason})

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
        names = {r["asset"] for r in rows if r["flag"] in ("unbound", "not_imported", "queued", "deliberate", "documented", "alternate")}
        for man in sorted(glob.glob(os.path.join(ART, "**", "manifest.json"), recursive=True)):
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
                               os.path.join(CONTENT, "Dink", "Data", "Art", "families.json"), unbound_by_class, placements)
        cards_out = a.cards_out or os.path.splitext(a.out)[0] + "_cards.csv"
        with open(cards_out, "w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, lineterminator="\n", fieldnames=["class", "cards", "with_origin", "screens", "final_origin_cards", "family_row", "mesh_available"])
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
    # every texture under the art folders, not only those reached from a source row
    tex_all = sorted(g for g in pk.files if g.startswith(tuple("/Game/" + x for x in ART_FOLDERS)) and os.path.basename(g).startswith("T_"))
    tex_ruled, tex_flags = 0, []
    for g in tex_all:
        n = os.path.basename(g)
        if NORMAL_TEX.search(n) or MASK_TEX.search(n) or COLOUR_TEX.search(n) or n.endswith("_E"):
            tex_ruled += 1
        tex_flags += ["%s (%s)" % (g, d) for f, d in check_package(pk, g, pk.tags(g))]
    lines += ["", "Textures under the art folders: %d; with a suffix rule (normal / mask / colour): %d; flagged: %d%s" % (
        len(tex_all), tex_ruled, len(tex_flags), (": " + "; ".join(tex_flags)) if tex_flags else "")]
    if card_rows:
        n_cards = sum(r["cards"] for r in card_rows)
        n_origin = sum(r["with_origin"] for r in card_rows)
        lines += ["", "Drawn sprite cards (scene audit, above the ground): %d cards of %d classes; %d carry an origin ID "
                  "(the final-origin check covers these; %d decor/instanced cards have none); on an origin counted final: %d; "
                  "classes with a delivered mesh made for them: %d" % (
                      n_cards, len(card_rows), n_origin, n_cards - n_origin,
                      sum(len(r["final_origin_cards"].split()) for r in card_rows),
                      sum(1 for r in card_rows if r["mesh_available"]))]
    unexplained = [r["asset"] for r in rows if r["flag"] == "not_seen" and "UNEXPLAINED" in r["detail"]]
    lines += ["", "not_seen rows without an explanation: %d%s" % (len(unexplained), (": " + ", ".join(unexplained)) if unexplained else "")]
    txt = "\n".join(lines) + "\n"
    print(txt)
    print("wrote", rel(a.out) if a.out.startswith(PROJECT) else a.out)
    if a.summary:
        with open(a.summary, "w", encoding="utf-8") as h:
            h.write(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
