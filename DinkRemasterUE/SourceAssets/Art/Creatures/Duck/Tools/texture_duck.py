"""Stage 2: procedural PBR atlas (BC / tangent N / ORM) synthesised in UV space with numpy.

    blender -b --factory-startup -t 3 --python Tools/texture_duck.py

No baking renders and no image inputs: every triangle of the rest mesh is
rasterised into the unique 2048 px UV layout, giving each texel its 3D rest
position, normal, part id and feather parameters.  Feathers are generated as
shingled contour-feather rows along the head-neck-body flow curve, covert rows
and long remiges on the folded wings and rachis/barb detail on the rectrices.
Bill, feet and eyes get their own keratin, scute and iris patterns.  Height is
authored in metres and converted to an OpenGL tangent-space normal map using
the measured texel size, so normal strength is physical.  Deterministic (seed
1997); PNGs are written with a stdlib encoder.
"""
import json
import math
import struct
import sys
import time
import zlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402
import duck_geometry as G  # noqa: E402

T0 = time.time()
RES = D.TEX_PX
TAU = math.tau


def log(*a):
    print('[duck-tex %.1fs]' % (time.time() - T0), *a, flush=True)


bpy.ops.wm.open_mainfile(filepath=str(D.WORKING / 'Duck_Working.blend'))
ob = bpy.data.objects[D.LOD0]
arm = bpy.data.objects['Armature']
arm.data.pose_position = 'REST'
me = ob.data
NV = len(me.vertices)
P = np.zeros(NV * 3, np.float32)
me.vertices.foreach_get('co', P)
PFIN = P.reshape(-1, 3).astype(np.float64)          # final rest-space positions (AO)
P = np.zeros(NV * 3, np.float32)
me.attributes['duck_dpos'].data.foreach_get('vector', P)
P = P.reshape(-1, 3).astype(np.float64)            # design-space positions (patterns)
NRM = np.zeros(NV * 3, np.float32)
me.vertices.foreach_get('normal', NRM)
NRM = NRM.reshape(-1, 3).astype(np.float64)
part_v = np.zeros(NV, np.int32)
me.attributes['duck_part'].data.foreach_get('value', part_v)
pa_v = np.zeros(NV, np.float32)
pc_v = np.zeros(NV, np.float32)
me.attributes['duck_a'].data.foreach_get('value', pa_v)
me.attributes['duck_c'].data.foreach_get('value', pc_v)
len_v = np.zeros(NV, np.float32)
me.attributes['duck_len'].data.foreach_get('value', len_v)
fpart_poly = np.zeros(len(me.polygons), np.int32)
me.attributes['duck_fpart'].data.foreach_get('value', fpart_poly)
me.calc_loop_triangles()
NT = len(me.loop_triangles)
tri_loops = np.zeros(NT * 3, np.int32)
tri_verts = np.zeros(NT * 3, np.int32)
me.loop_triangles.foreach_get('loops', tri_loops)
me.loop_triangles.foreach_get('vertices', tri_verts)
tri_loops = tri_loops.reshape(-1, 3)
tri_verts = tri_verts.reshape(-1, 3)
tri_poly = np.zeros(NT, np.int32)
me.loop_triangles.foreach_get('polygon_index', tri_poly)
tri_part = fpart_poly[tri_poly]
uv = np.zeros(len(me.loops) * 2, np.float32)
me.uv_layers[0].data.foreach_get('uv', uv)
uv = uv.reshape(-1, 2).astype(np.float64)

# ------------------------------------------------------------------ noise helpers (deterministic)
M64 = np.uint64(0xFFFFFFFFFFFFFFFF)


def hashu(*ints, seed=0):
    h = np.uint64(0x9E3779B97F4A7C15 + seed * 7919)
    for i, k in enumerate(ints):
        k = np.asarray(k).astype(np.int64).astype(np.uint64)
        h = h ^ (k * np.uint64([0x85EBCA6B, 0xC2B2AE35, 0x27D4EB2F, 0x165667B1][i % 4]) + np.uint64(0x9E3779B9) + (h << np.uint64(6)) + (h >> np.uint64(2)))
    h = h ^ (h >> np.uint64(33))
    h = h * np.uint64(0xFF51AFD7ED558CCD)
    h = h ^ (h >> np.uint64(33))
    return (h >> np.uint64(40)).astype(np.float64) / float(1 << 24)


def vnoise(p, freq, seed):
    q = p * freq
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1 - f[:, 0]
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1 - f[:, 1]
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1 - f[:, 2]
                out = out + wx * wy * wz * hashu(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed=seed)
    return out


def fbm(p, freq, octaves, seed, gain=0.5):
    s, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + a * vnoise(p, freq * (2.03 ** o), seed + 31 * o)
        tot += a
        a *= gain
    return s / tot


def worley(p, cell, seed):
    q = p / cell
    i = np.floor(q).astype(np.int64)
    f1 = np.full(len(p), 9.0)
    f2 = np.full(len(p), 9.0)
    idc = np.zeros(len(p))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = i + np.array([dx, dy, dz])
                fp = c + np.stack([hashu(c[:, 0], c[:, 1], c[:, 2], seed=seed + k) for k in range(3)], 1)
                d = np.linalg.norm(q - fp, axis=1)
                nearer = d < f1
                f2 = np.where(nearer, f1, np.minimum(f2, d))
                idc = np.where(nearer, hashu(c[:, 0], c[:, 1], c[:, 2], seed=seed + 7), idc)
                f1 = np.where(nearer, d, f1)
    return f1, f2, idc


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ per-vertex fields
# Feather flow coordinates along the bill-root -> head -> neck -> body -> tail curve.
curve = np.array(D.SPINE_CURVE, float)
A, B = curve[:-1], curve[1:]
seglen = np.linalg.norm(B - A, axis=1)
cum = np.concatenate([[0], np.cumsum(seglen)])
best = np.full(NV, 1e9)
s_v = np.zeros(NV)
U_v = np.zeros((NV, 3))
off_v = np.zeros((NV, 3))
Y = np.array([0, 1.0, 0])
for k in range(len(A)):
    ab = B[k] - A[k]
    t = np.clip(((P - A[k]) @ ab) / (ab @ ab), 0, 1)
    cp = A[k] + t[:, None] * ab
    d = np.linalg.norm(P - cp, axis=1)
    m = d < best
    best = np.where(m, d, best)
    s_v = np.where(m, cum[k] + t * seglen[k], s_v)
    T = ab / np.linalg.norm(ab)
    U = -np.cross(T, Y)
    U_v[m] = U
    off_v[m] = (P - cp)[m]
