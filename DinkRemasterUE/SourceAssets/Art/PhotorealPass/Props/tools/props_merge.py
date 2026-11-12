"""Swap the round-2 baked game meshes (Props/_build/bake/<Asset>.blend, made by props_bake.py) into Props/_build/Props.blend,
re-export their FBX (LOD0-2 + UCX hulls) and update Props/_build/modules.json. Run after props_build.py.
A bake may carry variants (extra assets on the same texture set, e.g. the opened chest) and assets that are new to Props.blend:
both get a collection, a box hull and a modules.json record from the 'meta' block of the bake record.

    blender -b -t 4 Props/_build/Props.blend --python Props/tools/props_merge.py [-- asset ...]"""
import bpy, os, sys, json, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PROPS = os.path.dirname(HERE); OUT = os.path.join(PROPS, '_build'); BK = os.path.join(OUT, 'bake')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ALIAS = {'SM_Prop_Candle_Holder_01': ['SM_Candle_Iron_PR']}        # same mesh and texture set under a second asset name
mods = json.load(open(os.path.join(OUT, 'modules.json'))); byname = {r['name']: r for r in mods}
sc = bpy.context.scene
SRC = 'authored in Blender (photoreal pass round 2, Props/tools/props_bake.py); unique bake from a high-detail source'


def ensure(tgt, cls, bmin, bmax, meta, hull=True):
    """collection + box hull + modules record for an asset that Props.blend does not have yet"""
    if tgt in bpy.data.collections:
        coll = bpy.data.collections[tgt]
    else:
        coll = bpy.data.collections.new(tgt); sc.collection.children.link(coll)
        coll['dink_class'] = cls; coll['dink_path'] = 'Props'; coll['dink_tex_px'] = 2048
    coll['dink_source'] = SRC
    if tgt not in byname:
        r = {'name': tgt, 'class': cls, 'fbx': tgt + '.fbx', 'materials': [], 'source_blend': 'Props.blend', 'open_edges': 0, 'collision_hulls': 1,
             'families': [], 'supersedes': 'none (new)', 'dresses': '', 'fit': {}}
        mods.append(r); byname[tgt] = r
    for k, v in (meta or {}).items():
        byname[tgt][k] = v
    if meta and 'class' in meta:
        coll['dink_class'] = meta['class']
    ucx = [o for o in coll.objects if o.name.startswith('UCX')]
    if hull and (not ucx or (meta or {}).get('rehull')):
        for o in ucx:
            me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
        for o in [o for o in bpy.data.objects if o.name.startswith('UCX_%s_LOD0_' % tgt) and not o.users_collection]:
            bpy.data.objects.remove(o)
        (x0, y0, z0), (x1, y1, z1) = bmin, bmax
        V = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        me = bpy.data.meshes.new('UCX_%s_LOD0_01' % tgt); me.from_pydata(V, [], F); o = bpy.data.objects.new(me.name, me); coll.objects.link(o); o.hide_render = True
    return coll


for jp in sorted(glob.glob(os.path.join(BK, '*.json'))):
    rec = json.load(open(jp)); src = rec['name']
    if ARGS and src not in ARGS:
        continue
    short = src[3:-3] if src.endswith('_PR') else src[3:]
    # every asset this bake feeds: (target name, object prefix in the bake .blend, bounds, meta)
    outs = [(src, src, rec, rec.get('meta'))] + [(a, src, rec, None) for a in ALIAS.get(src, [])] + [(vn, vn, v, v.get('meta')) for vn, v in (rec.get('variants') or {}).items()]
    for tgt, pre, b, meta in outs:                        # clear the old meshes, materials and images first so nothing comes in as .001
        if tgt in bpy.data.collections:
            for o in [o for o in bpy.data.collections[tgt].objects if not o.name.startswith('UCX')]:
                me = o.data; bpy.data.objects.remove(o)
                if me.users == 0:
                    bpy.data.meshes.remove(me)
    for m_ in list(bpy.data.materials):
        if m_.name.split('.')[0] in [s_['material'] for s_ in rec['slots']] and m_.users == 0:
            bpy.data.materials.remove(m_)
    for im in list(bpy.data.images):
        if im.name.startswith('T_' + src[3:] + '_') and im.users == 0:
            bpy.data.images.remove(im)
    pres = sorted({pre for (_, pre, _, _) in outs})
    with bpy.data.libraries.load(os.path.join(BK, src + '.blend'), link=False) as (df, dt):
        want = [n for n in df.objects if n in [p_ + '_LOD%d' % i for p_ in pres for i in range(3)]]; dt.objects = list(want)
    new = dict(zip(want, dt.objects))                     # appended objects are renamed .001 when the name is taken
    for o in new.values():
        o.location = (0, 0, 0)
    for tgt, pre, b, meta in outs:
        coll = ensure(tgt, (meta or {}).get('class', rec['class']), b['bounds_min_m'], b['bounds_max_m'], meta)
        lods = []
        for i in range(3):
            s_ = new[pre + '_LOD%d' % i]
            o = s_ if tgt == pre else s_.copy()
            if tgt != pre:
                o.data = s_.data.copy()
            o.name = tgt + '_LOD%d' % i; o.data.name = o.name
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o); o.hide_render = i > 0; o.hide_viewport = False; lods.append(o)
        coll['dink_tex_px'] = rec['px']
        if any(s['kind'] == 'translucent' for s in rec['slots']):
            coll['dink_translucent'] = 1
        ucx = [o for o in coll.objects if o.name.startswith('UCX')]
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in lods + ucx:
            hr = o.hide_render; o.hide_render = False; o.select_set(True); o['_hr'] = hr
        bpy.context.view_layer.objects.active = lods[0]
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, tgt + '.fbx'), use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='EDGE',
                                 use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'}, colors_type='NONE')
        for o in lods + ucx:
            o.hide_render = bool(o['_hr']); del o['_hr']
        r = byname[tgt]
        r['materials'] = [s['material'] for s in rec['slots']]
        tr = []
        for o in lods:
            o.data.calc_loop_triangles(); tr.append(len(o.data.loop_triangles))
        r['lod0_triangles'], r['lod1_triangles'], r['lod2_triangles'] = tr
        r['bounds_min_m'] = b['bounds_min_m']; r['bounds_max_m'] = b['bounds_max_m']; r['dimensions_m'] = b['dimensions_m']
        r['baked'] = {'texture_folder': short, 'textures': rec['textures'], 'px': rec['px'], 'slots': rec['slots'], 'emissive_nits': rec.get('emissive_nits'), 'params': rec.get('params'),
                      'stats': rec.get('stats'), 'hi_triangles': rec.get('hi_triangles'), 'third_party': rec.get('third_party', []), 'source_blend': '_build/bake/%s.blend' % src,
                      'extra': rec.get('extra'), 'shares_textures_of': src if tgt != src else None}
        print('MERGED', tgt, tr)
json.dump(mods, open(os.path.join(OUT, 'modules.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Props.blend'), compress=True)
print('MERGE DONE')
