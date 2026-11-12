"""Build every asset at LOD0-2, validate, export one FBX per LOD and save the source .blend per group.
blender -b -t 4 --python export_all.py -- [group ...]   (groups: pine broadleaf ground deadwood under meadow)"""
import bpy, sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas, bl_tree as T
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
GROUPS = {}
def reg():
    import veg_pine, veg_broadleaf, veg_ground, veg_deadwood, veg_under, veg_meadow
    GROUPS['meadow'] = (veg_meadow, list(veg_meadow.MEADOW))
    GROUPS['pine'] = (veg_pine, list(veg_pine.PINES) + list(getattr(veg_pine, 'EDGES', {})))
    GROUPS['broadleaf'] = (veg_broadleaf, list(veg_broadleaf.TREES))
    GROUPS['ground'] = (veg_ground, list(veg_ground.GROUND))
    GROUPS['deadwood'] = (veg_deadwood, list(veg_deadwood.DEAD))
    GROUPS['under'] = (veg_under, list(veg_under.UNDER))
EXP = os.path.join(HERE, '..', 'Export'); BL = os.path.join(HERE, '..', 'Blend')
for g in (argv or ['pine', 'broadleaf', 'ground', 'deadwood', 'under', 'meadow']):
    bl_atlas.reset(); reg(); mod, names = GROUPS[g]; stats = {}
    for name in names:
        st = dict(lods=[])
        for lod in range(3):
            ob = mod.build(name, lod); me = ob.data
            lo, hi = T.bounds(ob); tris = T.tri_count(ob)
            uv = np.array([d.uv[:] for d in me.uv_layers[0].data])
            issues = []
            if (lo[2] > 0.01 and 'HangingVines' not in name) or lo[2] < -(T.BELOW_GROUND + 0.02): issues.append(f'minz {lo[2]:.3f}')
            ext = hi - lo
            if abs(lo[0] + hi[0]) / 2 > 0.1 * max(ext[0], 0.01) + 0.01 or abs(lo[1] + hi[1]) / 2 > 0.1 * max(ext[1], 0.01) + 0.01: issues.append('pivot xy')
            if uv.min() < -1e-4 or uv.max() > 1 + 1e-4: issues.append(f'uv range {uv.min():.3f}..{uv.max():.3f}')
            if not np.isfinite(np.array([v.co[:] for v in me.vertices])).all(): issues.append('nan')
            path = os.path.join(EXP, f'{name}_LOD{lod}.fbx'); T.export_fbx(ob, path)
            st['lods'].append(dict(lod=lod, triangles=tris, vertices=len(me.vertices), fbx=f'Export/{name}_LOD{lod}.fbx', issues=issues))
            if lod == 0: st['dimensions_m'] = [round(float(x), 3) for x in ext]; st['materials'] = [m.name for m in me.materials]
            ob.location = (len(stats) * 12.0, lod * 12.0, 0)
            print('EXPORT', name, lod, tris, [round(float(x), 2) for x in ext], issues, flush=True)
        stats[name] = st
    bpy.ops.file.pack_all() if False else None
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BL, f'VEG_{g}.blend'), relative_remap=True)
    json.dump(stats, open(os.path.join(HERE, '..', 'work', f'stats_{g}.json'), 'w'), indent=1)