r_v = best
cos_t = np.einsum('ij,ij->i', off_v, U_v)
sin_t = off_v[:, 1]
nrm = np.hypot(cos_t, sin_t) + 1e-12
cos_t /= nrm
sin_t /= nrm
edges = np.zeros(len(me.edges) * 2, np.int32)
me.edges.foreach_get('vertices', edges)
edges = edges.reshape(-1, 2)
bodyv = part_v == D.PART_BODY
E = edges[bodyv[edges[:, 0]] & bodyv[edges[:, 1]]]
fields = np.stack([s_v, cos_t, sin_t], 1)
for _ in range(24):
    acc = np.zeros_like(fields)
    cnt = np.zeros(NV)
    np.add.at(acc, E[:, 0], fields[E[:, 1]])
    np.add.at(acc, E[:, 1], fields[E[:, 0]])
    np.add.at(cnt, E[:, 0], 1)
    np.add.at(cnt, E[:, 1], 1)
    sel = bodyv & (cnt > 0)
    fields[sel] = 0.5 * fields[sel] + 0.5 * acc[sel] / cnt[sel, None]
s_v = fields[:, 0]
cs = np.hypot(fields[:, 1], fields[:, 2]) + 1e-12
cos_t, sin_t = fields[:, 1] / cs, fields[:, 2] / cs
log('flow fields ready', NV, 'verts', NT, 'tris')

# Mean body radius as a function of s, for the number of feathers around each row.
sb = np.arange(0, cum[-1] + 0.01, 0.005)
rb = np.array([np.median(r_v[bodyv & (np.abs(s_v - x) < 0.006)]) if np.any(bodyv & (np.abs(s_v - x) < 0.006)) else np.nan for x in sb])
good = ~np.isnan(rb)
rb = np.interp(sb, sb[good], rb[good])

# Ambient occlusion per vertex (BVH rays over the whole rest mesh, fixed direction set).
occl_polys = [list(p.vertices) for p, fp in zip(me.polygons, fpart_poly) if fp not in (D.PART_CARD,) + D.GORE]
bvh = BVHTree.FromPolygons([Vector(p) for p in PFIN], occl_polys)
ndir = 20
gold = math.pi * (3 - math.sqrt(5))
dirs = []
for i in range(ndir):
    z = 1 - (i + 0.5) / ndir
    rr = math.sqrt(1 - z * z)
    dirs.append((math.cos(gold * i) * rr, math.sin(gold * i) * rr, z))
dirs = np.array(dirs)
ao_v = np.ones(NV)
for vi in range(NV):
    n = NRM[vi]
    t1 = np.cross(n, [0, 0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0, 0])
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    if part_v[vi] in (D.PART_CAP_BODY, D.PART_CAP_HEAD):
        continue
    o = Vector(PFIN[vi] + n * 0.0006)
    hits = 0.0
    for d in dirs:
        w = t1 * d[0] + t2 * d[1] + n * d[2]
        hit = bvh.ray_cast(o, Vector(w), 0.06)
        if hit[0] is not None:
            hits += 1.0 - min(1.0, hit[3] / 0.06) * 0.6
    ao_v[vi] = 1 - hits / ndir
log('vertex AO done')

# ------------------------------------------------------------------ rasteriser
uvp = uv[tri_loops] * RES - 0.5
tri_id = np.full((RES, RES), -1, np.int32)
bary = np.zeros((RES, RES, 3), np.float32)
P3 = P[tri_verts]
area3 = 0.5 * np.linalg.norm(np.cross(P3[:, 1] - P3[:, 0], P3[:, 2] - P3[:, 0]), axis=1)
e1 = uvp[:, 1] - uvp[:, 0]
e2 = uvp[:, 2] - uvp[:, 0]
areap = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
texel_m = np.sqrt(area3 / np.maximum(areap, 1e-12))
for t in range(NT):
    (ax, ay), (bx, by), (cx, cy) = uvp[t]
    x0 = max(int(math.floor(min(ax, bx, cx))), 0)
    x1 = min(int(math.ceil(max(ax, bx, cx))), RES - 1)
    y0 = max(int(math.floor(min(ay, by, cy))), 0)
    y1 = min(int(math.ceil(max(ay, by, cy))), RES - 1)
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-12 or x1 < x0 or y1 < y0:
        continue
    X, Yg = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    l0 = ((by - cy) * (X - cx) + (cx - bx) * (Yg - cy)) / den
    l1 = ((cy - ay) * (X - cx) + (ax - cx) * (Yg - cy)) / den
    l2 = 1 - l0 - l1
    m = (l0 >= -1e-5) & (l1 >= -1e-5) & (l2 >= -1e-5)
    if not m.any():
        continue
    tri_id[Yg[m], X[m]] = t
    bary[Yg[m], X[m]] = np.stack([l0[m], l1[m], l2[m]], 1)
mask = tri_id >= 0
log('rasterised coverage %.1f%%' % (100 * mask.mean()))
ti = tri_id[mask]
bw = bary[mask].astype(np.float64)
tv = tri_verts[ti]


def interp(arr):
    if arr.ndim == 1:
        return (arr[tv] * bw).sum(1)
    return (arr[tv] * bw[:, :, None]).sum(1)


pos = interp(P)
nor = interp(NRM)
nor /= np.linalg.norm(nor, axis=1, keepdims=True) + 1e-12
part = tri_part[ti]
flen = interp(len_v.astype(np.float64))
pa = interp(pa_v.astype(np.float64))
pc = interp(pc_v.astype(np.float64))
sv = interp(s_v)
ct = interp(cos_t)
st = interp(sin_t)
theta = np.arctan2(st, ct)
aov = interp(ao_v)
tex_m = texel_m[ti]
M = len(pos)
log('texels', M)

# Output channels (linear albedo, roughness, AO multiplier, height in metres).
alb = np.zeros((M, 3))
rough = np.full(M, 0.6)
micro_ao = np.ones(M)
height = np.zeros(M)
alpha = np.ones(M)

# ------------------------------------------------------------------ contour feathers (head/neck/body/lid)
S_ctrl = D.FEATHER_S
L_ctrl = D.FEATHER_L


def Lf(s):
    return np.interp(s, S_ctrl, L_ctrl)


sg = np.linspace(0, 0.75, 6001)
ug = np.concatenate([[0], np.cumsum((sg[1:] - sg[:-1]) / Lf(0.5 * (sg[1:] + sg[:-1])))])


def u_of_s(s):
    return np.interp(s, sg, ug)


def s_of_u(u):
    return np.interp(u, ug, sg)


def r_of_s(s):
    return np.interp(s, sb, rb)


