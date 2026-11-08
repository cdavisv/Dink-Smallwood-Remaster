"""Safe, opt-in, logged fixes for the usual faults of generated and imported meshes.

    blender -b --factory-startup -P tools/blender/dinkasset/fix.py -- \
        --blend in.blend --output out.blend [--collection NAME] <fix flags>

Every fix is a flag; nothing runs by default. --all-safe turns on the fixes that cannot change
how an asset looks (apply transforms, merge by distance, remove loose/degenerate, recalc normals,
prune/merge material slots, set pivot). Not part of --all-safe because they need a decision:
--fix-units, --scale/--height/--longest, --add-uvs, --rename, --set-class.

Triangulation is deliberately NOT a fix: the source keeps quads, export_ue.py triangulates on export.
Skeletal assets: only the mesh-data fixes run; transforms and pivot of rigs are reported, not changed.
"""
import math
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from dinkasset import common  # noqa: E402
from dinkasset import conventions as C  # noqa: E402

GENERIC_MAT = re.compile(r"^(Material|Mat|Default|None|Untitled|material)[_.\-\s]*\d*$")


class Log:
    def __init__(self):
        self.items = []

    def add(self, fix, asset, detail, obj=None, **data):
        e = {"fix": fix, "asset": asset, "detail": detail}
        if obj is not None:
            e["object"] = obj if isinstance(obj, str) else obj.name
        e.update(data)
        self.items.append(e)


# --- individual fixes ---------------------------------------------------------------------------------

def fix_units(log):
    us = bpy.context.scene.unit_settings
    f = us.scale_length
    if abs(f - 1.0) < 1e-9 and us.system == "METRIC":
        return
    for ob in bpy.context.scene.objects:
        if ob.type == "ARMATURE":
            log.add("fix_units", None, "armature %r not rescaled (rigs must be fixed by hand)" % ob.name, obj=ob)
            continue
        if ob.type == "MESH":
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            ob.data.transform(Matrix.Scale(f, 4))
        ob.location = ob.location * f
    us.system = "METRIC"
    us.scale_length = 1.0
    us.length_unit = "METERS"
    log.add("fix_units", None, "scene unit scale %g -> 1.0; geometry and locations multiplied by %g so real sizes are kept" % (f, f))


def fix_apply_transforms(a, log):
    if a.armatures:
        for ob in a.armatures + a.renders:
            rot, scl, neg = common.transforms_dirty(ob)
            if rot or scl or neg:
                log.add("apply_transforms", a.name, "skeletal asset: %r has unapplied transforms; fix the rig by hand" % ob.name, obj=ob)
        return
    for ob in a.all_objects():
        if ob.type != "MESH":
            continue
        if ob.parent is not None and common.unparent_keep_world(ob):
            log.add("apply_transforms", a.name, "unparented, world transform kept", obj=ob)
        before = (tuple(round(v, 5) for v in ob.matrix_basis.to_scale()),
                  tuple(round(math.degrees(v), 3) for v in ob.matrix_basis.to_euler()))
        if common.apply_rotation_scale(ob):
            log.add("apply_transforms", a.name, "applied scale %s rotation(deg) %s" % before, obj=ob)
    for ob in a.sockets:
        if ob.parent is not None:
            common.unparent_keep_world(ob)


def _dup_face_delete(bm):
    seen = {}
    dup = []
    for f in bm.faces:
        key = frozenset(v.index for v in f.verts)
        if key in seen:
            dup.append(f)
        else:
            seen[key] = f
    if dup:
        bmesh.ops.delete(bm, geom=dup, context="FACES_ONLY")
    return len(dup)


def fix_merge(a, dist, log):
    for ob in a.renders:
        with common.bmesh_of(ob) as bm:
            bm.verts.index_update()
            n0 = len(bm.verts)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
            bm.verts.index_update()
            dupf = _dup_face_delete(bm)
            merged = n0 - len(bm.verts)
            if merged or dupf:
                bm.to_mesh(ob.data)
                ob.data.update()
                log.add("merge_distance", a.name, "merged %d vertices within %g m, removed %d duplicate faces" % (merged, dist, dupf), obj=ob)


