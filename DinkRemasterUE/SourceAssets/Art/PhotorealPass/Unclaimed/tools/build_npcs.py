"""NPC families derived from the photoreal pass characters: maidens (blue, brown, red) from the Mother, the soldier
from Milder, and the corpses (mother, maiden, soldier, Dink, knight) as posed static meshes soaked in blood.

Rigged variants keep the 89-bone mannequin skeleton, skin weights and LOD chain of their base untouched; only the
outfit and hair base-colour maps are new. Corpses are the base's LOD2 with the pose applied.

    tools/bl.sh build_npcs.py <name,name|all>
"""
import bpy, math, os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import npclib as N
from mathutils import Matrix, Vector
from PIL import Image

SCRIPT = 'build_npcs.py'
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def recolour(src, dst, target, pick, keep=0.12, gain=2.4, size=None):
    """tint the pixels chosen by pick(rgb) -> 0..1 towards `target`, keeping their light and dark; writes dst"""
    im = Image.open(src).convert('RGB')
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0; m = np.clip(pick(a), 0, 1)[..., None]; lum = (a @ LUMA)[..., None]
    out = a * (1 - m) + m * (a * keep + (1 - keep) * np.clip(lum * gain, 0, 1.2) * np.array(target, np.float32))
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, optimize=True); return dst


def is_red(a):
    return (a[..., 0] - np.maximum(a[..., 1], a[..., 2]) - 0.06) * 8.0


def is_any(a):
    return np.ones(a.shape[:2], np.float32)


def is_blue(a):
    return (a[..., 2] - np.maximum(a[..., 0], a[..., 1]) - 0.03) * 8.0


def world_rot(arm, bone, axis, deg):
    """turn a pose bone (and its children) about a world axis through the bone's head"""
    bpy.context.view_layer.update(); pb = arm.pose.bones[bone]; h = arm.matrix_world @ pb.head; R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix; bpy.context.view_layer.update()


def write_manifest(outdir, man):
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', outdir)


# ---------------------------------------------------------------------------------------------- rigged variants
VARIANTS = {
    'Maiden_Blue': dict(base='Mother', fam='npc_maiden_blue', seq='251 people/maiden/blue/c7-w1-', outfit=((0.13, 0.20, 0.62), is_red, 4.2), hair=(0.80, 0.62, 0.30), dresses='woman in a long blue dress with fair hair'),
    'Maiden_Brown': dict(base='Mother', fam='npc_maiden_brown', seq='241 people/maiden/brown/c6-w1-', outfit=((0.34, 0.23, 0.13), is_red, 3.6), hair=(0.55, 0.26, 0.10), dresses='woman in a long brown dress with auburn hair'),
    'Maiden_Red': dict(base='Mother', fam='npc_maiden_red', seq='221 people/maiden/red/c4-w1-', outfit=((0.62, 0.04, 0.07), is_red, 3.4), hair=(0.80, 0.62, 0.30), dresses='woman in a long crimson dress with fair hair'),
    'Soldier': dict(base='Milder', fam='npc_soldier', seq='403 people/soldier/c10w3-', outfit=((0.22, 0.13, 0.07), is_blue), dresses='soldier in a leather jerkin over a brown gambeson, steel pauldrons, vambraces and greaves, mail skirt (the base\'s red hair is kept: recolouring its hair atlas also tints the hairline band)'),
}
W_VAR = ('PARTIAL by construction. A colour variant, not a new character: body, face, hair shape, garments, skeleton and skin weights are those of %s from the photoreal pass, so this NPC is her or his twin with a recoloured outfit and hair. '
         'Whatever that base still has wrong is inherited (see its manifest), including the Mother\'s dark patches at the neck and right forearm. No animation clips are delivered here; it plays whatever the base plays, on the same skeleton.')


