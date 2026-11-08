"""Four separateLOD exports for isolated hand-correction candidate; materials reused."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];CHARS=ROOT.parents[1];PROJECT=CHARS.parents[2]
sys.path.insert(0,str(PROJECT.parent/'Dink-Smallwood-Remaster/tools/blender'))
from dinkasset import common,validate,export_ue
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SK_Dink_Hands.blend'));scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.animation_data.action=None;arm.data.pose_position='REST';coll=bpy.data.collections['SK_Dink_Hands'];asset=common.Asset(coll);normals=[]
for ob in asset.renders:
 ob.data.update();zero={i for i,n in enumerate(ob.data.corner_normals) if n.vector.length<1e-4};flat=0
 for face in ob.data.polygons:
  if any(i in zero for i in face.loop_indices):face.use_smooth=False;flat+=1
 ob.data.update();remaining=sum(n.vector.length<1e-4 for n in ob.data.corner_normals)
 if remaining:raise RuntimeError('Zero normals '+ob.name)
 normals.append({'mesh':ob.name,'flat_faces_for_cancelled_normals':flat,'zero_normals_remaining':remaining})
# Save only candidate source, retainingmetres and previewtextures; originalhero untouched.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SK_Dink_Hands.blend'),relative_remap=False)
verdict=validate.validate_scene(only=['SK_Dink_Hands']);(ROOT/'hand_validation.json').write_text(json.dumps(verdict,indent=2)+'\n')
if verdict['summary']['errors']:
 for a in verdict['assets']:
  for f in a['findings']:
   if f['severity']=='error':print('HAND VALIDATION ERROR',f['code'],f['message'],flush=True)
 raise RuntimeError('Hand candidate sourceguide gate failed')
ob=bpy.data.objects['SK_Dink_Hands_LOD0'];lo,hi=common.world_bounds(ob);bounds=[common.world_bounds(o) for o in asset.renders];mn=Vector(tuple(min(b[0][i] for b in bounds) for i in range(3)));mx=Vector(tuple(max(b[1][i] for b in bounds) for i in range(3)));materials=[s.material.name for s in ob.material_slots]
report={'validation':verdict['summary'],'normals':normals,'lods':[{'mesh':o.name,'triangles':common.tri_count(o),'vertices':len(o.data.vertices)} for o in asset.renders],'rest_rig_bones':len(arm.data.bones),'materials_reused':materials}
(ROOT/'hand_lod_report.json').write_text(json.dumps(report,indent=2)+'\n')
row={'class':'character_hero','fbx':'Dink/HandBindingV2/Export/SK_Dink_Hands_LOD0.fbx','lod_fbx':['Dink/HandBindingV2/Export/SK_Dink_Hands_LOD%d.fbx'%i for i in range(4)],'dimensions_m':list(hi-lo),'lod_union_dimensions_m':list(mx-mn),'materials':materials,'source_blend':'Dink/HandBindingV2/SK_Dink_Hands.blend','root_bone':'root','bones':[b.name for b in arm.data.bones],'content_folder':'/Game/Dink/Hero/Refinements','bounds_min_m':list(lo),'bounds_max_m':list(hi),'source_credits':'Existing CC0MakeHuman-basedDink anatomy, originalprojectwardrobe; isolated originalper-digit handfit/weights; Epic89bone referenceunchanged.'}
manifest={'schema':'dink-character-art/1','assets':{'SK_Dink_Hands':row},'materials':{},'existing_materials':{n:'/Game/Dink/Materials/Characters/'+n+'.'+n for n in materials},'player':{'mesh':'SK_Dink_Hands'},'placements':[],'status':'candidate','source_scope':'Onlyskinhand/wristseam changed; alloutsidepositions/weights andUVs remain fingerprint-identical perLOD. ExistingSK_Dink/assets/materials/runtime unchanged.','animation_reference':'Animations/Unarmed/animation_manifest.json'}
(ROOT/'hand_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for mesh in asset.renders:
 for v in mesh.data.vertices:v.co*=100
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones:b.head*=100;b.tail*=100
bpy.ops.object.mode_set(mode='OBJECT');scene.unit_settings.scale_length=.01
for material in bpy.data.materials:
 if material.node_tree:material.node_tree.nodes.clear()
 material.use_nodes=False
for lod in range(4):
 m=bpy.data.objects['SK_Dink_Hands_LOD%d'%lod];proxy=type('ExportAsset',(),{'renders':[m],'collision':[],'armatures':[arm],'sockets':[]})()
 with export_ue.unhidden([m,arm]):export_ue.export_fbx(proxy,str(ROOT/'Export'/('SK_Dink_Hands_LOD%d.fbx'%lod)),'all','Armature')
print('HANDV2 EXPORT PASS',report,flush=True)
