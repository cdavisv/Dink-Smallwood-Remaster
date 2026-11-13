"""Character kit for the civilian NPC families, built on the CC0 MakeHuman base mesh (mhlib).

A Person is: the base body morphed to a build (male, stout, child ...), a skin from the bundled MakeHuman diffuse
map, fitted eyes / brows / lashes / hair (through the .mhclo bindings, so they follow the morph), garments cut from
the base mesh's own clothing helpers and loosened, optional authored head gear, and a skeleton with the project
humanoid bone names made from the base mesh's joint markers. Weights come from bone heat on the whole body and are
copied to every other part from the nearest body vertex.
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Matrix, Vector, kdtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import mhlib as M
from pplib import NT, smoothstep, fbm
from PIL import Image


# ---------------------------------------------------------------------------------------------- .mhclo fitting
def fit_mhclo(relpath, Vb, root=None):
    """positions (Blender space) of a bundled part fitted to the morphed base vertices Vb through its .mhclo bindings"""
    Vm = np.stack([Vb[:, 0], Vb[:, 2], -Vb[:, 1]], 1) * 10.0; sc = {}; rows = []; on = False
    for line in open(os.path.join(root or M.MH, relpath), errors='ignore'):
        p = line.split()
        if not p:
            continue
        if p[0] in ('x_scale', 'y_scale', 'z_scale'):
            ax = 'xyz'.index(p[0][0]); sc[ax] = abs(Vm[int(p[1])][ax] - Vm[int(p[2])][ax]) / float(p[3]); continue
        if p[0] == 'verts':
            on = True; continue
        if on:
            try:
                float(p[0])
            except ValueError:
                if p[0] in ('delete_verts', 'weights'):
                    break
                continue
            rows.append(p)
    out = np.zeros((len(rows), 3)); s3 = np.array([sc.get(0, 1.0), sc.get(1, 1.0), sc.get(2, 1.0)])
    for i, p in enumerate(rows):
        if len(p) == 1:
            out[i] = Vm[int(p[0])]
        else:
            v = [int(p[0]), int(p[1]), int(p[2])]; w = [float(p[3]), float(p[4]), float(p[5])]; d = np.array([float(p[6]), float(p[7]), float(p[8])]); out[i] = w[0] * Vm[v[0]] + w[1] * Vm[v[1]] + w[2] * Vm[v[2]] + d * s3
    return np.stack([out[:, 0], -out[:, 2], out[:, 1]], 1) * 0.1


def fitted_part(name, folder, stem, Vb, c=None, root=None, obj=None):
    """object for a bundled part (its OBJ gives faces and UVs, the .mhclo gives the fitted positions)"""
    V, VT, F = M.parse_obj(os.path.join(root or M.MH, folder, (obj or stem) + '.obj')); P = fit_mhclo(os.path.join(folder, stem + '.mhclo'), Vb, root)
    if len(P) != len(V):
        raise RuntimeError('%s: %d bound vertices, %d in the OBJ' % (stem, len(P), len(V)))
    ob = L.new_obj(name, P, [vi for _, vi, _ in F], c); uv = ob.data.uv_layers.new(name='UVMap')
    for poly, (_, vi, ti) in zip(ob.data.polygons, F):
        for li, t in zip(poly.loop_indices, ti):
            uv.data[li].uv = VT[t] if t >= 0 else (0.0, 0.0)
    return ob


# ---------------------------------------------------------------------------------------------- morphs
def scale_region(V, w, pivot, s):
    """P += w * (S - 1) * (P - pivot), S per axis"""
    s = np.array(s if not np.isscalar(s) else (s, s, s), float); return V + w[:, None] * (s - 1.0) * (V - np.array(pivot, float))


def morph(V, J, male=0.0, girth=1.0, belly=0.0, height=1.0, head=1.0, legs=1.0, shoulders=1.0, face=None, chest=0.0, stoop=0.0, limbs=1.0):
    """build of the body. Applied to every vertex of the base mesh (body, helpers, joint markers), so everything stays consistent."""
    x, y, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x); torso = (1 - smoothstep(0.15, 0.24, ax)) * smoothstep(0.80, 0.88, z) * (1 - smoothstep(1.38, 1.44, z))
    if male:
        # flatten the chest, square the shoulders, thicken waist and neck, narrow the hips, strengthen the jaw and nose
        br = np.exp(-(((ax - 0.085) / 0.07) ** 2 + ((z - 1.235) / 0.075) ** 2)) * smoothstep(-0.04, -0.09, y); V = V.copy(); V[:, 1] += br * male * 0.042; V[:, 2] += br * male * 0.006
        arm = np.maximum(smoothstep(1.12, 1.25, z), smoothstep(0.27, 0.31, ax) * smoothstep(0.9, 0.98, z)) * smoothstep(0.03, 0.17, ax) * (1 - smoothstep(1.40, 1.47, z) * (ax < 0.12)); V[:, 0] += np.sign(x) * 0.024 * male * arm
        hipm = np.exp(-((z - 0.90) / 0.11) ** 2) * (ax < 0.27); V = scale_region(V, male * hipm, (0, 0, 0.9), (0.90, 0.96, 1.0)); x, y, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
        V = scale_region(V, male * torso * np.exp(-((z - 1.07) / 0.1) ** 2), (0, -0.01, 1.07), (1.12, 1.14, 1.0)); pass
        nk = np.exp(-((z - 1.44) / 0.04) ** 2) * (ax < 0.09); V = scale_region(V, male * nk, (0, -0.01, 1.44), (1.14, 1.12, 1.0))
        jaw = np.exp(-((z - 1.455) / 0.03) ** 2) * (z > 1.40) * smoothstep(0.02, -0.06, y); V = scale_region(V, male * jaw, (0, -0.05, 1.455), (1.1, 1.04, 1.0))
        nose = np.exp(-(((x) / 0.02) ** 2 + ((z - 1.525) / 0.022) ** 2 + ((y + 0.155) / 0.03) ** 2)); V = scale_region(V, male * nose, (0, -0.125, 1.53), (1.2, 1.3, 1.15))
        brow = np.exp(-(((ax - 0.03) / 0.035) ** 2 + ((z - 1.572) / 0.012) ** 2)) * smoothstep(-0.09, -0.12, y); V[:, 1] -= brow * male * 0.004
    if face:
        V = face(V)
    x, y, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x); torso = (1 - smoothstep(0.15, 0.24, ax)) * smoothstep(0.80, 0.88, z) * (1 - smoothstep(1.38, 1.44, z))
    if girth != 1.0:
        V = scale_region(V, torso, (0, -0.01, 1.1), (girth, girth, 1.0)); limb = smoothstep(0.0, 0.1, z) * (1 - smoothstep(0.82, 0.9, z))          # legs thicken about their own axes
        for sx in (1, -1):
            m = limb * (x * sx > 0); V = scale_region(V, m, (sx * 0.16, -0.02, 0.5), (1 + (girth - 1) * 0.6, 1 + (girth - 1) * 0.6, 1.0))
    if belly:
        bl = np.exp(-(((x) / 0.14) ** 2 + ((z - 1.06) / 0.11) ** 2)) * smoothstep(0.0, -0.06, V[:, 1]); V = V.copy(); V[:, 1] -= bl * belly
    if shoulders != 1.0:
        V = scale_region(V, smoothstep(1.2, 1.3, V[:, 2]) * (1 - smoothstep(1.42, 1.46, V[:, 2])), (0, 0, 1.33), (shoulders, 1.0, 1.0))
    if legs != 1.0:                                        # shorter or longer legs: everything from the hips down scales in z, the rest follows
        hip = 0.87; lo = V[:, 2] < hip; V = V.copy(); V[lo, 2] = V[lo, 2] * legs; V[~lo, 2] -= hip * (1 - legs)
    if head != 1.0:
        nz = float(V[(np.abs(V[:, 0]) < 0.05) & (V[:, 2] > 1.2)][:, 2].min()) if False else None
        zc = 1.44 - (0.87 * (1 - legs) if legs != 1.0 else 0.0); V = scale_region(V, smoothstep(zc - 0.03, zc + 0.03, V[:, 2]) * (np.abs(V[:, 0]) < 0.14), (0, -0.02, zc), head)
    if chest and not male:                                  # flat chest (children)
        x, y, z = V[:, 0], V[:, 1], V[:, 2]; br = np.exp(-(((np.abs(x) - 0.085) / 0.07) ** 2 + ((z - 1.235) / 0.075) ** 2)) * smoothstep(-0.04, -0.09, y); V = V.copy(); V[:, 1] += br * chest * 0.042
    if limbs != 1.0:                                        # thinner or thicker arms and lower legs (about their own axes: cheap, by distance from the limb line)
        for sd in ('l', 'r'):
            for a_, b_ in (('shoulder', 'elbow'), ('elbow', 'hand'), ('knee', 'ankle')):
                pa = J['%s-%s' % (sd, a_)]; pb = J['%s-%s' % (sd, b_)]; ab = pb - pa; t_ = np.clip(((V - pa) @ ab) / (ab @ ab), 0, 1); C_ = pa + t_[:, None] * ab; d_ = V - C_; dist = np.linalg.norm(d_, axis=1)
                w_ = (1 - smoothstep(0.05, 0.075, dist)) * np.sin(np.pi * t_) ** 0.5; V = V + w_[:, None] * (limbs - 1.0) * d_
    if stoop:                                               # bent back: the upper body curls forward, the head lifts back up to look ahead
        z = V[:, 2]; arm = (np.abs(V[:, 0]) > 0.2) & (z > 0.95); w = np.where(arm, 1.0, smoothstep(1.0, 1.42, z)); a = np.radians(stoop) * w; py, pz = -0.01, 1.0; dy = V[:, 1] - py; dz = V[:, 2] - pz
        V = V.copy(); V[:, 1] = py + dy * np.cos(a) - dz * np.sin(a); V[:, 2] = pz + dy * np.sin(a) + dz * np.cos(a)
        hd = smoothstep(1.40, 1.46, z) * (~arm); a2 = -np.radians(stoop) * 0.6 * hd; piv = np.array([0.0, py - (1.43 - pz) * np.sin(np.radians(stoop)), pz + (1.43 - pz) * np.cos(np.radians(stoop))]); dy = V[:, 1] - piv[1]; dz = V[:, 2] - piv[2]
        V[:, 1] = piv[1] + dy * np.cos(a2) - dz * np.sin(a2); V[:, 2] = piv[2] + dy * np.sin(a2) + dz * np.cos(a2)
    if height != 1.0:
        V = V * height
    return V


# ---------------------------------------------------------------------------------------------- materials for the dense sources
def skin_mat(name, tex, tint=(1.0, 1.0, 1.0), age=0.0, beard=None, grime=0.0, zscale=1.0, pale=0.0):
    """MakeHuman skin diffuse with pores; age adds blotches and creases; beard = (colour, amount, jaw z, mouth z) paints stubble or a short beard round the jaw and mouth"""
    t = NT(name); im = t.image(tex, 'sRGB', t.uv); n = t.noise(900 / zscale, 3, 0.6); n2 = t.noise(60 / zscale, 4, 0.6); n3 = t.noise(9 / zscale, 4, 0.6); base = t.mix(1.0, im.outputs[0], tint, blend='MULTIPLY')
    if pale:
        base = t.hsv(base, sat=1.0 - 0.3 * pale, v=1.0 + 0.1 * pale)
    if age:
        spots = t.ramp(t.noise(160 / zscale, 3, 0.7), [(0.66, 0.0), (0.72, 1.0)]); base = t.mix(t.math('MULTIPLY', spots, 0.35 * age), base, (0.30, 0.17, 0.10)); base = t.hsv(base, sat=1.0 - 0.18 * age, v=1.0 - 0.06 * age)
        crease = t.ramp(t.voronoi(260 / zscale, feature='DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.06, 0.0)]); base = t.mix(t.math('MULTIPLY', crease, 0.22 * age), base, (0.22, 0.11, 0.08))
    if beard:
        col, amt, zj, zm = beard; sp = t.sep(t.obj); m = t.math('MULTIPLY', t.maprange(sp[2], zm + 0.012, zm - 0.004, 0.0, 1.0, interp='SMOOTHSTEP'), t.maprange(sp[2], zj - 0.035, zj - 0.01, 0.0, 1.0, interp='SMOOTHSTEP'))
        m = t.math('MULTIPLY', m, t.maprange(sp[1], 0.02, -0.03, 0.0, 1.0)); lip = t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', sp[2], zm - 0.012)), [(0.006, 1.0), (0.011, 0.0)]), t.ramp(t.math('ABSOLUTE', sp[0]), [(0.02, 1.0), (0.028, 0.0)]))
        m = t.math('MULTIPLY', t.math('MULTIPLY', m, t.math('SUBTRACT', 1.0, lip)), t.ramp(t.noise(1500 / zscale, 2, 0.5), [(0.3, 0.55), (0.6, 1.0)])); base = t.mix(t.math('MULTIPLY', m, amt), base, col)
    if grime:
        base = t.mix(t.math('MULTIPLY', t.ramp(n3, [(0.45, 0.0), (0.7, 1.0)]), grime), base, (0.10, 0.075, 0.05))
    h = t.math('ADD', t.math('MULTIPLY', n, 0.5), t.math('MULTIPLY', t.ramp(t.voronoi(700 / zscale, feature='DISTANCE_TO_EDGE'), [(0.0, 0.0), (0.2, 1.0)]), 0.5))
    if age:
        h = t.math('ADD', h, t.math('MULTIPLY', t.ramp(t.voronoi(260 / zscale, feature='DISTANCE_TO_EDGE'), [(0.0, 0.0), (0.08, 1.0)]), 1.5 * age))
    t.set(base=base, rough=t.mixf(n2, 0.42, 0.58), normal=t.bump(h, 0.12, 0.0004), sss=0.12, sss_radius=(1.0, 0.3, 0.15), sss_scale=0.006); return t.mat


def cloth_mat(name, col, weave=1.0, worn=0.5, dirt=0.4, hem_z=None, rough=0.86, trim=None, pattern=None, sheen=0.3):
    """woven wool or linen: thread-scale weave, uneven dye, wear on raised folds, dirt towards the hem; trim = (z0, z1, colour) band; pattern = (colour, scale, amount) scattered motif"""
    t = NT(name); sp = t.sep(t.obj); n = t.noise(5, 5, 0.65); n2 = t.noise(60, 4, 0.6); ang = t.math('ARCTAN2', sp[1], sp[0])
    wv = t.math('MULTIPLY', t.math('SINE', t.math('MULTIPLY', sp[2], 2600.0)), t.math('SINE', t.math('MULTIPLY', t.math('ADD', sp[0], sp[1]), 1900.0)))
    base = t.mix(n, tuple(v * 0.72 for v in col), tuple(min(1.0, v * 1.22) for v in col)); base = t.hsv(base, v=t.maprange(n2, 0.2, 0.8, 0.9, 1.1))
    stain = t.ramp(t.noise(2.2, 5, 0.7, distortion=0.8), [(0.5, 0.0), (0.72, 1.0)]); base = t.mix(t.math('MULTIPLY', stain, 0.35 + 0.4 * dirt), base, tuple(v * 0.45 + 0.012 for v in col))          # blotches of old dirt and damp
    fade = t.ramp(t.noise(1.3, 4, 0.6), [(0.45, 0.0), (0.75, 1.0)]); base = t.mix(t.math('MULTIPLY', fade, 0.3 * worn), base, tuple(min(1.0, (v * 1.5 + 0.03) * 0.8 + 0.2 * max(col)) for v in col))  # sun-faded patches
    if pattern:
        pc, ps, pa = pattern; st = t.ramp(t.voronoi(ps, feature='F1'), [(0.0, 1.0), (0.16, 0.0)]); base = t.mix(t.math('MULTIPLY', st, pa), base, pc)
    if trim:
        z0, z1, tc = trim; tm = t.math('MULTIPLY', t.maprange(sp[2], z0, z0 + 0.004, 0.0, 1.0), t.maprange(sp[2], z1 - 0.004, z1, 1.0, 0.0)); base = t.mix(tm, base, tc)
    wear = t.math('MULTIPLY', t.ramp(t.pointiness, [(0.5, 0.0), (0.58, 1.0)]), worn); base = t.mix(t.math('MULTIPLY', wear, 0.4), base, tuple(min(1.0, v * 1.7 + 0.05) for v in col))
    if hem_z is not None:
        dz = t.maprange(t.math('ADD', sp[2], t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.25)), hem_z, hem_z + 0.3, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', dz, dirt), base, (0.075, 0.058, 0.04))
    ao = t.ao(0.04, 10); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.85, 0.0)]), 0.6), base, tuple(v * 0.2 for v in col))
    t.set(base=base, rough=t.mixf(n2, rough - 0.06, min(1.0, rough + 0.08)), normal=t.bump(t.math('ADD', t.math('MULTIPLY', wv, 0.5 * weave), t.math('MULTIPLY', n2, 0.5)), 0.45, 0.0008), sheen=sheen); return t.mat


def leather_mat(name, col, rough=0.5):
    t = NT(name); n = t.noise(50, 4, 0.6); cr = t.voronoi(260, feature='DISTANCE_TO_EDGE'); base = t.mix(n, tuple(v * 0.6 for v in col), tuple(min(1, v * 1.4) for v in col)); base = t.mix(t.ramp(cr, [(0.0, 0.6), (0.07, 0.0)]), base, tuple(v * 0.3 for v in col))
    wear = t.ramp(t.pointiness, [(0.5, 0.0), (0.58, 1.0)]); base = t.mix(t.math('MULTIPLY', wear, 0.5), base, tuple(min(1, v * 2.2 + 0.04) for v in col)); ao = t.ao(0.03, 8); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.9, 0.0)]), 0.6), base, (0.02, 0.014, 0.01))
    t.set(base=base, rough=t.mixf(n, rough - 0.1, rough + 0.15), normal=t.bump(t.ramp(cr, [(0.0, 0.0), (0.12, 1.0)]), 0.4, 0.0008)); return t.mat


def hairmass_mat(name, col, axis=2):
    """solid hair mass (beards, fur trim): strands running along `axis`, lighter tips, dark gaps"""
    t = NT(name); sc = [220.0, 220.0, 220.0]; sc[axis] = 9.0; st = t.noise(1.0, 4, 0.65, vec=t.mapping(scale=tuple(sc)), distortion=0.6); n = t.noise(14, 4, 0.6)
    base = t.ramp(st, [(0.3, tuple(v * 0.35 for v in col)), (0.5, col), (0.75, tuple(min(1.0, v * 1.5 + 0.03) for v in col))]); base = t.hsv(base, v=t.maprange(n, 0.2, 0.8, 0.8, 1.15)); ao = t.ao(0.03, 8); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.9, 0.0)]), 0.6), base, tuple(v * 0.2 for v in col))
    t.set(base=base, rough=t.mixf(st, 0.45, 0.7), normal=t.bump(st, 0.9, 0.0015), sheen=0.4); return t.mat


def wood_mat(name, col=(0.24, 0.15, 0.08), axis=2, rough=0.6):
    t = NT(name); sc = [60.0, 60.0, 60.0]; sc[axis] = 3.0; g = t.noise(1.0, 5, 0.6, vec=t.mapping(scale=tuple(sc)), distortion=1.2); n = t.noise(25, 4, 0.6); ao = t.ao(0.03, 8)
    base = t.ramp(g, [(0.3, tuple(v * 0.5 for v in col)), (0.55, col), (0.8, tuple(min(1.0, v * 1.5) for v in col))]); base = t.mix(t.math('MULTIPLY', t.ramp(t.pointiness, [(0.5, 0.0), (0.56, 1.0)]), 0.4), base, tuple(min(1.0, v * 2.0 + 0.05) for v in col))
    base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.9, 0.0)]), 0.6), base, (0.03, 0.02, 0.012)); t.set(base=base, rough=t.mixf(n, rough - 0.12, rough + 0.12), normal=t.bump(g, 0.5, 0.001)); return t.mat


def straw_mat(name, col=(0.62, 0.48, 0.20)):
    """plaited straw: concentric braid ridges about the Z axis with cross strands"""
    t = NT(name); sp = t.sep(t.obj); r = t.math('SQRT', t.math('ADD', t.math('MULTIPLY', sp[0], sp[0]), t.math('MULTIPLY', sp[1], sp[1]))); th = t.math('ARCTAN2', sp[1], sp[0]); d = t.math('ADD', r, t.math('MULTIPLY', sp[2], 0.9))
    braid = t.math('SINE', t.math('MULTIPLY', d, 520.0)); cross = t.math('SINE', t.math('ADD', t.math('MULTIPLY', th, 90.0), t.math('MULTIPLY', d, 260.0))); h = t.math('ADD', t.math('MULTIPLY', braid, 0.6), t.math('MULTIPLY', t.math('MULTIPLY', cross, braid), 0.5))
    n = t.noise(40, 4, 0.6); base = t.mix(t.maprange(h, -1, 1, 0, 1), tuple(v * 0.45 for v in col), tuple(min(1.0, v * 1.25) for v in col)); base = t.hsv(base, v=t.maprange(n, 0.2, 0.8, 0.75, 1.15)); ao = t.ao(0.03, 8)
    base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.9, 0.0)]), 0.5), base, (0.10, 0.07, 0.03)); t.set(base=base, rough=0.62, normal=t.bump(h, 0.8, 0.0012)); return t.mat


def gold_mat(name='gold'):
    t = NT(name); n = t.noise(30, 5, 0.65); pit = t.noise(400, 3, 0.6); ao = t.ao(0.01, 8); base = t.mix(n, (0.72, 0.42, 0.08), (0.95, 0.62, 0.16)); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.9, 0.0)]), 0.75), base, (0.10, 0.06, 0.02))
    t.set(base=base, rough=t.mixf(pit, 0.2, 0.42), metal=1.0, normal=t.bump(pit, 0.2, 0.0005)); return t.mat


def fold_fn(k=1.0, belt=None, gather=0.006, drape=0.0055, fine=0.0015, sleeves=0.0):
    """displacement for the dense cloth sources: ridged vertical drape, fine wrinkles, gathers above and below a belt, creases round the elbows"""
    def f(Q):
        d = drape * k * ((1 - np.abs(2 * fbm(Q * np.array([1.0, 1.0, 0.22]), 3, 13 / k, 3) - 1)) - 0.5) + fine * k * fbm(Q, 5, 60 / k, 2)
        if belt is not None:
            th = np.arctan2(Q[:, 1] + 0.01 * k, Q[:, 0]); g = np.exp(-np.abs(Q[:, 2] - belt) / (0.09 * k)); d = d + gather * k * g * np.sin(th * 24 + 5 * fbm(Q, 7, 6 / k, 2))
        if sleeves:
            ax = np.abs(Q[:, 0]); m = smoothstep(0.2 * k, 0.24 * k, ax) * (0.35 + np.exp(-((ax - 0.31 * k) / (0.06 * k)) ** 2)); d = d + sleeves * k * m * np.sin(ax * 150 / k + 6 * fbm(Q, 9, 9 / k, 2))
        return d
    return f


def rim(ob, t):
    """turn the open edges of a single-sheet game mesh inwards by t (a hem with thickness, no inner shell); the rim faces get their own UV islands"""
    for i in range(3):
        ob.data.materials.append(bpy.data.materials.get('rim_tmp_%d' % i) or bpy.data.materials.new('rim_tmp_%d' % i))
    L.mod(ob, 'SOLIDIFY', thickness=t, offset=-1.0, material_offset=1, material_offset_rim=2); L.apply_mods(ob)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == 1], context='FACES'); bm.to_mesh(ob.data); bm.free(); ob.data.update()
    L.activate(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='FACE'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT'); n = 0
    for p_ in ob.data.polygons:
        p_.select = p_.material_index == 2; n += p_.select
    if n:
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.002); bpy.ops.object.mode_set(mode='OBJECT')
    ob.data.materials.clear(); L.fix_normals(ob); return ob


# ---------------------------------------------------------------------------------------------- the person
class Person:
    def __init__(s, name, spec):
        s.name = name; s.spec = spec; s.B = M.Base(); B = s.B; s.V = morph(B.V.copy(), B.J, **spec.get('build', {})); jv = {}
        for g, vi, ti in B.F:
            if g.startswith('joint-'):
                jv.setdefault(g[6:], set()).update(vi)
        s.J = {k: s.V[sorted(v)].mean(0) for k, v in jv.items()}; s.k = float(spec.get('build', {}).get('height', 1.0)); s.hi = L.coll('Source_Hi'); s.lo = L.coll('Game'); s.garments = []; s.rigid = {}; s.cards = []; s.under = set()
        s.body, s.body_orig = B.mesh('body', {'body'}, s.lo, V=s.V); s.zJ = lambda n: float(s.J[n][2])

    # -- garments ---------------------------------------------------------------------------------
    def piece(s, name, group, keep, offset, mat, smooth=2, thick=0.004, folds=None, post=None, under=False):
        """a garment cut from a helper group of the base mesh: faces whose centre passes keep(P), pushed out along the normals by offset (metres at k = 1; a number
        or fn(P) -> array), then post(P) -> P. The game mesh keeps the helper's own UV island and gets a turned hem (rim); the dense source is a closed shell with folds."""
        k = s.k; ob, orig = s.B.mesh(name, {group}, s.lo, V=s.V, keep=keep)
        if len(ob.data.polygons) == 0:
            raise RuntimeError('garment %s is empty' % name)
        P = L.co(ob); N = L.vnormals(ob); off = offset(P) if callable(offset) else np.full(len(P), float(offset)); P = P + N * (off * k)[:, None]
        if post:
            P = post(P)
        L.set_co(ob, P)
        if smooth:
            L.mod(ob, 'SMOOTH', factor=0.5, iterations=smooth); L.apply_mods(ob)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
        if under:
            s.under.add(name)
        return s._finish_sheet(ob, name, mat, thick, folds)

    def _finish_sheet(s, ob, name, mat, thick, folds, sub=2):
        k = s.k; hi = L.dup(ob, name + '_hi', s.hi); L.subsurf(hi, sub); L.displace_np(hi, folds or fold_fn(k))            # folds first, thickness after: both faces of the cloth follow the fold
        L.mod(hi, 'SOLIDIFY', thickness=thick * k, offset=-1.0); L.apply_mods(hi); L.fix_normals(hi); hi.data.materials.append(mat); rim(ob, thick * k); s.garments.append((ob, hi)); return ob

    def skirt(s, name, z_top, z_hem, mat, flare=1.15, ripple=(10, 0.012), margin=0.014, top=None, thick=0.004, folds=None, open_front=0.0, lift=0.0):
        """hanging cloth tube from z_top to z_hem: starts on the outline of the garments `top` at z_top (or the body), widens by flare, never comes closer to the
        legs than margin, ripples into vertical folds towards the hem. open_front = half-angle (radians) left open at the front (coats, cloaks)."""
        k = s.k; cy = float(s.J['pelvis'][1]); nb = 72; ang = -math.pi + (np.arange(nb) + 0.5) * 2 * math.pi / nb
        bodyv = sorted({i for g, vi, ti in s.B.F if g == 'body' for i in vi}); BP = s.V[bodyv]; BP = BP[~s.arm_mask(BP)]

        def env(pts, z, band):
            q = pts[np.abs(pts[:, 2] - z) < band * k]; R = np.full(nb, np.nan)
            if len(q):
                th = np.arctan2(q[:, 1] - cy, q[:, 0]); rr = np.hypot(q[:, 0], q[:, 1] - cy); bi = np.clip(((th + math.pi) / (2 * math.pi) * nb).astype(int), 0, nb - 1)
                for i in range(nb):
                    m = bi == i
                    if m.any():
                        R[i] = rr[m].max()
            if np.isnan(R).all():
                return np.zeros(nb)
            idx = np.arange(nb); good = ~np.isnan(R); R = np.interp(idx, np.r_[idx[good] - nb, idx[good], idx[good] + nb], np.r_[R[good], R[good], R[good]])
            R = np.max([np.roll(R, j) for j in range(-5, 6)], 0)                  # tent over the gap between the legs
            for _ in range(4):
                R = (np.roll(R, 1) + 2 * R + np.roll(R, -1)) / 4
            return R
        TP = np.vstack([L.co(o) for o in top]) if top else BP; TP = TP[~s.arm_mask(TP)]; R0 = env(TP, z_top, 0.03) + 0.003 * k

        def grid(nu, nv):
            Vv = []; F = []; UV = []; Rprev = R0.copy(); circ = 2 * math.pi * float(R0.mean()); rowsR = []
            for j in range(nv):
                t = j / (nv - 1); z = z_top + (z_hem - z_top) * t; Rb = env(BP, z, 0.035) + margin * k; R = np.maximum(np.maximum(R0 * (1 + (flare - 1) * t), Rb), Rprev); Rprev = R; rowsR.append(R)
            for j in range(nv):
                t = j / (nv - 1); z = z_top + (z_hem - z_top) * t; R = rowsR[j]
                for i in range(nu + (1 if open_front else 0)):
                    u = i / nu; a = (-math.pi / 2 + open_front + u * (2 * math.pi - 2 * open_front)) if open_front else (-math.pi + u * 2 * math.pi)
                    r = float(np.interp(((a + math.pi) % (2 * math.pi)) / (2 * math.pi) * nb - 0.5, np.arange(-1, nb + 1), np.r_[R[-1], R, R[0]]))
                    r += ripple[1] * k * (t ** 0.7) * math.sin(a * ripple[0] + 2.0 * math.sin(a * 3 + 1.0)); zz = z + lift * k * t * (0.5 + 0.5 * math.sin(a * 2.0 + 0.6)) * 0.0
                    Vv.append((r * math.cos(a), cy + r * math.sin(a), zz)); UV.append((u * circ, -t * abs(z_hem - z_top)))
            ncol = nu + (1 if open_front else 0)
            for j in range(nv - 1):
                for i in range(nu):
                    i1 = (i + 1) % ncol if not open_front else i + 1; F.append((j * ncol + i, (j + 1) * ncol + i, (j + 1) * ncol + i1, j * ncol + i1))
            return Vv, F, UV, ncol
        Vv, F, UV, ncol = grid(40, 12); ob = L.new_obj(name, Vv, F, s.lo); uv = ob.data.uv_layers.new(name='UVMap'); circ = max(u for u, v in UV) * (41 / 40 if not open_front else 1.0); hgt = abs(z_hem - z_top); sc = 1.0 / max(circ, hgt)
        for poly in ob.data.polygons:
            vs = list(poly.vertices); wrap = (not open_front) and any(v % ncol == 0 for v in vs) and any(v % ncol == ncol - 1 for v in vs)
            for li, v in zip(poly.loop_indices, vs):
                u, w = UV[v]
                if wrap and v % ncol == 0:
                    u = UV[ncol - 1][0] + UV[1][0]
                uv.data[li].uv = (u * sc, 1.0 + w * sc)
        L.fix_normals(ob); return s._finish_sheet(ob, name, mat, thick, folds or fold_fn(k, drape=0.006), sub=3)

    def solid(s, lo, hi, mat=None, bone=None):
        """an authored part (belt buckle, hat, beard, crown, staff ...): lo = game mesh, hi = dense source (already carrying its materials when mat is None);
        bone = follow that bone rigidly (head gear, things held in a hand); otherwise it is skinned like a garment"""
        L.link(lo, s.lo); L.link(hi, s.hi)
        if not lo.data.uv_layers:
            L.smart_uv(lo, angle=66, margin=0.004)
        if mat is not None:
            hi.data.materials.append(mat)
        s.garments.append((lo, hi))
        if bone:
            s.rigid[lo.name] = bone
        return lo

    def arm_mask(s, Q):
        """True for points that belong to an arm or hand rather than the trunk and legs (nearest limb axis, scaled by limb thickness)"""
        J = s.J; k = s.k; da = np.full(len(Q), 1e9); db = np.full(len(Q), 1e9)
        for sd in 'lr':
            sh, el, ha = J[sd + '-shoulder'], J[sd + '-elbow'], J[sd + '-hand']; tip = ha + (ha - el) / np.linalg.norm(ha - el) * 0.2 * k
            for a_, b_ in ((sh, el), (el, ha), (ha, tip)):
                da = np.minimum(da, C._seg_dist(Q, a_, b_))
            ul, kn, an = J[sd + '-upper-leg'], J[sd + '-knee'], J[sd + '-ankle']
            for a_, b_ in ((ul, kn), (kn, an)):
                db = np.minimum(db, C._seg_dist(Q, a_, b_))
        db = np.minimum(db, C._seg_dist(Q, J['pelvis'], J['spine-1'])); db = np.minimum(db, C._seg_dist(Q, J['spine-1'], J['head'])); return da / 0.055 < db / 0.13

    def hand_side(s, P, margin=0.0):
        """+1 / -1 when P lies in the left / right hand (past the wrist, less margin), else 0"""
        for sx, sd in ((1, 'l'), (-1, 'r')):
            w = s.J[sd + '-hand']; e = s.J[sd + '-elbow']; d = (w - e) / np.linalg.norm(w - e)
            if P[0] * sx > 0 and float((P - w) @ d) > -margin * s.k and abs(P[0]) > 0.25 * s.k:
                return sx
        return 0

    def boots(s, top_z, mat, sole=0.008):
        """soft leather boots: the leg and foot below top_z grown by a centimetre so the toes fuse, remeshed to one skin, lifted on a sole, rolled cuff"""
        k = s.k; out = []
        for sx, sd in ((1, 'l'), (-1, 'r')):
            hi, _ = s.B.mesh('boot_%s_hi' % sd, {'body'}, s.hi, V=s.V, keep=lambda P: P[2] < top_z and P[0] * sx > 0); P = L.co(hi); N = L.vnormals(hi); L.set_co(hi, P + N * 0.010 * k)
            bm = bmesh.new(); bm.from_mesh(hi.data); bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0); bm.to_mesh(hi.data); bm.free()
            for l_ in list(hi.data.uv_layers):
                hi.data.uv_layers.remove(l_)
            L.mod(hi, 'REMESH', mode='VOXEL', voxel_size=0.0035 * k, adaptivity=0.0, use_smooth_shade=True); L.apply_mods(hi); L.mod(hi, 'SMOOTH', factor=0.6, iterations=8); L.apply_mods(hi)
            P = L.co(hi); P[:, 2] += sole * k - float(P[:, 2].min()); flat = P[:, 2] < (sole + 0.010) * k; P[flat, 2] = sole * k + (P[flat, 2] - sole * k) * 0.25 - sole * k * 0.999; L.set_co(hi, P)     # flat tread on the ground
            top = P[np.abs(P[:, 2] - (P[:, 2].max() - 0.012 * k)) < 0.008 * k]; c = top.mean(0); rx = (top[:, 0].max() - top[:, 0].min()) / 2; ry = (top[:, 1].max() - top[:, 1].min()) / 2
            cuff = L.ring('cuff_%s_hi' % sd, 1.0, 0.010 * k, s.hi, seg=40, sides=10); Q = L.co(cuff); r = np.hypot(Q[:, 0], Q[:, 1]); th = np.arctan2(Q[:, 1], Q[:, 0])
            Q[:, 0] = c[0] + np.cos(th) * (rx + 0.002 * k + (r - 1.0)); Q[:, 1] = c[1] + np.sin(th) * (ry + 0.002 * k + (r - 1.0)); Q[:, 2] = c[2] + Q[:, 2] * 1.7; L.set_co(cuff, Q)
            hi = L.join([hi, cuff], 'boot_%s_hi' % sd); L.displace_np(hi, lambda Q_: 0.0012 * k * fbm(Q_, 11, 40 / k, 3)); hi.data.materials.append(mat)
            lo = L.dup(hi, 'boot_' + sd, s.lo); lo.data.materials.clear(); L.mod(lo, 'DECIMATE', ratio=min(1.0, 700.0 / L.tri_count(lo))); L.apply_mods(lo); L.clean_mesh(lo); lo.data.polygons.foreach_set('use_smooth', [True] * len(lo.data.polygons))
            L.smart_uv(lo, angle=66, margin=0.004); s.garments.append((lo, hi)); out.append(lo)
        return out

    def band(s, name, z, half=0.03, out=0.012, mat=None, around=None, squash=1.0):
        """a belt or cord round the body at height z: follows the widest outline of the garments there"""
        k = s.k; obs = around or [g[0] for g in s.garments]; pts = np.vstack([L.co(o) for o in obs]); m = (np.abs(pts[:, 2] - z) < 0.035 * k) & ~s.arm_mask(pts); pts = pts[m]; cy = float(pts[:, 1].mean()); th = np.arctan2(pts[:, 1] - cy, pts[:, 0]); rr = np.hypot(pts[:, 0], pts[:, 1] - cy)
        nb = 36; R = np.zeros(nb)
        for i in range(nb):
            a = -math.pi + (i + 0.5) * 2 * math.pi / nb; d = np.abs(np.angle(np.exp(1j * (th - a)))); sel = d < (2 * math.pi / nb); R[i] = rr[sel].max() if sel.any() else np.nan
        R = np.where(np.isnan(R), np.nanmean(R), R); R = (np.roll(R, 1) + R + np.roll(R, -1)) / 3 + out * k

        def mk(nu, hi_):
            V = []; F = []; prof = [(-1, 0.0), (-0.7, 0.6), (0, 1.0), (0.7, 0.6), (1, 0.0), (0, -0.6)]
            for i in range(nu):
                a = -math.pi + i * 2 * math.pi / nu; r = float(np.interp((a + math.pi) / (2 * math.pi) * nb - 0.5, np.arange(-1, nb + 1), np.r_[R[-1], R, R[0]]))
                for (pz, pr) in prof:
                    V.append(((r + pr * 0.006 * k * squash) * math.cos(a), cy + (r + pr * 0.006 * k * squash) * math.sin(a), z + pz * half * k))
            m_ = len(prof)
            for i in range(nu):
                i1 = (i + 1) % nu
                for j in range(m_):
                    j1 = (j + 1) % m_; F.append((i * m_ + j, i1 * m_ + j, i1 * m_ + j1, i * m_ + j1))
            o = L.new_obj(name + ('_hi' if hi_ else ''), V, F, s.hi if hi_ else s.lo); L.fix_normals(o)
            if hi_:
                L.subsurf(o, 2)
            return o
        lo = mk(36, False); hi = mk(72, True); hi.data.materials.append(mat); L.smart_uv(lo, angle=66, margin=0.004); s.garments.append((lo, hi)); return lo

    # -- head ---------------------------------------------------------------------------------------
    def head_parts(s, hair=None, hair_root=None, eye='brown'):
        s.eyes = fitted_part('eyes', 'eyes/low-poly', 'low-poly', s.V, s.lo); s.eye_tex = os.path.join(M.MH, 'eyes', 'materials', eye + '_eye.png')
        s.brows = fitted_part('brows', 'eyebrows/eyebrow001', 'eyebrow001', s.V, s.lo); s.lashes = fitted_part('lashes', 'eyelashes/eyelashes01', 'eyelashes01', s.V, s.lo); s.hair = None; s.hair_tex = None
        if hair:
            root = hair_root or M.MH; s.hair = fitted_part('hair', 'hair/' + hair, hair, s.V, s.lo, root=root); s.hair_tex = os.path.join(root, 'hair', hair, hair + '_diffuse.png')

    def trim_hair(s, hidden):
        """delete the hair faces a hat or hood hides (hidden(face centre) -> bool)"""
        if s.hair:
            bm = bmesh.new(); bm.from_mesh(s.hair.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if hidden(np.array(f.calc_center_median()))], context='FACES'); bm.to_mesh(s.hair.data); bm.free(); s.hair.data.update()

    def cull(s, hidden):
        """delete the body faces a garment covers (hidden(face centre) -> bool)"""
        if not getattr(s, 'full', None):
            s.full = L.dup(s.body, 'body_full', s.hi)
        bm = bmesh.new(); bm.from_mesh(s.body.data); kill = [f for f in bm.faces if hidden(np.array(f.calc_center_median()))]; bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(s.body.data); bm.free(); s.body.data.update()

    # -- rig -----------------------------------------------------------------------------------------
    def armature(s, asset):
        J = s.J; P = {}; sp3, sp2, sp1, nk, hd, hd2 = (J[n] for n in ('spine-3', 'spine-2', 'spine-1', 'neck', 'head', 'head-2')); chain = [sp3, sp2, (sp2 + sp1) / 2, sp1, (sp1 + nk) / 2, nk]
        bones = [('root', (0, 0, 0), (0, 0.1 * s.k, 0), None), ('pelvis', tuple(J['pelvis']), tuple(sp3), 'root')]
        for i in range(5):
            bones.append(('spine_%02d' % (i + 1), tuple(chain[i]), tuple(chain[i + 1]), 'pelvis' if i == 0 else 'spine_%02d' % i))
        bones += [('neck_01', tuple(nk), tuple((nk + hd) / 2), 'spine_05'), ('neck_02', tuple((nk + hd) / 2), tuple(hd), 'neck_01'), ('head', tuple(hd), tuple(hd2), 'neck_02')]
        for sd, m in (('l', 'l'), ('r', 'r')):
            g = lambda n: tuple(J['%s-%s' % (m, n)])
            bones += [('clavicle_' + sd, g('clavicle'), g('shoulder'), 'spine_05'), ('upperarm_' + sd, g('shoulder'), g('elbow'), 'clavicle_' + sd), ('lowerarm_' + sd, g('elbow'), g('hand'), 'upperarm_' + sd), ('hand_' + sd, g('hand'), g('finger-3-1'), 'lowerarm_' + sd),
                      ('thigh_' + sd, g('upper-leg'), g('knee'), 'pelvis'), ('calf_' + sd, g('knee'), g('ankle'), 'thigh_' + sd), ('foot_' + sd, g('ankle'), g('foot-1'), 'calf_' + sd), ('ball_' + sd, g('foot-1'), g('foot-2'), 'foot_' + sd)]
        s.arm = C.make_armature(asset + '_Armature', {}, bones, L.coll(asset)); return s.arm

    def weights(s, full_body, parts, rigid_head):
        """bone heat on the whole body; every other vertex copies the weights of the nearest body vertex; head gear follows the head bone only"""
        rep = C.bind(full_body, s.arm); names = [g.name for g in full_body.vertex_groups]; P = L.co(full_body); kd = kdtree.KDTree(len(P))
        for i, p in enumerate(P):
            kd.insert(Vector(p), i)
        kd.balance(); W = [[(names[g.group], g.weight) for g in v.groups if g.weight > 1e-4] for v in full_body.data.vertices]
        for o in parts:
            for g in list(o.vertex_groups):
                o.vertex_groups.remove(g)
            grp = {}
            if o in rigid_head:
                o.vertex_groups.new(name='head').add(list(range(len(o.data.vertices))), 1.0, 'REPLACE'); continue
            for v in o.data.vertices:
                for nm, w in W[kd.find(v.co)[1]]:
                    if nm not in grp:
                        grp[nm] = o.vertex_groups.new(name=nm)
                    grp[nm].add([v.index], w, 'REPLACE')
        return rep


