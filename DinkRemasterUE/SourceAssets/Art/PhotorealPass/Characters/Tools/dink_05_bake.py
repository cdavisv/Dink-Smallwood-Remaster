"""Stage 5: pack atlases, build bake-source shaders, bake BC / N / roughness / AO from the detailed meshes to the game
meshes (Cycles, selected-to-active). Writes raw bakes to Dink/Work/bake and a uv dump for the post step."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *; import matlib, folds
A_ = args(); only = A_[0] if A_ else 'all'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/dink_garments_b.blend'))
D = bpy.data.objects; sc = bpy.context.scene
arm = D['Armature']; B = arm.data.bones
folds.setup({n: list(B[n].head_local) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})
S, E_, Wr, T, K, A = folds.S, folds.E_, folds.Wr, folds.T, folds.K, folds.A
BK = OUT / 'Dink/Work/bake'; BK.mkdir(parents=True, exist_ok=True)
lows = [o for o in D if o.type == 'MESH' and 'fabric' in o and not o.name.endswith('_HI')]
def hi_of(o): return D.get(o.name + '_HI')
BIG = 1.0
def put(o, name, arr):
    a = o.data.attributes.get(name) or o.data.attributes.new(name, 'FLOAT', 'POINT'); a.data.foreach_set('value', np.asarray(arr, np.float32))
def mir(p):
    m = p.copy(); m[:, 0] = np.abs(m[:, 0]); return m
def seams(o):
    p = co_np(o.data); n = len(p); nm = o.name.replace('_HI', ''); seam = np.full(n, BIG); st = np.full(n, BIG)
    if nm == 'Shirt':
        h = folds.arm_h(p); s, th, _ = poly_params(mir(p), [S, E_, Wr], (0, 0, -1))
        under = np.where(h > .02, np.abs(th) * .05, BIG)
        seam = np.minimum(np.abs(h), under); st = np.minimum(np.abs(h - .005), np.abs(under - .004))
    elif nm == 'Jerkin':
        z = p[:, 2]; x = np.abs(p[:, 0]); y = p[:, 1]
        side = np.where((z < 1.36) & (x > .08), np.abs(y + .012), BIG)
        front = np.where((y < -.05) & (z < 1.33), x, BIG)
        shoulder = np.where((z > 1.44) & (x > .07), np.abs(y - .012), BIG)
        seam = np.minimum(np.minimum(side, front), shoulder)
        ah = folds.arm_h(p)
        fv = np.minimum((z - 1.335) * .40 - x, .02 - y); fn = np.minimum(.108 - np.sqrt(p[:, 0] ** 2 + (y - .004) ** 2), z - 1.40); nf = np.maximum(fv, fn)
        az = np.arctan2(p[:, 0], -y); hem = .872 + .008 * np.sin(3 * az + 1.0) + .006 * np.sin(7 * az)
        st = np.minimum.reduce([np.abs(seam - .0045), np.abs(ah + .003), np.abs(nf + .006), np.abs(z - hem - .008)])
    elif nm == 'Trousers':
        s, th, _ = poly_params(mir(p), [T, K, A], (1, 0, 0)); z = p[:, 2]
        d = np.minimum(np.abs(th), np.pi - np.abs(th)) * .07
        seam = np.where(z < .9, d, BIG); st = np.abs(seam - .0045)
    elif nm.startswith('Bracer_'):
        dF = (Wr - E_) / np.linalg.norm(Wr - E_); f = (mir(p) - E_) @ dF
        st = np.minimum(np.abs(f - .118), np.abs(f - .251))
    elif nm.startswith('Boot_'):
        z = p[:, 2]; s, th, _ = poly_params(mir(p), [K, A], (0, 1, 0))
        seam = np.where(z > .13, np.abs(th) * .05, BIG)
        st = np.minimum.reduce([np.abs(seam - .004), np.abs(z - .343), np.abs(z - .309)])
    elif nm == 'PackFlap':
        me = o.data; uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMetric'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv); vu = np.zeros((n, 2)); vu[lv] = uv
        st = np.minimum.reduce([vu[:, 0] - vu[:, 0].min(), vu[:, 0].max() - vu[:, 0], vu[:, 1].max() - vu[:, 1]]) - .007
    if o.data.attributes.get('lat') is not None and 'lat_c' in D[nm]:
        lat = np.empty(n, np.float32); o.data.attributes['lat'].data.foreach_get('value', lat); st = np.abs(lat) - D[nm]['lat_c']
    put(o, 'd_seam', seam); put(o, 'd_stitch', st)

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
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Dink/Work/dink_packed.blend'))
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
