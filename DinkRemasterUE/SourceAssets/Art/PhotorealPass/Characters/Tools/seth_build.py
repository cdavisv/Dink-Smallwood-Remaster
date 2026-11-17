"""Seth, the last enemy (script s7-boss, made in Milder's scene s7-mil on SCR_086): the last stage of his build.

His 1997 pictures are not the green gnome that dink.ini loads at 581-589: Milder's script replaces those sequences with
graphics/effects/magic/seth1w, seth3w, seth7w, seth9w and adds the standing picture `pose` as 580 (s7-mil.c main, init
"load_sequence_now ..."). They show the hero's own body model, a head taller than Dink, in a dark red jerkin over
slate-blue mail sleeves and trousers, dark gloves, with a head about twice the size a man's should be: a long hard
face under a tall crest of brown hair.

He is a character of his own in the character pipeline, standing in the hero's clothes (the hero's garment and gear
stages are not run again):
    python3 -I seth_outfit.py                                                          his outfit maps (dark red, slate mail)
    blender -b -t 4 --python dink_04_head.py -- <abs>/NPC/Seth/cfg/head.json           his own face (facelib ops)
    python3 -I eye_tex.py <abs>/NPC/Seth/Textures/T_Seth_PR_Eyes 62,48,34 7
    blender -b -t 4 --python dink_05b_skin.py -- <abs>/NPC/Seth/cfg/skin.json          older skin, stubble, gloved hands
    blender -b -t 4 --python hair_groom.py -- Seth atlas,save s1                       the crest (hair_styles.py 'Seth', kind 'crest')
    blender -b -t 4 --python dink_06_assemble.py -- <abs>/NPC/Seth/cfg/assemble.json
    blender -b -t 4 <Characters>/NPC/Seth/SK_Seth_Photoreal.blend --python seth_build.py [-- <head scale>]     THIS FILE
    blender -b -t 4 <Characters>/NPC/Seth/SK_Seth_Photoreal.blend --python export_char.py -- <abs>/NPC/Seth/Export <abs>/NPC/Seth/export_report.json character_hero
    python3 -I seth_manifest.py

This stage grows the head about the base of the neck (1997: the head is a quarter of his height; a man's is between a
seventh and an eighth) on every LOD, hair and all, and saves the file in place."""
import bpy, sys
import numpy as np
from pathlib import Path

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
HEAD = float(argv[0]) if argv else 1.8
# how much of the growth each bone's skin takes: the head all of it, the neck less towards the shoulders, so the collar stays
SHARE = {'head': 1.0, 'neck_02': 0.62, 'neck_01': 0.22}

arm = bpy.data.objects['Armature']
pivot = np.array(arm.matrix_world @ arm.data.bones['neck_01'].head_local, np.float64)
lods = sorted((o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name), key=lambda o: o.name)
assert len(lods) == 4, [o.name for o in lods]
if arm.get('seth_head_scale'):
    raise SystemExit('seth_build: the head of this file is already grown (x%s); assemble again first' % arm['seth_head_scale'])
for o in lods:
    me = o.data
    assert not me.shape_keys, o.name
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
    co = np.empty(n * 3, np.float64); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    co = local_pivot + (co - local_pivot) * factor
    me.vertices.foreach_set('co', co.reshape(-1))
    me.update()
    print('SETH', o.name, 'vertices', n, 'grown', int((w > 0.01).sum()), 'top z', round(float((world @ np.append(co.max(axis=0), 1.0))[2]), 3))
arm['seth_head_scale'] = HEAD
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_mainfile(compress=True, relative_remap=True)
print('SETH saved', Path(bpy.data.filepath).name, 'head x', HEAD)
