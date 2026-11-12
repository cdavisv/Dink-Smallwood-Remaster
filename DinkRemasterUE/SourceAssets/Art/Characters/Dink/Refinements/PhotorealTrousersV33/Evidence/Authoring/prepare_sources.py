import bpy,json,hashlib,re,os,struct
from pathlib import Path
P=Path('<HOME>/Work/DinkQA/HeroVisualRefinement');D=Path(__file__).resolve().parents[1]
for sub in ['Source','Source/Helpers','Textures/Pants','Textures/Context','Evidence','Export','Previews','References','Provenance','Shaders']:(D/sub).mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def jhash(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def core():
 out={}
 for ob in bpy.data.objects:
  if ob.type=='MESH':
   m=ob.data;out[ob.name]={'vertices':[tuple(v.co)for v in m.vertices],'faces':[tuple(f.vertices)for f in m.polygons],'smooth':[f.use_smooth for f in m.polygons],'uv':{u.name:[tuple(x.uv)for x in u.data]for u in m.uv_layers},'normals':[tuple(n.vector)for n in m.corner_normals],'weights':[sorted((ob.vertex_groups[g.group].name,g.weight)for g in v.groups)for v in m.vertices],'materials':[a.name for a in m.materials],'world':[tuple(r)for r in ob.matrix_world]}
  elif ob.type=='ARMATURE':out[ob.name]={'bones':[(b.name,b.parent.name if b.parent else None,[tuple(r)for r in b.matrix_local],tuple(b.head_local),tuple(b.tail_local),b.use_deform,b.inherit_scale,b.use_inherit_rotation)for b in ob.data.bones],'world':[tuple(r)for r in ob.matrix_world]}
 return jhash(out)
def images_in_tree(tree,seen=None):
 seen=set()if seen is None else seen
 if tree in seen:return set()
 seen.add(tree);out=set()
 for n in tree.nodes:
  if n.type=='TEX_IMAGE'and n.image:out.add(n.image)
  if n.type=='GROUP'and n.node_tree:out|=images_in_tree(n.node_tree,seen)
 return out
inputs=[('fit',P/'HandFitV19/Dink_Trousers_SidePanel_LOCAL_L16_R12mm_HAND_FIT_TRIAL.blend','Source/SK_Dink_Trousers_FitV19_Context.blend'),('appearance',P/'ClothMetricStitchV32/Dink_Trousers_METRIC_STITCH_SOURCE.blend','Source/SK_Dink_Trousers_MetricArtV32_Context.blend'),('coarse_procedural',P/'ClothSeamSourceV30/Dink_Trousers_COARSE_NO_STITCH_SOURCE.blend','Source/Helpers/Trousers_CoarseProcedural.blend'),('weave_tile',P/'ClothMetricTileV26/MetricWeave_TILE_SOURCE.blend','Source/Helpers/MetricWeave_Tile_Source.blend')]
rows=[]
for role,source,relative in inputs:
 pin=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));removed_context=[]
 if role=='coarse_procedural':
  for ob in list(bpy.data.objects):
   if ob.type=='MESH'and ob.name!='NEW_Dink_Trousers_LOD0':removed_context.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
 before=core()
 for ob in list(bpy.data.objects):
  if ob.type not in ['MESH','ARMATURE']:bpy.data.objects.remove(ob,do_unlink=True)
 bpy.data.orphans_purge(do_recursive=True)
 meshes=[o for o in bpy.data.objects if o.type=='MESH'];arms=[o for o in bpy.data.objects if o.type=='ARMATURE']
 if role!='weave_tile':
  assert len(meshes)==len(bpy.data.meshes)==(1 if role=='coarse_procedural' else 8) and len(arms)==len(bpy.data.armatures)==1 and len(arms[0].data.bones)==89
  assert not any(any(t in x.name.lower()for t in ['manny','recovered_fullbody','reference_body'])for table in [bpy.data.objects,bpy.data.meshes]for x in table)
  arms[0].data.pose_position='REST'
  collection=bpy.data.collections.new('SK_Dink_Trousers_SourceCandidate');bpy.context.scene.collection.children.link(collection)
  for ob in bpy.data.objects:
   for c in list(ob.users_collection):c.objects.unlink(ob)
   collection.objects.link(ob)
  collection['dink_class']='character_hero';collection['dink_path']='Hero/Refinements/PhotorealTrousersV33';collection['dink_nanite']='no';collection['dink_tex_px']=2048;collection['dink_source']='V19 fit / V32 metric woven source candidate. Other7 are retained project context, not final new head/hair.'
  for c in list(bpy.data.collections):
   if c!=collection and not c.objects and not c.children:bpy.data.collections.remove(c)
 else:assert len(meshes)==1 and not arms
 materials={mat for o in meshes for mat in o.data.materials if mat};used=set()
 for mat in materials:
  if mat.node_tree:used|=images_in_tree(mat.node_tree)
 image_rows=[];target=D/relative
 for im in sorted(used,key=lambda im:im.name):
  assert im.packed_file,('UnpackedImage',role,im.name);data=bytes(im.packed_file.data);h=hashlib.sha256(data).hexdigest();assert data[:8]==b'\x89PNG\r\n\x1a\n';w,hg,bits,ctype=struct.unpack('>IIBB',data[16:26]);kind='Pants'if im.name.startswith(('T_Dink_Trousers','T_Dink_Homespun'))else'Context';basename=re.sub('[^A-Za-z0-9_.-]+','_',im.name).strip('_');basename=basename[:-4]if basename.lower().endswith('.png')else basename;dest=D/'Textures'/kind/(basename+'_'+h[:12]+'.png')
  if dest.exists():assert dest.read_bytes()==data
  else:dest.write_bytes(data)
  im.filepath='//'+os.path.relpath(dest,target.parent).replace(os.sep,'/');image_rows.append({'name':im.name,'path':str(dest.relative_to(D)),'sha256':h,'bytes':len(data),'width':w,'height':hg,'bits':bits,'PNG_color_type':ctype,'colorspace':im.colorspace_settings.name})
 bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
 assert core()==before,('CoreChangedDuringPortablePreparation',role)
 if role=='appearance':bpy.data.objects['NEW_Dink_Trousers_LOD0']['source_stage']='Accepted source V19 fit and V32 metric woven appearance checkpoint; source only. Known walk11 rise/proxy limitations; native/game acceptance pending.'
 bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=False);assert sha(source)==pin
 rows.append({'role':role,'helper_only_removed_unchanged_context':removed_context,'authoring_origin':str(source),'authoring_origin_sha256':pin,'path':relative,'sha256':sha(target),'bytes':target.stat().st_size,'core_geometry_rig_material_slots_UVs_exact':True,'core_signature':before,'mesh_objects':len(meshes),'mesh_datablocks':len(bpy.data.meshes),'armatures':len(arms),'materials_used':len(materials),'used_images':image_rows,'all_used_images_packed_relative_byte_identical':True});(D/'Evidence/source_preparation.json').write_text(json.dumps({'scope':'Source-only portable preparation; source authoring files unchanged. No native/export acceptance implied.','scenes':rows},indent=2)+'\n');print('PORTABLE_SOURCE',role,target.stat().st_size,len(used),flush=True)
