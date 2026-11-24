"""Stage 4b: strand groom -> card atlas -> game hair cards, plus the strand-vs-card comparison render.
usage: blender -b -t 4 --python hair_groom.py -- <Name> [steps] [tag]
steps (comma list): atlas (re-render the card atlas), strands (re-render the strand reference), cards (re-render the cards),
                    save (write Hair into the head blend + the groom blend). Default: atlas,strands,cards,save
Reads <Name>/Work/<name>_head.blend (Skin, Eyes, old Hair with brow/lash cards); writes the new 'Hair' object back into it,
<Name>/Work/<name>_groom.blend (scalp, guide Curves with the procedural hair modifiers, cards) and T_<Name>_PR_Hair_*."""
import bpy, sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import sstep, fbm, vnoise
import hairlib as hl; import matlib
from hair_styles import STYLES
a = args(); N = a[0]; steps = (a[1] if len(a) > 1 else 'atlas,strands,cards,save').split(','); tag = a[2] if len(a) > 2 else 'h1'
n_ = N.lower(); S = STYLES[N]; rng = np.random.default_rng(S.get('seed', 1))
DIR = OUT / S.get('dir', N)      # a character in a sub-folder names it in its style ('dir': 'NPC/Seth')
head_blend = DIR / 'Work' / (n_ + '_head.blend'); TX = DIR / 'Textures'; PRE = TX / ('T_%s_PR' % N); REV = DIR / 'Review'
bpy.ops.wm.open_mainfile(filepath=str(head_blend)); D = bpy.data.objects; sc = bpy.context.scene
LM = json.load(open(str(head_blend) + '.json')); sk = D['Skin']
H = hl.Head(sk, LM, S.get('hairline', (.50, .14, -.52)))
for o_ in D:
    if o_.type == 'MESH' and o_.name not in ('Skin', 'Eyes', 'Hair') and not o_.name.startswith('Old'): o_.hide_render = True
# keep the brow / lash cards (layer 4) of the previous Hair object
old = D.get('Hair'); browlash = None
if old is not None:
    hv = np.zeros(len(old.data.vertices), np.float32)
    if old.data.attributes.get('hl') is not None: old.data.attributes['hl'].data.foreach_get('value', hv)
    bm = bmesh.new(); bm.from_mesh(old.data); bm.verts.ensure_lookup_table()
    uvl_ = bm.loops.layers.uv.active
    dead = set(v for v in bm.verts if abs(hv[v.index] - 4) > .1)
    for f in bm.faces:      # brows (left half of the band) are rebuilt from a strand groom below; the lash cards stay
        if all(l[uvl_].uv.x < .5 for l in f.loops): dead.update(f.verts)
    bmesh.ops.delete(bm, geom=list(dead), context='VERTS'); bm.to_mesh(old.data); bm.free()
    if old.data.attributes.get('hn') is not None: old.data.attributes.remove(old.data.attributes['hn'])
    old.name = 'BrowLash'; browlash = old; log('brow/lash verts kept', len(old.data.vertices))
scalp = hl.build_scalp(H, split_part=S.get('part_split', False), seed=S.get('seed', 1), fade=S.get('fade', .90))
RT = hl.Roots(H, scalp, rng); log('scalp area m2', round(float(RT.total), 4))
# ------------------------------------------------------------------ guide fields
crown = np.array([S.get('crown_x', .012), H.ctr[1] + S.get('crown_y', .05), H.top])
JS = 1.0
def guide_short(root, r, kind='hair'):
    loc, nrm = H.near(root); az, e = H.params(loc); d0 = hl.unit(loc - H.ctr); front = max(0.0, -d0[1])
    flow = loc - crown + np.array([0, 0, -.03]); flow = hl.unit(flow - nrm * (flow @ nrm)); around = np.cross(nrm, flow)
    flow = hl.unit(flow + around * 1.6 * float(sstep(.045, .0, np.linalg.norm(loc - crown))))     # the crown whorl
    around = np.cross(nrm, flow)
    flow = flow + around * S['sweep'] * (.2 + .9 * front ** 1.3)
    ang = (hl.f1(loc, S.get('tousle_scale', 38), 77 + S.get('seed', 1)) - .5) * 2 * S['tousle'] * (.5 + .5 * JS) + r.normal(0, S.get('jit', .12)) * JS
    flow = hl.unit(flow - nrm * (flow @ nrm)); around = np.cross(nrm, flow); flow = flow * math.cos(ang) + around * math.sin(ang)
    top_w = float(sstep(.80, .30, e)); back = max(0.0, d0[1]); fringe = float(sstep(.45, .70, e)) * float(sstep(1.1, .7, abs(az)))
    L = S['L_side'] + (S['L_top'] - S['L_side']) * top_w; L = L + (S['L_nape'] - L) * float(sstep(.75, 1.0, e)) * float(sstep(.2, .7, back)); L = L + (S['L_fringe'] - L) * fringe
    L *= (.8 + .4 * hl.f1(loc, 60, 91)) * r.uniform(.9, 1.08) * (1 - S.get('edge_short', 0.0) * float(sstep(.8, 1.0, e)) * (1 - fringe))
    # the fringe falls in locks of unequal length (fringe_var: the share by which a lock may be shorter or longer);
    # without it every strand over the forehead ends on one line, a bowl cut
    if S.get('fringe_var'): L *= 1 + S['fringe_var'] * fringe * (2 * hl.f1(loc, S.get('fringe_scale', 34), 123) - 1) * 1.6
    el = math.radians(S['el_side'] + (S['el_top'] - S['el_side']) * top_w + r.normal(0, S.get('el_jit', 8)))
    ml = (.0006, S['lift_tip'] * (1 + 1.2 * fringe))
    if kind == 'wisp': L *= r.uniform(.25, .5); el *= .6; ml = (.0004, .002)
    if kind == 'fly': L *= r.uniform(.6, .9); el += math.radians(r.uniform(8, 22))
    return hl.grow(H, loc + nrm * .0004, flow * math.cos(el) + nrm * math.sin(el), L, K=S.get('K', 9), gravity=S['gravity'], minlift=ml, wander=S.get('wander', .05), rng=r)
bun = None
if S['kind'] == 'bun':
    bd = hl.unit(np.array(S['bun_dir'])); ps, bn = H.near(H.ctr + bd * .25); bx = hl.unit(np.cross([0, 0, 1.0], bn)); by = np.cross(bn, bx)
    bun = dict(ps=ps, bn=bn, bx=bx, by=by, c=ps + bn * S['bun_r'][2] * .55)
def guide_bun(root, r, kind='hair'):
    loc, nrm = H.near(root); az, e = H.params(loc); d0 = hl.unit(loc - H.ctr)
    tg = bun['ps'] - loc; dist = np.linalg.norm(tg); tg = hl.unit(tg - nrm * (tg @ nrm))
    # from the centre parting the hair first runs sideways, then back
    partw = (.3 + .7 * (JS == 1.0)) * float(sstep(S.get('part_w', .014), .0, abs(loc[0]))) * float(sstep(H.ctr[1] + .02, H.ctr[1] - .02, loc[1]))
    lat = np.array([1.0 if loc[0] >= 0 else -1.0, 0, 0]); lat = hl.unit(lat - nrm * (lat @ nrm))
    d = hl.unit(tg * (1 - .5 * partw) + lat * .8 * partw + r.normal(0, S.get('jit', .05), 3))
    if kind == 'wisp':   # loose strands that escaped the bun: hang from the temples and nape
        dn = np.array([0, -.25 if d0[1] < 0 else .2, -1.0]); return hl.grow(H, loc + nrm * .0005, hl.unit(dn + nrm * .5), r.uniform(.05, .11), K=10, gravity=.9, minlift=(.0008, .006), wander=.10, rng=r, wave=(.25, 9.0, r.uniform(0, 6)))
    Km = 34; g = hl.grow(H, loc + nrm * .0005, d, .012 * (Km - 1), K=Km, gravity=0.0, minlift=(.0008, S['lift_tip'] * r.uniform(.5, 1.0)), maxlift=(.0015, S['lift_tip'] * 1.6), wander=S.get('wander', .01), rng=r, target=bun['c'], pull=.35, stop_r=S['bun_r'][0] * .6)
    seg = np.linalg.norm(np.diff(g, axis=0), axis=1); last = int(np.nonzero(seg > 1e-6)[0].max()) + 1 if (seg > 1e-6).any() else 1
    g = g[:last + 1]; cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(g, axis=0), axis=1))]; K_ = S.get('K', 16); ti = np.linspace(0, cum[-1], K_)
    return np.stack([np.interp(ti, cum, g[:, a_]) for a_ in range(3)], 1)