def hair_atlas(path, hair_tex, brow_tex, lash_tex, hair_col, brow_col, px=2048):
    """one RGBA map for every hair card: hair in the lower half, brows top left, lashes top right; tinted by value"""
    def tint(p, col, size):
        im = Image.open(p).convert('RGBA').resize(size, Image.LANCZOS); a = np.asarray(im, np.float32) / 255.0; lum = a[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        lum = lum / max(1e-4, float(np.percentile(lum[a[..., 3] > 0.3], 90)) if (a[..., 3] > 0.3).any() else 1.0); a[..., :3] = np.clip((lum[..., None] ** 1.6) * np.array(col, np.float32) * 1.5, 0, 1); return Image.fromarray((a * 255 + 0.5).astype(np.uint8), 'RGBA')
    can = Image.new('RGBA', (px, px), (0, 0, 0, 0))
    if hair_tex:
        can.paste(tint(hair_tex, hair_col, (px, px // 2)), (0, px // 2))
    can.paste(tint(brow_tex, brow_col, (px // 2, px // 2)), (0, 0)); can.paste(tint(lash_tex, tuple(v * 0.3 for v in brow_col), (px // 2, px // 2)), (px // 2, 0)); can.save(path, optimize=True)
    if hair_tex:                                            # strand relief from the lightness of the hair map (lower half only; brows and lashes stay flat)
        h = np.asarray(Image.open(hair_tex).convert('L').resize((px, px // 2), Image.LANCZOS), np.float32) / 255.0; gx = np.gradient(h, axis=1); gy = -np.gradient(h, axis=0); st = 9.0
        n = np.stack([-gx * st, -gy * st, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True); full = np.zeros((px, px, 3), np.float32); full[...] = (0.5, 0.5, 1.0); full[px // 2:] = n * 0.5 + 0.5
        npth = path.replace('_BC.png', '_N.png'); Image.fromarray((full * 255 + 0.5).astype(np.uint8)).save(npth, optimize=True); return path, npth
    return path, None


def remap_uv(ob, su, sv, ou, ov):
    uv = ob.data.uv_layers.active; n = len(uv.data); U = np.zeros(n * 2, np.float32); uv.data.foreach_get('uv', U); U = U.reshape(n, 2); U[:, 0] = U[:, 0] * su + ou; U[:, 1] = U[:, 1] * sv + ov; uv.data.foreach_set('uv', U.ravel())


def card_material(name, path, npath=None, rough=0.5):
    t = NT(name); im = t.image(path, 'sRGB', t.uv); im.image.name = os.path.splitext(os.path.basename(path))[0]; kw = {}
    if npath:
        nm = t.image(npath, 'Non-Color', t.uv); nm.image.name = os.path.splitext(os.path.basename(npath))[0]; kw['normal'] = t.normalmap(nm.outputs[0], 1.0)
    t.set(base=im.outputs[0], rough=rough, alpha=im.outputs[1], sheen=0.3, **kw); return t.mat


def assemble(s, asset, outdir, cls='character_humanoid', px_skin=2048, px_outfit=2048, skin=None, px_hair=2048):
    """bake skin and outfit, build the hair atlas and eye map, join everything, bind, LODs; returns dict(lo, lods, files)"""
    os.makedirs(outdir, exist_ok=True); name = asset[3:]; files = {}
    # skin: the whole body carries the dense material; the game body is baked from a subdivided copy
    full = getattr(s, 'full', None) or L.dup(s.body, 'body_full', s.hi)                            # uncut body for weights
    bh = L.dup(full, 'body_hi', s.hi); L.subsurf(bh, 1); bh.data.materials.append(skin)
    fs, st_s = L.bake_set(s.body, [bh], px_skin, outdir, name + '_Skin', extrude=0.004 * s.k, maxdist=0.012 * s.k); files['Skin'] = fs; L.assign(s.body, L.game_material('MI_%s_Skin' % name, fs, sss={'weight': 0.12, 'radius': (1.0, 0.3, 0.15), 'scale': 0.006}))
    # outfit: every garment and solid in one atlas
    pieces = s.garments; los = [p[0] for p in pieces]; his = [p[1] for p in pieces]; rb = sorted(set(s.rigid.values()))
    for o in los:
        C.set_attr(o, 'rigid_id', np.full(len(o.data.vertices), float(rb.index(s.rigid[o.name]) + 1) if o.name in s.rigid else 0.0))
    under_his = [h for l_, h in pieces if l_.name in s.under]; outer_his = [h for l_, h in pieces if l_.name not in s.under]
    for o in los:
        if not o.data.uv_layers:
            L.smart_uv(o, angle=66, margin=0.004)
        o.data.uv_layers[0].name = 'UVMap'; C.set_attr(o, 'under', np.full(len(o.data.vertices), 1.0 if o.name in s.under else 0.0))
    outfit = L.join(los, 'outfit') if len(los) > 1 else los[0]; L.clean_mesh(outfit, dist=1e-6); L.pack_uv(outfit, margin=0.004)
    fo, st_o = L.bake_set(outfit, outer_his, px_outfit, outdir, name + '_Outfit', extrude=0.012 * s.k, maxdist=0.03 * s.k); files['Outfit'] = fo
    if under_his:                                        # garments worn underneath are baked on their own, so the layer above never prints onto them
        fu, _ = L.bake_set(outfit, under_his, px_outfit, outdir, name + '_OutfitUnder', extrude=0.006 * s.k, maxdist=0.015 * s.k); un = np.zeros(len(outfit.data.vertices), np.float32); outfit.data.attributes['under'].data.foreach_get('value', un)
        from PIL import ImageDraw, ImageFilter
        mk = Image.new('L', (px_outfit, px_outfit), 0); dr = ImageDraw.Draw(mk); uvd = outfit.data.uv_layers.active.data
        for poly in outfit.data.polygons:
            if all(un[v] > 0.5 for v in poly.vertices):
                dr.polygon([(uvd[li].uv[0] * px_outfit, (1 - uvd[li].uv[1]) * px_outfit) for li in poly.loop_indices], fill=255)
        mk = mk.filter(ImageFilter.MaxFilter(9))
        for key in fo:
            a_ = Image.open(fo[key]); b_ = Image.open(fu[key]).convert(a_.mode); a_.paste(b_, (0, 0), mk); a_.save(fo[key], optimize=True); os.remove(fu[key])
    L.assign(outfit, L.game_material('MI_%s_Outfit' % name, fo))
    # hair cards and eyes
    hp, hn = hair_atlas(os.path.join(outdir, 'T_%s_Hair_BC.png' % name), s.hair_tex, os.path.join(M.MH, 'eyebrows/eyebrow001/eyebrow001.png'), os.path.join(M.MH, 'eyelashes/eyelashes01/eyelashes01.png'), s.spec.get('hair_col', (0.2, 0.12, 0.06)), s.spec.get('brow_col', s.spec.get('hair_col', (0.2, 0.12, 0.06))), px=px_hair)
    files['Hair'] = {'BC': hp, **({'N': hn} if hn else {})}; hm = card_material('MI_%s_Hair' % name, hp, hn); cards = [s.brows, s.lashes] + ([s.hair] if s.hair else []); remap_uv(s.brows, 0.5, 0.5, 0.0, 0.5); remap_uv(s.lashes, 0.5, 0.5, 0.5, 0.5)
    if s.hair:
        remap_uv(s.hair, 1.0, 0.5, 0.0, 0.0)
    for o in cards:
        L.assign(o, hm)
    ep = os.path.join(outdir, 'T_%s_Eyes_BC.png' % name); Image.open(s.eye_tex).convert('RGB').resize((256, 256), Image.LANCZOS).save(ep, optimize=True); files['Eyes'] = {'BC': ep}
    t = NT('MI_%s_Eyes' % name); im = t.image(ep, 'sRGB', t.uv); im.image.name = 'T_%s_Eyes_BC' % name; t.set(base=im.outputs[0], rough=0.06, coat=1.0, coat_rough=0.03, spec=0.7); L.assign(s.eyes, t.mat)
    # rig and weights
    arm = s.armature(asset); rh = np.zeros(len(outfit.data.vertices), np.float32); outfit.data.attributes['rigid_id'].data.foreach_get('value', rh); rh = np.rint(rh).astype(int)
    rep = s.weights(full, [s.body, outfit, s.eyes] + cards, rigid_head=[s.eyes] + cards)
    for bi, bone in enumerate(rb):                                        # rigid pieces inside the outfit mesh follow one bone
        idx = [int(i) for i in np.nonzero(rh == bi + 1)[0]]
        for g in outfit.vertex_groups:
            g.remove(idx)
        hg = outfit.vertex_groups.get(bone) or outfit.vertex_groups.new(name=bone); hg.add(idx, 1.0, 'REPLACE')
    bpy.data.objects.remove(full)
    lo = L.join([s.body, outfit, s.eyes] + cards, asset + '_LOD0'); L.link(lo, L.coll(asset)); lo.parent = arm
    for m in list(lo.modifiers):
        lo.modifiers.remove(m)
    am = lo.modifiers.new('Armature', 'ARMATURE'); am.object = arm; L.activate(lo)
    try:
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4); bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    except Exception as e:
        print('limit/normalise:', e)
    return {'lo': lo, 'arm': arm, 'files': files, 'bake': {'skin': st_s, 'outfit': st_o}, 'weights': rep, 'body_hi': bh}


def export_person(asset, cls, P, outdir, families, origin, dresses, weak, script, lod_ratios=(0.5, 0.25, 0.12), extra=None, third=()):
    lo, arm = P['lo'], P['arm']; lods = [lo]; ac = L.coll(asset); ac['dink_class'] = cls; ac['dink_tex_px'] = 2048; ac['dink_source'] = 'authored in Blender by script (%s) on the CC0 MakeHuman base mesh' % script; L.link(lo, ac); L.link(arm, ac)
    for i, r in enumerate(lod_ratios):
        lods.append(C.lod_keep_weights(lo, r, asset + '_LOD%d' % (i + 1)))
    fbx = []
    for i, o in enumerate(lods):
        p = os.path.join(outdir, '%s_LOD%d.fbx' % (asset, i)); C.export_skeletal(p, arm, o); fbx.append(L.rel(p))
    for o in lods[1:]:
        o.hide_render = True
    st = L.mesh_stats(lo); blend = os.path.join(outdir, asset + '.blend'); L.save_blend(blend); soft, hard = L.BUDGET[cls]; tex = []
    for slot, fs in P['files'].items():
        for k, p in fs.items():
            tex.append({'file': L.rel(p), 'size_px': list(Image.open(p).size), 'slot': slot, 'channels': {'BC': 'base colour sRGB' + (' + alpha' if slot == 'Hair' else ''), 'N': 'tangent normal, OpenGL (green up; flip green on import)', 'ORM': 'R occlusion, G roughness, B metallic'}[k]})
    man = {'name': asset, 'class': cls, 'fbx': fbx[0], 'lod_fbx': fbx, 'source_blend': L.rel(blend), 'build': 'Unclaimed/tools/bl.sh %s' % script, 'dimensions_m': st['dimensions_m'], 'bounds_min_m': st['bounds_min_m'], 'bounds_max_m': st['bounds_max_m'],
           'lod0_triangles': st['triangles'], **{'lod%d_triangles' % (i + 1): L.tri_count(o) for i, o in enumerate(lods[1:])}, 'triangle_budget': {'soft': soft, 'hard': hard, 'within_soft': st['triangles'] <= soft},
           'textures': tex, 'materials': [m.name for m in lo.data.materials], 'material_slots_note': 'Skin and Outfit are baked BC/N/ORM sets; Hair is one alpha-tested atlas (hair, brows, lashes): base colour + alpha and a strand normal, no ORM (roughness 0.5 constant); Eyes is a base-colour iris map',
           'rig': {'root_bone': 'root', 'bones': [b.name for b in arm.data.bones], 'bone_count': len(arm.data.bones), 'weights': P['weights'], 'rest_pose': 'the A pose of the MakeHuman base mesh (arms about 45 degrees down)',
                   'skeleton': 'project humanoid core set (CONVENTIONS.md section 11): root, pelvis, spine_01..05, neck_01..02, head, clavicle / upperarm / lowerarm / hand / thigh / calf / foot / ball _l/_r; no finger, twist or IK bones',
                   'animation': 'none: skeleton and skin weights only'},
           'validation': {k: st[k] for k in ('uv_range', 'transforms_applied')}, 'bake_stats': P['bake'], 'pivot': 'feet: armature origin on the ground between the feet, front on -Y', 'families': families, 'origin_ids': origin,
           'supersedes': 'none (placeholder greybox cards)', 'dresses': dresses, 'third_party': ['MakeHuman CC0 base mesh, skin, eyes, eyebrows, eyelashes and hair (Art/Characters/ThirdParty/MakeHuman)'] + list(third),
           'status': 'source delivered; not imported into Unreal, not bound to any placement', 'known_weaknesses': weak}
    if extra:
        man.update(extra)
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', outdir); return man, lods
