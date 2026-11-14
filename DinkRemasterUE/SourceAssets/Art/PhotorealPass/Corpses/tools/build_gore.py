"""The corpse kit: remains whose gore is part of the asset, as the 1997 sprites show it (the owner's rule: keep ALL
original gore, never less than 1997; 13 Nov 2026: "increased the blood and everything, like the 1997").

Every asset is ONE static mesh that a row of families.json can place: the body with its wounds on one baked atlas,
and under it a flat card with the pool of blood, the thrown drops and the mist (tools/gore_sheets.py, alpha-tested),
so nothing depends on a companion decal.

  Dragon_Corpse     sprites 212 / 216: the dragon torn open; ribs, raw flesh and entrails, one wing torn off
  Corpse_Knight     sprite 275: the knight on his back, the snapped halberd shaft standing in his chest, its head in the blood
  Corpse_<Person>   the posed bodies of PhotorealPass/Unclaimed (merchant blue and green, girl, maiden, mother, peasant,
                    soldier, Dink), soaked and gashed, each in its own pool
  Blood_Splat_*     sprites 187-189: thrown blood without a body (cards only)
  Burn_Hole_*       sprite 158: scorch holes (cards only)

Sources are read from PhotorealPass/Unclaimed (the rigged dragon and knight, the posed bodies) and PhotorealPass/Characters.

    ../../Unclaimed/tools/bl.sh ../../Corpses/tools/build_gore.py <name[,name...]|all|people|sheets> [preview]

`preview` skips the bake and the export and writes quick renders of the high source to _review/.
"""
import bpy, bmesh, json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); CORP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(CORP), 'Unclaimed', 'tools')); sys.path.insert(0, HERE)
import pplib as L
import gore_sheets as GS
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SCRIPT = 'build_gore.py'
REVIEW = os.path.join(CORP, '_review')
RNG = np.random.default_rng(1997)


# ------------------------------------------------------------------------------------------------ source handling
def open_src(folder, blend):
    d = os.path.join(L.UNC, *folder); bpy.ops.wm.open_mainfile(filepath=os.path.join(d, blend)); sc = bpy.context.scene; L.use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    for im in bpy.data.images:                       # stored paths are relative or scrubbed: find each map by its file name
        fn = os.path.basename(im.filepath.replace('\\', '/'))
        if fn and os.path.exists(os.path.join(d, fn)):
            im.filepath = os.path.join(d, fn); im.reload()
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE'), d


def world_rot(arm, bone, axis, deg):
    """turn a pose bone (and its children) about a world axis through the bone's head"""
    bpy.context.view_layer.update(); pb = arm.pose.bones[bone]; h = arm.matrix_world @ pb.head; R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix; bpy.context.view_layer.update()


def aim(arm, bone, target):
    """turn a pose bone (and its children) so it points along a world direction"""
    bpy.context.view_layer.update(); pb = arm.pose.bones[bone]; h = arm.matrix_world @ pb.head; d = ((arm.matrix_world @ pb.tail) - h).normalized(); tv = Vector(target).normalized(); ax = d.cross(tv)
    if ax.length < 1e-6:
        return
    R = Matrix.Translation(h) @ Matrix.Rotation(d.angle(tv), 4, ax.normalized()) @ Matrix.Translation(-h); pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix; bpy.context.view_layer.update()


def bone_pos(arm, bone, tail=False):
    bpy.context.view_layer.update(); pb = arm.pose.bones[bone]; return np.array(arm.matrix_world @ (pb.tail if tail else pb.head))


def posed_copy(src, name):
    """the posed LOD as a plain mesh, with its skin weights as arrays {group: per-vertex weight}"""
    lo = L.dup(src, name); lo.hide_render = False; lo.hide_viewport = False; L.apply_mods(lo); lo.parent = None; names = [g.name for g in lo.vertex_groups]
    W = {n: np.zeros(len(lo.data.vertices)) for n in names}
    for v in lo.data.vertices:
        for g in v.groups:
            W[names[g.group]][v.index] = g.weight
    lo.vertex_groups.clear(); return lo, W


def drop_everything_but(keep):
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if not c.all_objects:
            bpy.data.collections.remove(c)


def split_verts(ob, mask, name):
    """move the faces whose vertices are all in mask into a new object; returns it"""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table(); faces = [f for f in bm.faces if all(mask[v.index] for v in f.verts)]
    other = L.dup(ob, name); bm2 = bmesh.new(); bm2.from_mesh(other.data); bm2.verts.ensure_lookup_table()
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if not all(mask[v.index] for v in f.verts)], context='FACES'); bm2.to_mesh(other.data); bm2.free()
    bmesh.ops.delete(bm, geom=faces, context='FACES'); bm.to_mesh(ob.data); bm.free(); ob.data.update(); other.data.update(); return other


def delete_faces(ob, fn):
    """delete the faces whose centre satisfies fn(centres (n, 3)) -> bool array"""
    bm = bmesh.new(); bm.from_mesh(ob.data); C = np.array([f.calc_center_median()[:] for f in bm.faces]); kill = fn(C)
    bmesh.ops.delete(bm, geom=[f for f, k in zip(bm.faces, kill) if k], context='FACES'); loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS'); bm.to_mesh(ob.data); bm.free(); ob.data.update(); return ob


def drop_small_islands(ob, min_faces=14):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table(); seen = set(); kill = []
    for f in bm.faces:
        if f.index in seen:
            continue
        isl = [f]; seen.add(f.index); i = 0
        while i < len(isl):
            for e in isl[i].edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index); isl.append(g)
            i += 1
        if len(isl) < min_faces:
            kill += isl
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS'); bm.to_mesh(ob.data); bm.free(); ob.data.update(); return ob


def torn_rim(ob, depth, slot, seed=3):
    """turn every open border of the hide inwards: a strip of raw flesh (material slot `slot`) that runs from the torn edge into the body"""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.normal_update(); uvl = bm.loops.layers.uv.active; edges = [e for e in bm.edges if e.is_boundary]
    if not edges:
        bm.free(); return ob
    inner = {}
    for e in edges:
        for v in e.verts:
            if v not in inner:
                n = v.normal; j = 0.6 + 0.8 * L._hash(int(v.co.x * 997), int(v.co.y * 991), int(v.co.z * 983), seed)
                inner[v] = bm.verts.new(v.co - n * depth * j)
    for e in edges:
        a, b = e.verts; f0 = e.link_faces[0]; la = next(l for l in f0.loops if l.vert is a); order = (b, a) if la.link_loop_next.vert is b else (a, b)
        f = bm.faces.new((order[0], order[1], inner[order[1]], inner[order[0]])); f.material_index = slot; f.smooth = True
        if uvl:                                      # its own small rectangle at true proportions (packed with the rest later)
            w = max((order[0].co - order[1].co).length, 1e-4); h = max(depth, 1e-4)
            for l, uvq in zip(f.loops, ((0.0, 0.0), (w, 0.0), (w, h), (0.0, h))):
                l[uvl].uv = uvq
    bm.to_mesh(ob.data); bm.free(); ob.data.update(); return ob


def scale_all(obs, s):
    for o in obs:
        L.set_co(o, L.co(o) * s)


def shift_all(obs, d):
    for o in obs:
        L.set_co(o, L.co(o) + np.asarray(d))


# ------------------------------------------------------------------------------------------------ gore materials
BLOOD_DARK = (0.022, 0.0012, 0.0012); BLOOD_MID = (0.06, 0.003, 0.0025); BLOOD_BRIGHT = (0.11, 0.005, 0.004)
# In the game the dry-earth screens are exposed bright: the first set of colours (pool rim 0.39 linear) read as red paint there (capture of 14 Nov 2026).


def m_flesh(name='flesh', k=1.0):
    """raw muscle: fibre bundles in deep red, pale fat and sinew between them, wet"""
    t = L.NT(name); fib = t.mapping(t.obj, scale=(22 * k, 22 * k, 6 * k), rot=(0.4, 0.3, 0.0)); v = t.voronoi(1.0, vec=fib, feature='F1'); edge = t.voronoi(1.0, vec=fib, feature='DISTANCE_TO_EDGE')
    big = t.noise(4.5 * k, 5, 0.6); fine = t.noise(70 * k, 4, 0.6)
    col = t.ramp(t.math('ADD', t.math('MULTIPLY', big, 0.75), t.math('MULTIPLY', v, 0.35)), [(0.25, (0.018, 0.0014, 0.0014)), (0.45, (0.04, 0.002, 0.002)), (0.62, (0.075, 0.005, 0.004)), (0.85, (0.12, 0.014, 0.010))])
    fat = t.ramp(t.math('ADD', t.math('MULTIPLY', edge, 6.0), t.math('MULTIPLY', t.noise(9 * k, 4, 0.6), 1.2)), [(0.42, 1.0), (0.58, 0.0)])            # pale seams between the bundles, in patches
    col = t.mix(t.math('MULTIPLY', fat, 0.38), col, (0.22, 0.11, 0.07)); clot = t.ramp(t.noise(11 * k, 5, 0.65), [(0.60, 0.0), (0.70, 1.0)]); col = t.mix(t.math('MULTIPLY', clot, 0.85), col, BLOOD_DARK)
    h = t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, edge), -0.5), t.math('ADD', t.math('MULTIPLY', big, 1.2), t.math('MULTIPLY', fine, 0.12)))
    t.set(base=col, rough=t.mixf(clot, t.maprange(fine, 0.3, 0.7, 0.42, 0.60), 0.38), normal=t.bump(h, 0.35, 0.008 / k), spec=0.3); return t.mat


def m_bone(name='bone'):
    """rib and vertebra: ivory, pitted, blood in the pits and at the broken ends"""
    t = L.NT(name); n = t.noise(26, 5, 0.6); st = t.ramp(t.noise(9, 4, 0.6), [(0.46, 1.0), (0.66, 0.0)])
    col = t.mix(n, (0.36, 0.29, 0.19), (0.52, 0.45, 0.33)); col = t.mix(t.math('MULTIPLY', st, 0.92), col, BLOOD_MID)
    t.set(base=col, rough=t.mixf(st, 0.55, 0.28), normal=t.bump(n, 0.25, 0.002), spec=0.4); return t.mat


