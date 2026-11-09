import bpy,bmesh,json,time,sys,hashlib,os
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;source=O/'PhotorealPieV1_Source.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(source)
try:
 authorization=json.loads((O/'review_authorization.json').read_text());assert authorization['source_sha256']==pin and authorization['source_appearance_approved'] is True,'Appearance review required before bake'
 assert pin=='9eddc6e18db9dd6813ebbbdc2adcda1911c3dec8f84a680d0e6e3afcf72a986a','Unexpected source checkpoint'
 assert not (O/'PhotorealPieV1_Export.blend').exists(),'Refuse existing export'
 bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
 collection=bpy.data.collections['SM_Pie_Rustic_01'];s=next(s for s in bpy.data.scenes if collection.name in s.collection.children);bpy.context.window.scene=s
 name='SM_Pie_Rustic_01';ob=bpy.data.objects[name+'_LOD0'];lods=[bpy.data.objects[name+'_LOD'+str(i)]for i in range(3)];assert [sum(len(p.vertices)-2 for p in x.data.polygons)for x in lods]==[4844,2422,1210]
 for other in list(bpy.data.objects):
  if other not in list(collection.objects):bpy.data.objects.remove(other,do_unlink=True)
 for scene in list(bpy.data.scenes):
  if scene!=s:bpy.data.scenes.remove(scene)
 for col in list(bpy.data.collections):
  if col!=collection and not len(col.objects):bpy.data.collections.remove(col)
 collection['dink_path']='Stonebrook/PhotorealPieV1';collection['dink_nanite']='no';collection['dink_tex_px']=2048
 for lod in lods:
  bm=bmesh.new();bm.from_mesh(lod.data);bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='FIXED',ngon_method='EAR_CLIP');bm.to_mesh(lod.data);bm.free();lod.data.update()
 ob.hide_render=False;ob.hide_set(False);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 for other in s.objects:
  if other!=ob:other.hide_render=True
 s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=2;s.render.bake.margin=2;s.render.bake.use_selected_to_active=False;s.render.bake.use_clear=True
 (O/'Textures').mkdir(exist_ok=True);mats=list(ob.data.materials);images={};rows=[]
 for role,kind,socket in [('BC','EMIT','Base Color'),('Rough','EMIT','Roughness'),('Metal','EMIT','Metallic'),('N','NORMAL',None)]:
  im=bpy.data.images.new('T_Pie_Rustic_01_Photo_'+role,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB' if role=='BC' else 'Non-Color';restore=[]
  for mat in mats:
   n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL' and x.is_active_output)
   target=n.new('ShaderNodeTexImage');target.image=im;target.label='Bake target '+role;n.active=target
   if socket:
    previous=[(link.from_socket,link.to_socket) for link in out.inputs['Surface'].links];emit=n.new('ShaderNodeEmission');inp=bs.inputs[socket]
    if inp.is_linked:l.new(inp.links[0].from_socket,emit.inputs['Color'])
    else:
     value=inp.default_value;emit.inputs['Color'].default_value=tuple(value) if hasattr(value,'__len__') else (value,value,value,1)
    l.new(emit.outputs[0],out.inputs['Surface']);restore.append((mat,emit,previous))
  start=time.time();bpy.ops.object.bake(type=kind)
  for mat,emit,previous in restore:
   for from_socket,to_socket in previous:mat.node_tree.links.new(from_socket,to_socket)
   mat.node_tree.nodes.remove(emit)
  im.filepath_raw=str(O/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();im.pack();im.filepath='//Textures/'+im.name+'.png';images[role]=im
  rows.append({'role':role,'bake':kind,'source_socket':socket,'seconds':time.time()-start,'sha256':sha(O/'Textures'/(im.name+'.png'))});(O/'bake_receipt.json').write_text(json.dumps({'complete':False,'rows':rows},indent=2)+'\n');print('BAKED',role,flush=True)
 a=np.empty(2048*2048*4,dtype=np.float32);images['Rough'].pixels.foreach_get(a);a=a.reshape(-1,4);a[:,1]=a[:,0];a[:,0]=1;a[:,3]=1
 metal=np.empty(2048*2048*4,dtype=np.float32);images['Metal'].pixels.foreach_get(metal);a[:,2]=metal.reshape(-1,4)[:,0]
 orm=bpy.data.images.new('T_Pie_Rustic_01_Photo_ORM',width=2048,height=2048,alpha=False);orm.colorspace_settings.name='Non-Color';orm.pixels.foreach_set(a.ravel());orm.filepath_raw=str(O/'Textures'/(orm.name+'.png'));orm.file_format='PNG';orm.save();orm.pack();orm.filepath='//Textures/'+orm.name+'.png'
 baked_materials=[];slot_indices=[p.material_index for p in ob.data.polygons]
 for original in mats:
  old_bs=next(n for n in original.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  m=bpy.data.materials.new(original.name.replace('PhotoSource','PhotoBaked'));n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
  bs.inputs['Specular IOR Level'].default_value=old_bs.inputs['Specular IOR Level'].default_value;bs.inputs['IOR'].default_value=old_bs.inputs['IOR'].default_value
  for key in ['Subsurface Weight','Subsurface Scale','Subsurface Radius','Coat Weight','Coat Roughness']:bs.inputs[key].default_value=old_bs.inputs[key].default_value
  for role,im in [('BC',images['BC']),('N',images['N']),('ORM',orm)]:
   t=n.new('ShaderNodeTexImage');t.image=im;t.name='T_Pie_'+role
   if role=='BC':l.new(t.outputs['Color'],bs.inputs['Base Color'])
   elif role=='N':
    nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
   else:
    sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs[1],bs.inputs['Roughness']);l.new(sp.outputs[2],bs.inputs['Metallic'])
  baked_materials.append(m);original.use_fake_user=False
 for lod in lods:
  slot_indices=[p.material_index for p in lod.data.polygons];lod.data.materials.clear()
  for mat in baked_materials:lod.data.materials.append(mat)
  for poly,index in zip(lod.data.polygons,slot_indices):poly.material_index=index

 # Keep raw1254reference and donor graphs in separate immutable source only.
 keep_images={images['BC'],images['N'],orm}
 for oldmat in list(bpy.data.materials):
  if oldmat not in baked_materials:bpy.data.materials.remove(oldmat,do_unlink=True)
 for im in list(bpy.data.images):
  if im not in keep_images:bpy.data.images.remove(im,do_unlink=True)
 for im in keep_images:
  assert list(im.size)==[2048,2048];im.pack()
 assert len(bpy.data.images)==3
 sys.path.insert(0,str(O));from closed_crumb_normalization import normalize_closed_crumbs
 normalization=normalize_closed_crumbs();(O/'closed_crumb_normalization_receipt.json').write_text(json.dumps({'source_sha256':pin,'records':normalization,'LOD0_unchanged':True,'only_lower_collapsed_components_restored_from_LOD0':True},indent=2)+'\n')
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPieV1_Export.blend'))
 assert sha(source)==pin
 (O/'bake_receipt.json').write_text(json.dumps({'complete':True,'rows':rows,'source_sha256':pin,'source_unchanged':True,'triangles':len(ob.data.polygons),'metallic_linear_range':[float(a[:,2].min()),float(a[:,2].max())],'metallic_nonzero_texels':int((a[:,2]>.1).sum()),'R_AO':'neutral1','BC':'2048 emission bake of image-directed pastry/color and authored blueceramic/darkfruit; raw1254donor preserved separately, not resampled; independentN/ORM authored','normal':'tangent-space authored bump bake','ORM_sha256':sha(O/'Textures'/(orm.name+'.png'))},indent=2)+'\n');print('BAKE_COMPLETE',flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
except BaseException:
 import traceback
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