def row_cells(k, th):
    sk = s_of_u(k + 0.5)
    W = 1.30 * Lf(sk)
    Nk = np.maximum(8, np.round(TAU * np.maximum(r_of_s(sk), 0.004) / W))
    v = (th / TAU + 0.5) * Nk + 0.5 * (k % 2) + 0.37 * hashu(k, seed=11)
    j = np.floor(v)
    fv = v - j - 0.5
    j = np.mod(j, Nk)
    h1 = hashu(k, j, seed=21)
    h2 = hashu(k, j, seed=22)
    b = (0.40 + 0.22 * h1) * (2 * np.abs(fv)) ** (1.7 + 0.6 * h2) + 0.05 * h2
    return j, fv, b, h1, h2


def shingles(u, th, L, depth, fluff_seed, barb_spacing=None, rows_cb=row_cells):
    k0 = np.floor(u)
    jA, fvA, bA, hA1, hA2 = rows_cb(k0, th)
    jP, fvP, bP, _, _ = rows_cb(k0 - 1, th)
    jB, fvB, bB, hB1, hB2 = rows_cb(k0 + 1, th)
    inA = (u - k0) < (1 - bA)
    start = np.where(inA, k0 - bP, k0 + 1 - bA)
    end = np.where(inA, k0 + 1 - bA, k0 + 2 - bB)
    prog = np.clip((u - start) / np.maximum(end - start, 1e-6), 0, 1)
    fv = np.where(inA, fvA, fvB)
    h1 = np.where(inA, hA1, hB1)
    h2 = np.where(inA, hA2, hB2)
    k = np.where(inA, k0, k0 + 1)
    dist = (end - u) * L
    bevel = sstep(0.0, np.maximum(0.00045, 0.16 * L), dist)
    hgt = depth * (0.30 + 0.70 * sstep(0, 1, prog)) * (0.45 + 0.55 * bevel)
    hgt += depth * 0.22 * (1 - (2 * fv) ** 2)
    crev = 0.72 + 0.28 * sstep(0.0, 0.35, prog)
    if barb_spacing is not None:
        ang = 0.55 * np.sign(fv)
        ph = ((u - start) * L * np.cos(ang) + np.abs(fv) * 1.3 * L * np.sin(ang) * 2.2) / barb_spacing
        barb = 0.5 + 0.5 * np.cos(TAU * ph)
        return hgt, prog, fv, h1, h2, k, crev, barb, dist
    return hgt, prog, fv, h1, h2, k, crev, None, dist


WHITE = np.array([0.700, 0.688, 0.640])
CREAM = np.array([0.712, 0.672, 0.560])
DIRT = np.array([0.36, 0.31, 0.24])
GREYDOWN = np.array([0.50, 0.50, 0.49])

fb = (part == D.PART_BODY)
idx = np.nonzero(fb)[0]
s_b = sv[idx]
pb = pos[idx]
L_b = Lf(s_b)
r_b = np.maximum(r_of_s(s_b), 0.004)
# Domain warp: rows and columns wander like real feather tracts instead of a perfect lattice.
w1 = fbm(pb, 22, 3, 61) - 0.5
w2 = fbm(pb, 22, 3, 62) - 0.5
u_b = u_of_s(s_b) + 0.55 * w1
th_b = theta[idx] + 0.9 * w2 * (1.3 * L_b) / r_b
ventral = sstep(0.2, 0.9, -ct[idx])
dorsal = sstep(-0.1, 0.8, ct[idx])
# Visible layering: strong on back/flank/rump, soft on breast and belly, velvet on head and neck.
vis = (0.40 + 0.60 * (1 - ventral)) * (0.24 + 0.76 * sstep(0.10, 0.30, s_b))
tract = 0.70 + 0.60 * fbm(np.stack([s_b * 9, th_b * 1.4, np.zeros_like(s_b)], 1), 1.0, 3, 64)  # pterylae
depth_b = 0.0145 * L_b * vis * tract + 0.000045 * (1 - sstep(0.15, 0.30, s_b)) + 0.000015
hgt, prog, fv, h1, h2, kk, crev, barb, dist = shingles(u_b, th_b, L_b, depth_b, 5, barb_spacing=0.0011)
crev = 1 - (1 - crev) * 0.45 * vis
# fine anisotropic barb streaks along the flow and clumpy fluff
arc = th_b * r_b
streak = vnoise(np.stack([s_b * 140, arc * 1300, np.zeros_like(arc)], 1), 1.0, 66) * 0.6 + vnoise(np.stack([s_b * 300, arc * 2600, np.zeros_like(arc)], 1), 1.0, 67) * 0.4
fl = fbm(pb, 170, 3, 41)
velvet = 1 - sstep(0.12, 0.26, s_b)
hgt += (fl - 0.5) * 0.00006 + (streak - 0.5) * (0.000022 + 0.00002 * velvet)
hgt += (fbm(pb, 900, 2, 70) - 0.5) * 0.000045 * (0.3 + velvet)
hgt += (fbm(pb, 60, 3, 69) - 0.5) * 0.00014 * (0.5 + 0.5 * vis)
barb_vis = sstep(3.0, 6.0, 0.0011 / tex_m[idx]) * sstep(0.18, 0.28, s_b) * vis
hgt += (barb - 0.5) * 0.000014 * barb_vis
rach = (1 - sstep(0.0, 0.05, np.abs(fv))) * sstep(0.15, 0.4, prog) * sstep(0.24, 0.32, s_b) * vis
hgt += rach * 0.00002
worn = (h2 > 0.96) & (np.abs(fv - (h1 - 0.5) * 0.5) < 0.05) & (prog > 0.55) & (s_b > 0.24)
hgt = np.where(worn, hgt * 0.4, hgt)
# colour: near-uniform white with warm cream on neck/back, broad soft variation
big = fbm(pb, 7, 3, 68)
tone = 1.0 + (h1 - 0.5) * 0.025 * vis + (big - 0.5) * 0.05 + (streak - 0.5) * 0.03
neck = sstep(0.07, 0.13, s_b) * (1 - sstep(0.26, 0.34, s_b))
tint = np.clip(0.30 * dorsal + 0.40 * neck, 0, 1)
col = WHITE[None] * (1 - tint[:, None]) + CREAM[None] * tint[:, None]
col = col * tone[:, None] * crev[:, None]
col = np.where(worn[:, None], col * 0.86, col)
dn = fbm(pb, 38, 4, 51)
mud_spots = 1 - sstep(0.0, 0.08, worley(pb, 0.006, 57)[0] - 0.55)
dirt = sstep(0.35, 0.95, -ct[idx]) * (sstep(0.30, 0.72, dn) * 0.62 + 0.35 * mud_spots * sstep(0.4, 0.7, fbm(pb, 12, 2, 58)))
dirt += sstep(0.150, 0.105, pb[:, 2]) * 0.40 * sstep(0.3, 0.7, dn)
dirt += sstep(0.50, 0.62, s_b) * sstep(0.0, 0.8, -ct[idx]) * 0.25
dirt *= (1.10 - 0.3 * sstep(0.3, 1.0, prog))
dirt = np.clip(dirt, 0, 0.7)
col = col * (1 - dirt[:, None]) + DIRT[None] * dirt[:, None] * tone[:, None]
alb[idx] = col
rough[idx] = 0.70 - 0.07 * sstep(0.5, 1.0, prog) * vis + (h1 - 0.5) * 0.09 + (big - 0.5) * 0.10 + 0.14 * dirt
micro_ao[idx] = crev
height[idx] = hgt

