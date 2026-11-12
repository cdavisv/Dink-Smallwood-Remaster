"""Re-import every exported FBX and check it: triangle count vs the export stats, real size, pivot, non-manifold edges (more than two faces),
zero-area faces, loose vertices, missing UV / colour / material data. blender -b -t 4 --python validate_fbx.py
Open borders are expected on cards, cut faces and open tube ends and are reported separately, not as errors."""
import bpy, bmesh, sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.join(HERE, '..', 'Export')
stats = {}
for g in ('pine', 'broadleaf', 'ground', 'deadwood', 'under', 'meadow'):
    p = os.path.join(HERE, '..', 'work', f'stats_{g}.json')
    if os.path.exists(p):
        for n, s in json.load(open(p)).items():
            for l in s['lods']: stats[os.path.basename(l['fbx'])] = (l['triangles'], s['dimensions_m'] if l['lod'] == 0 else None)
out = {}; bad = 0
for f in sorted(glob.glob(os.path.join(EXP, '*.fbx'))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']; name = os.path.basename(f); r = dict(objects=len(obs)); err = []
    if len(obs) != 1: err.append('expected one mesh')
    else:
        o = obs[0]; me = o.data; bm = bmesh.new(); bm.from_mesh(me); bm.transform(o.matrix_world)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        r['triangles'] = len(bm.faces); r['nonmanifold_edges'] = sum(1 for e in bm.edges if len(e.link_faces) > 2); r['border_edges'] = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        r['zero_area_faces'] = sum(1 for fc in bm.faces if fc.calc_area() < 1e-10); r['loose_verts'] = sum(1 for v in bm.verts if not v.link_faces)
        xs = [v.co for v in bm.verts]; lo = [min(c[k] for c in xs) for k in range(3)]; hi = [max(c[k] for c in xs) for k in range(3)]
        r['size_m'] = [round(hi[k] - lo[k], 3) for k in range(3)]; r['min_z'] = round(lo[2], 3); r['scale'] = [round(x, 4) for x in o.scale]
        r['uv_layers'] = len(me.uv_layers); r['colour_layers'] = len(me.color_attributes); r['materials'] = [m.name for m in me.materials if m]
        if name in stats:
            if stats[name][0] != r['triangles']: err.append(f"triangles {r['triangles']} != exported {stats[name][0]}")
            if stats[name][1] and any(abs(a - b) > 0.02 for a, b in zip(stats[name][1], r['size_m'])): err.append(f"size {r['size_m']} != {stats[name][1]}")
        else: err.append('not in export stats (stale file?)')
        if r['nonmanifold_edges']: err.append(f"{r['nonmanifold_edges']} non-manifold edges")
        if r['zero_area_faces'] > 0: err.append(f"{r['zero_area_faces']} zero-area faces")
        if r['loose_verts']: err.append(f"{r['loose_verts']} loose verts")
        if r['uv_layers'] < 1 or r['colour_layers'] < 1 or not r['materials']: err.append('missing uv/colour/material')
        if any(abs(s - 1) > 1e-3 for s in o.scale): err.append('node scale not 1')
        bm.free()
    r['errors'] = err; out[name] = r; bad += bool(err)
    print('VALID', name, r.get('triangles'), 'ERR' if err else 'ok', err, flush=True)
json.dump(out, open(os.path.join(HERE, '..', 'work', 'fbx_validation.json'), 'w'), indent=1)
print('VALIDATED', len(out), 'files,', bad, 'with errors')
