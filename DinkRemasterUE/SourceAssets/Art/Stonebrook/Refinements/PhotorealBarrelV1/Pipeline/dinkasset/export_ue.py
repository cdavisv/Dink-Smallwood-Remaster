"""Batch-export asset collections to FBX (+ glTF) for Unreal, with a JSON manifest.

    blender -b --factory-startup -P tools/blender/dinkasset/export_ue.py -- \
        --blend in.blend [--out tools/blender/out/export] [--formats fbx,gltf] [--collection NAME] [--force]

Output tree mirrors the Unreal content path, one file per asset:
    <out>/Game/Dink/<Folder>[/<dink_path>]/<Asset>.fbx          (+ .glb, + Textures/*)
    <out>/manifest.json                                         (merged across runs by asset name)

Assets are validated first; failing assets are rejected (listed in the report, exit code 1) unless
--force. Everything is exported with the asset placed at the world origin (the pivot is the origin).

FBX settings and the reasons for them are in CONVENTIONS.md section 2. Short version: metres in
Blender, FBX unit header in metres (UnitScaleFactor 100, so Unreal converts to cm), object scale 1,
axes untouched (Z up, front = -Y, identical to Blender), triangulated, face smoothing groups, no leaf
bones, no animation. glTF: LOD0 only, Y-up per the glTF spec, no collision.
"""
import datetime
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from dinkasset import common  # noqa: E402
from dinkasset import conventions as C  # noqa: E402
from dinkasset import fix  # noqa: E402
from dinkasset import validate  # noqa: E402

FBX_SCALE_MODES = {"all": "FBX_SCALE_ALL", "local": "FBX_SCALE_NONE", "units": "FBX_SCALE_UNITS"}
MANIFEST_VERSION = 1


def content_dir(a):
    return C.content_path(a.cls_name, a.name, a.meta(C.META_PATH, "")).lstrip("/")


class unhidden:
    """Temporarily make objects selectable/visible so the exporters see them."""

    def __init__(self, objs):
        self.objs = objs

    def __enter__(self):
        self.state = [(o, o.hide_get(), o.hide_viewport, o.hide_select) for o in self.objs]
        for o in self.objs:
            o.hide_viewport = False
            o.hide_select = False
            o.hide_set(False)

    def __exit__(self, *exc):
        for o, h, hv, hs in self.state:
            o.hide_set(h)
            o.hide_viewport = hv
            o.hide_select = hs


class renamed_armature:
    """Optionally export the armature object under a fixed name (see CONVENTIONS.md)."""

    def __init__(self, a, name):
        self.arm = a.armatures[0] if a.armatures and name else None
        self.name = name

    def __enter__(self):
        if self.arm is None:
            return
        self.old = self.arm.name
        clash = bpy.data.objects.get(self.name)
        self.clash = clash
        if clash and clash is not self.arm:
            self.clash_old = clash.name
            clash.name = clash.name + "__tmp"
        self.arm.name = self.name

    def __exit__(self, *exc):
        if self.arm is None:
            return
        self.arm.name = self.old
        if self.clash and self.clash is not self.arm:
            self.clash.name = self.clash_old


def export_fbx(a, path, scale_mode, arm_name):
    objs = a.renders + a.collision + a.armatures + a.sockets
    common.select_only(objs)
    with renamed_armature(a, arm_name):
        bpy.ops.export_scene.fbx(
            filepath=path, use_selection=True, object_types={"MESH", "ARMATURE", "EMPTY"},
            use_mesh_modifiers=True, mesh_smooth_type="FACE", use_triangles=True, use_tspace=False,
            use_custom_props=False, colors_type="NONE",
            apply_unit_scale=True, global_scale=1.0, apply_scale_options=FBX_SCALE_MODES[scale_mode],
            axis_forward="Y", axis_up="Z", bake_space_transform=False, use_space_transform=True,
            add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
            use_armature_deform_only=False, armature_nodetype="NULL",
            bake_anim=False, path_mode="STRIP", embed_textures=False, batch_mode="OFF")


def export_gltf(a, path):
    lod0 = a.lod0()
    objs = [lod0] + a.armatures
    common.select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=not any(
            o.data.shape_keys for o in objs if o.type == "MESH"),
        export_yup=True, export_materials="EXPORT", export_image_format="AUTO",
        export_cameras=False, export_lights=False, export_animations=False, export_skins=True,
        export_texcoords=True, export_normals=True, export_tangents=False, export_extras=False)