# ------------------------------------------------------------------ folded-wing feathers (coverts .. primaries)
fw = part == D.PART_WING
idx = np.nonzero(fw)[0]
a_w = pa[idx]
c_w = pc[idx]
L_w = np.maximum(flen[idx], 0.02)
pw = pos[idx]
long_ = sstep(0.07, 0.10, L_w)                 # remiges vs coverts
shaft = (1 - sstep(0.0, 0.05 + 0.04 * (1 - long_), np.abs(c_w))) * sstep(0.0, 0.08, a_w)
vane = np.abs(c_w)
barb_ph = (a_w * L_w * np.cos(0.55) + vane * 0.012 * np.sin(0.55)) / 0.0009
barb = 0.5 + 0.5 * np.cos(TAU * barb_ph)
inner = c_w < 0        # inner vane slightly broader/softer on remiges
edge = sstep(0.70, 1.0, vane)
split = (hashu(np.floor(a_w * L_w / 0.006), np.floor(pw[:, 0] * 400), seed=74) > 0.93) & (vane > 0.4) & (a_w > 0.3)
fl = fbm(pw, 800, 3, 43)
hgt = shaft * (0.00006 + 0.00005 * long_) + (barb - 0.5) * 0.000018 - edge * 0.00012 + (fl - 0.5) * 0.00003  # bevelled vane edges
hgt = np.where(split, hgt - 0.00008, hgt)
tone = 1 + (hashu(np.round(L_w * 1000), np.round(pw[:, 2] * 200), seed=75) - 0.5) * 0.05 + (fl - 0.5) * 0.03
col = WHITE[None] * tone[:, None] * (1 - 0.025 * barb)[:, None] * (1 - 0.04 * edge * long_)[:, None]
col = np.where((shaft > 0.5)[:, None], col * np.array([1.0, 0.985, 0.93]), col)
col = np.where(split[:, None], col * 0.82, col)
dn = fbm(pw, 30, 4, 53)
dirt = (sstep(0.6, 1.0, a_w) * 0.22 * long_ + 0.10) * sstep(0.40, 0.78, dn)
col = col * (1 - dirt[:, None]) + DIRT[None] * dirt[:, None]
alb[idx] = col
rough[idx] = 0.64 - 0.06 * shaft + (tone - 1) * 0.6 + 0.12 * dirt
micro_ao[idx] = 0.90 + 0.10 * (1 - edge)
height[idx] = hgt

# ------------------------------------------------------------------ contour-feather cards (alpha tested)
fc = part == D.PART_CARD
idx = np.nonzero(fc)[0]
a_c = pa[idx]
c_c = pc[idx]
L_c = np.maximum(flen[idx], 0.004)
pcd = pos[idx]
# Soft, ragged vane: no hard rounded tip; the alpha feathers out over the outer third and at the sides.
prof = (0.55 + 0.45 * np.sin(0.5 * np.pi * np.clip(a_c / 0.25, 0, 1)))
rel = 0.95 * prof / (1 - 0.36 * a_c)
fluff = fbm(pcd, 2600, 2, 79)
barbs_edge = 0.5 + 0.5 * np.cos(TAU * (a_c * L_c / 0.0012 + np.abs(c_c) * 3.0 + 2.0 * fluff))
side_a = sstep(0.0, 0.55, rel - np.abs(c_c) + 0.18 * (fluff - 0.5))
tip_a = 1 - sstep(0.45, 1.0, a_c + 0.20 * (fluff - 0.5) + 0.10 * barbs_edge)
alpha[idx] = np.clip(side_a * tip_a * sstep(0.0, 0.12, a_c) * (0.65 + 0.35 * barbs_edge), 0, 1)
shaft = 1 - sstep(0.0, 0.06, np.abs(c_c))
barb = 0.5 + 0.5 * np.cos(TAU * (a_c * L_c * np.cos(0.6) + np.abs(c_c) * 0.5 * L_c * np.sin(0.6)) / 0.0010)
height[idx] = shaft * 0.00002 * sstep(0.1, 0.3, a_c) + (barb - 0.5) * 0.00001
# colour matched to the skin underneath: same white/cream tint, broad tone and soiling, no crevice darkening
big_c = fbm(pcd, 7, 3, 68)
s_c = sv[idx]
neck_c = sstep(0.07, 0.13, s_c) * (1 - sstep(0.26, 0.34, s_c))
dors_c = sstep(-0.1, 0.8, ct[idx])
tint_c = np.clip(0.30 * dors_c + 0.40 * neck_c, 0, 1)
col = WHITE[None] * (1 - tint_c[:, None]) + CREAM[None] * tint_c[:, None]
col = col * (1.0 + (big_c[:, None] - 0.5) * 0.05) * 0.965
dn = fbm(pcd, 38, 4, 51)
dirt = sstep(0.35, 0.95, -ct[idx]) * sstep(0.30, 0.72, dn) * 0.55 + sstep(0.150, 0.105, pcd[:, 2]) * 0.40 * sstep(0.3, 0.7, dn)
dirt = np.clip(dirt, 0, 0.7)
col = col * (1 - dirt[:, None]) + DIRT[None] * dirt[:, None]
alb[idx] = col
rough[idx] = 0.70 + (big_c - 0.5) * 0.10 + 0.12 * dirt
micro_ao[idx] = 1.0

# ------------------------------------------------------------------ wound caps (faithful original decapitation)
cutp = np.array(D.CUT_POINT)
cutn = np.array(D.CUT_NORMAL) / np.linalg.norm(D.CUT_NORMAL)
cu = np.array([1.0, 0, 0]) - cutn * cutn[0]
cu /= np.linalg.norm(cu)
cv = np.cross(cutn, cu)
fcap = np.isin(part, [D.PART_CAP_BODY, D.PART_CAP_HEAD])
idx = np.nonzero(fcap)[0]
q = pos[idx] - cutp
du, dv = q @ cu, q @ cv
r_k = pa[idx]                                  # 0 rim -> 1 centre
n1 = fbm(pos[idx], 900, 3, 101)
n2 = fbm(pos[idx], 250, 3, 102)
MUSCLE = np.array([0.15, 0.012, 0.012])
CLOT = np.array([0.075, 0.004, 0.004])
SKIN = np.array([0.58, 0.36, 0.28])
BONE = np.array([0.78, 0.70, 0.58])
CART = np.array([0.74, 0.58, 0.52])
LUMEN = np.array([0.025, 0.006, 0.005])
fib = 0.5 + 0.5 * np.sin(TAU * (np.arctan2(dv, du) * 7 + n1 * 3))
col = MUSCLE[None] * (0.70 + 0.45 * fib[:, None] * n2[:, None])
hgt = (fib - 0.5) * 0.00008 + (n1 - 0.5) * 0.00010
ro = 0.42 + 0.12 * n2
rim = 1 - sstep(0.06, 0.16, r_k)
col = col * (1 - rim[:, None]) + SKIN[None] * rim[:, None] * (0.85 + 0.3 * n1[:, None])
ro = ro * (1 - rim) + 0.45 * rim
def disk(cx, cy, r):
    return np.hypot(du - cx, dv - cy) / r
