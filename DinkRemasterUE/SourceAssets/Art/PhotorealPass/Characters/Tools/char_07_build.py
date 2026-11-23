"""Stage 8b (non-hero characters): bake a body build into the assembled character. The shipped skins all stand on the
same template skeleton with much the same frame; the build is what tells a burly knight from a village woman at the
play camera. Uses the hero's physique fields (physique.py: a displacement field in rest space applied to every layer
and every LOD alike, so cloth and armour keep their spacing), at a strength, written straight into the vertices.
Run once after dink_06_assemble (which rebuilds the meshes).  blender -b --python char_07_build.py -- <Name> <Build> [strength]"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *
import physique as PH
N, build = args()[0], args()[1]; k = float(args()[2]) if len(args()) > 2 else 1.0
bpy.ops.wm.open_mainfile(filepath=str(OUT / N / ('SK_%s_Photoreal.blend' % N)))
arm = bpy.data.objects['Armature']; heads = {b.name: list(b.head_local) for b in arm.data.bones}
rows = []; ACFG = json.load(open(OUT / N / 'cfg' / 'assemble.json'))
for ob in sorted((o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name), key=lambda o: o.name):
    me = ob.data
    if me.shape_keys: raise SystemExit('char_07_build: %s has shape keys; a baked build would not follow them' % ob.name)
    co = co_np(me); d = PH.field(co, PH.weights_of(ob), heads, build) * k
    set_co(me, co + d); me.update(); mag = np.linalg.norm(d, axis=1)
    RX = ACFG.get('skin_relax')
    if RX:      # the skin an open neckline shows is the coarse body under the dress: its kinks are combed out (Taubin, no shrinking), borders of the skin stay where they are
        si = [i for i, m in enumerate(me.materials) if m and 'Skin' in m.name]; c2 = co_np(me); use = np.zeros(len(c2), bool)
        for p_ in me.polygons:
            if p_.material_index in si: use[list(p_.vertices)] = True
        zone = use & (c2[:, 2] > RX['z'][0]) & (c2[:, 2] < RX['z'][1]) & (np.abs(c2[:, 0]) < RX['x']) & (c2[:, 1] < RX['y'])
        ecount = {}
        for p_ in me.polygons:
            for k_ in p_.edge_keys: ecount[k_] = ecount.get(k_, 0) + 1
        border = np.zeros(len(c2), bool)
        for (a_, b_), n_ in ecount.items():
            if n_ == 1: border[a_] = border[b_] = True
        nb = [[] for _ in c2]
        for (a_, b_) in ecount:
            if use[a_] and use[b_]: nb[a_].append(b_); nb[b_].append(a_)
        mv = np.nonzero(zone & ~border)[0]
        for it_ in range(RX.get('it', 10) * 2):
            lam = .5 if it_ % 2 == 0 else -.53; d2 = np.zeros_like(c2)
            for i_ in mv:
                if nb[i_]: d2[i_] = c2[nb[i_]].mean(0) - c2[i_]
            c2 = c2 + d2 * lam
        set_co(me, c2); me.update(); log('skin relaxed in the neckline', ob.name, len(mv))
    rows.append({'mesh': ob.name, 'moved_vertices': int((mag > 1e-5).sum()), 'max_mm': round(float(mag.max()) * 1000, 1)})
    log('build', build, k, json.dumps(rows[-1]))
(OUT / N / 'build_report.json').write_text(json.dumps({'schema': 'dink-character-build/1', 'build': build, 'strength': k, 'lods': rows}, indent=1) + '\n')
save_blend()
log('BUILD DONE')