def variant(name):
    v = VARIANTS[name]; base = v['base']; outdir = os.path.join(L.UNC, v['fam'], name); os.makedirs(outdir, exist_ok=True); arm, lods = N.open_char(base); tex = os.path.join(N.CHARS, base, 'Textures'); asset = 'SK_%s_PR' % name
    obc = recolour(os.path.join(tex, 'T_%s_PR_Outfit_BC.png' % base), os.path.join(outdir, 'T_%s_PR_Outfit_BC.png' % name), v['outfit'][0], v['outfit'][1], gain=v['outfit'][2] if len(v['outfit']) > 2 else 2.4)
    hbc = recolour(os.path.join(tex, 'T_%s_PR_Hair_BC.png' % base), os.path.join(outdir, 'T_%s_PR_Hair_BC.png' % name), v['hair'], is_any, keep=0.1, gain=2.0) if v.get('hair') else None
    mats = {}
    for key, path in (('Outfit', obc),) + ((('Hair', hbc),) if hbc else ()):
        src = next(m for m in lods[0].data.materials if m.name.endswith('_PR_' + key)); m = src.copy(); m.name = 'MI_%s_PR_%s' % (name, key); N.swap_image(m, 'BC', path); mats[src.name] = m
    for k, o in lods.items():
        for i, m in enumerate(o.data.materials):
            if m.name in mats:
                o.data.materials[i] = mats[m.name]
        o.name = '%s_LOD%d' % (asset, k); o.data.name = o.name; o.hide_render = k != 0
    fbx = []
    for k in sorted(lods):
        o = lods[k]; o.hide_render = False; p = os.path.join(outdir, '%s_LOD%d.fbx' % (asset, k)); C.export_skeletal(p, arm, o); fbx.append(L.rel(p)); o.hide_render = k != 0
    R = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0); lo = lods[0]
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=25, el=6, fill=1.1, lens=70, res=(900, 1200), spp=160)
    L.shot(R, os.path.join(outdir, 'render_close.png'), center=(0, 0, 1.52), radius=0.33, az=22, el=4, fill=0.9, lens=85, res=(1000, 800), spp=160, fstop=8)
    st = L.mesh_stats(lo); L.save_blend(os.path.join(outdir, asset + '.blend'))
    write_manifest(outdir, {
        'name': asset, 'class': 'character_humanoid', 'fbx': fbx[0], 'lod_fbx': fbx, 'source_blend': L.rel(os.path.join(outdir, asset + '.blend')), 'build': 'Unclaimed/tools/bl.sh %s %s' % (SCRIPT, name),
        'derived_from': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Characters/%s (SK_%s_Photoreal): mesh, LODs, skeleton and skin weights unchanged' % (base, base),
        'dimensions_m': st['dimensions_m'], 'lod0_triangles': st['triangles'], **{'lod%d_triangles' % k: L.tri_count(lods[k]) for k in sorted(lods) if k},
        'textures': [{'file': L.rel(obc), 'size_px': list(Image.open(obc).size), 'channels': 'base colour sRGB (outfit, recoloured)'}] + ([{'file': L.rel(hbc), 'size_px': list(Image.open(hbc).size), 'channels': 'base colour sRGB (hair, recoloured)'}] if hbc else []),
        'shared_textures': 'every other map (skin, eyes, gear, and the N / ORM / mask maps of outfit and hair) is the base character\'s, under PhotorealPass/Characters/%s/Textures' % base,
        'materials': [m.name for m in lo.data.materials], 'rig': {'skeleton': 'the 89-bone mannequin skeleton of the base, unchanged', 'bone_count': len(arm.data.bones), 'root_bone': 'root', 'animation': 'none delivered; shares the base skeleton'},
        'pivot': 'feet, front on -Y (as the base)', 'families': [v['fam'], v['seq']], 'origin_ids': L.origin_ids([v['fam']]), 'supersedes': 'none (placeholder greybox cards)', 'dresses': v['dresses'],
        'third_party': ['see the base character manifest'], 'status': 'source delivered; not imported into Unreal, not bound to any placement', 'known_weaknesses': W_VAR % base})