def guide_crest(root, r, kind='hair'):
    """A tall crest (Seth, pictures 580-589): the hair of the top of the head stands up from a high forehead and leans
    back, every lock bending towards one ridge above the skull, so the mass narrows upward like a flame; the sides are
    brushed back over the ears and the nape is short. Top strands are arcs from the root, out along the scalp normal,
    to a point near the ridge; they do not fall (set hair)."""
    loc, nrm = H.near(root); az, e = H.params(loc); d0 = hl.unit(loc - H.ctr); back = np.array([0.0, 1.0, 0.0])
    # the top stands; over the forehead the hair stands from the hair line itself, at the sides only above the temples
    ce = S.get('crest_e', (.86, .50)); fw = float(sstep(1.30, .80, abs(az)))
    top_w = float(sstep(ce[0] + (1.06 - ce[0]) * fw, ce[1] + (.82 - ce[1]) * fw, e))
    # the swept sides and the nape
    flow = back + np.array([0, 0, S.get('side_up', .30)]); flow = hl.unit(flow - nrm * (flow @ nrm))
    down = np.array([0, .25, -1.0]); down = hl.unit(down - nrm * (down @ nrm)); nape = float(sstep(.15, .55, d0[1])) * float(sstep(.55, .95, e))
    flow = hl.unit(flow * (1 - nape) + down * nape)
    ang = (hl.f1(loc, S.get('tousle_scale', 38), 77 + S.get('seed', 1)) - .5) * 2 * S['tousle'] * (.5 + .5 * JS) + r.normal(0, S.get('jit', .12)) * JS
    around = np.cross(nrm, flow); flow = flow * math.cos(ang) + around * math.sin(ang)
    Ls = (S['L_side'] + (S['L_nape'] - S['L_side']) * nape) * (.8 + .4 * hl.f1(loc, 60, 91)) * r.uniform(.9, 1.08)
    el = math.radians(S['el_side'] + r.normal(0, S.get('el_jit', 6)))
    K = S.get('K', 9)
    if kind == 'wisp': Ls *= r.uniform(.3, .55)
    side = hl.grow(H, loc + nrm * .0004, flow * math.cos(el) + nrm * math.sin(el), Ls, K=K, gravity=S['gravity'], minlift=(.0006, S['lift_tip']), wander=S.get('wander', .05), rng=r)
    if top_w <= 0: return side
    # the standing top
    ridge = np.array([S.get('crest_x', 0.0), H.ctr[1] + S.get('crest_back', .035), H.top + S.get('crest_h', .085)])
    lock = hl.f1(loc, S.get('lock_scale', 26), 211 + S.get('seed', 1))        # neighbouring strands share a lock: its length and its lean
    tip = ridge + np.array([loc[0] * S.get('crest_w', .42), (loc[1] - H.ctr[1]) * S.get('crest_l', .55), 0.0])
    tip[1] += S.get('crest_sweep', 0.0) * (.4 + .6 * max(0.0, -d0[1]))            # the tips are brushed back, the front ones most: a wave, not a spike
    tip[2] -= S.get('crest_arc', .9) * max(0.0, loc[1] - H.ctr[1] + S.get('crest_peak', .02)) ** 1.3 + 2.2 * abs(loc[0]) ** 1.6       # highest above the forehead, falling to the back and the sides
    tip = tip + (lock - .5) * np.array([.03, .05, .04]) * S.get('lock_var', 1.0) + r.normal(0, S.get('crest_jit', .004), 3) * JS
    reach = np.linalg.norm(tip - loc); ctrl = loc + nrm * reach * S.get('crest_out', .48) + np.array([0, -.25, .25]) * reach * S.get('crest_fwd', .25) * max(0.0, -d0[1])
    f = (S.get('crest_len', (.72, 1.0))[0] + (S.get('crest_len', (.72, 1.0))[1] - S.get('crest_len', (.72, 1.0))[0]) * lock) * r.uniform(.92, 1.04)
    if kind == 'fly': f *= r.uniform(1.0, 1.12)
    if kind == 'wisp': f *= r.uniform(.16, .34)          # short new hair along the hair line, so the crest does not start as a ruled edge
    t = np.linspace(0, 1, K)[:, None] * min(f, 1.15)
    up = (1 - t) ** 2 * (loc + nrm * .0004) + 2 * (1 - t) * t * ctrl + t ** 2 * tip
    return side * (1 - top_w) + up * top_w
def torso_push(p, clear):
    """Keep a point of long hair outside the neck, the shoulders and the back: a rounded box measured on the assembled
    body (style `torso`: top = where the neck leaves the collar, z_sh = shoulder line, a / b = half width and half depth
    at the shoulder line and at the top)."""
    T = S['torso']
    if p[2] > T['top']: return p, None
    t = float(sstep(T['top'], T['z_sh'], p[2]))
    a = T['a'][1] + (T['a'][0] - T['a'][1]) * t + clear; b = T['b'][1] + (T['b'][0] - T['b'][1]) * t + clear
    x, y = p[0] / a, (p[1] - T['y0']) / b; rr = (x ** 4 + y ** 4) ** .25
    if rr >= 1: return p, None
    q = p.copy()
    if y > -.15:      # behind (and just in front of) the shoulder line the hair is laid back onto the back, not slid sideways down the arm
        q[0] = float(np.clip(p[0], -a * .9, a * .9)); q[1] = T['y0'] + b * (1 - min(abs(q[0] / a), .999) ** 4) ** .25
        return q, np.array([0.0, 1.0, 0.0])
    k = 1 / max(rr, 1e-3); q[0] = p[0] * k; q[1] = T['y0'] + (p[1] - T['y0']) * k
    out = hl.unit(np.array([x ** 3 / a, y ** 3 / b, 0.0]))
    return q, out
PUFF = S.get('puff', 0.0)
def back_y(x, z, clear):
    """The back of the rounded torso box at height z (see torso_push), `clear` off it."""
    T = S['torso']; t = float(sstep(T['top'], T['z_sh'], z))
    a = T['a'][1] + (T['a'][0] - T['a'][1]) * t + clear; b = T['b'][1] + (T['b'][0] - T['b'][1]) * t + clear
    return T['y0'] + b * (1 - min(abs(x / a), .98) ** 4) ** .25
