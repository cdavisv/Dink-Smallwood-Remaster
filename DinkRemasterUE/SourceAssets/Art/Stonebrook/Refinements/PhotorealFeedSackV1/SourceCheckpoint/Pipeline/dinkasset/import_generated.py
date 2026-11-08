"""Bring an image-to-3D mesh (OBJ / GLB / glTF / FBX / PLY / STL) into a convention-compliant .blend.

    blender -b --factory-startup -P tools/blender/dinkasset/import_generated.py -- \
        --input barrel.glb --name SM_Barrel_02 --class prop --height 0.9 --out sources/Props/SM_Barrel_02.blend

What it does, in order (each step is logged in the JSON report):
  import -> drop non-mesh objects -> bake all transforms into one joined mesh -> optional --rotate
  -> scale to the requested real-world --height (Z) or --longest side, in metres
  -> cleanup (merge by distance, loose, degenerate, recalc normals) -> pivot by class rule at the world origin
  -> asset collection + custom properties -> UVs if missing -> materials/images renamed
  -> decimate to the class target if over budget -> collision / LODs if the class needs them
  -> save -> validate.  Exit 0 only if the saved file passes validation.

It never invents art: texture content, topology quality and UV quality still need a human look
(plan section 9). The report says what was automatic.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
from mathutils import Euler, Matrix  # noqa: E402

from dinkasset import common  # noqa: E402
from dinkasset import conventions as C  # noqa: E402
from dinkasset import fix  # noqa: E402
from dinkasset import make_lods  # noqa: E402
from dinkasset import validate  # noqa: E402


def import_file(path):
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    if ext == ".obj":
        # OBJ files from generators are Y-up, -Z forward (the OBJ convention); use --rotate otherwise.
        bpy.ops.wm.obj_import(filepath=path, forward_axis="NEGATIVE_Z", up_axis="Y")
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    else:
        raise SystemExit("unsupported input type %r (use obj, glb, gltf, fbx, ply, stl)" % ext)
    return [o for o in bpy.data.objects if o not in before]


def bake_and_join(objs, log):
    meshes = [o for o in objs if o.type == "MESH"]
    others = [o for o in objs if o.type != "MESH"]
    if not meshes:
        raise SystemExit("no mesh objects found in the input")
    for o in meshes:
        if o.data.users > 1:
            o.data = o.data.copy()
        # bake the full world transform (parents, import rotation, unit scale) into the vertices
        mw = o.matrix_world.copy()
        flip = mw.determinant() < 0
        o.parent = None
        o.data.transform(mw, shape_keys=True)
        if flip:
            o.data.flip_normals()
        o.matrix_world = Matrix.Identity(4)
        o.data.update()
        for m in list(o.modifiers):
            if m.type == "ARMATURE":
                o.modifiers.remove(m)
        o.vertex_groups.clear()
    for o in others:
        bpy.data.objects.remove(o, do_unlink=True)
    if others:
        log.append({"step": "drop_non_mesh", "count": len(others), "types": sorted({o.type for o in others})})
    if len(meshes) > 1:
        common.select_only(meshes)
        bpy.ops.object.join()
        log.append({"step": "join", "objects": len(meshes)})
    ob = bpy.context.view_layer.objects.active if len(meshes) > 1 else meshes[0]
    return ob


def main():
    p = common.make_parser("import_generated.py", __doc__.split("\n")[0])
    p.add_argument("--input", required=True, help="OBJ/GLB/GLTF/FBX/PLY/STL from the generator")
    p.add_argument("--name", required=True, help="asset name, e.g. SM_Barrel_02")
    p.add_argument("--class", dest="cls", required=True, choices=sorted(C.CLASSES))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--height", type=float, help="target height in metres (Z extent)")
    g.add_argument("--longest", type=float, help="target longest side in metres (for flat or long objects)")
    p.add_argument("--out", required=True, help="output .blend")
    p.add_argument("--path", default="", help="%s sub-folder under the class folder" % C.META_PATH)
    p.add_argument("--rotate", type=float, nargs=3, metavar=("X", "Y", "Z"), default=None,
                   help="Euler degrees applied after import, before scaling (fix a lying/rotated generator output)")
    p.add_argument("--source", default="", help="ledger note: generator, model, licence, prompt id")
    p.add_argument("--merge-distance", type=float, default=1e-5)
    p.add_argument("--no-uv", action="store_true", help="do not auto-unwrap when UVs are missing")
    p.add_argument("--no-decimate", action="store_true", help="do not decimate over-budget meshes")
    p.add_argument("--no-collision", action="store_true")
    p.add_argument("--no-lods", action="store_true")
    args = p.parse_args(common.script_argv())
    if not C.ASSET_NAME_RE.match(args.name):
        raise SystemExit("--name %r does not match the SM_/SK_ naming rule" % args.name)
    cls = C.CLASSES[args.cls]
    if cls["kind"] != "static":
        raise SystemExit("import_generated.py makes static meshes; skeletal classes need a rig (see CONVENTIONS.md)")
    if not args.name.startswith(C.STATIC_PREFIX + "_"):
        raise SystemExit("static classes need the SM_ prefix")

    log = []
    common.reset_scene()
    src = os.path.abspath(args.input)
    objs = import_file(src)
    log.append({"step": "import", "file": src, "objects": len(objs)})
    ob = bake_and_join(objs, log)
    ob.name = args.name
    ob.data.name = args.name
    if args.rotate:
        e = Euler([math.radians(v) for v in args.rotate], "XYZ")
        ob.data.transform(e.to_matrix().to_4x4())
        log.append({"step": "rotate", "degrees": args.rotate})
    # asset collection
    coll = bpy.data.collections.new(args.name)
    bpy.context.scene.collection.children.link(coll)
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    common.set_meta(coll, args.cls, args.path or None)
    if args.source:
        coll[C.META_SOURCE] = args.source
    a = common.Asset(coll)
    flog = fix.Log()
    # scale to real-world size
    mn, mx = common.world_bounds(ob)
    size = mx - mn
    before = [round(v, 4) for v in size]
    if args.height:
        f = args.height / size.z if size.z > 1e-9 else 1.0
    else:
        f = args.longest / max(size) if max(size) > 1e-9 else 1.0
    fix.scale_asset(a, f, flog, "height" if args.height else "longest")
    log.append({"step": "scale", "factor": f, "size_before_m": before,
                "size_after_m": [round(v * f, 4) for v in size]})
    # cleanup
    fix.fix_merge(a, args.merge_distance, flog)
    fix.fix_loose(a, flog)
    fix.fix_degenerate(a, flog)
    fix.fix_loose(a, flog)
    fix.fix_normals(a, flog)
    # pivot at the world origin
    d = fix.pivot_delta(a)
    if d is not None:
        common.shift_pivot([ob], d)
    ob.location = (0, 0, 0)
    flog.add("set_pivot", a.name, "pivot rule %s, origin at world origin" % cls["pivot"])
    # materials
    if not ob.data.materials:
        mat = bpy.data.materials.new("Material")
        ob.data.materials.append(mat)
        flog.add("materials", a.name, "mesh had no material: added a placeholder")
    fix.fix_materials(a, flog)
    # UVs
    if not args.no_uv:
        fix.fix_uvs(a, flog)
    fix.fix_rename(a, args.name, flog)
    # budget
    tris = common.tri_count(ob)
    target, hard = cls["tris"]
    if tris > hard and not args.no_decimate:
        got = make_lods.decimate_object(ob, target, ("MATERIAL",))
        flog.add("decimate", a.name, "%d triangles exceeded the %d budget: collapsed to %d (target %d). Re-topologise by hand for final art."
                 % (tris, hard, got, target))
    a.refresh()
    # collision and LODs
    if cls["collision"] and not args.no_collision:
        for e in make_lods.make_collision(a, "auto"):
            flog.add("collision", a.name, e.get("name") or e.get("why", ""), **{k: v for k, v in e.items() if k in ("mode", "vertices")})
    need_lods = C.lods_required(args.cls, coll.get(C.META_NANITE), bool(coll.get(C.META_TRANSLUCENT, 0)))
    if need_lods > 1 and not args.no_lods:
        for e in make_lods.make_lods(a, list(cls["lod_ratios"] or C.LOD_RATIOS_STANDARD)):
            flog.add("lods", a.name, e.get("name") or e.get("why", ""), tris=e.get("tris"))
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    v = validate.validate_scene([coll.name])
    report = {"tool": "import_generated", "ok": True, "saved": out, "asset": a.name, "class": args.cls,
              "steps": log, "fixes": flog.items, "compliant": v["passed"], "validation": v}
    common.emit(report, args.report)
    common.finish(0 if v["passed"] else 1)


if __name__ == "__main__":
    main()
