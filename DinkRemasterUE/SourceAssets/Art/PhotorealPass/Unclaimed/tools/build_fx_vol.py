"""One-shot effect flipbooks rendered as real volumes (art rows GP-Q9, CG-6): the shock explosion 167, the small
explosion 70, the "atomic" fire burst 161 and the blood burst 164.

Each frame is a pair of 3D fields (smoke density and flame heat) computed with numpy from analytic shapes pushed through
tileable noise, written as OpenVDB and rendered by Cycles as a volume (the fire lights its own smoke, the sun shades it),
seen from the side at 18 degrees as the camera-facing card of the game shows it. The blood burst is a mesh of drops and
gobbets with a red mist volume. Output per effect: T_FX_<name>_Flipbook.png (straight colour + alpha, frames row by row
from the top left), frames_strip.png, manifest.json. The length of each flipbook is the life of the 1997 sprite
(frames x frame delay of dink.ini), because the card lives exactly as long as the sprite.

    blender -b --factory-startup -t 4 --python Unclaimed/tools/build_fx_vol.py -- <name,name|all> [draft]
"""
import bpy, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_grade
import numpy as np
import openvdb as vdb

HERE = os.path.dirname(os.path.abspath(__file__))
UNC = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(UNC, '..', '..', '..', '..', '..'))
ELEV = math.radians(18.0)


def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, '/')


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-12), 0.0, 1.0); return t * t * (3 - 2 * t)


def ease_out(t, p=2.2):
    return 1.0 - (1.0 - np.clip(t, 0, 1)) ** p


class Noise:
    """three tileable 3D noise fields (broad, medium, fine), sampled trilinearly at metre coordinates"""

    def __init__(s, seed, n=64):
        rng = np.random.default_rng(seed); s.n = n; s.F = []
        k = np.fft.fftfreq(n) * n; KX, KY, KZ = np.meshgrid(k, k, k, indexing='ij'); K = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
        for lo, hi, beta in ((1, 4, 1.6), (3, 10, 1.5), (8, 30, 1.2)):
            sp = np.fft.fftn(rng.standard_normal((n, n, n))) * np.where((K >= lo) & (K <= hi), 1.0 / np.maximum(K, 1) ** beta, 0.0)
            f = np.real(np.fft.ifftn(sp)); f = (f - f.mean()) / (f.std() + 1e-9); s.F.append(f.astype(np.float32))

    def at(s, i, X, Y, Z, period):
        """field i (0 broad .. 2 fine) with `period` metres per tile; about -2..2, mean 0"""
        n = s.n; F = s.F[i]; u = X / period * n; v = Y / period * n; w = Z / period * n
        i0 = np.floor(u).astype(np.int32); j0 = np.floor(v).astype(np.int32); k0 = np.floor(w).astype(np.int32); fu = u - i0; fv = v - j0; fw = w - k0
        out = 0.0
        for di in (0, 1):
            for dj in (0, 1):
                for dk in (0, 1):
                    wgt = (fu if di else 1 - fu) * (fv if dj else 1 - fv) * (fw if dk else 1 - fw)
                    out = out + wgt * F[(i0 + di) % n, (j0 + dj) % n, (k0 + dk) % n]
        return out


def lattice(size, height, n):
    vs = size / n; nz = int(round(height / vs)); ax = (np.arange(n, dtype=np.float32) + 0.5) * vs - size / 2; az = (np.arange(nz, dtype=np.float32) + 0.5) * vs
    X, Y, Z = np.meshgrid(ax, ax, az, indexing='ij'); return X, Y, Z, vs


def warp(N, X, Y, Z, amp, period, drift):
    """push the sample point through broad noise: the turbulence that grows as the blast ages"""
    return (X + amp * N.at(0, X + 11.3, Y, Z - drift, period), Y + amp * N.at(0, X, Y + 7.1, Z - drift, period), Z + amp * 0.8 * N.at(0, X, Y, Z + 5.7 - drift, period))


