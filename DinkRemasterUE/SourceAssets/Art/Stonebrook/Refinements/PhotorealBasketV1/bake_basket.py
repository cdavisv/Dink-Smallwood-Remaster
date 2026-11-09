import bpy,bmesh,json,time,sys,hashlib,os
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;source=O/'PhotorealBasketV1_Source.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pin=sha(source)
try:
 bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
 collection=bpy.data.collections['SM_Basket_Wicker_01'];s=next(s for s in bpy.data.scenes if collection.name in s.collection.children);bpy.context.window.scene=s
 name='SM_Basket_Wicker_01';ob=bpy.data.objects[name]
 for other in list(bpy.data.objects):
  if other not in list(collection.objects):bpy.data.objects.remove(other,do_unlink=True)
 for scene in list(bpy.data.scenes):
  if scene!=s:bpy.data.scenes.remove(scene)
 for col in list(bpy.data.collections):
  if col!=collection and not len(col.objects):bpy.data.collections.remove(col)
 collection['dink_path']='Stonebrook/PhotorealBasketV1';collection['dink_nanite']='yes';collection['dink_tex_px']=2048
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='FIXED',ngon_method='EAR_CLIP');bm.to_mesh(ob.data);bm.free();ob.data.update()
 ob.hide_render=False;ob.hide_set(False);bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 for other in s.objects:
  if other!=ob:other.hide_render=True
 s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=2;s.render.bake.margin=2;s.render.bake.use_selected_to_active=False;s.render.bake.use_clear=True
 (O/'Textures').mkdir(exist_ok=True);mats=list(ob.data.materials);images={};rows=[]
 for role,kind,socket in [('BC','EMIT','Base Color'),('Rough','EMIT','Roughness'),('Metal','EMIT','Metallic'),('N','NORMAL',None)]:
  im=bpy.data.images.new('T_Basket_Wicker_01_Photo_'+role,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB' if role=='BC' else 'Non-Color';restore=[]
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
 orm=bpy.data.images.new('T_Basket_Wicker_01_Photo_ORM',width=2048,height=2048,alpha=False);orm.colorspace_settings.name='Non-Color';orm.pixels.foreach_set(a.ravel());orm.filepath_raw=str(O/'Textures'/(orm.name+'.png'));orm.file_format='PNG';orm.save();orm.pack();orm.filepath='//Textures/'+orm.name+'.png'
 m=bpy.data.materials.new('MI_Basket_Wicker_01_PhotoBaked');n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.25;bs.inputs['IOR'].default_value=1.46
 for role,im in [('BC',images['BC']),('N',images['N']),('ORM',orm)]:
  t=n.new('ShaderNodeTexImage');t.image=im;t.name='T_Basket_'+role
  if role=='BC':l.new(t.outputs['Color'],bs.inputs['Base Color'])
  elif role=='N':
   nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
  else:
   sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs[1],bs.inputs['Roughness']);l.new(sp.outputs[2],bs.inputs['Metallic'])
 for mat in mats:mat.use_fake_user=True
 ob.data.materials.clear();ob.data.materials.append(m)
 for p in ob.data.polygons:p.material_index=0
 for im in bpy.data.images:
  if im.source=='FILE' and not im.packed_file:im.pack()
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealBasketV1_Export.blend'))
 assert sha(source)==pin
 (O/'bake_receipt.json').write_text(json.dumps({'complete':True,'rows':rows,'source_sha256':pin,'source_unchanged':True,'triangles':len(ob.data.polygons),'metallic_linear_range':[float(a[:,2].min()),float(a[:,2].max())],'metallic_nonzero_texels':int((a[:,2]>.1).sum()),'R_AO':'neutral1','BC':'Emission bake of authored procedural dry willow colour','normal':'tangent-space authored bump bake','ORM_sha256':sha(O/'Textures'/(orm.name+'.png'))},indent=2)+'\n');print('BAKE_COMPLETE',flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
except BaseException:
 import traceback
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
