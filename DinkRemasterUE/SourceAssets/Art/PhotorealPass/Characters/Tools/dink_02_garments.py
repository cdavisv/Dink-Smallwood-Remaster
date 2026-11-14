"""Stage 2: garments. Old MakeHuman-derived shirt/trouser topology gives clean armhole and crotch loops; everything is
re-cut, re-shaped and folded here. Produces *_Base (undisplaced, with UVMetric and chart ids) objects; fold functions
are applied later at two resolutions (game mesh: macro folds; bake source: macro + fine)."""
import bpy, sys, os, pickle
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/dink_bodyvol.blend'))
arm = bpy.data.objects['Armature']; B = arm.data.bones
def bh(n): return np.array(B[n].head_local)
S, E_, Wr = bh('upperarm_l'), bh('lowerarm_l'), bh('hand_l')
T, K, A, BALL = bh('thigh_l'), bh('calf_l'), bh('foot_l'), bh('ball_l')
dU = (E_ - S) / np.linalg.norm(E_ - S); dF = (Wr - E_) / np.linalg.norm(Wr - E_)
MIR = np.array([-1, 1, 1.0])
def mirx(c):
    m = np.array(c, float).copy(); m[..., 0] = np.abs(m[..., 0]); return m
def s_arm(c): return (mirx(c) - S) @ dU
def f_arm(c): return (mirx(c) - E_) @ dF


import folds
folds.setup({n: list(B[n].head_local) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})
import folds
folds.setup({n: list(B[n].head_local) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})
bv = bpy.data.objects['BodyVol']
for nm in ('OldHair', 'OldEyes', 'BrowLash', 'OldWardrobe', 'OldShirtTopo', 'OldTrousersTopo', 'Skin'): bpy.data.objects[nm].hide_render = False

def displace(o, fn, fine):
    co = co_np(o.data); o.data.update(); nr = normals_np(o.data)
    set_co(o.data, co + nr * fn(co, fine)[:, None])

def finish(base, fn, target_tris, classify, fabric, name, lipsel=None, lip=(.0025, .012), recut=()):
    """base (cut, undisplaced) -> hi (subdivided, all folds) and game mesh (decimated hi, lips).
    recut: the garment's own cut functions, moved a few millimetres into the cloth. Decimation collapses border
    vertices unevenly and leaves a torn rim (pointed tabs, notches, lips that fold over each other: the hero's
    armholes and neckline on 13 Nov 2026); cutting the decimated mesh again along the same surfaces gives every
    opening a rim that follows the cut exactly."""
    hi = dup(base, name + '_HI'); subdivide(hi, 1); displace(hi, fn, True); smooth_shade(hi)
    lo = dup(base, name); displace(lo, fn, True)
    t = tri_count(lo); d = lo.modifiers.new('dec', 'DECIMATE'); d.ratio = min(1, target_tris / t)
    if lo.vertex_groups.get('keep') is not None:
        # a constructed band (the stand collar) keeps its rings: decimation tears a band four narrow quads high to shreds
        kept = {v.index for v in lo.data.vertices if any(g.group == lo.vertex_groups['keep'].index and g.weight > .5 for g in v.groups)}
        vg = lo.vertex_groups.new(name='_dec'); vg.add([v.index for v in lo.data.vertices if v.index not in kept], 1.0, 'REPLACE')
        d.vertex_group = '_dec'; d.ratio = min(1, max(.02, (target_tris - 2 * len(kept)) / max(1, t - 2 * len(kept))))
    apply_mods(lo)
    for nm_ in ('keep', '_dec'):
        for o_ in (lo, hi):
            if o_.vertex_groups.get(nm_) is not None: o_.vertex_groups.remove(o_.vertex_groups[nm_])
    for f_ in recut: implicit_cut(lo, f_)
    if recut: tidy_rim(lo); log(name, 'rims re-cut after decimation, tris', tri_count(lo))
    smooth_shade(lo)
    for o in (hi, lo):
        chart_uv(o, classify[0], classify[1]); o['fabric'] = fabric; o['mat'] = 'outfit'
    smooth_boundary(lo)
    add_lips(lo, lip[0], lip[1], select=lipsel)
    log(name, 'hi tris', tri_count(hi), 'game tris', tri_count(lo))
    bpy.data.objects.remove(base, do_unlink=True)
    return lo, hi