def export_textures(a, dest_dir, log):
    """Copy/save every image used by the asset's materials. Returns [{name, file, role}]."""
    out = []
    seen = set()
    for ob in a.renders[:1]:
        for s in ob.material_slots:
            mat = s.material
            if not mat or not mat.use_nodes or not mat.node_tree:
                continue
            roles = fix.texture_roles(mat)
            for node in mat.node_tree.nodes:
                if node.type != "TEX_IMAGE" or node.image is None or node.image.name in seen:
                    continue
                img = node.image
                seen.add(img.name)
                os.makedirs(dest_dir, exist_ok=True)
                src = bpy.path.abspath(img.filepath) if img.filepath else ""
                ext = os.path.splitext(src)[1] or ".png"
                dest = os.path.join(dest_dir, img.name + (ext if os.path.exists(src) and not img.packed_file else ".png"))
                try:
                    if os.path.exists(src) and not img.packed_file:
                        shutil.copyfile(src, dest)
                    else:
                        tmp = img.copy()
                        tmp.filepath_raw = dest
                        tmp.file_format = "PNG"
                        tmp.save()
                        bpy.data.images.remove(tmp)
                    out.append({"name": img.name, "file": os.path.basename(dest), "role": roles.get(img),
                                "size": [img.size[0], img.size[1]],
                                "srgb": roles.get(img) in ("BC", "E"),
                                "normal_green_flip": roles.get(img) == "N"})
                except Exception as e:  # noqa: BLE001
                    log.append({"warning": "texture %s not exported: %s" % (img.name, e)})
    return out


def manifest_entry(a, rel, source_rel, source_hash, tex, scale_mode, vreport):
    cls = a.cls
    translucent = bool(a.meta(C.META_TRANSLUCENT, 0))
    nanite = C.nanite_enabled(a.cls_name, a.meta(C.META_NANITE), translucent)
    lod0 = a.lod0()
    origin = validate._origin_for_pivot(a)
    # bounds are of the LOD0 mesh relative to the pivot
    mn, mx = common.world_bounds(lod0)
    tris = {"LOD%d" % n: common.tri_count(objs[0]) for n, objs in sorted(a.lods().items())}
    skeleton = None
    if a.armatures:
        arm = a.armatures[0]
        skeleton = {"armature_object": arm.name, "bones": len(arm.data.bones),
                    "unreal_skeleton_asset": C.SKELETON_ASSET.get(cls.get("skeleton")),
                    "type": cls.get("skeleton")}
    mats = []
    for s in lod0.material_slots:
        mats.append(s.material.name if s.material else None)
    return {
        "name": a.name,
        "class": a.cls_name,
        "kind": cls["kind"],
        "content_path": C.content_path(a.cls_name, a.name, a.meta(C.META_PATH, "")),
        "files": {k: v for k, v in rel.items() if v},
        "source": {"blend": source_rel, "sha256": source_hash, "collection": a.coll.name,
                   "note": a.meta(C.META_SOURCE)},
        "tris": tris,
        "lod_count": len(tris),
        "bounds_cm": common.bounds_report(mn, mx, origin),
        "pivot_rule": cls["pivot"],
        "nanite": nanite,
        "translucent": translucent,
        "collision": [o.name for o in a.collision],
        "material_slots": mats,
        "textures": tex,
        "skeleton": skeleton,
        "sockets": [{"name": s.name,
                     "location_cm_blender": common.to_cm(s.matrix_world.translation - origin)} for s in a.sockets],
        "validation": {"errors": vreport["errors"], "warnings": vreport["warnings"], "forced": False},
        # Contract for the future Unreal import script. Documentation-derived, NOT editor-verified.
        "import_hints": {
            "fbx_scale_mode": scale_mode,
            "import_uniform_scale": 1.0,
            "convert_scene": True,
            "force_front_x_axis": False,
            "unreal_front_axis": "+Y",
            "generate_lightmap_uvs": False,
            "build_nanite": nanite,
            "normal_import": "import_normals",
            "use_custom_collision": bool(a.collision),
            "combine_meshes": True,
            "texture_normal_flip_green": True,
            "texture_orm_compression": "Masks (no sRGB)",
        },
    }


