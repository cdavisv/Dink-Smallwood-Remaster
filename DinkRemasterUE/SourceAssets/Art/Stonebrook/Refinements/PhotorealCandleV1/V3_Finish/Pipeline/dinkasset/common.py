"""Shared Blender-side helpers for the dinkasset scripts (needs bpy).

Every script is started as:
    blender -b --factory-startup [file.blend] -P dinkasset/<script>.py -- <args>
and talks to its caller through (1) a JSON report between marker lines on stdout,
(2) an optional --report file, (3) the process exit code.
"""
import argparse
import array
import contextlib
import hashlib
import json
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

from dinkasset import conventions as C

REPORT_BEGIN = "@@DINK_REPORT_BEGIN@@"
REPORT_END = "@@DINK_REPORT_END@@"

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/blender
DEFAULT_OUT = os.path.join(TOOLS_DIR, "out")


# --- CLI ------------------------------------------------------------------------

def script_argv():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def make_parser(prog, description):
    p = argparse.ArgumentParser(prog=prog, description=description)
    p.add_argument("--blend", help="open this .blend (otherwise the file Blender was started with)")
    p.add_argument("--collection", action="append", default=[],
                   help="only this asset collection (repeatable); default: every asset collection")
    p.add_argument("--report", help="also write the JSON report to this file")
    return p


def open_blend(path):
    if path:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(path))
    if not bpy.data.filepath:
        raise SystemExit("no .blend loaded: pass --blend FILE (or start Blender with the file)")
    return bpy.data.filepath


def emit(report, path=None):
    text = json.dumps(report, indent=2)
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            f.write(text + "\n")
    sys.stdout.write("\n%s\n%s\n%s\n" % (REPORT_BEGIN, text, REPORT_END))
    sys.stdout.flush()


def finish(code):
    """Flush and exit with a status code that Blender passes through."""
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(code)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_object_mode():
    try:
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        pass


# --- Assets -----------------------------------------------------------------------

class Asset:
    """One asset == one collection. Objects are classified by name and type."""

    def __init__(self, coll):
        self.coll = coll
        self.name = coll.name
        self.cls_name = coll.get(C.META_CLASS)
        self.refresh()

    @property
    def cls(self):
        return C.CLASSES.get(self.cls_name)

    def meta(self, key, default=None):
        return self.coll.get(key, default)

    def refresh(self):
        self.renders = []        # mesh objects that are not collision
        self.collision = []
        self.armatures = []
        self.sockets = []
        self.other = []
        for ob in self.coll.all_objects:
            if ob.type == "MESH":
                if ob.name.startswith(("UCX_", "UBX_", "USP_", "UCP_")):
                    self.collision.append(ob)
                else:
                    self.renders.append(ob)
            elif ob.type == "ARMATURE":
                self.armatures.append(ob)
            elif ob.type == "EMPTY" and ob.name.startswith("SOCKET_"):
                self.sockets.append(ob)
            else:
                self.other.append(ob)
        self.renders.sort(key=lambda o: (lod_index(o.name), o.name))
        self.collision.sort(key=lambda o: o.name)

    def lods(self):
        """{lod index: [objects]}; an unsuffixed mesh counts as LOD0."""
        out = {}
        for ob in self.renders:
            out.setdefault(lod_index(ob.name), []).append(ob)
        return out

    def lod0(self):
        objs = self.lods().get(0)
        return objs[0] if objs else None

    def all_objects(self):
        return list(self.coll.all_objects)

    def top_level_objects(self):
        """Objects whose parent is not part of this asset (they carry the placement)."""
        members = set(self.coll.all_objects)
        return [o for o in members if o.parent not in members]


def lod_index(name):
    m = C.LOD_RE.match(name)
    return int(m.group("n")) if m else 0


def lod_base(name):
    m = C.LOD_RE.match(name)
    return m.group("base") if m else name


def find_assets(only=(), default_class=None):
    """Asset collections reachable from the active scene.

    A collection is an asset if it carries dink_class, or is named SM_*/SK_*, or was
    asked for by name. Child collections of an asset are part of it, not assets.
    """
    scene = bpy.context.scene
    found = []
    seen = set()

    def walk(coll, inside_asset):
        for ch in coll.children:
            is_asset = (ch.name in only) if only else (
                C.META_CLASS in ch or ch.name.startswith(("SM_", "SK_")))
            if is_asset and not inside_asset and ch.name not in seen:
                seen.add(ch.name)
                a = Asset(ch)
                if a.cls_name is None and default_class:
                    a.cls_name = default_class
                found.append(a)
                walk(ch, True)
            else:
                walk(ch, inside_asset)

    walk(scene.collection, False)
    return found