dt = disk(0.0105, 0.0, 0.0046)                 # trachea: cartilage ring, dark airway
ring_t = sstep(0.62, 0.72, dt) * (1 - sstep(0.95, 1.08, dt))
lum_t = 1 - sstep(0.55, 0.66, dt)
de = disk(0.0050, 0.0075, 0.0034)              # oesophagus
ring_e = sstep(0.55, 0.70, de) * (1 - sstep(0.95, 1.10, de))
lum_e = 1 - sstep(0.45, 0.60, de)
dvb = disk(-0.0105, 0.0, 0.0058)               # cervical vertebra with spinal cord
bone = 1 - sstep(0.92, 1.05, dvb)
cord = 1 - sstep(0.25, 0.34, dvb)
smear = sstep(0.35, 0.75, fbm(pos[idx], 500, 3, 104))
for m_, c_ in ((ring_t, CART * 0.75), (ring_e, np.array([0.30, 0.08, 0.07])), (bone, BONE * 0.8)):
    m_ = m_ * (1 - 0.7 * smear)
    col = col * (1 - m_[:, None]) + c_[None] * m_[:, None] * (0.9 + 0.2 * n1[:, None])
col = col * (1 - cord[:, None]) + np.array([0.86, 0.74, 0.66])[None] * cord[:, None]
for m_ in (lum_t, lum_e):
    col = col * (1 - m_[:, None]) + LUMEN[None] * m_[:, None]
hgt += ring_t * 0.0004 + bone * 0.0006 - lum_t * 0.0009 - lum_e * 0.0006 - cord * 0.0002
ro = np.where(bone > 0.5, 0.30, ro)
clot = sstep(0.45, 0.62, fbm(pos[idx], 160, 3, 103)) * (1 - 0.6 * bone) * (1 - 0.6 * ring_t)
col = col * (1 - clot[:, None]) + CLOT[None] * clot[:, None]
ro = ro * (1 - clot) + 0.14 * clot
alb[idx] = col
rough[idx] = ro
height[idx] = hgt
micro_ao[idx] = 1 - 0.5 * (lum_t + lum_e)

# ------------------------------------------------------------------ blood films (runs down the stump / head stub)
fbl = np.isin(part, [D.PART_BLOOD_BODY, D.PART_BLOOD_HEAD])
idx = np.nonzero(fbl)[0]
dist_c = pa[idx]                               # metres from the cut
ang = pc[idx]                                  # 0..1 around the neck
head_side = part[idx] == D.PART_BLOOD_HEAD
circ = 0.176
NCOL = 34
cpos = ang * NCOL
j = np.floor(cpos)
off = (cpos - j - 0.5) * circ / NCOL           # metres from the column centre
h1 = hashu(j, seed=111)
h2 = hashu(j, seed=112)
run_len = np.where(head_side, 0.004 + 0.010 * h1 ** 2, 0.008 + 0.070 * h1 ** 2.2)
wid = (0.0012 + 0.0030 * h2) * (1 - 0.55 * np.clip(dist_c / np.maximum(run_len, 1e-4), 0, 1))
wob = (fbm(pos[idx], 220, 2, 113) - 0.5) * 0.004
runm = sstep(0.0002, -0.0002, np.abs(off + wob) - wid) * sstep(0.0004, -0.0004, dist_c - run_len)
bulb = sstep(0.0004, -0.0002, np.hypot(off + wob, dist_c - run_len) - 1.25 * wid)
sheet = sstep(0.0002, -0.0003, dist_c - (0.004 + 0.006 * fbm(pos[idx], 60, 2, 114)))
spat = (hashu(np.floor(pos[idx, 0] / 0.0016), np.floor(pos[idx, 1] / 0.0016), np.floor(pos[idx, 2] / 0.0016), seed=115) > 0.985) & (dist_c < 0.05)
bmask = np.clip(np.maximum.reduce([runm, bulb * (dist_c > 0.005), sheet, spat.astype(float) * 0.9]), 0, 1)
alpha[idx] = bmask
thick = bmask * (0.00012 + 0.00030 * bulb + 0.00010 * sheet)
height[idx] = thick
fresh = 1 - sstep(0.0, 0.06, dist_c)
nb = fbm(pos[idx], 400, 2, 116)
col = np.array([0.14, 0.005, 0.006])[None] * (fresh[:, None] * 1.0 + (1 - fresh[:, None]) * 0.55) * (0.85 + 0.3 * nb[:, None])
edge_dry = 1 - sstep(0.4, 0.9, bmask)
col = col * (1 - 0.35 * edge_dry[:, None])
alb[idx] = col
rough[idx] = 0.15 + 0.22 * (1 - fresh) + 0.2 * edge_dry
micro_ao[idx] = 1.0

# ------------------------------------------------------------------ rectrices
ft = part == D.PART_TAIL
idx = np.nonzero(ft)[0]
a_t = pa[idx]
c_t = pc[idx]
pt = pos[idx]
sh = 1 - sstep(0.0, 0.10, np.abs(c_t))
barb = 0.5 + 0.5 * np.cos(TAU * (a_t * 0.075 * np.cos(0.6) + np.abs(c_t) * 0.012 * np.sin(0.6)) / 0.0010)
edge = sstep(0.75, 1.0, np.abs(c_t))
fl = fbm(pt, 800, 3, 45)
height[idx] = sh * 0.00008 + (barb - 0.5) * 0.00002 + (fl - 0.5) * 0.00004 - edge * 0.00005
col = WHITE[None] * (1 + (fl[:, None] - 0.5) * 0.05) * (1 - 0.03 * barb)[:, None]
col *= (1 - 0.10 * edge)[:, None]
dn = fbm(pt, 30, 3, 55)
dirt = sstep(0.5, 0.9, dn) * 0.35 * sstep(0.4, 1.0, a_t)
col = col * (1 - dirt[:, None]) + DIRT[None] * dirt[:, None]
alb[idx] = col
rough[idx] = 0.62 + 0.1 * dirt
micro_ao[idx] = 0.92 + 0.08 * sh

