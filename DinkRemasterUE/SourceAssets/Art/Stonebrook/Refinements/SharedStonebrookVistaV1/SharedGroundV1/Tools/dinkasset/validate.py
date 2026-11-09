"""Validate assets in a .blend against CONVENTIONS.md.

    blender -b --factory-startup -P tools/blender/dinkasset/validate.py -- \
        --blend my.blend [--collection SM_Barrel_01] [--class prop] [--strict] [--report out.json]

Prints a JSON report between @@DINK_REPORT_BEGIN@@ / @@DINK_REPORT_END@@ and exits
0 (all assets pass), 1 (errors found; with --strict also warnings), 2 (usage / load error).
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from dinkasset import common  # noqa: E402
from dinkasset import conventions as C  # noqa: E402

ERROR, WARNING, INFO = "error", "warning", "info"
MAX_UV_OVERLAP_TRIS = 120000   # the pure-Python overlap test is skipped above this (reported as info)


class Findings:
    def __init__(self, asset_name):
        self.asset = asset_name
        self.items = []

    def add(self, code, severity, message, obj=None, **data):
        f = {"code": code, "severity": severity, "asset": self.asset, "message": message}
        if obj is not None:
            f["object"] = obj if isinstance(obj, str) else obj.name
        if data:
            f["data"] = data
        self.items.append(f)

    def count(self, severity):
        return sum(1 for f in self.items if f["severity"] == severity)


def _is_pow2(n):
    return n > 0 and (n & (n - 1)) == 0


# --- UV analysis ------------------------------------------------------------------------

def _clip_area(subject, clip):
    """Area of the intersection of two convex polygons (Sutherland-Hodgman)."""
    out = subject
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        inp, out = out, []
        if not inp:
            break
        ex, ey = b[0] - a[0], b[1] - a[1]

        def side(p):
            return ex * (p[1] - a[1]) - ey * (p[0] - a[0])
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            sp, sq = side(p), side(q)
            if sp >= 0:
                out.append(p)
            if (sp >= 0) != (sq >= 0):
                t = sp / (sp - sq)
                out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    if len(out) < 3:
        return 0.0
    s = 0.0
    for i in range(len(out)):
        x1, y1 = out[i]
        x2, y2 = out[(i + 1) % len(out)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def uv_stats(mesh, layer_index=0, max_pairs=300000):
    """UV-space statistics of one UV layer: total area, overlapped area, out-of-range, texel ratio.

    Triangles are tested pairwise through a spatial hash. Pairs from the same polygon are
    skipped; shared edges give zero area so adjacent triangles never count."""
    layer = mesh.uv_layers[layer_index]
    import array
    n = len(mesh.loops)
    flat = array.array("f", [0.0]) * (2 * n)
    layer.uv.foreach_get("vector", flat)
    mesh.calc_loop_triangles()
    tris = []
    total_uv_area = 0.0
    total_3d_area = 0.0
    degenerate = 0
    out_of_range = 0
    co = common.local_vertices(mesh)
    loops_v = array.array("i", [0]) * n
    mesh.loops.foreach_get("vertex_index", loops_v)
    for t in mesh.loop_triangles:
        l = t.loops
        pts = [(flat[2 * i], flat[2 * i + 1]) for i in l]
        a = abs((pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1])
                - (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])) / 2.0
        p3 = [Vector(co[3 * loops_v[i]:3 * loops_v[i] + 3]) for i in l]
        a3 = (p3[1] - p3[0]).cross(p3[2] - p3[0]).length / 2.0
        total_uv_area += a
        total_3d_area += a3
        if a < 1e-10 and a3 > 1e-8:
            degenerate += 1
        for p in pts:
            if p[0] < -1e-4 or p[0] > 1 + 1e-4 or p[1] < -1e-4 or p[1] > 1 + 1e-4:
                out_of_range += 1
                break
        if a >= 1e-10:
            # make counter-clockwise for the clipper
            cross = (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])
            if cross < 0:
                pts = [pts[0], pts[2], pts[1]]
            tris.append((t.polygon_index, pts, a))
    # spatial hash
    # Preserve exact UV clip/area semantics while bounding the broadphase for tiledUVs.
    # Original fixed64cells/UVunit explodes on legitimate terrain UVspan16+.
    all_uv = [point for _, points, _ in tris for point in points]
    uv_span = max(1.0, max((p[0] for p in all_uv), default=0.0) - min((p[0] for p in all_uv), default=0.0),
                  max((p[1] for p in all_uv), default=0.0) - min((p[1] for p in all_uv), default=0.0))
    G = 64.0 / uv_span
    cells = {}
    for idx, (_, pts, _) in enumerate(tris):
        us = [p[0] for p in pts]
        vs = [p[1] for p in pts]
        for cx in range(int(math.floor(min(us) * G)), int(math.floor(max(us) * G)) + 1):
            for cy in range(int(math.floor(min(vs) * G)), int(math.floor(max(vs) * G)) + 1):
                cells.setdefault((cx, cy), []).append(idx)
    seen = set()
    overlapped = 0.0
    pairs = 0
    overlapping_tris = set()
    truncated = False
    for members in cells.values():
        if len(members) < 2:
            continue
        for i in range(len(members)):
            ia = members[i]
            pa, ptsa, _ = tris[ia]
            for j in range(i + 1, len(members)):
                ib = members[j]
                key = (ia, ib) if ia < ib else (ib, ia)
                if key in seen:
                    continue
                seen.add(key)
                pb, ptsb, _ = tris[ib]
                if pa == pb:
                    continue
                pairs += 1
                if pairs > max_pairs:
                    truncated = True
                    break
                # cheap bbox reject
                if (max(p[0] for p in ptsa) <= min(p[0] for p in ptsb)
                        or max(p[0] for p in ptsb) <= min(p[0] for p in ptsa)
                        or max(p[1] for p in ptsa) <= min(p[1] for p in ptsb)
                        or max(p[1] for p in ptsb) <= min(p[1] for p in ptsa)):
                    continue
                area = _clip_area(ptsa, ptsb)
                if area > 1e-7:
                    overlapped += area
                    overlapping_tris.add(ia)
                    overlapping_tris.add(ib)
            if truncated:
                break
        if truncated:
            break
    return {
        "uv_area": total_uv_area, "area_3d": total_3d_area, "overlap_area": overlapped,
        "overlap_ratio": (overlapped / total_uv_area) if total_uv_area > 0 else 0.0,
        "overlapping_tris": len(overlapping_tris), "degenerate_tris": degenerate,
        "tris_out_of_range": out_of_range, "truncated": truncated, "tris": len(tris),
    }


# --- Individual checks ---------------------------------------------------------------------

def check_scene(findings_list):
    us = bpy.context.scene.unit_settings
    if us.system != "METRIC" or abs(us.scale_length - 1.0) > 1e-6:
        f = Findings(None)
        f.add("SCENE_UNITS", ERROR,
              "scene units must be Metric with Unit Scale 1.0 (1 Blender unit = 1 m); got %s scale %g"
              % (us.system, us.scale_length), system=us.system, scale_length=us.scale_length)
        findings_list.extend(f.items)


def check_names(a, F):
    cls = a.cls
    if not C.ASSET_NAME_RE.match(a.name):
        F.add("NAME_ASSET", ERROR,
              "collection name %r does not match SM_/SK_ + PascalCase tokens (e.g. SM_Barrel_01)" % a.name)
    elif len(a.name) > C.MAX_NAME_LEN:
        F.add("NAME_ASSET", ERROR, "asset name longer than %d characters" % C.MAX_NAME_LEN)
    if cls:
        want = C.SKELETAL_PREFIX if cls["kind"] == "skeletal" else C.STATIC_PREFIX
        if not a.name.startswith(want + "_"):
            F.add("NAME_PREFIX", ERROR, "class %s needs the %s_ prefix" % (a.cls_name, want))
    lods = a.lods()
    chain = any(n > 0 for n in lods) or any(C.LOD_RE.match(o.name) for o in a.renders)
    for ob in a.renders:
        n = common.lod_index(ob.name)
        ok = ob.name == "%s_LOD%d" % (a.name, n) or (not chain and ob.name == a.name)
        if not ok:
            want = "%s_LOD%d" % (a.name, n) if chain else "%s (or %s_LOD0)" % (a.name, a.name)
            F.add("NAME_OBJECT", ERROR, "render mesh object %r should be named %s" % (ob.name, want), obj=ob)
        elif ob.data.name != ob.name:
            F.add("NAME_MESHDATA", INFO, "mesh data %r differs from object name %r" % (ob.data.name, ob.name), obj=ob)
    lod0 = a.lod0()
    seen = set()
    for ob in a.collision:
        m = C.COLLISION_RE.match(ob.name)
        if not m:
            F.add("NAME_COLLISION", ERROR, "collision object %r must be named UCX_<LOD0 mesh name>_NN" % ob.name, obj=ob)
            continue
        if not ob.name.startswith("UCX_"):
            F.add("NAME_COLLISION", WARNING, "%s_ primitives are not generated by this toolchain; prefer UCX_" % m.group("kind"), obj=ob)
        if lod0 is not None and m.group("mesh") != lod0.name:
            F.add("NAME_COLLISION", ERROR,
                  "collision %r names mesh %r but LOD0 is %r (Unreal matches by name)" % (ob.name, m.group("mesh"), lod0.name), obj=ob)
        if ob.name in seen:
            F.add("NAME_COLLISION", ERROR, "duplicate collision name %r" % ob.name, obj=ob)
        seen.add(ob.name)
    mats = []
    for ob in a.renders:
        for s in ob.material_slots:
            if s.material and s.material not in mats:
                mats.append(s.material)
    for mat in mats:
        if not C.MATERIAL_NAME_RE.match(mat.name):
            F.add("NAME_MATERIAL", ERROR, "material %r must be M_<Name> or MI_<Name> (no .001 suffixes)" % mat.name)


def check_meta(a, F):
    if a.cls_name is None:
        F.add("ASSET_CLASS_MISSING", ERROR,
              "collection has no %s custom property (use fix.py --set-class or pass --class)" % C.META_CLASS)
        return False
    if a.cls is None:
        F.add("ASSET_CLASS_UNKNOWN", ERROR, "unknown class %r; valid: %s" % (a.cls_name, ", ".join(sorted(C.CLASSES))))
        return False
    return True


def check_structure(a, F):
    cls = a.cls
    if not a.renders:
        F.add("NO_MESH", ERROR, "asset has no render mesh")
        return
    lods = a.lods()
    for n, objs in lods.items():
        if len(objs) > 1:
            F.add("MULTI_MESH", ERROR,
                  "LOD%d has %d mesh objects (%s); join them into one (Unreal merges unpredictably)"
                  % (n, len(objs), ", ".join(o.name for o in objs)))
    if 0 not in lods:
        F.add("LOD_GAP", ERROR, "no LOD0 mesh (an unsuffixed %s or %s_LOD0)" % (a.name, a.name))
    if cls["kind"] == "static" and a.armatures:
        F.add("STATIC_HAS_ARMATURE", ERROR, "static-mesh class %s contains an armature" % a.cls_name)
    if cls["kind"] == "skeletal" and len(a.armatures) != 1:
        F.add("SKELETON_COUNT", ERROR, "skeletal class needs exactly one armature, found %d" % len(a.armatures))
    needs = cls.get("needs_socket")
    if needs and not any(s.name == needs for s in a.sockets):
        F.add("SOCKET_MISSING", ERROR, "class %s needs an Empty named %s" % (a.cls_name, needs))
    for ob in a.other:
        F.add("UNEXPECTED_OBJECT", WARNING, "object %r (%s) is not part of the asset contract and will not be exported" % (ob.name, ob.type), obj=ob)


def check_transforms(a, F):
    cls = a.cls
    members = set(a.all_objects())
    lod0 = a.lod0()
    for ob in a.all_objects():
        if ob.parent is not None:
            if cls["kind"] == "skeletal" and ob.parent in a.armatures and ob.type == "MESH":
                pass
            elif ob.parent in members and ob.type == "EMPTY":
                pass
            else:
                F.add("PARENTED", ERROR,
                      "%r is parented to %r; assets are flat (parent only meshes to the armature)" % (ob.name, ob.parent.name), obj=ob)
        if ob.type in ("MESH", "ARMATURE"):
            rot, scl, neg = common.transforms_dirty(ob)
            if neg:
                F.add("NEGATIVE_SCALE", ERROR, "%r has negative scale (mirrored): apply scale" % ob.name, obj=ob)
            if rot or scl:
                F.add("TRANSFORM_UNAPPLIED", ERROR,
                      "%r has unapplied %s (scale %s, rotation %s)" % (
                          ob.name, "/".join(x for x, f in (("rotation", rot), ("scale", scl)) if f),
                          [round(v, 4) for v in ob.matrix_basis.to_scale()],
                          [round(math.degrees(v), 2) for v in ob.matrix_basis.to_euler()]), obj=ob)
        if ob.type == "MESH" and ob is not lod0 and lod0 is not None and ob not in a.sockets:
            d = (ob.matrix_world.translation - lod0.matrix_world.translation).length
            if d > 1e-4:
                F.add("ORIGIN_MISMATCH", ERROR,
                      "%r origin is %.1f cm from the LOD0 origin; every mesh of an asset shares one pivot" % (ob.name, d * 100), obj=ob)
    for ob in a.renders:
        extra = [m.type for m in ob.modifiers if m.type != "ARMATURE"]
        if extra:
            F.add("MODIFIERS", WARNING,
                  "%r has live modifiers (%s); the export applies them, triangle counts are for the evaluated mesh. Apply them in the source." % (ob.name, ", ".join(extra)), obj=ob)


def _origin_for_pivot(a):
    if a.cls["kind"] == "skeletal" and a.armatures:
        return a.armatures[0].matrix_world.translation.copy()
    lod0 = a.lod0()
    return lod0.matrix_world.translation.copy() if lod0 else Vector()


def check_scale_and_pivot(a, F):
    cls = a.cls
    lod0 = a.lod0()
    if lod0 is None:
        return
    mn, mx = common.world_bounds(lod0)
    size = mx - mn
    lo, hi = cls["longest"]
    longest = max(size)
    if longest < lo - 1e-9 or longest > hi + 1e-9:
        hint = ""
        for factor, label in ((100.0, "centimetres"), (1000.0, "millimetres"), (0.01, "x100 too small"), (0.001, "x1000 too small")):
            if lo <= longest / factor <= hi:
                hint = " Looks like %s: scale by %g." % (label if factor > 1 else label, 1.0 / factor)
                break
        F.add("SCALE_RANGE", ERROR,
              "longest dimension %.3f m is outside the %s range %.2f-%.2f m.%s" % (longest, a.cls_name, lo, hi, hint),
              obj=lod0, longest_m=round(longest, 4), range_m=[lo, hi], size_m=[round(v, 4) for v in size])
    if "height" in cls:
        hlo, hhi = cls["height"]
        if not (hlo <= size.z <= hhi):
            F.add("SCALE_RANGE", ERROR, "height %.3f m outside %.2f-%.2f m for %s" % (size.z, hlo, hhi, a.cls_name), obj=lod0)
    if cls.get("snap"):
        axes = cls["grid_axes"]
        for i, ax in enumerate("xyz"):
            if ax not in axes:
                continue
            q = size[i] / C.SUBGRID_M
            if abs(q - round(q)) * C.SUBGRID_M > C.SNAP_TOL_M:
                F.add("SNAP", ERROR, "%s extent %.3f m is not a multiple of the %.1f m sub-grid" % (ax, size[i], C.SUBGRID_M), obj=lod0)
            elif abs(size[i] / C.GRID_M - round(size[i] / C.GRID_M)) * C.GRID_M > C.SNAP_TOL_M:
                F.add("SNAP", INFO, "%s extent %.2f m is a half module (not a multiple of %.0f m)" % (ax, size[i], C.GRID_M), obj=lod0)
        if cls.get("height_snap"):
            q = size.z / C.SUBGRID_M
            if size.z > C.CEILING_M + C.SNAP_TOL_M or abs(q - round(q)) * C.SUBGRID_M > C.SNAP_TOL_M:
                F.add("SNAP", ERROR, "wall height %.3f m must be a multiple of %.1f m and at most %.1f m" % (size.z, C.SUBGRID_M, C.CEILING_M), obj=lod0)
    # pivot: bounds relative to the pivot origin (transform application is checked separately)
    origin = _origin_for_pivot(a)
    rmn, rmx = mn - origin, mx - origin
    socket_pos = None
    if cls["pivot"] == "grip":
        sock = [s for s in a.sockets if s.name == "SOCKET_Grip"]
        if sock:
            socket_pos = sock[0].matrix_world.translation - origin
    if cls["pivot"] == "grip":
        if socket_pos is not None:
            ok = socket_pos.length <= C.SNAP_TOL_M
            off = socket_pos
            note = "origin must coincide with SOCKET_Grip"
        else:
            ok, off, note = common.pivot_error("grip", rmn, rmx)
    else:
        ok, off, note = common.pivot_error(cls["pivot"], rmn, rmx, tol_xy=cls.get("pivot_xy"))
    if not ok:
        F.add("PIVOT", ERROR,
              "pivot is wrong for %s (rule %s): origin is %.1f cm off, should move by (%.1f, %.1f, %.1f) cm. %s"
              % (a.cls_name, cls["pivot"], off.length * 100, off.x * 100, off.y * 100, off.z * 100, note),
              obj=lod0, rule=cls["pivot"], offset_cm=[round(v * 100, 2) for v in off])
    return mn, mx, origin


def check_budget(a, F):
    cls = a.cls
    lod0 = a.lod0()
    if lod0 is None:
        return {}
    tris = {}
    for n, objs in sorted(a.lods().items()):
        tris[n] = common.tri_count(objs[0])
    target, mx = cls["tris"]
    t0 = tris.get(0, 0)
    if t0 > mx:
        F.add("TRIS_OVER_BUDGET", ERROR, "LOD0 has %d triangles, hard budget for %s is %d" % (t0, a.cls_name, mx), obj=lod0, tris=t0, budget=mx)
    elif t0 > target:
        F.add("TRIS_OVER_TARGET", WARNING, "LOD0 has %d triangles, target for %s is %d (hard max %d)" % (t0, a.cls_name, target, mx), obj=lod0, tris=t0, target=target)
    return tris


def check_geometry(a, F):
    cls = a.cls
    for ob in a.renders:
        with common.bmesh_of(ob) as bm:
            loose_v = sum(1 for v in bm.verts if not v.link_edges)
            loose_e = sum(1 for e in bm.edges if not e.link_faces)
            if loose_v or loose_e:
                F.add("LOOSE_GEOMETRY", WARNING, "%d loose vertices, %d loose (wire) edges" % (loose_v, loose_e), obj=ob, vertices=loose_v, edges=loose_e)
            zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
            if zero:
                F.add("ZERO_AREA", ERROR, "%d zero-area faces (area < 1e-8 m2)" % zero, obj=ob, faces=zero)
            if bm.verts:
                dmap = bmesh.ops.find_doubles(bm, verts=bm.verts, dist=1e-5)["targetmap"]
                if dmap:
                    F.add("DUPLICATE_VERTS", WARNING, "%d vertices coincide with another vertex (within 0.01 mm); merge by distance" % len(dmap), obj=ob, vertices=len(dmap))
            boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
            multi = sum(1 for e in bm.edges if len(e.link_faces) > 2)
            wire = sum(1 for e in bm.edges if len(e.link_faces) == 0)
            nm = boundary + multi + wire
            if nm:
                sev = ERROR if cls["manifold"] == "error" else WARNING
                F.add("NON_MANIFOLD", sev,
                      "%d non-manifold edges (%d open boundary, %d shared by >2 faces, %d wire); %s must be a closed solid"
                      % (nm, boundary, multi, wire, a.cls_name) if sev == ERROR else
                      "%d non-manifold edges (%d open boundary, %d >2 faces, %d wire); acceptable for %s only if intentional (cards)"
                      % (nm, boundary, multi, wire, a.cls_name),
                      obj=ob, boundary=boundary, multi_face=multi, wire=wire)
            else:
                if bm.faces and bm.calc_volume(signed=True) < -1e-9:
                    F.add("NORMALS_INVERTED", ERROR, "closed mesh has negative volume: normals point inward (recalculate outside)", obj=ob)
            incon = sum(1 for e in bm.edges if len(e.link_faces) == 2 and not e.is_contiguous)
            if incon:
                F.add("NORMALS_INCONSISTENT", ERROR, "%d edges join faces with opposite winding (flipped faces)" % incon, obj=ob, edges=incon)


def check_uv_and_materials(a, F):
    cls = a.cls
    lod0 = a.lod0()
    if lod0 is None:
        return
    me = lod0.data
    if len(me.uv_layers) == 0:
        F.add("UV_MISSING", ERROR, "no UV map on LOD0", obj=lod0)
    else:
        if len(me.uv_layers) > 2:
            F.add("UV_COUNT", WARNING, "%d UV maps; keep UV0 (textures) and at most one extra (UV1)" % len(me.uv_layers), obj=lod0)
        me.calc_loop_triangles()
        if len(me.loop_triangles) > MAX_UV_OVERLAP_TRIS:
            F.add("UV_OVERLAP", INFO, "UV overlap / texel checks skipped: %d triangles is above the %d limit of the Python test"
                  % (len(me.loop_triangles), MAX_UV_OVERLAP_TRIS), obj=lod0)
            st = {"overlap_ratio": 0.0, "overlapping_tris": 0, "tris_out_of_range": 0, "degenerate_tris": 0,
                  "truncated": False, "area_3d": 0.0, "uv_area": 0.0}
        else:
            st = uv_stats(me, 0)
        if not cls["uv_overlap"] and st["overlap_ratio"] > 0.002:
            F.add("UV_OVERLAP", ERROR,
                  "UV0 islands overlap (%.1f %% of UV area, %d triangles); class %s needs unique UVs"
                  % (st["overlap_ratio"] * 100, st["overlapping_tris"], a.cls_name), obj=lod0,
                  overlap_ratio=round(st["overlap_ratio"], 5))
        if not cls["uv_overlap"] and st["tris_out_of_range"]:
            F.add("UV_RANGE", WARNING, "%d triangles have UVs outside 0-1" % st["tris_out_of_range"], obj=lod0)
        if st["degenerate_tris"]:
            F.add("UV_DEGENERATE", WARNING, "%d triangles are collapsed in UV space" % st["degenerate_tris"], obj=lod0)
        if st["truncated"]:
            F.add("UV_OVERLAP", INFO, "UV overlap test truncated (very dense UVs); result is a lower bound", obj=lod0)
        if cls.get("texel_check") and st["area_3d"] > 0 and st["uv_area"] > 0:
            target = cls["texel"]
            # texture edge needed to reach the target density if UV0 is the only texture set
            needed = target * math.sqrt(st["area_3d"] / st["uv_area"])
            declared = a.meta(C.META_TEX_PX)
            if declared:
                density = math.sqrt(st["uv_area"] / st["area_3d"]) * float(declared)
                if not (0.5 * target <= density <= 2.0 * target):
                    F.add("TEXEL_DENSITY", WARNING,
                          "texel density %.0f px/m at the declared %d px texture; target %d px/m (accepted %d-%d)"
                          % (density, declared, target, 0.5 * target, 2 * target),
                          obj=lod0, density_px_per_m=round(density, 1), target=target)
            elif needed > cls["tex_max"] * 1.0:
                F.add("TEXEL_DENSITY", WARNING,
                      "reaching %d px/m with this UV layout needs a %d px texture, above the %d px cap for %s: "
                      "use more UV tiles/materials or accept a lower density (set %s to declare it)"
                      % (target, needed, cls["tex_max"], a.cls_name, C.META_TEX_PX),
                      obj=lod0, needed_px=round(needed), target=target)
    # materials
    slots = lod0.material_slots
    if len(slots) > cls["slots"]:
        F.add("SLOTS_OVER", ERROR, "%d material slots, limit for %s is %d" % (len(slots), a.cls_name, cls["slots"]), obj=lod0)
    used = {}
    for p in me.polygons:
        used[p.material_index] = used.get(p.material_index, 0) + 1
    for i, s in enumerate(slots):
        if s.material is None:
            F.add("MATERIAL_EMPTY_SLOT", ERROR, "material slot %d is empty" % i, obj=lod0)
        if used.get(i, 0) == 0 and len(slots) > 1:
            F.add("SLOT_UNUSED", WARNING, "material slot %d (%s) has no faces" % (i, s.material.name if s.material else "-"), obj=lod0)
    if len(slots) == 0:
        F.add("NO_MATERIAL", WARNING, "LOD0 has no material", obj=lod0)
    base_mats = [s.material.name if s.material else None for s in slots]
    for n, objs in sorted(a.lods().items()):
        if n == 0:
            continue
        mats = [s.material.name if s.material else None for s in objs[0].material_slots]
        if mats != base_mats:
            F.add("LOD_MATERIAL_MISMATCH", WARNING, "LOD%d material slots %s differ from LOD0 %s" % (n, mats, base_mats), obj=objs[0])
    # textures
    seen = set()
    for s in slots:
        mat = s.material
        if not mat or not mat.use_nodes or not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE":
                continue
            img = node.image
            if img is None:
                F.add("TEXTURE_MISSING", WARNING, "image node in %s has no image" % mat.name)
                continue
            if img.name in seen:
                continue
            seen.add(img.name)
            if not C.TEXTURE_NAME_RE.match(img.name):
                F.add("NAME_TEXTURE", WARNING, "image %r should be T_<Name>_<%s>" % (img.name, "|".join(C.TEXTURE_SUFFIXES)))
            w, h = img.size[0], img.size[1]
            if w == 0 or h == 0:
                F.add("TEXTURE_MISSING", WARNING, "image %r has no pixel data (missing file?)" % img.name)
                continue
            if not (_is_pow2(w) and _is_pow2(h)):
                F.add("TEXTURE_SIZE", ERROR, "image %r is %dx%d: must be power-of-two (mips and streaming)" % (img.name, w, h))
            elif max(w, h) > cls["tex_max"]:
                F.add("TEXTURE_SIZE", ERROR, "image %r is %dx%d: %s textures max %d" % (img.name, w, h, a.cls_name, cls["tex_max"]))


def _convex_check(ob):
    """(is_convex, nverts) for a collision hull. Tests every triangle plane (n-gon planes of a
    dissolved hull may be slightly non-planar, triangles are exact)."""
    me = ob.data
    n = len(me.vertices)
    if n > 1500:
        return False, n
    pts = [v.co.copy() for v in me.vertices]
    me.calc_loop_triangles()
    scale = max((max(p[i] for p in pts) - min(p[i] for p in pts)) for i in range(3)) if pts else 1.0
    tol = max(1e-3 * scale, 5e-4)  # 0.1 % of size, at least 0.5 mm
    for t in me.loop_triangles:
        a, b, c = (me.vertices[i].co for i in t.vertices)
        nrm = (b - a).cross(c - a)
        if nrm.length < 1e-12:
            continue
        nrm.normalize()
        d = nrm.dot(a)
        for p in pts:
            if nrm.dot(p) - d > tol:
                return False, n
    return True, n


def check_collision(a, F):
    cls = a.cls
    translucent = bool(a.meta(C.META_TRANSLUCENT, 0))
    if cls["collision"] and not a.collision:
        F.add("COLLISION_MISSING", ERROR, "class %s needs UCX_ collision (run make_lods.py --collision)" % a.cls_name)
    lod0 = a.lod0()
    allmin = allmax = None
    for ob in a.collision:
        with common.bmesh_of(ob) as bm:
            nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
            vol = bm.calc_volume(signed=True) if bm.faces else 0.0
        convex, n = _convex_check(ob)
        if n > C.COLLISION_HARD_MAX_VERTS:
            F.add("COLLISION_TOO_COMPLEX", ERROR, "%r has %d vertices (max %d)" % (ob.name, n, C.COLLISION_HARD_MAX_VERTS), obj=ob)
        elif n > C.COLLISION_MAX_HULL_VERTS:
            F.add("COLLISION_TOO_COMPLEX", WARNING, "%r has %d vertices (target <= %d)" % (ob.name, n, C.COLLISION_MAX_HULL_VERTS), obj=ob)
        if nm:
            F.add("COLLISION_NOT_CLOSED", ERROR, "%r is not a closed solid (%d open edges)" % (ob.name, nm), obj=ob)
        elif abs(vol) < 1e-9:
            F.add("COLLISION_DEGENERATE", ERROR, "%r has no volume" % ob.name, obj=ob)
        if not convex:
            F.add("COLLISION_NOT_CONVEX", ERROR, "%r is not convex (Unreal collapses a non-convex UCX into its hull, losing holes)" % ob.name, obj=ob)
        mn, mx = common.world_bounds(ob)
        allmin = mn if allmin is None else Vector(min(allmin[i], mn[i]) for i in range(3))
        allmax = mx if allmax is None else Vector(max(allmax[i], mx[i]) for i in range(3))
    if a.collision and lod0 is not None and allmin is not None:
        mmn, mmx = common.world_bounds(lod0)
        out = max(max(mmn[i] - allmin[i], allmax[i] - mmx[i]) for i in range(3))
        if out > 0.05:
            F.add("COLLISION_BOUNDS", WARNING, "collision extends %.0f cm beyond the render mesh bounds" % (out * 100), obj=a.collision[0])


def check_lods(a, F, tris):
    cls = a.cls
    lods = a.lods()
    translucent = bool(a.meta(C.META_TRANSLUCENT, 0))
    nan_over = a.meta(C.META_NANITE)
    nanite = C.nanite_enabled(a.cls_name, nan_over, translucent)
    need = C.lods_required(a.cls_name, nan_over, translucent)
    present = sorted(lods)
    if present and present != list(range(len(present))):
        F.add("LOD_GAP", ERROR, "LOD indices %s are not contiguous from 0" % present)
    if len(present) < need:
        F.add("LOD_MISSING", ERROR, "%s needs %d LOD levels (LOD0..LOD%d), found %d (run make_lods.py)" % (a.cls_name, need, need - 1, len(present)),
              have=len(present), need=need)
    for n in present:
        if n == 0 or n - 1 not in tris or n not in tris:
            continue
        if tris[n] > tris[n - 1] * C.LOD_MONOTONIC_SLACK:
            F.add("LOD_NOT_DECREASING", ERROR, "LOD%d has %d triangles, LOD%d has %d: each LOD must be lighter" % (n, tris[n], n - 1, tris[n - 1]), obj=lods[n][0])
    lod0 = a.lod0()
    if lod0 is not None:
        b0 = common.world_bounds(lod0)
        s0 = b0[1] - b0[0]
        for n in present:
            if n == 0:
                continue
            bn = common.world_bounds(lods[n][0])
            sn = bn[1] - bn[0]
            dev = max(abs(sn[i] - s0[i]) for i in range(3))
            if dev > max(0.05, 0.1 * max(s0)):
                F.add("LOD_BOUNDS", WARNING, "LOD%d bounds differ from LOD0 by %.0f cm (decimation shrank it?)" % (n, dev * 100), obj=lods[n][0])
    if nanite and len(present) > 1:
        F.add("LOD_UNEXPECTED", INFO, "%s uses Nanite: the LOD chain is only a fallback; keep it only if the fallback matters" % a.cls_name)
    if cls["kind"] == "skeletal":
        for n in present:
            ob = lods[n][0]
            if not any(m.type == "ARMATURE" for m in ob.modifiers):
                F.add("SKIN_NO_ARMATURE_MODIFIER", ERROR, "%r has no Armature modifier (LODs must be skinned)" % ob.name, obj=ob)


def check_skeleton(a, F):
    cls = a.cls
    if cls["kind"] != "skeletal" or len(a.armatures) != 1:
        return
    arm = a.armatures[0]
    bones = list(arm.data.bones)
    names = {b.name for b in bones}
    required = C.SKELETONS[cls["skeleton"]]
    missing = [n for n in required if n not in names]
    if missing:
        F.add("SKELETON_BONES", ERROR, "missing %d required %s bones: %s" % (len(missing), cls["skeleton"], ", ".join(missing[:12]) + ("..." if len(missing) > 12 else "")),
              obj=arm, missing=missing)
    roots = [b.name for b in bones if b.parent is None]
    if roots != ["root"]:
        F.add("SKELETON_ROOT", ERROR, "skeleton must have a single root bone named 'root', found %s" % roots, obj=arm)
    bad = [n for n in names if any(t in n for t in (".L", ".R", ".l", ".r", " ")) or n != n.strip()]
    if bad:
        F.add("SKELETON_BONE_NAME", ERROR, "bone names must use _l/_r and no spaces or dots: %s" % ", ".join(sorted(bad)[:8]), obj=arm)
    if len(bones) > C.MAX_BONES_WARN:
        F.add("SKELETON_BONE_COUNT", WARNING, "%d bones (> %d)" % (len(bones), C.MAX_BONES_WARN), obj=arm)
    for lod_ob in a.renders:
        _check_skin(lod_ob, names, F)


def _check_skin(lod0, names, F):
    groups = {g.index: g.name for g in lod0.vertex_groups}
    orphan = sorted(n for n in groups.values() if n not in names)
    if orphan:
        F.add("SKIN_ORPHAN_GROUPS", WARNING, "%d vertex groups match no bone: %s" % (len(orphan), ", ".join(orphan[:6])), obj=lod0)
    unweighted = 0
    over8 = 0
    over4 = 0
    for v in lod0.data.vertices:
        w = [g for g in v.groups if groups.get(g.group) in names and g.weight > 1e-4]
        if not w:
            unweighted += 1
        if len(w) > C.MAX_BONE_INFLUENCES:
            over8 += 1
        elif len(w) > C.PREFERRED_BONE_INFLUENCES:
            over4 += 1
    if unweighted:
        F.add("SKIN_UNWEIGHTED", ERROR, "%d vertices have no bone weight" % unweighted, obj=lod0)
    if over8:
        F.add("SKIN_INFLUENCES", ERROR, "%d vertices have more than %d bone influences" % (over8, C.MAX_BONE_INFLUENCES), obj=lod0)
    if over4:
        F.add("SKIN_INFLUENCES", WARNING, "%d vertices have more than %d influences (limit weights to 4 for the Deck)" % (over4, C.PREFERRED_BONE_INFLUENCES), obj=lod0)


# --- Driver ---------------------------------------------------------------------------------------

def validate_asset(a):
    F = Findings(a.name)
    tris = {}
    bounds = None
    info = {"name": a.name, "class": a.cls_name, "collection": a.name}
    check_names(a, F)
    if check_meta(a, F):
        check_structure(a, F)
        if a.renders:
            check_transforms(a, F)
            r = check_scale_and_pivot(a, F)
            tris = check_budget(a, F)
            check_geometry(a, F)
            check_uv_and_materials(a, F)
            check_collision(a, F)
            check_lods(a, F, tris)
            check_skeleton(a, F)
            lod0 = a.lod0()
            if lod0 is not None:
                mn, mx = common.world_bounds(lod0)
                bounds = common.bounds_report(mn, mx, _origin_for_pivot(a))
    info["tris_per_lod"] = {"LOD%d" % k: v for k, v in sorted(tris.items())}
    info["bounds"] = bounds
    info["errors"] = F.count(ERROR)
    info["warnings"] = F.count(WARNING)
    info["findings"] = F.items
    return info


def validate_scene(only=(), default_class=None, strict=False):
    common.ensure_object_mode()
    findings = []
    check_scene(findings)
    assets = common.find_assets(only=only, default_class=default_class)
    results = [validate_asset(a) for a in assets]
    for r in results:
        r["passed"] = r["errors"] == 0 and not (strict and r["warnings"])
    orph = common.orphan_meshes(assets)
    if not assets:
        findings.append({"code": "NO_ASSETS", "severity": ERROR, "asset": None,
                         "message": "no asset collections found (collections named SM_*/SK_* or with %s)" % C.META_CLASS})
    elif orph:
        findings.append({"code": "ORPHAN_OBJECTS", "severity": WARNING, "asset": None,
                         "message": "%d mesh objects are outside any asset collection and will not be exported: %s"
                                    % (len(orph), ", ".join(o.name for o in orph[:8]))})
    scene_errors = sum(1 for f in findings if f["severity"] == ERROR)
    scene_warnings = sum(1 for f in findings if f["severity"] == WARNING)
    passed = scene_errors == 0 and all(r["passed"] for r in results) and not (strict and scene_warnings)
    return {
        "tool": "validate", "schema_version": C.SCHEMA_VERSION,
        "blender": bpy.app.version_string, "file": bpy.data.filepath, "strict": strict,
        "passed": passed,
        "summary": {"assets": len(results), "assets_passed": sum(1 for r in results if r["passed"]),
                    "errors": scene_errors + sum(r["errors"] for r in results),
                    "warnings": scene_warnings + sum(r["warnings"] for r in results)},
        "scene_findings": findings,
        "assets": results,
    }


def main():
    p = common.make_parser("validate.py", __doc__.split("\n")[0])
    p.add_argument("--class", dest="default_class", help="class to assume for assets that lack %s" % C.META_CLASS)
    p.add_argument("--strict", action="store_true", help="warnings also fail")
    args = p.parse_args(common.script_argv())
    try:
        common.open_blend(args.blend)
    except (RuntimeError, SystemExit) as e:
        common.emit({"tool": "validate", "passed": False, "fatal": str(e)}, args.report)
        common.finish(2)
    report = validate_scene(args.collection, args.default_class, args.strict)
    common.emit(report, args.report)
    common.finish(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