def erode(N, body, X, Y, Z, drift, amount, period=1.1):
    """eat the soft edge of a 0..1 body with fine noise so it billows instead of being a smooth blob"""
    n = 0.6 * N.at(1, X, Y, Z - drift, period) + 0.4 * N.at(2, X + 3.0, Y, Z - drift * 1.6, period * 0.55)
    return np.clip(body * (1.0 + amount) - amount * (0.5 + 0.38 * n), 0.0, 1.0) * sstep(0.0, 0.06, body)


# ------------------------------------------------------------------------------------------------ recipes (t = 0..1)
def shock167(N, t, X, Y, Z):
    """167: a white-hot ball that swells, hollows into a ring of fire rolling outwards over the ground and breaks into separate burning clumps"""
    wx, wy, wz = warp(N, X, Y, Z, 0.05 + 0.26 * t, 2.4, 1.2 * t)
    r = np.sqrt(wx * wx + wy * wy); e = ease_out(t, 2.4)
    rc = 0.30 + 1.05 * ease_out(t / 0.5, 2.0); cz = 0.50 + 0.35 * t; ball = sstep(rc, rc * 0.55, np.sqrt(r * r + (wz - cz) ** 2 * 1.25)) * (1.0 - sstep(0.26, 0.56, t))
    R = 0.25 + 1.20 * e; a = 0.24 + 0.16 * t ** 0.6; h = 0.34 + 0.30 * t
    ring = sstep(a, a * 0.30, np.sqrt((r - R) ** 2 + (wz - h) ** 2)) * sstep(0.10, 0.34, t)
    th = np.arctan2(wy, wx); clump = N.at(1, np.cos(th) * 2.2, np.sin(th) * 2.2, Z * 0.3 + 4.0, 3.3)          # breaks the ring along its length
    ring = ring * sstep(-1.5 + 2.1 * sstep(0.42, 1.0, t), -1.5 + 2.1 * sstep(0.42, 1.0, t) + 0.5, clump + 0.9)
    body = erode(N, np.maximum(ball, ring), X, Y, Z, 1.5 * t, 0.35 + 0.9 * t) * (1.0 - sstep(0.80, 0.99, t))
    heat = body ** 1.7 * (1.0 - 0.60 * t ** 1.6) * (0.80 + 0.16 * N.at(1, X, Y, Z - 2.0 * t, 1.4))
    smoke = body * (0.20 + 0.7 * sstep(0.45, 1.0, t))
    return smoke * 2.6, heat


def splode70(N, t, X, Y, Z):
    """70: a ragged fireball that grows, burns white, then cools to pale grey smoke with sooty edges that thins from the middle"""
    wx, wy, wz = warp(N, X, Y, Z, 0.04 + 0.16 * t, 1.5, 0.9 * t)
    rc = 0.20 + 0.66 * ease_out(t / 0.7, 2.0); cz = 0.95 + 0.15 * t; d = np.sqrt(wx * wx + wy * wy + (wz - cz) ** 2)
    ball = sstep(rc, rc * 0.45, d); hollow = sstep(0.66, 0.92, t); ball = ball * (1.0 - hollow * sstep(rc * 0.86, rc * 0.50, d))
    body = erode(N, ball, X, Y, Z, 1.1 * t, 0.55 + 0.9 * t, 0.8) * (1.0 - 0.75 * sstep(0.70, 0.99, t))
    heat = body ** 1.6 * (1.0 - sstep(0.52, 0.80, t)) * (0.75 + 0.25 * sstep(0.0, 0.3, t)) * (0.80 + 0.16 * N.at(1, X, Y, Z - 1.5 * t, 1.1))
    smoke = body * (0.25 + 0.9 * sstep(0.50, 0.8, t))
    return smoke * 2.4, heat