# ---------------------------------------------------------------------------------------------- corpses
def blood_bake(lo, wound, outdir, name, px=2048, amount=1.0, slots=('Skin', 'Outfit', 'Gear', 'Knight'), radius=0.5, ground=0.11):
    """bake blood into copies of the base-colour maps: soaked round the wound and wherever the body touches the ground, spattered elsewhere; one 3D mask shared by every material"""
    sc = bpy.context.scene; L.use_hip_gpu(sc); sc.cycles.samples = 4; sc.cycles.use_denoising = False; out = {}; targets = []; dummies = []
    for m in lo.data.materials:
        key = next((k for k in slots if m.name.endswith(k) or ('_%s' % k) in m.name), None); bc = N.mat_image(m, 'BC')
        if not key or not bc:                          # not baked: give it a throwaway target, or the bake would overwrite whichever image node is active (the hair map)
            dummy = bpy.data.images.new('bake_dummy', 8, 8); dn = m.node_tree.nodes.new('ShaderNodeTexImage'); dn.image = dummy; m.node_tree.nodes.active = dn; dummies.append((m, dn, dummy)); continue
        nt = m.node_tree; Lk = nt.links; geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); Lk.new(geo.outputs['Position'], sep.inputs[0])
        dist = nt.nodes.new('ShaderNodeVectorMath'); dist.operation = 'DISTANCE'; Lk.new(geo.outputs['Position'], dist.inputs[0]); dist.inputs[1].default_value = wound
        noi = nt.nodes.new('ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 4.5 / radius; noi.inputs['Detail'].default_value = 6.0; noi.inputs['Roughness'].default_value = 0.7; Lk.new(geo.outputs['Position'], noi.inputs['Vector'])
        spk = nt.nodes.new('ShaderNodeTexNoise'); spk.inputs['Scale'].default_value = 70.0; spk.inputs['Detail'].default_value = 3.0; Lk.new(geo.outputs['Position'], spk.inputs['Vector'])

        def mth(op, a, b, clamp=False):
            n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
            for i, v in enumerate((a, b)):
                if isinstance(v, (int, float)):
                    n.inputs[i].default_value = v
                else:
                    Lk.new(v, n.inputs[i])
            return n.outputs[0]
        near = mth('SUBTRACT', 1.0, mth('DIVIDE', dist.outputs['Value'], radius), clamp=True); low = mth('SUBTRACT', 1.0, mth('DIVIDE', sep.outputs[2], ground), clamp=True)
        field = mth('ADD', mth('ADD', mth('MULTIPLY', near, 1.1), mth('MULTIPLY', low, 0.8)), mth('MULTIPLY', mth('SUBTRACT', noi.outputs['Fac'], 0.5), 1.3))
        soak = mth('MULTIPLY', mth('SUBTRACT', field, 0.28), 5.0, clamp=True); spat = mth('MULTIPLY', mth('SUBTRACT', spk.outputs['Fac'], 0.64), 14.0, clamp=True); mask = mth('MULTIPLY', mth('MAXIMUM', soak, mth('MULTIPLY', spat, 0.8)), 0.94 * amount, clamp=True)
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; Lk.new(mask, mix.inputs[0]); Lk.new(bc.outputs[0], mix.inputs[6]); dark = nt.nodes.new('ShaderNodeMix'); dark.data_type = 'RGBA'; Lk.new(noi.outputs['Fac'], dark.inputs[0])
        dark.inputs[6].default_value = (0.030, 0.002, 0.002, 1); dark.inputs[7].default_value = (0.16, 0.006, 0.005, 1); Lk.new(dark.outputs[2], mix.inputs[7])
        em = nt.nodes.new('ShaderNodeEmission'); Lk.new(mix.outputs[2], em.inputs[0]); outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output); old = outn.inputs['Surface'].links[0].from_socket; Lk.new(em.outputs[0], outn.inputs['Surface'])
        img = bpy.data.images.new('bake_%s' % key, px, px, alpha=False, float_buffer=True, is_data=True); tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; nt.nodes.active = tn; targets.append((m, key, bc, img, tn, old, outn))
    L.activate(lo); bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
    for m, dn, dummy in dummies:
        m.node_tree.nodes.remove(dn); bpy.data.images.remove(dummy)
    for m, key, bc, img, tn, old, outn in targets:
        a = np.zeros(px * px * 4, np.float32); img.pixels.foreach_get(a); a = a.reshape(px, px, 4)[..., :3]; p = os.path.join(outdir, 'T_%s_%s_BC.png' % (name, key)); L.save_png(L.lin2srgb(a), p); out[key] = p
        m.node_tree.links.new(old, outn.inputs['Surface']); m.node_tree.nodes.remove(tn); bpy.data.images.remove(img); im = bpy.data.images.load(p); im.colorspace_settings.name = 'sRGB'; bc.image = im
    return out