def m_gut(name='gut'):
    """entrails: grey-pink, veined, slick"""
    t = L.NT(name); n = t.noise(14, 4, 0.55); vein = t.ramp(t.voronoi(40, feature='DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.06, 0.0)]); bl = t.ramp(t.noise(5, 4, 0.6), [(0.45, 1.0), (0.66, 0.0)])
    col = t.mix(n, (0.22, 0.10, 0.09), (0.34, 0.19, 0.16)); col = t.mix(t.math('MULTIPLY', vein, 0.6), col, (0.20, 0.02, 0.05)); col = t.mix(t.math('MULTIPLY', bl, 0.8), col, BLOOD_MID)
    t.set(base=col, rough=0.26, normal=t.bump(t.math('ADD', n, t.math('MULTIPLY', vein, -0.3)), 0.3, 0.004), spec=0.5); return t.mat


def m_blood(name='blood', k=1.0):
    """pooled blood: nearly black where it is deep, red where it thins out at the rim, a skin of half-dried clots"""
    t = L.NT(name); z = t.sep(t.obj)[2]; deep = t.maprange(z, 0.0015, 0.011, 0.0, 1.0); n = t.noise(6 * k, 5, 0.6); clot = t.ramp(t.noise(34 * k, 4, 0.7), [(0.60, 0.0), (0.68, 1.0)])
    col = t.mix(t.math('MULTIPLY', deep, 0.9), BLOOD_BRIGHT, BLOOD_DARK); col = t.mix(t.math('MULTIPLY', n, 0.5), col, BLOOD_MID); col = t.mix(t.math('MULTIPLY', clot, 0.7), col, (0.012, 0.001, 0.001))
    t.set(base=col, rough=t.mixf(clot, t.maprange(deep, 0, 1, 0.44, 0.27), 0.50), normal=t.bump(t.math('ADD', t.math('MULTIPLY', n, 0.4), clot), 0.14, 0.0015), spec=0.38); return t.mat


def worn_steel(mat, bc_path):
    """turn a clean plate-armour material into worn steel: the silver base colour map, grime in patches, scratches, dull and uneven
    roughness, dents. Rewires base colour, roughness and normal of its Principled BSDF."""
    nt = mat.node_tree; Lk = nt.links; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bc = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.upper().split('.')[0].endswith('_BC')); im = bpy.data.images.load(bc_path); im.colorspace_settings.name = 'sRGB'; bc.image = im

    def node(typ, **kw):
        n = nt.nodes.new(typ)
        for k_, v in kw.items():
            setattr(n, k_, v)
        return n

    def noise(scale, detail, vec=None, rough=0.6):
        n = node('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough; Lk.new(vec or geo.outputs['Position'], n.inputs['Vector']); return n.outputs['Fac']

    def ramp(src, lo, hi):
        n = node('ShaderNodeMapRange'); n.inputs['From Min'].default_value = lo; n.inputs['From Max'].default_value = hi; Lk.new(src, n.inputs['Value']); return n.outputs['Result']

    def mixc(fac, a, bcol):
        n = node('ShaderNodeMix', data_type='RGBA'); Lk.new(fac, n.inputs[0])
        if isinstance(a, tuple):
            n.inputs[6].default_value = a + (1,)
        else:
            Lk.new(a, n.inputs[6])
        n.inputs[7].default_value = bcol + (1,); return n.outputs[2]
    geo = node('ShaderNodeNewGeometry')
    grime = ramp(noise(7.0, 6, rough=0.7), 0.40, 0.62); fine = noise(140.0, 3)
    mp = node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (260.0, 9.0, 9.0); mp.inputs['Rotation'].default_value = (0.3, 0.5, 0.9); Lk.new(geo.outputs['Position'], mp.inputs['Vector'])
    mp2 = node('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (8.0, 240.0, 11.0); mp2.inputs['Rotation'].default_value = (0.8, 0.1, 0.4); Lk.new(geo.outputs['Position'], mp2.inputs['Vector'])
    s1 = ramp(noise(1.0, 2, mp.outputs[0]), 0.70, 0.76); s2 = ramp(noise(1.0, 2, mp2.outputs[0]), 0.71, 0.77)
    mx = node('ShaderNodeMath', operation='MAXIMUM'); Lk.new(s1, mx.inputs[0]); Lk.new(s2, mx.inputs[1]); scr = mx.outputs[0]
    g2 = node('ShaderNodeMath', operation='MULTIPLY'); Lk.new(grime, g2.inputs[0]); g2.inputs[1].default_value = 0.86
    col = mixc(g2.outputs[0], bc.outputs[0], (0.030, 0.026, 0.022))          # old oil, dirt and rust-brown in patches
    tar = mixc(ramp(noise(3.0, 5), 0.44, 0.70), col, (0.085, 0.052, 0.034)); sc2 = node('ShaderNodeMath', operation='MULTIPLY'); Lk.new(scr, sc2.inputs[0]); sc2.inputs[1].default_value = 0.55
    col = mixc(sc2.outputs[0], tar, (0.52, 0.52, 0.53))                      # bright scratches through to clean steel
    Lk.new(col, b.inputs['Base Color'])
    r = b.inputs['Roughness']; old = r.links[0].from_socket if r.links else None
    rr = node('ShaderNodeMix', data_type='FLOAT'); Lk.new(grime, rr.inputs[0]); rr.inputs[2].default_value = 0.42; rr.inputs[3].default_value = 0.70
    r2 = node('ShaderNodeMix', data_type='FLOAT'); Lk.new(scr, r2.inputs[0]); Lk.new(rr.outputs[0], r2.inputs[2]); r2.inputs[3].default_value = 0.28
    r3 = node('ShaderNodeMath', operation='ADD'); Lk.new(r2.outputs[0], r3.inputs[0]); f2 = node('ShaderNodeMath', operation='MULTIPLY'); Lk.new(fine, f2.inputs[0]); f2.inputs[1].default_value = 0.10; Lk.new(f2.outputs[0], r3.inputs[1])
    Lk.new(r3.outputs[0], r)
    nrm = b.inputs['Normal']; oldn = nrm.links[0].from_socket if nrm.links else None
    vo = node('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 11.0; Lk.new(geo.outputs['Position'], vo.inputs['Vector'])
    dent = ramp(vo.outputs['Distance'], 0.0, 0.22); hh = node('ShaderNodeMath', operation='ADD'); Lk.new(dent, hh.inputs[0]); s3 = node('ShaderNodeMath', operation='MULTIPLY'); Lk.new(scr, s3.inputs[0]); s3.inputs[1].default_value = -0.25; Lk.new(s3.outputs[0], hh.inputs[1])
    bp = node('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.7; bp.inputs['Distance'].default_value = 0.006; Lk.new(hh.outputs[0], bp.inputs['Height'])
    if oldn is not None:
        Lk.new(oldn, bp.inputs['Normal'])
    Lk.new(bp.outputs['Normal'], nrm)
    return mat


def bloody(mat, centres, ground=0.10, amount=1.0, spatter=0.62, keep_metal=False, drench=0.0, use_link=False, runs=None):
    """soak a baked material in blood: around each (xyz, radius) centre, wherever it comes near the ground, and in spatters elsewhere.
    Rewires base colour, roughness and metallic of its Principled BSDF; the base colour is taken straight from the BC map (no AO multiply)."""
    nt = mat.node_tree; Lk = nt.links; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); bc = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.upper().split('.')[0].endswith('_BC')), None)
    base_src = bc.outputs[0] if (bc and not use_link) else (b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].links else None); base_def = tuple(b.inputs['Base Color'].default_value)

    def node(typ, **kw):
        n = nt.nodes.new(typ)
        for k_, v in kw.items():
            setattr(n, k_, v)
        return n

    def mth(op, a, b_=None, clamp=False):
        n = node('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b_)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        return n.outputs[0]
    geo = node('ShaderNodeNewGeometry'); sep = node('ShaderNodeSeparateXYZ'); Lk.new(geo.outputs['Position'], sep.inputs[0]); near = None
    for c, r in centres:
        d = node('ShaderNodeVectorMath', operation='DISTANCE'); Lk.new(geo.outputs['Position'], d.inputs[0]); d.inputs[1].default_value = tuple(float(x) for x in c)
        v = mth('SUBTRACT', 1.0, mth('DIVIDE', d.outputs['Value'], float(r)), clamp=True); near = v if near is None else mth('MAXIMUM', near, v)
    noi = node('ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 7.0; noi.inputs['Detail'].default_value = 6.0; noi.inputs['Roughness'].default_value = 0.7; Lk.new(geo.outputs['Position'], noi.inputs['Vector'])
    spk = node('ShaderNodeTexNoise'); spk.inputs['Scale'].default_value = 130.0; spk.inputs['Detail'].default_value = 2.0; Lk.new(geo.outputs['Position'], spk.inputs['Vector'])
    low = mth('SUBTRACT', 1.0, mth('DIVIDE', sep.outputs[2], ground), clamp=True)
    field = mth('ADD', mth('ADD', mth('MULTIPLY', near if near is not None else 0.0, 1.25), mth('MULTIPLY', low, 0.9)), mth('MULTIPLY', mth('SUBTRACT', noi.outputs['Fac'], 0.5), 1.2))
    if runs:                                        # blood run down from a wound: streaks drawn out along Z, under and round (xyz, radius)
        rc, rr = runs; flat = node('ShaderNodeVectorMath', operation='MULTIPLY'); Lk.new(geo.outputs['Position'], flat.inputs[0]); flat.inputs[1].default_value = (1.0, 1.0, 0.0)
        dd = node('ShaderNodeVectorMath', operation='DISTANCE'); Lk.new(flat.outputs[0], dd.inputs[0]); dd.inputs[1].default_value = (float(rc[0]), float(rc[1]), 0.0)
        reach = mth('SUBTRACT', 1.0, mth('DIVIDE', dd.outputs['Value'], float(rr)), clamp=True); below = mth('MULTIPLY', mth('SUBTRACT', float(rc[2]) + 0.02, sep.outputs[2]), 40.0, clamp=True)
        mp = node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (34.0, 34.0, 2.2); Lk.new(geo.outputs['Position'], mp.inputs['Vector'])
        sn = node('ShaderNodeTexNoise'); sn.inputs['Scale'].default_value = 1.0; sn.inputs['Detail'].default_value = 3.0; Lk.new(mp.outputs[0], sn.inputs['Vector'])
        streak = mth('MULTIPLY', mth('SUBTRACT', sn.outputs['Fac'], 0.50), 7.0, clamp=True)
        field = mth('ADD', field, mth('MULTIPLY', mth('MULTIPLY', mth('MULTIPLY', reach, below), streak), 1.9))
    if drench:                                      # sprites 245, 335, 355, 405, 415: red from head to foot, whatever the height above the ground
        field = mth('ADD', field, float(drench))
    soak = mth('MULTIPLY', mth('SUBTRACT', field, 0.30), 5.0, clamp=True); spat = mth('MULTIPLY', mth('SUBTRACT', spk.outputs['Fac'], spatter), 14.0, clamp=True)
    mask = mth('MULTIPLY', mth('MAXIMUM', soak, mth('MULTIPLY', spat, 0.85)), 0.96 * amount, clamp=True)
    dark = node('ShaderNodeMix', data_type='RGBA'); Lk.new(noi.outputs['Fac'], dark.inputs[0]); dark.inputs[6].default_value = BLOOD_DARK + (1,); dark.inputs[7].default_value = (0.075, 0.003, 0.003, 1)
    mix = node('ShaderNodeMix', data_type='RGBA'); Lk.new(mask, mix.inputs[0])
    if base_src is not None:
        Lk.new(base_src, mix.inputs[6])
    else:
        mix.inputs[6].default_value = base_def
    Lk.new(dark.outputs[2], mix.inputs[7]); Lk.new(mix.outputs[2], b.inputs['Base Color'])
    for ch, wet in (('Roughness', 0.22), ('Metallic', None if keep_metal else 0.0)):
        if wet is None:
            continue
        s = b.inputs[ch]; m2 = node('ShaderNodeMix', data_type='FLOAT'); Lk.new(mth('MULTIPLY', mask, 0.85), m2.inputs[0])
        if s.links:
            Lk.new(s.links[0].from_socket, m2.inputs[2])
        else:
            m2.inputs[2].default_value = s.default_value
        m2.inputs[3].default_value = wet; Lk.new(m2.outputs[0], s)
    return mat


# ------------------------------------------------------------------------------------------------ gore geometry (high and game mesh share the shape functions)
def lump(name, centre, radii, seed, sub, amp=0.22, freq=None, rot=0.0, flat=None):
    """a displaced blob; the same call with a lower `sub` gives the game mesh of the same shape. flat = z below which it is cut off flat (resting on the ground)"""
    r = np.asarray(radii, float) if not np.isscalar(radii) else np.full(3, radii); ob = L.icosphere(name, 1.0, sub); P = L.co(ob); f = freq or 1.6
    d = 1.0 + amp * L.fbm(P * f + seed * 3.7, seed, 1.0, 4) + amp * 0.35 * L.fbm(P * f * 3.1 + seed, seed + 5, 1.0, 3); P = P * d[:, None] * r
    c, s = math.cos(rot), math.sin(rot); P = P @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]); P = P + np.asarray(centre, float)
    if flat is not None:
        P[:, 2] = np.maximum(P[:, 2], flat)
    L.set_co(ob, P); return ob


def pool(name, outline, n_theta=120, rings=7, h=0.011, edge=0.0016, centre=(0.0, 0.0)):
    """a pool of blood as a thin lens on the ground. outline(theta) -> radius. Top surface only; z runs from `edge` at the rim to `h` inside."""
    th = np.arange(n_theta) / n_theta * 2 * math.pi; R = outline(th); V = [(centre[0], centre[1], h)]; F = []
    for j in range(1, rings + 1):
        u = j / rings; rr = R * (u ** 0.8); z = edge + (h - edge) * np.clip(1 - u ** 6, 0, 1) if j < rings else np.full(n_theta, edge * 0.5)
        if j == rings:
            z = np.full(n_theta, 0.0004)
        for a, r_, z_ in zip(th, rr, np.broadcast_to(z, th.shape)):
            V.append((centre[0] + math.cos(a) * r_, centre[1] + math.sin(a) * r_, float(z_)))
    for k in range(n_theta):
        k1 = (k + 1) % n_theta; F.append((0, 1 + k, 1 + k1))
        for j in range(rings - 1):
            a = 1 + j * n_theta; b = 1 + (j + 1) * n_theta; F.append((a + k, b + k, b + k1, a + k1))
    ob = L.new_obj(name, V, F); L.fix_normals(ob)
    if L.vnormals(ob)[0][2] < 0:
        ob.data.flip_normals()
    return ob


def lobed(base, seed, lobes=0.22, fine=0.07, runs=()):
    """outline function: radius `base` (number or function of theta) broken into lobes; runs = [(angle, width, extra length)] tongues that reach further out"""
    def fn(th):
        b = base(th) if callable(base) else np.full(th.shape, float(base)); P = np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], 1)
        r = b * (1 + lobes * L.fbm(P * 1.3 + seed, seed, 1.0, 3) + fine * L.fbm(P * 6.0 + seed, seed + 9, 1.0, 3))
        for a, w, e in runs:
            d = np.angle(np.exp(1j * (th - a))); r = r + e * np.exp(-(d / w) ** 2)
        return r
    return fn


def splashes(prefix, n, r0, r1, seed, size=(0.012, 0.05), away=(0.0, 0.0)):
    """drops and streaks thrown out beyond a pool: small lenses, the far ones smaller and drawn out along the direction they flew"""
    rng = np.random.default_rng(seed); out = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi); u = rng.uniform(0, 1) ** 1.6; d = r0 + (r1 - r0) * u; s = size[1] - (size[1] - size[0]) * u ** 0.5; s *= rng.uniform(0.6, 1.3); el = 1.0 + rng.uniform(0.0, 2.2) * u
        ob = pool('%s_%02d' % (prefix, i), lobed(s, seed * 31 + i, lobes=0.35, fine=0.0), n_theta=12, rings=2, h=min(0.006, s * 0.25), edge=0.001)
        P = L.co(ob); P[:, 0] *= el; c, sn = math.cos(a), math.sin(a); P = P @ np.array([[c, sn, 0], [-sn, c, 0], [0, 0, 1]]); P[:, 0] += away[0] + c * d; P[:, 1] += away[1] + sn * d; L.set_co(ob, P); out.append(ob)
    return out


def with_mat(obs, mat):
    for o in (obs if isinstance(obs, (list, tuple)) else [obs]):
        L.assign(o, mat)
    return obs


def unwrap(ob, angle=66, top=False):
    """fresh UVs for a game-mesh part (packed together later)"""
    for l in list(ob.data.uv_layers):
        ob.data.uv_layers.remove(l)
    if top:                                          # flat things: project straight down
        uv = ob.data.uv_layers.new(name='UVMap'); P = L.co(ob); lo, hi = P.min(0), P.max(0); s = max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)
        for lp in ob.data.loops:
            p = P[lp.vertex_index]; uv.data[lp.index].uv = ((p[0] - lo[0]) / s, (p[1] - lo[1]) / s)
    else:
        L.smart_uv(ob, angle=angle, margin=0.006)
    return ob