def guide_drape(loc, nrm, r, kind, sg, lift, lock, K):
    """Long hair as a combed path in two smooth parts (style key `drape`), instead of a march with clamps: the march turned
    its locks at the ear and threw the side hair onto the back in one step, so in the game (23 Nov 2026) the maiden's head was a
    lattice of kinked planks crossing one another. (1) On the skull the lock lies on the head and runs with ONE flow field
    (sideways from the parting, then down and a little back), in short steps, to the height where hair leaves the head
    (`rel` under the nose line: ear lobe and nape). (2) From there it eases onto its own place in the curtain on the back
    (`width`: half width of the mane at the shoulder line; the place follows the angle round the head at which the lock left it)
    and hangs to `z_end`. The joined path is smoothed with the head and the torso kept clear, and resampled to K points."""
    DR = S['drape']; T = S['torso']; ds = DR.get('ds', .008); d0 = hl.unit(loc - H.ctr); back = max(0.0, d0[1])
    z_rel = H.nose[2] - DR.get('rel', .03) + (lock - .5) * DR.get('rel_var', .014)
    fy_ = DR.get('front_y', (.02, -.05)); fr0 = float(sstep(fy_[0], fy_[1], loc[1] - H.ctr[1]))
    v0 = np.array([sg * .95 * (1 - min(1.0, S.get('part_back', .6) * back)), DR.get('back', .30) + DR.get('front', 1.2) * fr0, -1.0]); d = hl.unit(v0 - nrm * (v0 @ nrm))      # the flow's own direction from the first step: sideways from the parting on top, down and a little back on the sides, back over the head in front
    comb = np.array([0.0, DR.get('back', .30), -1.0]) * DR.get('comb', .16)
    p = loc + nrm * .0006; pts = [p.copy()]; run = 0.0
    for _ in range(int(.40 / ds)):
        fr_ = float(sstep(DR.get('front_y', (.02, -.05))[0], DR.get('front_y', (.02, -.05))[1], p[1] - H.ctr[1]))      # in front of the ears the hair is combed BACK over the ear (it fell down the cheek and was then dragged through the neck to the back: kinked locks on the face)
        l2, n2 = H.near(p); d = d + comb + np.array([0.0, DR.get('front', 1.2) * DR.get('comb', .16) * fr_, 0.0]) + r.normal(0, DR.get('wander', .004), 3); d = hl.unit(d - n2 * (d @ n2)); p = p + d * ds; run += ds
        l2, n2 = H.near(p); p = l2 + n2 * (.0008 + (lift + .003) * min(1.0, run / .05) + DR.get('body', .004) * lock * min(1.0, run / .08))
        pts.append(p.copy())
        if p[2] < z_rel or (n2[2] < -DR.get('under', .10) and p[1] > H.ctr[1] - .02): break      # hair leaves the head where the skull turns under (the bulge at the back, the widest line over the ears): it hangs from there, it does not follow the head in to the nape
    pr = pts[-1]; az_ = abs(H.params(loc)[0])      # the lock's place across the curtain follows the angle of its ROOT round the head (pi = the middle of the back): roots are even round the head, the places where locks leave it are not (they crowd at the nape and left the edges of the mane bare)
    u_ = min(1.0, (math.pi - az_) / (math.pi - DR.get('az_edge', 1.15)))
    if u_ >= 1.0: u_ = 1 - DR.get('edge_spread', .3) * r.random()      # hair rooted in front of the ears joins the outer part of the mane
    xt = sg * DR.get('width', .155) * u_ ** DR.get('gamma', .9) + (hl.f1(loc, 18, 77 + S.get('seed', 1)) - .5) * DR.get('x_var', .03) + r.normal(0, .004)
    z_tip = S['z_end'] + (.5 - lock) * S.get('len_lock', .07) + r.normal(0, .012) + (r.uniform(0, .05) if kind == 'over' else 0.0)
    clear = .008 + lift * 1.6 + DR.get('depth', .008) * lock; z_c = T['z_sh'] + DR.get('land', 0.0); ph = 6.283 * lock + r.uniform(0, 1.2)
    nf = max(4, int((pr[2] - z_tip) / DR.get('ds_fall', .015)))
    for k in range(1, nf + 1):
        z = pr[2] + (z_tip - pr[2]) * k / nf; s_ = float(sstep(0.0, 1.0, (pr[2] - z) / max(pr[2] - z_c, 1e-3))); s2 = 1 - (1 - s_) ** 1.6
        x = pr[0] + (xt - pr[0]) * s_; x *= 1 - DR.get('narrow', .10) * float(sstep(T['z_sh'], S['z_end'], z))
        x += S.get('wave', .06) * .12 * math.sin(ph + S.get('wave_n', 6.0) * k / nf) * s_
        y = pr[1] + (back_y(x, T['z_sh'], clear) - pr[1]) * s2      # towards the curtain at the shoulder line all the way (the box at neck height is narrow: aiming at it drew the lock in before it went out)
        pts.append(np.array([x, y, z]))
    pts = np.array(pts); ns = len(pts) - nf - 1
    def push(P):      # how far each point must move to clear the skin of head, neck and shoulders (the cloth of the dress below the collar) and the torso box
        Dv = np.zeros_like(P)
        for i in range(1, len(P)):
            q = P[i].copy()
            if q[2] > T['z_sh'] - .06:
                c_ = .0008 + lift + DR.get('cloth', .008) * float(sstep(T['top'] + .03, T['top'] - .01, q[2])); l2, n2 = H.near(q); v_ = q - l2
                if v_ @ n2 < c_ and v_ @ v_ < .05 ** 2: q = l2 + n2 * c_
            if q[2] < T['top']:
                q2, out = torso_push_r(q, .006 + lift * 1.6)
                if out is not None: q = q2
            Dv[i] = q - P[i]
        return Dv
    kb = np.array([1, 2, 3, 2, 1.0]) / 9
    for _ in range(DR.get('clear_it', 4)):      # a push is spread along the lock (widened, then blurred) before it is applied, so the lock rides over a shoulder in one long curve; a push on single points left a kink at each
        Dv = push(pts); m = np.linalg.norm(Dv, axis=1)
        if m.max() < 1e-4: break
        md = np.array([m[max(0, i - 3):i + 4].max() for i in range(len(m))]); md = np.convolve(np.pad(md, 2, mode='edge'), kb, mode='valid')
        Db = np.stack([np.convolve(np.pad(Dv[:, c], 3, mode='edge'), np.ones(7) / 7, mode='valid') for c in range(3)], 1); nb = np.linalg.norm(Db, axis=1)
        w_ = np.minimum(1.0, np.arange(len(pts)) / 3.0)      # the root stays on the scalp
        pts = pts + Db / np.maximum(nb, 1e-9)[:, None] * (md * w_)[:, None] * (nb > 1e-6)[:, None]
    for _ in range(DR.get('smooth', 6)):
        pts[1:-1] = (pts[:-2] + 2 * pts[1:-1] + pts[2:]) / 4
    pts = pts + push(pts) * np.minimum(1.0, np.arange(len(pts)) / 3.0)[:, None]
    for _ in range(2): pts[1:-1] = (pts[:-2] + 2 * pts[1:-1] + pts[2:]) / 4
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]; dd = np.linspace(0, cum[-1], K)
    return np.stack([np.interp(dd, cum, pts[:, c]) for c in range(3)], 1)
def torso_push_r(p, clear):
    """torso_push without the jump onto the back: a point inside the rounded box leaves it by the shortest way."""
    T = S['torso']
    if p[2] > T['top']: return p, None
    t = float(sstep(T['top'], T['z_sh'], p[2])); a = T['a'][1] + (T['a'][0] - T['a'][1]) * t + clear; b = T['b'][1] + (T['b'][0] - T['b'][1]) * t + clear
    x, y = p[0] / a, (p[1] - T['y0']) / b; rr = (x ** 4 + y ** 4) ** .25
    if rr >= 1: return p, None
    k = 1 / max(rr, 1e-3); q = p.copy(); q[0] = p[0] * k; q[1] = T['y0'] + (p[1] - T['y0']) * k
    return q, hl.unit(np.array([x ** 3 / a, y ** 3 / b, 0.0]))
