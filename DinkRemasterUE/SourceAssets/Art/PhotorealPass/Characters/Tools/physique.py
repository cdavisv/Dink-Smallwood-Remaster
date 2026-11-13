"""Hero build (physique) fields for the photoreal Dink: how the body and everything worn on it move between three
builds of the same person. The exported mesh is the middle build ("farmhand"); two shape keys reach the ends:

  Physique_Scrawny  the new-game pig farmer: narrow sloping shoulders, thin neck, arms and legs, flat chest
  Physique_Brawny   the late-game hero: broad shoulders, deep chest, thick neck and arms, strong legs, same waist

A build is a displacement FIELD in rest space, not a sculpt: every vertex of every LOD and of every layer (skin,
shirt, jerkin, bracers, boots, pack) is moved by the same smooth function of where it is, so layers keep their
spacing and all LODs get the same build. Offsets are additive (metres along a direction), never a scale, so cloth,
leather and buckle thickness is unchanged. Skin weights only decide which part of the body a vertex belongs to
(garment weights were surface-transferred from the body, so layers agree) and switch the head, hair, hands and feet
off entirely: those do not change with the build.

numpy only; used by dink_07_physique.py (shape keys) and render_physique.py (review)."""
import numpy as np

BUILDS = ('Scrawny', 'Brawny')
KEY = 'Physique_%s'

def _n(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)

def _ss(x, a, b):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def _prof(t, pts):
    xs, ys = zip(*pts); return np.interp(t, xs, ys)

# ---- the design: offsets in metres. Each profile is (position along the part, offset).
# Limbs: position 0..1 from the upper joint to the lower one. 'ang' = (front, back, inner, outer) multipliers.
LIMBS = {
    'Brawny': {
        'upperarm': {'prof': [(0, .008), (.18, .012), (.45, .015), (.8, .009), (1, .006)], 'ang': (1.25, 1.2, .55, 1.0)},
        'lowerarm': {'prof': [(0, .006), (.25, .009), (.7, .004), (1, .0015), (1.1, 0)], 'ang': (1.0, 1.0, 1.0, 1.15)},
        'thigh':    {'prof': [(-.1, .004), (.1, .009), (.35, .015), (.8, .008), (1, .004)], 'ang': (1.3, 1.0, .45, 1.0)},
        'calf':     {'prof': [(0, .004), (.3, .009), (.65, .003), (.9, 0)], 'ang': (.4, 1.4, .8, 1.0)},
    },
    'Scrawny': {
        'upperarm': {'prof': [(0, -.007), (.18, -.010), (.45, -.011), (.8, -.009), (1, -.007)], 'ang': (1.0, 1.0, .8, 1.0)},
        'lowerarm': {'prof': [(0, -.007), (.25, -.008), (.7, -.005), (1, -.0015), (1.1, 0)], 'ang': (1.0, 1.0, 1.0, 1.0)},
        'thigh':    {'prof': [(-.1, -.004), (.1, -.009), (.35, -.013), (.8, -.009), (1, -.006)], 'ang': (1.1, 1.0, .7, 1.0)},
        'calf':     {'prof': [(0, -.005), (.3, -.007), (.65, -.003), (.9, 0)], 'ang': (.6, 1.2, 1.0, 1.0)},
    },
}
# Trunk: height above the ground (m) -> offset to the side, to the front, to the back.
TRUNK = {
    'Brawny': {
        'side':  [(.86, .002), (.93, .004), (1.00, .002), (1.10, .004), (1.22, .013), (1.33, .022), (1.42, .016), (1.48, .007), (1.56, .003)],
        'front': [(.86, 0), (1.02, 0), (1.12, .004), (1.25, .014), (1.34, .024), (1.42, .014), (1.48, .005), (1.56, 0)],
        'back':  [(.86, .003), (.93, .006), (1.02, .003), (1.15, .006), (1.30, .013), (1.42, .016), (1.50, .010), (1.56, .004)],
    },
    'Scrawny': {
        'side':  [(.86, -.003), (.93, -.005), (1.00, -.007), (1.10, -.009), (1.22, -.012), (1.33, -.015), (1.42, -.012), (1.48, -.005), (1.56, -.002)],
        'front': [(.86, 0), (1.02, -.004), (1.12, -.006), (1.25, -.010), (1.34, -.013), (1.42, -.009), (1.48, -.004), (1.56, 0)],
        'back':  [(.86, -.003), (.93, -.006), (1.02, -.004), (1.15, -.005), (1.30, -.008), (1.42, -.008), (1.50, -.005), (1.56, -.002)],
    },
}
# Shoulder cap (deltoid): outward bump around the shoulder joint; 'drop' lowers (-) or raises the shoulder point.
SHOULDER = {'Brawny': {'out': .023, 'radius': .125, 'drop': .003}, 'Scrawny': {'out': -.016, 'radius': .125, 'drop': -.010}}
# Trapezius: the slope from neck to shoulder, lifted (+) or let fall (-); peak at 'x' from the centre line.
TRAPS = {'Brawny': {'up': .014, 'x': .075, 'w': .06}, 'Scrawny': {'up': -.006, 'x': .09, 'w': .06}}
# Neck: radius offset at the base and under the skull.
NECK = {'Brawny': (.010, .005), 'Scrawny': (-.006, -.004)}

