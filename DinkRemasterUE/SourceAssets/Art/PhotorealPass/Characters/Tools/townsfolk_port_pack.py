"""The parts file of a townsman who keeps the clothes of his Unclaimed source (a robe: townsfolk.py `body='port'`).

    NPC_PORT_ONLY=1 blender -b -t 4 --python npc_port.py -- <Name> <abs>/NPC/<Name>/Work      the source on the mannequin rig, no export
    blender -b -t 4 --python townsfolk_port_pack.py -- <Name>

Reads NPC/<Name>/Work/SK_<Name>_Photoreal.blend (npc_port.py: every LOD of the Unclaimed figure carried onto the
89-bone rig by its own skin weights); writes NPC/<Name>/Work/<name>_packed.blend, the input of dink_06_assemble.py:
the clothes of LOD0 only, with the weights of the port (`weights: keep`). The ported skin, eyes and modelled hair go, and so
does every piece of the outfit that lies inside a `drop` box of the row (the old man's beard, a slab of clay in the
outfit's atlas): head, hands, hair and beard come from the head, skin and groom stages. Pieces inside a `gear` box
(shoes, a cane) go to the Gear slot, which shows the same texture files as the Outfit slot."""
import bpy, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from prlib import OUT, log, args, save_blend
from townsfolk import TOWNSFOLK
NAME = args()[0]; ROW = TOWNSFOLK[NAME]; DIR = OUT / 'NPC' / NAME; n_ = NAME.lower()
bpy.ops.wm.open_mainfile(filepath=str(DIR / 'Work' / f'SK_{NAME}_Photoreal.blend'))
D = bpy.data.objects; lod0 = D[f'SK_{NAME}_Photoreal_LOD0']
for o in list(D):
    if o.type == 'MESH' and o is not lod0: bpy.data.objects.remove(o, do_unlink=True)
import bmesh
bm = bmesh.new(); bm.from_mesh(lod0.data); bm.faces.ensure_lookup_table()
slot = {i: (m.material.name.split('_PR_')[-1] if m.material else '') for i, m in enumerate(lod0.material_slots)}
seen = set(); kinds = {'drop': [], 'gear': [], 'outfit': []}; report = []


def inside(lo, hi, box): return all(lo[k] >= box[2 * k] and hi[k] <= box[2 * k + 1] for k in range(3))


for f0 in bm.faces:
    if f0.index in seen: continue
    st = [f0]; comp = []; seen.add(f0.index)
    while st:      # one connected piece
        f = st.pop(); comp.append(f)
        for e in f.edges:
            for g in e.link_faces:
                if g.index not in seen: seen.add(g.index); st.append(g)
    P = np.array([v.co[:] for f in comp for v in f.verts]); lo, hi = P.min(0), P.max(0); sl = slot[comp[0].material_index]
    kind = 'drop' if sl != 'Outfit' or any(inside(lo, hi, b) for b in ROW.get('drop', ())) else 'gear' if any(inside(lo, hi, b) for b in ROW.get('gear', ())) else 'outfit'
    kinds[kind].extend(comp); report.append((kind, sl, len(comp), [round(float(x), 2) for x in lo], [round(float(x), 2) for x in hi]))
