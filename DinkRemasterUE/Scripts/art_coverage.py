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
  placeholder  still drawn by the greybox (card, block, volume, instance) or not
               drawn at all; no art binding. Also the conservative answer
               whenever the binding model is ambiguous.
  cut          coverage.csv marks it inactive/skipped; the reason is its detail.

The runtime model mirrored here is UDinkArtSubsystem / UDinkCreatureSubsystem:
bindings are by origin ID (or screen number), never by sprite sequence/frame;
a dink-art manifest is discarded whole if any referenced mesh is missing.
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

    seq_of = {}
    gp = os.path.join(PROJECT, "Content", "Dink", "Data", "Gameplay", "placements.csv")
    with open(gp, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            seq_of[r["origin"]] = int(r["seq"])

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
                finish(r, "screen ground (tile layer)", "terrain/screen", "placeholder", "greybox ground mesh, hardness prisms and volumes" + extra)
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


def summarise(out, manifests, assets, ledger_counts, notes, cov_path, top):
    states = ("final", "placeholder", "cut")
    by_state = collections.Counter(r["state"] for r in out)
    ids = {r["origin_id"] for r in out}
    print("Art coverage of %d coverage rows (%d unique origin IDs; the 93 sprite warps share their placement's ID)" % (len(out), len(ids)))
    print("input: %s (%d bytes)" % (rel(cov_path), os.path.getsize(cov_path)))
    print()
    table("State", ["state", "rows"], [[s, by_state[s]] for s in states] + [["total", len(out)]])

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
    print("Final grades: origin-bound %d, screen-dressing %d, warp rows inheriting a final host %d" % (direct, dress, warp_final))
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