ARM = ('upperarm', 'lowerarm'); LEG = ('thigh', 'calf')
CHAIN = {'upperarm': ('upperarm_%s', 'upperarm_twist_01_%s', 'upperarm_twist_02_%s'),
         'lowerarm': ('lowerarm_%s', 'lowerarm_twist_01_%s', 'lowerarm_twist_02_%s'),
         'thigh': ('thigh_%s', 'thigh_twist_01_%s', 'thigh_twist_02_%s'),
         'calf': ('calf_%s', 'calf_twist_01_%s', 'calf_twist_02_%s')}
ENDS = {'upperarm': ('upperarm_%s', 'lowerarm_%s'), 'lowerarm': ('lowerarm_%s', 'hand_%s'),
        'thigh': ('thigh_%s', 'calf_%s'), 'calf': ('calf_%s', 'foot_%s')}
FRONT = np.array([0, -1.0, 0])     # the character faces -Y

def _limb(co, A, B, spec, inward):
    u = _n(B - A); L = np.linalg.norm(B - A); s = (co - A) @ u; t = s / L
    rv = co - (A + np.outer(s, u)); r = np.linalg.norm(rv, axis=1); rh = rv / np.maximum(r, 1e-6)[:, None]
    f = _n(FRONT - (FRONT @ u) * u); i = _n(inward - (inward @ u) * u)
    cf = rh @ f; ci = rh @ i; kf, kb, ki, ko = spec['ang']
    # blend the four side multipliers by squared direction cosines (they sum to about 1 around the limb)
    wf, wb, wi, wo = np.maximum(cf, 0) ** 2, np.maximum(-cf, 0) ** 2, np.maximum(ci, 0) ** 2, np.maximum(-ci, 0) ** 2
    rest = np.maximum(1 - wf - wb - wi - wo, 0)
    m = wf * kf + wb * kb + wi * ki + wo * ko + rest
    return rh * (_prof(t, spec['prof']) * m * _ss(r, .004, .016))[:, None]