def fix_loose(a, log):
    for ob in a.renders:
        with common.bmesh_of(ob) as bm:
            wire = [e for e in bm.edges if not e.link_faces]
            if wire:
                bmesh.ops.delete(bm, geom=wire, context="EDGES")
            verts = [v for v in bm.verts if not v.link_edges]
            if verts:
                bmesh.ops.delete(bm, geom=verts, context="VERTS")
            if wire or verts:
                bm.to_mesh(ob.data)
                ob.data.update()
                log.add("remove_loose", a.name, "removed %d loose vertices and %d wire edges" % (len(verts), len(wire)), obj=ob)


def fix_degenerate(a, log):
    for ob in a.renders:
        with common.bmesh_of(ob) as bm:
            before = len(bm.faces)
            bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
            zero = [f for f in bm.faces if f.calc_area() < 1e-8]
            if zero:
                bmesh.ops.delete(bm, geom=zero, context="FACES")
            lonely = [v for v in bm.verts if not v.link_edges]
            if lonely:
                bmesh.ops.delete(bm, geom=lonely, context="VERTS")
            removed = before - len(bm.faces)
            if removed:
                bm.to_mesh(ob.data)
                ob.data.update()
                log.add("remove_degenerate", a.name, "removed %d zero-area faces" % removed, obj=ob)


def fix_normals(a, log):
    for ob in a.renders:
        with common.bmesh_of(ob) as bm:
            if not bm.faces:
                continue
            before = [tuple(f.normal) for f in bm.faces]
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.normal_update()
            changed = sum(1 for f, b in zip(bm.faces, before) if Vector(b).dot(f.normal) < 0)
            closed = all(len(e.link_faces) == 2 for e in bm.edges)
            if closed and bm.calc_volume(signed=True) < 0:
                bmesh.ops.reverse_faces(bm, faces=bm.faces)
                changed = len(bm.faces) - changed
            if changed:
                bm.to_mesh(ob.data)
                ob.data.update()
                log.add("recalc_normals", a.name, "flipped %d faces to a consistent outward direction" % changed, obj=ob)


def _remap_slots(ob, keep_map):
    """keep_map: {old slot index: new slot index}. Rebuild material list and polygon indices."""
    me = ob.data
    mats = [s.material for s in ob.material_slots]
    new_len = max(keep_map.values()) + 1 if keep_map else 0
    new_mats = [None] * new_len
    for old, new in keep_map.items():
        new_mats[new] = mats[old]
    import array
    idx = array.array("i", [0]) * len(me.polygons)
    me.polygons.foreach_get("material_index", idx)
    for i in range(len(idx)):
        idx[i] = keep_map.get(idx[i], 0)
    me.materials.clear()
    for m in new_mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", idx)
    me.update()


def fix_materials(a, log):
    for ob in a.renders:
        # 1. point ".001" duplicates back at the original
        for s in ob.material_slots:
            m = s.material
            if m is None:
                continue
            mm = re.match(r"^(.*)\.\d{3}$", m.name)
            if mm and mm.group(1) in bpy.data.materials and bpy.data.materials[mm.group(1)] is not m:
                log.add("merge_materials", a.name, "%s -> %s" % (m.name, mm.group(1)), obj=ob)
                s.material = bpy.data.materials[mm.group(1)]
        # 2. collapse identical slots, drop unused ones
        slots = [s.material for s in ob.material_slots]
        if not slots:
            continue
        used = {p.material_index for p in ob.data.polygons}
        keep_map = {}
        first_of = {}
        for i, m in enumerate(slots):
            if i not in used:
                continue
            key = m.name if m else None
            if key is not None and key in first_of:
                keep_map[i] = keep_map[first_of[key]]
            else:
                keep_map[i] = len(set(keep_map.values()))
                first_of[key] = i
        if not keep_map:
            continue
        if len(set(keep_map.values())) != len(slots):
            _remap_slots(ob, keep_map)
            log.add("prune_slots", a.name, "material slots %d -> %d" % (len(slots), len(ob.material_slots)), obj=ob)


