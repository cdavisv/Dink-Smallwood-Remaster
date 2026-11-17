"""Port the people of PhotorealPass/Unclaimed onto the game's 89-bone mannequin rig, so the humanoid component can
animate them with the clips the Mother and Milder use.

The Unclaimed people stand on the 26-bone "project humanoid" (the core bones of the mannequin, same names, other joint
positions and no clips). Here every LOD mesh is carried, by its own skin weights, from its joints to the mannequin's
(one affine map per bone: the bone's segment goes onto the mannequin's segment, thickness scales with the body height),
its vertex groups keep their names, and it is bound to the mannequin armature taken from a Characters blend. Long things
held in a hand (halberd, staff, pole) cannot follow a hand that has no hold pose: they are stood upright beside the body
and bound to the root.

    blender -b -t 4 --python npc_port.py -- <Name[,Name]|all> [work dir]

Writes Characters/NPC/<Name>/Work-free output: Export/SK_<Name>_Photoreal_LOD0-3.fbx, export_report.json, generated
filler textures under Textures/, manifest.json (schema dink-photoreal-character/1; the other textures stay where they
are, under Unclaimed/, and the manifest points at them). The intermediate .blend goes to the work dir (default: the
system temp folder) and is not kept: this script rebuilds it from the Unclaimed source."""
import bpy, sys, os, json, subprocess, tempfile, math
import numpy as np
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from npcs import NPCS
CHARS = HERE.parent; PASS = CHARS.parent; UNC = PASS / 'Unclaimed'; OUT = CHARS / 'NPC'
argv = sys.argv[sys.argv.index('--') + 1:]
names = list(NPCS) if argv[0] == 'all' else argv[0].split(',')
WORK = Path(argv[1]) if len(argv) > 1 else Path(tempfile.gettempdir())
CHILD = {'pelvis': 'spine_01', 'spine_01': 'spine_02', 'spine_02': 'spine_03', 'spine_03': 'spine_04', 'spine_04': 'spine_05', 'spine_05': 'neck_01',
         'neck_01': 'neck_02', 'neck_02': 'head'}
for s in 'lr':
    CHILD.update({f'clavicle_{s}': f'upperarm_{s}', f'upperarm_{s}': f'lowerarm_{s}', f'lowerarm_{s}': f'hand_{s}', f'thigh_{s}': f'calf_{s}',
                  f'calf_{s}': f'foot_{s}', f'foot_{s}': f'ball_{s}'})
TRUNK = ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05')
LIKE = {'hand_l': 'lowerarm_l', 'hand_r': 'lowerarm_r', 'ball_l': 'foot_l', 'ball_r': 'foot_r'}   # leaf bones turn with their parent


def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = float(a @ b); s = np.linalg.norm(v)
    if s < 1e-8: return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]) / s
    return np.eye(3) + k * s + k @ k * (1 - c)


def bone_maps(src, dst):
    """src, dst: {bone: head}. Returns {bone: (A 3x3, t 3)} with v' = A v + t, and the height ratio g."""
    g = dst['head'][2] / src['head'][2]; M = {}; R = {}
    # The trunk goes over as ONE map (pelvis onto pelvis, base of the neck onto base of the neck: a stretch in height and
    # a slight lean, thickness by g). The two rigs place the spine joints at different heights; joint-exact maps per
    # spine bone squeezed the waist to a third and gave every figure a paunch.
    dz = src['neck_01'][2] - src['pelvis'][2]; e = dst['neck_01'] - dst['pelvis']; f = src['neck_01'] - src['pelvis']
    T = np.array([[g, 0, (e[0] - g * f[0]) / dz], [0, g, (e[1] - g * f[1]) / dz], [0, 0, e[2] / dz]])
    for b in src:
        if b in TRUNK:
            M[b] = (T, dst['pelvis'] - T @ src['pelvis']); continue
        if b in CHILD and CHILD[b] in src:
            ds = src[CHILD[b]] - src[b]; dt = dst[CHILD[b]] - dst[b]; ls = np.linalg.norm(ds); u = ds / ls
            R[b] = rot_between(ds, dt); S = g * np.eye(3) + (np.linalg.norm(dt) / ls - g) * np.outer(u, u)   # length along the bone, g across it
            A = R[b] @ S
        elif b in LIKE and LIKE[b] in R:
            A = R[LIKE[b]] * g
        else:
            A = np.eye(3) * g
        M[b] = (A, dst[b] - A @ src[b])
    return M, g