def guide_long(root, r, kind='hair'):
    """Long loose hair (the maidens, pictures 221-259): parted in the middle, combed sideways over the crown, falling
    behind the shoulders down the back to `z_end`, with a short fringe over the brow. kinds: 'under' lies on the back,
    'hair' a little off it, 'over' loose outer locks, 'fringe', 'wisp' (short new hair along the hair line)."""
    loc, nrm = H.near(root); az, e = H.params(loc); d0 = hl.unit(loc - H.ctr); sg = 1.0 if loc[0] >= 0 else -1.0; K = S.get('K', 22)
    if kind == 'cross': sg = -sg      # a lock combed over the parting from the other side, so the parting is not a ruled line of scalp
    if kind == 'fringe':
        d = np.array([sg * .45 * min(1.0, abs(loc[0]) / .03), -1.0, -.35]); d = hl.unit(hl.unit(d - nrm * (d @ nrm)) + nrm * .22)
        L = S['L_fringe'] * r.uniform(.7, 1.1) * (.75 + .5 * hl.f1(loc, 40, 51))
        return hl.grow(H, loc + nrm * .0004, d, L, K=K, gravity=1.5, minlift=(.0006, .0035), wander=.03, rng=r)
    back = max(0.0, d0[1])
    d = np.array([sg * (.95 - S.get('part_back', .6) * back), .45 + .5 * back, -.30]); d = hl.unit(d - nrm * (d @ nrm))      # part_back: how far the middle parting closes towards the back of the head
    if kind == 'wisp':
        return hl.grow(H, loc + nrm * .0004, d, r.uniform(.02, .045), K=K, gravity=.6, minlift=(.0005, .002), wander=.05, rng=r)
    lift = {'under': 0.0, 'hair': .004, 'over': S.get('over_lift', .010)}.get(kind, .004)
    lock = hl.f1(loc, S.get('lock_scale', 30), 311 + S.get('seed', 1))
    if S.get('drape'): return guide_drape(loc, nrm, r, kind, sg, lift, lock, K)
    L = max(.12, (loc[2] - S['z_end'] - S.get('z_back', 0.0) * back) * 1.10 + .05 * float(sstep(.6, .1, e)) + (lock - .5) * S.get('len_lock', .07) + r.normal(0, .012))
    if kind == 'over': L *= r.uniform(.92, 1.0)
    step = L / (K - 1); p = loc + nrm * .0006; pts = [p.copy()]; ph = 6.283 * lock + r.uniform(0, 1.2)
    for k in range(1, K):
        t = k / (K - 1)
        # falling; between the ears and the shoulders the side hair is drawn behind the shoulder
        zs = S['torso']['z_sh']; pull = S.get('back_pull', .5) * float(sstep(zs + .24, zs + .10, p[2])) * float(p[2] > zs - .02) * float(sstep(.09, .02, p[1]))
        fan = S.get('fan', 0.0) * float(p[2] < zs + .04) * float(p[1] > .04)          # on the back the hair spreads to the width of the shoulders
        d = d + np.array([sg * fan, pull, -1.0]) * S['gravity'] * step * 14 * (.3 + .7 * t)
        if S.get('tuck') and zs - .02 < p[2] < zs + .22 and p[1] < .07:      # tucked behind the shoulder: steered back before it lands on it
            d = d + np.array([0.0, S['tuck'] * (.07 - p[1]) / .07 * float(sstep(zs + .22, zs + .12, p[2])), 0.0])
        side = np.cross(d, [0.0, 0.0, 1.0]); side = hl.unit(side) if np.linalg.norm(side) > 1e-3 else np.array([1.0, 0.0, 0.0])
        d = d + side * S.get('wave', .1) * math.sin(ph + t * S.get('wave_n', 6.0)) * step * 14 + r.normal(0, S.get('wander', .02), 3)
        d = hl.unit(d); p = p + d * step
        l2, n2 = H.near(p); h = (p - l2) @ n2; ml = .0008 + (lift + .003) * min(1.0, t * 4)
        if PUFF:      # a full head of hair (the Mother's bob, pictures 351-359): the hair stands off the skull and the cheeks, more so further down, and turns under at the tips
            ml += PUFF * (.35 + .65 * lock) * float(sstep(0.0, .45, t)) * (1 - .55 * float(sstep(.82, 1.0, t)))
            if t > .8: d = hl.unit(d - n2 * S.get('curl', 0.0) * (t - .8) * 5 * step * 14)
        mx = ml + S.get('hug', .010) + lift
        if h < ml:
            p = l2 + n2 * ml; dn = d @ n2
            if dn < 0: d = hl.unit(d - n2 * dn)
        elif h > mx and p[2] > H.nose[2] - .06 and l2[2] > H.nose[2] - .08:      # combed: on the skull the hair lies on the head
            p = l2 + n2 * mx; dn = d @ n2
            if dn > 0: d = hl.unit(d - n2 * dn)
        q, out = torso_push(p, .008 + lift * 1.6)
        if out is not None:
            p = q; dn = d @ out
            if dn < 0: d = hl.unit(d - out * dn)
        pts.append(p.copy())
    pts = np.array(pts)
    for _ in range(S.get('guide_smooth', 0)):      # a brushed head of hair: the kinks the skull, ear and collar clamps leave are combed out
        pts[1:-1] = (pts[:-2] + 2 * pts[1:-1] + pts[2:]) / 4
    return pts
guide = {'short': guide_short, 'crest': guide_crest, 'long': guide_long}.get(S['kind'], guide_bun)
# ------------------------------------------------------------------ strand groom (hair Curves + procedural hair node groups)
gr = np.random.default_rng(S.get('seed', 1) + 100)
roots = RT.sample(S['guides'], 0, 1.0)
G = np.array([guide(p, gr) for p, _ in roots]); UVr = np.array([uv for _, uv in roots])
if os.environ.get('HAIR_DBG'):
    for z_ in (1.60, 1.52, 1.44, 1.30, 1.15):
        q_ = np.array([g[np.argmin(np.abs(g[:, 2] - z_))] for g in G if g[:, 2].min() < z_ + .01])
        if len(q_): log('dbg z', z_, 'n', len(q_), '|x| p10/50/90/max', np.percentile(np.abs(q_[:, 0]), [10, 50, 90, 100]).round(3).tolist(), 'y p10/50/90', np.percentile(q_[:, 1], [10, 50, 90]).round(3).tolist())
    if 'dbgonly' in steps: raise SystemExit
if S.get('drape'):
    dv_ = np.diff(G, axis=1); dv_ /= np.maximum(np.linalg.norm(dv_, axis=2, keepdims=True), 1e-9); an_ = np.degrees(np.arccos(np.clip((dv_[:, 1:] * dv_[:, :-1]).sum(2), -1, 1))).max(1)
    ang_ = np.degrees(np.arccos(np.clip((dv_[:, 1:] * dv_[:, :-1]).sum(2), -1, 1))); ix_ = ang_.argmax(1); zz_ = G[np.arange(len(G)), ix_ + 1, 2]
    if os.environ.get('HAIR_DBG'):
        log('drape dbg: index of the sharpest turn, histogram', np.bincount(ix_, minlength=38).tolist())
        for lo_, hi_ in ((1.70, 9), (1.64, 1.70), (1.60, 1.64), (1.52, 1.60), (1.44, 1.52), (0, 1.44)):
            m_ = (zz_ >= lo_) & (zz_ < hi_); log('drape dbg: z', lo_, hi_, 'n', int(m_.sum()), 'p50/p90 turn', np.percentile(an_[m_], [50, 90]).round(1).tolist() if m_.any() else None, 'mean y', round(float(G[np.arange(len(G)), ix_ + 1, 1][m_].mean()), 3) if m_.any() else None)
    if os.environ.get('HAIR_DBG'):
        for gi_ in np.nonzero((zz_ > 1.52) & (zz_ < 1.60) & (an_ > 45))[0][:3]:
            log('drape dbg guide', int(gi_), 'turn', round(float(an_[gi_]), 1), 'at', int(ix_[gi_]), 'pts', G[gi_, max(0, ix_[gi_] - 4):ix_[gi_] + 5].round(3).tolist())
    log('drape: sharpest turn per guide, degrees p50/p90/p99/max', np.percentile(an_, [50, 90, 99, 100]).round(1).tolist(), 'over 30:', int((an_ > 30).sum()))
    def card_n(p, nrm):      # below the head a hanging card faces away from the neck and the back, not along the nearest skin's normal (over a shoulder that is straight up: the card lay flat and showed as a line)
        T = S['torso']; w_ = float(sstep(H.nose[2] - .02, H.nose[2] - .09, p[2]))
        if w_ <= 0: return nrm
        t = float(sstep(T['top'], T['z_sh'], p[2])); a = T['a'][1] + (T['a'][0] - T['a'][1]) * t; b = T['b'][1] + (T['b'][0] - T['b'][1]) * t
        o = np.array([(p[0] / a) ** 3 / a, ((p[1] - T['y0']) / b) ** 3 / b, 0.0]); o = hl.unit(o) if np.linalg.norm(o) > 1e-6 else np.array([0.0, 1.0, 0.0])
        return hl.unit(nrm * (1 - w_) + o * w_)
log('guides', G.shape, 'mean length', float(np.linalg.norm(np.diff(G, axis=1), axis=2).sum(1).mean()))
smat = hl.strand_material('M_%s_HairStrands' % N, **S['strand'])
strands = hl.make_curves('HairStrands', G, radius=S.get('radius', 4.5e-5), surface=scalp, root_uv=UVr)
chain = [('Interpolate Hair Curves', {'Density': S['density'], 'Density Mask': ('attr', 'dens'), 'Interpolation Guides': S.get('interp', 4), 'Part by Mesh Islands': True, 'Seed': 3}),
         ('Clump Hair Curves', {'Factor': S['clump'], 'Shape': S.get('clump_shape', .45), 'Tip Spread': S.get('tip_spread', .002), 'Existing Guide Map': False, 'Guide Distance': S.get('clump_d', .009), 'Seed': 5}),
         ('Hair Curves Noise', {'Distance': S.get('noise_d', .003), 'Scale': S.get('noise_s', 14.0), 'Shape': .4, 'Scale along Curve': 1.0, 'Offset per Curve': .4, 'Seed': 7}),
         ('Frizz Hair Curves', {'Distance': S.get('frizz_d', .0012), 'Shape': .5, 'Seed': 9}),
         ('Trim Hair Curves', {'Replace Length': False, 'Length Factor': 1.0, 'Random Offset': S.get('trim_rand', .012), 'Seed': 11}),
         ('Set Hair Curve Profile', {'Replace Radius': True, 'Radius': S.get('radius', 4.5e-5), 'Shape': .35})]