def game_mesh(parts, name):
    """join the unwrapped parts, weight their texture share, pack once"""
    lo = L.join(parts, name) if len(parts) > 1 else parts[0]; lo.name = name; lo.data.name = name; lo.data.materials.clear(); L.clean_mesh(lo)
    lo.data.polygons.foreach_set('use_smooth', [True] * len(lo.data.polygons)); L.pack_uv(lo, margin=0.004, average=True); return lo


def preview(obs, tag, shots):
    R = L.review_setup(ground='park_dirt', ground_scale=0.6, exposure=-5.0)
    for i, kw in enumerate(shots):
        L.shot(R, os.path.join(REVIEW, '%s_%d.png' % (tag, i)), obs, spp=48, res=(1000, 750), **kw)


def final_renders(lo, outdir, beauty, close):
    R = L.review_setup(ground='park_dirt', ground_scale=0.6, exposure=-5.0)
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], spp=160, **beauty); L.shot(R, os.path.join(outdir, 'render_close.png'), [lo], spp=160, res=(1000, 800), **close)


# ------------------------------------------------------------------------------------------------ the kit's common steps
def relink(dirs):
    """stored image paths are relative or scrubbed: find each map by its file name in the given folders"""
    for im in bpy.data.images:
        fn = os.path.basename(im.filepath.replace('\\', '/'))
        if not fn or os.path.exists(bpy.path.abspath(im.filepath)):
            continue
        for d in dirs:
            if os.path.exists(os.path.join(d, fn)):
                im.filepath = os.path.join(d, fn); im.reload(); break


def ensure_principled(m):
    """bake_set reads Base Color / Roughness / Metallic / Alpha from a Principled BSDF; materials built from other shaders
    (the photoreal pass hair) get one that carries their base-colour map and its alpha"""
    nt = m.node_tree
    if any(n.type == 'BSDF_PRINCIPLED' for n in nt.nodes):
        return
    bc = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and os.path.basename(n.image.filepath).upper().endswith('_BC.PNG')), None)
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = 0.55
    if bc:
        nt.links.new(bc.outputs[0], b.inputs['Base Color']); nt.links.new(bc.outputs[1], b.inputs['Alpha'])
    nm = next((n for n in nt.nodes if n.type == 'NORMAL_MAP'), None)
    if nm:
        nt.links.new(nm.outputs[0], b.inputs['Normal'])
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output); nt.links.new(b.outputs[0], out.inputs['Surface'])


def spin_z(obs, ang, pivot=(0.0, 0.0)):
    c, s = math.cos(ang), math.sin(ang); R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]); pv = np.array([pivot[0], pivot[1], 0.0])
    for o in obs:
        L.set_co(o, (L.co(o) - pv) @ R.T + pv)


def mesh_dir(sprite_deg):
    """a direction read off the sprite (degrees anticlockwise from screen right) as a mesh XY angle in Blender: the game looks
    north, screen right is +X and screen up is +Y here (the FBX import turns +Y into Unreal's -Y, north); for yaw_from_sprite rows"""
    return math.radians(sprite_deg)


def bvh_of(ob):
    dg = bpy.context.evaluated_depsgraph_get(); return BVHTree.FromObject(ob, dg)


def drop_on(bvh, x, y, top=3.0):
    """the highest point of the body under (x, y): (location, normal) or None"""
    hit = bvh.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)))
    return (np.array(hit[0]), np.array(hit[1])) if hit[0] is not None else None


def gash(bvh, cxy, ang, length, width, seed, dense):
    """a slash laid open on the body: swollen lips and a groove of raw muscle between them. Built on the body's surface under the
    line through cxy. Returns the patch (None if the line misses the body)."""
    nu, nv = (40, 13) if dense else (10, 5); V = []; ok = True; d = np.array([math.cos(ang), math.sin(ang)]); p = np.array([-d[1], d[0]])
    for i in range(nu):
        u = -1 + 2 * i / (nu - 1); wob = 0.22 * width * math.sin(u * 5.0 + seed) + (0.07 * width * math.sin(u * 19.0 + seed * 1.7) if dense else 0.0)
        for j in range(nv):
            v = -1 + 2 * j / (nv - 1); w = width / 2 * (1 - u * u) ** 0.55 + 0.002; q = np.asarray(cxy) + d * u * length / 2 + p * (v * w + wob)
            h = drop_on(bvh, q[0], q[1])
            if h is None:
                ok = False; h = (np.array([q[0], q[1], 0.0]), np.array([0, 0, 1.0]))
            lip = math.exp(-((abs(v) - 0.72) / 0.22) ** 2) * (1 - u * u) ** 0.5; groove = math.exp(-(v / 0.38) ** 2)
            lift = (0.0010 + 0.0028 * lip - 0.0005 * groove) if dense else 0.0026
            V.append(h[0] + h[1] * lift)
    if not ok:
        return None
    F = [(i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1) for i in range(nu - 1) for j in range(nv - 1)]
    ob = L.new_obj('gash_%d_%s' % (seed, 'hi' if dense else 'lo'), V, F); L.fix_normals(ob)
    if L.vnormals(ob)[:, 2].mean() < 0:
        ob.data.flip_normals()
    return ob


def sheet_card(name, size, files, z=0.006, centre=(0.0, 0.0), anchor=False):
    """the ground card of a sheet: a square of `size` metres just above the ground, UV 0..1, alpha-tested.
    anchor adds one tiny triangle at z = 0 under the middle (the family layer stands a mesh on its lowest point)"""
    h = size / 2; V = [(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)]; F = [(0, 1, 2, 3)]
    if anchor:
        V += [(-0.004, -0.004, 0.0), (0.004, -0.004, 0.0), (0.0, 0.004, 0.0)]; F.append((4, 5, 6))
    ob = L.new_obj(name, [(x + centre[0], y + centre[1], zz) for x, y, zz in V], F, smooth=False); uv = ob.data.uv_layers.new(name='UVMap')
    for lp in ob.data.loops:
        x, y, _ = V[lp.vertex_index]; uv.data[lp.index].uv = ((x + h) / size, (y + h) / size) if lp.vertex_index < 4 else (0.002, 0.002)
    mat = L.game_material('MI_' + name, files, alpha='CLIP'); L.assign(ob, mat); return ob


def write_sheet(sheet, outdir, tname):
    os.makedirs(outdir, exist_ok=True); return GS.save(sheet, os.path.join(outdir, 'T_' + tname))


def finish(asset, cls, outdir, families, dresses, weaknesses, body=None, hi=(), card=None, px=2048, ss=2, alpha=False, extrude=0.005, maxdist=0.02,
           third_party=(), extra=None, beauty=None, close=None, ao_dist=None):
    """bake the body atlas, join the ground card, export one FBX object named after the asset, save the .blend, renders and manifest.json"""
    from PIL import Image
    os.makedirs(outdir, exist_ok=True); name = asset[3:]; ac = L.coll(asset); ac['dink_class'] = cls; parts = []; kit = []; stats = None
    if body is not None:
        L.link(body, ac); body.name = asset + '_body'
        files, stats = L.bake_set(body, list(hi), px, outdir, name, extrude=extrude, maxdist=maxdist, alpha=alpha, ss=ss, ao_dist=ao_dist, ao_floor=0.25)
        L.assign(body, L.game_material('MI_' + name, files, alpha='CLIP' if alpha else None)); parts.append(body)
        kit.append({'name': 'MI_' + name, 'kind': 'masked' if alpha else 'opaque', 'files': {k: L.rel(p) for k, p in files.items()}})
    if card is not None:
        ob, cfiles = card; L.link(ob, ac); parts.append(ob); kit.append({'name': ob.data.materials[0].name, 'kind': 'masked', 'files': {k: L.rel(p) for k, p in cfiles.items()}})
    for o in parts:
        for l in o.data.uv_layers:
            l.name = 'UVMap'
    lo = L.join(parts, asset) if len(parts) > 1 else parts[0]; lo.name = asset; lo.data.name = asset
    st = L.mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); L.export_fbx(fbx, [lo])
    for o in hi:
        try:
            bpy.data.objects.remove(o)
        except Exception:
            pass
    R = L.review_setup(ground='park_dirt', ground_scale=0.6, exposure=-5.0)
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), [lo], spp=128, **(beauty or dict(az=0, el=52, fill=1.0, lens=60)))
    L.shot(R, os.path.join(outdir, 'render_close.png'), [lo], spp=128, res=(1000, 800), **(close or dict(az=-35, el=24, fill=1.9, lens=70)))
    for im in list(bpy.data.images):                 # nothing but this asset's maps stays in the file
        if im.users == 0:
            bpy.data.images.remove(im)
    blend = os.path.join(outdir, asset + '.blend'); L.save_blend(blend)
    if os.path.exists(blend + '1'):
        os.remove(blend + '1')
    tex = [{'file': f, 'size_px': list(Image.open(os.path.join(L.REPO, f)).size), 'material': k['name'],
            'channels': {'BC': 'base colour sRGB' + (' + alpha (cut-out)' if k['kind'] == 'masked' else ''), 'N': 'tangent normal, OpenGL (green up; flip green on import)', 'ORM': 'R occlusion, G roughness, B metallic'}[r]}
           for k in kit for r, f in k['files'].items()]
    man = {'name': asset, 'class': cls, 'fbx': L.rel(fbx), 'source_blend': L.rel(blend), 'build': 'Unclaimed/tools/bl.sh ../../Corpses/tools/%s %s' % (SCRIPT, name),
           'dimensions_m': st['dimensions_m'], 'bounds_min_m': st['bounds_min_m'], 'bounds_max_m': st['bounds_max_m'], 'lod0_triangles': st['triangles'],
           'textures': tex, 'materials': [k['name'] for k in kit], 'kit_materials': kit, 'collision_hulls': 0,
           'material_exception': 'unique BC/N/ORM bakes private to this asset (not a row of ART_STANDARD.md section 2): remains are one-off set pieces',
           'pivot': 'bbox centre in X/Y, lowest point at z = 0; in Blender +X is screen right and +Y screen up (north) for a yaw_from_sprite row',
           'families': families, 'dresses': dresses, 'third_party': list(third_party), 'known_weaknesses': weaknesses}
    if stats:
        man['bake_stats'] = stats
    if extra:
        man.update(extra)
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', asset); return man


# ================================================================================================ the people
PEOPLE_TP = ['MakeHuman CC0 base mesh, skin, eyes and hair (Art/Characters/ThirdParty/MakeHuman), through the source character', 'park_dirt (render ground)']
W_PERSON = ('The body is the posed, frozen %s of PhotorealPass/Unclaimed (no ragdoll, clothes not draped by simulation, eyes open), baked again onto one %d px atlas together with the new blood and the gashes, '
            'so face, hands and hair are softer than on the living character and the hair is a hard cut-out. The gashes are relief on the surface (swollen lips, a groove of muscle), not cuts into the body: no bone, no organs. '
            'The pool, the drops and the mist are a flat alpha-tested card 6 mm above the ground: a hard-edged cut-out without soaking into the ground, and it does not follow uneven ground. Static.')
HUMANS = {
    # head = where the head points in the sprite, degrees anticlockwise from screen right
    'Corpse_Merchant': dict(src=('corpse_merchant', 'Corpse_Merchant'), who='merchant', fams=['corpse_merchant', '345 people/merchant/death-'], head=205, seed=345,
                            dresses='the dead merchant (blue) on his back, drenched, slashed across chest and belly, in a pool of his blood with thrown drops round it'),
    'Corpse_Merchant_Green': dict(src=('corpse_merchant', 'Corpse_Merchant'), who='merchant', fams=['corpse_merchant', '385 people/merchant/green/death-'], head=335, seed=385, swap=('Outfit', 'T_Corpse_Merchant_PR_Outfit_Green_BC.png'),
                                  dresses='the dead merchant in green on his back, drenched, slashed, in a pool of his blood'),
    'Corpse_Girl': dict(src=('corpse_girl', 'Corpse_Girl'), who='girl', fams=['corpse_girl', '335 people/girl/death-'], head=150, seed=335, pool=0.8,
                        dresses='the dead village girl on her back, dress and face drenched, in a pool of her blood'),
    'Corpse_Maiden': dict(src=('corpse_maiden', 'Corpse_Maiden'), who='maiden', fams=['corpse_maiden', '245 people/maiden/red/death-'], head=205, seed=245, drench=0.35,
                          dresses='the dead woman in the crimson dress on her back, drenched and slashed, in a pool of her blood'),
    'Corpse_Mother': dict(src=('corpse_mom', 'Corpse_Mother'), who='Mother', fams=['corpse_mom', '355 people/mom/death-'], head=205, seed=355, drench=0.35,
                          dresses='the dead mother of the burnt house on her back, drenched and slashed, in a pool of her blood'),
    'Corpse_Peasant': dict(src=('corpse_peasant', 'Corpse_Peasant'), who='peasant', fams=['corpse_peasant', '415 people/peasant2/death-'], head=120, seed=415, pool=1.15, pole=True,
                           dresses='the dead peasant on his back, tunic and face drenched, slashed, his scythe pole lying beside him in the wide pool'),
    'Corpse_Soldier': dict(src=('corpse_soldier', 'Corpse_Soldier'), who='soldier (Milder)', fams=['corpse_soldier', '405 people/soldier/death-'], head=215, seed=405,
                           dresses='the dead soldier on his back, jerkin and mail drenched, slashed, in a pool of his blood'),
    'Dink_Dead': dict(src=('dink_dead', 'Dink_Dead'), who='Dink', fams=['dink_dead', '436 dink/die/ds-x3-'], head=320, seed=436, amount=0.8, pool=0.9, shift=(0.25, 0.2),
                      dresses='Dink lying dead on his back (the cutscene picture), blood over chest and face, the pool spreading from under him'),
}