def atomic161(N, t, X, Y, Z):
    """161: a low mound of fire, a stem that climbs out of it, a cap that rolls over the top (a small mushroom), then the whole
    mass sinks back into a wide fire that cools to grey smoke"""
    wx, wy, wz = warp(N, X, Y, Z, 0.05 + 0.22 * t, 1.6, 1.6 * t)
    r = np.sqrt(wx * wx + wy * wy); up = sstep(0.0, 0.42, t); col = 1.0 - sstep(0.50, 0.62, t)          # col: the mushroom stands until the collapse
    mound = sstep(1.0, 0.45, np.sqrt((r / (0.55 + 0.75 * sstep(0.0, 0.25, t))) ** 2 + (wz / (0.30 + 0.50 * sstep(0.0, 0.3, t))) ** 2))
    top = 0.45 + 2.05 * up; stem = sstep(0.36, 0.14, r * (1.0 + 0.25 * np.sin(wz * 3.0))) * sstep(top + 0.1, top - 0.35, wz) * sstep(0.06, 0.2, t)
    capr = 0.25 + 0.50 * sstep(0.30, 0.55, t); cap = sstep(1.0, 0.5, np.sqrt((r / capr) ** 2 + ((wz - top) / (capr * 0.62)) ** 2)) * sstep(0.26, 0.40, t)
    mush = np.maximum(np.maximum(mound, stem), cap) * col
    late = sstep(0.50, 0.64, t); lz = 0.75 + 0.45 * sstep(0.6, 1.0, t)
    mass = sstep(1.0, 0.42, np.sqrt((wx / (1.15 + 0.25 * t)) ** 2 + (wy / 0.9) ** 2 + ((wz - lz) / (0.62 + 0.25 * t)) ** 2)) * late
    body = erode(N, np.maximum(mush, mass), X, Y, Z, 1.8 * t, 0.45 + 0.8 * t, 0.9) * (1.0 - sstep(0.88, 0.995, t))
    heat = body ** 1.6 * (1.0 - sstep(0.74, 0.93, t)) * (0.8 + 0.2 * col) * (0.80 + 0.16 * N.at(1, X, Y, Z - 2.2 * t, 1.2))
    smoke = body * (0.25 + 1.0 * sstep(0.70, 0.92, t))
    return smoke * 2.6, heat


def blood164(N, t, X, Y, Z):
    """the red mist inside the burst: thick while the ball is tight, gone as the drops fly apart"""
    wx, wy, wz = warp(N, X, Y, Z, 0.04 + 0.2 * t, 1.2, 0.3 * t); rb = 0.30 + 0.95 * ease_out(t, 1.8); d = np.sqrt(wx * wx + wy * wy + (wz - 1.0) ** 2)
    body = erode(N, sstep(rb, rb * 0.3, d), X, Y, Z, 0.4 * t, 0.5 + 0.6 * t, 0.7) * (1.0 - sstep(0.10, 0.50, t))
    return body * 6.0, body * 0.0


def blood_drops(t, seed=5):
    """(centres, radii, stretch axis, stretch) of the drops at time t: a tight ball of 4,200 that flies apart, the far drops living longest"""
    rng = np.random.default_rng(seed); n = 4200; d = rng.standard_normal((n, 3)); d /= np.linalg.norm(d, axis=1)[:, None]
    u = rng.random(n) ** (1 / 2.2); r0 = 0.30 * u; r1 = 1.50 * u ** 0.75 * (0.75 + 0.5 * rng.random(n)); rad = (0.010 + 0.022 * rng.random(n) ** 2.5) * (1.0 + 1.6 * (rng.random(n) > 0.97))
    e = ease_out(t, 2.2); r = r0 + (r1 - r0) * e; P = d * r[:, None]; P[:, 2] += 1.0 - 0.55 * t * t * (0.4 + 0.6 * rng.random(n))          # gravity late
    life = 0.80 + 0.55 * rng.random(n) * (0.4 + 0.6 * u); keep = (t < life) & (P[:, 2] > 0.02)
    shrink = np.clip((life - t) / 0.12, 0.0, 1.0) * (1.0 - 0.15 * t); speed = (r1 - r0) * 1.7 * (1.0 - min(t, 1.0)) ** 0.7
    return P[keep], (rad * shrink)[keep], d[keep], (1.0 + 0.7 * speed)[keep]