hl.gn_chain(strands, 'GN_%s_Hair' % N, chain, material=smat, surface=scalp, resample=S.get('resample', 14), streak=S.get('streak_scale'))
extra = []          # further strand objects (bun bundles, loose wisps)
BUNP = []
if S['kind'] == 'bun':
    R3 = S['bun_r']; c = bun['c']; nb = S.get('bun_bundles', 9)
    for q in range(nb):   # wound bundles: each wraps the bun on a tilted coil, twisting with its neighbour
        ph = 2 * math.pi * q / nb + gr.uniform(-.2, .2); turns = gr.uniform(1.1, 1.6); lat0 = gr.uniform(-.1, .35); Kb = 40; pts = []
        tw_r = gr.uniform(.003, .006); tw_f = gr.uniform(2.5, 4.0); tw_p = gr.uniform(0, 6.28)
        for k in range(Kb):
            t = k / (Kb - 1); az = ph + 2 * math.pi * turns * t; la = lat0 + (1.15 - lat0) * t ** 1.3 * (.55 + .45 * (q % 3) / 2)
            rr = 1.0 + .10 * math.sin(tw_p + tw_f * az)
            p = c + bun['bn'] * (R3[2] * rr * math.sin(la) + tw_r * math.cos(tw_p + tw_f * az)) + (bun['bx'] * R3[0] * math.cos(az) + bun['by'] * R3[1] * math.sin(az)) * math.cos(la) * rr
            pts.append(p)
        BUNP.append(np.array(pts))
    bobj = hl.make_curves('HairBun', np.array(BUNP), radius=S.get('radius', 4.5e-5))
    hl.gn_chain(bobj, 'GN_%s_Bun' % N, [('Duplicate Hair Curves', {'Amount': S.get('bun_amount', 420), 'Radius': S.get('bun_bundle_r', .0075), 'Distribution Shape': .3, 'Tip Roundness': .6, 'Seed': 2}),
                                       ('Frizz Hair Curves', {'Distance': S.get('frizz_d', .0012) * 1.3, 'Shape': .3, 'Seed': 6}),
                                       ('Set Hair Curve Profile', {'Replace Radius': True, 'Radius': S.get('radius', 4.5e-5), 'Shape': .35})], material=smat, resample=60, streak=S.get('streak_scale'))
    extra.append(bobj)
    wr = [p for p, _ in RT.sample(S.get('wisps', 14), .86, 1.0, azmin=.75, azmax=1.5)] + [p for p, _ in RT.sample(S.get('wisps_nape', 10), .86, 1.0, azmin=2.2)]
    WP = np.array([guide(p, gr, 'wisp') for p in wr])
    wobj = hl.make_curves('HairWisps', WP, radius=S.get('radius', 4.5e-5))
    hl.gn_chain(wobj, 'GN_%s_Wisps' % N, [('Duplicate Hair Curves', {'Amount': 5, 'Radius': .0013, 'Seed': 2}), ('Frizz Hair Curves', {'Distance': .0015, 'Seed': 6}),
                                          ('Set Hair Curve Profile', {'Replace Radius': True, 'Radius': S.get('radius', 4.5e-5) * .9, 'Shape': .35})], material=smat, resample=16)
    extra.append(wobj)
# ------------------------------------------------------------------ brows: a short strand groom per brow, baked into the atlas band
BR = dict(z0=.0185, arch=.0055, th=.0048, x0=-.021, span=.054, n=600, len=(.0095, .006), r=4.0e-5, inner_up=0.0); BR.update(S.get('brow', {}))   # inner_up: the inner third of the brow raised (a harmless, slightly puzzled look instead of a scowl)
KE = abs(H.eyes[1][0][0]) / .031
for k_ in ('z0', 'arch', 'th', 'x0', 'span', 'inner_up'): BR[k_] *= KE
def brow_zc(sgn, s_):
    e_ = H.eyes[sgn][0]; return e_[2] + BR['z0'] + BR['arch'] * math.sin(math.pi * min(max(s_, 0), 1.15) * .72) - .0035 * float(sstep(.7, 1.1, s_)) + BR['inner_up'] * (1 - float(sstep(0, .4, s_)))
def brow_th(s_): return BR['th'] * (1 - .72 * float(sstep(.4, 1.0, s_))) * (.55 + .45 * float(sstep(0, .12, s_)))
def brow_pt(sgn, s_, dz):
    e_ = H.eyes[sgn][0]; x = sgn * (abs(e_[0]) + BR['x0'] + s_ * BR['span']); z = brow_zc(sgn, s_) + dz
    loc, nrm, _, _ = H.bvh.ray_cast(Vector((x, e_[1] - .09, z)), Vector((0, 1, 0)))
    if loc is None: return H.near(np.array([x, e_[1] + .01, z]))
    return np.array(loc), np.array(nrm)
BROWP = []; BROWB = []; brng = np.random.default_rng(S.get('seed', 1) + 400); bcol = np.array(S['albedo']) * S.get('brow_dark', .6)
BW = BR['th'] * 2.4     # card half height
for sgn in (1, -1):
    k = 0
    while k < BR['n']:
        s_ = brng.uniform(-.02, .97); w_ = brng.uniform(-1, 1)
        if brng.random() < abs(w_) ** 2.5 * .7 or brng.random() < .5 * float(sstep(.75, 1.05, s_)): continue
        p, nrm = brow_pt(sgn, s_, w_ * brow_th(s_))
        if p is None: continue
        p2, _ = brow_pt(sgn, s_ + .05, 0); p1, _ = brow_pt(sgn, s_, 0); T = hl.unit(p2 - p1); U = hl.unit(np.array([0, 0, 1.0]) - nrm * nrm[2])
        th = math.radians(78 - 50 * float(sstep(0, .2, s_))) if s_ < .2 else math.radians(-26 * w_ + 6)
        th += brng.normal(0, .14); d = T * math.cos(th) + U * math.sin(th)
        L = (BR['len'][0] + (BR['len'][1] - BR['len'][0]) * min(max(s_, 0), 1)) * brng.uniform(.75, 1.2) * (1 - .5 * float(sstep(.8, 1.0, s_)))
        g = hl.grow(H, p + nrm * .0002, hl.unit(d + nrm * .22), L, K=5, gravity=0.0, minlift=(.0002, .0014), wander=.03, rng=brng)
        BROWP.append(g); k += 1
        e_ = H.eyes[sgn][0]; ss = (sgn * g[:, 0] - (abs(e_[0]) + BR['x0'])) / BR['span']; zz = np.array([g[i, 2] - brow_zc(sgn, ss[i]) for i in range(len(g))])
        u = (ss + .10) / 1.25 * .5; v = (.125 if sgn > 0 else 0.0) + (zz / (2 * BW) + .5) * .125
        BROWB.append(dict(P=np.c_[np.clip(u, .002, .498), np.clip(v, .002, .248), np.full(len(g), .5)], r=S.get('brow_px', 2.8), col=bcol * math.exp(brng.normal(0, .2))))
