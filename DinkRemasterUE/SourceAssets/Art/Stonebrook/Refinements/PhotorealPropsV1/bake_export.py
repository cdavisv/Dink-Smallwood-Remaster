import bpy,json,time,sys,hashlib
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O/'Pipeline'));bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPropsV1.blend'));s=bpy.context.scene
names=['SM_Table_Oak_01','SM_Chair_Oak_01','SM_Bed_Oak_01']
# Final review corrections: exact legacy chair local bounds and explicit woven relief.
chair=bpy.data.objects['SM_Chair_Oak_01']
target_min=-.26875001192092896
chair_delta=target_min-min(v.co.y for v in chair.data.vertices)
for v in chair.data.vertices:v.co.y+=chair_delta
for ob in bpy.data.collections['SM_Chair_Oak_01'].objects:
 if ob.name.startswith('UCX_'):
  for v in ob.data.vertices:v.co.y+=chair_delta
for mn in ['MI_Photoreal_Flax','MI_Photoreal_UndyedLinen']:
 m=bpy.data.materials[mn];ns=m.node_tree.nodes;lk=m.node_tree.links
 col=(.04,.052,.012) if mn=='MI_Photoreal_Flax' else (.30,.265,.17)
 bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED');bs.inputs['Sheen Weight'].default_value=.03;bs.inputs['Sheen Tint'].default_value=(*[min(1,v*4)for v in col],1)
 ramp=next(n for n in ns if n.type=='VALTORGB');ramp.color_ramp.elements[0].color=(*[v*.72 for v in col],1);ramp.color_ramp.elements[1].color=(*[v*1.12 for v in col],1)
 tc=next(n for n in ns if n.type=='TEX_COORD');bump=next(n for n in ns if n.type=='BUMP')
 warp=ns.new('ShaderNodeTexWave');warp.wave_type='BANDS';warp.bands_direction='X';warp.inputs['Scale'].default_value=180;warp.inputs['Distortion'].default_value=.8;warp.inputs['Detail Scale'].default_value=2
 weft=ns.new('ShaderNodeTexWave');weft.wave_type='BANDS';weft.bands_direction='Y';weft.inputs['Scale'].default_value=240;weft.inputs['Distortion'].default_value=.6
 for n in [warp,weft]:lk.new(tc.outputs['Generated'],n.inputs[0])
 weave=ns.new('ShaderNodeMath');weave.operation='MULTIPLY';lk.new(warp.outputs['Fac'],weave.inputs[0]);lk.new(weft.outputs['Fac'],weave.inputs[1]);lk.new(weave.outputs[0],bump.inputs['Height']);bump.inputs['Distance'].default_value=.00045;bump.inputs['Strength'].default_value=.35
r=json.loads((O/'geometry_report.json').read_text());r['assets']['SM_Chair_Oak_01']['candidate_bounds_m']=[[min(v.co[k]for v in chair.data.vertices)for k in range(3)],[max(v.co[k]for v in chair.data.vertices)for k in range(3)]];r['final_review_corrections']=list(dict.fromkeys(r.get('final_review_corrections',[])+['Chair localY aligned to exact original bounds','Explicit woven warp/weft bump in linen materials']));(O/'geometry_report.json').write_text(json.dumps(r,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPropsV1.blend'))

# The exported asset scene includes only the three candidate collections and authored hulls.
for ob in list(s.objects):
 if not any(c.name in names for c in ob.users_collection):bpy.data.objects.remove(ob,do_unlink=True)
for c in list(bpy.data.collections):
 if c.name not in names and len(c.objects)==0:bpy.data.collections.remove(c)
s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.use_denoising=False;s.render.threads_mode='FIXED';s.render.threads=4;s.render.bake.margin=12;s.render.bake.use_pass_direct=False;s.render.bake.use_pass_indirect=False;s.render.bake.use_pass_color=True
(O/'Textures').mkdir(exist_ok=True);rows=[]
for name in names:
 ob=bpy.data.objects[name];bpy.ops.object.select_all(action='DESELECT')
 for n in names:bpy.data.objects[n].hide_render=n!=name
 ob.hide_render=False;ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mats=list(ob.data.materials);ims={}
 for role,kind in [('BC','DIFFUSE'),('Rough','ROUGHNESS'),('N','NORMAL')]:
  im=bpy.data.images.new('T_'+name[3:]+'_Photo_'+role,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB'if role=='BC'else'Non-Color'
  for m in mats:
   node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;node.label='Bake target';m.node_tree.nodes.active=node
  start=time.time();bpy.ops.object.bake(type=kind);im.filepath_raw=str(O/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save();im.pack();im.filepath='//Textures/'+im.name+'.png';ims[role]=im
  rows.append({'asset':name,'role':role,'seconds':time.time()-start,'image':im.name});(O/'bake_receipt.json').write_text(json.dumps(rows,indent=2));print('BAKED',name,role,flush=True)
 rough=ims['Rough'];rgba=np.empty(2048*2048*4,dtype=np.float32);rough.pixels.foreach_get(rgba);rgba=rgba.reshape(-1,4);rgba[:,1]=rgba[:,0];rgba[:,0]=1;rgba[:,2]=0;rgba[:,3]=1
 orm=bpy.data.images.new('T_'+name[3:]+'_Photo_ORM',width=2048,height=2048,alpha=False);orm.colorspace_settings.name='Non-Color';orm.pixels.foreach_set(rgba.ravel());orm.filepath_raw=str(O/'Textures'/(orm.name+'.png'));orm.file_format='PNG';orm.save();orm.pack();orm.filepath='//Textures/'+orm.name+'.png'
 m=bpy.data.materials.new('MI_'+name[3:]+'_PhotoBaked');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Specular IOR Level'].default_value=.3
 for role,im in [('BC',ims['BC']),('N',ims['N']),('ORM',orm)]:
  t=n.new('ShaderNodeTexImage');t.image=im
  if role=='BC':l.new(t.outputs['Color'],bs.inputs['Base Color'])
  elif role=='N':
   nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs[1]);l.new(nm.outputs[0],bs.inputs['Normal'])
  else:
   sp=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs[1],bs.inputs['Roughness']);l.new(sp.outputs[2],bs.inputs['Metallic'])
 for old in mats:old.use_fake_user=True
 ob.data.materials.clear();ob.data.materials.append(m)
 for p in ob.data.polygons:p.material_index=0
 ob.hide_render=False
for name in names:bpy.data.objects[name].hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPropsV1_Export.blend'))
print('BAKES_AND_EXPORT_SCENE_READY',flush=True)

# Blender audio teardown hangs in this sandbox; all durable writes above are complete.
import os,sys
sys.stdout.flush();sys.stderr.flush();os._exit(0)