CORPSES = {
    'Corpse_Mother': dict(base='Mother', fam='corpse_mom', seq='355 people/mom/death-', wound=(0.05, 0.25, 0.16), dresses='the dead mother of the burnt house, lying on her back in her red dress, arms flung out, soaked in blood',
                          pose=[('upperarm_l', 'Y', -35), ('upperarm_r', 'Y', 70), ('lowerarm_r', 'Y', 40), ('thigh_l', 'Y', 8), ('thigh_r', 'X', -18), ('calf_r', 'X', 30), ('head', 'Z', 40), ('spine_03', 'Z', 8)]),
    'Corpse_Maiden': dict(base='Mother', fam='corpse_maiden', seq='245 people/maiden/red/death-', wound=(-0.1, 0.1, 0.16), hair=(0.80, 0.62, 0.30), outfit=((0.62, 0.04, 0.07), is_red), yaw=160, dresses='dead woman in a crimson dress with fair hair, lying on her back with one knee drawn up, soaked in blood',
                          pose=[('upperarm_l', 'Y', 60), ('lowerarm_l', 'Y', 50), ('upperarm_r', 'Y', -20), ('thigh_l', 'X', -30), ('calf_l', 'X', 55), ('head', 'Z', -35)]),
    'Corpse_Soldier': dict(base='Milder', fam='corpse_soldier', seq='405 people/soldier/death-', wound=(0.0, 0.2, 0.2), outfit=((0.22, 0.13, 0.07), is_blue), yaw=35, dresses='dead soldier in jerkin and mail lying on his back, limbs sprawled, in a pool of blood',
                           pose=[('upperarm_l', 'Y', 55), ('upperarm_r', 'Y', -45), ('lowerarm_r', 'Y', -35), ('thigh_l', 'Y', 14), ('thigh_r', 'Y', -16), ('calf_l', 'X', 25), ('head', 'Z', 30)]),
    'Dink_Dead': dict(base='Dink', fam='dink_dead', seq='436 dink/die/ds-x3-', wound=(0.0, 0.15, 0.18), yaw=-50, amount=0.75, dresses='Dink lying dead on his back (the cutscene pose), arms out, blood under him',
                      pose=[('upperarm_l', 'Y', 40), ('upperarm_r', 'Y', -40), ('thigh_l', 'Y', 10), ('thigh_r', 'X', -15), ('calf_r', 'X', 25), ('head', 'Z', -30)]),
}
W_CORPSE = ('A posed copy of %s (its LOD2, about %d triangles) with the pose applied: no ragdoll, no wounds cut into the mesh, eyes open as in the base, clothes not draped by simulation (the skirt and limbs are flattened towards the ground by rule). '
            'Blood is baked into copies of the base-colour maps from one 3D mask: it does not change roughness or normal, so soaked cloth is not glossy. The pool under the body is the separate decal named in `companion_decal`. '
            'Normal and ORM maps are the base character\'s. One convex hull is exported; corpses are visual only in the game.')