def fix_uvs(a, log):
    for ob in a.renders:
        if len(ob.data.uv_layers) == 0:
            common.select_only([ob])
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
            bpy.ops.object.mode_set(mode="OBJECT")
            log.add("add_uvs", a.name, "smart UV project (automatic; unwrap by hand for hero assets)", obj=ob)


def scale_asset(a, factor, log, fix="scale"):
    """Uniformly scale every mesh (and socket) of the asset about the object origin."""
    if abs(factor - 1.0) < 1e-9:
        return
    for ob in a.all_objects():
        if ob.type == "MESH":
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            ob.data.transform(Matrix.Scale(factor, 4))
            ob.data.update()
        elif ob.type == "EMPTY":
            ob.location = ob.location * factor
    log.add(fix, a.name, "scaled by %.6g" % factor)


def fix_scale(a, args, log):
    if a.armatures:
        log.add("scale", a.name, "skeletal asset: scale the rig by hand")
        return
    lod0 = a.lod0()
    if lod0 is None:
        return
    mn, mx = common.world_bounds(lod0)
    size = mx - mn
    f = None
    if args.scale:
        f = args.scale
    elif args.height:
        f = args.height / size.z if size.z > 1e-9 else None
    elif args.longest:
        f = args.longest / max(size) if max(size) > 1e-9 else None
    if f:
        scale_asset(a, f, log, "scale" if args.scale else ("height" if args.height else "longest"))


def pivot_delta(a):
    """Vector (world) by which the pivot must move so the class rule holds, or None."""
    lod0 = a.lod0()
    cls = a.cls
    if lod0 is None or cls is None:
        return None
    mn, mx = common.world_bounds(lod0)
    origin = lod0.matrix_world.translation
    rmn, rmx = mn - origin, mx - origin
    rule = cls["pivot"]
    if rule == "grip":
        sock = [s for s in a.sockets if s.name == "SOCKET_Grip"]
        return (sock[0].matrix_world.translation - origin) if sock else None
    return common.pivot_target(rule, rmn, rmx)


def fix_pivot(a, log):
    if a.armatures:
        log.add("set_pivot", a.name, "skeletal asset: move the armature origin by hand (feet at z=0)")
        return
    d = pivot_delta(a)
    if d is None:
        log.add("set_pivot", a.name, "cannot determine pivot (class %s, rule needs a socket?)" % a.cls_name)
        return
    if d.length < 1e-5:
        return
    common.shift_pivot([o for o in a.all_objects() if o.type in ("MESH",)], d)
    for s in a.sockets:
        s.location = s.location - d  # sockets keep their world position
    log.add("set_pivot", a.name, "origin moved by (%.2f, %.2f, %.2f) cm for rule %s" % (d.x * 100, d.y * 100, d.z * 100, a.cls["pivot"]))


# --- naming -----------------------------------------------------------------------------------------------

def texture_roles(mat):
    """{image: suffix} by tracing Principled BSDF inputs back to image nodes (best effort)."""
    roles = {}
    if not mat or not mat.use_nodes or not mat.node_tree:
        return roles

    def upstream_image(sock, depth=0):
        if depth > 6:
            return None
        for link in sock.links:
            n = link.from_node
            if n.type == "TEX_IMAGE" and n.image:
                return n.image
            for inp in n.inputs:
                if inp.is_linked:
                    r = upstream_image(inp, depth + 1)
                    if r:
                        return r
        return None

    for n in mat.node_tree.nodes:
        if n.type != "BSDF_PRINCIPLED":
            continue
        for sock_name, suffix in (("Base Color", "BC"), ("Normal", "N"), ("Roughness", "ORM"), ("Metallic", "ORM"),
                                  ("Emission Color", "E"), ("Alpha", "MSK")):
            sock = n.inputs.get(sock_name)
            if sock is not None and sock.is_linked:
                img = upstream_image(sock)
                if img is not None and img not in roles:
                    roles[img] = suffix
    return roles