bmat = hl.strand_material('M_%s_BrowStrands' % N, **{**S['strand'], 'melanin': min(1.0, S['strand']['melanin'] + S.get('brow_melanin', .12)), 'grey': 0.0})
brows = hl.make_curves('BrowStrands', np.array(BROWP), radius=np.tile(BR['r'] * (1 - .8 * sstep(.4, 1.0, np.linspace(0, 1, 5)))[None, :], (len(BROWP), 1)))
brows.data.materials.append(bmat)
# ------------------------------------------------------------------ cap: the evaluated groom projected about the head centre
CM = hl.CapMap(H); CM.build_skull()
SP = hl.evaluated_strands(strands, 14)
cu0, cv0, r0 = CM.uv(SP); th_ = np.hypot(cu0 - .5, cv0 - .5) * 2 * CM.th_max; CM.th_max = float(min(2.75, np.percentile(th_, 99.9) + .08)); CM.build_skull()
cu, cv, hh = CM.fields(SP); log('cap: strands', len(SP), 'th_max', round(CM.th_max, 3), 'height p50/p99', round(float(np.percentile(hh, 50)), 4), round(CM.hmax, 4))
# ------------------------------------------------------------------ atlas
NT = S.get('ntiles', ['n_dense'] * 9 + ['n_mid'] * 10 + ['n_thin'] * 7 + ['n_wisp'] * 4 + ['n_fly'] * 2)
TILES = NT + ['dense'] * 4
TI = {k: [i for i, t in enumerate(TILES) if t == k] for k in set(TILES)}
if 'atlas' in steps or not (TX / ('T_%s_PR_Hair_FLOW.png' % N)).exists():
    ar = np.random.default_rng(S.get('seed', 1) + 200); base = np.array(S['albedo']); grey = S.get('grey', 0.0)
    def col_fun(r):
        if r.random() < grey: return np.array(S.get('grey_col', (.42, .40, .36))) * r.uniform(.8, 1.15)
        c = base * math.exp(r.normal(0, S.get('col_var', .22))); c = c * (1 + r.normal(0, .06, 3)); return np.clip(c, .004, .9)
    CR = hl.CAP_RECT; near = np.clip(hh / max(CM.hmax, 1e-4), 0, 1)
    capP = np.stack([CR[0] + cu * (CR[2] - CR[0]), near, CR[1] + cv * (CR[3] - CR[1])], -1)
    # the cap carries the inner part of every strand; the free tips belong to the cards (ragged, feathered cap edge)
    te = ar.uniform(S.get('cap_tip', (.5, 1.0))[0], S.get('cap_tip', (.5, 1.0))[1], len(capP)); Kc = capP.shape[1]; ti = np.linspace(0, 1, Kc)[None, :] * te[:, None] * (Kc - 1)
    i0_ = np.clip(np.floor(ti).astype(int), 0, Kc - 2); f_ = (ti - i0_)[..., None]; ar_ = np.arange(len(capP))[:, None]; capP = capP[ar_, i0_] * (1 - f_) + capP[ar_, i0_ + 1] * f_
    lowf = np.array([.75 + .5 * hl.f1(p, 70, 311) for p in SP[:, 0]])         # lock-scale colour coherence
    capC = np.array([col_fun(ar) for _ in range(len(SP))]) * lowf[:, None]
    A, B = hl.render_atlas(str(PRE) + '_Hair', S.get('tile', {}), ar, TILES, col_fun, band=BROWB, cap=dict(P=capP, col=capC, r_px=S.get('cap_px', 2.2)))
    hl.compose_atlas(str(PRE) + '_Hair', A, B, S.get('tile', {}), alpha_gain=S.get('alpha_gain', 1.6), under_mask=CM.rgrid)
    MH = CHARS / 'ThirdParty/MakeHuman'
    r_ = subprocess.run(['python3', '-I', str(Path(__file__).parent / 'hair_band.py'), str(PRE) + '_Hair', str(MH / 'eyebrows/eyebrow001/eyebrow001.png'), str(MH / 'eyelashes/eyelashes01/eyelashes01.png'), S['brow_rgb'], S['lash_rgb'], 'lashonly'], capture_output=True, text=True)
    log('band', r_.stdout.strip(), r_.stderr.strip()[-300:])
# ------------------------------------------------------------------ game hair: opaque cap shell + narrow lock cards from the same guide field
cr = np.random.default_rng(S.get('seed', 1) + 300); CB = hl.Cards(H); DN = S.get('card_density', 1.0)
def cap_mesh(NR=S.get('cap_rings', 20), NS=S.get('cap_segs', 44), kh=S.get('cap_h', .3)):
    CR = hl.CAP_RECT; base = len(CB.v); idx = {}; dens = {}
    def vert(i, j):
        key = (i, j % NS) if i else (0, 0)
        if key in idx: return idx[key]
        rho = i / NR; az = 2 * math.pi * (j % NS) / NS; c_u = .5 + .5 * rho * math.sin(az); c_v = .5 - .5 * rho * math.cos(az)
        d = CM.dirs(np.array(c_u), np.array(c_v)); loc, nrm = CM.cast(d); h = float(CM.lookup(CM.hgrid, c_u, c_v)); dn = float(CM.lookup(CM.dgrid, c_u, c_v))
        kk = kh + (S.get('cap_h_hi', kh) - kh) * float(sstep(.012, .03, h))
        pv = loc + d * (S.get('cap_off', .0010) + min(kk * h, S.get('cap_hmax', .02))); l2, n2 = H.near(pv); sd_ = float((pv - l2) @ n2)
        if sd_ < .0010: pv = pv + n2 * (.0010 - sd_)
        CB.v.append(pv); CB.uv.append((CR[0] + c_u * (CR[2] - CR[0]), CR[1] + c_v * (CR[3] - CR[1]))); CB.hl.append(1); CB.hn.append(hl.unit(nrm * .6 + d * .4))
        idx[key] = len(CB.v) - 1; dens[idx[key]] = dn; return idx[key]
    nf = 0
    for i in range(NR):
        for j in range(NS):
            if i == 0: f = (vert(0, 0), vert(1, j), vert(1, j + 1))
            else: f = (vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1))
            if max(dens[q] for q in f) > .04: CB.f.append(f); nf += 1
    sd = []
    for q in range(base, len(CB.v)):
        l_, n_ = H.near(CB.v[q]); sd.append(float((CB.v[q] - l_) @ n_))
    sd = np.array(sd); log('cap faces', nf, 'verts', len(sd), 'signed dist to skin min/p5/median', round(float(sd.min()), 4), round(float(np.percentile(sd, 5)), 4), round(float(np.median(sd)), 4), 'below skin', int((sd < .0003).sum()), 'dens<.5', int(sum(1 for v_ in dens.values() if v_ < .5)))
cap_mesh()
def cap_floor(p, kh=S.get('cap_h', .3)):
    c_u, c_v, _ = CM.uv(np.asarray(p)); h = float(CM.lookup(CM.hgrid, c_u, c_v)); kk = kh + (S.get('cap_h_hi', kh) - kh) * float(sstep(.012, .03, h))
    return S.get('cap_off', .0010) + min(kk * h, S.get('cap_hmax', .02))
CB.floor = cap_floor
def nseg_for(g, n0, seg_len):
    if not seg_len: return n0
    L = float(np.linalg.norm(np.diff(g, axis=0), axis=1).sum()); return int(min(max(round(L / seg_len), 2), n0))
def shell(n, layer, tiles, e0, e1, width, nseg, across, lift_scale, lift_off, flare=(0.0, 0.0), kind='hair', roll=.03, bow=.05, azmin=0.0, azmax=4.0, t_range=(0.0, 1.0), wfun=None, nblend=.92, len_var=0.0, root_ext=0.0, v_span=(0.0, 1.0), seg_len=0.0, taper=.3, adapt=0.0, seg_max=.10, root_w=1.0):
    tl = [i for k in ([tiles] if isinstance(tiles, str) else tiles) for i in TI[k]]
    for p, _ in RT.sample(int(n * DN), e0, e1, azmin, azmax, wfun):
        if S['kind'] == 'short' and np.linalg.norm(p - crown) < S.get('crown_clear', .016): continue     # the whorl centre is carried by the cap
        g = guide(p, cr, kind); wk = 1 - S.get('edge_narrow', .3) * float(sstep(.72, 1.0, H.params(p)[1]))
        CB.ribbon(g, cr.uniform(*width) * wk, int(cr.choice(tl)), layer, cr, nseg=nseg_for(g, nseg, seg_len), across=across, lift_scale=lift_scale, lift_off=lift_off, roll=roll, bow=bow, taper=taper, flare=cr.uniform(*flare), t_range=(t_range[0], t_range[1] * (1 - len_var * cr.random())), nblend=nblend, root_ext=root_ext, v_span=v_span, adapt=adapt, seg_max=seg_max, root_w=root_w)
JS = S.get('card_jit', .7)
CB.t_pow = S.get('card_t_pow', 1.0)
if S.get('drape'): CB.card_n = card_n
for sh in S['shells']:
    f0_ = len(CB.f); shell(**sh); log('shell', sh.get('kind', 'hair'), 'n', sh['n'], 'tris', 2 * (len(CB.f) - f0_))