# card width of the 1997 picture in the world, metres (ImportData/placements.json `card.width_m`, 14 Nov 2026)
FOOT = {'Corpse_Knight': 2.02, 'Corpse_Merchant': 1.85, 'Corpse_Merchant_Green': 1.85, 'Corpse_Girl': 1.45, 'Corpse_Maiden': 1.57, 'Corpse_Soldier': 1.85, 'Corpse_Peasant': 2.85, 'Dink_Dead': 2.60}


def fit_scale(obs, foot_m, margin=0.10):
    """uniform scale (never above 1) that brings the bodies' ground extent inside the sprite footprint, leaving `margin` for the pool's edge"""
    P = np.vstack([L.co(o) for o in obs]); ext = float(max(np.ptp(P[:, 0]), np.ptp(P[:, 1])))
    s = min(1.0, (foot_m - margin) / ext); print('FIT body extent %.2f m -> scale %.3f for a %.2f m footprint' % (ext, s, foot_m)); return s


def person_pool(P, c, seed, pool=1.0, shift=(0.0, 0.0), reach=0.42, grow=0.11, extra_pts=None, fit_m=None):
    """the blood sheet under a body: it hugs the body's outline, swells under the torso and throws drops outwards"""
    low = P[P[:, 2] < 0.30]; foot = low[::9, :2]
    if extra_pts is not None:
        foot = np.vstack([foot, extra_pts])
    rng = np.random.default_rng(seed); cc = (c[0] + shift[0], c[1] + shift[1]); rot = rng.uniform(0, math.pi)
    if fit_m:
        # the 1997 picture's footprint (card width of placements.json): the pool hugs the body and the whole of it, drops included, stays inside that width
        half = fit_m / 2.0; grow = 0.045; reach = 0.07; r = np.hypot(foot[:, 0] - cc[0], foot[:, 1] - cc[1]); keep = r < half - grow - 0.01; foot = foot[keep]
        a = min(0.62 * pool, half * 0.62); b = min(0.42 * pool, half * 0.42)
        pools = [(cc[0], cc[1], a, b, rot, [(rng.uniform(0, 6.3), 0.3, 0.16 * a / 0.62), (rng.uniform(0, 6.3), 0.2, 0.2 * a / 0.62)])]
        size = round(fit_m + 0.35, 1)
        sheet = GS.blood_sheet(2048, size, seed, pools=pools, foot=foot, grow=grow, n_drops=90, reach=reach, casts=3, mist=350, drop_r=(0.003, 0.016), centre=cc)
        cov = sheet['cover'] > 0.5; ex = max(np.ptp(np.nonzero(cov.any(0))[0]), np.ptp(np.nonzero(cov.any(1))[0])) / 2048.0 * size
        print('FOOTPRINT pool incl. drops %.2f m, sprite card %.2f m' % (ex, fit_m)); sheet['extent_m'] = float(ex); return sheet, size
    ext = float(np.abs(foot).max()) + grow + reach + 0.12; size = round(2 * ext + 0.049, 1)
    pools = [(cc[0], cc[1], 0.62 * pool, 0.42 * pool, rot, [(rng.uniform(0, 6.3), 0.35, 0.22 * pool), (rng.uniform(0, 6.3), 0.2, 0.3 * pool), (rng.uniform(0, 6.3), 0.25, 0.16 * pool)])]
    return GS.blood_sheet(2048, size, seed, pools=pools, foot=foot, grow=grow * pool, n_drops=170, reach=reach, casts=6, mist=700, centre=cc), size


def soak_and_gash(body, c, axis, seed, amount=1.0, n_gash=3, drench=0.0):
    """drench every material of the body and lay slashes open on it; returns (hi gashes, lo gashes)"""
    rng = np.random.default_rng(seed); cen = [(np.array([c[0] + axis[0] * t, c[1] + axis[1] * t, 0.15]), r) for t, r in ((0.0, 0.44), (0.30, 0.38), (-0.30, 0.36), (0.62, 0.24), (-0.62, 0.30), (-0.9, 0.24))]
    for m in body.data.materials:
        ensure_principled(m)
        if any(n.type == 'TEX_IMAGE' and n.image and n.image.name.upper().split('.')[0].endswith('_BC') for n in m.node_tree.nodes):
            bloody(m, cen, ground=0.15, amount=amount, spatter=0.60, drench=drench)
    bvh = bvh_of(body); wm = m_flesh('wound', k=4.0); hi = []; lo = []; perp = np.array([-axis[1], axis[0]])
    for i in range(n_gash):
        t = (-0.05, 0.28, -0.26)[i % 3] + rng.normal(0, 0.03); q = np.array(c[:2]) + axis * t + perp * rng.normal(0, 0.04); ang = math.atan2(perp[1], perp[0]) + rng.uniform(-0.7, 0.7)
        ln = rng.uniform(0.15, 0.24); wd = rng.uniform(0.028, 0.045); h = gash(bvh, q, ang, ln, wd, seed + i, True); l_ = gash(bvh, q, ang, ln, wd, seed + i, False)
        if h is None or l_ is None:
            continue
        L.assign(h, wm); unwrap(l_, top=True); hi.append(h); lo.append(l_)
    return hi, lo


def body_lo(body, extra, name, big=()):
    """the game mesh of a body: the same triangles with every island repacked onto one atlas; islands of the materials named in `big`
    (hair, eyes) get a larger share"""
    lo = L.dup(body, name); lo.hide_render = False; parts = [lo] + list(extra); lo = L.join(parts, name) if len(parts) > 1 else lo
    L.pack_uv(lo, margin=0.003, average=True)
    if big:
        idx = {i for i, m in enumerate(lo.data.materials) if m and any(b in m.name for b in big)}; uv = lo.data.uv_layers.active.data
        for p in lo.data.polygons:
            if p.material_index in idx:
                for li in p.loop_indices:
                    uv[li].uv = uv[li].uv * 1.7
        L.pack_uv(lo, margin=0.003, average=False)
    lo.data.materials.clear(); return lo


def person(name, prev=False):
    v = HUMANS[name]; asset = 'SM_%s_PR' % name; d = os.path.join(L.UNC, *v['src']); outdir = os.path.join(CORP, name)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(d, 'SM_%s_PR.blend' % v['src'][1])); sc = bpy.context.scene; L.use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    relink([d] + [os.path.join(L.PP, 'Characters', b, 'Textures') for b in ('Mother', 'Milder', 'Dink')])
    body = bpy.data.objects['SM_%s_PR' % v['src'][1]]; drop_everything_but([body]); body.hide_render = False; body.hide_viewport = False
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)
    if v.get('swap'):
        m = next(m for m in body.data.materials if v['swap'][0] in m.name); n = next(n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.upper().split('.')[0].endswith('_BC'))
        im = bpy.data.images.load(os.path.join(d, v['swap'][1])); im.colorspace_settings.name = 'sRGB'; n.image = im
    # turn the body the way the sprite shows it: head towards `head`
    P = L.co(body); c0 = P.mean(0); hair = {i for i, m in enumerate(body.data.materials) if m and ('Hair' in m.name or 'Eyes' in m.name)}
    hv = sorted({vi for p in body.data.polygons if p.material_index in hair for vi in p.vertices}); hd = P[hv].mean(0) - c0
    spin_z([body], mesh_dir(v['head']) - math.atan2(hd[1], hd[0]), pivot=c0[:2]); P = L.co(body); P[:, :2] -= (P[:, :2].min(0) + P[:, :2].max(0)) / 2; P[:, 2] -= P[:, 2].min(); L.set_co(body, P)
    c = P.mean(0); a = mesh_dir(v['head']); axis = np.array([math.cos(a), math.sin(a)])
    hi_g, lo_g = soak_and_gash(body, c, axis, v['seed'], amount=v.get('amount', 1.0), drench=v.get('drench', 0.0)); hi = [body] + hi_g; extra_lo = list(lo_g); extra_pts = None
    if v.get('pole'):                               # sprite 415: the peasant's long-handled sickle lies along his side in the blood
        side = np.array([-axis[1], axis[0]]) * (1 if axis[0] < 0 else -1)          # the side towards the camera (-Y)
        p0 = c[:2] + axis * 0.95 + side * 0.42; p1 = c[:2] - axis * 1.05 + side * 0.50; wood = m_pole()
        for dense in (True, False):
            n = 40 if dense else 6; pts = np.array([[*(p0 + (p1 - p0) * t), 0.022 + 0.004 * math.sin(t * 9)] for t in np.linspace(0, 1, n)]); sh = L.tube('pole_' + ('hi' if dense else 'lo'), pts, 0.017, sides=14 if dense else 6)
            m2 = 24 if dense else 7; th = np.linspace(0, 2.3, m2); r = 0.24; cen = p0 + axis * 0.02 - side * r
            bl = np.array([[*(cen + r * (math.cos(t) * side + math.sin(t) * axis)), 0.02] for t in th]); blade = L.tube('sickle_' + ('hi' if dense else 'lo'), bl, np.linspace(0.016, 0.003, m2), sides=8 if dense else 4)
            Pb = L.co(blade); Pb[:, 2] = 0.012 + (Pb[:, 2] - 0.012) * 0.3; L.set_co(blade, Pb)
            if dense:
                L.assign(sh, wood); L.assign(blade, m_iron()); hi += [sh, blade]
            else:
                unwrap(sh); unwrap(blade); extra_lo += [sh, blade]
        extra_pts = np.array([p0 + (p1 - p0) * t for t in np.linspace(0, 1, 30)])
        bloody(wood, [(np.array([c[0], c[1], 0.0]), 0.9)], ground=0.03, amount=0.9, spatter=0.45)
    if prev:
        for o in extra_lo:
            o.hide_render = True
        preview(hi, name, [dict(az=0, el=52, fill=1.0, lens=60), dict(az=-35, el=24, fill=1.6, lens=70)] + ([dict(az=-20, el=45, lens=70, center=tuple(L.co(hi_g[0]).mean(0)), radius=0.22, fill=1.0)] if hi_g else [])); return
    lo = body_lo(body, extra_lo, asset + '_lo', big=('Hair', 'Eyes'))
    sheet, size = person_pool(L.co(body), c, v['seed'], pool=v.get('pool', 1.0), shift=v.get('shift', (0.0, 0.0)), extra_pts=extra_pts)
    cfiles = write_sheet(sheet, outdir, name + '_Pool'); card = sheet_card(name + '_Pool', size, cfiles)
    finish(asset, 'prop', outdir, v['fams'], v['dresses'], W_PERSON % (v['who'], 2048), body=lo, hi=hi, card=(card, cfiles), px=2048, ss=2, alpha=True, extrude=0.005, maxdist=0.02, third_party=PEOPLE_TP,
           extra={'derived_from': 'Unclaimed/%s/%s (SM_%s_PR), turned to the sprite, soaked, gashed and baked again' % (v['src'][0], v['src'][1], v['src'][1]), 'gore_in_mesh': 'blood over the whole body (wet), slashes, pool with thrown drops and mist (no companion decal)',
                  'pool_card_m': size})