def _fire(N, t, X, Y, Z, seats, glow_r):
    """a standing fire that loops: every noise field climbs a whole number of its own periods over the loop, so the last
    frame meets the first. seats = [(x, y, base radius, height, noise offset)]: one tongue of flame each; glow_r = radius of
    the bed of embers under them."""
    n1 = lambda ox: N.at(0, X + ox, Y + ox * 0.7, Z - 4.0 * t, 2.0)          # 2 periods of 2 m: the big licks
    body = 0.0; heat = 0.0
    for (sx, sy, rb, hh, off) in seats:
        sw = 0.20 * rb / 0.4 * (Z / hh + 0.1); wx = X - sx + sw * N.at(0, X + off, Y, Z - 4.0 * t, 2.0) + 0.5 * sw * N.at(1, X + off, Y, Z - 3.0 * t, 1.0); wy = Y - sy + sw * N.at(0, X, Y + off + 3.3, Z - 4.0 * t, 2.0)
        top = hh * (0.80 + 0.22 * n1(off)); zz = np.clip(Z / np.maximum(top, 0.05), 0.0, 1.5)
        allow = rb * np.clip(1.0 - zz, 0.0, 1.0) ** 1.15 * (0.55 + 0.45 * sstep(0.0, 0.18, zz)) * (1.0 + 0.18 * np.sin(zz * 6.0 + off + 6.2832 * t)); r = np.sqrt(wx * wx + wy * wy)
        b = sstep(allow, allow * 0.25, r) * (allow > 0.0)
        fine = N.at(1, X + off, Y + off, Z - 3.0 * t, 1.0)
        b = np.clip(b * (1.15 + 0.3 * zz) - (0.15 + 0.3 * zz) * (0.5 + 0.35 * fine), 0.0, 1.0) * sstep(0.0, 0.10, b)
        core = np.clip(1.0 - r / (allow + 1e-3), 0.0, 1.0) ** 0.75          # hottest on the tongue's axis, cool at its skin
        body = np.maximum(body, b); heat = np.maximum(heat, (b * core) ** 1.1 * (1.0 - 0.55 * np.clip(zz, 0, 1) ** 1.2))
    bed = sstep(glow_r, glow_r * 0.5, np.sqrt(X * X + Y * Y * 1.6)) * sstep(0.16, 0.02, Z) * (0.75 + 0.2 * N.at(2, X, Y, Z + 2.0 * t * 0.0, 0.5))
    heat = np.maximum(heat, bed * 0.55); body = np.maximum(body, bed)
    return body * 0.22 + bed * 0.6, heat          # a flame is light with very little body; the ember bed is solid


def hearth86(N, t, X, Y, Z):
    """86: a hearth fire: a row of low flames over glowing logs, 0.9 m wide"""
    return _fire(N, t, X, Y, Z, [(-0.26, 0.0, 0.16, 0.66, 1.0), (0.0, 0.03, 0.19, 0.86, 6.1), (0.25, -0.02, 0.15, 0.60, 12.4), (0.12, 0.06, 0.11, 0.46, 17.0)], 0.45)


