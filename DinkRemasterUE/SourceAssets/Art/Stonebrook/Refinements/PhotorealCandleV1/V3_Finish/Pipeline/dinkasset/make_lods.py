"""Generate LOD chains and simple convex UCX_ collision for asset collections.

    blender -b --factory-startup -P tools/blender/dinkasset/make_lods.py -- \
        --blend in.blend --output out.blend [--lods] [--collision [MODE]] [options]

LOD chain: LOD0 is decimated (collapse) to LOD_RATIOS of its triangle count, each LOD built from
LOD0 (not cascaded). Defaults per class come from conventions.CLASSES[...]["lod_ratios"]; for
Nanite classes nothing is generated unless --force. LOD0 is renamed <asset>_LOD0 and its collision
is renamed with it.

Collision: UCX_<LOD0 mesh name>_NN convex hulls.
  hull  one hull of the whole mesh (props)
  grid  clip the mesh into --cell sized cells, merge occupied cells into boxes, one hull per box
        (modular kit pieces: keeps door openings open)
  box   one axis-aligned box (UBX_ is NOT used; the box is still a UCX_ hull)
  auto  grid for kit_*/building, hull otherwise
Hulls are reduced to --max-verts vertices (collapse + re-hull, so they stay convex).
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


# --- LODs ---------------------------------------------------------------------------------

def _rename_lod0(asset, log):
    lod0 = asset.lod0()
    want = "%s_LOD0" % asset.name
    if lod0.name == want:
        return lod0
    old = lod0.name
    lod0.name = want
    lod0.data.name = want
    for col in asset.collision:
        m = C.COLLISION_RE.match(col.name)
        if m and m.group("mesh") == old:
            col.name = "UCX_%s_%s" % (want, m.group("n"))
            col.data.name = col.name
    log.append({"action": "rename", "from": old, "to": want, "why": "LOD chain needs _LOD0 suffix"})
    asset.refresh()
    return asset.lod0()


def decimate_object(ob, target_tris, delimit=("MATERIAL",)):
    """Collapse-decimate ob's mesh in place to about target_tris triangles.

    Retries with a corrected ratio (delimit rules can stop the collapse early). An Armature
    modifier is lifted off during evaluation and put back, so skinned meshes decimate at rest.
    Returns the achieved triangle count."""
    arm_obj = None
    for m in list(ob.modifiers):
        if m.type == "ARMATURE":
            arm_obj = m.object
            ob.modifiers.remove(m)
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    base = common.tri_count(ob)
    target_tris = max(C.LOD_MIN_TRIS, int(target_tris))
    dec = ob.modifiers.new("LODDecimate", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.use_collapse_triangulate = True
    dec.delimit = set(delimit)
    r = min(1.0, target_tris / float(max(base, 1)))
    achieved = base
    for attempt in range(4):
        dec.ratio = max(0.001, r)
        bpy.context.view_layer.update()
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        me.calc_loop_triangles()
        achieved = len(me.loop_triangles)
        ev.to_mesh_clear()
        if abs(achieved - target_tris) <= max(4, 0.12 * target_tris) or r >= 1.0:
            break
        r = max(0.001, min(1.0, r * target_tris / max(achieved, 1)))
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    new_me = bpy.data.meshes.new_from_object(ev)
    old_me = ob.data
    name = old_me.name
    ob.modifiers.remove(dec)
    ob.data = new_me
    if old_me.users == 0:
        bpy.data.meshes.remove(old_me)
    new_me.name = name
    if arm_obj is not None:
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = arm_obj
    return achieved


def make_lods(asset, ratios, delimit=("MATERIAL",), replace=False, force=False):
    log = []
    cls = asset.cls
    if cls is None:
        return [{"action": "skip", "why": "no class"}]
    nanite = C.nanite_enabled(asset.cls_name, asset.meta(C.META_NANITE), bool(asset.meta(C.META_TRANSLUCENT, 0)))
    if nanite and not force:
        return [{"action": "skip", "why": "class %s uses Nanite: no LOD chain needed (use --force to build a fallback chain)" % asset.cls_name}]
    lod0 = asset.lod0()
    if lod0 is None:
        return [{"action": "skip", "why": "no LOD0 mesh"}]
    if any(common.transforms_dirty(o)[0] or common.transforms_dirty(o)[1] for o in (lod0,)):
        return [{"action": "skip", "why": "LOD0 has unapplied transforms: run fix.py --apply-transforms first"}]
    lod0 = _rename_lod0(asset, log)
    base = common.tri_count(lod0)
    existing = asset.lods()
    for i, ratio in enumerate(ratios, start=1):
        name = "%s_LOD%d" % (asset.name, i)
        if i in existing:
            if not replace:
                log.append({"action": "skip", "lod": i, "why": "LOD%d exists (use --replace)" % i})
                continue
            for o in existing[i]:
                bpy.data.objects.remove(o, do_unlink=True)
        target = max(C.LOD_MIN_TRIS, int(round(base * ratio)))
        ob = lod0.copy()
        ob.data = lod0.data.copy()
        ob.name = name
        ob.data.name = name
        asset.coll.objects.link(ob)
        achieved = decimate_object(ob, target, delimit)
        log.append({"action": "lod", "name": name, "ratio_requested": ratio, "tris": achieved,
                    "tris_lod0": base, "ratio_achieved": round(achieved / float(base), 4)})
    asset.refresh()
    return log


# --- Collision -----------------------------------------------------------------------------------

def _hull_from_points(points):
    """bmesh with the convex hull of the points (dissolved to n-gons), or None if degenerate."""
    if len(points) < 4:
        return None
    # flat or line-like point sets have no volume (and make bmesh's hull op return garbage)
    for i in range(3):
        if max(p[i] for p in points) - min(p[i] for p in points) < 1e-5:
            return None
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=verts)
    drop = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
    if drop:
        bmesh.ops.delete(bm, geom=list(drop), context="VERTS")
    if not bm.faces:
        bm.free()
        return None
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.05), verts=bm.verts, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def _simplify_hull(bm, max_verts):
    """Reduce hull vertex count with a decimate collapse then re-hull; stays convex."""
    for _ in range(6):
        if len(bm.verts) <= max_verts:
            return bm
        me = bpy.data.meshes.new("_hull_tmp")
        bm.to_mesh(me)
        ob = bpy.data.objects.new("_hull_tmp", me)
        bpy.context.scene.collection.objects.link(ob)
        mod = ob.modifiers.new("d", "DECIMATE")
        mod.ratio = max(0.02, 0.8 * max_verts / float(len(bm.verts)))
        bpy.context.view_layer.update()
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        tmp = ev.to_mesh()
        pts = [v.co.copy() for v in tmp.vertices]
        ev.to_mesh_clear()
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
        bm.free()
        bm = _hull_from_points(pts)
        if bm is None:
            return None
    return bm


def _clip_points(src_bm, mn, mx):
    """Vertex positions of src_bm clipped to the AABB [mn, mx] (no capping)."""
    bm = src_bm.copy()
    for axis in range(3):
        for keep_positive, value in ((True, mn[axis]), (False, mx[axis])):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            co = Vector((0, 0, 0))
            co[axis] = value
            no = Vector((0, 0, 0))
            no[axis] = 1.0
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=1e-6,
                                   clear_inner=keep_positive, clear_outer=not keep_positive)
    bm.normal_update()
    eps = 1e-5
    pts = {}
    for f in bm.faces:
        # A face lying exactly on a clip plane with its outward normal pointing into the cell is the
        # surface of something OUTSIDE the cell touching it (e.g. a door jamb seen from the opening
        # side): not part of this cell's solid.
        skip = False
        for axis in range(3):
            for value, inward in ((mn[axis], 1.0), (mx[axis], -1.0)):
                if all(abs(v.co[axis] - value) < eps for v in f.verts) and f.normal[axis] * inward > 0.5:
                    skip = True
        if skip:
            continue
        for v in f.verts:
            pts[(round(v.co.x, 7), round(v.co.y, 7), round(v.co.z, 7))] = v.co.copy()
    bm.free()
    # clamp for safety against bisect round-off
    return [Vector(tuple(min(max(p[i], mn[i]), mx[i]) for i in range(3))) for p in pts.values()]


def _merge_cells(occupied, shape):
    """Greedy cover of occupied (ix,iy,iz) cells with boxes -> list of (lo, hi) inclusive index boxes."""
    nx, ny, nz = shape
    used = set()
    boxes = []
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                c = (ix, iy, iz)
                if c not in occupied or c in used:
                    continue
                x1 = ix
                while x1 + 1 < nx and (x1 + 1, iy, iz) in occupied and (x1 + 1, iy, iz) not in used:
                    x1 += 1
                y1 = iy
                while y1 + 1 < ny and all((x, y1 + 1, iz) in occupied and (x, y1 + 1, iz) not in used for x in range(ix, x1 + 1)):
                    y1 += 1
                z1 = iz
                while z1 + 1 < nz and all((x, y, z1 + 1) in occupied and (x, y, z1 + 1) not in used
                                          for x in range(ix, x1 + 1) for y in range(iy, y1 + 1)):
                    z1 += 1
                for x in range(ix, x1 + 1):
                    for y in range(iy, y1 + 1):
                        for z in range(iz, z1 + 1):
                            used.add((x, y, z))
                boxes.append(((ix, iy, iz), (x1, y1, z1)))
    return boxes


def make_collision(asset, mode="auto", cell=None, max_verts=None, replace=False):
    log = []
    cls = asset.cls
    lod0 = asset.lod0()
    if cls is None or lod0 is None:
        return [{"action": "skip", "why": "no class or no LOD0"}]
    if cls["kind"] == "skeletal":
        return [{"action": "skip", "why": "skeletal classes use a Physics Asset in Unreal, not UCX_ hulls"}]
    rot, scl, neg = common.transforms_dirty(lod0)
    if rot or scl or neg:
        return [{"action": "skip", "why": "LOD0 has unapplied transforms: run fix.py --apply-transforms first"}]
    if asset.collision:
        if not replace:
            return [{"action": "skip", "why": "collision exists (use --replace)"}]
        for o in asset.collision:
            bpy.data.objects.remove(o, do_unlink=True)
    max_verts = max_verts or C.COLLISION_MAX_HULL_VERTS
    if mode == "auto":
        mode = "grid" if cls["pivot"].startswith("grid") or asset.cls_name in ("kit_wall", "kit_floor", "kit_ceiling", "kit_piece", "building") else "hull"
    cell = cell or (0.25 if mode == "grid" and cls["folder"] == "Kits" else 0.5)
    src = bmesh.new()
    src.from_mesh(lod0.data)
    mn, mx = common.mesh_bounds_local(lod0.data)
    hulls = []
    if mode == "hull":
        hulls.append(_hull_from_points([v.co.copy() for v in src.verts]))
    elif mode == "box":
        pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
        hulls.append(_hull_from_points(pts))
    elif mode == "grid":
        size = mx - mn
        n = [max(1, int(math.ceil(size[i] / cell - 1e-6))) for i in range(3)]
        while n[0] * n[1] * n[2] > 2500:
            cell *= 1.5
            n = [max(1, int(math.ceil(size[i] / cell - 1e-6))) for i in range(3)]
            log.append({"action": "note", "why": "too many cells; cell size raised to %.2f m" % cell})
        occupied = set()
        for ix in range(n[0]):
            for iy in range(n[1]):
                for iz in range(n[2]):
                    lo = Vector((mn.x + ix * cell, mn.y + iy * cell, mn.z + iz * cell))
                    hi = Vector((min(lo.x + cell, mx.x), min(lo.y + cell, mx.y), min(lo.z + cell, mx.z)))
                    pts = _clip_points(src, lo, hi)
                    h = _hull_from_points(pts)
                    if h is None:
                        continue
                    vol = h.calc_volume()
                    h.free()
                    cvol = max((hi.x - lo.x) * (hi.y - lo.y) * (hi.z - lo.z), 1e-9)
                    if vol > 0.02 * cvol and vol > 1e-6:
                        occupied.add((ix, iy, iz))
        for (lo_i, hi_i) in _merge_cells(occupied, n):
            lo = Vector((mn.x + lo_i[0] * cell, mn.y + lo_i[1] * cell, mn.z + lo_i[2] * cell))
            hi = Vector((min(mn.x + (hi_i[0] + 1) * cell, mx.x), min(mn.y + (hi_i[1] + 1) * cell, mx.y),
                         min(mn.z + (hi_i[2] + 1) * cell, mx.z)))
            hulls.append(_hull_from_points(_clip_points(src, lo, hi)))
    else:
        src.free()
        return [{"action": "skip", "why": "unknown collision mode %r" % mode}]
    src.free()
    k = 0
    for h in hulls:
        if h is None:
            continue
        h = _simplify_hull(h, max_verts)
        if h is None:
            continue
        k += 1
        name = "UCX_%s_%02d" % (lod0.name, k)
        me = bpy.data.meshes.new(name)
        h.to_mesh(me)
        nverts = len(h.verts)
        h.free()
        ob = bpy.data.objects.new(name, me)
        ob.location = lod0.location
        ob.display_type = "WIRE"
        ob.hide_render = True
        ob["dink_generated"] = "make_lods.py"
        asset.coll.objects.link(ob)
        log.append({"action": "collision", "name": name, "mode": mode, "vertices": nverts})
    asset.refresh()
    if k == 0:
        log.append({"action": "warning", "why": "no collision hull could be built"})
    return log


def main():
    p = common.make_parser("make_lods.py", __doc__.split("\n")[0])
    p.add_argument("--class", dest="default_class", help="class for assets without %s" % C.META_CLASS)
    p.add_argument("--lods", action="store_true", help="generate the LOD chain")
    p.add_argument("--ratios", help="comma list of LOD1.. triangle ratios (default: per class)")
    p.add_argument("--delimit", default="MATERIAL", help="decimate delimit set, comma list of NORMAL,MATERIAL,SEAM,SHARP,UV")
    p.add_argument("--force", action="store_true", help="build LODs even for Nanite classes")
    p.add_argument("--collision", nargs="?", const="auto", choices=["auto", "hull", "grid", "box"],
                   help="generate UCX_ collision")
    p.add_argument("--cell", type=float, help="grid cell size in metres (grid mode)")
    p.add_argument("--max-verts", type=int, help="max vertices per hull (default %d)" % C.COLLISION_MAX_HULL_VERTS)
    p.add_argument("--replace", action="store_true", help="replace existing LODs/collision")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output", help="save the result here")
    g.add_argument("--inplace", action="store_true", help="overwrite the input .blend")
    args = p.parse_args(common.script_argv())
    if not (args.lods or args.collision):
        p.error("nothing to do: pass --lods and/or --collision")
    try:
        path = common.open_blend(args.blend)
    except (RuntimeError, SystemExit) as e:
        common.emit({"tool": "make_lods", "ok": False, "fatal": str(e)}, args.report)
        common.finish(2)
    out = path if args.inplace else os.path.abspath(args.output)
    assets = common.find_assets(only=args.collection, default_class=args.default_class)
    results = []
    for a in assets:
        entry = {"asset": a.name, "class": a.cls_name, "log": []}
        if a.cls is None:
            entry["log"].append({"action": "skip", "why": "unknown or missing class"})
        else:
            if args.lods:
                ratios = [float(x) for x in args.ratios.split(",")] if args.ratios else list(a.cls["lod_ratios"] or C.LOD_RATIOS_STANDARD)
                entry["log"] += make_lods(a, ratios, args.delimit.split(","), args.replace, args.force)
            if args.collision:
                entry["log"] += make_collision(a, args.collision, args.cell, args.max_verts, args.replace)
        results.append(entry)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    common.emit({"tool": "make_lods", "ok": True, "saved": out, "assets": results}, args.report)
    common.finish(0)


if __name__ == "__main__":
    main()
