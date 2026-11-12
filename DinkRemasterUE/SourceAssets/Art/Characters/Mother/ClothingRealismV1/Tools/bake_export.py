"""Bake only wardrobe to existing UV authority, export all4 LODs/89bones in process-only cm copy."""
import bpy,bmesh,json,sys
from pathlib import Path
H=Path(__file__).resolve().parents[1];P=next(p for p in H.parents if(p/'DinkRemaster.uproject').exists());sys.path.insert(0,str(P.parent/'tools/blender'))
from dinkasset import export_ue
bpy.ops.wm.open_mainfile(filepath=str(H/'SK_Mother_ClothingRealismV1.blend'));bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.threads_mode='FIXED';s.render.threads=1;s.render.bake.margin=8;s.render.bake.use_selected_to_active=False;s.render.bake.use_clear=True
meshes=[bpy.data.objects['SK_Mother_LOD%d'%i]for i in range(4)];arm=bpy.data.objects['Armature'];source=meshes[0];m=source.data.materials[4];nodes=m.node_tree.nodes;links=m.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
proxy=source.copy();proxy.data=source.data.copy();s.collection.objects.link(proxy);bm=bmesh.new();bm.from_mesh(proxy.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=4],context='FACES');bm.to_mesh(proxy.data);bm.free();proxy.data.materials.clear();proxy.data.materials.append(m)
for face in proxy.data.polygons:face.material_index=0
bpy.ops.object.select_all(action='DESELECT');proxy.hide_set(False);proxy.hide_render=False;proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
images={}
for kind in ['BC','ORM','N']:
 im=bpy.data.images.new('T_Mother_ClothingV1_'+kind,width=4096,height=4096,alpha=True);im.colorspace_settings.name='sRGB'if kind=='BC'else'Non-Color';target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
 if kind in ['BC','ORM']:
  emission=nodes.new('ShaderNodeEmission');sock=bs.inputs['Base Color'if kind=='BC'else'Roughness'];links.new(sock.links[0].from_socket,emission.inputs['Color']);links.new(emission.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT');links.new(bs.outputs[0],out.inputs['Surface']);nodes.remove(emission)
  if kind=='ORM':
   import numpy as np
   pix=np.array(im.pixels[:],dtype=np.float32).reshape(-1,4);pix[:,1]=pix[:,0];pix[:,0]=1;pix[:,2]=0;pix[:,3]=1;im.pixels.foreach_set(pix.ravel())
 else:bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
 im.filepath_raw=str(H/'Textures'/('T_Mother_ClothingV1_'+kind+'.png'));im.file_format='PNG';im.save();nodes.remove(target);loaded=bpy.data.images.load(im.filepath_raw,check_existing=False);loaded.colorspace_settings.name='sRGB'if kind=='BC'else'Non-Color';images[kind]=loaded;bpy.data.images.remove(im);loaded.name='T_Mother_ClothingV1_'+kind;print('BAKED',kind,flush=True)
bpy.data.objects.remove(proxy,do_unlink=True)
# Runtime-style packed sibling retains exact other four material graphs/images.
nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs['Surface']);bs.inputs['Specular IOR Level'].default_value=.28;bs.inputs['Sheen Weight'].default_value=.075
for k in images:
 t=nodes.new('ShaderNodeTexImage');t.image=images[k]
 if k=='BC':links.new(t.outputs['Color'],bs.inputs['Base Color'])
 elif k=='ORM':
  sep=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 else:
  n=nodes.new('ShaderNodeNormalMap');links.new(t.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
for im in bpy.data.images:
 if im.source=='FILE'and im.size[0]:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(H/'SK_Mother_ClothingRealismV1_Baked.blend'))
# Preserve source metre rest matrices; convert only temporary export memory to cm.
for ob in meshes:
 for v in ob.data.vertices:v.co*=100
bpy.ops.object.select_all(action='DESELECT');arm.hide_set(False);arm.select_set(True);bpy.context.view_layer.objects.active=arm;bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones:b.head*=100;b.tail*=100
bpy.ops.object.mode_set(mode='OBJECT');s.unit_settings.scale_length=.01
for mat in bpy.data.materials:
 if mat.node_tree:mat.node_tree.nodes.clear()
 mat.use_nodes=False
for i,ob in enumerate(meshes):
 asset=type('ExportAsset',(),{'renders':[ob],'collision':[],'armatures':[arm],'sockets':[]})()
 with export_ue.unhidden([ob,arm]):export_ue.export_fbx(asset,str(H/'Export'/('SK_Mother_ClothingV1_LOD%d.fbx'%i)),'all','Armature')
print('EXPORTED4LODS89BONES',flush=True)
