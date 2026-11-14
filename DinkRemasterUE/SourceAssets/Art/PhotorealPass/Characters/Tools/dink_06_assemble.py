"""Stage 6: assemble the game character: join parts per material slot, skin to the 89-bone rig by transferring the
shipped hero's weights, build LOD1-3, hook up the baked texture sets. Writes SK_<Name>_Photoreal.blend."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *; import matlib
import hairlib; from hair_styles import STYLES
CFG = dict(name='Dink', packed='Dink/Work/dink_packed.blend', head='Dink/Work/dink_head.blend', tex='Dink/Textures', prefix='T_Dink_PR', out='Dink/SK_Dink_Photoreal.blend',
           rigid={'Pack': 'spine_04', 'PackFlap': 'spine_04', 'PackStrap_l': 'spine_04', 'PackStrap_r': 'spine_04', 'PackBuckle_l': 'spine_04', 'PackBuckle_r': 'spine_04',
                  'Buckle': 'pelvis', 'BeltKeeper': 'pelvis'},
           lod_ratios=[1.0, .5, .3, .19])
if args(): CFG.update(json.loads(Path(args()[0]).read_text()))
N = CFG['name']
bpy.ops.wm.open_mainfile(filepath=str(OUT / CFG['packed']))
D = bpy.data.objects; sc = bpy.context.scene
for o in list(D):
    if o.type == 'MESH' and (o.name.endswith('_HI') or o.name in ('BodyVol', 'OldShirtTopo', 'OldTrousersTopo', 'OldHair', 'OldEyes', 'BrowLash', 'Skin') or o.name in CFG.get('junk', ())):
        bpy.data.objects.remove(o, do_unlink=True)
with bpy.data.libraries.load(str(OUT / CFG['head'])) as (src, dst):
    dst.objects = ['Skin', 'Eyes', 'Hair']
skin, eyes, hair = dst.objects
for o in dst.objects: sc.collection.objects.link(o)
arm = D['Armature']; olds = [D[n_] for n_ in CFG.get('wsrc', ['OldWardrobe'])]
# weight source: the shipped hero (wardrobe + skin) in the same rest pose
src = dup(skin, 'WSrc'); wsrc = join([src] + [dup(o_, 'WSrc2') for o_ in olds], 'WeightSource')
bone_names = [b.name for b in arm.data.bones]
def transfer(o):
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    for m in list(o.modifiers): o.modifiers.remove(m)
    dt = o.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = wsrc; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    activate(o); bpy.ops.object.datalayout_transfer(modifier='dt'); bpy.ops.object.modifier_apply(modifier='dt')
def rigid(o, bone):
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    g = o.vertex_groups.new(name=bone); g.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
def one_point(o, p):
    """Whole object follows the weights found at one point (keeps small hard parts rigid on a soft carrier)."""
    t = new_obj('tmpw', [p, (p[0] + .001, p[1], p[2]), (p[0], p[1], p[2] + .001)], [(0, 1, 2)]); transfer(t)
    ws = {g.group: g.weight for g in t.data.vertices[0].groups}; names = {g.index: g.name for g in t.vertex_groups}
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    for gi, w in ws.items():
        if w > 0: o.vertex_groups.new(name=names[gi]).add(list(range(len(o.data.vertices))), w, 'REPLACE')
    bpy.data.objects.remove(t, do_unlink=True)
parts = [o for o in D if o.type == 'MESH' and 'fabric' in o]
for nm_, ratio_ in CFG.get('decimate', {}).items():   # budget: thin over-tessellated smooth parts (belt loops, buckles, flat leather) before skinning; UVs and bakes stay valid
    o_ = D.get(nm_)
    if o_ is None: log('decimate: no part', nm_); continue
    t0_ = tri_count(o_); d_ = o_.modifiers.new('dec', 'DECIMATE'); d_.ratio = ratio_; d_.delimit = {'UV'}; apply_mods(o_); smooth_shade(o_); log('decimated', nm_, t0_, '->', tri_count(o_))
if CFG.get('eye_back_cull'):   # the back of each eyeball sits inside the skull and is never seen (the eyes are rigid on the head bone)
    bm = bmesh.new(); bm.from_mesh(eyes.data); bm.normal_update(); dead = [f for f in bm.faces if f.normal.y > CFG['eye_back_cull']]; nt_ = sum(len(f.verts) - 2 for f in dead)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(eyes.data); bm.free(); log('eye back faces removed, tris', nt_)
for o in parts:
    if o.get('weights') == 'keep': pass
    elif o.get('rigidw'):
        for g in list(o.vertex_groups): o.vertex_groups.remove(g)
        for part in o['rigidw'].split(','): o.vertex_groups.new(name=part.split(':')[0]).add(list(range(len(o.data.vertices))), float(part.split(':')[1]), 'REPLACE')
    elif o.name in CFG['rigid']: rigid(o, CFG['rigid'][o.name])
    elif o['fabric'] in ('brass', 'iron'): one_point(o, tuple(np.mean(co_np(o.data), axis=0)))
    else: transfer(o)
# smooth garment weights a little so layers shear together
def smooth_w(o, it=2):
    activate(o); 
    try:
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=.5, repeat=it); bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as ex:
        bpy.ops.object.mode_set(mode='OBJECT'); log('smooth fail', o.name, ex)
for o in parts:
    if o.name in CFG.get('smooth', ('Shirt', 'Jerkin', 'Trousers')): smooth_w(o, CFG.get('smooth_it', 3))
# A sleeveless garment hangs from the shoulders: what the weight transfer gave its armhole rim of the upper arm (and
# its twist bones) goes to the collar bone of that side instead, so the rim rises with the shoulder and does not
# swing out with the arm. 'arm_to_clavicle': {part: share moved}.
# 'under': {part: [rim, deep]} for a garment worn under a sleeveless one (attribute cover_f, written by tuck_under: the
# cover's cut field, negative where covered). Where it is covered it takes the same share, fading out over `rim` metres
# outside the cover's edge, so the two layers ride together and the hidden shirt cannot swing out through the leather
# when the arm is raised; faces deeper than `deep` under the cover are never seen and go.
for nm_, share_ in CFG.get('arm_to_clavicle', {}).items():
    o_ = D.get(nm_)
    if o_ is None: log('arm_to_clavicle: no part', nm_); continue
    moved_ = 0; fade_ = None
    if nm_ in CFG.get('under', {}):
        ca_ = o_.data.attributes.get('cover_f')
        if ca_ is None: log('arm_to_clavicle: no cover_f on', nm_); continue
        cf_ = np.empty(len(o_.data.vertices), np.float32); ca_.data.foreach_get('value', cf_); rim_, deep_ = CFG['under'][nm_]
        fade_ = sstep(rim_, -.004, cf_)
        bm_ = bmesh.new(); bm_.from_mesh(o_.data); bm_.verts.ensure_lookup_table()
        dead_ = [f_ for f_ in bm_.faces if all(cf_[v_.index] < -deep_ for v_ in f_.verts)]; nd_ = sum(len(f_.verts) - 2 for f_ in dead_)
        # which vertices survive, by their index before the delete (deleting faces takes their unshared vertices along)
        deadset_ = set(dead_); keep_ = np.zeros(len(cf_), bool)
        for f_ in bm_.faces:
            if f_ not in deadset_:
                for v_ in f_.verts: keep_[v_.index] = True
        bmesh.ops.delete(bm_, geom=dead_, context='FACES'); bmesh.ops.delete(bm_, geom=[v_ for v_ in bm_.verts if not v_.link_faces], context='VERTS')
        bm_.to_mesh(o_.data); bm_.free(); o_.data.update(); fade_ = fade_[keep_]
        if len(fade_) != len(o_.data.vertices): raise RuntimeError('under: %s has %d vertices, %d cover values' % (nm_, len(o_.data.vertices), len(fade_)))
        log('under its cover:', nm_, 'tris removed', nd_, 'vertices that share the cover weights', int((fade_ > 0).sum()))
    for sd_ in ('l', 'r'):
        cl_ = o_.vertex_groups.get('clavicle_' + sd_) or o_.vertex_groups.new(name='clavicle_' + sd_)
        for bn_ in ('upperarm_' + sd_, 'upperarm_twist_01_' + sd_, 'upperarm_twist_02_' + sd_, 'lowerarm_' + sd_):
            g_ = o_.vertex_groups.get(bn_)
            if g_ is None: continue
            for v_ in o_.data.vertices:
                for ge_ in v_.groups:
                    if ge_.group == g_.index and ge_.weight > 0:
                        k_ = share_ * (float(fade_[v_.index]) if fade_ is not None else 1.0)
                        if k_ <= 0: break
                        w_ = ge_.weight; g_.add([v_.index], w_ * (1 - k_), 'REPLACE'); cl_.add([v_.index], w_ * k_, 'ADD'); moved_ += 1; break
    log('arm weight moved to the collar bones', nm_, 'share', share_, 'vertex weights', moved_)
# the hair and eyes ride the head bone; skin keeps its shipped weights
rigid(hair, 'head'); rigid(eyes, 'head')
for o in (skin,):
    for m in list(o.modifiers): o.modifiers.remove(m)
TX = OUT / CFG['tex']; P = CFG['prefix']
mats = {
 'Skin': matlib.game_material('MI_%s_PR_Skin' % N, TX / (P + '_Skin_BC.png'), TX / (P + '_Skin_N.png'), TX / (P + '_Skin_ORM.png'), sss=TX / (P + '_Skin_SSS.png'), ao_mix=.5),
 'Eyes': matlib.game_material('MI_%s_PR_Eyes' % N, TX / (P + '_Eyes_BC.png'), TX / (P + '_Eyes_N.png'), TX / (P + '_Eyes_ORM.png'), ao_mix=.8, spec=.8),
 'Hair': hairlib.card_material('MI_%s_PR_Hair' % N, TX / (P + '_Hair_BC.png'), TX / (P + '_Hair_N.png'), TX / (P + '_Hair_ORM.png'), **STYLES[N].get('card_mat', {})),
 'Outfit': matlib.game_material('MI_%s_PR_Outfit' % N, TX / (P + '_Outfit_BC.png'), TX / (P + '_Outfit_N.png'), TX / (P + '_Outfit_ORM.png')),
 'Gear': matlib.game_material('MI_%s_PR_Gear' % N, TX / (P + '_Gear_BC.png'), TX / (P + '_Gear_N.png'), TX / (P + '_Gear_ORM.png')),
}
order = ['Skin', 'Eyes', 'Hair', 'Outfit', 'Gear']
def prep(o, slot):
    o.data.materials.clear(); o.data.materials.append(mats[slot])
    for l in list(o.data.uv_layers):
        if l.name != 'UVMap': o.data.uv_layers.remove(l)
    for a in list(o.data.attributes):
        if a.name in ('chart', 'lat', 'd_stitch', 'd_seam', 'cover_f'): o.data.attributes.remove(a)
    if o.data.color_attributes.get('Col') is None:
        ca = o.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', np.ones(len(o.data.vertices) * 4, np.float32))
    o['slot'] = slot
# skin hidden under the shirt yoke goes (the neck column inside the collar stays)
bm = bmesh.new(); bm.from_mesh(skin.data)
dead = [] if CFG.get('skin_cull', 'dink') != 'dink' else [f for f in bm.faces if all((v.co.z < 1.482 and (v.co.x ** 2 + (v.co.y - .008) ** 2) ** .5 > CFG.get('skin_cull_r', .079)) or v.co.z < 1.44 for v in f.verts) and f.calc_center_median().z > 1.3]
bmesh.ops.delete(bm, geom=dead, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(skin.data); bm.free()
log('hidden skin faces removed', len(dead))
if CFG.get('skin_tuck'):   # pull the neck skin that sits under the collar a few millimetres in so it cannot show through the cloth
    skin.data.update(); c_ = co_np(skin.data); n_ = normals_np(skin.data); w_ = sstep(1.492, 1.470, c_[:, 2]) * (c_[:, 2] > 1.40) * (np.abs(c_[:, 0]) < .14)
    set_co(skin.data, c_ - n_ * (w_ * CFG['skin_tuck'])[:, None])
if CFG.get('scalp_cull'):   # scalp skin that the opaque hair cap always hides goes (inside the hairline by a margin; the cap is opaque there)
    LM_ = json.load(open(str(OUT / CFG['head']) + '.json')); hctr = np.array(LM_['ctr']); HL_ = STYLES[N].get('hairline', (.50, .14, -.52))
    class _H: pass
    h_ = _H(); h_.ctr = hctr; h_.HL = HL_; h_.hairline = lambda d: hairlib.Head.hairline(h_, d)
    skin.data.update(); c_ = co_np(skin.data); e_ = np.full(len(c_), 9.0)
    for i_ in np.nonzero(c_[:, 2] > hctr[2] - .02)[0]: e_[i_] = hairlib.Head.params(h_, c_[i_])[1]
    bm = bmesh.new(); bm.from_mesh(skin.data); bm.verts.ensure_lookup_table()
    dead = [f for f in bm.faces if all(e_[v.index] < CFG['scalp_cull'] for v in f.verts) and np.array(f.normal) @ hairlib.unit(np.array(f.calc_center_median()) - hctr) > .2]
    nt_ = sum(len(f.verts) - 2 for f in dead)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(skin.data); bm.free()
    log('scalp skin under the hair cap removed, tris', nt_)
if CFG.get('skin_tuck_q'):   # open neckline: the skin just outside the dress opening sinks under the cloth so it cannot poke through the hem
    qc, qr, q0, q1, dep = CFG['skin_tuck_q']; skin.data.update(); c_ = co_np(skin.data); n_ = normals_np(skin.data)
    q_ = np.sqrt((((c_ - np.array(qc)) / np.array(qr)) ** 2).sum(1)); w_ = sstep(q0, q1, q_) * (c_[:, 2] > 1.30) * (c_[:, 2] < 1.56) * (np.abs(c_[:, 0]) < .19) * sstep(.070, .082, np.sqrt(c_[:, 0] ** 2 + (c_[:, 1] - .008) ** 2))
    set_co(skin.data, c_ - n_ * (w_ * dep)[:, None]); log('skin tucked under the neckline', int((w_ > 0).sum()))
prep(skin, 'Skin'); prep(eyes, 'Eyes'); prep(hair, 'Hair')
for o in parts: prep(o, 'Outfit' if o['mat'] == 'outfit' else 'Gear')
allp = [skin, eyes, hair] + parts
hair_n = None
# join per slot first (keeps slot order), then all
slot_objs = []
by_slot = {s: [o for o in allp if o['slot'] == s] for s in order}
for s in order:
    objs = by_slot[s]
    slot_objs.append(join(objs, 'slot_' + s) if len(objs) > 1 else objs[0])
lod0 = join(slot_objs, 'SK_%s_Photoreal_LOD0' % N)
bpy.data.objects.remove(wsrc, do_unlink=True)
for o_ in olds: bpy.data.objects.remove(o_, do_unlink=True)
# fixed slot order regardless of join order
me0 = lod0.data; names = [m.name for m in me0.materials]; want = [mats[s].name for s in order]
mi = np.empty(len(me0.polygons), np.int32); me0.polygons.foreach_get('material_index', mi)
remap = np.array([want.index(n) for n in names], np.int32)
me0.materials.clear()
for s in order: me0.materials.append(mats[s])
me0.polygons.foreach_set('material_index', remap[mi]); me0.update()
bpy.context.view_layer.update()
log('slots', [m.name for m in lod0.data.materials])
if CFG.get('hidden_cull'):
    # faces that another layer covers tightly (skin under plates and cuffs, strap and plate backs, cloth under belts): every ray of a
    # 13-ray fan about the face normal is blocked within `reach`. Hair, eyes and the head are never touched; loose cloth is not tight, so it stays.
    reach = float(CFG['hidden_cull']); me_ = lod0.data; bm = bmesh.new(); bm.from_mesh(me_); bm.faces.ensure_lookup_table(); bm.normal_update()
    hs_, es_, ss_ = order.index('Hair'), order.index('Eyes'), order.index('Skin')
    isl = {}; ni = 0        # connected pieces: a face only counts as covered when a DIFFERENT piece blocks it (pleats and folds cover themselves)
    for f0 in bm.faces:
        if f0.index in isl: continue
        st = [f0]; isl[f0.index] = ni
        while st:
            g_ = st.pop()
            for e_ in g_.edges:
                for h2 in e_.link_faces:
                    if h2.index not in isl: isl[h2.index] = ni; st.append(h2)
        ni += 1
    occl = [f for f in bm.faces if f.material_index != hs_]; tree = BVHTree.FromPolygons([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in occl])
    fan = [(0.0, 0.0)] + [(math.radians(28), 2 * math.pi * k / 4 + .4) for k in range(4)] + [(math.radians(58), 2 * math.pi * k / 8) for k in range(8)]
    dead = []; per = {}
    for f in bm.faces:
        if f.material_index == hs_: continue
        c = f.calc_center_median()
        if f.material_index == ss_ and c.z > 1.46: continue
        n = f.normal
        if n.length < .5: continue
        t1 = n.orthogonal().normalized(); t2 = n.cross(t1); vis = False
        vs_ = [v.co for v in f.verts]; nv_ = len(vs_)
        # the whole face must be covered, not just its middle: centre, corners (pulled in a little) and edge midpoints
        pts_ = [c] + [v_ + (c - v_) * .12 for v_ in vs_] + [(vs_[k_] + vs_[(k_ + 1) % nv_]) * .5 + (c - (vs_[k_] + vs_[(k_ + 1) % nv_]) * .5) * .06 for k_ in range(nv_)]
        for p_ in pts_:
            for el, az in fan:
                d = n * math.cos(el) + (t1 * math.cos(az) + t2 * math.sin(az)) * math.sin(el)
                hit = tree.ray_cast(p_ + n * .0012, d, reach)
                if hit[0] is None or isl[occl[hit[2]].index] == isl[f.index]: vis = True; break
            if vis: break
        if not vis: dead.append(f); per[order[f.material_index]] = per.get(order[f.material_index], 0) + len(f.verts) - 2
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(me_); bm.free(); me_.update()
    log('tightly covered faces removed, tris per slot', per)
def clean_weights(o):
    valid = set(bone_names)
    for g in list(o.vertex_groups):
        if g.name not in valid: o.vertex_groups.remove(g)
    for b in bone_names:
        if b not in o.vertex_groups: o.vertex_groups.new(name=b)
    activate(o)
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    nw = sum(1 for v in o.data.vertices if not v.groups); mx = max(len(v.groups) for v in o.data.vertices)
    if nw:
        hg = o.vertex_groups['spine_03']
        for v in o.data.vertices:
            if not v.groups: hg.add([v.index], 1.0, 'REPLACE')
    return nw, mx
nw, mx = clean_weights(lod0); log('LOD0 unweighted (fixed)', nw, 'max influences', mx)
def add_arm(o):
    for m in list(o.modifiers): o.modifiers.remove(m)
    m = o.modifiers.new('Armature', 'ARMATURE'); m.object = arm; o.parent = None
add_arm(lod0)
bm = bmesh.new(); bm.from_mesh(lod0.data); bmesh.ops.triangulate(bm, faces=bm.faces)
if CFG.get('clean_degenerate'):
    bmesh.ops.dissolve_degenerate(bm, dist=2e-5, edges=bm.edges); bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-8], context='FACES')
bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(lod0.data); bm.free()
smooth_shade(lod0)
hair_slot = order.index('Hair')
def make_lod(i, ratio):
    o = dup(lod0, 'SK_%s_Photoreal_LOD%d' % (N, i))
    me = o.data
    # hair: thin the card layers instead of collapsing them
    hl = np.zeros(len(me.vertices), np.float32)
    if me.attributes.get('hl') is not None: me.attributes['hl'].data.foreach_get('value', hl)
    keep_layers = {1: (1, 2, 3, 4, 5), 2: (1, 2, 3, 4), 3: (1, 3, 4)}[i]
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    dead = [v for v in bm.verts if hl[v.index] > .5 and int(round(hl[v.index])) not in keep_layers]
    bmesh.ops.delete(bm, geom=dead, context='VERTS'); bm.to_mesh(me); bm.free()
    vg = o.vertex_groups.new(name='_dec')
    hl2 = np.zeros(len(me.vertices), np.float32)
    if me.attributes.get('hl') is not None: me.attributes['hl'].data.foreach_get('value', hl2)
    vg.add([int(j) for j in np.nonzero(hl2 < .5)[0]], 1.0, 'REPLACE')
    d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = ratio; d.vertex_group = '_dec'; d.use_collapse_triangulate = True
    activate(o); bpy.ops.object.modifier_move_to_index(modifier='dec', index=0); bpy.ops.object.modifier_apply(modifier='dec')
    o.vertex_groups.remove(o.vertex_groups['_dec'])
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(o.data); bm.free()
    clean_weights(o); return o
lods = [lod0] + [make_lod(i, CFG['lod_ratios'][i]) for i in (1, 2, 3)]
for o in lods:
    hairlib.apply_hn(o)          # hair cards shade with their scalp-blended normals (custom split normals, exported in the FBX)
    log(o.name, 'tris', tri_count(o), 'verts', len(o.data.vertices), 'dims', [round(x, 3) for x in o.dimensions])
    o.hide_render = o is not lod0
arm.data.pose_position = 'REST'
bpy.ops.file.make_paths_relative() if False else None
save_blend(filepath=str(OUT / CFG['out']))
