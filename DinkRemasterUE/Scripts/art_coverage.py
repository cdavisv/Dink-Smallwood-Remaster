#!/usr/bin/env python3
"""Art state of every origin ID: final, placeholder or cut (alpha gate audit).

Read-only on everything that exists. Writes only Saved/Import/art_coverage.csv
(override with --out). Pure Python 3 standard library.

    cd <project dir>            # DinkRemasterUE
    python3 -I Scripts/art_coverage.py

States (one per coverage row; see Plugins/DinkImport/Docs/art_coverage.md):

  final        a Codex-delivered asset under Content/Dink is bound to the ID at
               runtime and the binding resolves to an existing .uasset. Two
               grades, told apart in `evidence`:
                 "origin-bound"      the ID is named in a runtime manifest
                                     (Data/Art/creatures.json, characters.json
                                     placements, dink-art replacements) - exact;
                 "screen-dressing"   the ID is hidden by a published dink-art
                                     screen manifest whose authored kit elements
                                     replace that screen's sprites (hide_origins,
                                     or an instance under hide_screen_visuals) -
                                     the mapping is per screen, not per ID.
               Both are "final bespoke". A third grade is "final by family":
                 "family-bound"      Data/Art/families.json binds the placement's
                                     sprite family (class id, else sequence) to an
                                     existing mesh and no origin or screen binding
                                     handles it; UDinkArtFamilySubsystem dresses it
                                     at screen activation (visual only).
               A fourth grade is "final by town house":
                 "town-house"        Data/Art/town_houses.json (Scripts/assemble_town_houses.py) hides
                                     the card and names the assembled kit house that stands for it
                                     (`stands_for`); UDinkEnvironmentSubsystem::ApplyTownHouses shows
                                     that house instead (dink.TownHouses, visual only). See
                                     town_house_cards() for the exact conditions.
               A fifth grade is the screen ground:
                 "ground-layers"     the screen's tile layer is drawn by the photoreal terrain
                                     material and every tile class on it passed the in-game review
                                     (Data/Environment/ground_classes.json and ground_review.json;
                                     see screen_ground_state()).
  placeholder  still drawn by the greybox (card, block, volume, instance) or not
               drawn at all; no art binding. Also the conservative answer
               whenever the binding model is ambiguous.
  cut          coverage.csv marks it inactive/skipped; the reason is its detail.

The runtime model mirrored here is UDinkArtSubsystem / UDinkCreatureSubsystem
(bindings by origin ID or screen number; a dink-art manifest is discarded whole if
any referenced mesh is missing) and UDinkArtFamilySubsystem (bindings by sprite
family, for what those leave greybox; same precedence rules as its C++).
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_REPO = os.path.dirname(PROJECT)

KIND_BY_CATEGORY = {
    "npc": "character",
    "enemy": "creature", "animal": "creature",
    "interior_wall": "building kit", "structure": "building kit", "structure_part": "building kit",
    "furniture": "prop", "container": "prop", "prop": "prop", "pickup": "prop", "hazard": "prop",
    "flora_tree": "terrain/screen", "flora_grass": "terrain/screen", "flora_bush": "terrain/screen",
    "rock": "terrain/screen",
    "effect": "other", "other": "other",
}
KIND_BY_CLASS = {"duck_head": "creature", "duck_corpse": "creature", "pillbug_corpse": "creature"}
# Categories a screen kit does not stand in for: hidden sprites of these stay unbound.
NOT_KIT_COVERED = {"npc", "enemy", "animal", "effect", "other"}
ORIGIN_RE = re.compile(r"^S\d{3}_P\d{2}$")
LFS_MAGIC = b"version https://git-lfs"


def rel(path):
    return os.path.relpath(path, PROJECT)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


class Assets:
    """Resolves /Game/Dink/... object paths to .uasset files under Content/."""

    def __init__(self):
        self.cache = {}
        self.lfs_pointers = set()

    def resolve(self, game_path):
        """-> (exists, note). Only /Game/Dink/* counts as Codex-delivered content."""
        if game_path in self.cache:
            return self.cache[game_path]
        result = (False, "not a /Game path")
        if game_path.startswith("/Game/"):
            stem = game_path[len("/Game/"):].split(".")[0]
            f = os.path.join(PROJECT, "Content", stem + ".uasset")
            if not os.path.isfile(f):
                result = (False, "missing " + rel(f))
            else:
                try:
                    with open(f, "rb") as h:
                        pointer = h.read(32).startswith(LFS_MAGIC)
                except OSError:
                    pointer = False
                if pointer:
                    self.lfs_pointers.add(game_path)
                if not game_path.startswith("/Game/Dink/"):
                    result = (True, "engine template content, not Codex art")
                else:
                    result = (True, "LFS pointer, not pulled" if pointer else "")
        self.cache[game_path] = result
        return result


def load_ledger():
    """basename -> set(status) for art/source rows (ledger paths are SourceAssets or Content)."""
    index = collections.defaultdict(set)
    counts = collections.Counter()
    path = os.path.join(PROJECT, "SourceAssets", "asset_ledger.csv")
    if not os.path.isfile(path):
        return index, counts
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["asset_path"].startswith("SourceAssets/Audio"):
                continue
            counts[row["status"]] += 1
            for key in ("asset_path", "derived_path"):
                if row.get(key):
                    name = re.split(r"[\\/]", row[key])[-1].rsplit(".", 1)[0]
                    index[name].add(row["status"])
    return index, counts


def ledger_status(index, game_path):
    name = game_path.split("/")[-1].split(".")[0]
    s = index.get(name)
    return "/".join(sorted(s)) if s else "none"


def load_sequences():
    data = read_json(os.path.join(DATA_REPO, "tools", "dinkex", "out", "sequences.json"))
    names = {}
    if data:
        for s in data.get("sequences", []):
            p = s.get("path", "")
            names[int(s["seq"])] = p[len("graphics/"):] if p.startswith("graphics/") else p
    return names


def family(seq, names):
    if seq is None:
        return "-"
    return "%d %s" % (seq, names[seq]) if seq in names else "seq %d" % seq


def parse_detail(detail):
    """'live tree_pine_large flora_tree; vision 1 ...' -> (kind, class_id, category)."""
    head = re.sub(r"\(type \d+\)", "", detail.split(";")[0]).split()
    if len(head) >= 3:
        return head[0], head[1], head[2]
    return (head[0] if head else ""), "", ""


def load_manifests(assets, notes):
    """Published runtime art bindings, mirroring the order and validation of the C++ loaders."""
    art_dir = os.path.join(PROJECT, "Content", "Dink", "Data", "Art")
    files = sorted((f for f in os.listdir(art_dir) if f.lower().endswith(".json")), key=str.lower)
    m = {
        "replace": {},        # origin -> (manifest, mesh)
        "hide": {},           # origin -> manifest
        "warp_override": {},  # origin -> manifest
        "screen_dress": {},   # screen number -> (manifest, element count)
        "creature": {},       # origin -> (mesh, locomotion, feed)
        "character": {},      # origin -> mesh
        "context": [],        # render-only screen contexts (bind no origin IDs)
        "invalid": [],
        "player": None,
        "script_profiles": {},
        "manifests": {},
    }
    for name in files:
        d = read_json(os.path.join(art_dir, name))
        if not isinstance(d, dict):
            m["invalid"].append((name, "unparseable JSON"))
            continue
        schema = d.get("schema")
        if schema == "dink-art/1":
            rows = (d.get("replacements") or []) + (d.get("elements") or [])
            bad = []
            for r in rows:
                mesh = r.get("mesh") if isinstance(r, dict) else None
                if not mesh:
                    bad.append("row without mesh")
                    break
                ok, why = assets.resolve(mesh)
                if not ok:
                    bad.append("%s (%s)" % (mesh, why))
                    break
            if bad:  # the C++ loader returns before touching the scene
                m["invalid"].append((name, "runtime would discard whole manifest: " + bad[0]))
                continue
            if "context" in d:
                m["context"].append((name, d.get("screen"), len(d.get("elements") or [])))
                continue
            screen = int(d.get("screen", 1))
            elements = len(d.get("elements") or [])
            m["manifests"][name] = {"screen": screen, "elements": elements}
            for r in d.get("replacements") or []:
                m["replace"][r["origin"]] = (name, r["mesh"])  # later file wins, as at runtime
            for o in d.get("hide_origins") or []:
                m["hide"][o] = name
            for r in d.get("warp_overrides") or []:
                m["warp_override"][r["origin"]] = name
            for s in d.get("hide_screen_visuals") or []:
                if elements or d.get("replacements"):
                    m["screen_dress"][int(s)] = (name, elements)
        elif schema == "dink-creatures/1":
            for r in d.get("placements") or []:
                needed = [r.get("mesh", ""), r.get("locomotion", "")]
                if r.get("feed_animation"):
                    needed.append(r["feed_animation"])
                res = [assets.resolve(p) for p in needed]
                if all(ok for ok, _ in res) and r.get("body_boxes"):
                    m["creature"][r["origin"]] = (r["mesh"], r["locomotion"], r.get("feed_animation") or "")
                else:
                    notes.append("creatures.json: %s not bound, asset missing or no body_boxes" % r.get("origin"))
        elif schema == "dink-characters/1":
            for r in d.get("placements") or []:
                mesh, loco = r.get("mesh", ""), r.get("locomotion", "")
                if assets.resolve(mesh)[0] and assets.resolve(loco)[0]:
                    m["character"][r["origin"]] = mesh
                else:
                    notes.append("characters.json: %s not bound, asset missing" % r.get("origin"))
            player = (d.get("player") or {}).get("mesh")
            if player and assets.resolve(player)[0]:
                m["player"] = player
            for script, prof in (d.get("script_profiles") or {}).items():
                if assets.resolve(prof.get("mesh", ""))[0]:
                    m["script_profiles"][script] = prof["mesh"]
        # camera_materials / hero_actions carry no origin bindings.
    return m


def load_source_candidates():
    """Art delivered as source only (not wired at runtime): origin id -> label, class prefix -> label."""
    by_origin = collections.defaultdict(list)
    by_class = {}
    root = os.path.join(PROJECT, "SourceAssets", "Art")
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith(".json") and "draft" in f.lower():
                d = read_json(os.path.join(dirpath, f))
                if not isinstance(d, dict) or d.get("schema") != "dink-art/1":
                    continue
                ids = set()
                for r in (d.get("replacements") or []) + (d.get("emitters") or []) + (d.get("warp_overrides") or []):
                    if isinstance(r, dict) and ORIGIN_RE.match(str(r.get("origin", ""))):
                        ids.add(r["origin"])
                ids.update(o for o in (d.get("hide_origins") or []) if ORIGIN_RE.match(str(o)))
                for lst in (d.get("hide_origins_by_vision") or {}).values():
                    ids.update(o for o in lst if ORIGIN_RE.match(str(o)))
                for e in d.get("elements") or []:
                    if isinstance(e, dict) and ORIGIN_RE.match(str(e.get("name", ""))):
                        ids.add(e["name"])
                for o in ids:
                    by_origin[o].append("unpublished draft %s" % rel(os.path.join(dirpath, f)))
    cre = os.path.join(root, "Creatures")
    if os.path.isdir(cre):
        for name in sorted(os.listdir(cre)):
            d = os.path.join(cre, name)
            if not os.path.isdir(d):
                continue
            by_class[name.lower()] = "creature source SourceAssets/Art/Creatures/%s (not wired for this ID)" % name
            og = read_json(os.path.join(d, name.lower() + "_origins.json"))
            if isinstance(og, dict):
                for p in og.get("placements") or []:
                    if isinstance(p, dict) and p.get("origin"):
                        by_origin[p["origin"]].append(by_class[name.lower()])
    return by_origin, by_class


def load_families(assets, notes):
    """families.json -> (rows, precedence origins, precedence screens), mirroring UDinkArtFamilySubsystem.

    Rows whose mesh is missing are dropped (the runtime keeps those cards). The precedence is read from the raw
    manifests, valid or not, exactly as FDinkFamilyPrecedence::AddManifest does."""
    art_dir = os.path.join(PROJECT, "Content", "Dink", "Data", "Art")
    rows, origins, screens = [], set(), set()
    fam = read_json(os.path.join(art_dir, "families.json"))
    if isinstance(fam, dict) and fam.get("schema") == "dink-art-families/1":
        seen = set()
        for r in fam.get("families") or []:
            if not isinstance(r, dict) or not str(r.get("family", "")).strip() or not str(r.get("mesh", "")).startswith("/Game/"):
                notes.append("families.json: row without family or /Game/ mesh skipped")
                continue
            name = r["family"].strip()
            m = re.match(r"^(\d+)", name)
            key = ("seq", int(m.group(1))) if m else ("class", name.lower())
            if m and isinstance(r.get("frame"), (int, float)) and int(r["frame"]) >= 1:
                key = ("seqframe", int(m.group(1)), int(r["frame"]))  # one picture of the sequence; wins over class rows
            if key in seen:
                notes.append("families.json: %s bound twice, second row skipped" % name)
                continue
            seen.add(key)
            ok, why = assets.resolve(r["mesh"])
            if not ok:
                notes.append("families.json: %s -> %s not bound at runtime (%s)" % (name, r["mesh"], why))
                continue
            rows.append({"family": name, "key": key, "mesh": r["mesh"], "scripted": bool(r.get("scripted", False))})
    for fn in sorted(os.listdir(art_dir)):
        if not fn.lower().endswith(".json") or fn.lower() == "families.json":
            continue
        d = read_json(os.path.join(art_dir, fn))
        if not isinstance(d, dict):
            continue
        schema = d.get("schema")
        if schema == "dink-art/1":
            for field in ("replacements", "warp_overrides"):
                origins.update(x["origin"] for x in d.get(field) or [] if isinstance(x, dict) and x.get("origin"))
            origins.update(o for o in d.get("hide_origins") or [] if isinstance(o, str))
            hv = d.get("hide_origins_by_vision")
            for lst in (hv.values() if isinstance(hv, dict) else [hv] if isinstance(hv, list) else []):
                origins.update(o for o in lst or [] if isinstance(o, str))
            for field in ("hide_screen_visuals", "authored_collision_screens"):
                screens.update(int(x) for x in d.get(field) or [] if isinstance(x, (int, float)))
            if d.get("elements") and isinstance(d.get("screen"), (int, float)):
                screens.add(int(d["screen"]))
        elif schema in ("dink-creatures/1", "dink-characters/1"):
            origins.update(x["origin"] for x in d.get("placements") or [] if isinstance(x, dict) and x.get("origin"))
    return rows, origins, screens


def family_binding(rows, seq, cls, frame=None):
    """Sequence-and-frame row first, then class row, then plain sequence row (DinkArtFamily::Resolve)."""
    for r in rows:
        if seq is not None and frame and r["key"] == ("seqframe", seq, frame):
            return r
    for r in rows:
        if r["key"] == ("class", (cls or "").lower()):
            return r
    for r in rows:
        if seq is not None and r["key"] == ("seq", seq):
            return r
    return None


TOWN_KIT = "/Game/Dink/Photoreal/TownExteriors/"


def town_house_cards(data, resolve):
    """town_houses.json -> {origin: (state, evidence)} for every card the file names, mirroring
    UDinkEnvironmentSubsystem::LoadTownHouses / ApplyTownHouses.

    `resolve(game_path)` -> (exists, note). A card is final when, and only when, all of these hold:
      1. its own screen's entry hides it (a `hide` list of that screen: the runtime hides cards per screen);
      2. `stands_for` of that screen names a house for it, the house exists in the file and has modules;
      3. every kit mesh of that house's modules exists (a house with a missing module is drawn with a hole);
      4. the card's screen draws something or needs nothing drawn: the runtime leaves every card of a screen alone
         when the screen lists modules and none of their meshes loads;
      5. the house did not fail the in-game review (`review.state` placeholder, written from REVIEW in the script);
      6. a house body covers the ground the card's picture covered: the card is not in `uncovered_m` of its screen
         (the assembled houses are shallower than the 1997 buildings; a roof picture that lay over what is now
         open ground behind the houses is hidden, but nothing stands where it was).
    Anything else the file names is placeholder, with the reason."""
    out = {}
    screens = data.get("screens") if isinstance(data, dict) else None
    if not isinstance(screens, dict):
        return out
    houses = {}
    for row in screens.values():
        for h in row.get("houses") or []:
            if isinstance(h, dict) and h.get("id"):
                houses[h["id"]] = h
    building = {hid: b.get("id", "") for b in data.get("buildings") or [] for hid in b.get("houses") or []}

    def mesh_path(mesh):
        return mesh if mesh.startswith("/") else TOWN_KIT + mesh

    def missing(h):
        return sorted({m.get("mesh", "") for m in h.get("modules") or [] if not resolve(mesh_path(m.get("mesh", "")))[0]})

    for row in screens.values():
        hidden = {o for h in row.get("houses") or [] for o in h.get("hide") or []}
        stands = row.get("stands_for") or {}
        uncovered = row.get("uncovered_m") or {}
        mods = [m for h in row.get("houses") or [] for m in h.get("modules") or []]
        screen_draws = (not mods) or any(resolve(mesh_path(m.get("mesh", "")))[0] for m in mods)
        for o in sorted(hidden | set(stands)):
            hid = stands.get(o)
            h = houses.get(hid) if hid else None
            if o not in hidden:
                out[o] = ("placeholder", "town_houses.json names house %s for this card but its screen does not hide it: the sprite card stays" % hid)
            elif h is None:
                out[o] = ("placeholder", "town_houses.json hides this card but no assembled house stands for it (stands_for %s)" % (hid or "is empty"))
            elif not h.get("modules"):
                out[o] = ("placeholder", "town_houses.json hides this card but house %s has no modules" % hid)
            elif missing(h):
                out[o] = ("placeholder", "town house %s lacks kit mesh %s: drawn incomplete" % (hid, ", ".join(missing(h)[:3])))
            elif not screen_draws:
                out[o] = ("placeholder", "no kit mesh of this card's screen loads: the runtime keeps the sprite cards")
            elif (h.get("review") or {}).get("state") == "placeholder":
                out[o] = ("placeholder", "town house %s failed the in-game review: %s" % (hid, h["review"].get("reason", "no reason recorded")))
            elif o in uncovered:
                out[o] = ("placeholder", "card hidden and town house %s stands for its building, but no house body covers the ground this picture "
                          "covered (nearest %.1f m away): open ground is shown there" % (hid, float(uncovered[o])))
            else:
                kit = sorted({m["mesh"] for m in h["modules"]})
                out[o] = ("final", "town-house: town_houses.json house %s%s (%d modules of %d kit meshes under %s) stands for this card; "
                          "card hidden by ApplyTownHouses (dink.TownHouses), collision, warps and scripts unchanged" % (
                              hid, " of building %s" % building[hid] if building.get(hid) else "", len(h["modules"]), len(kit), TOWN_KIT.rstrip("/")))
    return out


ENV_TEXTURES = "/Game/Dink/Textures/Environment/"
ENV_TERRAIN = "/Game/Dink/Materials/Environment/M_Env_Terrain"


def screen_ground_state(facts, review, resolve):
    """One screen's ground -> (state, evidence).

    `facts` is the screen's row of Content/Dink/Data/Environment/ground_classes.json (written by the world export:
    tile classes, the terrain layer of each, the layers the mask carries, the layers it could not carry, water);
    `review` is Content/Dink/Data/Environment/ground_review.json (the verdicts of the in-game review, kept by hand);
    `resolve(game_path)` -> (exists, note). The ground is final when, and only when:
      1. the screen instances the photoreal terrain material (not the 1997 painted ground) and every tile on it
         belongs to a class that has a terrain layer;
      2. the master material and the BC, N, ORM and H textures of every layer the mask carries exist (the importer
         falls back to the painted ground when one is missing);
      3. no layer was dropped for want of a mask channel (`dropped`: those tiles are drawn as an unrelated layer;
         `merged`, a layer drawn as one of its own family, is allowed);
      4. every tile class on the screen passed the review, indoors or outdoors as the screen is (`classes`);
         a class nobody looked at is not passed;
      5. water tiles have a water surface, unless the review passed the condition `water_without_surface`;
      6. the review holds no finding against this one screen (`screens`).
    Anything else is placeholder, with every reason found."""
    if not isinstance(facts, dict) or not facts.get("classes"):
        return "placeholder", "no ground facts for this screen in ground_classes.json (run the world export)"
    if not ground_rule_enabled(review):
        return "placeholder", "photoreal terrain layers %s, not final: the rule that counts reviewed screen grounds final is switched off (%s)" % (
            ", ".join(facts.get("layers") or []) or "none", "ground_review.json rule.count_reviewed_grounds_final, or --ground-rule off")
    where = "indoor" if facts.get("indoor") else "outdoor"
    classes = {c: n for c, n in facts["classes"].items() if n}
    layers = list(facts.get("layers") or [])
    drawn = "photoreal terrain layers %s%s" % (", ".join(layers) or "none", " and a water surface" if facts.get("water_surface") else "")
    reasons = []
    if facts.get("painted_ground") or not layers:
        reasons.append("keeps the 1997 painted ground picture as its texture")
    if facts.get("unmapped_tiles"):
        reasons.append("%d tiles of a class without a terrain layer" % facts["unmapped_tiles"])
    if layers and not resolve(ENV_TERRAIN)[0]:
        reasons.append("the terrain master material is not imported")
    for layer in layers:
        missing = [k for k in ("BC", "N", "ORM", "H") if not resolve("%sT_Env_%s_%s" % (ENV_TEXTURES, layer, k))[0]]
        if missing:
            reasons.append("layer %s lacks its %s texture: the importer falls back to the painted ground" % (layer, "/".join(missing)))
    for layer, lost in sorted((facts.get("dropped") or {}).items()):
        tiles = lost.get("tiles") if isinstance(lost, dict) else lost
        reasons.append("layer %s (%.1f tiles) is not drawn, the mask carries %d layers: shown as %s" % (
            layer, float(tiles), len(layers), lost.get("drawn_as", "another layer") if isinstance(lost, dict) else layers[0] if layers else "nothing"))
    verdicts = (review or {}).get("classes") or {}
    for cls in sorted(classes):
        v = (verdicts.get(cls) or {}).get(where) or {}
        if v.get("verdict") == "pass":
            continue
        reasons.append("tile class %s (%d tiles, %s): %s" % (cls, classes[cls], where, v.get("reason") or "not reviewed in the game"))
    if classes.get("water") and not facts.get("water_surface"):
        v = ((review or {}).get("conditions") or {}).get("water_without_surface") or {}
        if v.get("verdict") != "pass":
            reasons.append("%d water tiles without a water surface: %s" % (classes["water"], v.get("reason") or "not reviewed in the game"))
    return ("placeholder", "%s, not final: %s" % (drawn, "; ".join(reasons))) if reasons else ("final", (
        "ground-layers: tile classes %s -> %s (M_Env_Terrain, textures exist)%s; every class passed the in-game review of %s "
        "(ground_review.json); nothing greybox is drawn (hardness prisms are hidden unless dink.GreyboxBlockers 1)" % (
            ", ".join("%s %d" % (c, classes[c]) for c in sorted(classes, key=lambda c: (-classes[c], c))), drawn,
            "; %s drawn as a layer of its family" % ", ".join(sorted(facts["merged"])) if facts.get("merged") else "",
            (review or {}).get("date", "an unrecorded date"))))


def ground_rule_enabled(review):
    """The one switch of the screen-ground rule: ground_review.json `rule.count_reviewed_grounds_final` (absent = off;
    `--ground-rule on|off` overrides it for one run). Off, no ground counts final by review, whatever the verdicts."""
    return bool(((review or {}).get("rule") or {}).get("count_reviewed_grounds_final"))


def load_ground(notes, override=None):
    env = os.path.join(PROJECT, "Content", "Dink", "Data", "Environment")
    facts = read_json(os.path.join(env, "ground_classes.json"))
    review = read_json(os.path.join(env, "ground_review.json"))
    if not isinstance(facts, dict) or not isinstance(facts.get("screens"), dict):
        notes.append("ground_classes.json not found: every screen ground stays placeholder (run the world export)")
        facts = {"screens": {}}
    if not isinstance(review, dict):
        notes.append("ground_review.json not found: no tile class counts as reviewed")
        review = {}
    if override in ("on", "off"):
        review = dict(review, rule=dict(review.get("rule") or {}, count_reviewed_grounds_final=(override == "on")))
        notes.append("screen-ground rule forced %s by --ground-rule" % override)
    return facts["screens"], review


def classify(args):
    notes = []
    assets = Assets()
    manifests = load_manifests(assets, notes)
    ledger_idx, ledger_counts = load_ledger()
    names = load_sequences()
    cand_origin, cand_class = load_source_candidates()
    if not names:
        notes.append("tools/dinkex/out/sequences.json not found: families are bare sequence numbers")

    cov_path = os.path.join(PROJECT, args.coverage)
    if not os.path.isfile(cov_path):
        sys.exit("missing %s (run Scripts/import_greybox.sh --region all)" % rel(cov_path))
    with open(cov_path, newline="", encoding="utf-8") as f:
        cov = list(csv.DictReader(f))

    seq_of, frame_of, scripted_of = {}, {}, {}
    gp = os.path.join(PROJECT, "Content", "Dink", "Data", "Gameplay", "placements.csv")
    with open(gp, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            seq_of[r["origin"]] = int(r["seq"])
            frame_of[r["origin"]] = int(r["frame"])
            scripted_of[r["origin"]] = bool(r["script"].strip())
    fam_rows, fam_origins, fam_screens = load_families(assets, notes)
    manifests["families"] = fam_rows
    ground_facts, ground_review = load_ground(notes, getattr(args, "ground_rule", None))
    town_cards = town_house_cards(read_json(os.path.join(PROJECT, "Content", "Dink", "Data", "Art", "town_houses.json")), assets.resolve)

    def family_decision(oid, screen_no, cls, detail):
        """-> family row if UDinkArtFamilySubsystem dresses this placement on its own merits, else None."""
        if not fam_rows or detail.startswith("hardness_only") or "no picture" in detail:
            return None
        if screen_no in fam_screens or oid in fam_origins:
            return None
        row = family_binding(fam_rows, seq_of.get(oid), cls, frame_of.get(oid))
        if row is None or (scripted_of.get(oid) and not row["scripted"]):
            return None
        return row

    # The runtime dresses an instance decor component (one sprite frame on one screen) only when every instance in it
    # is bound to the same row; otherwise the whole component keeps its cards.
    decor_ok = {}
    for r in cov:
        if r["type"] != "placement" or r["became"].startswith("actor"):
            continue
        oid = r["origin_id"]
        if oid not in seq_of:
            continue
        group = (r["screen"], seq_of[oid], frame_of[oid])
        row = family_decision(oid, int(r["screen"].split("_")[1]), parse_detail(r["detail"])[1], r["detail"])
        prev = decor_ok.get(group, row)
        decor_ok[group] = row if (row is not None and prev is not None and prev is row) else None

    place = {r["origin_id"]: r for r in cov if r["type"] == "placement"}
    for tag, ids in (("replacement", manifests["replace"]), ("hide_origins", manifests["hide"]),
                     ("creatures.json", manifests["creature"]), ("characters.json", manifests["character"])):
        gone = sorted(o for o in ids if o not in place)
        if gone:
            notes.append("%s lists %d origin(s) absent from coverage (stale coverage?): %s" % (tag, len(gone), ", ".join(gone[:5])))

    rows = {}  # (origin_id, type) -> dict
    out = []

    def finish(r, fam, kind, state, ev):
        rec = {"origin_id": r["origin_id"], "type": r["type"], "screen": r["screen"], "region": r["region"],
               "sprite_family": fam, "art_kind": kind, "state": state, "evidence": ev}
        rows[(r["origin_id"], r["type"])] = rec
        out.append(rec)
        return rec

    def ledger_tag(mesh):
        return "ledger=" + ledger_status(ledger_idx, mesh)

    def placement_row(r):
        rec = _placement_row(r)
        rec["_cls"] = parse_detail(r["detail"])[1]  # class id, for the backlog print only
        return rec

    def _placement_row(r):
        oid = r["origin_id"]
        kind_tok, cls, cat = parse_detail(r["detail"])
        art_kind = KIND_BY_CLASS.get(cls) or KIND_BY_CATEGORY.get(cat, "other")
        fam = family(seq_of.get(oid), names)
        is_actor = r["became"].startswith("actor")
        screen_no = int(r["screen"].split("_")[1])
        flags = []
        # --- final: exact origin bindings -------------------------------------------------
        if is_actor and oid in manifests["creature"]:
            mesh, loco, feed = manifests["creature"][oid]
            return finish(r, fam, art_kind, "final", "origin-bound: creatures.json -> %s (+%s%s); %s; mesh/locomotion exist, skeleton compatibility needs the engine" % (
                mesh, loco.split("/")[-1].split(".")[0], ", feed" if feed else "", ledger_tag(mesh)))
        if is_actor and oid in manifests["character"]:
            mesh = manifests["character"][oid]
            return finish(r, fam, art_kind, "final", "origin-bound: characters.json -> %s; %s; locomotion is the engine template blendspace" % (mesh, ledger_tag(mesh)))
        if is_actor and oid in manifests["replace"]:
            name, mesh = manifests["replace"][oid]
            return finish(r, fam, art_kind, "final", "origin-bound: %s replacement -> %s; %s" % (name, mesh, ledger_tag(mesh)))
        # --- final: screen dressing ---------------------------------------------------------
        dress = manifests["screen_dress"].get(screen_no)
        hidden_by = None
        if is_actor and oid in manifests["hide"]:
            hidden_by = "hide_origins of %s" % manifests["hide"][oid]
        elif (not is_actor) and dress:
            hidden_by = "instance hidden by hide_screen_visuals of %s" % dress[0]
        if hidden_by:
            if cat in NOT_KIT_COVERED:
                flags.append("hidden by %s but %s sprites have no replacement art (nothing drawn)" % (hidden_by, cat))
            elif dress:
                return finish(r, fam, art_kind, "final", "screen-dressing: %s; screen %d kit has %d authored elements; per-screen, not a 1:1 binding" % (
                    hidden_by, screen_no, dress[1]))
            else:
                flags.append("hidden by %s but its screen has no published dressing" % hidden_by)
        # --- placeholder ------------------------------------------------------------------------
        base = "greybox " + ("instance" if not is_actor else "actor card")
        if kind_tok == "hardness_only":
            base = "greybox hardbox volume (hardness-only type 2 card, hidden in game)"
            flags.append("REVIEW-CUT no sprite art expected for a hardness-only proxy")
        if cls == "empty_placement":
            flags.append("REVIEW-CUT empty placement (data repo treatment not_needed)")
        if "unknown: no script found" in r["detail"]:
            flags.append("REVIEW-CUT vision-gated by a variable no script sets, never visible in play")
        elif "vision" in r["detail"]:
            flags.append("vision-gated variant")
        cands = list(cand_origin.get(oid, []))
        for prefix, label in cand_class.items():
            if cls == prefix or cls.startswith(prefix + "_"):
                if label not in cands:
                    cands.append(label)
        if cands:
            flags.append("source candidate: " + "; ".join(cands))
        cut_reasons = [f[len("REVIEW-CUT "):] for f in flags if f.startswith("REVIEW-CUT ")]
        if cut_reasons:
            # Owner decision, 9 Nov 2026: placements that can never meaningfully become final are cut, with the reason.
            return finish(r, fam, art_kind, "cut", "cut (owner decision 9 Nov 2026): " + "; ".join(cut_reasons) + "; " + base + " (%s)" % cls)
        # --- final: town house (family 33 cards the assembled kit houses stand for) -------------------
        town = town_cards.get(oid)
        if town and town[0] == "final":
            return finish(r, fam, art_kind, "final", town[1])
        if town:
            flags.append("town-house open: " + town[1])
        # --- final: family binding (what no origin or screen binding handles) ------------------------
        row = family_decision(oid, screen_no, cls, r["detail"])
        if row is not None and not is_actor:
            row = decor_ok.get((r["screen"], seq_of.get(oid), frame_of.get(oid)))
        if row is not None:
            return finish(r, fam, art_kind, "final", "family-bound: %s -> %s; %s, card hidden at screen activation, collision and script unchanged; %s" % (
                row["family"], row["mesh"], "actor" if is_actor else "instance", ledger_tag(row["mesh"])))
        return finish(r, fam, art_kind, "placeholder", "; ".join([base + " (%s)" % cls] + flags))

    # placements first (warps inherit their host)
    for r in cov:
        if r["type"] == "placement":
            placement_row(r)

    for r in cov:
        t, oid = r["type"], r["origin_id"]
        if t == "placement":
            continue
        if t == "screen":
            no = int(oid.split("_")[1])
            dress = manifests["screen_dress"].get(no)
            if dress:
                finish(r, "screen ground (tile layer)", "terrain/screen", "final",
                       "screen-dressing: %s hides the greybox ground/volumes of screen %d and spawns %d authored kit elements (collision replaced)" % (dress[0], no, dress[1]))
            else:
                extra = ""
                for lab in cand_origin.get("S%03d_P01" % no, []):
                    if lab.startswith("unpublished draft"):
                        extra = "; source candidate: " + lab
                        break
                state, evidence = screen_ground_state(ground_facts.get(str(no)), ground_review, assets.resolve)
                finding = (ground_review.get("screens") or {}).get(str(no))
                if state == "final" and isinstance(finding, dict) and finding.get("verdict") != "pass":
                    state, evidence = "placeholder", "photoreal terrain layers drawn, not final: this screen in the review: %s" % finding.get("reason", "no reason recorded")
                finish(r, "screen ground (tile layer)", "terrain/screen", state, evidence + (extra if state == "placeholder" else ""))
        elif t == "warp":
            if r["became"].startswith("inactive"):
                finish(r, "script warp", "warp", "cut", "cut: %s - %s" % (r["became"], r["detail"]))
                continue
            host = oid.split("@")[1] if "@" in oid else oid
            h = rows.get((host, "placement"))
            if h is None:
                finish(r, "script warp", "warp", "placeholder", "warp trigger volume, host placement %s not in coverage" % host)
                continue
            ov = manifests["warp_override"].get(host)
            ev = "warp trigger on host %s (%s): %s" % (host, h["state"], h["evidence"])
            if ov:
                ev += "; trigger moved onto authored door by warp_overrides of " + ov
            finish(r, h["sprite_family"], "warp", h["state"], ev)
        elif t == "start":
            if manifests["player"]:
                finish(r, "dink hero", "character", "final",
                       "origin-bound (ambiguous: marker, not a sprite): player pawn spawns here and characters.json player -> %s; %s" % (
                           manifests["player"], ledger_tag(manifests["player"])))
            else:
                finish(r, "dink hero", "character", "placeholder", "no player mesh bound")
        else:
            finish(r, "-", "other", "placeholder", "unrecognised coverage type " + t)
    return out, manifests, assets, ledger_counts, notes, cov_path


def table(title, header, rows):
    widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    print(title)
    print("  " + "  ".join(str(h).ljust(w) for h, w in zip(header, widths)))
    for r in rows:
        print("  " + "  ".join((str(c).ljust(w) if i == 0 else str(c).rjust(w)) for i, (c, w) in enumerate(zip(r, widths))))
    print()


def is_family_final(r):
    """Final through families.json: the placement itself, or a warp row whose host is."""
    return r["state"] == "final" and (r["evidence"].startswith("family-bound") or (
        r["evidence"].startswith("warp trigger") and "family-bound:" in r["evidence"]))


def summarise(out, manifests, assets, ledger_counts, notes, cov_path, top):
    states = ("final", "placeholder", "cut")
    by_state = collections.Counter(r["state"] for r in out)
    ids = {r["origin_id"] for r in out}
    print("Art coverage of %d coverage rows (%d unique origin IDs; the 93 sprite warps share their placement's ID)" % (len(out), len(ids)))
    print("input: %s (%d bytes)" % (rel(cov_path), os.path.getsize(cov_path)))
    print()
    table("State", ["state", "rows"], [[s, by_state[s]] for s in states] + [["total", len(out)]])
    by_family = sum(1 for r in out if is_family_final(r))
    table("State, final split into bespoke and family art", ["state", "rows"],
          [["final bespoke", by_state["final"] - by_family], ["final by family", by_family],
           ["placeholder", by_state["placeholder"]], ["cut", by_state["cut"]], ["total", len(out)]])

    by_type = collections.Counter((r["type"], r["state"]) for r in out)
    table("Row type x state", ["type"] + list(states),
          [[t] + [by_type[(t, s)] for s in states] for t in ("placement", "screen", "warp", "start")])

    kinds = sorted({r["art_kind"] for r in out})
    bk = collections.Counter((r["art_kind"], r["state"]) for r in out)
    table("Art kind x state", ["art_kind"] + list(states) + ["total"],
          [[k] + [bk[(k, s)] for s in states] + [sum(bk[(k, s)] for s in states)] for k in kinds])

    br = collections.Counter((r["region"], r["state"]) for r in out)
    regions = sorted({r["region"] for r in out}, key=lambda x: -sum(br[(x, s)] for s in states))
    table("Region x state", ["region"] + list(states) + ["total", "final%"],
          [[g] + [br[(g, s)] for s in states] + [sum(br[(g, s)] for s in states),
                "%.1f" % (100.0 * br[(g, "final")] / sum(br[(g, s)] for s in states))] for g in regions])

    finals = [r for r in out if r["state"] == "final"]
    direct = sum(1 for r in finals if r["evidence"].startswith("origin-bound"))
    dress = sum(1 for r in finals if r["evidence"].startswith("screen-dressing"))
    warp_final = sum(1 for r in finals if r["evidence"].startswith("warp trigger"))
    family_final = sum(1 for r in finals if r["evidence"].startswith("family-bound"))
    print("Final grades: origin-bound %d, screen-dressing %d, family-bound %d, warp rows inheriting a final host %d (%d of them family-bound)" % (
        direct, dress, family_final, warp_final, sum(1 for r in finals if r["evidence"].startswith("warp trigger") and is_family_final(r))))
    grounds = [r for r in out if r["type"] == "screen"]
    print("Screen grounds: %d final by screen-dressing, %d final by reviewed terrain layers, %d placeholder" % (
        sum(1 for r in grounds if r["state"] == "final" and r["evidence"].startswith("screen-dressing")),
        sum(1 for r in grounds if r["state"] == "final" and r["evidence"].startswith("ground-layers")),
        sum(1 for r in grounds if r["state"] == "placeholder")))
    why = collections.Counter()
    for r in grounds:
        if r["state"] == "placeholder" and ", not final: " in r["evidence"]:
            for reason in r["evidence"].split(", not final: ", 1)[1].split("; "):
                why[re.sub(r" \(\d+ tiles, (indoor|outdoor)\)", r" (\1)", re.sub(r" \(\d+\.\d tiles\)|^\d+ ", "", reason)).split(":")[0].strip()] += 1
    for reason, n in why.most_common(30):
        print("  %4d screens: %s" % (n, reason))
    print("Town houses (town_houses.json): %d placements final, %d named by the file but still placeholder" % (
        sum(1 for r in finals if r["evidence"].startswith("town-house")),
        sum(1 for r in out if r["state"] == "placeholder" and r["type"] == "placement" and "town-house open: " in r["evidence"])))
    ledger_final = collections.Counter()
    for r in (r for r in finals if r["evidence"].startswith("origin-bound")):
        m = re.search(r"ledger=(\S+?)(;|$| )", r["evidence"])
        ledger_final[m.group(1) if m else "n/a"] += 1
    print("Ledger status of the primary asset behind origin-bound finals: %s" % dict(ledger_final))
    print("Art/source ledger rows by status (audio excluded): %s -> nothing is owner-approved, 'final' means delivered and bound" % dict(ledger_counts))
    if assets.lfs_pointers:
        print("WARNING: %d bound assets are Git LFS pointers (run git lfs pull)" % len(assets.lfs_pointers))
    ph = [r for r in out if r["state"] == "placeholder" and r["type"] != "warp"]  # warps repeat their host
    cand = sum(1 for r in ph if "source candidate" in r["evidence"])
    decided = sum(1 for r in out if r["state"] == "cut" and r["type"] == "placement" and "owner decision" in r["evidence"])
    print("Placeholder placements/screens with an unwired source candidate: %d; placements cut by owner decision (hardness proxies, never-set vision variants, empty placements): %d" % (cand, decided))
    print("Runtime manifests: %d dressed screens %s; %d render-only contexts; %d creature, %d character, %d replacement bindings" % (
        len(manifests["screen_dress"]), sorted(manifests["screen_dress"]), len(manifests["context"]),
        len(manifests["creature"]), len(manifests["character"]), len(manifests["replace"])))
    fams = collections.Counter()
    for r in out:
        if r["type"] == "placement" and r["evidence"].startswith("family-bound"):
            fams[r["evidence"][len("family-bound: "):].split(" -> ")[0]] += 1
    print("Family bindings (families.json): %d rows with an existing mesh; placements turned final: %s" % (
        len(manifests.get("families") or []), ", ".join("%s %d" % kv for kv in sorted(fams.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"))
    for name, why in manifests["invalid"]:
        print("WARNING: manifest %s ignored: %s" % (name, why))
    for n in notes:
        print("NOTE:", n)
    print()

    fam = collections.defaultdict(lambda: collections.Counter())
    classes = collections.defaultdict(collections.Counter)
    kind = collections.defaultdict(collections.Counter)
    for r in out:
        if r["type"] in ("warp", "start"):
            continue
        if r["state"] == "placeholder" and r.get("_cls"):
            classes[r["sprite_family"]][r["_cls"]] += 1
        fam[r["sprite_family"]][r["state"]] += 1
        kind[r["sprite_family"]][r["art_kind"]] += 1
    backlog = sorted((f for f in fam if fam[f]["placeholder"]), key=lambda f: (-fam[f]["placeholder"], f))
    rows = []
    for i, f in enumerate(backlog[:top], 1):
        c = fam[f]
        rows.append([i, f, kind[f].most_common(1)[0][0], c["placeholder"], c["final"], c["cut"],
                     ", ".join("%s %d" % kv for kv in classes[f].most_common(3))])
    table("Backlog: top %d sprite families still placeholder (placements and screens; warps share their host's art)" % top,
          ["#", "sprite_family", "art_kind", "placeholder", "final", "cut", "main classes (placeholder)"], rows)
    cls_total = collections.Counter()
    cls_final = collections.Counter()
    for r in out:
        if r["type"] == "placement" and r.get("_cls"):
            (cls_total if r["state"] == "placeholder" else cls_final)[r["_cls"]] += 1
    table("Same backlog by class id (one asset family each, across sequences): top 15",
          ["class_id", "placeholder", "final"], [[c, n, cls_final[c]] for c, n in cls_total.most_common(15)])
    covered = sum(fam[f]["placeholder"] for f in backlog[:top])
    total_ph = sum(fam[f]["placeholder"] for f in backlog)
    print("Top %d families hold %d of %d placeholder placements/screens (%.1f%%); %d families in all" % (
        top, covered, total_ph, 100.0 * covered / max(total_ph, 1), len(backlog)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--coverage", default=os.path.join("Saved", "Import", "coverage.csv"), help="importer coverage report (project relative)")
    ap.add_argument("--out", default=os.path.join("Saved", "Import", "art_coverage.csv"), help="CSV to write (project relative)")
    ap.add_argument("--top", type=int, default=40, help="backlog families to print")
    ap.add_argument("--ground-rule", choices=("on", "off"), default=None,
                    help="override ground_review.json rule.count_reviewed_grounds_final for this run (the rule that counts a reviewed screen ground final)")
    args = ap.parse_args()
    out, manifests, assets, ledger_counts, notes, cov_path = classify(args)
    out_path = os.path.join(PROJECT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["origin_id", "type", "screen", "region", "sprite_family", "art_kind", "state", "evidence"],
                           lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    summarise(out, manifests, assets, ledger_counts, notes, cov_path, args.top)
    print("wrote %s (%d rows)" % (rel(out_path), len(out)))


if __name__ == "__main__":
    main()
