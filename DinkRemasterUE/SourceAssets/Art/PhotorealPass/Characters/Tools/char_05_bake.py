"""Stage 5 (generic copy of dink_05_bake; usage: -- <Name> [pack|Outfit|Gear]): pack atlases, build bake-source shaders, bake BC / N / roughness / AO from the detailed meshes to the game
meshes (Cycles, selected-to-active). Writes raw bakes to Dink/Work/bake and a uv dump for the post step."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *; import matlib
A_ = args(); N = A_[0]; n_ = N.lower(); only = A_[1] if len(A_) > 1 else 'all'
bpy.ops.wm.open_mainfile(filepath=str(OUT / N / ('Work/%s_garments_b.blend' % n_)))
D = bpy.data.objects; sc = bpy.context.scene
BK = OUT / N / 'Work/bake'; BK.mkdir(parents=True, exist_ok=True)
lows = [o for o in D if o.type == 'MESH' and 'fabric' in o and not o.name.endswith('_HI')]
def hi_of(o): return D.get(o.name + '_HI')
BIG = 1.0
def put(o, name, arr):
    a = o.data.attributes.get(name) or o.data.attributes.new(name, 'FLOAT', 'POINT'); a.data.foreach_set('value', np.asarray(arr, np.float32))
def seams(o):
    """Seam / stitch distance fields are authored by the build stage; only defaults and belt-style 'lat' fields here."""
    n = len(o.data.vertices); nm = o.name.replace('_HI', '')
    if o.data.attributes.get('lat') is not None and nm in D and 'lat_c' in D[nm]:
        lat = np.empty(n, np.float32); o.data.attributes['lat'].data.foreach_get('value', lat); put(o, 'd_stitch', np.abs(lat) - D[nm]['lat_c'])
    for k in ('d_seam', 'd_stitch'):
        if o.data.attributes.get(k) is None: put(o, k, np.full(n, BIG))

groups = {'Outfit': (4096, [o for o in lows if o['mat'] == 'outfit']), 'Gear': (2048, [o for o in lows if o['mat'] == 'gear'])}
dump = {}
for gname, (size, objs) in groups.items():
    ppm = pack_charts(objs, size, margin_px=10)
    log(gname, 'px per m', round(ppm), [o.name for o in objs])
    for o in objs:
        me = o.data; me.calc_loop_triangles()
        uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
        tl = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get('loops', tl)
        dump[o.name] = dict(group=gname, fabric=o['fabric'], ppm=float(o['px_per_m']), tris=uv[tl].reshape(-1, 6).astype(np.float32))
np.savez_compressed(BK / 'uvdump.npz', **{k: v['tris'] for k, v in dump.items()})
json.dump({k: {a: b for a, b in v.items() if a != 'tris'} for k, v in dump.items()}, open(BK / 'uvdump.json', 'w'))
save_blend(filepath=str(OUT / N / ('Work/%s_packed.blend' % n_)))
if only == 'pack': sys.exit(0)

sc.render.engine = 'CYCLES'; use_hip_gpu(sc); sc.cycles.samples = 2; sc.cycles.use_denoising = False
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.render.bake.margin = 12; sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = .006; sc.render.bake.max_ray_distance = .014
try: sc.render.bake.margin_type = 'EXTEND'
except Exception: pass
for i, o in enumerate(lows):
    h = hi_of(o)
    if h is None:
        h = dup(o, o.name + '_HI'); subdivide(h, 1)
    seams(h)
    h.data.materials.clear(); h.data.materials.append(matlib.fabric_source('SRC_' + o.name, o['fabric'], seed=i * 1.37))
    smooth_shade(h)
for o in D:
    if o.type == 'MESH': o.hide_render = not (o.name.endswith('_HI') or o.name == 'Skin')
for gname, (size, objs) in groups.items():
    if only not in ('all', gname): continue
    imgs = {}
    for k in ('BC', 'N', 'R', 'AO'):
        s_ = size if k != 'AO' else size // 2
        im = bpy.data.images.new('bake_%s_%s' % (gname, k), s_, s_, alpha=False, float_buffer=(k == 'N'))
        if k != 'BC': im.colorspace_settings.name = 'Non-Color'
        im.generated_color = (.5, .5, 1, 1) if k == 'N' else ((1, 1, 1, 1) if k == 'AO' else (.5, .5, .5, 1)); imgs[k] = im
    tm = bpy.data.materials.new('BAKE_' + gname); tm.use_nodes = True; tn = tm.node_tree.nodes.new('ShaderNodeTexImage'); tm.node_tree.nodes.active = tn
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(tm)
        o.data.uv_layers.active = o.data.uv_layers['UVMap']
    for k, typ in (('BC', 'DIFFUSE'), ('N', 'NORMAL'), ('R', 'ROUGHNESS'), ('AO', 'AO')):
        tn.image = imgs[k]
        sc.cycles.samples = 48 if k == 'AO' else 2
        for o in objs:
            h = hi_of(o)
            if h is None: continue
            deselect(); o.hide_render = False; h.select_set(True); o.select_set(True); bpy.context.view_layer.objects.active = o
            kw = dict(type=typ, use_selected_to_active=True, cage_extrusion=.006, max_ray_distance=.014, margin=12, use_clear=False)
            if typ == 'DIFFUSE': kw['pass_filter'] = {'COLOR'}
            if typ == 'NORMAL': kw['normal_space'] = 'TANGENT'
            bpy.ops.object.bake(**kw)
            o.hide_render = True
        im = imgs[k]; im.filepath_raw = str(BK / ('%s_%s.png' % (gname, k))); im.file_format = 'PNG'; im.save()
        log('baked', gname, k)