def components(me):
    n = len(me.vertices); parent = np.arange(n)
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b: parent[a] = b
    return np.array([find(i) for i in range(n)])


LIMBS = (('upperarm', 'lowerarm', 'clavicle', .046), ('lowerarm', 'hand', None, .038), ('thigh', 'calf', 'pelvis', .074), ('calf', 'foot', None, .050))


def add_body(lods, dst, cfg):
    """A body under a harness of rigid plates (the knight): the source is plates only, so at the armpits, elbows,
    knees, hips and neck one looked through the figure. Limbs are tubes from joint to joint with a ball at each joint,
    the trunk a loft of ellipses from the hips to the neck, all sized from the plates around them (inside their inner
    face) and skinned to the bones with blended rings at the joints. They wear the mail of the harness's own texture:
    every quad shows the mail patch `uv` (centre) +- `half` of the atlas, mirrored from quad to quad so it tiles."""
    import bmesh
    o0 = lods[0]; me0 = o0.data; n = len(me0.vertices); co = np.empty(n * 3); me0.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    names = [g.name for g in o0.vertex_groups]; W = np.zeros((n, len(names)))
    for v in me0.vertices:
        for ge in v.groups: W[v.index, ge.group] = ge.weight
    def of(bone): return W[:, names.index(bone)] > .5 if bone in names else np.zeros(n, bool)
    def radius(a, b, default):
        A, B = dst[a], dst[b]; ax = (B - A) / np.linalg.norm(B - A); sel = co[of(a)]
        if len(sel) < 12: return default
        t = (sel - A) @ ax / np.linalg.norm(B - A); mid = sel[(t > .2) & (t < .8)]
        if len(mid) < 8: return default
        d = np.linalg.norm((mid - A) - np.outer((mid - A) @ ax, ax), axis=1)
        return float(np.clip(np.percentile(d, 15) * cfg.get('inside', .90), default * .6, default * 1.5))
    parts = []      # (rings: list of (centre, x axis, y axis, rx, ry, {bone: weight}))
    def frame(ax):
        ref = np.array([0.0, 1.0, 0.0]) if abs(ax[1]) < .9 else np.array([1.0, 0.0, 0.0])
        x = np.cross(ref, ax); x /= np.linalg.norm(x); return x, np.cross(ax, x)
    for base, child, parent, default in LIMBS:
        for sd in 'lr':
            a, b = f'{base}_{sd}', f'{child}_{sd}'; A, B = dst[a], dst[b]; ax = (B - A) / np.linalg.norm(B - A); x, y = frame(ax); r = radius(a, b, default)
            par = (f'{parent}_{sd}' if parent == 'clavicle' else parent) if parent else None
            rings = []
            for k in range(7):
                t = k / 6; w = {a: 1.0}
                if k == 6: w = {a: .5, b: .5}
                elif k == 0 and par: w = {a: .6, par: .4}
                taper = 1.0 - .12 * t
                rings.append((A + (B - A) * t, x, y, r * taper, r * taper, w))
            parts.append(rings)
            # the ball in the joint at the head of the segment (shoulder, elbow, hip, knee)
            ball = []; w = {a: .5, par: .5} if par else {a: .5, {'lowerarm': f'upperarm_{sd}', 'calf': f'thigh_{sd}'}[base]: .5}
            for k in range(1, 6):
                th = math.pi * k / 6; ball.append((A + ax * math.cos(th) * -r * 1.08, x, y, r * 1.08 * math.sin(th), r * 1.08 * math.sin(th), w))
            parts.append(ball)
    # the trunk: ellipses through the spine, sized from the plates at each height
    trunk = []; chain = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02']
    body = np.zeros(n, bool)
    for bn in chain: body |= of(bn)
    for i, bn in enumerate(chain):
        c = dst[bn].copy(); sl = co[body & (np.abs(co[:, 2] - c[2]) < .05)]
        if len(sl) >= 10 and not bn.startswith('neck'):
            yc = float(np.median(sl[:, 1])); rx = float(np.percentile(np.abs(sl[:, 0]), 55)) * cfg.get('inside', .90); ry = float(np.percentile(np.abs(sl[:, 1] - yc), 55)) * cfg.get('inside', .90); c[1] = yc
        else:
            rx, ry = (.062, .060) if bn.startswith('neck') else (.15, .11)
        trunk.append((c, np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), rx, ry, {bn: 1.0}))
    hip = trunk[0]; trunk.insert(0, (hip[0] - np.array([0, 0, .09]), hip[1], hip[2], hip[3] * .9, hip[4] * .9, {'pelvis': 1.0}))
    head = dst['head']; trunk.append((head + np.array([0, 0, .03]), trunk[-1][1], trunk[-1][2], .058, .058, {'head': 1.0}))
    parts.append(trunk)
    U, Vc = cfg['uv']; H = cfg['half']; SIDES = 10; added = 0
    for o in lods:
        me = o.data; bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.verify(); uvl = bm.loops.layers.uv.verify()
        gi = {g.name: g.index for g in o.vertex_groups}
        for rings in parts:
            rows = []
            for c, x, y, rx, ry, w in rings:
                row = []
                for j in range(SIDES):
                    ang = 2 * math.pi * j / SIDES; v = bm.verts.new(c + x * rx * math.cos(ang) + y * ry * math.sin(ang))
                    for bone, wt in w.items():
                        if bone not in gi: gi[bone] = o.vertex_groups.new(name=bone).index
                        v[dl][gi[bone]] = wt
                    row.append(v)
                rows.append(row)
            for i in range(len(rows) - 1):
                for j in range(SIDES):
                    quad = (rows[i][j], rows[i][(j + 1) % SIDES], rows[i + 1][(j + 1) % SIDES], rows[i + 1][j])
                    try: f = bm.faces.new(quad)
                    except ValueError: continue
                    f.smooth = True; f.material_index = 0
                    for loop, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                        uu = du if j % 2 == 0 else 1 - du; vv = dv if i % 2 == 0 else 1 - dv
                        loop[uvl].uv = (U + (uu * 2 - 1) * H, Vc + (vv * 2 - 1) * H)
                    added += 1
        bm.normal_update(); bm.to_mesh(me); bm.free(); me.update()
    return {'body_quads_per_lod': added // len(lods)}


def port_static(name):
    """A set piece that never moves (the king on his throne): the whole mesh on the root bone, LODs by decimation.
    It goes through the character path only so that the same placement binding and material kinds apply."""
    cfg = NPCS[name]; asset = cfg['asset']; src = bpy.data.objects[asset]; new_name = f'SK_{name}_Photoreal'
    for o in list(bpy.data.objects):
        if o is not src: bpy.data.objects.remove(o, do_unlink=True)
    with bpy.data.libraries.load(str(CHARS / 'Milder/SK_Milder_Photoreal.blend')) as (s_, d): d.objects = ['Armature']
    arm = d.objects[0]; bpy.context.scene.collection.objects.link(arm); arm.name = 'Armature'
    if arm.animation_data: arm.animation_data.action = None
    lods = []; stats = {'height_ratio': 1.0, 'static': True, 'lods': []}
    for i, ratio in enumerate((1.0, .5, .25, .12)):
        o = src.copy(); o.data = src.data.copy(); bpy.context.scene.collection.objects.link(o)
        if ratio < 1:
            m = o.modifiers.new('d', 'DECIMATE'); m.ratio = ratio; bpy.context.view_layer.update()
            me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); o.modifiers.clear(); o.data = me
        o.name = f'{new_name}_LOD{i}'; o.data.name = o.name; o.vertex_groups.clear(); o.vertex_groups.new(name='root').add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        o.modifiers.new('Armature', 'ARMATURE').object = arm; o.hide_render = i != 0; lods.append(o)
        stats['lods'].append({'vertices': len(o.data.vertices), 'pole_vertices': 0})
    bpy.data.objects.remove(src, do_unlink=True); slots = {}
    for s_ in lods[0].material_slots:
        slot = s_.material.name.split('_PR_')[-1]; s_.material.name = f'MI_{name}_PR_{slot}'; slots[s_.material.name] = slot
    blend = WORK / f'{new_name}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=False)
    print('[PR] ported static', name, json.dumps(stats), flush=True)
    return blend, slots, stats