def export_asset(a, vreport, out_root, formats, scale_mode, source_rel, source_hash, no_textures, arm_name, forced):
    base_rel = content_dir(a)
    folder = os.path.join(out_root, *base_rel.split("/")[:-1])
    os.makedirs(folder, exist_ok=True)
    rel = {"fbx": None, "glb": None}
    log = []
    with unhidden(a.all_objects()), common.at_origin(a):
        if "fbx" in formats:
            p = os.path.join(folder, a.name + ".fbx")
            export_fbx(a, p, scale_mode, arm_name)
            rel["fbx"] = os.path.relpath(p, out_root).replace(os.sep, "/")
        if "gltf" in formats:
            p = os.path.join(folder, a.name + ".glb")
            export_gltf(a, p)
            rel["glb"] = os.path.relpath(p, out_root).replace(os.sep, "/")
        tex = []
        if not no_textures:
            tex = export_textures(a, os.path.join(folder, "Textures"), log)
            for t in tex:
                t["file"] = os.path.relpath(os.path.join(folder, "Textures", t["file"]), out_root).replace(os.sep, "/")
        entry = manifest_entry(a, rel, source_rel, source_hash, tex, scale_mode, vreport)
    entry["validation"]["forced"] = forced
    if log:
        entry["warnings"] = log
    return entry


def main():
    p = common.make_parser("export_ue.py", __doc__.split("\n")[0])
    p.add_argument("--out", default=os.path.join(common.DEFAULT_OUT, "export"), help="export root (default tools/blender/out/export)")
    p.add_argument("--formats", default="fbx,gltf", help="comma list of fbx,gltf")
    p.add_argument("--class", dest="default_class")
    p.add_argument("--force", action="store_true", help="export assets that fail validation")
    p.add_argument("--fbx-scale-mode", choices=sorted(FBX_SCALE_MODES), default="all",
                   help="FBX 'Apply Scalings' mode (default all = FBX All, unit header in metres)")
    p.add_argument("--no-textures", action="store_true")
    p.add_argument("--source-root", help="record the .blend path relative to this directory in the manifest")
    p.add_argument("--armature-export-name", help="export the armature object under this name (see CONVENTIONS.md, verify in editor)")
    args = p.parse_args(common.script_argv())
    try:
        path = common.open_blend(args.blend)
    except (RuntimeError, SystemExit) as e:
        common.emit({"tool": "export", "ok": False, "fatal": str(e)}, args.report)
        common.finish(2)
    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    for f in formats:
        if f not in ("fbx", "gltf"):
            raise SystemExit("unknown format %r" % f)
    out_root = os.path.abspath(args.out)
    os.makedirs(out_root, exist_ok=True)
    source_hash = common.sha256_file(path)
    source_rel = os.path.relpath(path, args.source_root) if args.source_root else os.path.basename(path)
    only = args.collection
    vscene = validate.validate_scene(only, args.default_class)
    vby = {r["name"]: r for r in vscene["assets"]}
    assets = common.find_assets(only=only, default_class=args.default_class)
    entries, rejected = [], []
    for a in assets:
        v = vby.get(a.name)
        if v is None or a.cls is None:
            rejected.append({"name": a.name, "reason": "no valid class", "errors": []})
            continue
        if v["errors"] and not args.force:
            rejected.append({"name": a.name, "reason": "validation errors",
                             "errors": [f["code"] + ": " + f["message"] for f in v["findings"] if f["severity"] == "error"]})
            continue
        entries.append(export_asset(a, v, out_root, formats, args.fbx_scale_mode, source_rel, source_hash,
                                    args.no_textures, args.armature_export_name, bool(v["errors"])))
    # merge into the manifest of previous runs
    mpath = os.path.join(out_root, "manifest.json")
    merged = {}
    if os.path.exists(mpath):
        try:
            with open(mpath) as f:
                for e in json.load(f).get("assets", []):
                    merged[e["name"]] = e
        except (ValueError, KeyError):
            pass
    for e in entries:
        merged[e["name"]] = e
    manifest = {
        "schema_version": MANIFEST_VERSION,
        "generator": "tools/blender/dinkasset/export_ue.py",
        "blender": bpy.app.version_string,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "units": {"blender_unit": "metre", "unreal_unit": "centimetre", "multiplier": C.UNIT_TO_CM},
        "axes": {"blender": "Z up, asset front faces -Y",
                 "fbx_file": "Z up, front axis -Y (same as Blender), right-handed, no rotation baked",
                 "unreal_asset_space": "Z up, asset front faces +Y; Unreal negates Y on import (documentation-derived, verify in editor)"},
        "content_root": C.CONTENT_ROOT,
        "assets": sorted(merged.values(), key=lambda e: e["content_path"]),
    }
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    report = {"tool": "export", "ok": not rejected, "out": out_root, "manifest": mpath,
              "exported": [{"name": e["name"], "files": e["files"], "tris": e["tris"]} for e in entries],
              "rejected": rejected}
    common.emit(report, args.report)
    common.finish(0 if not rejected else 1)


if __name__ == "__main__":
    main()