FX = {
    'Shock': dict(fam='explosion_fx', fn=shock167, seq=167, life_s=0.42, size=4.2, height=2.9, grid=(4, 4), cell=512, seed=3, glow=1.6, emit=5.0, strip=(1, 4, 7, 10, 13),
                  dresses='explosion 167, 0.42 s: a white-hot ball 2.6 m across that hollows into a ring of fire rolling out to 4 m over the ground and breaks into burning clumps with dark smoke',
                  weak='The motion is an analytic shape pushed through noise, not a fluid simulation: the ring does not curl as a real vortex ring would and there is no ground flash, debris or light on the scene (a point light is runtime work).'),
    'Splode': dict(fam='explosion_small_fx', fn=splode70, seq=70, life_s=0.60, size=2.4, height=2.4, grid=(4, 4), cell=512, seed=8, glow=1.6, emit=5.0, strip=(1, 4, 7, 10, 13),
                   dresses='explosion 70, 0.6 s: a ragged fireball growing to 2.1 m, white-hot, cooling to pale grey smoke with sooty edges that opens into a ring of soot',
                   weak='Analytic shape and noise, not a simulation; no sparks or debris, no light on the scene.'),
    'Atomic': dict(fam='fire_burst_fx', fn=atomic161, seq=161, life_s=1.30, size=3.6, height=3.6, grid=(8, 4), cell=512, seed=12, glow=1.6, emit=5.0, strip=(2, 8, 14, 18, 23, 28),
                   dresses='fire burst 161, 1.3 s: a mound of fire, a stem climbing to 3 m with a cap rolling over it, the collapse into a wide burning mass and grey smoke',
                   weak='Analytic shapes and noise: the cap does not roll as a real thermal does. No light on the scene.'),
    'Blood_Burst': dict(fam='blood_burst_fx', fn=blood164, seq=164, life_s=0.70, size=3.2, height=3.2, grid=(8, 4), cell=512, seed=21, glow=1.0, emit=0.0, strip=(0, 7, 14, 21, 28), drops=True,
                        dresses='blood burst 164, 0.7 s: a tight dark red ball of 4,200 drops and gobbets in a red mist that bursts to 3 m and falls apart into specks',
                        weak='Drops are stretched spheres on straight paths (no splitting, no strings of blood); nothing lands on the ground (stains are the decal layer).'),
    'Hearth': dict(fam='hearth_fire', fn=hearth86, seq=86, life_s=1.6, loop=True, size=1.05, height=1.0, grid=(8, 8), cell=256, seed=41, glow=3.0, emit=5.0, soot=True, strip=(0, 12, 24, 36, 48, 60),
                   dresses='hearth fire (86), a 1.6 s loop: a row of four low flames to 0.7 m over glowing embers, 0.9 m wide',
                   weak='Flames and an ember bed only: the logs, the fire back and the surround of the 1997 picture are the fireplace mesh\'s job.'),
}


def scene_setup(size, draft):
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; sc.render.engine = 'CYCLES'
    if not os.environ.get('DINK_CPU'):
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'HIP'; prefs.refresh_devices()
            for dv in prefs.devices:
                dv.use = (dv.type == 'HIP' and 'Radeon RX 6800' in dv.name)
            sc.cycles.device = 'GPU'; print('CYCLES DEVICES IN USE:', [(dv.name, dv.type) for dv in prefs.devices if dv.use])
            if not any(dv.use for dv in prefs.devices):
                raise SystemExit('the Radeon RX 6800 HIP device was not found: not rendering on another GPU')
        except SystemExit:
            raise
        except Exception as ex:
            print('HIP not available:', ex)
    sc.cycles.samples = 24 if draft else 96; sc.cycles.use_denoising = True; sc.render.film_transparent = True; sc.cycles.volume_step_rate = 1.0 if draft else 0.5; sc.cycles.volume_bounces = 2; sc.cycles.max_bounces = 6
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    for k in dir(sc.render):
        if k.startswith('use_stamp'):
            try:
                setattr(sc.render, k, False)
            except Exception:
                pass
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.50, 0.60, 0.78, 1); bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 3.2; sun.data.angle = math.radians(2.0); sun.rotation_euler = (math.radians(48), 0, math.radians(35))
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = size; cam.data.clip_end = 100.0
    half = size / 2; dist = 20.0          # the card's centre stands 0.9 x half its size over the sprite's ground point (UDinkArtFamilySubsystem)
    cam.location = (0.0, -dist * math.cos(ELEV), dist * math.sin(ELEV) + half * 0.9 * math.cos(ELEV)); cam.rotation_euler = (math.pi / 2 - ELEV, 0.0, 0.0)
    return sc