def valid_asset_name(raw, kind, explicit=None):
    prefix = C.SKELETAL_PREFIX if kind == "skeletal" else C.STATIC_PREFIX
    if explicit:
        return explicit
    base = re.sub(r"^(SM|SK)_", "", raw)
    return "%s_%s" % (prefix, common.clean_name(base))


def fix_rename(a, explicit, log):
    cls = a.cls
    kind = cls["kind"] if cls else "static"
    new = valid_asset_name(a.name, kind, explicit)
    if not C.ASSET_NAME_RE.match(new):
        log.add("rename", a.name, "refusing to rename to invalid name %r" % new)
        return
    old = a.name
    lod0 = a.lod0()
    lods = a.lods()
    chain = any(n > 0 for n in lods) or any(C.LOD_RE.match(o.name) for o in a.renders)
    # collision first (they reference the LOD0 name)
    old_lod0 = lod0.name if lod0 else None
    new_lod0 = ("%s_LOD0" % new) if chain else new
    for n, objs in sorted(lods.items()):
        for ob in objs:
            nn = "%s_LOD%d" % (new, n) if chain else new
            if ob.name != nn:
                ob.name = nn
                ob.data.name = nn
    for i, col in enumerate(sorted(a.collision, key=lambda o: o.name), start=1):
        nn = "UCX_%s_%02d" % (new_lod0, i)
        if col.name != nn:
            col.name = nn
            col.data.name = nn
    if a.armatures and len(a.armatures) == 1 and not a.armatures[0].name.startswith(new):
        a.armatures[0].name = new + "_Armature"
        a.armatures[0].data.name = new + "_Armature"
    if a.coll.name != new:
        a.coll.name = new
        a.name = new
    # materials
    base = new[3:]
    seen = set()
    idx = 0
    for ob in a.renders:
        for s in ob.material_slots:
            m = s.material
            if m is None or m.name in seen or C.MATERIAL_NAME_RE.match(m.name):
                continue
            seen.add(m.name)
            idx += 1
            if GENERIC_MAT.match(m.name):
                nn = "MI_%s_%02d" % (base, idx)
            else:
                nn = "MI_" + common.clean_name(re.sub(r"^(M|MI)_", "", m.name))
            if nn in bpy.data.materials and bpy.data.materials[nn] is not m:
                nn = "MI_%s_%02d" % (base, idx)
            log.add("rename", a.name, "material %s -> %s" % (m.name, nn))
            m.name = nn
    # textures by role
    for ob in a.renders[:1]:
        for s in ob.material_slots:
            for img, suf in texture_roles(s.material).items():
                if C.TEXTURE_NAME_RE.match(img.name):
                    continue
                matpart = re.sub(r"^MI_", "", s.material.name)
                nn = "T_%s_%s" % (matpart, suf)
                if nn in bpy.data.images and bpy.data.images[nn] is not img:
                    continue
                log.add("rename", a.name, "image %s -> %s" % (img.name, nn))
                img.name = nn
    asset_new = a.name
    if old != asset_new:
        log.add("rename", old, "asset %s -> %s (objects, mesh data, collision renamed to match)" % (old, asset_new))
    a.refresh()


def fix_set_class(a, cls_name, path, log):
    if cls_name not in C.CLASSES:
        raise SystemExit("unknown class %r; valid: %s" % (cls_name, ", ".join(sorted(C.CLASSES))))
    common.set_meta(a.coll, cls_name, path)
    a.cls_name = cls_name
    log.add("set_class", a.name, "%s = %s%s" % (C.META_CLASS, cls_name, (", path " + path) if path else ""))


# --- driver ---------------------------------------------------------------------------------------------