def gore_ground():
    """review ground with the Blood_Pool_02 decal blended in under the body"""
    R = L.review_setup(ground=None, exposure=-5.0); dec = os.path.join(L.UNC, 'blood_splat', 'Blood_Pool_02')
    g = L.new_obj('ground', [(-15, -15, 0), (15, -15, 0), (15, 15, 0), (-15, 15, 0)], [(0, 1, 2, 3)], smooth=False); t = L.NT('ground_with_decal'); sset = t.scan('park_dirt', scale=0.6, proj='FLAT'); gb = t.bsdf
    t.set(base=sset['diff'], rough=sset['rough'], normal=t.normalmap(sset['nor_gl'], 1.0)); S_ = 2.2; uv = t.mapping(t.obj, scale=(1 / S_, 1 / S_, 1), loc=(0.5, 0.5, 0))
    bc = t.image(os.path.join(dec, 'T_Decal_Blood_Pool_02_BC.png'), 'sRGB', uv, ext='CLIP'); nm = t.image(os.path.join(dec, 'T_Decal_Blood_Pool_02_N.png'), 'Non-Color', uv, ext='CLIP'); orm = t.image(os.path.join(dec, 'T_Decal_Blood_Pool_02_ORM.png'), 'Non-Color', uv, ext='CLIP')
    db = t.node('ShaderNodeBsdfPrincipled'); sp = t.node('ShaderNodeSeparateColor'); t.L.new(orm.outputs[0], sp.inputs[0]); t.L.new(bc.outputs[0], db.inputs['Base Color']); t.L.new(sp.outputs[1], db.inputs['Roughness']); t.L.new(t.normalmap(nm.outputs[0], 1.0), db.inputs['Normal'])
    mx = t.node('ShaderNodeMixShader'); t.L.new(bc.outputs[1], mx.inputs[0]); t.L.new(gb.outputs[0], mx.inputs[1]); t.L.new(db.outputs[0], mx.inputs[2]); t.L.new(mx.outputs[0], t.out.inputs['Surface']); L.assign(g, t.mat)
    return R


def lay_down(ob, yaw=0.0, flatten=None, axis='X', angle=-90.0):
    """turn the standing mesh onto the ground (on its back by default), resting on z = 0, centred. The turn goes through the object matrix so
    custom normals (hair cards) turn with it. flatten = per-vertex 0..1: how far soft parts sink towards the ground (applied along the back-to-front axis first)"""
    if flatten is not None:
        P = L.co(ob); yb = P[:, 1].max(); P[:, 1] = yb - (yb - P[:, 1]) * (1 - 0.5 * flatten); L.set_co(ob, P)
    ob.matrix_world = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(angle), 4, axis); L.apply_xf(ob)
    P = L.co(ob); c = (P.min(0) + P.max(0)) / 2; c[2] = P[:, 2].min(); ob.matrix_world = Matrix.Translation(tuple(-c)); L.apply_xf(ob); return ob


