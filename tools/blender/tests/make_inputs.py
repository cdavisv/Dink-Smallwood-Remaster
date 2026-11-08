"""Write fake image-to-3D generator outputs (OBJ, GLB, FBX) with arbitrary scale/pivot.

    blender -b --factory-startup -P tests/make_inputs.py -- --out DIR

Files: gen_barrel.obj (Y-up, 2.7 units tall, centred), gen_barrel.glb (1.8 m, centred),
gen_barrel.fbx (cm-ish scale), gen_barrel_lying.obj (axis along X, needs --rotate), gen_dense.glb (~59k tris).
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix  # noqa: E402

from dinkasset import common  # noqa: E402
import build_assets as B  # noqa: E402


def make(scale, rot=None, name="gen"):
    common.reset_scene()
    bm = B.barrel_bm(scale=scale)
    ys = [v.co.z for v in bm.verts]
    bmesh.ops.translate(bm, vec=(0, 0, -(max(ys) + min(ys)) / 2), verts=bm.verts)  # centre pivot
    if rot is not None:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rot)
    coll = bpy.data.collections.new("c")
    bpy.context.scene.collection.children.link(coll)
    ob = B.make_object(name, bm, coll)
    ob.data.materials.append(B.material("Material.001"))
    B.unwrap(ob)
    common.select_only([ob])
    return ob


def main():
    argv = common.script_argv()
    out = argv[argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    make(3.0)
    bpy.ops.wm.obj_export(filepath=os.path.join(out, "gen_barrel.obj"), export_selected_objects=True)
    make(2.0)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "gen_barrel.glb"), export_format="GLB", use_selection=True)
    make(100.0)  # authored in cm, exported without unit conversion
    bpy.ops.export_scene.fbx(filepath=os.path.join(out, "gen_barrel.fbx"), use_selection=True, apply_unit_scale=False)
    make(1.0, rot=Matrix.Rotation(math.pi / 2, 3, "Y"))
    bpy.ops.wm.obj_export(filepath=os.path.join(out, "gen_barrel_lying.obj"), export_selected_objects=True)
    # dense mesh: far over the prop budget (~59k triangles), like a raw image-to-3D result
    common.reset_scene()
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=200, v_segments=150, radius=0.5, calc_uvs=True)
    coll = bpy.data.collections.new("c")
    bpy.context.scene.collection.children.link(coll)
    ob = B.make_object("dense", bm, coll)
    ob.data.materials.append(B.material("Material.001"))
    common.select_only([ob])
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "gen_dense.glb"), export_format="GLB", use_selection=True)


if __name__ == "__main__":
    main()
