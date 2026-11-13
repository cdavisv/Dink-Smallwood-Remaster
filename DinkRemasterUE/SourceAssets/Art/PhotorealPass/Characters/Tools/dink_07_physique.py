"""Stage 7: the hero's builds. Adds the shape keys Physique_Scrawny and Physique_Brawny (see physique.py) to all four
LODs of SK_Dink_Photoreal.blend, writes Dink/physique_report.json (tape measurements of the three builds) and saves.
Re-running replaces the keys. blender -b -P dink_07_physique.py [-- <blend rel to the Characters folder>]"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
import physique as PH
a = args(); blend = OUT / (a[0] if a else 'Dink/SK_Dink_Photoreal.blend')
bpy.ops.wm.open_mainfile(filepath=str(blend))
arm = bpy.data.objects['Armature']; heads = {b.name: list(b.head_local) for b in arm.data.bones}
report = {'schema': 'dink-hero-physique/1', 'keys': [PH.KEY % b for b in PH.BUILDS], 'lods': [], 'tape_cm': {}}
for lod in range(4):
    ob = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('_LOD%d' % lod)); me = ob.data
    if me.shape_keys:
        for k in list(me.shape_keys.key_blocks)[::-1]: ob.shape_key_remove(k)
    co = co_np(me); W = PH.weights_of(ob); ob.shape_key_add(name='Basis', from_mix=False); row = {'mesh': ob.name, 'vertices': len(co)}
    for b in PH.BUILDS:
        d = PH.field(co, W, heads, b); k = ob.shape_key_add(name=PH.KEY % b, from_mix=False)
        k.data.foreach_set('co', np.asarray(co + d, np.float32).ravel()); k.value = 0.0; k.slider_min = 0.0; k.slider_max = 1.0
        mag = np.linalg.norm(d, axis=1)
        row[b] = {'moved_vertices': int((mag > 1e-5).sum()), 'max_mm': round(float(mag.max()) * 1000, 2), 'mean_mm': round(float(mag[mag > 1e-5].mean()) * 1000, 2)}
        if lod == 0:
            zero = np.zeros(len(co)); H = lambda n: np.array(heads[n])
            if not report['tape_cm']:
                # the tape is laid on the SAME vertices for every build: slices are chosen on the exported mesh
                g = lambda *n: sum((W.get(x, zero) for x in n), zero.copy())
                up = lambda A, B, t: H(A) + (H(B) - H(A)) * t
                torso = (g('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'clavicle_l', 'clavicle_r') > .5) & (co[:, 1] < .12)   # pack left out
                def ring(mask, origin, axis, half=.006):
                    u = np.asarray(axis, float); u = u / np.linalg.norm(u); return (mask & (np.abs((co - origin) @ u) < half), np.asarray(origin, float), u)
                RINGS = {'chest_girth': ring(torso, [0, 0, 1.33], [0, 0, 1]), 'waist_girth': ring(torso, [0, 0, 1.06], [0, 0, 1]),
                         'neck_girth': ring((g('neck_01', 'neck_02') > .15) & (g('head') < .5), up('neck_01', 'head', .45), H('head') - H('neck_01'), .012),
                         'upper_arm_girth': ring(g('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l') > .5, up('upperarm_l', 'lowerarm_l', .45), H('lowerarm_l') - H('upperarm_l')),
                         'forearm_girth': ring(g('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l') > .5, up('lowerarm_l', 'hand_l', .25), H('hand_l') - H('lowerarm_l')),
                         'thigh_girth': ring(g('thigh_l', 'thigh_twist_01_l', 'thigh_twist_02_l') > .5, up('thigh_l', 'calf_l', .35), H('calf_l') - H('thigh_l')),
                         'calf_girth': ring(g('calf_l', 'calf_twist_01_l', 'calf_twist_02_l') > .5, up('calf_l', 'foot_l', .3), H('foot_l') - H('calf_l'))}
                SH = (np.linalg.norm(co - H('upperarm_l'), axis=1) < .10) | (np.linalg.norm(co - H('upperarm_r'), axis=1) < .10)
                def tape(c):
                    out = {'shoulder_width': round(float(c[SH, 0].max() - c[SH, 0].min()) * 100, 1)}
                    for name, (sel, origin, u) in RINGS.items(): out[name] = round(PH.girth(c, sel, origin, u, half=1.0) * 100, 1)
                    out['height'] = round(float(c[:, 2].max()) * 100, 1); return out
                report['tape_cm']['Farmhand'] = tape(co)
            report['tape_cm'][b] = tape(co + d)
    report['lods'].append(row)
    log('LOD%d' % lod, json.dumps(row))
report['tape_note'] = 'Measured over the clothes on LOD0 in the rest pose (convex girths in cm; the pack is left out). Farmhand is the exported mesh.'
(OUT / 'Dink/physique_report.json').write_text(json.dumps(report, indent=1) + '\n')
log('TAPE', json.dumps(report['tape_cm']))
save_blend()
log('PHYSIQUE DONE')