def orphan_meshes(assets):
    claimed = set()
    for a in assets:
        claimed.update(a.coll.all_objects)
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and o not in claimed]


def set_meta(coll, cls_name=None, path=None, **extra):
    if cls_name is not None:
        coll[C.META_CLASS] = cls_name
    if path is not None:
        coll[C.META_PATH] = path
    for k, v in extra.items():
        coll[k] = v


# --- Geometry helpers ---------------------------------------------------------------

def eval_object(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(dg)


def tri_count(obj, evaluated=True):
    """Triangles the exporter will write for this object (quads/ngons triangulated)."""
    if obj.type != "MESH":
        return 0
    if evaluated:
        ev = eval_object(obj)
        me = ev.to_mesh()
        try:
            me.calc_loop_triangles()
            return len(me.loop_triangles)
        finally:
            ev.to_mesh_clear()
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def world_bounds(obj, evaluated=True):
    """World-aligned (min, max) Vectors of an object's bounding box, in metres."""
    ob = eval_object(obj) if evaluated else obj
    corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = Vector((min(c[i] for c in corners) for i in range(3)))
    mx = Vector((max(c[i] for c in corners) for i in range(3)))
    return mn, mx


def local_vertices(mesh):
    n = len(mesh.vertices)
    a = array.array("f", [0.0]) * (n * 3)
    mesh.vertices.foreach_get("co", a)
    return a


def mesh_bounds_local(mesh):
    a = local_vertices(mesh)
    if not a:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    mn = Vector((min(a[i::3]) for i in range(3)))
    mx = Vector((max(a[i::3]) for i in range(3)))
    return mn, mx


def union_bounds(objs):
    mins, maxs = [], []
    for o in objs:
        mn, mx = world_bounds(o)
        mins.append(mn)
        maxs.append(mx)
    if not mins:
        return Vector(), Vector()
    return (Vector(min(m[i] for m in mins) for i in range(3)),
            Vector(max(m[i] for m in maxs) for i in range(3)))


def to_cm(v):
    return [round(x * C.UNIT_TO_CM, 3) for x in v]


def bounds_report(mn, mx, origin=Vector((0, 0, 0))):
    """Bounds relative to the pivot, Blender axes and Unreal axes, in cm."""
    rmn, rmx = mn - origin, mx - origin
    size = rmx - rmn
    return {
        "blender_min_cm": to_cm(rmn), "blender_max_cm": to_cm(rmx), "size_cm": to_cm(size),
        # Unreal asset space after import: x -> x, y -> -y, z -> z (FBX is right-handed, UE left-handed)
        "unreal_min_cm": to_cm((rmn.x, -rmx.y, rmn.z)),
        "unreal_max_cm": to_cm((rmx.x, -rmn.y, rmx.z)),
    }


@contextlib.contextmanager
def bmesh_of(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        yield bm
    finally:
        bm.free()


def poly_tri_count(mesh):
    return sum(len(p.vertices) - 2 for p in mesh.polygons)


# --- Pivot ----------------------------------------------------------------------------

def pivot_target(rule, mn, mx, sockets=None):
    """Where the pivot SHOULD be, in the same space as mn/mx. None if undeterminable.

    mn/mx are bounds relative to the current origin (origin = (0,0,0))."""
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    if rule == "base_center" or rule == "feet":
        return Vector((cx, cy, mn.z))
    if rule == "grid_wall" or rule == "hinge":
        return Vector((mn.x, cy, mn.z))
    if rule == "grid_floor":
        return Vector((mn.x, mn.y, mx.z))
    if rule == "grid_ceiling":
        return Vector((mn.x, mn.y, mn.z))
    if rule == "grid_piece":
        snap = C.SUBGRID_M
        return Vector((round(cx / snap) * snap, round(cy / snap) * snap, mn.z))
    if rule == "grip":
        if sockets:
            return Vector(sockets[0])
        return None
    return None


def pivot_error(rule, mn, mx, tol_xy=None, sockets_present=False):
    """Return (ok, offset Vector from where the pivot should be, note). Offset is
    expected_target - current_origin in metres, i.e. how far the origin is off."""
    tol = C.SNAP_TOL_M
    txy = tol_xy if tol_xy is not None else tol
    if rule == "grip":
        e = Vector((0.05, 0.05, 0.05))
        inside = all(mn[i] - e[i] <= 0 <= mx[i] + e[i] for i in range(3))
        return inside, Vector((0, 0, 0)), "origin must be inside the mesh bounds (at the grip)"
    tgt = pivot_target(rule, mn, mx)
    if tgt is None:
        return True, Vector(), ""
    off = tgt  # origin is (0,0,0): the target position is the offset
    if rule == "grid_piece":
        ok = abs(off.z) <= tol and (mn.x - tol <= 0 <= mx.x + tol) and (mn.y - tol <= 0 <= mx.y + tol)
        return ok, off, "origin must be on a grid vertex at floor level inside the footprint"
    if rule == "base_center":
        # bounds centre +-10 % of the extent, so a protruding handle or spout does not force a lopsided pivot
        tx = max(tol, 0.1 * (mx.x - mn.x))
        ty = max(tol, 0.1 * (mx.y - mn.y))
    elif rule == "feet":
        tx = ty = txy
    else:
        tx = ty = tol
    ok = abs(off.z) <= tol and abs(off.x) <= tx and abs(off.y) <= ty
    return ok, off, ""


# --- Transform application -----------------------------------------------------------------

def reset_rotation_scale(obj):
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = (0, 0, 0)
    obj.rotation_quaternion = (1, 0, 0, 0)
    obj.scale = (1, 1, 1)
    obj.delta_rotation_euler = (0, 0, 0)
    obj.delta_scale = (1, 1, 1)


def transforms_dirty(obj):
    """(rotation_dirty, scale_dirty, negative_scale) for rotation/scale incl. deltas.
    A pure axis flip counts as negative scale only, not as rotation."""
    m = obj.matrix_basis.to_3x3()
    cols = [Vector((m[0][j], m[1][j], m[2][j])) for j in range(3)]
    lens = [c.length for c in cols]
    scale_dirty = any(abs(l - 1.0) > 1e-4 for l in lens)
    rot_dirty = any(abs(abs(cols[j][i] / (lens[j] or 1.0)) - (1.0 if i == j else 0.0)) > 1e-4
                    for j in range(3) for i in range(3))
    return rot_dirty, scale_dirty, m.determinant() < 0


def apply_rotation_scale(obj):
    """Bake rotation and scale into the mesh (keeps location). Handles shared data,
    shape keys and mirrored (negative-scale) objects. Returns True if anything changed."""
    if obj.type != "MESH":
        return False
    rot, scl, neg = transforms_dirty(obj)
    if not (rot or scl or neg):
        return False
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    loc = obj.matrix_basis.translation.copy()
    rs = obj.matrix_basis.to_3x3().to_4x4()
    flip = rs.determinant() < 0
    obj.data.transform(rs, shape_keys=True)
    if flip:
        obj.data.flip_normals()
    reset_rotation_scale(obj)
    obj.delta_location = (0, 0, 0)
    obj.location = loc
    obj.data.update()
    return True


def unparent_keep_world(obj):
    if obj.parent is None:
        return False
    mw = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = mw
    return True


def shift_pivot(objs, delta_world):
    """Move the origin of every object by delta_world (Vector) without moving geometry.
    Objects must have rotation/scale applied."""
    for ob in objs:
        if ob.type == "MESH":
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            ob.data.transform(Matrix.Translation(-delta_world))
            ob.data.update()
        ob.location = ob.location + delta_world


@contextlib.contextmanager
def at_origin(asset, reference=None):
    """Temporarily move the asset so the reference object's origin sits at the world
    origin (export is always at the origin); restore afterwards."""
    ref = reference or asset.lod0() or (asset.renders[0] if asset.renders else None)
    tops = asset.top_level_objects()
    saved = [(o, o.location.copy()) for o in tops]
    if ref is not None:
        delta = ref.matrix_world.translation.copy()
        for o in tops:
            o.location = o.location - delta
        bpy.context.view_layer.update()
    try:
        yield
    finally:
        for o, loc in saved:
            o.location = loc
        bpy.context.view_layer.update()


def select_only(objs):
    ensure_object_mode()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def clean_name(text, default="Asset"):
    """'old barrel.001' -> 'OldBarrel' (PascalCase tokens, ASCII, no dot suffix)."""
    import re
    text = re.sub(r"\.\d+$", "", text)
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", text) if t]
    out = []
    for t in toks:
        out.append(t[0].upper() + t[1:])
    s = "_".join(out) if out else default
    # PascalCase inside one token is fine; tokens joined by underscore stay separate
    return s


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_object_mode()