def corpse(name):
    v = CORPSES[name]; base = v['base']; outdir = os.path.join(L.UNC, v['fam'], name); os.makedirs(outdir, exist_ok=True); arm, lods = N.open_char(base); tex = os.path.join(N.CHARS, base, 'Textures'); asset = 'SM_%s_PR' % name
    src = lods[2]
    for k, o in lods.items():
        o.hide_render = True
    for b, ax, deg in v['pose']:
        world_rot(arm, b, ax, deg)
    lo = L.dup(src, asset); lo.hide_render = False; names = [g.name for g in lo.vertex_groups]; legw = np.zeros(len(lo.data.vertices), np.float32)
    for vert in lo.data.vertices:
        legw[vert.index] = sum(g.weight for g in vert.groups if names[g.group].startswith(('thigh', 'calf', 'foot', 'ball', 'pelvis')))
    L.apply_mods(lo); lo.vertex_groups.clear(); lo.parent = None; lay_down(lo, v.get('yaw', 0.0) + 80.0, flatten=np.clip(legw, 0, 1) if base == 'Mother' else None)
    mats = []
    for i, m in enumerate(lo.data.materials):                 # private copies, so the base materials stay as they are
        mm = m.copy(); mm.name = m.name.replace('MI_%s_PR' % base, 'MI_%s' % name); lo.data.materials[i] = mm; mats.append(mm)
    if v.get('outfit'):
        N.swap_image(next(m for m in mats if m.name.endswith('Outfit')), 'BC', recolour(os.path.join(tex, 'T_%s_PR_Outfit_BC.png' % base), os.path.join(outdir, 'T_tmp_Outfit_BC.png'), v['outfit'][0], v['outfit'][1], gain=3.4 if v['outfit'][1] is is_red else 2.4, size=2048))
    hair_file = None
    if v.get('hair'):
        hair_file = recolour(os.path.join(tex, 'T_%s_PR_Hair_BC.png' % base), os.path.join(outdir, 'T_%s_Hair_BC.png' % name), v['hair'], is_any, keep=0.1, gain=2.0, size=2048); N.swap_image(next(m for m in mats if m.name.endswith('Hair')), 'BC', hair_file)
    files = blood_bake(lo, v['wound'], outdir, name, amount=v.get('amount', 1.0))
    if os.path.exists(os.path.join(outdir, 'T_tmp_Outfit_BC.png')):
        os.remove(os.path.join(outdir, 'T_tmp_Outfit_BC.png'))
    R = gore_ground()
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=25, el=38, fill=1.05, lens=60, spp=160); L.shot(R, os.path.join(outdir, 'render_close.png'), [lo], az=-40, el=24, fill=1.3, lens=80, res=(1000, 800), spp=160, fstop=8)
    ac = L.coll(asset); ac['dink_class'] = 'prop'; L.link(lo, ac); ucx = L.make_ucx(lo); st = L.mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, [lo, ucx]); L.save_blend(os.path.join(outdir, asset + '.blend'))
    tx = [{'file': L.rel(p), 'size_px': list(Image.open(p).size), 'channels': 'base colour sRGB with baked blood (%s)' % k} for k, p in files.items()] + ([{'file': L.rel(hair_file), 'size_px': [2048, 2048], 'channels': 'base colour sRGB (hair, recoloured)'}] if hair_file else [])
    write_manifest(outdir, {
        'name': asset, 'class': 'prop', 'fbx': L.rel(fbx), 'source_blend': L.rel(os.path.join(outdir, asset + '.blend')), 'build': 'Unclaimed/tools/bl.sh %s %s' % (SCRIPT, name),
        'derived_from': 'DinkRemasterUE/SourceAssets/Art/PhotorealPass/Characters/%s (SK_%s_Photoreal, LOD2), posed and frozen' % (base, base), 'dimensions_m': st['dimensions_m'], 'lod0_triangles': st['triangles'],
        'triangle_budget': {'soft': 6000, 'hard': 20000, 'within_soft': st['triangles'] <= 6000}, 'textures': tx,
        'shared_textures': 'N / ORM (and hair masks, eyes) are the base character\'s maps under PhotorealPass/Characters/%s/Textures' % base, 'materials': [m.name for m in lo.data.materials], 'collision_hulls': 1,
        'companion_decal': 'Unclaimed/blood_splat/Blood_Pool_02 (2.2 m), centred under the body; the render shows it', 'pivot': 'base centre, lying on z = 0', 'families': [v['fam'], v['seq']], 'origin_ids': L.origin_ids([v['fam']]),
        'supersedes': 'none (placeholder greybox cards)', 'dresses': v['dresses'], 'third_party': ['park_dirt (render ground)', 'see the base character manifest'], 'status': 'source delivered; not imported into Unreal, not bound to any placement',
        'known_weaknesses': W_CORPSE % ('SK_%s_Photoreal' % base, st['triangles'])})


