"""Seth, the last enemy (script s7-boss, made in Milder's scene s7-mil on SCR_086).

His 1997 pictures are not the green gnome that dink.ini loads at 581-589: Milder's script replaces those sequences with
graphics/effects/magic/seth1w, seth3w, seth7w, seth9w and adds the standing picture `pose` as 580 (s7-mil.c main, init
"load_sequence_now ..."). They show the hero's own body model, a head taller than Dink, in a dark red tunic over
slate-blue sleeves and trousers, with a head about twice the size a man's should be and brown hair swept up.
So Seth is built from the hero: the same body, skeleton and skin weights, the head grown about the base of the neck,
the outfit recoloured. The head's face is the hero kit's sculpted face, not the 1997 photograph.

    blender -b -t 4 <Characters>/Dink/SK_Dink_Photoreal.blend --python seth_build.py [-- <head scale> [<hair sweep 0..1>]]
    blender -b -t 4 <Characters>/NPC/Seth/SK_Seth_Photoreal.blend --python export_char.py -- <Characters>/NPC/Seth/Export <Characters>/NPC/Seth/export_report.json character_hero
    python3 -I seth_manifest.py

(after `python3 -I npc_variants.py`, which makes his outfit map NPC/Seth/Textures/T_Seth_PR_Outfit_BC.png)
Writes NPC/Seth/SK_Seth_Photoreal.blend (meshes SK_Seth_Photoreal_LOD0-3, materials MI_Seth_PR_*)."""
import bpy, sys
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHARS = HERE.parent
OUT = CHARS / 'NPC/Seth'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
HEAD = float(argv[0]) if argv else 1.8          # 1997: the head is a quarter of his height (a man's is between a seventh and an eighth)
# how much of the growth each bone's skin takes: the head all of it, the neck less towards the shoulders, so the collar stays
SHARE = {'head': 1.0, 'neck_02': 0.62, 'neck_01': 0.22}

SWEEP = float(argv[1]) if len(argv) > 1 else 1.0   # 0 keeps the hero's fringe


def sweep_hair(o, co):
    """The hero's fringe hangs over his brow; Seth's hair is swept up and back from a high forehead and stands over it.
    The hair cards and their cap (vertex attribute hl; not the brows and lashes) are turned upward about
    the middle of the skull, in the plane of the nose, the more the further forward they lie: the fringe is gathered
    above the forehead and the crown is pushed up and out. The sides and the back keep their fall."""
    me = o.data
    layer = me.attributes['hl']       # hair layer of the groom per vertex: 1 cap, 2 and 3 lock cards, 5 wisps; 4 = brows and lashes; 0 = not hair
    hl = np.empty(len(me.vertices), np.float32); layer.data.foreach_get('value', hl); hl = np.round(hl).astype(int)
    ids = np.flatnonzero((hl > 0) & (hl != 4))
    if not len(ids) or SWEEP <= 0:
        return
    world = np.array(o.matrix_world, np.float64); inverse = np.linalg.inv(world)
    p = (world @ np.c_[co[ids], np.ones(len(ids))].T).T[:, :3]
    centre = np.array([0.0, pivot[1] + (-0.044 - 0.0157) * HEAD, pivot[2] + 0.173 * HEAD])      # middle of the skull (the face looks along -Y)
    v = p - centre
    flat = np.hypot(v[:, 0], v[:, 1]) + 1e-9
    front = np.clip(-v[:, 1] / flat, 0.0, 1.0) ** 1.3                 # 1 over the nose, 0 at the ears and behind
    r = np.hypot(v[:, 1], v[:, 2]); theta = np.arctan2(v[:, 2], -v[:, 1])       # 0 = straight ahead, pi/2 = up
    lo, hair_line, top = np.radians(-25.0), np.radians(30.0), np.radians(80.0)
    t = np.clip((theta - lo) / (top - lo), 0.0, 1.0)
    target = hair_line + (top - hair_line) * t ** 0.8                 # everything between the fringe tips and the crown, gathered above the hair line
    moved = (theta > lo - 0.3) & (theta < top)
    new_theta = np.where(moved, theta + SWEEP * front * (target - theta), theta)
    crest = np.exp(-((new_theta - np.radians(52.0)) / np.radians(30.0)) ** 2)   # the hair stands highest above the forehead
    # the cards stand up; the opaque cap under them stays on the skull (lifted with them, its dark inside showed as a hollow
    # under the quiff from the front)
    cards = (hl[ids] != 1).astype(np.float64)
    new_r = r * (1.0 + SWEEP * 0.42 * front * crest * cards)
    v[:, 1] = -np.cos(new_theta) * new_r; v[:, 2] = np.sin(new_theta) * new_r
    co[ids] = (inverse @ np.c_[centre + v, np.ones(len(ids))].T).T[:, :3]
    o.data.vertices.foreach_set('co', co.reshape(-1))
    print('SETH hair', o.name, 'cards and cap vertices', len(ids), 'turned', int((moved & (front > 0.05)).sum()))


