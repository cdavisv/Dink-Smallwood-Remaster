"""Mother's body for the SCR_001 vision-1 fire (original S001_P34, seq 355 'people/mom/death-':
she lies dead on the floor of the burning room with blood around her).  Owner decision: keep the
original's grim content, do not sanitise.

Opens Characters/SK_Mother.blend READ-ONLY (never saved), poses the armature (face down, head
turned on the cheek, right arm flung above the head, left leg drawn up), bakes the pose into static
copies of her LOD0..LOD2 meshes and saves ONLY those into StonebrookRuins/Working/.
Mesh provenance: CC0 MakeHuman anatomy + project wardrobe (see Characters/README.md).

    blender -b --factory-startup -t 3 -P pose_mother_remains.py
"""
import bpy, math
from pathlib import Path
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
KIT = HERE.parent; UE = KIT.parents[2]
SRC = UE / 'SourceAssets/Art/Characters/SK_Mother.blend'
OUT = KIT / 'Working'; OUT.mkdir(exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SRC))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
bpy.context.view_layer.objects.active = arm
print('STEP pose', flush=True)
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'


def rot(bone, axis, deg):
    """Rotate a pose bone about an armature-space axis through its head."""
    pb = arm.pose.bones[bone]
    bpy.context.view_layer.update()
    m = pb.matrix.copy(); head = m.translation.copy()
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-head)
    pb.matrix = R @ m
    bpy.context.view_layer.update()


# Standing frame: front -Y, up +Z, her left +X.  Later the whole body is laid face down.
rot('spine_02', (0, 0, 1), 9); rot('spine_04', (0, 0, 1), 8)
rot('neck_01', (0, 0, 1), 30); rot('head', (0, 0, 1), 55); rot('head', (0, 1, 0), -12)
rot('upperarm_r', (0, 1, 0), 95); rot('upperarm_r', (1, 0, 0), -15)
rot('lowerarm_r', (1, 0, 0), -35)
rot('hand_r', (0, 1, 0), 20)
rot('upperarm_l', (0, 1, 0), -18); rot('lowerarm_l', (1, 0, 0), -25)
rot('thigh_l', (0, 1, 0), -32); rot('thigh_l', (1, 0, 0), -18)
rot('calf_l', (1, 0, 0), 20)
rot('foot_l', (1, 0, 0), 30)
rot('thigh_r', (0, 1, 0), 6)
rot('foot_r', (1, 0, 0), 40)
print('STEP posed', flush=True)

dg = bpy.context.evaluated_depsgraph_get()
lay = Matrix.Rotation(math.radians(90), 4, 'X')        # face down: front (-Y) -> -Z
out_objs = []
for lod in range(3):
    src = bpy.data.objects[f'SK_Mother_LOD{lod + 1}']     # character LOD1-3 -> prop LOD0-2 (static budget)
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    me.transform(src.matrix_world); me.transform(lay)
    ob = bpy.data.objects.new(f'MotherRemains_LOD{lod}', me)
    out_objs.append(ob)
# rest on the floor, centred
co = [v.co for v in out_objs[0].data.vertices]
mn = Vector([min(c[i] for c in co) for i in range(3)]); mx = Vector([max(c[i] for c in co) for i in range(3)])
shift = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
for ob in out_objs:
    ob.data.transform(Matrix.Translation(-shift))
    ob.data.name = ob.name + '_Mesh'
    # dead weight: the rigid, leg-skinned skirt and the back settle toward the floor
    for v in ob.data.vertices:
        z = v.co.z
        if z > .16:
            v.co.z = .16 + (z - .16) * .32

print('STEP baked', flush=True)
keep = set(out_objs)
for ob in list(bpy.data.objects):
    if ob not in keep:
        bpy.data.objects.remove(ob, do_unlink=True)
for ob in out_objs:
    bpy.context.scene.collection.objects.link(ob)
bpy.ops.outliner.orphans_purge(do_recursive=True)
# a NEW file in StonebrookRuins/Working; the character source is never written
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MotherRemains_posed.blend'), compress=True, copy=True)
print('MOTHER REMAINS posed: dims', tuple(round(d, 3) for d in (mx - mn)), 'verts', [len(o.data.vertices) for o in out_objs])
