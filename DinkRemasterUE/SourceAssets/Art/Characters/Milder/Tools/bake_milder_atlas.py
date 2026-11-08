"""Bake the five-slot character into one unique-UV PBR atlas set."""
import bpy,json,sys
from pathlib import Path
import numpy as np
ROOT=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE');ART=ROOT/'SourceAssets/Art/Characters/Milder';TEX=ART/'Textures'
bpy.ops.wm.open_mainfile(filepath=str(ART/'Working/Milder_Rigged_PreBake.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
ob=bpy.data.objects['SK_Milder_LOD0'];arm=bpy.data.objects['Armature'];arm.data.pose_position='REST'
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
for mat in ob.data.materials:
    uv=mat.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='UVSource'
    for node in list(mat.node_tree.nodes):
        if node.type=='TEX_IMAGE':mat.node_tree.links.new(uv.outputs['UV'],node.inputs['Vector'])
atlas=ob.data.uv_layers.new(name='UVAtlas');ob.data.uv_layers.active=atlas;atlas.active_render=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.151917,island_margin=.0025,area_weight=.35,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=8;scene.render.bake.use_clear=True
N=4096
def image(name,linear=False):
    im=bpy.data.images.new(name,width=N,height=N,alpha=True)
    im.colorspace_settings.name='Non-Color' if linear else 'sRGB'
    return im
def bake_channel(name,channel,linear=False):
    im=image(name,linear);changes=[]
    for mat in ob.data.materials:
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
        before=out.inputs['Surface'].links[0].from_socket
        emit=nodes.new('ShaderNodeEmission')
        source=bs.inputs[channel]
        if source.is_linked:links.new(source.links[0].from_socket,emit.inputs['Color'])
        else:
            value=source.default_value
            emit.inputs['Color'].default_value=tuple(value) if channel=='Base Color' else (value,value,value,1)
        links.new(emit.outputs[0],out.inputs['Surface'])
        target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
        changes.append((mat,before,emit,target,out))
    bpy.ops.object.bake(type='EMIT')
    for mat,before,emit,target,out in changes:
        mat.node_tree.links.new(before,out.inputs['Surface']);mat.node_tree.nodes.remove(emit);mat.node_tree.nodes.remove(target)
    print('BAKED',channel,flush=True)
    return im
bc=bake_channel('T_Milder_Atlas_BC','Base Color')
alpha=bake_channel('MilderAlphaTemporary','Alpha',True)
color=np.array(bc.pixels[:],dtype=np.float32).reshape(-1,4)
mask=np.array(alpha.pixels[:],dtype=np.float32).reshape(-1,4)
color[:,3]=mask[:,0];bc.pixels.foreach_set(color.ravel())
bc.filepath_raw=str(TEX/'T_Milder_Atlas_BC.png');bc.file_format='PNG';bc.save()
del color,mask
rough=bake_channel('T_Milder_Atlas_ORM','Roughness',True)
metal=bake_channel('MilderMetalTemporary','Metallic',True)
metal_pixels=np.empty(N*N*4,dtype=np.float32);metal.pixels.foreach_get(metal_pixels)
pixels=np.array(rough.pixels[:],dtype=np.float32).reshape(-1,4);pixels[:,1]=pixels[:,0];pixels[:,0]=1;pixels[:,2]=metal_pixels.reshape(-1,4)[:,0];pixels[:,3]=1
rough.pixels.foreach_set(pixels.ravel());rough.filepath_raw=str(TEX/'T_Milder_Atlas_ORM.png');rough.file_format='PNG';rough.save();del pixels,metal_pixels
normal=image('T_Milder_Atlas_N',True)
for mat in ob.data.materials:
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=normal;mat.node_tree.nodes.active=node
bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
normal.filepath_raw=str(TEX/'T_Milder_Atlas_N.png');normal.file_format='PNG';normal.save()
materials={}
for mat in ob.data.materials:
    masked=mat.name in ['MI_Milder_Hair','MI_Milder_BrowLash'];skin=mat.name=='MI_Milder_Skin'
    mat.node_tree.nodes.clear();nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs['Surface'])
    tex=nodes.new('ShaderNodeTexImage');tex.image=bc;links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    if masked:links.new(tex.outputs['Alpha'],bs.inputs['Alpha']);mat.surface_render_method='DITHERED'
    if skin:bs.inputs['Subsurface Weight'].default_value=.08
    t=nodes.new('ShaderNodeTexImage');t.image=rough;sep=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    t=nodes.new('ShaderNodeTexImage');t.image=normal;n=nodes.new('ShaderNodeNormalMap');links.new(t.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
    materials[mat.name]={'base_color':[.5,.5,.5],'roughness':.5,'metallic':0,'alpha_mask':masked,'masked':masked,'two_sided':masked,
        'subsurface':.08 if skin else 0,'normal_strength':1,'normal_flip_green':True,
        'textures':{'BC':'Textures/T_Milder_Atlas_BC.png','N':'Textures/T_Milder_Atlas_N.png','ORM':'Textures/T_Milder_Atlas_ORM.png'}}
ob.data.uv_layers.remove(ob.data.uv_layers['UVSource']);ob.data.uv_layers[0].name='UVMap'
ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
(ART/'milder_materials.json').write_text(json.dumps(materials,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Working/Milder_Baked.blend'))
print('MILDER ATLAS:4096px unique UV; BC+alpha/N/ORM',flush=True)