def corpse_knight():
    """the dead knight: this folder's SK_Knight_PR (red set), fallen on his back with the halberd still in his hand"""
    name = 'Corpse_Knight'; outdir = os.path.join(L.UNC, 'corpse_knight', name); os.makedirs(outdir, exist_ok=True); kd = os.path.join(L.UNC, 'npc_knight_blue', 'Knight'); asset = 'SM_%s_PR' % name
    bpy.ops.wm.open_mainfile(filepath=os.path.join(kd, 'SK_Knight_PR.blend')); sc = bpy.context.scene; L.use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); src = bpy.data.objects['SK_Knight_PR_LOD1']
    for o in bpy.data.objects:
        o.hide_render = True
    for b, ax, deg in [('upperarm_l', 'Y', 50), ('lowerarm_l', 'Y', 30), ('upperarm_r', 'Y', -25), ('thigh_l', 'Y', 12), ('thigh_r', 'X', -20), ('calf_r', 'X', 35), ('head', 'Z', 35)]:
        world_rot(arm, b, ax, deg)
    lo = L.dup(src, asset); lo.hide_render = False; lo.hide_viewport = False; L.apply_mods(lo); lo.vertex_groups.clear(); lo.parent = None; lay_down(lo, 105.0)
    m = lo.data.materials[0].copy(); m.name = 'MI_Corpse_Knight'; lo.data.materials[0] = m; N.swap_image(m, 'BC', os.path.join(kd, 'T_Knight_PR_Red_BC.png'))
    files = blood_bake(lo, (0.0, 0.1, 0.25), outdir, name, slots=('Knight',))
    R = gore_ground()
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=25, el=38, fill=1.05, lens=60, spp=160); L.shot(R, os.path.join(outdir, 'render_close.png'), [lo], az=-40, el=24, fill=1.3, lens=80, res=(1000, 800), spp=160, fstop=8)
    ac = L.coll(asset); ac['dink_class'] = 'prop'; L.link(lo, ac); ucx = L.make_ucx(lo); st = L.mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, [lo, ucx]); L.save_blend(os.path.join(outdir, asset + '.blend'))
    write_manifest(outdir, {
        'name': asset, 'class': 'prop', 'fbx': L.rel(fbx), 'source_blend': L.rel(os.path.join(outdir, asset + '.blend')), 'build': 'Unclaimed/tools/bl.sh %s Corpse_Knight' % SCRIPT,
        'derived_from': 'Unclaimed/npc_knight_blue/Knight (SK_Knight_PR, LOD1, red set), posed and frozen', 'dimensions_m': st['dimensions_m'], 'lod0_triangles': st['triangles'], 'triangle_budget': {'soft': 6000, 'hard': 20000, 'within_soft': st['triangles'] <= 6000},
        'textures': [{'file': L.rel(p), 'size_px': list(Image.open(p).size), 'channels': 'base colour sRGB with baked blood'} for p in files.values()], 'shared_textures': 'T_Knight_PR_N.png and T_Knight_PR_ORM.png of the knight',
        'materials': ['MI_Corpse_Knight'], 'collision_hulls': 1, 'companion_decal': 'Unclaimed/blood_splat/Blood_Pool_02 (2.2 m), centred under the body; the render shows it', 'pivot': 'base centre, lying on z = 0',
        'families': ['corpse_knight', '275 people/knight/red/death-'], 'origin_ids': L.origin_ids(['corpse_knight']), 'supersedes': 'none (placeholder greybox cards)',
        'dresses': 'dead knight in red plate lying on his back, the halberd beside him, armour streaked with blood', 'third_party': ['park_dirt (render ground)'], 'status': 'source delivered; not imported into Unreal, not bound to any placement',
        'known_weaknesses': 'The knight\'s rigid plate parts posed and frozen: an empty harness with nobody inside, as the standing knight. Blood is baked into the base colour only. The pool under the body is the separate decal named in `companion_decal`.'})