def run_fixes(assets, args, log):
    for a in assets:
        if args.set_class:
            fix_set_class(a, args.set_class, args.path, log)
    if args.fix_units:
        fix_units(log)
    for a in assets:
        a.refresh()
        if args.apply_transforms:
            fix_apply_transforms(a, log)
        if args.scale or args.height or args.longest:
            fix_scale(a, args, log)
        if args.merge_distance:
            fix_merge(a, args.merge_distance, log)
        if args.remove_loose:
            fix_loose(a, log)
        if args.remove_degenerate:
            fix_degenerate(a, log)
            if args.remove_loose:
                fix_loose(a, log)
        if args.recalc_normals:
            fix_normals(a, log)
        if args.prune_slots:
            fix_materials(a, log)
        if args.add_uvs:
            fix_uvs(a, log)
        if args.set_pivot:
            if a.cls is None:
                log.add("set_pivot", a.name, "skipped: no class (use --set-class)")
            else:
                fix_pivot(a, log)
        if args.rename:
            fix_rename(a, args.name, log)


def main():
    p = common.make_parser("fix.py", __doc__.split("\n")[0])
    p.add_argument("--class", dest="default_class", help="class for assets without %s" % C.META_CLASS)
    g = p.add_argument_group("fixes (all opt-in)")
    g.add_argument("--all-safe", action="store_true", help="apply-transforms, merge-distance, remove-loose, remove-degenerate, recalc-normals, prune-slots, set-pivot")
    g.add_argument("--fix-units", action="store_true", help="scene units -> metric 1.0, keeping real sizes")
    g.add_argument("--apply-transforms", action="store_true")
    g.add_argument("--scale", type=float, help="multiply asset size by this factor")
    g.add_argument("--height", type=float, help="scale uniformly so LOD0 is this many metres tall (Z)")
    g.add_argument("--longest", type=float, help="scale uniformly so the longest side is this many metres")
    g.add_argument("--merge-distance", type=float, nargs="?", const=1e-5, metavar="M", help="merge vertices closer than M metres (default 1e-5)")
    g.add_argument("--remove-loose", action="store_true")
    g.add_argument("--remove-degenerate", action="store_true")
    g.add_argument("--recalc-normals", action="store_true")
    g.add_argument("--prune-slots", action="store_true", help="drop unused material slots, merge duplicates (.001)")
    g.add_argument("--add-uvs", action="store_true", help="smart-project UVs where a mesh has none")
    g.add_argument("--set-pivot", action="store_true", help="move the origin to the class rule position")
    g.add_argument("--rename", action="store_true", help="rename collection, objects, mesh data, collision, materials to the convention")
    g.add_argument("--name", help="explicit asset name for --rename (single asset)")
    g.add_argument("--set-class", help="set %s on the selected collections" % C.META_CLASS)
    g.add_argument("--path", help="with --set-class: %s sub-folder" % C.META_PATH)
    p.add_argument("--validate", action="store_true", help="run the validator afterwards and include its report")
    o = p.add_mutually_exclusive_group(required=True)
    o.add_argument("--output")
    o.add_argument("--inplace", action="store_true")
    args = p.parse_args(common.script_argv())
    if args.all_safe:
        args.apply_transforms = args.remove_loose = args.remove_degenerate = True
        args.recalc_normals = args.prune_slots = args.set_pivot = True
        args.merge_distance = args.merge_distance or 1e-5
    try:
        path = common.open_blend(args.blend)
    except (RuntimeError, SystemExit) as e:
        common.emit({"tool": "fix", "ok": False, "fatal": str(e)}, args.report)
        common.finish(2)
    out = path if args.inplace else os.path.abspath(args.output)
    assets = common.find_assets(only=args.collection, default_class=args.default_class)
    if args.set_class and not assets and len(bpy.data.collections) == 1:
        assets = common.find_assets(only=[bpy.data.collections[0].name])
    log = Log()
    run_fixes(assets, args, log)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    report = {"tool": "fix", "ok": True, "saved": out, "assets": [a.name for a in assets], "fixes": log.items}
    code = 0
    if args.validate:
        from dinkasset import validate
        v = validate.validate_scene(args.collection and [a.name for a in assets] or (), args.default_class)
        report["validation"] = v
        code = 0 if v["passed"] else 1
    common.emit(report, args.report)
    common.finish(code)


if __name__ == "__main__":
    main()