def fire_material(emit, mist=None):
    mat = bpy.data.materials.new('fx_volume'); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear(); out = nt.nodes.new('ShaderNodeOutputMaterial'); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Blackbody Intensity'].default_value = 0.0; pv.inputs['Density'].default_value = 1.0; pv.inputs['Anisotropy'].default_value = 0.2
    pv.inputs['Color'].default_value = (mist + (1.0,)) if mist else (0.42, 0.40, 0.38, 1.0)
    if emit > 0:
        fl = nt.nodes.new('ShaderNodeAttribute'); fl.attribute_name = 'flame'; ramp = nt.nodes.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
        stops = [(0.0, (0.0, 0.0, 0.0)), (0.07, (0.32, 0.012, 0.0)), (0.20, (0.95, 0.11, 0.006)), (0.40, (1.0, 0.36, 0.035)), (0.65, (1.0, 0.70, 0.20)), (1.0, (1.0, 0.92, 0.66))]
        cr.elements[0].position = 0.0; cr.elements[0].color = stops[0][1] + (1,); cr.elements[1].position = 1.0; cr.elements[1].color = stops[-1][1] + (1,)
        for p_, c_ in stops[1:-1]:
            el = cr.elements.new(p_); el.color = c_ + (1,)
        nt.links.new(fl.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], pv.inputs['Emission Color'])
        pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6; nt.links.new(fl.outputs['Fac'], pw.inputs[0])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = emit; nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], pv.inputs['Emission Strength'])
    nt.links.new(pv.outputs[0], out.inputs['Volume']); return mat


def drops_mesh(ob, P, R, D, S):
    """rebuild the drop mesh: one stretched icosphere per drop"""
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0); V0 = np.array([v.co[:] for v in bm.verts], np.float32); F0 = np.array([[v.index for v in f.verts] for f in bm.faces], np.int32); bm.free()
    n = len(P); along = (V0 @ D.T).T                                              # (n, nv): component of each unit vertex along the drop's flight
    V = V0[None, :, :] + along[:, :, None] * D[:, None, :] * (S[:, None, None] - 1.0)
    V = V * R[:, None, None] + P[:, None, :]; F = F0[None, :, :] + (np.arange(n) * len(V0))[:, None, None]
    me = bpy.data.meshes.new('drops'); me.from_pydata(V.reshape(-1, 3).tolist(), [], F.reshape(-1, 3).tolist()); me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.update()
    old = ob.data; ob.data = me; me.materials.append(bpy.data.materials['blood'])
    if old and old.users == 0:
        bpy.data.meshes.remove(old)


