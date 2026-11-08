"""Procedurally build the self-test assets (run inside Blender).

    blender -b --factory-startup -P tests/build_assets.py -- --out DIR

Writes DIR/good.blend (convention-compliant apart from missing collision/LODs, which
the tests generate) and DIR/broken.blend (deliberate faults).

Every asset carries an asymmetric marker so axis mistakes are detectable:
  * SM_Barrel_01   a tap sticking out of the FRONT (-Y in Blender)
  * SM_Wall_Door_2m_01  a door opening at x 0.5..1.5 m
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from dinkasset import common  # noqa: E402
from dinkasset import conventions as C  # noqa: E402


def new_collection(name, cls_name, path="Test", offset=(0, 0, 0)):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    common.set_meta(coll, cls_name, path)
    return coll


def make_object(name, bm, coll, location=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location = location
    return ob


def unwrap(ob, margin=0.02):
    common.select_only([ob])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    return m


def revolve(profile, segments, close_bottom=True, close_top=True, flip=False):
    """Closed solid of revolution about Z from (radius, z) rings, bottom to top."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        ring = [bm.verts.new((r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z))
                for i in range(segments)]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if close_bottom:
        bm.faces.new(list(reversed(rings[0])))
    if close_top:
        bm.faces.new(rings[-1])
    bm.normal_update()
    if flip:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm, rings


def barrel_bm(scale=1.0, flip=False):
    """0.6 m wide, 0.9 m tall barrel standing on z=0, tap at the front (-Y)."""
    prof = [(0.26, 0.0), (0.285, 0.1), (0.30, 0.25), (0.31, 0.45), (0.30, 0.65), (0.285, 0.8), (0.26, 0.9)]
    bm, _ = revolve([(r * scale, z * scale) for r, z in prof], 24, flip=flip)
    # hoops: two bands of faces get material 1
    for f in bm.faces:
        zc = f.calc_center_median().z / scale
        if 0.08 < zc < 0.2 or 0.7 < zc < 0.82:
            f.material_index = 1
    # tap: a closed box shell poking out of the front, partly inside the staves
    tap = bmesh.new()
    bmesh.ops.create_cube(tap, size=1.0)
    bmesh.ops.scale(tap, vec=(0.06 * scale, 0.2 * scale, 0.06 * scale), verts=tap.verts)
    bmesh.ops.translate(tap, vec=(0, -0.36 * scale, 0.5 * scale), verts=tap.verts)
    tm = bpy.data.meshes.new("tap_tmp")
    tap.to_mesh(tm)
    tap.free()
    bm.from_mesh(tm)
    bpy.data.meshes.remove(tm)
    if flip:
        # keep the tap shell consistent with the flipped barrel
        pass
    return bm


def wall_door_bm():
    """2 m x 0.2 m x 3.5 m wall, centre line on y=0, 1 m x 2.2 m door opening at x 0.5..1.5."""
    outline = [(0, 0), (0.5, 0), (0.5, 2.2), (1.5, 2.2), (1.5, 0), (2.0, 0), (2.0, 3.5), (0, 3.5)]
    bm = bmesh.new()
    t = 0.1
    front = [bm.verts.new((x, -t, z)) for x, z in outline]
    back = [bm.verts.new((x, +t, z)) for x, z in outline]
    n = len(outline)
    bm.faces.new(list(reversed(front)))
    bm.faces.new(back)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def box_bm(sx, sy, sz, center):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=center, verts=bm.verts)
    return bm


