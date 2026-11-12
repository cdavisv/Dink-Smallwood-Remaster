"""Read-only source front/back/idle/fist/walk-like deformation review. Noexports."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ART=Path(Path(__file__).resolve().parents[1]);CHARS=ART.parents[1]
# Read the existingEpic walk reference into temporary memory only, never into
# the saved candidate or any authored/exported animation asset.
walk_samples=[];walk_rest={};walk_path=Path(Path.home()/'Work/DinkQA/CharacterReference/Manny_Walk_Reference.fbx')
if not walk_path.exists():walk_path=Path('/tmp/dink-character-reference/Manny_Walk_Reference.fbx')
if walk_path.exists():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(walk_path),automatic_bone_orientation=False,use_anim=True)
 reference=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');action=reference.animation_data.action
 start,end=action.frame_range
 def normalized_world(matrix,root):
  out=matrix.to_quaternion().to_matrix().to_4x4();out.translation=matrix.translation-root;return out
 bpy.context.scene.frame_set(round(start));bpy.context.view_layer.update();reference_origin=reference.matrix_world.translation.copy()
 for bone in reference.data.bones:
  walk_rest[bone.name]=normalized_world(reference.matrix_world@bone.matrix_local,reference_origin)
 walk_rest['root']=Matrix.Identity(4)
 for fraction in [.20,.70]:
  frame=round(start+(end-start)*fraction);bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();root=reference.matrix_world.translation.copy();matrices={'root':normalized_world(reference.matrix_world,root)}
  for bone in reference.pose.bones:
   matrices[bone.name]=normalized_world(reference.matrix_world@bone.matrix,root)
  walk_samples.append((frame,matrices))
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));scene=bpy.context.scene;arm=bpy.data.objects['Armature'];arm.animation_data_create();arm.animation_data.action=None;arm.data.pose_position='POSE'

import numpy as np,hashlib
from mathutils.geometry import closest_point_on_tri,barycentric_transform
report=json.loads((ART/'integrated_skin_yoke_report.json').read_text());tile_index={tuple(v):i for i,v in enumerate(report['new_unique_atlas_tiles'])};objects=[];models=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];assert all(m.type=='ARMATURE' for m in ob.modifiers),[(m.name,m.type) for m in ob.modifiers];mesh=ob.data;mesh.calc_loop_triangles();source_ids=report['lods'][lod]['selected_skin_source_faces'];incident={}
 for p in mesh.polygons:
  if p.material_index!=4:continue
  uv=[mesh.uv_layers[0].data[i].uv for i in p.loop_indices];center=sum(uv,Vector((0,0)))/len(uv);key=(int(center.y*4096)//16,int((center.x-1)*4096)//16);index=tile_index.get(key,-1)
  if 0<=index<len(source_ids):
   for v in p.vertices:incident.setdefault(v,set()).add(source_ids[index])
 protected=len(json.loads(ob['protected_original_vertex_indices']));assert all(v>=protected for v in incident)
 sourcevertices={v for faces in incident.values() for f in faces for v in mesh.polygons[f].vertices};exact={tuple(round(x,5) for x in mesh.vertices[v].co+mesh.vertices[v].normal*.008):v for v in sourcevertices};tri_by_poly={}
 for t in mesh.loop_triangles:
  if mesh.polygons[t.polygon_index].material_index==0:tri_by_poly.setdefault(t.polygon_index,[]).append(tuple(t.vertices))
 ids=sorted(incident);mapping=[]
 for i in ids:
  co=mesh.vertices[i].co.copy();match=exact.get(tuple(round(x,5) for x in co));candidates=[]
  for face in incident[i]:
   for tri in tri_by_poly[face]:
    a,b,c=[mesh.vertices[j].co for j in tri];point=closest_point_on_tri(co,a,b,c);candidates.append(((point-co).length,face,tri,point))
  d,face,tri,point=min(candidates,key=lambda row:row[0])
  if match is not None:tri=(match,match,match);alpha=(1.,0.,0.)
  else:
   a,b,c=[mesh.vertices[j].co for j in tri];alpha=tuple(barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))));values={}
   for j,factor in zip(tri,alpha):
    for group in mesh.vertices[j].groups:values[group.group]=values.get(group.group,0)+group.weight*max(0,factor)
   values=sorted(values.items(),key=lambda row:-row[1])[:4];total=sum(w for _,w in values)
   if total>1e-8:
    for group in ob.vertex_groups:group.remove([i])
    for group,w in values:ob.vertex_groups[group].add([i],w/total,'REPLACE')
  mapping.append((tri,alpha,face))
 objects.append(ob);models.append({'ids':ids,'rest':np.array([tuple(mesh.vertices[i].co) for i in ids],np.float64),'mapping':mapping,'A':[],'B':[],'targets':[]})
idle=json.loads((CHARS/'Animations/Unarmed/idle_boundary_pose.json').read_text())['bones']
def clear_pose():
 arm.animation_data.action=None
 for b in arm.pose.bones:b.rotation_mode='QUATERNION';b.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
def set_idle():
 clear_pose();arm.data.pose_position='POSE'
 for b in arm.pose.bones:
  if b.name in idle:b.matrix=Matrix(idle[b.name]);bpy.context.view_layer.update()
with bpy.data.libraries.load(str(CHARS/'Animations/Unarmed/Dink_Fist.blend'),link=False) as (src,dst):dst.actions=['Dink_Fist_Forward']
fist_action=next(a for a in dst.actions if a)
def capture():
 outputs=[];deps=bpy.context.evaluated_depsgraph_get()
 for ob in objects:
  ev=ob.evaluated_get(deps);mesh=ev.to_mesh();mesh.calc_loop_triangles();tri_by_poly={}
  for tri in mesh.loop_triangles:
   if mesh.polygons[tri.polygon_index].material_index==0:tri_by_poly.setdefault(tri.polygon_index,[]).append(tuple(tri.vertices))
  outputs.append(([ob.matrix_world@v.co for v in mesh.vertices],[v.normal.copy() for v in mesh.vertices],tri_by_poly));ev.to_mesh_clear()
 return outputs
poses=['REST','ActualEpicIdle','OriginalFist8']+['ActualEpicWalk'+str(i) for i in range(len(walk_samples))]
for pose in poses:
 clear_pose();arm.data.pose_position='POSE'
 if pose=='REST':arm.data.pose_position='REST'
 elif pose=='ActualEpicIdle':set_idle()
 elif pose=='OriginalFist8':arm.animation_data.action=fist_action;scene.frame_set(8)
 else:
  frame,matrices=walk_samples[int(pose[-1])]
  for bone in arm.pose.bones:
   if bone.name in matrices:bone.matrix=matrices[bone.name];bpy.context.view_layer.update()
 bpy.context.view_layer.update();base=capture();targets=[]
 for model,(positions,normals,tris_by_face) in zip(models,base):
  values=[]
  for tri,alpha,face in model['mapping']:
   point=sum((positions[j]*factor for j,factor in zip(tri,alpha)),Vector());normal=sum((normals[j]*factor for j,factor in zip(tri,alpha)),Vector()).normalized();near=[]
   for face_tri in tris_by_face[face]:
    a,b,c=[positions[j] for j in face_tri];p=closest_point_on_tri(point,a,b,c);near.append(((p-point).length,p,(b-a).cross(c-a).normalized()))
   distance,point,geometry_normal=min(near,key=lambda row:row[0])
   if normal.dot(geometry_normal)<.8:normal=(normal+geometry_normal).normalized()
   values.append(tuple(point+normal*.010))
  targets.append(np.array(values,np.float64))
 derivatives=[np.empty((len(model['ids']),3,3),np.float64) for model in models];step=.01
 for axis in range(3):
  for ob,model in zip(objects,models):
   for vertex,co in zip(model['ids'],model['rest']):ob.data.vertices[vertex].co=Vector(co)+Vector(tuple(step if k==axis else 0 for k in range(3)))
   ob.data.update()
  bpy.context.view_layer.update();perturbed=capture()
  for model,base_data,changed,A in zip(models,base,perturbed,derivatives):
   A[:,:,axis]=(np.array([tuple(changed[0][i]) for i in model['ids']])-np.array([tuple(base_data[0][i]) for i in model['ids']]))/step
 for ob,model in zip(objects,models):
  for vertex,co in zip(model['ids'],model['rest']):ob.data.vertices[vertex].co=co
  ob.data.update()
 for model,base_data,A,target in zip(models,base,derivatives,targets):
  output=np.array([tuple(base_data[0][i]) for i in model['ids']],np.float64);model['A'].append(A);model['B'].append(output-np.einsum('nij,nj->ni',A,model['rest']));model['targets'].append(target)
 print('CAPTURED POSE ENVELOPE',pose,flush=True)
rows=[]
for lod,(ob,model) in enumerate(zip(objects,models)):
 A=np.array(model['A']);B=np.array(model['B']);target=np.array(model['targets']);regularization=.12;lhs=np.einsum('pnji,pnjk->nik',A,A)+np.eye(3)[None,:,:]*regularization;rhs=np.einsum('pnji,pnj->ni',A,target-B)+model['rest']*regularization;fitted=np.linalg.solve(lhs,rhs[:,:,None])[:,:,0];delta=fitted-model['rest'];length=np.linalg.norm(delta,axis=1);scale=np.minimum(1,.012/np.maximum(length,1e-8));fitted=model['rest']+delta*scale[:,None]
 for i,co in zip(model['ids'],fitted):ob.data.vertices[i].co=co
 ob.data.update();predicted=np.einsum('pnij,nj->pni',A,fitted)+B;error=np.linalg.norm(predicted-target,axis=2);rows.append({'lod':lod,'fitted_cloth_vertices':len(model['ids']),'target_offset_m':.010,'initial_offset_m':.008,'maximum_rest_adjustment_m':float(np.max(np.linalg.norm(fitted-model['rest'],axis=1))),'maximum_pose_target_error_m':float(error.max()),'rms_pose_target_error_m':float(np.sqrt(np.mean(error**2)))})
clear_pose();arm.data.pose_position='REST';scene.frame_set(1);bpy.data.actions.remove(fist_action)
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'pose_envelope_fit_report.json').write_text(json.dumps({'scope':'Only fitted cloth yoke rest positions and clipped-edge Skin barycentric weights adjusted; exact Armature deformation Jacobians measured forREST/idle/fist/bothactualwalks, least-squares enclosure against actual posed protectedSkin. Protected geometry/UV/weights/restbones/materialgraphs unchanged. No reference geometry or animation saved.','poses':poses,'lods':rows},indent=2)+'\n');print('POSE ENVELOPE FIT COMPLETE',rows,flush=True)
