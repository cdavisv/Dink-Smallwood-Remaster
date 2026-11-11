#!/usr/bin/env python3
"""Prepare the explicit 85-barrel rollout inputs from the audited source and original game files."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from build_runtime_hardness_descriptors import build, write_missing
from sync_gameplay_data import rle_rows

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "tools/dinkex"))
from dinkex import TILES_PER_SCREEN, hard as original_hard
from dinkex.extract import Extractor
from dinkex.jsonfmt import pretty
from dinkex.runtime_hardness import decode_runtime_layers, runtime_layers

PHOTO_MESH = '/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01'
SURFACE_ALGORITHM = 'DinkOrientedTrianglesF32LEMaterialU16LE/1'
PHOTO_SURFACE_SHA1 = 'de0f514e0172077e7bbd9dc0b30c75f5c40939e6'
PAIR = {"S031_P03", "S209_P13"}
SOURCE_KEYS = ("id", "hash", "screen", "index", "type", "representation",
               "script", "brain", "vision", "seq", "frame", "map_x", "map_y", "hardness")


def legacy_sections(path):
    lines = [line for line in path.read_text().splitlines() if not line.startswith("#")]
    sections = {}
    for index in range(0, len(lines), 401):
        header = lines[index]
        if header in sections or len(lines[index + 1:index + 401]) != 400:
            raise ValueError(f"invalid legacy hardness sections: {path}")
        sections[header] = lines[index + 1:index + 401]
    return sections


def build_inputs(bundle, inventory_path, data, output):
    bundle_placements = (bundle / "placements.json").read_bytes()
    inventory = json.loads(inventory_path.read_bytes())
    if hashlib.sha256(bundle_placements).hexdigest() != inventory["placements_sha256"]:
        raise ValueError("bundle placement bytes differ from the audited inventory")
    placements = {row["id"]: row for row in json.loads(bundle_placements)["placements"]}
    targets = {row["id"]: row for row in inventory["rows"]}
    if len(targets) != len(inventory["rows"]) or len(targets) != 83 or PAIR & targets.keys():
        raise ValueError("expected 83 distinct additions to the original pair")
    excluded = set(inventory["preserve_soft"]) | set(inventory["preserve_authored_exclusions"])
    if excluded & (targets.keys() | PAIR):
        raise ValueError("soft or authored control appears in rollout targets")
    for origin, row in targets.items():
        if any(row[key] != placements[origin][key] for key in SOURCE_KEYS):
            raise ValueError(f"source tuple changed for {origin}")

    art = PROJECT / "Content/Dink/Data/Art"
    families = json.loads((art / "families.json").read_bytes())
    origins = sorted(targets.keys() | PAIR)
    prior_rules = {row["origin"]: row for row in families["collision_fit"]["origins"]}
    if set(prior_rules) != set(origins) or families["collision_fit"]["schema"] != "dink-family-collision-fit/3":
        raise ValueError("expected the explicit approved photoreal85 policy")
    common_rule = dict(family="barrel", mesh=PHOTO_MESH, surface_algorithm=SURFACE_ALGORITHM,
                       surface_sha1=PHOTO_SURFACE_SHA1, anchor="sprite_ground",
                       geometry="cooked_complex", raster="cell_center")
    for origin, prior in prior_rules.items():
        expected = dict(common_rule, origin=origin, source_hash=placements[origin]["hash"],
                        source_script=placements[origin]["script"], source_type=placements[origin]["type"],
                        source_representation=placements[origin]["representation"])
        if prior != expected:
            raise ValueError(f"approved photoreal source/policy changed for {origin}")
    barrel = next(row for row in families["families"] if row["family"] == "barrel")
    if barrel["mesh"] != PHOTO_MESH or barrel["fit"] != "none" or not barrel["scripted"] or barrel["yaw_from_sprite"]:
        raise ValueError("global photoreal barrel family binding changed")
    selected = {placements[origin]["screen"] for origin in origins}
    authored = set()
    for path in art.glob("*.json"):
        manifest = json.loads(path.read_bytes())
        if manifest.get("schema") == "dink-art/1":
            authored.update(manifest.get("authored_collision_screens", []))
    if selected & authored:
        raise ValueError(f"fitted generation overlaps authored collision: {selected & authored}")

    extractor = Extractor(data, output, steps=())
    rules = []
    for origin in origins:
        row = placements[origin]
        source = extractor.screen(row["screen"]).sprites[row["index"]]
        expected = (True, 0, 0, row["type"], row["script"], 0, 0, 173, 1,
                    row["map_x"] + 20, row["map_y"])
        keys = ("active", "hard", "prop", "type", "script", "brain", "vision", "seq", "frame", "x", "y")
        if tuple(source[key] for key in keys) != expected or row["class_id"] != "barrel":
            raise ValueError(f"original map.dat placement no longer matches {origin}")
        rules.append(dict(common_rule, origin=origin, source_hash=row["hash"],
                          source_script=row["script"], source_type=row["type"],
                          source_representation=row["representation"]))
    families["collision_fit"] = dict(schema="dink-family-collision-fit/3", origins=rules)

    def hardbox(sprite):
        picture = extractor.seqs.pic_for(sprite["seq"], sprite["frame"])
        return picture.hardbox if picture is not None else None

    gameplay = PROJECT / "Content/Dink/Data/Gameplay"
    layers = {}
    for number in sorted(selected):
        screen = extractor.screen(number)
        sprites = {index: sprite for index, sprite in screen.sprites.items() if 1 <= index <= 99}
        tiles = screen.tiles[:TILES_PER_SCREEN]
        legacy = legacy_sections(gameplay / "Hardness" / f"SCR_{number:03d}.txt")
        # The original base mains set vision to 1 or 2 and force_vision uses 0 or 2.
        # Include those values even when the screen has no corresponding visual variant.
        visions = {0, 1, 2} | {sprite["vision"] for sprite in sprites.values()}
        for vision in sorted(visions):
            packet = runtime_layers(extractor.hard, tiles, sprites, hardbox, vision,
                                    editor_hard_flags=screen.editor_hard_flags)
            base, stamps = decode_runtime_layers(packet, expected_vision=vision)
            codes, owners, _ = original_hard.build_hitmap(extractor.hard, tiles, sprites, hardbox, vision)
            composed = bytearray(base)
            composed_owners = bytearray(len(base))
            for stamp in stamps:
                left, top, right, bottom = stamp["rect"]
                code = original_hard.CODE_WARP if stamp["warp"] else original_hard.CODE_SPRITE
                for y in range(top, bottom):
                    start, end = y * 600 + left, y * 600 + right
                    composed[start:end] = bytes([code]) * (right - left)
                    composed_owners[start:end] = bytes([stamp["owner"]]) * (right - left)
            if composed != codes.tobytes() or composed_owners != owners.tobytes():
                raise ValueError(f"runtime layers differ from original ordered hardness on screen {number}, vision {vision}")
            owner_codes = codes.copy()
            stamped = owners != 0
            owner_codes[stamped] = 100 + owners[stamped]
            legacy_vision = legacy.get(f"vision {vision}", legacy["vision 0"])
            if list(rle_rows(owner_codes)) != legacy_vision:
                raise ValueError(f"runtime owner map differs from deployed legacy screen {number}, vision {vision}")
            suffix = f"_v{vision}" if vision else ""
            name = f"SCR_{number:03d}{suffix}_layers.json"
            encoded = (pretty(packet, expand_levels=1) + "\n").encode()
            installed = gameplay / "Hardness" / name
            if installed.exists() and installed.read_bytes() != encoded:
                raise ValueError(f"generated layer differs from the existing accepted layer {name}")
            layers[name] = encoded

    # All raw inputs and the ordered composition were verified before writing.
    output.mkdir(parents=True)
    game_output = output / "Gameplay"
    write_missing(game_output / "Hardness", layers)
    descriptors = build(bundle, gameplay, selected_screens=selected, layers_root=game_output)
    write_missing(game_output / "Hardness/Foundations", descriptors)
    manifest = json.loads((gameplay / "gameplay_manifest.json").read_bytes())
    manifest["files"].update({f"Hardness/{name}": hashlib.sha256(raw).hexdigest()
                              for name, raw in layers.items()})
    manifest["files"] = dict(sorted(manifest["files"].items()))
    manifest["counts"]["hardness_files"] = sum(name.startswith("Hardness/") for name in manifest["files"])
    write_missing(game_output, {"gameplay_manifest.json": (json.dumps(manifest, indent=2) + "\n").encode()})
    write_missing(output / "Art", {"families.json": (json.dumps(families, indent=2) + "\n").encode()})
    return len(rules), len(selected), len(layers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--data", type=Path, default=PROJECT.parent / "bin/dink")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rules, screens, layers = build_inputs(args.bundle, args.inventory, args.data, args.output)
    print(f"{rules} fitted rules, {screens} foundation descriptors, {layers} verified original hardness layers")