def build_worm(coll, loc):
    """A creature-class tube skinned to a 4-bone chain. Custom skeleton: only 'root' is required."""
    bm = bmesh.new()
    rings = []
    for i in range(13):
        z = i * 0.1
        r = 0.12 if 0 < i < 12 else 0.09
        ring = [bm.verts.new((r * math.cos(2 * math.pi * k / 16), r * math.sin(2 * math.pi * k / 16), z)) for k in range(16)]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(16):
            l = (k + 1) % 16
            bm.faces.new((a[k], a[l], b[l], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    name = "SK_Test_Worm"
    mesh_ob = make_object(name, bm, coll, loc)
    # armature
    adata = bpy.data.armatures.new(name + "_Armature")
    arm = bpy.data.objects.new(name + "_Armature", adata)
    coll.objects.link(arm)
    arm.location = loc
    common.select_only([arm])
    bpy.ops.object.mode_set(mode="EDIT")
    bones = [("root", 0.0, 0.2, None), ("spine_01", 0.2, 0.6, "root"), ("spine_02", 0.6, 1.0, "spine_01"), ("head", 1.0, 1.2, "spine_02")]
    for bname, z0, z1, parent in bones:
        eb = adata.edit_bones.new(bname)
        eb.head = (0, 0, z0)
        eb.tail = (0, 0, z1)
        if parent:
            eb.parent = adata.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for bname, z0, z1, _ in bones:
        mesh_ob.vertex_groups.new(name=bname)
    for v in mesh_ob.data.vertices:
        for bname, z0, z1, _ in bones:
            if z0 - 1e-6 <= v.co.z <= z1 + 1e-6 or (bname == "head" and v.co.z > 1.0):
                mesh_ob.vertex_groups[bname].add([v.index], 1.0, "REPLACE")
                break
    mod = mesh_ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    mesh_ob.parent = arm
    mesh_ob.matrix_parent_inverse = arm.matrix_world.inverted()
    mesh_ob.data.materials.append(material("MI_Worm_Skin"))
    unwrap(mesh_ob)
    return mesh_ob, arm


def build_good(path):
    common.reset_scene()
    # barrel, deliberately placed away from the origin to prove export normalises placement
    coll = new_collection("SM_Barrel_01", "prop", "Test")
    ob = make_object("SM_Barrel_01", barrel_bm(), coll, (5.0, 3.0, 0.0))
    ob.data.materials.append(material("MI_Barrel_Wood"))
    ob.data.materials.append(material("MI_Barrel_Metal"))
    unwrap(ob)
    # wall module
    coll = new_collection("SM_Wall_Door_2m_01", "kit_wall", "Test")
    ob = make_object("SM_Wall_Door_2m_01", wall_door_bm(), coll, (10.0, 0.0, 0.0))
    ob.data.materials.append(material("MI_Stone_Trim_01"))
    unwrap(ob)
    # skinned creature
    coll = new_collection("SK_Test_Worm", "creature", "Test")
    build_worm(coll, (0.0, 10.0, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=path)


def build_broken(path):
    common.reset_scene()
    # 1. Many faults: wrong names, centimetre-authored mesh with scale+rotation, centre pivot,
    #    inverted normals, duplicate vertices, a loose vertex, default material name.
    coll = new_collection("Barrel old", "prop", "Test")
    bm = barrel_bm(scale=100.0, flip=True)  # centimetres, inverted
    # barrel authored along Z; rotate the data so the axis is local Y like a Y-up import
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-math.pi / 2, 3, "X"))
    bmesh.ops.translate(bm, vec=(0, 0, 0), verts=bm.verts)
    # centre pivot: shift so the origin is at the middle of the barrel (local y in [-45, 45])
    ys = [v.co.y for v in bm.verts]
    bmesh.ops.translate(bm, vec=(0, -(max(ys) + min(ys)) / 2, 0), verts=bm.verts)
    bm.verts.new((10.0, 10.0, 10.0))  # loose vertex
    bm.verts.ensure_lookup_table()
    bm.verts.new(bm.verts[3].co.copy())  # coincident duplicate vertex
    ob = make_object("Cylinder.003", bm, coll, (2.0, 2.0, 0.0))
    ob.scale = (0.01, 0.01, 0.01)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    m = bpy.data.materials.new("Material.001")
    ob.data.materials.append(m)
    ob.data.materials.append(bpy.data.materials.new("Material.002"))
    unwrap(ob)

    # 2. No UVs, 8 material slots, over the triangle budget, centre pivot.
    coll = new_collection("SM_NoUv_01", "prop", "Test")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=170, v_segments=100, radius=0.5, calc_uvs=False)
    ob = make_object("SM_NoUv_01", bm, coll, (6.0, 0.0, 0.5))
    for i in range(8):
        ob.data.materials.append(material("MI_Slot_%02d" % i))

    # 3. Kit wall that is off the grid and not at its grid corner.
    coll = new_collection("SM_Wall_Wrong_01", "kit_wall", "Test")
    ob = make_object("SM_Wall_Wrong_01", box_bm(2.3, 0.2, 3.3, (0, 0, 0)), coll, (10.0, 4.0, 0.0))
    ob.data.materials.append(material("MI_Stone_Trim_01"))
    unwrap(ob)

    # 4. A prop that is 100x too big (centimetres, scale never applied): hint expected.
    coll = new_collection("SM_Huge_01", "prop", "Test")
    bm, _ = revolve([(30.0, 0.0), (31.0, 45.0), (30.0, 90.0)], 16)
    ob = make_object("SM_Huge_01", bm, coll, (-5.0, 0.0, 0.0))
    ob.data.materials.append(material("MI_Barrel_Wood"))
    unwrap(ob)
    # 5. Mirrored (negative scale) box with a correct pivot otherwise.
    coll = new_collection("SM_Mirror_01", "prop", "Test")
    ob = make_object("SM_Mirror_01", box_bm(0.5, 0.4, 0.6, (0.3, 0, 0.3)), coll, (3.0, 3.0, 0.0))
    ob.data.materials.append(material("MI_Barrel_Wood"))
    unwrap(ob)
    ob.scale = (-1.0, 1.0, 1.0)

    # 6. Every face mapped onto the same UV square: overlapping UVs on a class that forbids them.
    coll = new_collection("SM_Stacked_01", "prop", "Test")
    ob = make_object("SM_Stacked_01", box_bm(0.5, 0.5, 0.5, (0, 0, 0.25)), coll, (0.0, 6.0, 0.0))
    ob.data.materials.append(material("MI_Barrel_Wood"))
    uv = ob.data.uv_layers.new(name="UVMap")
    corner = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]
    for poly in ob.data.polygons:
        for k, li in enumerate(poly.loop_indices):
            uv.uv[li].vector = corner[k % 4]

    # 7. Open box (one face missing) plus a zero-area triangle.
    coll = new_collection("SM_Open_01", "prop", "Test")
    bm = box_bm(0.5, 0.5, 0.5, (0, 0, 0.25))
    bm.faces.ensure_lookup_table()
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    bmesh.ops.delete(bm, geom=[top], context="FACES_ONLY")
    a = [bm.verts.new((1.0 + 0.1 * i, 0, 0.1)) for i in range(3)]  # collinear -> zero area
    bm.faces.new(a)
    ob = make_object("SM_Open_01", bm, coll, (0.0, 8.0, 0.0))
    ob.data.materials.append(material("MI_Barrel_Wood"))
    unwrap(ob)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def build_units_cm(path):
    """A barrel authored in a scene whose unit scale is 0.01 (1 Blender unit = 1 cm)."""
    common.reset_scene()
    coll = new_collection("SM_Cm_Barrel_01", "prop", "Test")
    ob = make_object("SM_Cm_Barrel_01", barrel_bm(scale=100.0), coll)
    ob.data.materials.append(material("MI_Barrel_Wood"))
    ob.data.materials.append(material("MI_Barrel_Metal"))
    unwrap(ob)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01
    bpy.ops.wm.save_as_mainfile(filepath=path)


def main():
    argv = common.script_argv()
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(common.DEFAULT_OUT, "tests")
    os.makedirs(out, exist_ok=True)
    build_good(os.path.join(out, "good.blend"))
    build_broken(os.path.join(out, "broken.blend"))
    build_units_cm(os.path.join(out, "units_cm.blend"))
    print("built test assets in", out)


if __name__ == "__main__":
    main()