# ------------------------------------------------------------------ SHIRT
sh = dup(bv, 'Shirt_Base')
implicit_cut(sh, lambda P: f_arm(P) - .135)
implicit_cut(sh, lambda P: 1.06 - P[:, 2])
implicit_cut(sh, lambda P: np.minimum(1.14 - P[:, 2], -.075 - folds.arm_h(P)))
implicit_cut(sh, lambda P: np.minimum(.080 - np.sqrt(P[:, 0] ** 2 + (P[:, 1] - .008) ** 2), P[:, 2] - 1.40))     # neck opening, higher at the nape
bm = bmesh.new(); bm.from_mesh(sh.data); bm.normal_update()
loops = boundary_loops(bm)
log('shirt loops', len(loops))
neck = max(loops, key=lambda L: sum(v.co.z for v in L) / len(L))
skin_bvh = bvh_of(bpy.data.objects['Skin'])
# The neck opening is cut where a cylinder meets the slope of the shoulders, so its edge climbs in steps at the sides;
# a collar raised from that edge ring by ring crumpled there. Fair the edge first (the loop's own curve, 16 passes).
n = len(neck)
for _ in range(16):
    P_ = [v.co.copy() for v in neck]
    for i, v in enumerate(neck): v.co = P_[i] * .5 + (P_[i - 1] + P_[(i + 1) % n]) * .25
prev = neck
# stand collar: a clean band that rises from the neck opening, low at the throat and higher at the nape, always clear of the neck skin
NRING = 4; coll_top = []
for k in range(NRING):
    fr = (k + 1) / NRING; ring = []
    for v in neck:
        az = math.atan2(v.co.x, -(v.co.y - .01)); notch = float(sstep(.0, .55, abs(az)))
        z_top = max(1.468 + .030 * notch, v.co.z + .012)
        zt = v.co.z + (z_top - v.co.z) * fr ** .85
        axis = Vector((0, .01 + .25 * (zt - 1.5), zt))
        d = Vector((v.co.x, v.co.y - axis.y, 0)); d.normalize()
        hit = skin_bvh.ray_cast(axis + d * .2, -d, .2)
        r_skin = (hit[0] - axis).length if hit[0] is not None else .06
        r0 = Vector((v.co.x, v.co.y - axis.y, 0)).length
        r = r0 + (r_skin + .0075 + .0035 * fr - r0) * min(1.0, fr * 1.6)
        ring.append(bm.verts.new(axis + d * max(r, r_skin + .0065)))
    for i in range(n):
        j = (i + 1) % n
        try: bm.faces.new((prev[j], prev[i], ring[i], ring[j]))
        except ValueError: pass
    prev = ring
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.verts.index_update()
collar_idx = [v.index for v in neck] + [v.index for v in bm.verts if v.index >= len(sh.data.vertices)]
bm.to_mesh(sh.data); bm.free()
sh.vertex_groups.new(name='keep').add(collar_idx, 1.0, 'REPLACE'); log('collar band verts kept out of the decimation', len(collar_idx))
def shirt_class(C, N):
    s = folds.arm_h(C)
    return np.where(s > 0, np.where(C[:, 0] > 0, 1, 2), np.where(C[:, 1] < 0, 3, 4))
shirt_charts = {1: ('cyl', [S, E_, Wr], (0, 0, 1), .058), 2: ('cyl', [S * MIR, E_ * MIR, Wr * MIR], (0, 0, 1), .058),
                3: ('planar', (0, 0, 1.3), (1, 0, 0), (0, .6, .8)), 4: ('planar', (0, 0, 1.3), (-1, 0, 0), (0, -.6, .8))}
shirt, shirt_hi = finish(sh, folds.shirt, 7600, (shirt_class, shirt_charts), 'linen', 'Shirt', lipsel=lambda c: c.z > 1.45, lip=(.0022, .005))   # a short lip: 12 mm turned in reached the neck
def collar_clear(o, clear=.0045):
    """After folds and decimation: every collar vertex stays at least `clear` outside the neck skin (no skin poking
    through). The push a vertex needs is shared with its neighbours before it is applied: pushing single vertices
    left a rim of small teeth."""
    c = co_np(o.data); push = np.zeros((len(c), 3)); n_moved = 0
    for i in np.nonzero((c[:, 2] > 1.452) & (np.sqrt(c[:, 0] ** 2 + (c[:, 1] - .008) ** 2) < .105))[0]:
        loc, nrm, _, dist = skin_bvh.find_nearest(Vector(c[i]), .05)
        if loc is None: continue
        sd = float((Vector(c[i]) - loc).dot(nrm))
        if sd < clear: push[i] = np.array(nrm) * (clear - sd); n_moved += 1
    bm_ = bmesh.new(); bm_.from_mesh(o.data); bm_.verts.ensure_lookup_table()
    nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm_.verts]; bm_.free()
    raw = push.copy(); need = np.linalg.norm(raw, axis=1)
    for _ in range(4):
        avg = np.array([(push[i] + push[nb].sum(0)) / (1 + len(nb)) if nb else push[i] for i, nb in enumerate(nbr)])
        push = np.where((np.linalg.norm(avg, axis=1) > need)[:, None], avg, raw)
    set_co(o.data, c + push); log('collar clearance fixed', o.name, n_moved)
