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
rows = []
for ob in sorted((o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name), key=lambda o: o.name):
    me = ob.data
    if me.shape_keys: raise SystemExit('char_07_build: %s has shape keys; a baked build would not follow them' % ob.name)
    co = co_np(me); d = PH.field(co, PH.weights_of(ob), heads, build) * k
    set_co(me, co + d); me.update(); mag = np.linalg.norm(d, axis=1)
    rows.append({'mesh': ob.name, 'moved_vertices': int((mag > 1e-5).sum()), 'max_mm': round(float(mag.max()) * 1000, 1)})
    log('build', build, k, json.dumps(rows[-1]))
(OUT / N / 'build_report.json').write_text(json.dumps({'schema': 'dink-character-build/1', 'build': build, 'strength': k, 'lods': rows}, indent=1) + '\n')
save_blend()
log('BUILD DONE')
