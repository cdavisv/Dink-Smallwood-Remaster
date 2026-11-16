"""Unreal export of a rigged monster with its clips, in the convention the creature importer accepts.

The kit's SK_<Name>_PR_LOD*.fbx (tools/creature.py, metres) import with a scaled reference pose, which the importer's
creature gate refuses ("non-unit reference bone scale"). This writes Export/SK_<Name>_PR_LOD0..2.fbx and
Export/A_<Name>_<Clip>.fbx through Creatures/Tools/crlib.export_skeletal (a temporary x100 cm scene, as the duck, the
slime and the pig are exported). Nothing is saved back to the .blend.

usage: tools/bl.sh export_monster_ue.py <bonca|slayer|dragon|giant|knight|goblin_hammer|goblin_horned|goblin_soldier>
"""
import bpy, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); UNC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(UNC), 'Creatures', 'Tools'))
WHO = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'slayer'
FAM, NAME = {'bonca': ('bonca_gray', 'Bonca'), 'slayer': ('slayer', 'Slayer'), 'dragon': ('dragon', 'Dragon'), 'giant': ('stone_giant', 'Stone_Giant'), 'knight': ('npc_knight_blue', 'Knight'),
             'goblin_hammer': ('goblin_hammer', 'Goblin_Hammer'), 'goblin_horned': ('goblin_horned', 'Goblin_Horned'), 'goblin_soldier': ('goblin_soldier', 'Goblin_Soldier')}[WHO]
DIR = os.path.join(UNC, FAM, NAME)
sys.argv = sys.argv[:sys.argv.index('--') + 1] if '--' in sys.argv else sys.argv      # crlib reads its own arguments
import crlib
bpy.ops.wm.open_mainfile(filepath=os.path.join(DIR, 'SK_%s_PR.blend' % NAME))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meta = json.load(open(os.path.join(DIR, 'clips.json')))
coll = bpy.data.collections['SK_%s_PR' % NAME]
for o in list(coll.objects):                                  # three LODs, as the importer reads them
    if o.type == 'MESH' and o.name.endswith('_LOD3'): coll.objects.unlink(o)
files, verdict = crlib.export_skeletal('SK_%s_PR' % NAME, arm, os.path.join(DIR, 'Export'), {clip: '%s_%s' % (NAME, clip) for clip in meta}, 'A_%s' % NAME, 30)
print('[UE] exported', files)