collar_clear(shirt_hi); collar_clear(shirt)

# ------------------------------------------------------------------ JERKIN
jk = dup(bv, 'Jerkin_Base')
def smin(a, b, k): return -k * np.logaddexp(-a / k, -b / k)
def armhole_f(P):
    """The jerkin's armhole: folds.arm_h's two surfaces (the tube round the arm, the plane across the shoulder) with
    their meeting edge rounded (k 14 mm: a corner radius of about 3 cm). The hard minimum left a pointed corner on the shoulder cap,
    front and back."""
    m = np.abs(P * np.array([1, 0, 0])) + P * np.array([0, 1, 1]); s_, th_, d_arm = poly_params(m, [S, E_, Wr], (0, 0, -1))
    d_sp = np.sqrt(m[:, 0] ** 2 + (m[:, 1] + .02) ** 2); s0 = (m - S) @ dU
    f = smin((d_sp / .16 - d_arm / .058) * .05, s0 + .03, .014) - .004
    # ...and the cap ends 2 cm outside the shoulder joint. It reached 6 cm out over the upper arm, so it had to follow
    # the arm bone and stood up as a horn whenever the arm was raised.
    return -smin(-f, -(m[:, 0] - S[0] - .020), .010)
implicit_cut(jk, armhole_f)
def neck_f(P):
    fv = np.minimum((P[:, 2] - 1.335) * .40 - np.abs(P[:, 0]), .02 - P[:, 1])
    # round neck opening, 10.8 cm about the neck in front and at the sides, 9 cm behind: the body volume has a step
    # of 3 cm behind each shoulder at 10 to 12 cm, and an opening that ran along it tore into a slit and a hooked flap
    az = np.abs(np.arctan2(P[:, 0], -(P[:, 1] - .004)))
    rad = .108 - .018 * sstep(math.radians(100), math.radians(140), az)
    fn = np.minimum(rad - np.sqrt(P[:, 0] ** 2 + (P[:, 1] - .004) ** 2), P[:, 2] - 1.40)
    return np.maximum(fv, fn)
implicit_cut(jk, neck_f)
def hem_f(P): return (.872 + .008 * np.sin(3 * np.arctan2(P[:, 0], -P[:, 1]) + 1.0) + .006 * np.sin(7 * np.arctan2(P[:, 0], -P[:, 1]))) - P[:, 2]
implicit_cut(jk, hem_f)
RIM = .0045      # the second cut sits this far inside the first, clear of every vertex the decimation moved
TA = [(0, -.02, .8), (0, -.02, 1.7)]
def jerkin_class(C, N):
    front = (C[:, 1] + .02) < 0
    return np.where(C[:, 2] > 1.40, np.where(C[:, 1] < 0, 13, 14), np.where(front, np.where(C[:, 0] > 0, 11, 15), 12))
# The planar charts look at the cloth from in front and above (front) or behind and above (back): their v axis leans
# WITH the slope of the shoulder. Leaning the other way (as until 13 Nov 2026) folded each chart over at the shoulder
# line, the chest and the shoulder top shared texels, and the bake left dark triangles beside the armholes.
jerkin_charts = {13: ('planar', (0, 0, 1.3), (1, 0, 0), (0, .6, .8)), 14: ('planar', (0, 0, 1.3), (-1, 0, 0), (0, -.6, .8)),
                 11: ('cyl', TA, (0, -1, 0), .16), 15: ('cyl', TA, (0, -1, 0), .16), 12: ('cyl', TA, (0, 1, 0), .16)}
jerkin, jerkin_hi = finish(jk, folds.jerkin, 5200, (jerkin_class, jerkin_charts), 'leather_brown', 'Jerkin', lip=(.003, .014),
                           recut=(lambda P: armhole_f(P) + RIM, lambda P: neck_f(P) + RIM, lambda P: hem_f(P) + RIM))