# ------------------------------------------------------------------ eyelid ring (bare skin, fine)
fl_ = part == D.PART_LID
idx = np.nonzero(fl_)[0]
n_ = fbm(pos[idx], 2500, 2, 47)
alb[idx] = np.array([0.20, 0.17, 0.15]) * (0.9 + 0.2 * n_[:, None])
rough[idx] = 0.40
height[idx] = (n_ - 0.5) * 0.00002

# ------------------------------------------------------------------ bill (keratin rhamphotheca)
fbill = np.isin(part, [D.PART_BILL_UP, D.PART_BILL_LO])
idx = np.nonzero(fbill)[0]
pbi = pos[idx]
bx = np.clip((pbi[:, 0] - 0.184) / (0.2752 - 0.184), 0, 1)
upper = part[idx] == D.PART_BILL_UP
BILL = np.array([0.80, 0.33, 0.035])
NAIL = np.array([0.74, 0.40, 0.14])
n1 = fbm(pbi, 260, 4, 81)
n2 = fbm(pbi, 1600, 2, 82)
n3 = fbm(pbi, 55, 4, 84)
streak_b = vnoise(np.stack([pbi[:, 0] * 180, pbi[:, 1] * 2200, pbi[:, 2] * 2200], 1), 1.0, 85)
col = BILL[None] * (0.86 + 0.14 * n1[:, None] + 0.12 * (n3[:, None] - 0.5)) * (1 + 0.05 * (streak_b[:, None] - 0.5))
col = col * np.array([1.0, 0.94, 0.85])[None] ** (sstep(0.55, 0.8, n3)[:, None])
col *= (1 - 0.18 * sstep(0.15, 0.0, bx))[:, None] * np.array([1.0, 0.92, 0.80])[None] ** sstep(0.15, 0.0, bx)[:, None]
# nail at the tip of the upper mandible
nail = upper & (bx > 0.86) & (pbi[:, 2] > 0.4095)
nailw = sstep(0.86, 0.91, bx) * upper * sstep(0.4085, 0.4105, pbi[:, 2])
col = col * (1 - nailw[:, None]) + NAIL[None] * nailw[:, None] * (0.95 + 0.1 * n1[:, None])
ring = np.exp(-((bx - 0.875) / 0.012) ** 2) * upper * sstep(0.408, 0.411, pbi[:, 2])
# nostrils: dark oval openings on the culmen, near the base
ny = np.abs(pbi[:, 1]) - 0.0072
nxx = (bx - 0.45) / 0.036
nzz = 0.0
nos = upper & (pbi[:, 2] > 0.4185)
ell = np.sqrt(nxx ** 2 + (ny / 0.0017) ** 2)
nost = nos * (1 - sstep(0.75, 1.0, ell))
nost_rim = nos * np.exp(-((ell - 1.0) / 0.18) ** 2)
col = col * (1 - 0.92 * nost[:, None]) * (1 - 0.18 * nost_rim[:, None])
# lamellae / tomium: fine dark serrations along the mouth line
mouth_up = upper & (pbi[:, 2] < 0.4105 + 0.004 * (1 - bx))
lam = (0.5 + 0.5 * np.cos(TAU * pbi[:, 0] / 0.0011)) * sstep(0.0, 0.0018, 0.0026 - np.abs(pbi[:, 2] - (0.4075 + 0.010 * (1 - bx) ** 2)))
lam *= upper
col *= (1 - 0.28 * lam)[:, None]
# subtle dirt on the bill tip from dabbling
dn = fbm(pbi, 90, 3, 83)
dirt = sstep(0.55, 1.0, bx) * sstep(0.45, 0.8, dn) * 0.35
col = col * (1 - dirt[:, None]) + DIRT[None] * dirt[:, None]
alb[idx] = col
rough[idx] = 0.58 + 0.12 * (n2 - 0.5) + 0.08 * (n3 - 0.5) - 0.06 * nailw + 0.25 * nost + 0.15 * dirt
height[idx] = (n2 - 0.5) * 0.000030 + (n1 - 0.5) * 0.00003 + (streak_b - 0.5) * 0.000014 - nost * 0.0006 - ring * 0.00006 + lam * 0.00003
micro_ao[idx] = 1 - 0.6 * nost

# ------------------------------------------------------------------ legs, toes, webs, claws
ffeet = np.isin(part, [D.PART_LEG, D.PART_TOE, D.PART_WEB, D.PART_CLAW])
idx = np.nonzero(ffeet)[0]
pf = pos[idx]
pp = part[idx]
LEGC = np.array([0.74, 0.26, 0.040])
WEBC = np.array([0.78, 0.33, 0.085])
CLAW = np.array([0.075, 0.060, 0.050])
f1, f2, cid = worley(pf, 0.0021, 91)
scale_h = sstep(0.0, 0.14, f2 - f1)
scale_h2 = sstep(0.0, 0.25, f2 - f1)
# transverse scutes along the toes: arcs around the foot point of each side
Fp = np.stack([np.full(len(pf), -0.004), np.sign(pf[:, 1]) * D.LEG_Y, np.zeros(len(pf))], 1)
rr = np.linalg.norm((pf - Fp)[:, :2], axis=1)
scute = 0.5 + 0.5 * np.cos(TAU * rr / 0.0030)
scute_h = sstep(0.15, 0.6, scute)
n1 = fbm(pf, 300, 3, 92)
dn = fbm(pf, 120, 4, 93)
col = np.zeros((len(idx), 3))
hgt = np.zeros(len(idx))
r_ = np.zeros(len(idx))
leg = pp == D.PART_LEG
toe = pp == D.PART_TOE
web = pp == D.PART_WEB
claw = pp == D.PART_CLAW
tone = (0.88 + 0.18 * n1)[:, None] * (0.9 + 0.1 * cid)[:, None]
col[leg] = (LEGC[None] * tone)[leg] * (0.80 + 0.20 * scale_h[leg])[:, None]
hgt[leg] = scale_h[leg] * 0.00009
r_[leg] = 0.48 + 0.10 * (1 - scale_h[leg])
col[toe] = (LEGC[None] * tone)[toe] * (0.78 + 0.22 * scute_h[toe])[:, None]
hgt[toe] = scute_h[toe] * 0.00008
r_[toe] = 0.47 + 0.10 * (1 - scute_h[toe])
# webs: fine wrinkle network and radiating vessels, slightly translucent pinker orange
vein = np.exp(-((np.mod(np.arctan2((pf - Fp)[:, 1], (pf - Fp)[:, 0]) * 9.0 + 3.0 * n1, 1.0) - 0.5) / 0.06) ** 2)
wr = sstep(0.0, 0.12, f2 - f1)
col[web] = (WEBC[None] * tone)[web] * (0.86 + 0.14 * wr[web])[:, None] * (1 - 0.10 * vein[web])[:, None]
hgt[web] = wr[web] * 0.00004 - vein[web] * 0.00002
r_[web] = 0.52
col[claw] = CLAW[None] * (0.85 + 0.3 * n1[claw])[:, None]
hgt[claw] = (n1[claw] - 0.5) * 0.00002
r_[claw] = 0.36
# mud: soles, webs and grooves, patchy
mud = (sstep(0.010, 0.0, pf[:, 2]) * 0.55 + sstep(0.03, 0.0, pf[:, 2]) * 0.25) * sstep(0.35, 0.75, dn)
mud += (1 - np.maximum(scale_h, scute_h * toe)) * 0.20 * (leg | toe)
mud = np.clip(mud * (~claw), 0, 0.8)
MUD = np.array([0.20, 0.15, 0.10])
col = col * (1 - mud[:, None]) + MUD[None] * mud[:, None]
r_ = r_ + 0.25 * mud
alb[idx] = col
rough[idx] = r_
height[idx] = hgt
micro_ao[idx] = 0.85 + 0.15 * np.maximum(scale_h * (leg | web), scute_h * toe) + 0.15 * claw

