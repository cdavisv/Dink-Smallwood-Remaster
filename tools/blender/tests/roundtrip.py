"""Re-import an exported FBX/GLB into an empty scene and print what Blender sees as JSON.

    blender -b --factory-startup -P tests/roundtrip.py -- --file X.fbx [--report r.json]

This is the unit/axis round trip: if the exporter or the file header were wrong, sizes
(metres x100 = cm) or the front marker direction would be off here.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import bpy  # noqa: E402
from dinkasset import common  # noqa: E402


def main():
    argv = common.script_argv()
    path = argv[argv.index("--file") + 1]
    report_path = argv[argv.index("--report") + 1] if "--report" in argv else None
    common.reset_scene()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    objs = []
    arms = []
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH":
            mn, mx = common.world_bounds(ob)
            objs.append({"name": ob.name, "parent": ob.parent.name if ob.parent else None,
                         "tris": common.tri_count(ob),
                         "min_cm": common.to_cm(mn), "max_cm": common.to_cm(mx),
                         "size_cm": common.to_cm(mx - mn)})
        elif ob.type == "ARMATURE":
            arms.append({"name": ob.name, "bones": [
                {"name": b.name, "head_cm": common.to_cm(ob.matrix_world @ b.head_local),
                 "tail_cm": common.to_cm(ob.matrix_world @ b.tail_local)} for b in ob.data.bones]})
    common.emit({"tool": "roundtrip", "file": path, "meshes": objs, "armatures": arms}, report_path)


if __name__ == "__main__":
    main()