def tuck_under(o, cover, covered, clear=.0025, reach=.02):
    """Keeps a garment under the one worn over it. covered(P) is the outer garment's cut field (negative where it
    covers, RIM inside its rim). The shirt's large decimated triangles came up through the jerkin at its neckline
    and armholes as pale spikes; every shirt vertex under the jerkin, and in the few millimetres outside its rim, is
    held at least `clear` below the jerkin's surface (less and less towards the open side, so no step shows)."""
    # the cover's outer surface only: its lips (the rim turned in, faces without area in the chart) face the body, and a
    # shirt vertex measured against one of those was pushed out through the leather instead of under it
    bm_ = bmesh.new(); bm_.from_mesh(cover.data); uvl_ = bm_.loops.layers.uv.verify()
    def uv_area(fc):
        q = [l[uvl_].uv for l in fc.loops]; return abs(sum(q[i].x * q[(i + 1) % len(q)].y - q[(i + 1) % len(q)].x * q[i].y for i in range(len(q)))) / 2
    outer = [fc for fc in bm_.faces if uv_area(fc) > 1e-9]
    tree = BVHTree.FromPolygons([v.co.copy() for v in bm_.verts], [[v.index for v in fc.verts] for fc in outer]); n_lip = len(bm_.faces) - len(outer); bm_.free()
    c = co_np(o.data); f = covered(c); n_moved = 0; worst = 0.0
    w = sstep(.004, -RIM, f)
    for i in np.nonzero(w > 0)[0]:
        loc, nrm, _, dist = tree.find_nearest(Vector(c[i]), reach)
        if loc is None: continue
        sd = float((Vector(c[i]) - loc).dot(nrm)); want = -clear * float(w[i])
        if sd > want: c[i] = c[i] - np.array(nrm) * (sd - want); n_moved += 1; worst = max(worst, sd - want)
    set_co(o.data, c); log('tucked under', cover.name, '(%d lip faces ignored):' % n_lip, o.name, 'vertices', n_moved, 'largest move mm', round(worst * 1000, 1))
    # the assembly reads this: how far under the cover each vertex lies (negative: covered; see dink_06_assemble 'under')
    a_ = o.data.attributes.get('cover_f') or o.data.attributes.new('cover_f', 'FLOAT', 'POINT'); a_.data.foreach_set('value', np.asarray(f, np.float32))
def jerkin_cover(P): return np.maximum.reduce([armhole_f(P), neck_f(P), hem_f(P)])
tuck_under(shirt, jerkin, jerkin_cover)

# ------------------------------------------------------------------ TROUSERS
tr = dup(bv, 'Trousers_Base')
implicit_cut(tr, lambda P: .295 - P[:, 2])
implicit_cut(tr, lambda P: P[:, 2] - .96)
implicit_cut(tr, lambda P: np.where((P[:, 2] > .9) & (np.abs(P[:, 0]) > .25), 1.0, -1.0))
def tro_class(C, N):
    return np.where(C[:, 2] < .875, np.where(C[:, 0] > 0, 21, 22), np.where((C[:, 1] + .02) < 0, 23, 24))
tro_charts = {21: ('cyl', [T, K, A], (1, 0, 0), .075), 22: ('cyl', [T * MIR, K * MIR, A * MIR], (-1, 0, 0), .075),
              23: ('cyl', TA, (0, -1, 0), .17), 24: ('cyl', TA, (0, 1, 0), .17)}
trousers, trousers_hi = finish(tr, folds.trousers, 7200, (tro_class, tro_charts), 'wool', 'Trousers', lipsel=lambda c: False)
save_blend(filepath=str(OUT / 'Dink/Work/dink_garments_a.blend'))
# quick look
for nm in ('OldHair', 'OldEyes', 'BrowLash', 'OldWardrobe', 'OldShirtTopo', 'OldTrousersTopo', 'BodyVol', 'Shirt_HI', 'Jerkin_HI', 'Trousers_HI'):
    bpy.data.objects[nm].hide_render = True
if 'hi' in args():
    for a_, b_ in ((shirt, shirt_hi), (jerkin, jerkin_hi), (trousers, trousers_hi)): a_.hide_render = True; b_.hide_render = False
for o, c in ((shirt, (.42, .5, .6)), (shirt_hi, (.42, .5, .6)), (jerkin, (.25, .14, .08)), (jerkin_hi, (.25, .14, .08)), (trousers, (.3, .33, .15)), (trousers_hi, (.3, .33, .15))):
    mt = bpy.data.materials.new('pv'); mt.use_nodes = True; mt.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*c, 1); mt.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .8
    o.data.materials.clear(); o.data.materials.append(mt)
if 'norender' in args(): sys.exit(0)
setup_render(samples=32, res=(1500, 1000))
bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = .08
shoot(OUT / 'Dink/Review/g_a_front.png', (0.7, -3.4, 1.3), (0, 0, .92), lens=60)
shoot(OUT / 'Dink/Review/g_a_back.png', (-0.9, 3.3, 1.4), (0, 0, .92), lens=60)