def port(name):
    cfg = NPCS[name]; src_dir = UNC / cfg['src']; asset = cfg['asset']; out = OUT / name; (out / 'Textures').mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(src_dir / (asset + '.blend')))
    if cfg.get('static'): return port_static(name)
    sarm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); lods = [bpy.data.objects[f'{asset}_LOD{i}'] for i in range(4)]
    for o in list(bpy.data.objects):
        if o is not sarm and o not in lods: bpy.data.objects.remove(o, do_unlink=True)
    with bpy.data.libraries.load(str(CHARS / 'Milder/SK_Milder_Photoreal.blend')) as (s, d): d.objects = ['Armature']
    arm = d.objects[0]; bpy.context.scene.collection.objects.link(arm); arm.name = 'Armature'
    if arm.animation_data: arm.animation_data.action = None
    src = {b.name: np.array(sarm.matrix_world @ b.head_local) for b in sarm.data.bones}
    dst = {b.name: np.array(arm.matrix_world @ b.head_local) for b in arm.data.bones}
    M, g = bone_maps(src, dst); g = float(g); new_name = f'SK_{name}_Photoreal'; stats = {'height_ratio': round(g, 4), 'lods': []}
    for i, o in enumerate(lods):
        me = o.data; n = len(me.vertices); co = np.empty(n * 3, np.float64); me.vertices.foreach_get('co', co); co = (co.reshape(-1, 3) @ np.array(o.matrix_world.to_3x3()).T) + np.array(o.matrix_world.translation)
        gnames = [vg.name for vg in o.vertex_groups]; W = np.zeros((n, len(gnames)))
        for v in me.vertices:
            for ge in v.groups: W[v.index, ge.group] = ge.weight
        if W.shape[1] > 4:      # four influences a vertex, as the main characters have (the decimated LODs carry up to seven)
            small = np.argsort(W, axis=1)[:, :-4]; np.put_along_axis(W, small, 0.0, axis=1)
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9); newco = np.zeros((n, 3)); trimmed = True
        # The face is rigid on the head bone. The source weights the skin of the face partly to the neck (a quarter at eye
        # level) while the eyeballs are all head: when the mannequin's clips turn or nod the head, the eyeballs travelled
        # centimetres behind the lids and the iris went under them (the "eyes without an iris" of the first import).
        # Everything within 7 cm of an eye (skin, lids, brow and lash cards, the fringe) takes the head bone alone,
        # fading out to the source weights at 12 cm.
        eye_slots = [k for k, s_ in enumerate(o.material_slots) if s_.material and s_.material.name.endswith('_Eyes')]
        if eye_slots and 'head' in gnames:
            ev = sorted({v for p_ in me.polygons if p_.material_index in eye_slots for v in p_.vertices}); ec = co[ev]
            centres = [ec[ec[:, 0] * sg > 0].mean(0) for sg in (1, -1) if (ec[:, 0] * sg > 0).any()]
            if centres:
                dist = np.min([np.linalg.norm(co - c_, axis=1) for c_ in centres], axis=0)
                rigid = np.clip((.12 - dist) / .05, 0.0, 1.0); rigid = rigid * rigid * (3 - 2 * rigid)
                hj = gnames.index('head'); W *= (1 - rigid)[:, None]; W[:, hj] += rigid
                stats.setdefault('face_rigid_vertices', []).append(int((rigid > .999).sum()))
        for j, b in enumerate(gnames):
            A, t = M[b]; newco += W[:, j:j + 1] * (co @ A.T + t)
        # long things held in a hand: upright beside the body, bound to the root
        pole_ids = set(); comp = components(me); poles = 0; hands = [gnames.index(b) for b in ('hand_l', 'hand_r') if b in gnames]
        if hands:
            only_hand = W[:, hands].sum(1) > .999; axes = []
            for c in np.unique(comp[only_hand]):
                idx = np.where(comp == c)[0]
                if only_hand[idx].all() and np.ptp(co[idx, 2]) > .9: axes.append((co[idx, :2].mean(0), idx))
            for axis, idx0 in axes:
                side = 1.0 if axis[0] > 0 else -1.0; sel = np.zeros(n, bool); sel[idx0] = True
                for c in np.unique(comp[only_hand]):
                    idx = np.where(comp == c)[0]; ctr = co[idx].mean(0)
                    if only_hand[idx].all() and np.linalg.norm(ctr[:2] - axis) < .16 and ctr[2] > src['head'][2] + .12: sel[idx] = True
                target = np.array(cfg.get('pole_xy', (.33, -.07))) * (side, 1)
                newco[sel] = (co[sel] - (axis[0], axis[1], 0)) * g + (target[0], target[1], 0)
                if 'root' not in o.vertex_groups: o.vertex_groups.new(name='root')
                ids = [int(k) for k in np.where(sel)[0]]
                for vg in o.vertex_groups: vg.remove(ids)
                o.vertex_groups['root'].add(ids, 1.0, 'REPLACE'); poles += len(ids); pole_ids.update(ids)
        for j, vg in enumerate(o.vertex_groups[:len(gnames)]):      # write the trimmed weights back
            col = W[:, j]; zero = [int(k) for k in np.where(col <= 0)[0] if k not in pole_ids]
            if zero: vg.remove(zero)
            for k in np.where(col > 0)[0]:
                if k not in pole_ids: vg.add([int(k)], float(col[k]), 'REPLACE')
        me.vertices.foreach_set('co', newco.ravel()); me.update()
        o.matrix_world.identity(); o.parent = None
        for m in list(o.modifiers): o.modifiers.remove(m)
        mod = o.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
        o.name = f'{new_name}_LOD{i}'; me.name = o.name; o.hide_render = i != 0; o.hide_viewport = False
        stats['lods'].append({'vertices': n, 'pole_vertices': poles, 'min_z': round(float(newco[:, 2].min()), 4), 'max_z': round(float(newco[:, 2].max()), 4)})
    if cfg.get('body'): stats.update(add_body(lods, dst, cfg['body']))
    lift = -min(l['min_z'] for l in stats['lods'][:1])     # soles on the ground
    for o in lods:
        for v in o.data.vertices: v.co.z += lift
    stats['lift_m'] = round(lift, 4)
    bpy.data.objects.remove(sarm, do_unlink=True)
    # material names: MI_<Name>_PR_<Slot>; the slot word decides the Unreal material (Skin, Eyes, Hair, Outfit)
    slots = {}
    for s in lods[0].material_slots:
        old = s.material.name; slot = old.split('_PR_')[-1] if '_PR_' in old else 'Outfit'
        s.material.name = f'MI_{name}_PR_{slot}'; slots[s.material.name] = slot
    blend = WORK / f'{new_name}.blend'; bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=False)
    print('[PR] ported', name, json.dumps(stats), flush=True)
    return blend, slots, stats