# ------------------------------------------------------------------------------------------------ people, second version (review of PR #103)
# Posed from the rigged characters as dead weight, opened as the 1997 pictures show them, bloodied round the wounds only (the
# clothes keep their colours), and scaled so body and pool stay inside the picture's footprint (FOOT).
ARM_KEYS = ('upperarm', 'lowerarm', 'hand', 'index', 'middle', 'thumb', 'pinky', 'ring'); LEG_KEYS = ('thigh', 'calf', 'foot', 'ball')
CHAR_TEX = ('Mother', 'Milder', 'Dink')
# arms / legs: ((upper x, upper z), (lower x, lower z)) for the left and the right limb in the standing rig, x = away from the body, z = up
# open: (along the body from its middle, across, half length, half width, turn against the body axis, what shows: 'ribs', 'gut' or both)
# sever: (bone name prefixes, side, moved along the body, moved across, turned)
PEOPLE = {
    'Corpse_Girl': dict(rig=('npc_girl', 'Girl', 'SK_Girl_PR'), who='girl', fams=['corpse_girl', '335 people/girl/death-'], head=150, seed=335, turn=-40, flat=(0.09, 0.3),
                        arms=(((0.95, -0.3), (0.2, 0.98)), ((0.55, -0.83), (0.85, -0.5))), legs=(((0.30, -0.95), (-0.05, -1.0)), ((0.12, -0.99), (0.3, -0.95))),
                        open=[(0.02, 0.0, 0.17, 0.085, 0.15, 'ribs gut')], sever=[(('calf', 'foot', 'ball'), 'l', -0.10, 0.16, 0.7), (('lowerarm', 'hand'), 'r', 0.05, -0.14, -0.9)],
                        dresses='the village girl torn open: belly and chest laid open over ribs and entrails, a leg and a forearm torn off beside her, in her blood'),
    'Corpse_Maiden': dict(rig=('npc_maiden_red', 'Maiden_Red', 'SK_Maiden_Red_PR'), who='woman in the crimson dress', fams=['corpse_maiden', '245 people/maiden/red/death-'], head=205, seed=245, turn=35, skirt=0.3,
                          arms=(((0.8, -0.6), (0.9, 0.4)), ((0.9, -0.42), (0.35, -0.93))), legs=(((0.14, -0.99), (0.0, -1.0)), ((0.26, -0.96), (-0.1, -1.0))),
                          open=[(0.10, 0.0, 0.24, 0.10, -0.1, 'ribs gut')], sever=[],
                          dresses='the woman in the crimson dress torn open from throat to belly, ribs bare, entrails pulled out onto the ground, in her blood'),
    'Corpse_Merchant': dict(rig=('npc_merchant_blue', 'Merchant', 'SK_Merchant_PR'), who='merchant', fams=['corpse_merchant', '345 people/merchant/death-'], head=205, seed=345, turn=-30,
                            arms=(((0.9, -0.42), (0.6, 0.8)), ((0.6, -0.8), (0.9, -0.4))), legs=(((0.2, -0.98), (0.02, -1.0)), ((0.34, -0.94), (-0.12, -1.0))),
                            open=[(0.20, 0.0, 0.20, 0.040, 0.7, 'ribs'), (-0.02, 0.02, 0.17, 0.050, -0.55, 'gut')], sever=[(('lowerarm', 'hand'), 'l', 0.12, 0.20, 1.1)],
                            dresses='the merchant (blue) hacked down: the chest split to the ribs, the belly cut open with entrails out, a forearm struck off, in his blood'),
    'Corpse_Merchant_Green': dict(rig=('npc_merchant_blue', 'Merchant', 'SK_Merchant_PR'), who='merchant', fams=['corpse_merchant', '385 people/merchant/green/death-'], head=335, seed=385, turn=40, swap=('Outfit', 'T_Merchant_PR_Outfit_Green_BC.png'),
                                  arms=(((0.7, -0.7), (0.95, -0.3)), ((0.95, -0.3), (0.3, 0.95))), legs=(((0.36, -0.93), (-0.15, -1.0)), ((0.16, -0.99), (0.05, -1.0))),
                                  open=[(0.0, 0.0, 0.21, 0.055, 1.25, 'gut'), (0.24, -0.03, 0.15, 0.035, -0.5, 'ribs')], sever=[],
                                  dresses='the merchant in green hacked down: the belly cut across with entrails out, the shoulder and chest split to the ribs, in his blood'),
    'Corpse_Peasant': dict(rig=('npc_peasant', 'Peasant', 'SK_Peasant_PR'), who='peasant', fams=['corpse_peasant', '415 people/peasant2/death-'], head=120, seed=415, turn=-35, pole=True, drop_tool=True,
                           arms=(((0.6, -0.8), (0.3, 0.95)), ((0.95, -0.3), (0.7, -0.7))), legs=(((0.18, -0.98), (0.0, -1.0)), ((0.30, -0.95), (-0.1, -1.0))),
                           open=[(0.18, 0.0, 0.22, 0.045, -0.75, 'ribs'), (-0.05, 0.0, 0.16, 0.05, 0.6, 'gut')], sever=[],
                           dresses='the peasant hacked down: the chest split to the ribs, the belly cut open, his long-handled sickle beside him, in his blood'),
    'Corpse_Soldier': dict(rig=('npc_soldier', 'Soldier', 'SK_Soldier_PR'), who='soldier (Milder)', fams=['corpse_soldier', '405 people/soldier/death-'], head=215, seed=405, turn=30,
                           arms=(((0.9, -0.42), (0.95, 0.3)), ((0.7, -0.7), (0.5, -0.87))), legs=(((0.22, -0.97), (0.0, -1.0)), ((0.34, -0.94), (-0.14, -1.0))),
                           open=[(0.0, 0.0, 0.20, 0.055, 0.9, 'gut'), (0.22, 0.02, 0.16, 0.035, -0.4, 'ribs')], sever=[],
                           dresses='the soldier hacked through jerkin and mail: the belly cut across with entrails out, the chest split to the ribs, in his blood'),
}


def limb_weight(W, keys, side):
    m = np.zeros(len(next(iter(W.values()))))
    for n, w in W.items():
        if n.endswith('_' + side) and any(n.startswith(k) for k in keys):
            m += w
    return np.clip(m, 0, 1)


def boundary_centre(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data); pts = [v.co[:] for e in bm.edges if e.is_boundary for v in e.verts]; bm.free()
    return np.array(pts).mean(0) if pts else None


def person2(name, prev=False):
    v = PEOPLE[name]; asset = 'SM_%s_PR' % name; outdir = os.path.join(CORP, name); foot_m = FOOT[name]
    arm, d = open_src(v['rig'][:2], v['rig'][2] + '.blend'); relink([d] + [os.path.join(L.PP, 'Characters', b, 'Textures') for b in CHAR_TEX]); src = bpy.data.objects[v['rig'][2] + '_LOD0']
    if v.get('drop_tool'):                           # a long tool skinned to a hand (the peasant's scythe) would stand in the air: his sickle is laid beside him instead
        lab, k = islands(src); P0 = L.co(src); names = [g.name for g in src.vertex_groups]; hands = [names.index(n) for n in ('hand_l', 'hand_r') if n in names]
        hw = np.array([max([g.weight for g in vx.groups if g.group in hands] or [0.0]) for vx in src.data.vertices]); tool = np.zeros(len(P0), bool)
        for i in range(k):
            m = lab == i
            if hw[m].mean() > 0.5 and np.ptp(P0[m], axis=0).max() > 0.6:
                tool |= m
        if tool.any():
            bpy.data.objects.remove(split_verts(src, tool, 'tool_junk'))
    # ---- dead weight: arms and legs in the plane of the back so they lie on the ground, bent at elbow and knee, the head rolled over
    for side, (au, al), (lu, ll) in (('l', v['arms'][0], v['legs'][0]), ('r', v['arms'][1], v['legs'][1])):
        sx = 1.0 if bone_pos(arm, 'upperarm_' + side)[0] > 0 else -1.0
        for b, (x, z) in (('upperarm_', au), ('lowerarm_', al), ('thigh_', lu), ('calf_', ll)):
            aim(arm, b + side, (sx * x, 0.0, z))
    world_rot(arm, 'head', 'Z', v.get('turn', 30)); world_rot(arm, 'neck_01', 'Y', v.get('turn', 30) * 0.3)
    body, W = posed_copy(src, name.lower()); drop_everything_but([body]); body.hide_render = False; body.hide_viewport = False
    for w in list(bpy.data.worlds):
        bpy.data.worlds.remove(w)
    if v.get('swap'):
        m = next(m for m in body.data.materials if v['swap'][0] in m.name); n = next(n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.upper().split('.')[0].endswith('_BC'))
        im = bpy.data.images.load(os.path.join(d, v['swap'][1])); im.colorspace_settings.name = 'sRGB'; n.image = im
    lay_down(body, 0.0); P = L.co(body); c0 = P.mean(0); hd = P[W['head'] > 0.5].mean(0) - c0
    spin_z([body], mesh_dir(v['head']) - math.atan2(hd[1], hd[0]), pivot=c0[:2]); P = L.co(body); P[:, :2] -= (P[:, :2].min(0) + P[:, :2].max(0)) / 2; P[:, 2] -= P[:, 2].min()
    torso = (W['spine_02'] + W['spine_03'] + W['pelvis']) > 0.5; tc = P[torso].mean(0)
    if v.get('skirt'):                               # a wide skirt would hold the body off the ground: fold it towards the plane of the body, then rest the back on the ground
        k_ = v['skirt']; lg = np.clip(limb_weight(W, LEG_KEYS, 'l') + limb_weight(W, LEG_KEYS, 'r') + W['pelvis'], 0, 1); zm = float(np.median(P[torso][:, 2])); P[:, 2] = P[:, 2] - lg * (P[:, 2] - zm) * (1 - k_)
        P[:, 2] -= np.percentile(P[torso][:, 2], 2); tc = P[torso].mean(0)
    for keys in (ARM_KEYS, LEG_KEYS):                # each limb sinks to the ground towards its end
        for side in 'lr':
            m = limb_weight(W, keys, side); sel = m > 0.5
            if sel.sum() < 10:
                continue
            dist = np.linalg.norm(P[:, :2] - tc[:2], axis=1); d0 = dist[sel].min(); t_ = np.clip((dist - d0) / max(dist[sel].max() - d0, 1e-6), 0, 1)
            drop = P[sel & (t_ > 0.7)][:, 2].min() - 0.004; P[:, 2] -= m * t_ * drop
    if v.get('flat'):                                # a skirt standing out round the legs settles flat
        zc, k_ = v['flat']; lg = np.clip(limb_weight(W, LEG_KEYS, 'l') + limb_weight(W, LEG_KEYS, 'r') + W['pelvis'], 0, 1); z = P[:, 2]; P[:, 2] = np.where(z > zc, z - lg * (z - zc) * (1 - k_), z)
    P[:, 2] = np.maximum(P[:, 2], 0.002)
    ext = float(max(np.ptp(P[:, 0]), np.ptp(P[:, 1]))); s = min(1.0, (foot_m - 0.10) / ext); print('FIT %s body extent %.2f m -> scale %.3f for a %.2f m footprint' % (name, ext, s, foot_m)); P *= s; L.set_co(body, P)
    c = P[torso].mean(0); a = mesh_dir(v['head']); axis = np.array([math.cos(a), math.sin(a)]); perp = np.array([-axis[1], axis[0]]); rng = np.random.default_rng(v['seed'])
    flesh = m_flesh('flesh_' + name, k=3.0); bone = m_bone('bone_' + name); gut = m_gut('gut_' + name); hi = [body]; lo_x = []; wounds = []

    def both(fn, mat_):
        h = fn(True); l_ = fn(False)
        for o in (h if isinstance(h, list) else [h]):
            L.assign(o, mat_); hi.append(o)
        for o in (l_ if isinstance(l_, list) else [l_]):
            unwrap(o); lo_x.append(o)
    # ---- severed parts: struck off, thrown a little way, a stump of raw flesh and bone at both ends
    parts = []; lab = np.zeros(len(P), np.int32)
    for k_, (keys, side, da, dp, yaw) in enumerate(v.get('sever', ())):
        lab[limb_weight(W, keys, side) > 0.5] = k_ + 1
    at = body.data.attributes.new('dink_sever', 'INT', 'POINT'); at.data.foreach_set('value', lab)       # the label rides through the splits (vertex order changes)
    for k_, (keys, side, da, dp, yaw) in enumerate(v.get('sever', ())):
        cur = np.zeros(len(body.data.vertices), np.int32); body.data.attributes['dink_sever'].data.foreach_get('value', cur)
        part = split_verts(body, cur == k_ + 1, 'part_%s_%s' % (keys[0], side))
        cut = boundary_centre(part)
        if cut is None:
            continue
        Pp = L.co(part); pc = Pp.mean(0); cy, sy = math.cos(yaw), math.sin(yaw); R = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]); mv = np.array([*(axis * da + perp * dp), 0.0])
        Pp = (Pp - pc) @ R.T + pc + mv; Pp[:, 2] -= Pp[:, 2].min() - 0.003; L.set_co(part, Pp); cut2 = (cut - pc) @ R.T + pc + mv; cut2[2] = max(cut2[2] - (cut[2] - 0.03), 0.02)
        parts.append(part); hi.append(part)
        for j, q in enumerate((cut, cut2)):
            r = 0.034 * s; q = np.array([q[0], q[1], max(q[2], r * 0.7)]); wounds.append((q, 0.16))
            both(lambda dense, q=q, r=r, j=j: lump('stump_%d_%d_%s' % (len(parts), j, dense), q, (r * 1.2, r * 1.2, r), v['seed'] + j, 4 if dense else 2, amp=0.4, freq=3.0, flat=0.003), flesh)
            dq = (q - (pc if j == 0 else pc + mv)); dq[2] = 0; dq = dq / max(np.linalg.norm(dq), 1e-6) * (-1 if j == 0 else 1)       # out of the stump
            both(lambda dense, q=q, dq=dq, j=j: L.tube('stumpbone_%d_%d_%s' % (len(parts), j, dense), np.array([q - dq * 0.02, q + dq * 0.035]), 0.010 * s, sides=10 if dense else 5), bone)
    # ---- the body opened: the front cut away over a ragged patch, the edge turned in as raw flesh, and what lies inside
    bvh = bvh_of(body); body.data.materials.append(flesh); slot = len(body.data.materials) - 1
    for i, (ta, tp, ha, hb, turn, inside) in enumerate(v.get('open', ())):
        ha *= s; hb *= s; q = c[:2] + axis * ta * s + perp * tp * s; ang = a + turn; ca, sa_ = math.cos(ang), math.sin(ang); top = drop_on(bvh, q[0], q[1])
        if top is None:
            continue
        ztop = float(top[0][2]); zin = max(ztop * 0.38, 0.03 * s); seedi = v['seed'] + 10 * i

        def inside_patch(C, q=q, ca=ca, sa_=sa_, ha=ha, hb=hb, ztop=ztop, seedi=seedi):
            dx = C[:, 0] - q[0]; dy = C[:, 1] - q[1]; u = (dx * ca + dy * sa_) / ha; w_ = (-dx * sa_ + dy * ca) / hb
            rag = 1.0 + 0.28 * L.fbm(C * 38.0, seedi, 1.0, 3)
            return (u * u + w_ * w_ < rag * rag) & (C[:, 2] > ztop * 0.45)
        delete_faces(body, inside_patch); wounds.append((np.array([q[0], q[1], ztop]), max(ha, hb) + 0.10))
        both(lambda dense, q=q, ha=ha, hb=hb, ang=ang, zin=zin, seedi=seedi: lump('cavity_%d_%s' % (i, dense), (q[0], q[1], zin * 0.6), (ha * 1.15, hb * 1.25, zin * 0.9), seedi, 4 if dense else 2, amp=0.30, freq=2.6, rot=ang, flat=0.004), flesh)
        d_ = np.array([ca, sa_]); p_ = np.array([-sa_, ca])
        if 'ribs' in inside:                          # ribs across the opening, some snapped and standing up
            def ribs(dense, q=q, ha=ha, hb=hb, d_=d_, p_=p_, ztop=ztop, seedi=seedi):
                out = []; n = max(3, int(ha * 2 / (0.045 * s)))
                for r_ in range(n):
                    u = -0.8 + 1.6 * r_ / max(n - 1, 1); snapped = L._hash(r_, seedi, 1, 7) > 0.55; m_ = 12 if dense else 5; half = hb * (1.25 if not snapped else 0.75)
                    ws = np.linspace(-half, half * (1.0 if not snapped else 0.25), m_); base = q + d_ * u * ha
                    pts = np.array([[*(base + p_ * w_ + d_ * 0.012 * math.sin(w_ * 30 + r_)), ztop - 0.018 * s - 0.03 * s * (w_ / max(half, 1e-6)) ** 2 + (0.035 * s * (w_ + half) / (2 * half) if snapped else 0.0)] for w_ in ws])
                    out.append(L.tube('rib_%d_%d_%s' % (i, r_, dense), pts, np.linspace(0.0075, 0.0055, m_) * s, sides=8 if dense else 4))
                return out
            both(ribs, bone)
        if 'gut' in inside:                           # entrails pulled out over the side onto the ground
            def guts(dense, q=q, ha=ha, hb=hb, d_=d_, p_=p_, zin=zin, ztop=ztop, seedi=seedi):
                out = []; side_ = p_ if p_[1] < 0 else -p_                                   # towards the camera
                for j in range(4):
                    m_ = 70 if dense else 16; u = np.linspace(0, 1, m_); ph = seedi * 0.7 + j * 2.1; reach = (0.26 + 0.07 * j) * s + hb
                    st = q + d_ * (j - 1) * ha * 0.45; path = st[None, :] + np.outer(u * reach, side_) + np.outer(np.sin(u * 13.0 + ph) * 0.045 * s * u ** 0.5 + (j - 1) * 0.05 * s * u, d_)
                    rr = 0.0115 * s * (1 + 0.18 * np.sin(u * 50 + ph)); zz = np.maximum(ztop * 0.85 * (1 - np.clip(u * 2.4, 0, 1)) ** 2, 0.0) + rr + 0.004 * np.sin(u * 37 + ph)
                    for k_ in range(m_):                # ride over the body where it is still under the path
                        hsurf = drop_on(bvh, path[k_, 0], path[k_, 1]); zz[k_] = max(zz[k_], (float(hsurf[0][2]) + rr[k_] * 0.8) if (hsurf is not None and u[k_] > 0.12) else 0.0)
                    out.append(L.tube('gut_%d_%d_%s' % (i, j, dense), np.column_stack([path, zz]), rr, sides=12 if dense else 6))
                return out
            both(guts, gut)
    torn_rim(body, 0.016 * s, slot, seed=v['seed'])
    # ---- blood round the wounds, soaked in where the body lies in the pool, a few thrown spots: the clothes keep their colour
    for m in list(body.data.materials) + [p.data.materials[0] for p in parts if p.data.materials]:
        ensure_principled(m)
        if any(n.type == 'TEX_IMAGE' and n.image and n.image.name.upper().split('.')[0].endswith('_BC') for n in m.node_tree.nodes) and not m.get('dink_bloodied') and 'Eyes' not in m.name:
            bloody(m, wounds or [(np.array([c[0], c[1], 0.1]), 0.2)], ground=0.045 * s, amount=1.0, spatter=0.70); m['dink_bloodied'] = True
    extra_pts = None
    if v.get('pole'):
        side = perp * (1 if perp[1] < 0 else -1); p0 = c[:2] + axis * 0.80 * s + side * 0.34 * s; p1 = c[:2] - axis * 0.90 * s + side * 0.42 * s; wood = m_pole('pole_' + name)

        def pole(dense):
            n = 40 if dense else 6; pts = np.array([[*(p0 + (p1 - p0) * t_), 0.020 + 0.003 * math.sin(t_ * 9)] for t_ in np.linspace(0, 1, n)]); return L.tube('pole_%s' % dense, pts, 0.015 * s, sides=14 if dense else 6)

        def blade(dense):
            m2 = 24 if dense else 7; r = 0.21 * s; cen = p0 + axis * 0.02 - side * r; bl = np.array([[*(cen + r * (math.cos(t_) * side + math.sin(t_) * axis)), 0.012] for t_ in np.linspace(0, 2.3, m2)]); return L.tube('sickle_%s' % dense, bl, np.linspace(0.014, 0.003, m2) * s, sides=8 if dense else 4)
        both(pole, wood); both(blade, m_iron('iron_' + name)); extra_pts = np.array([p0 + (p1 - p0) * t_ for t_ in np.linspace(0, 1, 30)])
        bloody(wood, [(np.array([c[0], c[1], 0.0]), 0.6 * s)], ground=0.03, amount=0.9, spatter=0.5)
    if prev:
        for o in lo_x:
            o.hide_render = True
        preview(hi, name, [dict(az=0, el=52, fill=1.0, lens=60), dict(az=-35, el=24, fill=1.6, lens=70), dict(az=150, el=30, fill=1.6, lens=70)]); return
    lo_parts = [L.dup(p_, p_.name + '_lo') for p_ in parts]; lo = body_lo(body, lo_parts + lo_x, asset + '_lo', big=('Hair', 'Eyes'))
    allp = np.vstack([L.co(body)] + [L.co(p_) for p_ in parts]); xp = np.vstack([L.co(p_)[::7, :2] for p_ in parts] + ([extra_pts] if extra_pts is not None else [])) if (parts or extra_pts is not None) else None
    sheet, size = person_pool(allp, c, v['seed'], pool=1.0, extra_pts=xp, fit_m=foot_m); cfiles = write_sheet(sheet, outdir, name + '_Pool'); card = sheet_card(name + '_Pool', size, cfiles)
    weak = ('The body is the rigged %s of PhotorealPass/Unclaimed posed by rule (limbs aimed into the plane of the back and sunk to the ground, no cloth simulation: the clothes follow the skin weights), baked again onto one %d px atlas, so face, hands and hair are softer than on the living character and the hair is a hard cut-out. '
            'The openings are cut by a ragged ellipse and their inside is a displaced lump of muscle with plain rib rods and three loops of gut: no organs, no anatomy beyond that; severed ends are a lump and a rod of bone. '
            'Scaled by %.2f to keep body and pool inside the %.2f m footprint of the 1997 picture. The pool, the drops and the soaked fringe are a flat alpha-tested card 6 mm above the ground. Static.' % (v['who'], 2048, s, foot_m))
    finish(asset, 'prop', outdir, v['fams'], v['dresses'], weak, body=lo, hi=hi, card=(card, cfiles), px=2048, ss=2, alpha=True, extrude=0.005, maxdist=0.02, third_party=PEOPLE_TP,
           extra={'derived_from': 'Unclaimed/%s/%s (%s LOD0), posed dead, opened, bloodied and baked again' % v['rig'], 'sprite_footprint_m': foot_m, 'body_scale': round(s, 3), 'pool_extent_m': round(sheet.get('extent_m', 0.0), 2),
                  'gore_in_mesh': 'opened body with flesh rims, ribs and entrails as the picture shows, severed parts with stumps, blood round the wounds; pool card with drops and a soaked fringe (no companion decal)', 'pool_card_m': size})