arm = bpy.data.objects['Armature']
pivot = np.array(arm.matrix_world @ arm.data.bones['neck_01'].head_local, np.float64)
lods = sorted((o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name), key=lambda o: o.name)
assert len(lods) == 4, [o.name for o in lods]
for o in lods:
    me = o.data
    n = len(me.vertices)
    index = {g.index: SHARE[g.name] for g in o.vertex_groups if g.name in SHARE}
    w = np.zeros(n, np.float64)
    for v in me.vertices:
        total = sum(g.weight for g in v.groups)
        if total > 0:
            w[v.index] = sum(g.weight * index.get(g.group, 0.0) for g in v.groups) / total
    w = np.clip(w, 0.0, 1.0) ** 0.85     # a little fuller at the jaw line than a linear blend
    factor = (1.0 + (HEAD - 1.0) * w)[:, None]
    world = np.array(o.matrix_world, np.float64); inverse = np.linalg.inv(world)
    local_pivot = (inverse @ np.append(pivot, 1.0))[:3]
    blocks = me.shape_keys.key_blocks if me.shape_keys else [None]
    for block in blocks:
        data = block.data if block is not None else me.vertices
        co = np.empty(n * 3, np.float64); data.foreach_get('co', co); co = co.reshape(-1, 3)
        co = local_pivot + (co - local_pivot) * factor
        data.foreach_set('co', co.reshape(-1))
    if me.shape_keys:      # the hero's two physique keys are not Seth's: he keeps the rest shape only
        co = np.empty(n * 3, np.float64); me.shape_keys.key_blocks[0].data.foreach_get('co', co); co = co.reshape(-1, 3)
        o.shape_key_clear(); me.vertices.foreach_set('co', co.reshape(-1))
    sweep_hair(o, co)
    me.update()
    o.name = o.name.replace('SK_Dink_Photoreal', 'SK_Seth_Photoreal'); me.name = o.name
    print('SETH', o.name, 'vertices', n, 'grown', int((w > 0.01).sum()), 'top z', round(float((world @ np.append(co.max(axis=0), 1.0))[2]), 3))
for m in bpy.data.materials:
    if m.name.startswith('MI_Dink_PR_'):
        m.name = m.name.replace('MI_Dink_PR_', 'MI_Seth_PR_')
for c in bpy.data.collections:
    if c.name.startswith('SK_Dink'):
        c.name = c.name.replace('SK_Dink', 'SK_Seth')

dst = OUT / 'Textures/T_Seth_PR_Outfit_BC.png'      # made by npc_variants.py (leather vest -> dark red tunic, olive trousers -> slate blue)
for image in bpy.data.images:      # the review render shows the new colours
    if dst.exists() and Path(bpy.path.abspath(image.filepath)).name == 'T_Dink_PR_Outfit_BC.png':
        image.filepath = str(dst); image.reload()
bpy.ops.file.make_paths_relative() if bpy.data.filepath else None
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'SK_Seth_Photoreal.blend'), relative_remap=True, compress=True)
print('SETH saved', OUT / 'SK_Seth_Photoreal.blend', 'head x', HEAD)