# ------------------------------------------------------------------ eyes
fe = part == D.PART_EYE
idx = np.nonzero(fe)[0]
pole = pa[idx]
ang = np.arccos(np.clip(pole, -1, 1))
IRIS = np.array([0.105, 0.052, 0.022])
pe = pos[idx]
ne = fbm(pe, 3000, 3, 95)
radial = 0.5 + 0.5 * np.cos(np.arctan2(pe[:, 2] - pe[:, 2].mean(), pe[:, 0] - pe[:, 0].mean()) * 37 + ne * 6)
iris_w = 1 - sstep(0.70, 0.80, ang)
pupil = 1 - sstep(0.30, 0.36, ang)
limbus = np.exp(-((ang - 0.74) / 0.05) ** 2)
col = IRIS[None] * (0.75 + 0.5 * radial[:, None] * ne[:, None])
col = col * (1 - 0.6 * limbus[:, None])
col = col * iris_w[:, None] + np.array([0.04, 0.035, 0.03])[None] * (1 - iris_w[:, None])
col = col * (1 - pupil[:, None]) + np.array([0.004, 0.004, 0.004])[None] * pupil[:, None]
alb[idx] = col
rough[idx] = 0.035
height[idx] = 0.0
micro_ao[idx] = 1.0

# ------------------------------------------------------------------ assemble maps
log('patterns done')


def to_img(vals, ch, fill):
    img = np.empty((RES, RES, ch)) if ch > 1 else np.empty((RES, RES))
    img[...] = fill
    img[mask] = vals
    return img


def dilate(img, valid, passes=24):
    img = img.copy()
    valid = valid.copy()
    for _ in range(passes):
        acc = np.zeros_like(img)
        cnt = np.zeros(valid.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            sv_ = np.roll(np.roll(valid, dy, 0), dx, 1)
            si = np.roll(np.roll(img, dy, 0), dx, 1)
            if img.ndim == 3:
                acc += si * sv_[..., None]
            else:
                acc += si * sv_
            cnt += sv_
        new = (~valid) & (cnt > 0)
        if img.ndim == 3:
            img[new] = acc[new] / cnt[new][:, None]
        else:
            img[new] = acc[new] / cnt[new]
        valid = valid | new
    return img


# tangent-space normal from height (gradient in texel units / measured texel size)
Himg = to_img(height, 1, 0.0)
Pimg = to_img(pos, 3, 0.0)
TS = to_img(tex_m, 1, 1.0)


def grad(axis):
    fwd = np.roll(Himg, -1, axis)
    bwd = np.roll(Himg, 1, axis)
    Pf = np.roll(Pimg, -1, axis)
    Pb = np.roll(Pimg, 1, axis)
    mf = np.roll(mask, -1, axis) & (np.linalg.norm(Pf - Pimg, axis=2) < 4 * TS)
    mb = np.roll(mask, 1, axis) & (np.linalg.norm(Pb - Pimg, axis=2) < 4 * TS)
    g = np.where(mf & mb, 0.5 * (fwd - bwd), np.where(mf, fwd - Himg, np.where(mb, Himg - bwd, 0.0)))
    return g / TS


gx = grad(1)
gy = grad(0)
nx, ny, nz = -gx, -gy, np.ones_like(gx)
ln = np.sqrt(nx * nx + ny * ny + nz * nz)
Nimg = np.stack([nx / ln, ny / ln, nz / ln], 2)
Nimg[~mask] = (0, 0, 1)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)[mask]))

BC = dilate(to_img(alb, 3, 0.5), mask)
ALPHA = dilate(to_img(alpha, 1, 1.0), mask)
ORM = dilate(np.stack([to_img(np.clip(aov ** 0.9 * micro_ao, 0, 1), 1, 1.0), to_img(np.clip(rough, 0.02, 1), 1, 0.6), np.zeros((RES, RES))], 2), mask)
Nimg = dilate(Nimg, mask)
Nimg /= np.linalg.norm(Nimg, axis=2, keepdims=True)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def write_png(path, arr8):
    arr8 = np.flipud(arr8)  # PNG row 0 is the top (v = 1)
    h, w, c = arr8.shape
    raw = b''.join(b'\x00' + arr8[y].tobytes() for y in range(h))
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2 if c == 3 else 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    Path(path).write_bytes(png)


D.TEXTURES.mkdir(exist_ok=True)
paths = {'BC': D.TEXTURES / 'T_Duck_Atlas_BC.png', 'N': D.TEXTURES / 'T_Duck_Atlas_N.png', 'ORM': D.TEXTURES / 'T_Duck_Atlas_ORM.png'}
write_png(paths['BC'], np.round(np.concatenate([srgb(BC), np.clip(ALPHA, 0, 1)[..., None]], 2) * 255).astype(np.uint8))
write_png(paths['N'], np.round((Nimg * 0.5 + 0.5) * 255).astype(np.uint8))
write_png(paths['ORM'], np.round(np.clip(ORM, 0, 1) * 255).astype(np.uint8))
log('textures written')

# ------------------------------------------------------------------ material graphs (Blender source/preview)
images = {}
for key, p in paths.items():
    img = bpy.data.images.load(str(p), check_existing=False)
    img.name = p.stem
    img.colorspace_settings.name = 'sRGB' if key == 'BC' else 'Non-Color'
    img.filepath = '//../Textures/' + p.name
    images[key] = img