def m_pole(name='pole'):
    t = L.NT(name); g = t.mapping(t.obj, scale=(3, 60, 60)); n = t.noise(8, 5, 0.6, vec=g); col = t.mix(n, (0.16, 0.085, 0.04), (0.34, 0.20, 0.10))
    t.set(base=col, rough=0.62, normal=t.bump(n, 0.3, 0.001)); return t.mat


def m_iron(name='iron_blade'):
    t = L.NT(name); n = t.noise(40, 4, 0.6); col = t.mix(n, (0.20, 0.21, 0.23), (0.42, 0.44, 0.47)); t.set(base=col, rough=t.maprange(n, 0.3, 0.7, 0.3, 0.5), metal=1.0, normal=t.bump(n, 0.2, 0.0006)); return t.mat


# ================================================================================================ the knight
def lay_down(ob, yaw=0.0, axis='X', angle=-90.0):
    """turn the standing mesh onto its back, resting on z = 0, centred"""
    ob.matrix_world = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(angle), 4, axis); L.apply_xf(ob)
    P = L.co(ob); c = (P.min(0) + P.max(0)) / 2; c[2] = P[:, 2].min(); ob.matrix_world = Matrix.Translation(tuple(-c)); L.apply_xf(ob); return ob


def islands(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table(); lab = np.full(len(bm.verts), -1); k = 0
    for v in bm.verts:
        if lab[v.index] >= 0:
            continue
        st = [v]; lab[v.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                w = e.other_vert(x)
                if lab[w.index] < 0:
                    lab[w.index] = k; st.append(w)
        k += 1
    bm.free(); return lab, k


def knight(prev=False):
    name = 'Corpse_Knight'; asset = 'SM_%s_PR' % name; outdir = os.path.join(CORP, name)
    arm, kd = open_src(('npc_knight_blue', 'Knight'), 'SK_Knight_PR.blend'); src = bpy.data.objects['SK_Knight_PR_LOD0']
    # the halberd is skinned to the right hand: its islands reach above the helmet in the rest pose
    lab, k = islands(src); P0 = L.co(src); names = [g.name for g in src.vertex_groups]; gi = names.index('hand_r'); hw = np.array([max([g.weight for g in v.groups if g.group == gi] or [0.0]) for v in src.data.vertices])
    hal = np.zeros(len(P0), bool)
    for i in range(k):
        m = lab == i
        if hw[m].mean() > 0.5 and (P0[m, 2].max() > 1.8 or np.ptp(P0[m, 2]) > 1.2):
            hal |= m
    shaft_isl = max(range(k), key=lambda i: np.ptp(P0[lab == i, 2]) if hal[lab == i].all() else -1.0); is_shaft = lab == shaft_isl
    for b, ax, deg in [('upperarm_l', 'Y', 62), ('lowerarm_l', 'Y', 25), ('upperarm_r', 'Y', -58), ('lowerarm_r', 'Y', -30), ('thigh_l', 'Y', 16), ('thigh_r', 'Y', -14), ('calf_r', 'X', 22), ('head', 'Z', 30)]:
        world_rot(arm, b, ax, deg)
    skin, W = posed_copy(src, 'knight'); drop_everything_but([skin]); mat = skin.data.materials[0]
    ensure_principled(mat); worn_steel(mat, os.path.join(kd, 'T_Knight_PR_Silver_BC.png'))      # sprite 275: grey-brown steel, not a red harness
    lay_down(skin, 0.0); P = L.co(skin); headw = W['head'] > 0.5; c0 = P[~hal].mean(0); hd = P[headw].mean(0) - c0
    spin_z([skin], mesh_dir(204) - math.atan2(hd[1], hd[0]), pivot=c0[:2]); P = L.co(skin); off = np.array([*(P[~hal][:, :2].min(0) + P[~hal][:, :2].max(0)) / 2, P[~hal][:, 2].min()]); P -= off
    ext = float(max(np.ptp(P[~hal][:, 0]), np.ptp(P[~hal][:, 1]))); s = min(1.0, (FOOT['Corpse_Knight'] - 0.10) / ext); print('FIT knight extent %.2f m -> scale %.3f' % (ext, s)); P *= s; L.set_co(skin, P)
    chest = P[(W['spine_03'] > 0.5) & ~hal].mean(0); ctop = P[(W['spine_03'] > 0.5) & ~hal][:, 2].max(); c = P[~hal].mean(0); a = mesh_dir(204); axis = np.array([math.cos(a), math.sin(a)])
    # take the halberd apart: the shaft is replaced by a snapped one standing in the chest; the head is laid flat in the blood
    head_m = hal & ~is_shaft; shaft_ax = P[is_shaft]; u, s_, vt = np.linalg.svd(shaft_ax - shaft_ax.mean(0), full_matrices=False); sa = vt[0]
    if (P[head_m].mean(0) - shaft_ax.mean(0)) @ sa < 0:
        sa = -sa
    hpart = split_verts(skin, head_m, 'halberd_head'); junk = split_verts(skin, _mask_after(is_shaft, head_m), 'old_shaft'); bpy.data.objects.remove(junk)
    Ph = L.co(hpart); hc = Ph.mean(0); u, s_, vt = np.linalg.svd(Ph - hc, full_matrices=False); nb = vt[2]                 # the blade is flat: its thin direction becomes up
    nb = nb - sa * (nb @ sa); nb /= np.linalg.norm(nb); e2 = np.cross(nb, sa); src_f = np.stack([sa, e2, nb], 1)
    side = np.array([-axis[1], axis[0]]); side = side if side[1] < 0 else -side                                               # towards the camera
    dgo = np.array([*(axis * -0.25 + side * 0.97), 0.0]); dgo /= np.linalg.norm(dgo); dst_f = np.stack([dgo, np.cross([0, 0, 1.0], dgo), [0, 0, 1.0]], 1); Rm = dst_f @ src_f.T
    tgt = np.array([*(c[:2] - axis * 0.42 + side * 0.50), 0.0]); Ph = (Ph - hc) @ Rm.T; Ph += tgt - np.array([0, 0, Ph[:, 2].min() - 0.010]); L.set_co(hpart, Ph)
    # blood where it would be: welling round the wound, run down the plates from it, soaked where the harness lies in the pool, a few thrown spots
    wound = np.array([chest[0], chest[1], ctop])
    bloody(mat, [(wound, 0.22), (np.array([c[0], c[1], 0.02]), 0.34)], ground=0.07, amount=1.0, spatter=0.69, use_link=True, runs=(wound, 0.55)); hi_g, lo_g = [], []
    hpart.data.materials.clear(); hpart.data.materials.append(mat)
    wood = m_pole('shaft'); bloody(wood, [(np.array([chest[0], chest[1], ctop]), 0.45)], ground=0.03, amount=1.0, spatter=0.55); fl = m_flesh('entry', k=2.5); hi = [skin, hpart]; lo_x = []
    lean = np.array([0.10, -0.06, 1.0]); lean /= np.linalg.norm(lean); base = np.array([chest[0], chest[1], ctop - 0.07]); stub0 = tgt - dgo * 0.20 + np.array([0, 0, 0.022]); stub1 = tgt - dgo * 0.62 + np.array([0, 0, 0.020])
    for dense in (True, False):
        n = 30 if dense else 5; t = np.linspace(0, 1, n); pts = base[None, :] + np.outer(t * 0.98, lean); rr = np.full(n, 0.0165); rr[-1] = 0.004; rr[-2] = 0.012
        if dense:
            pts[-3:, :2] += RNG.normal(0, 0.004, (3, 2))
        s1 = L.tube('shaft_up_' + str(dense), pts, rr, sides=14 if dense else 7)
        pts2 = np.array([stub0 + (stub1 - stub0) * q for q in np.linspace(0, 1, 12 if dense else 3)]); r2 = np.full(len(pts2), 0.0165); r2[-1] = 0.005; s2 = L.tube('shaft_stub_' + str(dense), pts2, r2, sides=14 if dense else 7)
        en = lump('entry_' + str(dense), (chest[0], chest[1], ctop - 0.006), (0.060, 0.050, 0.016), 9, 4 if dense else 2, amp=0.35, freq=3.0)
        if dense:
            L.assign(s1, wood); L.assign(s2, wood); L.assign(en, fl); hi += [s1, s2, en]
        else:
            for o in (s1, s2, en):
                unwrap(o)
            lo_x += [s1, s2, en]
    if prev:
        for o in lo_x:
            o.hide_render = True
        preview(hi, name, [dict(az=0, el=52, fill=1.0, lens=60), dict(az=-35, el=24, fill=1.6, lens=70)]); return
    hl = L.dup(hpart, 'head_lo'); lo = body_lo(skin, [hl] + lo_x, asset + '_lo')
    foot_x = np.vstack([np.array([tgt[:2] + dgo[:2] * q for q in np.linspace(-0.6, 0.25, 12)])])
    sheet, size = person_pool(L.co(skin), c, 275, pool=1.0, extra_pts=foot_x, fit_m=FOOT['Corpse_Knight']); cfiles = write_sheet(sheet, outdir, name + '_Pool'); card = sheet_card(name + '_Pool', size, cfiles)
    weak = ('The knight is the plate harness of Unclaimed/npc_knight_blue (silver set) with procedural wear (grime, scratches, dents as a bump): swept plates without straps or rivets and nobody inside, so there is no flesh to see at the joints; the wound is a ring of raw flesh round the shaft. '
            'The halberd head is the knight\'s own, laid flat; the shafts are plain turned poles with a tapered break, not splintered wood. The pool, drops and mist are a flat alpha-tested card 6 mm above the ground. Static.')
    finish(asset, 'prop', outdir, ['corpse_knight', '275 people/knight/red/death-'], 'the knight dead on his back in worn steel plate, lying in his blood, drops thrown round it, the snapped shaft of his halberd standing in his chest and its head lying in the blood beside him',
           weak, body=lo, hi=hi, card=(card, cfiles), px=2048, ss=2, alpha=False, third_party=('park_dirt (render ground)',),
           extra={'derived_from': 'Unclaimed/npc_knight_blue/Knight (SK_Knight_PR LOD0, silver set), posed, worn, the halberd broken, bloodied and baked again', 'sprite_footprint_m': FOOT['Corpse_Knight'], 'gore_in_mesh': 'blood welling round the wound and run down the plates, soaked underside, entry wound, pool with thrown drops and mist (no companion decal)', 'pool_card_m': size})


def _mask_after(mask, removed):
    """a per-vertex mask of the mesh after the vertices of `removed` were split away (vertex order is kept)"""
    return mask[~removed]


# ================================================================================================ sheets without a body
SHEETS = {
    # sprite 187: a splat with a wet middle; 188 / 189: thrown drops (to the left / to the right); frame 4 of both: a band of drops
    'Blood_Splat_A': dict(kind='blood', size=1.6, fams=['blood_splat', '187 effects/spurt/spurt-'], kw=dict(pools=[(0, 0, 0.30, 0.17, 0.2, [(0.3, 0.3, 0.14), (2.8, 0.25, 0.18)])], n_drops=170, reach=0.40, casts=7, mist=500), seed=1871,
                          dresses='blood thrown on the ground: a wet splat with drops and streaks round it'),
    'Blood_Splat_B': dict(kind='blood', size=1.6, fams=['blood_splat', '187 effects/spurt/spurt-'], kw=dict(pools=[(-0.1, 0, 0.22, 0.13, 1.1, [(4.0, 0.3, 0.2)]), (0.22, 0.08, 0.12, 0.08, 0.4, [])], n_drops=190, reach=0.42, casts=6, mist=500), seed=1872,
                          dresses='blood thrown on the ground: two run-together splats with drops round them'),
    'Blood_Drops_A': dict(kind='blood', size=1.6, fams=['blood_splat', '188 effects/spurt/sprtl-', '189 effects/spurt/sprtr-'], kw=dict(pools=[(0, 0, 0.07, 0.05, 0.3, [])], n_drops=230, reach=0.55, casts=9, mist=600, drop_r=(0.005, 0.034)), seed=1881,
                          dresses='blood thrown on the ground: scattered drops and cast-off lines, no pool'),
    'Blood_Drops_B': dict(kind='blood', size=1.6, fams=['blood_splat', '188 effects/spurt/sprtl-', '189 effects/spurt/sprtr-'], kw=dict(pools=[(0.05, -0.05, 0.09, 0.05, 2.0, [])], n_drops=210, reach=0.55, casts=11, mist=600, drop_r=(0.005, 0.036)), seed=1891,
                          dresses='blood thrown on the ground: scattered drops and cast-off lines, no pool'),
    'Burn_Hole_A': dict(kind='scorch', size=1.5, fams=['burn_hole_decal', '158 struct/details/damage/hole-'], kw=dict(r=0.27, spikes=20), seed=1581, dresses='a hole burnt into the ground: charred, cracked centre, burn tongues running out, ash and cinders'),
    'Burn_Hole_B': dict(kind='scorch', size=1.5, fams=['burn_hole_decal', '158 struct/details/damage/hole-'], kw=dict(r=0.25, spikes=24, aspect=1.2, rot=0.6), seed=1582, dresses='a hole burnt into the ground, slightly drawn out'),
    'Burn_Hole_C': dict(kind='scorch', size=1.5, fams=['burn_hole_decal', '158 struct/details/damage/hole-'], kw=dict(r=0.22, spikes=26, aspect=1.75, rot=-0.75, spike_len=(0.5, 1.3)), seed=1583, dresses='two burnt holes run together (picture 3)'),
}


def sheet_asset(name):
    v = SHEETS[name]; asset = 'SM_%s_PR' % name; outdir = os.path.join(CORP, name); L.reset()
    sh = GS.blood_sheet(1024, v['size'], v['seed'], **v['kw']) if v['kind'] == 'blood' else GS.scorch_sheet(1024, v['size'], v['seed'], **v['kw'])
    files = write_sheet(sh, outdir, name); card = sheet_card(name, v['size'], files, anchor=True)
    weak = ('A flat alpha-tested card 6 mm above the ground: the outline is a hard cut-out, nothing soaks into the ground or stains grass blades, and it does not follow uneven ground. '
            + ('The wet look is roughness and a thin normal relief only.' if v['kind'] == 'blood' else 'No depth: the hole is a darkened, cracked patch, not a pit.'))
    finish(asset, 'prop_small', outdir, v['fams'], v['dresses'], weak, card=(card, files), third_party=('park_dirt (render ground)',), beauty=dict(az=0, el=55, fill=1.0, lens=60), close=dict(az=-30, el=22, fill=1.8, lens=70),
           extra={'pool_card_m': v['size'], 'derived_from': 'tools/gore_sheets.py (numpy and PIL, no scan)'})


# ================================================================================================ the dragon
def dragon(prev=False):
    name = 'Dragon_Corpse'; asset = 'SM_%s_PR' % name; outdir = os.path.join(CORP, name)
    arm, _ = open_src(('dragon', 'Dragon'), 'SK_Dragon_PR.blend'); src = bpy.data.objects['SK_Dragon_PR_LOD1']
    # ---- pose: pitched forward onto its belly, one wing still up, tail arched over the back, neck along the ground, legs splayed
    for b, ax, deg in [('pelvis', 'X', 64), ('thigh_l', 'Y', -78), ('thigh_r', 'Y', 78), ('calf_l', 'Z', 25), ('calf_r', 'Z', -25),
                       ('tail_01', 'X', 38), ('tail_02', 'X', 20), ('tail_03', 'X', 26), ('tail_04', 'X', 32), ('tail_05', 'X', 40), ('tail_06', 'X', 46), ('tail_07', 'X', 40), ('tail_03', 'Z', 14),
                       ('neck_01', 'Z', -52), ('neck_02', 'X', -22), ('neck_02', 'Z', -46), ('neck_03', 'X', -24), ('neck_03', 'Z', -40), ('head', 'X', -16), ('head', 'Y', 62),
                       ('upperarm_l', 'Y', -60), ('upperarm_r', 'Y', 60)]:
        world_rot(arm, b, ax, deg)
    aim(arm, 'wing_01_l', (0.45, 0.25, 1.0))            # the left wing still stands, turned as a whole so its fan stays a fan
    J = {b: bone_pos(arm, b) for b in ('pelvis', 'spine_01', 'spine_02', 'neck_01', 'neck_02', 'head', 'wing_01_r', 'wing_01_l', 'tail_01')}; J['neck_end'] = bone_pos(arm, 'neck_01', tail=True)
    skin, W = posed_copy(src, 'hide'); drop_everything_but([skin]); mat = skin.data.materials[0]
    torso_w = W['pelvis'] + W['spine_01'] + W['spine_02']; wing_r = W['wing_01_r'] + W['wing_02_r'] + W['wing_f1_r'] + W['wing_f2_r'] + W['wing_f3_r']
    # ---- rest it on the ground: the belly line becomes z = 0 and what hangs below it is pressed flat
    P = L.co(skin); g = float(np.percentile(P[torso_w > 0.6, 2], 6)); z = P[:, 2] - g; P[:, 2] = np.where(z < 0.05, 0.05 * np.exp((z - 0.05) / 0.05 * 0.35) + 0.0, z); P[:, 2] -= P[:, 2].min(); L.set_co(skin, P)
    for k in J:
        J[k] = J[k] - np.array([0, 0, g])
    A0 = J['pelvis']; B0 = J['neck_end']; ax0 = (B0 - A0) / np.linalg.norm(B0 - A0); r0 = P - A0; al0 = r0 @ ax0; len0 = float(np.linalg.norm(B0 - A0))
    core_native = float(np.median(np.linalg.norm(r0 - np.outer(al0, ax0), axis=1)[(torso_w > 0.7) & (al0 > 0.2 * len0) & (al0 < 0.8 * len0)]))
    # ---- the right wing is torn off: only a rag of membrane with a piece of its arm is left, lying flat beside the body
    wing = split_verts(skin, wing_r > 0.5, 'wing_off'); Pw = L.co(wing); Pw -= Pw.mean(0)
    u, s_, vt = np.linalg.svd(Pw, full_matrices=False); nrm = vt[2] * (1 if vt[2][2] > 0 else -1); ax = np.cross(nrm, (0, 0, 1.0)); an = math.acos(float(np.clip(nrm[2], -1, 1)))
    Rm = np.array(Matrix.Rotation(an, 3, Vector(ax / (np.linalg.norm(ax) + 1e-9)))) if np.linalg.norm(ax) > 1e-6 else np.eye(3); Pw = Pw @ Rm.T; Pw[:, 2] = (Pw[:, 2] - Pw[:, 2].min()) * 0.5; L.set_co(wing, Pw)
    e_ = float(max(np.ptp(Pw[:, 0]), np.ptp(Pw[:, 1]))); c_ = Pw[np.argmax(Pw[:, 2])][:2] * 0.5
    delete_faces(wing, lambda C: np.linalg.norm(C[:, :2] - c_, axis=1) > e_ * (0.24 + 0.12 * L.fbm(C * 1.3, 31, 1.0, 3))); drop_small_islands(wing, 12); Pw = L.co(wing); Pw[:, :2] -= Pw[:, :2].mean(0); L.set_co(wing, Pw)
    # ---- final size: body, neck and tail about as wide as the sprite card (2.6 m)
    Pb = L.co(skin); ext = float(max(np.ptp(Pb[:, 0]), np.ptp(Pb[:, 1]))); S = 2.45 / ext; scale_all([skin, wing], S); J = {k: v * S for k, v in J.items()}; stump = J['wing_01_r']
    # ---- tear the torso open: the whole back and the right flank are gone, hide is left in rags on the left and round the hips and shoulders
    A = J['pelvis']; B = J['neck_end']; axis = (B - A) / np.linalg.norm(B - A); length = float(np.linalg.norm(B - A)); core_r = core_native * S

    def torn(C):
        r_ = C - A; al = r_ @ axis; rd = r_ - np.outer(al, axis); t = al / length; inside = (t > -0.12) & (t < 1.08) & (np.linalg.norm(rd, axis=1) < core_r * 1.9)
        up = rd[:, 2] / (core_r + 1e-9); side = rd[:, 0] / (core_r + 1e-9); n = L.fbm(C * 4.2, 11, 1.0, 4)
        open_ = (up > 0.30 + 0.5 * n) | (side < 0.10 + 0.6 * n) | (n > 0.42)
        return inside & open_ & (C[:, 2] > 0.02)
    delete_faces(skin, torn)
    nA = J['neck_02']; delete_faces(skin, lambda C: (np.linalg.norm(C - nA, axis=1) < core_r * (0.55 + 0.35 * L.fbm(C * 6.0, 23, 1.0, 3))) & (C[:, 2] > nA[2] - 0.02))      # the throat is ripped out
    drop_small_islands(skin, 10)
    side_ = np.cross(axis, (0, 0, 1.0)); side_ /= np.linalg.norm(side_); right = side_ if side_[0] < 0 else -side_; Pw = L.co(wing); ang_ = math.radians(35); c2, s2 = math.cos(ang_), math.sin(ang_)
    Pw[:, :2] = Pw[:, :2] @ np.array([[c2, s2], [-s2, c2]]); Pw[:, :2] += (A + axis * 0.15 * length + right * core_r * 3.4)[:2]; Pw[:, 2] += 0.012; L.set_co(wing, Pw)
    flesh = m_flesh(); skin.data.materials.append(flesh); wing.data.materials.append(flesh); torn_rim(skin, 0.05, 1); torn_rim(wing, 0.04, 1)
    bloody(mat, [((A + B) / 2 + np.array([0, 0, core_r * 0.5]), core_r * 3.0), (nA, core_r * 1.5), (stump, core_r * 1.6), (L.co(wing).mean(0), core_r * 1.6)], ground=0.11, amount=1.0, spatter=0.58)
    # ---- what is inside: the carcass core along the spine, heaps of torn muscle, the rib cage broken open, entrails run out on the right
    bone = m_bone(); gut = m_gut(); blood = m_blood(); hi = [skin, wing]; lo = []

    def both(fn, mat_, top=False):                   # build a gore part twice: dense for the bake, light for the game
        h = fn(True); l = fn(False)
        for o in (h if isinstance(h, list) else [h]):
            L.assign(o, mat_); hi.append(o)
        for o in (l if isinstance(l, list) else [l]):
            unwrap(o, top=top); lo.append(o)

    spine = [A - axis * 0.10 * length, A, (A + B) / 2 + np.array([0, 0, 0.02]), B, B + axis * 0.06 * length]; cz = core_r * 0.80

    def core(dense):
        n = 40 if dense else 10; pts = np.array([spine[0] + (spine[-1] - spine[0]) * t for t in np.linspace(0, 1, n)]); pts[:, 2] = np.maximum(pts[:, 2] * 0.0 + cz * 0.95, 0.0)
        rr = cz * (0.12 + 0.88 * np.sin(np.linspace(0.03, 0.97, n) * math.pi) ** 0.7); ob = L.tube('core', pts, rr, sides=48 if dense else 14)
        if dense:
            L.subsurf(ob, 1)
        Pc = L.co(ob); N = L.vnormals(ob); Pc = Pc + N * (0.035 * L.fbm(Pc * 7.0, 3, 1.0, 4))[:, None]; Pc[:, 2] = np.maximum(Pc[:, 2], 0.004); L.set_co(ob, Pc); return ob
    both(core, flesh)
    rng = np.random.default_rng(212); mid = (A + B) / 2
    heaps = []
    for i in range(15):
        t = rng.uniform(0.05, 0.95); off = rng.normal(0, 0.45); up_ = rng.uniform(0.55, 1.15); c = A + axis * length * t + right * core_r * (0.25 + off * 0.9) + np.array([0, 0, cz * up_]); r = core_r * rng.uniform(0.30, 0.55)
        heaps.append((c, (r * rng.uniform(0.9, 1.5), r, r * rng.uniform(0.55, 0.85)), 40 + i, rng.uniform(0, 3.1)))
    for i in range(7):                               # the heap slumps down the open right side onto the ground
        t = rng.uniform(0.15, 0.85); d = rng.uniform(1.0, 2.1); r = core_r * rng.uniform(0.22, 0.42); c = A + axis * length * t + right * core_r * d; c[2] = r * 0.45
        heaps.append((c, (r * 1.4, r, r * 0.6), 70 + i, rng.uniform(0, 3.1)))

    def meat(dense):                                 # one torn mass, not a heap of separate lumps: the union of the heaps under one skin
        parts = [lump('meat_%02d' % i, c, r, sd, 4 if dense else 3, amp=0.30, freq=2.2, rot=ro, flat=0.003) for i, (c, r, sd, ro) in enumerate(heaps)]; ob = L.join(parts, 'meat_hi' if dense else 'meat_lo')
        L.mod(ob, 'REMESH', mode='VOXEL', voxel_size=0.011 if dense else 0.022, adaptivity=0.0, use_smooth_shade=True); L.apply_mods(ob); L.mod(ob, 'SMOOTH', factor=0.5, iterations=4 if dense else 2); L.apply_mods(ob)
        if dense:                                    # torn fibre: ridges along the bundles, pits between them
            Pm = L.co(ob); Nm = L.vnormals(ob); Pm = Pm + Nm * (0.012 * L.fbm(Pm * np.array([9.0, 9.0, 30.0]), 5, 1.0, 4) + 0.006 * L.fbm(Pm * 55.0, 8, 1.0, 3))[:, None]; Pm[:, 2] = np.maximum(Pm[:, 2], 0.003); L.set_co(ob, Pm)
        else:
            L.mod(ob, 'DECIMATE', ratio=min(1.0, 3200 / max(1, L.tri_count(ob)))); L.apply_mods(ob); L.clean_mesh(ob)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons)); return ob
    both(meat, flesh)

    def ribs(dense):
        out = []; n = 7
        for i in range(n):
            t = 0.16 + 0.70 * i / (n - 1); base = A + axis * length * t; base[2] = cz * 1.55; rr = core_r * (0.78 + 0.30 * math.sin(t * math.pi))
            for sgn in (1, -1):
                broken = sgn < 0 or i in (2, 5); a1 = math.radians(64 if broken else 118) * (0.8 + 0.4 * L._hash(i, sgn + 2, 0, 5)); splay = (0.55 if sgn < 0 else 0.12) + 0.25 * L._hash(i, sgn + 2, 1, 5); m = 16 if dense else 6; pts = []
                for a in np.linspace(math.radians(8), a1, m):
                    rad_ = rr * (1.0 + splay * (a / a1) ** 2); p = base + (-right * sgn) * math.sin(a) * rad_ + np.array([0, 0, 1.0]) * (math.cos(a) * rad_ - rr * 0.92) + axis * 0.05 * length * (a / a1) * (L._hash(i, sgn + 2, 2, 5) - 0.3); pts.append(p)
                pts = np.array(pts); pts[:, 2] = np.maximum(pts[:, 2], 0.012); th_ = np.linspace(0.030, 0.014, m) * (core_r / 0.3) ** 0.5
                ob = L.tube('rib_%d_%d' % (i, sgn), pts, th_, sides=10 if dense else 5); out.append(ob)
        m = 30 if dense else 8; pts = np.array([A + axis * length * t for t in np.linspace(0.08, 0.92, m)]); pts[:, 2] = cz * 1.50 + 0.012 * np.sin(np.linspace(0, 16 * math.pi, m)) * (1 if dense else 0)
        out.append(L.tube('backbone', pts, 0.034 * (core_r / 0.3) ** 0.5, sides=10 if dense else 6)); return out
    both(ribs, bone)

    def guts(dense):
        out = []
        for j, (t0, reach, ph) in enumerate(((0.30, 2.6, 0.0), (0.45, 3.2, 1.7), (0.58, 2.2, 3.1))):
            m = 90 if dense else 22; u = np.linspace(0, 1, m); st = A + axis * length * t0 + right * core_r * 0.4; st[2] = cz * 0.9
            path = st[None, :] + np.outer(u * reach * core_r, right) + np.outer(np.sin(u * 9.0 + ph) * 0.34 * core_r * u ** 0.5 + (j - 1) * 0.25 * core_r * u, axis)
            path[:, 2] = np.maximum(cz * 0.9 * (1 - np.clip(u * 3.2, 0, 1)) ** 2, 0.0) + 0.036 * (core_r / 0.3) + 0.012 * np.sin(u * 40 + ph); rr = 0.036 * (core_r / 0.3) * (1 + 0.18 * np.sin(u * 55 + ph))
            out.append(L.tube('gut_%d' % j, path, rr, sides=12 if dense else 6))
        return out
    both(guts, gut)
    # ---- the pool the carcass lies in, chunks thrown clear of it, splashes beyond
    ctr = (mid + axis * 0.22 * length)[:2]; ea = 0.80 * length + core_r; eb = 2.3 * core_r; phi = math.atan2(axis[1], axis[0]); rang = math.atan2(right[1], right[0])

    def ell(th):
        d = th - phi; return ea * eb / np.sqrt((eb * np.cos(d)) ** 2 + (ea * np.sin(d)) ** 2)
    chunks = []
    for i in range(16):
        a = rng.uniform(0, 2 * math.pi); d = float(ell(np.array([a]))[0]) * rng.uniform(1.08, 1.75); r = rng.uniform(0.04, 0.085) * (1.5 if i < 4 else 1.0); chunks.append(((ctr[0] + math.cos(a) * d, ctr[1] + math.sin(a) * d, r * 0.42), (r * rng.uniform(1.0, 1.7), r, r * 0.62), 100 + i, a))
    both(lambda dense: [lump('chunk_%02d' % i, c, (r[0] * 1.25, r[1], r[2] * 0.55), sd, 4 if dense else 2, amp=0.55, freq=2.9, rot=ro, flat=0.002) for i, (c, r, sd, ro) in enumerate(chunks)], flesh)
    if prev:
        preview(hi, 'dragon_hi', [dict(az=25, el=38, fill=1.0, lens=60), dict(az=205, el=30, fill=1.0, lens=60), dict(az=-60, el=22, fill=1.25, lens=70), dict(az=100, el=40, fill=1.0, lens=60)]); return
    sk = L.dup(skin, 'hide_lo'); wg = L.dup(wing, 'wing_lo'); unwrap(sk); unwrap(wg); game = game_mesh([sk, wg] + lo, asset)
    c = L.co(game); d = -np.array([(c[:, 0].min() + c[:, 0].max()) / 2, (c[:, 1].min() + c[:, 1].max()) / 2, c[:, 2].min()]); shift_all(hi + [game], d)
    foot = np.vstack([L.co(skin)[::25, :2], L.co(wing)[::6, :2]]); cc = (float(ctr[0] + d[0]), float(ctr[1] + d[1]))
    ext = float(np.abs(foot).max()) + 0.75; size = round(2 * ext + 0.049, 1)
    sheet = GS.blood_sheet(2048, size, 212, pools=[(cc[0], cc[1], ea * 1.02, eb * 1.05, phi, [(rang, 0.45, 1.5 * core_r), (rang + 2.2, 0.16, 0.9 * core_r), (rang - 2.6, 0.2, 0.7 * core_r)])], foot=foot[np.linalg.norm(foot - np.array(cc), axis=1) < ea * 1.5], grow=0.10,
                           n_drops=260, reach=0.6, casts=9, mist=900, drop_r=(0.006, 0.04), centre=cc)
    cfiles = write_sheet(sheet, outdir, name + '_Pool'); card = sheet_card(name + '_Pool', size, cfiles)
    weak = ('The hide is the rigged dragon of Unclaimed/dragon (its baked LOD1) posed, pressed onto the ground and cut by rule, so the torn edges follow its triangles and the flesh behind them is one procedural muscle material: '
            'no anatomy beyond a rib cage, a backbone and three loops of gut; the raw mass is a displaced union of lumps, not modelled muscle groups. The wing panels are the flat opaque panels of the source. '
            'The pool, the drops and the mist are a flat alpha-tested card 6 mm above the ground. Built to the size of the sprite card (about 2.6 m), far smaller than the living dragon of the source (6.7 m). Static, as the sprite.')
    finish(asset, 'prop_large', outdir, ['dragon_corpse', '212 foes/dragon/f2-x3-', '216 foes/dragon/f2-x7-'],
           'the dragon torn open on its belly: the back and one flank gone, ribs, backbone and raw muscle laid bare, entrails run out on the ground, one wing torn off beside it, the other still raised, the tail arched over, flesh thrown around, all of it in a pool of its own blood with drops thrown round it',
           weak, body=game, hi=hi, card=(card, cfiles), px=2048, ss=2, alpha=False, extrude=0.006, maxdist=0.03, third_party=('park_dirt (render ground)',), beauty=dict(az=0, el=48, fill=1.0, lens=60), close=dict(az=-50, el=22, fill=1.5, lens=70),
           extra={'derived_from': 'Unclaimed/dragon/Dragon (SK_Dragon_PR, LOD1), posed, cut and baked again with the gore', 'gore_in_mesh': 'torn hide with flesh rims, carcass core, raw muscle mass, ribs, backbone, entrails, severed wing, thrown chunks; pool card with drops and mist (no companion decal)', 'pool_card_m': size})


if __name__ == '__main__':
    a = L.args(); groups = {'people': list(PEOPLE), 'sheets': list(SHEETS), 'all': ['Dragon_Corpse', 'Corpse_Knight'] + list(HUMANS) + list(SHEETS)}
    names = groups.get(a[0]) or a[0].split(','); prev = 'preview' in a[1:]
    for n in names:
        print('=== BUILD', n); sys.stdout.flush()
        if n == 'Dragon_Corpse':
            dragon(prev)
        elif n == 'Corpse_Knight':
            knight(prev)
        elif n in PEOPLE:
            person2(n, prev)
        elif n in HUMANS:
            person(n, prev)
        else:
            sheet_asset(n)
