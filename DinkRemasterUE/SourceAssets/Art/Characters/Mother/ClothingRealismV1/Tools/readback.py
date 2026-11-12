"""Independent fresh-process Blender readback: baseline vs packed editable and baked successors.
Checks actual stored data, not producer reports. Fails before writing a PASS on divergence.
"""
import bpy,hashlib,json,struct
from pathlib import Path
H=Path(__file__).resolve().parents[1];A=H.parents[1]
def sha(x):return hashlib.sha256(x).hexdigest()
def collect(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));r={};arm=bpy.data.objects['Armature']
 r['bones']=[(b.name,b.parent.name if b.parent else None,tuple(tuple(row)for row in b.matrix_local))for b in arm.data.bones];r['meshes']={}
 for j in range(4):
  ob=bpy.data.objects['SK_Mother_LOD%d'%j];m=ob.data;cloth=set()
  for f in m.polygons:
   if f.material_index==4:cloth.update(f.vertices)
  r['meshes'][j]={'coords':[tuple(v.co)for v in m.vertices],'cloth':cloth,'faces':[(tuple(f.vertices),f.material_index)for f in m.polygons],'uvs':[[tuple(v.uv)for v in layer.data]for layer in m.uv_layers],'weights':[[(g.group,g.weight)for g in v.groups]for v in m.vertices],'groups':[g.name for g in ob.vertex_groups],'modifiers':[(x.type,x.object.name if x.type=='ARMATURE'and x.object else None)for x in ob.modifiers],'material_names':[s.material.name for s in ob.material_slots],'objectTRS':tuple(tuple(row)for row in ob.matrix_world)}
 r['original_images']={}
 for name in ['T_Mother_Atlas_BC','T_Mother_Atlas_N','T_Mother_Atlas_ORM']:
  im=bpy.data.images.get(name);assert im and im.size[0]==4096
  import array
  x=array.array('f',[0])*len(im.pixels);im.pixels.foreach_get(x);r['original_images'][name]=sha(x.tobytes())
 return r
baseline=collect(A/'SK_Mother.blend');report={'status':'PASS','rig_bones':len(baseline['bones']),'files':{}}
assert len(baseline['bones'])==89
for name in ['SK_Mother_ClothingRealismV1.blend','SK_Mother_ClothingRealismV1_Baked.blend']:
 target=collect(H/name);assert baseline['bones']==target['bones'];assert baseline['original_images']==target['original_images'];lods=[]
 for j,a in baseline['meshes'].items():
  b=target['meshes'][j]
  for k in ['faces','uvs','weights','groups','modifiers','objectTRS']:assert a[k]==b[k],(name,j,k)
  assert a['material_names'][:4]==b['material_names'][:4];assert len(b['material_names'])==5
  changed=[i for i,(x,y)in enumerate(zip(a['coords'],b['coords']))if x!=y];assert changed and all(i in a['cloth']for i in changed)
  maxd=max(sum((a['coords'][i][k]-b['coords'][i][k])**2 for k in range(3))**.5 for i in changed);assert maxd<.045
  assert all(len([g for g,w in weights if w>1e-6])<=4 and abs(sum(w for g,w in weights)-1)<1e-4 for weights in b['weights'])
  import numpy as np
  ca=np.asarray(a['coords']);cb=np.asarray(b['coords']);tris=[]
  for indices,material in a['faces']:
   if material==4:
    for n in range(1,len(indices)-1):tris.append([indices[0],indices[n],indices[n+1]])
  t=np.asarray(tris);na=np.cross(ca[t[:,1]]-ca[t[:,0]],ca[t[:,2]]-ca[t[:,0]]);nb=np.cross(cb[t[:,1]]-cb[t[:,0]],cb[t[:,2]]-cb[t[:,0]]);aa=np.linalg.norm(na,axis=1);ab=np.linalg.norm(nb,axis=1);newcollapsed=int(np.count_nonzero((aa>1e-12)&(ab<=1e-12)));flipped=int(np.count_nonzero((aa>1e-12)&(ab>1e-12)&(np.sum(na*nb,axis=1)<0)));assert newcollapsed==0,(name,j,'new collapsed cloth triangles');assert flipped==0,(name,j,'cloth triangle orientation reversed')
  lods.append({'new_collapsed_cloth_triangles':newcollapsed,'reversed_cloth_triangle_normals':flipped,'lod':j,'vertices':len(b['coords']),'triangles':sum(len(f[0])-2 for f in b['faces']),'changed_cloth_vertices':len(changed),'max_displacement_m':maxd,'topology_uv_weights_noncloth_geometry_exact':True})
 report['files'][name]={'sha256':sha((H/name).read_bytes()),'lods':lods,'original_atlas_pixels_exact':True,'rest89_exact':True}
(H/'independent_blend_readback.json').write_text(json.dumps(report,indent=2)+'\n');print('INDEPENDENT BLEND READBACK PASS',flush=True)