CB.t_pow = 1.0; CB.card_n = None
if S.get('beard'):
    # A beard (style key `beard`): locks rooted on the skin of the lower face, not on the scalp. Roots are drawn by area from
    # the triangles under the cheek line (from the corner of the moustache up to the ear), on the chin, under it, and on the
    # upper lip; the mouth stays open. Each lock is a guide grown downwards (hl.grow: it keeps clear of the neck and the
    # chest by `tip_lift`), longest at the chin (`L`) and shorter towards the ears (`L_side`), the moustache (`L_lip`) swept
    # out to the sides. Three sets of cards in the hair's own atlas tiles: a dense under layer (layer 1: it stays in every
    # LOD), narrower locks over it (layer 3) and wisps at the edge (layer 5). No cap shell lies under a beard: the skin
    # stage paints the stubble zone in the hair's colour (cfg/skin.json `stubble`).
    BD = S['beard']; b_rng = np.random.default_rng(S.get('seed', 1) + 500); floor_ = CB.floor; CB.floor = None; HB = H
    if BD.get('over'):      # '<blend under Characters>:<object>': clothes the beard lies over (a cowl); a lock inside or close over the cloth keeps clear of the cloth, not of the skin under it
        bl_, ob_ = BD['over'].split(':')
        with bpy.data.libraries.load(str(OUT / bl_)) as (s_, d_): d_.objects = [ob_]
        cl_ = d_.objects[0]; sc.collection.objects.link(cl_); cl_.hide_render = True; bpy.context.view_layer.update(); cbvh_ = bvh_of(cl_)
        class _Over:
            def near(s, p):
                l2, n2, _, _ = cbvh_.find_nearest(Vector(p))
                if l2 is not None and float((np.asarray(p) - np.array(l2)) @ np.array(n2)) < .05 and (np.asarray(p) - np.array(l2)) @ (np.asarray(p) - np.array(l2)) < .09 ** 2: return np.array(l2), np.array(n2)
                return H.near(p)
        HB = _Over(); CB.H = HB
    me_ = sk.data; me_.calc_loop_triangles(); cs_ = co_np(me_); nz_ = H.nose; cand = []; area = []; kind_ = []
    for t_ in me_.loop_triangles:
        c_ = cs_[list(t_.vertices)].mean(0); x_ = abs(c_[0]); y_ = c_[1] - nz_[1]; z_ = c_[2] - nz_[2]
        if z_ > .03 or z_ < -.125 or y_ > BD.get('y_max', .112) or t_.normal.dot(Vector(hl.unit(c_ - (H.ctr + np.array([0, -.02, -.06]))))) < .1: continue
        lip = z_ > -.027 and z_ < -.008 and x_ < .036 and y_ < .04                       # the upper lip
        mouth = z_ > -.047 and z_ <= -.027 and x_ < .029 and y_ < .035                    # the lips themselves
        cheek = z_ < -.036 + .50 * max(0.0, y_ - .03) + BD.get('cheek', 0.0) and z_ > -.108 + .25 * max(0.0, y_ - .03)      # under the cheek line, above the jaw's underside
        under = z_ <= -.108 + .25 * max(0.0, y_ - .03) and z_ > -.122 and y_ < .075       # a little way under the chin
        if mouth or not (lip or cheek or under): continue
        cand.append(list(t_.vertices)); area.append(t_.area); kind_.append('lip' if lip else 'face')
    area = np.array(area); log('beard: root triangles', len(cand), 'area cm2', round(float(area.sum()) * 1e4, 1))
    def beard_guide(wisp=False, ls=1.0, lk=1.0):
        i_ = int(b_rng.choice(len(cand), p=area / area.sum())); P_ = cs_[cand[i_]]; r1, r2 = b_rng.random(2)
        if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
        p = P_[0] + (P_[1] - P_[0]) * r1 + (P_[2] - P_[0]) * r2; loc, nrm = H.near(p); sx = 1.0 if p[0] >= 0 else -1.0
        y_ = p[1] - nz_[1]; side = float(np.clip((y_ - .03) / .07, 0, 1)); mid = float(np.clip(1 - abs(p[0]) / .03, 0, 1))
        if kind_[i_] == 'lip':
            d0 = np.array([sx * (.9 - .5 * mid), -.15, -.55 - .3 * mid]); L = BD.get('L_lip', .045) * b_rng.uniform(.7, 1.15)
        else:
            d0 = np.array([sx * .12 * side, -.30 * (1 - side) - .05, -1.0]) + nrm * .30; L = (BD['L_side'] + (BD['L'] - BD['L_side']) * (1 - side) ** (1.5 if lk >= 1.0 else .6)) * b_rng.uniform(.72, 1.1)
            if lk >= 1.0: L *= 1 - BD.get('point', .35) * (1 - mid) * (1 - side)           # the beard comes to a point under the chin (its core does not: it fills the sides down to the collar, where the dark opening of the cowl showed between the short side locks)
        if wisp: L *= b_rng.uniform(.3, .6)
        L *= ls
        return hl.grow(HB, loc + nrm * .0005, d0, L, K=BD.get('K', 10), gravity=BD.get('gravity', .8), minlift=(.0008, lk * BD.get('tip_lift', .03) * (.4 + .6 * min(1.0, L / max(BD['L'], 1e-3)))),
                       wander=BD.get('wander', .03), rng=b_rng, wave=(BD.get('wave', .10), BD.get('wave_n', 9.0), b_rng.uniform(0, 6.28)))
    w_ = BD.get('width', 1.0)
    def beard_n(p):      # a beard faces forwards and outwards from the neck's axis, a little upwards (it was shaded by the throat's downward normal: black locks under the chin)
        o_ = np.array([p[0] - H.ctr[0], p[1] - (H.ctr[1] + .03), 0.0]); o_ = hl.unit(o_) if np.linalg.norm(o_) > 1e-6 else np.array([0.0, -1.0, 0.0])
        return hl.unit(o_ + np.array([0.0, -.35, .35]))
    CB.shade_n = beard_n
    # `core` (optional): broad dense cards a little shorter and closer to the chest than the rest, the beard's body. Without it
    # the thinning tips of the under layer left gaps down to the dark cloth behind (the old man's beard read as black streaks).
    for n_b, layer, tl_, wd, seg, roll_, tap, nb_, wisp_, ls_, lk_ in ((BD.get('core', 0), 1, TI['n_dense'], (.034, .046), 5, .04, .40, .92, False, .84, .55),
                                                              (BD['n'][0], 1, TI['n_dense'] + TI['n_mid'], (.016, .024), 6, .10, .35, .85, False, 1.0, 1.0),
                                                              (BD['n'][1], 3, TI['n_mid'] + TI['n_thin'], (.009, .015), 6, .30, .55, .65, False, 1.0, 1.0),
                                                              (BD['n'][2], 5, TI['n_wisp'] + TI['n_thin'], (.005, .009), 3, .45, .6, .5, True, 1.0, 1.0)):
        for _ in range(int(n_b)):
            g = beard_guide(wisp_, ls_, lk_)
            CB.ribbon(g, b_rng.uniform(*wd) * w_, int(b_rng.choice(tl_)), layer, b_rng, nseg=nseg_for(g, seg, BD.get('seg_len', .03)), across=1, roll=roll_, bow=.06, taper=tap, nblend=nb_)
    CB.floor = floor_; CB.H = H; CB.shade_n = None
    if BD.get('over'): bpy.data.objects.remove(cl_, do_unlink=True)