def corpse_dragon():
    """the dead dragon: this folder's SK_Dragon_PR collapsed on its side, wings folded, neck and tail on the ground, the hide drenched in blood"""
    name = 'Dragon_Corpse'; outdir = os.path.join(L.UNC, 'dragon_corpse', name); os.makedirs(outdir, exist_ok=True); dd = os.path.join(L.UNC, 'dragon', 'Dragon'); asset = 'SM_%s_PR' % name
    bpy.ops.wm.open_mainfile(filepath=os.path.join(dd, 'SK_Dragon_PR.blend')); sc = bpy.context.scene; L.use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); src = bpy.data.objects['SK_Dragon_PR_LOD1']
    for o in bpy.data.objects:
        o.hide_render = True
    for b, ax, deg in [('wing_01_l', 'Y', 75), ('wing_02_l', 'Y', 40), ('wing_01_r', 'Y', -100), ('wing_02_r', 'Y', -30), ('neck_01', 'X', 35), ('neck_02', 'X', 30), ('neck_03', 'X', 25), ('head', 'X', 20),
                       ('tail_02', 'X', -14), ('tail_03', 'X', -14), ('tail_04', 'Z', 25), ('tail_05', 'Z', 30), ('thigh_l', 'X', 35), ('calf_l', 'X', -30), ('thigh_r', 'X', -20), ('upperarm_l', 'X', 40)]:
        world_rot(arm, b, ax, deg)
    lo = L.dup(src, asset); lo.hide_render = False; lo.hide_viewport = False; L.apply_mods(lo); lo.vertex_groups.clear(); lo.parent = None; lay_down(lo, 30.0, axis='Y', angle=82.0)
    m = lo.data.materials[0].copy(); m.name = 'MI_Dragon_Corpse'; lo.data.materials[0] = m
    files = blood_bake(lo, (0.2, 0.0, 0.5), outdir, name, slots=('Dragon',), radius=2.2, ground=0.45, amount=1.0)
    R = gore_ground()
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], az=25, el=34, fill=1.05, lens=50, spp=160); L.shot(R, os.path.join(outdir, 'render_close.png'), [lo], az=-40, el=22, fill=1.5, lens=70, res=(1000, 800), spp=160, fstop=8)
    ac = L.coll(asset); ac['dink_class'] = 'prop_large'; L.link(lo, ac); ucx = L.make_ucx(lo); st = L.mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, [lo, ucx]); L.save_blend(os.path.join(outdir, asset + '.blend'))
    write_manifest(outdir, {
        'name': asset, 'class': 'prop_large', 'fbx': L.rel(fbx), 'source_blend': L.rel(os.path.join(outdir, asset + '.blend')), 'build': 'Unclaimed/tools/bl.sh %s Dragon_Corpse' % SCRIPT,
        'derived_from': 'Unclaimed/dragon/Dragon (SK_Dragon_PR, LOD1), posed and frozen', 'dimensions_m': st['dimensions_m'], 'lod0_triangles': st['triangles'], 'triangle_budget': {'soft': 20000, 'hard': 60000, 'within_soft': st['triangles'] <= 20000},
        'textures': [{'file': L.rel(p), 'size_px': list(Image.open(p).size), 'channels': 'base colour sRGB with baked blood'} for p in files.values()], 'shared_textures': 'T_Dragon_PR_N.png and T_Dragon_PR_ORM.png of the dragon',
        'materials': ['MI_Dragon_Corpse'], 'collision_hulls': 1, 'companion_decal': 'a blood pool decal scaled to about 5 m under the body (the render shows Blood_Pool_02 at 2.2 m)', 'pivot': 'base centre, lying on z = 0',
        'families': ['dragon_corpse', '212 foes/dragon/f2-x3-', '216 foes/dragon/f2-x7-'], 'origin_ids': L.origin_ids(['dragon_corpse']), 'supersedes': 'none (placeholder greybox cards)',
        'dresses': 'the dead dragon collapsed on its side, wings folded, neck and tail on the ground, drenched in blood', 'third_party': ['park_dirt (render ground)'], 'status': 'source delivered; not imported into Unreal, not bound to any placement',
        'known_weaknesses': 'PARTIAL. The original frames show a torn carcass: raw flesh, a severed wing and tail, scattered chunks. This is the whole dragon posed dead and soaked in blood; nothing is cut, opened or separated, so the gore of the original is only hinted at by colour. '
                            'Posed by bone rotations and frozen (no ragdoll); limbs and wings may pass through each other. Inherits every weakness of the dragon mesh.'})


if __name__ == '__main__':
    a = L.args(); names = (list(VARIANTS) + list(CORPSES) + ['Corpse_Knight', 'Dragon_Corpse']) if a[0] == 'all' else a[0].split(',')
    for n in names:
        if n in VARIANTS:
            variant(n)
        elif n in CORPSES:
            corpse(n)
        elif n == 'Corpse_Knight':
            corpse_knight()
        elif n == 'Dragon_Corpse':
            corpse_dragon()