def flat(path, rgb, size=16):
    from PIL import Image
    Image.new('RGB', (size, size), tuple(int(round(c * 255)) for c in rgb)).save(path)


def finish(name, blend, slots, stats):
    """export (in its own Blender: the exporter rescales the scene), then the manifest"""
    cfg = NPCS[name]; out = OUT / name; rep = out / 'export_report.json'
    r = subprocess.run([bpy.app.binary_path, '-b', '-t', '4', str(blend), '--python', str(HERE / 'export_char.py'), '--', str(out / 'Export'), str(rep), 'character_humanoid'],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith(('EXPORT DONE', 'VALIDATION error')): print(line[:300], flush=True)
    if 'EXPORT DONE' not in r.stdout: raise RuntimeError('export failed: ' + r.stdout[-2000:] + r.stderr[-2000:])
    report = json.loads(rep.read_text()); src_dir = UNC / cfg['src']; asset = cfg['asset']; up = os.path.relpath(src_dir, out)
    tex_of = cfg.get('tex', asset[3:])     # texture stem: T_<tex>_<Slot>_BC.png
    mats = {}
    home = (src_dir, tex_of, up)
    for mat, slot in slots.items():
        t = {}; src_dir, tex_of, up = home
        if slot in cfg.get('tex_slots', {}):      # this slot's maps live in another Unclaimed folder under another stem
            src_dir = UNC / cfg['tex_slots'][slot][0]; tex_of = cfg['tex_slots'][slot][1]; up = os.path.relpath(src_dir, out)
        for role in ('BC', 'N', 'ORM'):
            stem = f'T_{tex_of}_{slot}_{role}.png' if len(slots) > 1 else f'T_{tex_of}_{role}.png'
            if role == 'BC' and cfg.get('bc', {}).get(slot): stem = cfg['bc'][slot]
            if role == 'BC' and slot == 'Eyes' and (src_dir / stem).exists():
                # The source's eye map carries a pale lavender cornea disc and, on some, a bright red-brown iris: lit by the
                # game they read as bloodshot eyes with a blue spot (the merchant, 14 Nov 2026). The disc goes dark, a
                # saturated red iris goes to brown.
                from PIL import Image
                e = np.asarray(Image.open(src_dir / stem).convert('RGB'), np.float32) / 255.0
                lav = (np.clip((e[..., 2] - np.maximum(e[..., 0], e[..., 1]) - .02) * 12, 0, 1) * (e.min(axis=2) > .5))[..., None]   # pale lavender only: a blue iris is darker
                red = np.clip((e[..., 0] - e[..., 1] - .15) * 6, 0, 1)[..., None]
                e = e * (1 - lav) + lav * .03; e = e * (1 - red) + red * e * np.array([.42, .62, .55], np.float32)
                fixed = out / 'Textures' / f'T_{name}_PR_Eyes_BC.png'; Image.fromarray((np.clip(e, 0, 1) * 255 + .5).astype(np.uint8)).save(fixed)
                t[role] = f'Textures/{fixed.name}'; continue
            if (src_dir / stem).exists(): t[role] = f'{up}/{stem}'
            else:
                if role == 'BC': raise RuntimeError(f'{name}: no base colour map {src_dir / stem} for slot {slot}')   # a flat filler colour is no substitute (the throne came out orange)
                fill = out / 'Textures' / f'T_{name}_PR_{slot}_{role}.png'
                flat(fill, (.5, .5, 1.0) if role == 'N' else {'Eyes': (1.0, .12, 0.0), 'Hair': (1.0, .55, 0.0)}.get(slot, (1.0, .6, 0.0)))
                t[role] = f'Textures/{fill.name}'
        shading = 'default lit'
        if slot == 'Skin':
            sss = out / 'Textures' / f'T_{name}_PR_Skin_SSS.png'; flat(sss, (.73, .46, .39)); t['SSS'] = f'Textures/{sss.name}'
            shading = 'subsurface profile / skin; SSS is a flat scatter colour (the source has no thickness map)'
        elif slot == 'Hair': shading = 'MASKED (alpha in BC.a), two-sided hair cards, default lit'
        elif slot == 'Eyes': shading = 'default lit, low roughness'
        mats[mat] = {'textures': t, 'shading': shading, 'normal': 'OpenGL (+Y), flip green for UE'}
    man = {'schema': 'dink-photoreal-character/1', 'asset': report['asset'], 'class': 'character_humanoid',
           'source_blend': os.path.relpath(UNC / cfg['src'] / (asset + '.blend'), PASS).replace(os.sep, '/'),
           'build': f'blender -b -t 4 --python Characters/Tools/npc_port.py -- {name}',
           'fbx': [f'Export/{report["asset"]}_LOD{i}.fbx' for i in range(4)], 'dimensions_m': report['dimensions_m'], 'bone_count': report['bone_count'],
           'root_bone': 'root', 'skeleton': '/Game/Characters/Mannequins/Meshes/SK_Mannequin (89 bones; armature of Characters/Milder)',
           'lods': report['lods'], 'lod0_triangles': report['lods'][0]['triangles'], 'material_slots': report['materials'], 'materials': mats,
           'port': stats, 'placement_scale': round(1.0 / stats['height_ratio'], 3), 'animation_set': cfg['set'], 'families': cfg['families'],
           'validation': report['validation'], 'validator_findings': report['findings'],
           'known_weaknesses': cfg.get('weak', []) + ([] if cfg.get('static') else ['Ported from the 26-bone Unclaimed source by its own skin weights: fingers, twist bones and the other mannequin bones carry no weight (mitten hands, no forearm twist).',
                                                      'Face, hair and cloth are those of the Unclaimed source (see its manifest): a plain base face and card hair; they have not been through the head, skin and groom tools of the three main characters.'])}
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n'); print('[PR] manifest', name, report['dimensions_m'], flush=True)


for nm in names:
    b, s, st = port(nm); finish(nm, b, s, st)
print('NPC_PORT_DONE', names)
