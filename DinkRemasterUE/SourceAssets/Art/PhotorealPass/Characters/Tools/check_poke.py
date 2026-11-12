"""Numeric poke-through check for skirts: poses the assembled character through the walk samples and a turn and counts
inner-layer vertices (boots / hose, by material slot) that end up outside the skirt wall.
usage: blender -b --python check_poke.py -- <blend rel to OUT> <outer slot substr> <inner slot substr> [zmin zmax]"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
a = args(); bpy.ops.wm.open_mainfile(filepath=str(OUT / a[0]))
zmin = float(a[3]) if len(a) > 3 else .0; zmax = float(a[4]) if len(a) > 4 else 2.0
D = bpy.data.objects; arm = D['Armature']; arm.data.pose_position = 'POSE'
lod0 = next(o for o in D if o.type == 'MESH' and o.name.endswith('_LOD0'))
walk = json.loads((Path(__file__).parent / 'pose_cache/walk_poses.json').read_text())
slots = [s.material.name for s in lod0.material_slots]
oi = [i for i, n in enumerate(slots) if a[1] in n]; ii = [i for i, n in enumerate(slots) if a[2] in n]
poses = list(walk) + ['turn', 'idle']
for p in poses:
    reset_pose(arm)
    if p == 'idle': apply_world_pose(arm, load_idle())
    elif p == 'turn':
        apply_world_pose(arm, walk['walk_45']); rot_bone(arm, 'spine_01', (0, 0, 1), 14); rot_bone(arm, 'spine_03', (0, 0, 1), 14); rot_bone(arm, 'thigh_l', (0, 0, 1), 28)
    else: apply_world_pose(arm, walk[p])
    dg = bpy.context.evaluated_depsgraph_get(); ev = lod0.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices]); mi = np.array([t.material_index for t in me.loop_triangles]); tv = np.array([t.vertices[:] for t in me.loop_triangles])
    ot = tv[np.isin(mi, oi)]; outer_v = np.unique(ot)
    # the skirt part of the outer slot: the connected piece with the lowest hem
    bvh = BVHTree.FromPolygons([Vector(c) for c in co], [tuple(t) for t in ot])
    inner_v = np.unique(tv[np.isin(mi, ii)]); bad = 0; worst = 0.0; n = 0
    for vi in inner_v:
        c = Vector(co[vi])
        if not (zmin < c.z < zmax): continue
        loc, nrm, idx, dist = bvh.find_nearest(c, .12)
        if loc is None: continue
        n += 1
        if (c - loc).dot(nrm) > 0 and dist > .003:
            # ignore points that merely stick out below / above an open rim (nearest point on a boundary)
            l2, n2, i2, d2 = bvh.ray_cast(c, -nrm, .2)
            if l2 is not None and abs(d2 - dist) < .004: bad += 1; worst = max(worst, dist)
    log('POKE', p, 'inner verts tested', n, 'outside skirt', bad, 'worst mm', round(worst * 1000, 1))
    ev.to_mesh_clear()