if S['kind'] == 'bun':
    for q, pts in enumerate(BUNP):
        CB.wound(pts, S.get('bun_bundle_r', .0075) * 1.05, TI['n_dense'] + TI['n_mid'], 2, cr, strips=S.get('bun_strips', 5), nseg=S.get('bun_nseg', 14))
        off = cr.normal(0, .002, 3)
        if S.get('bun_ribbons', True): CB.ribbon(pts[2:-2] + off, cr.uniform(.007, .010), int(cr.choice(TI['n_thin'])), 3, cr, nseg=10, across=1, lift_scale=1.0, lift_off=0.0, roll=.6, bow=.1, nblend=.0)
    # core: an opaque ellipsoid of wound hair under the ribbons (wide dense tile, strands run round the azimuth)
    Rc = np.array(S['bun_r']) * S.get('bun_core', .96); NS, NR = S.get('bun_core_res', (24, 8)); CA = S.get('bun_coil', 0.0)   # bun_coil: the core itself is modelled as a wound coil (two spiral ridges), so the bun has volume without the ribbons
    base = len(CB.v); u0, v0, u1, v1 = hl.tile_rect(TI['dense'][0])
    for i in range(NR + 1):
        la = math.pi * (.5 - .92 * i / NR)
        for j in range(NS + 1):
            az = 2 * math.pi * j / NS - math.pi / 2; nn = bun['bn'] * math.sin(la) + (bun['bx'] * math.cos(az) + bun['by'] * math.sin(az)) * math.cos(la)
            kc = 1.0 + CA * math.cos(2 * az + 9.0 * (math.pi / 2 - la)) * min(1.0, (math.pi / 2 - la) / .5)
            CB.v.append(bun['c'] + (bun['bn'] * Rc[2] * math.sin(la) + (bun['bx'] * Rc[0] * math.cos(az) + bun['by'] * Rc[1] * math.sin(az)) * math.cos(la)) * kc)
            CB.uv.append((u0 + (.12 + .76 * i / NR) * (u1 - u0), v0 + (.5 + .4 * j / NS) * (v1 - v0))); CB.hl.append(1); CB.hn.append(nn)
    for i in range(NR):
        for j in range(NS):
            a_ = base + i * (NS + 1) + j; CB.f.append((a_, a_ + 1, a_ + NS + 2, a_ + NS + 1))
    wr2 = [p for p, _ in RT.sample(S.get('card_wisps', 16), .84, 1.0, azmin=.7, azmax=1.6)] + [p for p, _ in RT.sample(S.get('card_wisps_nape', 12), .86, 1.0, azmin=2.2)]
    for p in wr + wr2:
        g = guide(p, cr, 'wisp'); CB.ribbon(g, cr.uniform(.005, .008), int(cr.choice(TI['n_fly'] + TI['n_wisp'])), 5, cr, nseg=5, across=1, lift_scale=1.0, lift_off=0.0, roll=.5, bow=.05, nblend=.3)
for sgn in (1, -1):     # brow cards: a patch on the brow ridge carrying the baked brow groom
    NS_ = 14; NW_ = 4; base = len(CB.v); e_ = H.eyes[sgn][0]
    for i in range(NS_ + 1):
        s_ = -.10 + 1.25 * i / NS_
        for j in range(NW_ + 1):
            p, nrm = brow_pt(sgn, s_, (j / NW_ * 2 - 1) * BW)
            CB.v.append(p + nrm * .0016); CB.uv.append((i / NS_ * .5, (.125 if sgn > 0 else 0.0) + j / NW_ * .125)); CB.hl.append(4); CB.hn.append(nrm)
    for i in range(NS_):
        for j in range(NW_):
            a_ = base + i * (NW_ + 1) + j; A_ = NW_ + 1; CB.f.append((a_, a_ + A_, a_ + A_ + 1, a_ + 1) if sgn > 0 else (a_, a_ + 1, a_ + A_ + 1, a_ + A_))
hair = CB.build('HairCards'); log('hair card tris', tri_count(hair))
cmat = hl.card_material('MI_%s_PR_Hair' % N, str(PRE) + '_Hair_BC.png', str(PRE) + '_Hair_N.png', str(PRE) + '_Hair_ORM.png', **S.get('card_mat', {}))
hair.data.materials.append(cmat)
if browlash is not None: browlash.data.materials.clear(); browlash.data.materials.append(cmat)
dg_ = bpy.context.evaluated_depsgraph_get()
for o_ in [strands, brows] + extra:
    ed_ = o_.evaluated_get(dg_).data; pp_ = np.empty(len(ed_.points) * 3, np.float32); ed_.attributes['position'].data.foreach_get('vector', pp_); pp_ = pp_.reshape(-1, 3)
    rr_ = np.empty(len(ed_.points), np.float32); ed_.attributes['radius'].data.foreach_get('value', rr_) if ed_.attributes.get('radius') else rr_.fill(-1)
    log('strand object', o_.name, 'curves', len(ed_.curves), 'bbox', pp_.min(0).round(3).tolist(), pp_.max(0).round(3).tolist(), 'radius mean', float(rr_.mean()), 'mats', [m_.name if m_ else None for m_ in ed_.materials])
# ------------------------------------------------------------------ comparison render: strands vs cards, same cameras
if 'strands' in steps or 'cards' in steps:
    P_ = 'T_%s_PR' % N
    sk.data.materials.clear(); sk.data.materials.append(matlib.game_material('MI_%s_PR_Skin' % N, TX / (P_ + '_Skin_BC.png'), TX / (P_ + '_Skin_N.png'), TX / (P_ + '_Skin_ORM.png'), sss=TX / (P_ + '_Skin_SSS.png'), ao_mix=.5))
    ETX, EP_ = (TX, P_) if (TX / (P_ + '_Eyes_BC.png')).exists() else (OUT / 'Mother' / 'Textures', 'T_Mother_PR')      # the maidens wear the Mother's eye maps (cfg/assemble.json tex_override)
    ey = D['Eyes']; ey.data.materials.clear(); ey.data.materials.append(matlib.game_material('MI_%s_PR_Eyes' % N, ETX / (EP_ + '_Eyes_BC.png'), ETX / (EP_ + '_Eyes_N.png'), ETX / (EP_ + '_Eyes_ORM.png'), ao_mix=.8, spec=.8))
    setup_render(samples=int(os.environ.get('HAIR_SPP', 96)), res=(640, 640)); sc.world.node_tree.nodes['Background'].inputs[1].default_value = .085
    sc.cycles.transparent_max_bounces = 64      # at 24 and less a ray through many card layers comes back black
    try: sc.cycles.use_curves = True
    except Exception: pass
    sky = next(n for n in sc.world.node_tree.nodes if n.type == 'TEX_SKY'); hc = H.ctr + np.array([0, 0, .0])
    shots = [('sun2m', (hc[0] + .55, hc[1] - 1.9, hc[2] + .25), 215, False), ('sun05', (hc[0] + .14, hc[1] - .47, hc[2] + .07), 55, False), ('ovc05', (hc[0] - .2, hc[1] - .43, hc[2] + .1), 55, True), ('back', (hc[0] - .45, hc[1] + 1.1, hc[2] + .25), 140, False), ('crown', (hc[0] + .1, hc[1] + .32, hc[2] + .45), 60, False)]
    for x_ in filter(None, os.environ.get('HAIR_SHOTS_X', '').split(';')):      # further looks: name,dx,dy,dz,lens[,target dz] about the head centre
        f_ = x_.split(','); shots.append((f_[0], (hc[0] + float(f_[1]), hc[1] + float(f_[2]), hc[2] + float(f_[3])), float(f_[4]), False) + ((float(f_[5]),) if len(f_) > 5 else ()))
    only = os.environ.get('HAIR_SHOTS'); shots = [s_ for s_ in shots if not only or s_[0] in only.split(',')]
    REV.mkdir(parents=True, exist_ok=True)
    for mode in ('strands', 'cards'):
        if mode not in steps: continue
        for o in [strands, brows] + extra: o.hide_render = mode != 'strands'
        hair.hide_render = mode != 'cards'
        for nm, loc, lens, ovc, *tz_ in shots:
            try: sky.sun_intensity = 0.0 if ovc else 1.0
            except Exception: pass
            sc.world.node_tree.nodes['Background'].inputs[1].default_value = .22 if ovc else .085
            shoot(REV / ('%s_%s_%s.png' % (tag, mode, nm)), loc, tuple(hc + np.array([0, 0, tz_[0] if tz_ else .015])), lens=lens)
    from PIL import Image
    rows = []
    for mode in ('strands', 'cards'):
        fs = [REV / ('%s_%s_%s.png' % (tag, mode, s_[0])) for s_ in shots]
        if all(f.exists() for f in fs): rows.append(np.concatenate([np.asarray(Image.open(f).convert('RGB')) for f in fs], 1))
    if rows: Image.fromarray(np.concatenate(rows, 0)).save(REV / ('%s_hair_compare.png' % tag)); log('compare', REV / ('%s_hair_compare.png' % tag))
if 'save' in steps:
    save_blend(filepath=str(DIR / 'Work' / (n_ + '_groom.blend')), copy=True)
    for o in [strands, scalp, brows] + extra: bpy.data.objects.remove(o, do_unlink=True)
    for nm in ('PR_GroundPlane', 'PR_Cam'):
        if nm in D: bpy.data.objects.remove(D[nm], do_unlink=True)
    final = join([hair] + ([browlash] if browlash is not None else []), 'Hair'); hl.apply_hn(final)
    log('Hair object tris', tri_count(final))
    save_blend(filepath=str(head_blend))
log('HAIR_DONE', N)