for r in sorted(report, key=lambda r: -r[2])[:20]: log('piece', *r)
bmesh.ops.delete(bm, geom=kinds['drop'], context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
gear = set(kinds['gear']); bm.faces.ensure_lookup_table()
for f in bm.faces: f.select = f in gear
bm.to_mesh(lod0.data); bm.free(); lod0.data.update()
bpy.context.view_layer.objects.active = lod0; lod0.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
parts = [o for o in bpy.context.selected_objects if o.type == 'MESH']
other = next((o for o in parts if o is not lod0), None)
lod0.name = 'Robe'; lod0.data.name = 'Robe'; lod0['fabric'] = ROW.get('fabric', 'wool'); lod0['mat'] = 'outfit'; lod0['weights'] = 'keep'
if other is not None: other.name = 'Shoes'; other.data.name = 'Shoes'; other['fabric'] = 'leather_boot'; other['mat'] = 'gear'; other['weights'] = 'keep'
extra = []
if ROW.get('undersleeve'):
    # The hero's skin ends at the wrist: inside a wide sleeve the hands hung in the air. An under-sleeve per arm: a narrow
    # tube of the robe's own cloth from the heel of the hand up the forearm into the sleeve, rigid on the forearm bone,
    # its far end closed. It is short (it must not reach the elbow, where it came out through the bent sleeve) and takes
    # one texel of the sleeve's own cloth.
    import math
    from mathutils import Vector
    us = ROW['undersleeve']; arm = next(o for o in D if o.type == 'ARMATURE'); me0 = lod0.data
    rco = np.array([v.co[:] for v in me0.vertices]); ruv = np.zeros((len(me0.vertices), 2)); uvl0 = me0.uv_layers.active.data
    for l in me0.loops: ruv[l.vertex_index] = uvl0[l.index].uv[:]
    for sd in ('l', 'r'):
        E = np.array(arm.data.bones['lowerarm_' + sd].head_local); Wp = np.array(arm.data.bones['hand_' + sd].head_local); ax = (Wp - E) / np.linalg.norm(Wp - E)
        a = np.cross(ax, [0.0, 0.0, 1.0]); a /= np.linalg.norm(a); b = np.cross(ax, a); NS = 10; NR = 5; verts = []; faces = []
        for k in range(NR + 1):
            t = k / NR; c = Wp + ax * (us['over'] - (us['over'] + us['length']) * t); r = us['r0'] + (us['r1'] - us['r0']) * t ** .8
            if k == 0: r *= .94      # the cuff closes on the hand a little
            for j in range(NS):
                ph = 2 * math.pi * j / NS; verts.append(tuple(c + (a * math.cos(ph) + b * math.sin(ph)) * r * (1 + .05 * math.sin(3 * ph + k))))
        for k in range(NR):
            for j in range(NS):
                q = (k * NS + j, k * NS + (j + 1) % NS, (k + 1) * NS + (j + 1) % NS, (k + 1) * NS + j); faces.append(q if sd == 'r' else tuple(reversed(q)))
        cap = tuple(range(NR * NS, NR * NS + NS)); faces.append(cap if sd == 'r' else tuple(reversed(cap)))
        m_ = bpy.data.meshes.new('UnderSleeve_' + sd); m_.from_pydata(verts, [], faces); m_.update(); o_ = bpy.data.objects.new('UnderSleeve_' + sd, m_); bpy.context.scene.collection.objects.link(o_)
        # faces must look outwards whatever the handedness of the frame
        ctr = np.mean(np.array(verts), axis=0); flip = sum(1 for p in m_.polygons[:NS] if (np.array(p.center) - ctr - ax * ((np.array(p.center) - ctr) @ ax)) @ np.array(p.normal) < 0) > NS / 2
        if flip: m_.flip_normals()
        side_ok = (rco[:, 0] > .15) if Wp[0] > 0 else (rco[:, 0] < -.15); idx = np.nonzero(side_ok)[0]; uvl = m_.uv_layers.new(name=me0.uv_layers.active.name)
        mid = E + (Wp - E) * .45; one = int(idx[np.argmin(((rco[idx] - mid) ** 2).sum(1))])      # ONE texel of the sleeve's own cloth, at the middle of the forearm: the nearest-vertex UVs put pale texels of other islands on the tube (a light peg at the elbow in the game)
        for l in m_.loops: uvl.data[l.index].uv = tuple(ruv[one])
        for p in m_.polygons: p.use_smooth = True
        o_['fabric'] = ROW.get('fabric', 'wool'); o_['mat'] = 'outfit'; o_['rigidw'] = 'lowerarm_%s:1.0' % sd; extra.append(o_)
        log('under-sleeve', sd, 'faces', len(m_.polygons), 'from the hand', us['over'], 'up the forearm', us['length'], 'flipped', flip)
for o in (lod0, other):
    if o is None: continue
    for m in list(o.modifiers): o.modifiers.remove(m)
    o.hide_render = False
    log('part', o.name, 'faces', len(o.data.polygons), 'groups', len(o.vertex_groups))
save_blend(filepath=str(DIR / 'Work' / f'{n_}_packed.blend'))
log('packed', NAME, {k: len(v) for k, v in kinds.items()})
