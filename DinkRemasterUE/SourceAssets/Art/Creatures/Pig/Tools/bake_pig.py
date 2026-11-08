"""Bake procedural original pig materials into a unique-UV2048 PBR atlas."""
import bpy,bmesh,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];TEX=ROOT/'Textures';TEX.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Pig_Working.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
arm=bpy.data.objects['Armature'];arm.data.pose_position='REST';arm.animation_data.action=None
ob=bpy.data.objects['SK_Pig_Stonebrook_LOD0']
# Enforce the reviewedv2 palette even if resuming an old procedural Working checkpoint.
source_skin=bpy.data.materials['MI_Pig_Skin']
for node in source_skin.node_tree.nodes:
    if node.type=='VALTORGB':node.color_ramp.elements[0].color=(.14,.115,.11,1);node.color_ramp.elements[1].color=(.32,.215,.20,1)
bpy.data.materials['MI_Pig_Muzzle'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.24,.125,.12,1)
# Remove microscopic Boolean slivers/wires before allocating atlas space.
bm=bmesh.new();bm.from_mesh(ob.data);bad=[f for f in bm.faces if f.calc_area()<1e-8]
if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
wire=[e for e in bm.edges if not e.link_faces]
if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(ob.data);bm.free();ob.data.update()
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer)
ob.data.uv_layers.new(name='UVMap');ob.data.uv_layers.active_index=0
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.003,area_weight=.3,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=6;scene.render.bake.use_clear=True
N=2048
def image(name,linear=False):
    im=bpy.data.images.new(name,width=N,height=N,alpha=True);im.colorspace_settings.name='Non-Color' if linear else 'sRGB';return im

def bake_channel(name,channel,linear=False):
    im=image(name,linear);changes=[]
    for mat in ob.data.materials:
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');before=out.inputs['Surface'].links[0].from_socket
        emit=nodes.new('ShaderNodeEmission');source=bs.inputs[channel]
        if source.is_linked:links.new(source.links[0].from_socket,emit.inputs['Color'])
        else:
            value=source.default_value;emit.inputs['Color'].default_value=tuple(value) if channel=='Base Color' else (value,value,value,1)
        links.new(emit.outputs[0],out.inputs['Surface']);target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target;changes.append((mat,before,emit,target,out))
    bpy.ops.object.bake(type='EMIT')
    for mat,before,emit,target,out in changes:
        mat.node_tree.links.new(before,out.inputs['Surface']);mat.node_tree.nodes.remove(emit);mat.node_tree.nodes.remove(target)
    print('PIG BAKED',channel,flush=True);return im
bc=bake_channel('T_Pig_Atlas_BC','Base Color');bc.filepath_raw=str(TEX/'T_Pig_Atlas_BC.png');bc.file_format='PNG';bc.save()
rough=bake_channel('T_Pig_Atlas_ORM','Roughness',True);pixels=np.empty(N*N*4,dtype=np.float32);rough.pixels.foreach_get(pixels);pixels=pixels.reshape(-1,4)
pixels[:,1]=pixels[:,0];pixels[:,0]=1;pixels[:,2]=0;pixels[:,3]=1;rough.pixels.foreach_set(pixels.ravel());rough.filepath_raw=str(TEX/'T_Pig_Atlas_ORM.png');rough.file_format='PNG';rough.save();del pixels
normal=image('T_Pig_Atlas_N',True)
for mat in ob.data.materials:
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=normal;mat.node_tree.nodes.active=node
bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT');normal.filepath_raw=str(TEX/'T_Pig_Atlas_N.png');normal.file_format='PNG';normal.save()
materials={}
for mat in ob.data.materials:
    subsurface=.055 if mat.name=='MI_Pig_Skin' else (.07 if mat.name=='MI_Pig_Muzzle' else 0)
    mat.node_tree.nodes.clear();nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs['Surface']);bs.inputs['Subsurface Weight'].default_value=subsurface
    tex=nodes.new('ShaderNodeTexImage');tex.image=bc;links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    t=nodes.new('ShaderNodeTexImage');t.image=rough;sep=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    t=nodes.new('ShaderNodeTexImage');t.image=normal;n=nodes.new('ShaderNodeNormalMap');links.new(t.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
    materials[mat.name]={'base_color':[.5,.5,.5],'roughness':.6,'metallic':0,'masked':False,'two_sided':False,'subsurface':subsurface,'normal_strength':1,'normal_flip_green':True,
                        'textures':{'BC':'Textures/T_Pig_Atlas_BC.png','N':'Textures/T_Pig_Atlas_N.png','ORM':'Textures/T_Pig_Atlas_ORM.png'}}
for name,color in [('MI_Pig_Skin',[.234,.166,.157]),('MI_Pig_Muzzle',[.2395,.125,.119])]:
    materials[name]['base_color']=color;materials[name]['appearance_revision']='skin-muzzle-linear-half-v2'
(ROOT/'pig_materials.json').write_text(json.dumps(materials,indent=2)+'\n');(ROOT/'Working').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Working/Pig_Baked.blend'))
print('PIG ATLAS READY2048,4slots',flush=True)
