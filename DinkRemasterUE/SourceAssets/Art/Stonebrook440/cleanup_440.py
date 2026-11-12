"""Post-build cleanup (run by build_440.py, or alone): removes loose vertices and zero-area faces left by
joins/decimation in every render LOD, so no exported FBX carries a zero-length normal.  Re-saves the kit."""
import bpy, bmesh, json
from pathlib import Path
ART = Path(__file__).resolve().parent
if not bpy.data.filepath:
    bpy.ops.wm.open_mainfile(filepath=str(ART / 'KIT_Stonebrook440.blend'))
log = {}
for coll in [c for c in bpy.data.collections if c.get('dink_class')]:
    for ob in coll.objects:
        if ob.type != 'MESH' or ob.name.startswith('UCX_'):
            continue
        bm = bmesh.new(); bm.from_mesh(ob.data); v0, f0 = len(bm.verts), len(bm.faces)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
        bad = [f for f in bm.faces if f.calc_area() < 1e-12]
        if bad:
            bmesh.ops.delete(bm, geom=bad, context='FACES')
        # decimation can fold thin parts (liggers, straw stalks) into back-to-back face pairs whose smooth
        # corner normals cancel; drop one face of each reversed duplicate (bounds unchanged)
        seen = {}; dup = []
        for f in bm.faces:
            key = tuple(sorted(v.index for v in f.verts))
            if key in seen and f.normal.dot(seen[key].normal) < -.99:
                dup.extend([f, seen[key]])     # a fully folded pair encloses no volume: remove both
            else:
                seen[key] = f
        if dup:
            bmesh.ops.delete(bm, geom=list(set(dup)), context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(ob.data); ob.data.update()
        zc = sum(1 for n in ob.data.corner_normals if n.vector.length < 1e-4)
        log[ob.name] = {'removed_verts': v0 - len(bm.verts), 'removed_faces': f0 - len(bm.faces), 'zero_corner_normals_after': zc}
        bm.free()
bpy.ops.wm.save_mainfile(compress=True)
(ART / 'cleanup_report.json').write_text(json.dumps(log, indent=2) + '\n')
print('CLEANUP OK', sum(v['removed_verts'] for v in log.values()), 'loose/degenerate verts removed')