SHADER = {
    'MI_Duck_Feather': dict(sheen=0.22, sheen_rough=0.50, sss=0.0, coat=0.0),
    'MI_Duck_Bill': dict(sheen=0.0, sheen_rough=0.5, sss=0.18, coat=0.0),
    'MI_Duck_Feet': dict(sheen=0.0, sheen_rough=0.5, sss=0.10, coat=0.0),
    'MI_Duck_Eye': dict(sheen=0.0, sheen_rough=0.5, sss=0.0, coat=1.0),
}
for name, cfg in SHADER.items():
    mat = bpy.data.materials[name]
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    tb = nt.nodes.new('ShaderNodeTexImage')
    tb.image = images['BC']
    to = nt.nodes.new('ShaderNodeTexImage')
    to.image = images['ORM']
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = images['N']
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = 1.0
    nt.links.new(tb.outputs['Color'], bs.inputs['Base Color'])
    if name == 'MI_Duck_Feather':
        nt.links.new(tb.outputs['Alpha'], bs.inputs['Alpha'])  # cards and blood films are alpha tested
        # preview-only sheen follows the albedo, so wounds and blood stay dark and wet
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = 0.15
        mr.inputs['From Max'].default_value = 0.45
        mr.inputs['To Min'].default_value = 0.0
        mr.inputs['To Max'].default_value = cfg['sheen']
        nt.links.new(tb.outputs['Color'], bw.inputs[0])
        nt.links.new(bw.outputs[0], mr.inputs['Value'])
        nt.links.new(mr.outputs['Result'], bs.inputs['Sheen Weight'])
        mat.surface_render_method = 'DITHERED'
        mat.use_backface_culling = False
    nt.links.new(to.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[1], bs.inputs['Roughness'])
    nt.links.new(sep.outputs[2], bs.inputs['Metallic'])
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    bs.inputs['Sheen Weight'].default_value = cfg['sheen']
    bs.inputs['Sheen Roughness'].default_value = cfg['sheen_rough']
    bs.inputs['Subsurface Weight'].default_value = cfg['sss']
    bs.inputs['Subsurface Radius'].default_value = (0.004, 0.0015, 0.0008)
    bs.inputs['Subsurface Scale'].default_value = 0.01
    bs.inputs['Coat Weight'].default_value = cfg['coat']
    bs.inputs['Coat Roughness'].default_value = 0.03
    if name == 'MI_Duck_Eye':
        bs.inputs['Coat IOR'].default_value = 1.376

# ------------------------------------------------------------------ blood decal sources (ground pool + spatter)
def blood_decal(res, seed, pool=True):
    yy, xx = np.mgrid[0:res, 0:res]
    p = np.stack([(xx + 0.5) / res - 0.5, (yy + 0.5) / res - 0.5, np.zeros((res, res))], 2).reshape(-1, 3)
    r = np.linalg.norm(p[:, :2], axis=1)
    ang = np.arctan2(p[:, 1], p[:, 0])
    if pool:
        edge = 0.30 + 0.09 * (fbm(np.stack([np.cos(ang), np.sin(ang), np.zeros_like(ang)], 1) * 1.3, 1.0, 2, seed, gain=0.35) - 0.5) * 2
        body = sstep(0.010, -0.010, r - edge)
    else:
        body = np.zeros(len(p))
    drops = np.zeros(len(p))
    rnd = np.random.RandomState(seed)
    for _ in range(70 if pool else 140):
        cx, cy = rnd.uniform(-0.45, 0.45, 2) * (0.6 if not pool else 1.0)
        rad = rnd.uniform(0.004, 0.025) * (1.0 if pool else 0.8)
        if pool and np.hypot(cx, cy) < 0.25:
            continue
        drops = np.maximum(drops, sstep(0.004, -0.004, np.hypot(p[:, 0] - cx, p[:, 1] - cy) - rad))
        if rnd.rand() < 0.35:  # elongated splash tail
            dx, dy = cx / (np.hypot(cx, cy) + 1e-6), cy / (np.hypot(cx, cy) + 1e-6)
            for k in range(1, 4):
                drops = np.maximum(drops, sstep(0.003, -0.003, np.hypot(p[:, 0] - cx - dx * rad * 1.6 * k, p[:, 1] - cy - dy * rad * 1.6 * k) - rad * (0.6 ** k)))
    a = np.clip(np.maximum(body, drops), 0, 1)
    thick = sstep(0.0, 1.0, a) * (0.6 + 0.4 * fbm(p * 3, 6, 3, seed + 1))
    n_ = fbm(p, 9, 4, seed + 2)
    col = np.array([0.17, 0.006, 0.006])[None] * (0.7 + 0.5 * n_[:, None]) * (0.55 + 0.45 * thick[:, None])
    h = thick * 0.0015
    g1, g0 = np.gradient(h.reshape(res, res), 1.0 / res * 0.6)
    nn = np.stack([-g0, -g1, np.ones_like(g0)], 2)
    nn /= np.linalg.norm(nn, axis=2, keepdims=True)
    bc = np.concatenate([srgb(col.reshape(res, res, 3)), a.reshape(res, res, 1)], 2)
    rough_ = (0.06 + 0.3 * (1 - thick)).reshape(res, res)
    orm = np.stack([np.ones((res, res)), rough_, np.zeros((res, res))], 2)
    return bc, nn * 0.5 + 0.5, orm


for name, pool, seed in (('BloodPool', True, 131), ('BloodSpatter', False, 137)):
    bc, nn, orm = blood_decal(512, seed, pool)
    write_png(D.TEXTURES / ('T_Duck_%s_BC.png' % name), np.round(bc * 255).astype(np.uint8))
    write_png(D.TEXTURES / ('T_Duck_%s_N.png' % name), np.round(nn * 255).astype(np.uint8))
    write_png(D.TEXTURES / ('T_Duck_%s_ORM.png' % name), np.round(orm * 255).astype(np.uint8))
log('blood decal sources written')

stats = {
    'resolution': RES, 'texels_covered_ratio': float(mask.mean()), 'texel_size_m_median': float(np.median(tex_m)),
    'texel_density_px_per_m_median': float(1 / np.median(tex_m)),
    'normal_slope_deg_p50_p99_max': [float(np.percentile(slope_deg, 50)), float(np.percentile(slope_deg, 99)), float(slope_deg.max())],
    'albedo_linear_median_by_part': {str(p): [round(float(x), 4) for x in np.median(alb[part == p], 0)] for p in np.unique(part)},
    'albedo_linear_max': float(alb.max()),
    'roughness_median_by_part': {str(p): round(float(np.median(rough[part == p])), 3) for p in np.unique(part)},
    'vertex_ao_mean': float(ao_v.mean()),
    'seed': D.SEED,
}
(D.ROOT / 'duck_texture_report.json').write_text(json.dumps(stats, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=str(D.WORKING / 'Duck_Textured.blend'))
log('DUCK TEXTURES READY', json.dumps(stats['normal_slope_deg_p50_p99_max']))