def field(co, W, heads, build):
    """co: (N,3) rest positions (m). W: bone name -> (N,) skin weight. heads: bone name -> head position.
    Returns the (N,3) offset of the named build."""
    co = np.asarray(co, float); N = len(co); out = np.zeros((N, 3)); zero = np.zeros(N)
    def w(*names): return sum((W.get(n, zero) for n in names), zero.copy())
    def H(n): return np.asarray(heads[n], float)
    fingers = [b for b in W if any(k in b for k in ('index_', 'middle_', 'ring_', 'pinky_', 'thumb_'))]
    fixed = np.clip(w('head', 'hand_l', 'hand_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r', *fingers), 0, 1)
    limb_w = zero.copy()
    for side, sg in (('l', 1.0), ('r', -1.0)):
        for part in ARM + LEG:
            m = w(*[b % side for b in CHAIN[part]]); limb_w += m
            A, B = H(ENDS[part][0] % side), H(ENDS[part][1] % side)
            inward = np.array([-sg, 0, 0]) if part in LEG else np.array([-sg, 0, -.6])
            out += _limb(co, A, B, LIMBS[build][part], inward) * m[:, None]
    # trunk: radial in the horizontal plane about the spine line, amount by height and by side/front/back
    trunk = np.clip(1 - limb_w - fixed - w('neck_01', 'neck_02'), 0, 1)
    z = co[:, 2]; yc = np.interp(z, [.86, 1.0, 1.2, 1.4, 1.56], [-.005, -.01, -.015, -.005, .01])
    rv = np.stack([co[:, 0], co[:, 1] - yc, zero], 1); r = np.linalg.norm(rv, axis=1); rh = rv / np.maximum(r, 1e-6)[:, None]
    T = TRUNK[build]; c2 = rh[:, 0] ** 2; s2 = 1 - c2
    amt = _prof(z, T['side']) * c2 + np.where(rh[:, 1] < 0, _prof(z, T['front']), _prof(z, T['back'])) * s2
    out += rh * (amt * trunk * _ss(r, .01, .04))[:, None]
    free = np.clip(1 - fixed, 0, 1)
    for side, sg in (('l', 1.0), ('r', -1.0)):
        # shoulder cap: spherical bump about a point a little inside and below the joint, outward and upward only
        S = SHOULDER[build]; J = H('upperarm_%s' % side); C = J + np.array([-sg * .035, 0, -.025])
        d = co - C; dist = np.linalg.norm(co - J, axis=1); dh = d / np.maximum(np.linalg.norm(d, axis=1), 1e-6)[:, None]
        cap = (1 - _ss(dist, .035, S['radius'])) * _ss(dh @ _n([sg * .8, 0, .6]), -.15, .75) * free
        out += dh * (S['out'] * cap)[:, None]; out[:, 2] += S['drop'] * cap
        # trapezius: lift of the neck-to-shoulder slope
        Tz = TRAPS[build]; x = co[:, 0] * sg
        bump = np.exp(-((x - Tz['x']) / Tz['w']) ** 2) * _ss(z, 1.40, 1.47) * (1 - _ss(z, 1.56, 1.60)) * _ss(x, .0, .03)
        out[:, 2] += Tz['up'] * bump * free * np.clip(1 - limb_w, 0, 1)
    # neck: radial about the neck axis, fading into the fixed skull
    A, B = H('neck_01'), H('head'); u = _n(B - A); s = (co - A) @ u; t = s / np.linalg.norm(B - A)
    rv = co - (A + np.outer(s, u)); r = np.linalg.norm(rv, axis=1); rh = rv / np.maximum(r, 1e-6)[:, None]
    n0, n1 = NECK[build]
    out += rh * (np.interp(t, [-.3, 0, 1, 1.2], [n0 * .5, n0, n1, 0]) * w('neck_01', 'neck_02') * _ss(r, .005, .02))[:, None]
    return out

def weights_of(ob):
    """Blender mesh object -> {bone: (N,) weights}."""
    N = len(ob.data.vertices); names = [g.name for g in ob.vertex_groups]; W = {n: np.zeros(N) for n in names}
    for v in ob.data.vertices:
        for g in v.groups: W[names[g.group]][v.index] = g.weight
    return W

def girth(co, mask, origin, axis, half=.006):
    """Convex-hull perimeter (m) of the vertices of `mask` within `half` of the plane through origin normal to axis."""
    u = _n(axis); s = (co - origin) @ u; sel = mask & (np.abs(s) < half)
    if sel.sum() < 8: return 0.0
    a = _n(np.cross(u, [0, 0, 1.0]) if abs(u[2]) < .9 else np.cross(u, [1.0, 0, 0])); b = np.cross(u, a)
    P = np.stack([(co[sel] - origin) @ a, (co[sel] - origin) @ b], 1); P = P[np.lexsort((P[:, 1], P[:, 0]))]
    def half_hull(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0: h.pop()
            h.append(p)
        return h
    hull = half_hull(P)[:-1] + half_hull(P[::-1])[:-1]; hull = np.array(hull)
    return float(np.linalg.norm(hull - np.roll(hull, -1, 0), axis=1).sum())