def build(name, draft):
    sp = FX[name]; outdir = os.path.join(UNC, sp['fam'], name); os.makedirs(outdir, exist_ok=True); tmp = os.path.join(os.environ.get('DINK_FX_TMP') or os.path.join(UNC, '_review'), 'fx_' + name); os.makedirs(tmp, exist_ok=True)
    cols, rows = sp['grid']; nf = cols * rows; cell = sp['cell'] // (2 if draft else 1); sc = scene_setup(sp['size'], draft); sc.render.resolution_x = sc.render.resolution_y = cell
    if sp.get('agx'):
        sc.view_settings.view_transform = 'AgX'          # a filmic shoulder: hot cores roll off to pale yellow instead of clipping
    N = Noise(sp['seed']); X, Y, Z, vs = lattice(sp['size'] * 1.04, sp['height'], 72 if draft else 128)
    vol = bpy.data.objects.new('vol', bpy.data.volumes.new('vol')); sc.collection.objects.link(vol); vol.location = (-sp['size'] * 1.04 / 2, -sp['size'] * 1.04 / 2, 0.0); vol.scale = (vs, vs, vs)
    vol.data.materials.append(fire_material(sp['emit'], mist=(0.045, 0.0, 0.0) if sp.get('drops') else ((0.03, 0.022, 0.016) if sp.get('soot') else None)))
    drops = None
    if sp.get('drops'):
        bm = bpy.data.materials.new('blood'); bm.use_nodes = True; b = bm.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.21, 0.002, 0.002, 1); b.inputs['Roughness'].default_value = 0.34
        b.inputs['Subsurface Weight'].default_value = 0.0; b.inputs['Coat Weight'].default_value = 0.0; b.inputs['Specular IOR Level'].default_value = 0.35
        drops = bpy.data.objects.new('drops', bpy.data.meshes.new('drops0')); sc.collection.objects.link(drops)
    frames = []
    for i in range(nf):
        t = (i / nf) if sp.get('loop') else (i + 0.5) / nf; dens, flame = sp['fn'](N, t, X, Y, Z); path = os.path.join(tmp, 'f_%03d.vdb' % i)
        g1 = vdb.FloatGrid(); g1.copyFromArray(np.ascontiguousarray(dens, np.float32), tolerance=1e-4); g1.name = 'density'; g2 = vdb.FloatGrid(); g2.copyFromArray(np.ascontiguousarray(np.clip(flame, 0, 1), np.float32), tolerance=1e-4); g2.name = 'flame'
        vdb.write(path, grids=[g1, g2]); old = vol.data; vd = bpy.data.volumes.new('vol%d' % i); vd.filepath = path; vd.materials.append(old.materials[0]); vol.data = vd; bpy.data.volumes.remove(old)
        if drops:
            drops_mesh(drops, *blood_drops(t))
        sc.frame_set(i + 1); sc.render.filepath = os.path.join(tmp, 'f_%03d.png' % i); bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(sc.render.filepath); px = np.array(img.pixels[:], np.float32).reshape(cell, cell, 4)[::-1]; bpy.data.images.remove(img); frames.append(px); os.remove(path)
        print('FRAME', name, i, 'alpha %.3f' % float(px[..., 3].mean())); sys.stdout.flush()
    atlas = np.zeros((rows * cell, cols * cell, 4), np.float32)
    for i, px in enumerate(frames):
        # the render is premultiplied and fire adds light where there is little smoke: give the light its own cover, then store straight colour
        rgb = px[..., :3]; a = np.clip(np.maximum(px[..., 3], np.clip(rgb.max(-1) * 1.15, 0, 1)), 0, 1); col = np.where(a[..., None] > 1e-3, rgb / np.maximum(a[..., None], 1e-3), 0.0)
        edge = np.minimum.reduce([np.arange(cell)[None, :] + 0 * a, np.arange(cell)[::-1][None, :] + 0 * a, np.arange(cell)[:, None] + 0 * a, np.arange(cell)[::-1][:, None] + 0 * a]); a = a * np.clip(edge / 6.0, 0, 1)
        if not sp.get('drops') and not sp.get('loop'):
            a = a * (1.0 - 0.92 * sstep(0.84, 1.0, (i + 0.5) / nf))          # the last frames thin out instead of leaving a grey veil
        r_, c_ = divmod(i, cols); atlas[r_ * cell:(r_ + 1) * cell, c_ * cell:(c_ + 1) * cell] = np.concatenate([np.clip(col, 0, 1), a[..., None]], -1)
    if sp.get('emit', 0) > 0 and not sp.get('loop'):      # fire: orange in the game, no veil of light round the shapes (fx_grade.py)
        atlas = fx_grade.grade(atlas)
    from_lin = lambda x: x          # the PNG pixels were read back in the file's own (sRGB) encoding
    out8 = (np.clip(from_lin(atlas), 0, 1) * 255 + 0.5).astype(np.uint8)
    img = bpy.data.images.new('atlas', cols * cell, rows * cell, alpha=True); img.alpha_mode = 'STRAIGHT'; img.colorspace_settings.name = 'sRGB'
    tex = os.path.join(outdir if not draft else tmp, 'T_FX_%s_Flipbook.png' % name)
    _save_png(out8, tex)
    green = np.array((74, 112, 54), np.float32) / 255; st = [atlas[(k // cols) * cell:(k // cols + 1) * cell, (k % cols) * cell:(k % cols + 1) * cell] for k in sp['strip']]
    s = np.concatenate(st, 1)[::2, ::2]; comp = s[..., :3] * s[..., 3:4] + green * (1 - s[..., 3:4]); _save_png((np.clip(comp, 0, 1) * 255 + 0.5).astype(np.uint8), os.path.join(outdir if not draft else tmp, 'frames_strip.png'))
    if draft:
        print('DRAFT', tmp); return
    man = {'name': 'FX_' + name, 'class': 'effect flipbook (texture atlas; no mesh)', 'lod0_triangles': 0, 'dimensions_m': [sp['size'], sp['size'], 0.0],
           'textures': [{'file': rel(tex), 'size_px': [cols * cell, rows * cell], 'channels': 'RGB straight colour (sRGB) + alpha; %d x %d frames of %d px, row by row from the top left' % (cols, rows, cell)}],
           'flipbook': {'frames': nf, 'grid': [cols, rows], 'fps': round(nf / sp['life_s'], 2), 'loop': bool(sp.get('loop')), 'billboard_size_m': [sp['size'], sp['size']], 'blend': 'alpha; hot texels glow', 'ue_blend': 'alpha', 'glow': sp['glow'], **({'hot': fx_grade.HOT, 'graded': True} if sp.get('emit', 0) > 0 and not sp.get('loop') else {}),
                        'life_s': sp['life_s'], 'ground_line': 'the sprite\'s ground point is 5 % of the frame above its bottom edge; side view at 18 degrees'},
           'preview': rel(os.path.join(outdir, 'frames_strip.png')), 'source_note': 'frames are computed by the build script (seeded, deterministic): numpy fields -> OpenVDB -> Cycles volume render; no .blend is kept',
           'build': 'blender -b --factory-startup -t 4 --python Unclaimed/tools/build_fx_vol.py -- ' + name,
           'families': [sp['fam'], '%d (sequence of the 1997 sprite)' % sp['seq']], 'origin_ids': {}, 'supersedes': 'none (grey script-sprite marker)', 'dresses': sp['dresses'], 'third_party': [],
           'status': 'source delivered', 'known_weaknesses': sp['weak'] + ' A flipbook on a camera-facing card: it has no depth against the scene and casts no light.'}
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', outdir)


def _save_png(arr8, path):
    h, w, c = arr8.shape; img = bpy.data.images.new('out', w, h, alpha=(c == 4)); img.alpha_mode = 'STRAIGHT'
    a = arr8[::-1].astype(np.float32) / 255.0
    if c == 3:
        a = np.concatenate([a, np.ones((h, w, 1), np.float32)], -1)
    img.colorspace_settings.name = 'Non-Color'; img.pixels.foreach_set(a.ravel()); img.filepath_raw = path; img.file_format = 'PNG'
    sc = bpy.context.scene; old = (sc.render.image_settings.color_mode, sc.view_settings.view_transform); sc.render.image_settings.color_mode = 'RGBA' if c == 4 else 'RGB'
    img.save_render(path, scene=None) if False else img.save(); bpy.data.images.remove(img); print('WROTE', path)


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['all']; names = list(FX) if a[0] == 'all' else a[0].split(','); draft = len(a) > 1 and a[1] == 'draft'
    for n in names:
        build(n, draft)
